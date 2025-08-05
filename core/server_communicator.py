"""
Server communication module for SatelliteProcessor client
Handles job submission, monitoring, and result retrieval
"""

import os
import json
import time
import uuid
import pathlib
import paramiko
import subprocess
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ServerCommunicator:
    """Handles all communication with the HPC server"""

    def __init__(self, auth_manager):
        self.auth_manager = auth_manager

        # Server configuration
        self.gateway_host = "ash.ssec.wisc.edu"
        self.gateway_user = "vdidur"
        self.compute_host = "orchid-submit"
        self.server_base_path = "/home/vdidur/Server_SatelliteProcessor"

        # SSH clients
        self.gateway_client = None
        self.compute_client = None

    def connect(self) -> bool:
        """Establish SSH connection through gateway to compute node"""
        try:
            # Connect to gateway
            self.gateway_client = paramiko.SSHClient()
            self.gateway_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Try key-based auth first, then password
            try:
                self.gateway_client.connect(
                    self.gateway_host,
                    username=self.gateway_user,
                    key_filename=os.path.expanduser("~/.ssh/id_rsa")
                )
            except:
                # Fallback to password (you'll need to handle this)
                password = input(f"Enter password for {self.gateway_user}@{self.gateway_host}: ")
                self.gateway_client.connect(
                    self.gateway_host,
                    username=self.gateway_user,
                    password=password
                )

            # Create channel for compute node
            gateway_transport = self.gateway_client.get_transport()
            dest_addr = (self.compute_host, 22)
            local_addr = ('127.0.0.1', 0)
            channel = gateway_transport.open_channel("direct-tcpip", dest_addr, local_addr)

            # Connect to compute node
            self.compute_client = paramiko.SSHClient()
            self.compute_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.compute_client.connect(
                self.compute_host,
                username="vdidur",
                sock=channel,
                key_filename=os.path.expanduser("~/.ssh/id_rsa")
            )

            logger.info("Successfully connected to server")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False

    def disconnect(self):
        """Close SSH connections"""
        if self.compute_client:
            self.compute_client.close()
        if self.gateway_client:
            self.gateway_client.close()

    def submit_job(self, function: str, parameters: Dict) -> Optional[str]:
        """
        Submit a job to the server

        Args:
            function: Function name (polar_circle, single_strip, etc.)
            parameters: Job parameters

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            # Generate job ID
            job_id = f"{function}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            # Add credentials to parameters
            username, password = self.auth_manager.get_credentials()
            parameters['credentials'] = {
                'username': username,
                'password': password
            }

            # Create job data
            job_data = {
                'job_id': job_id,
                'function': function,
                'parameters': parameters,
                'status': 'pending',
                'submitted_time': datetime.now().isoformat()
            }

            # Write job file to server
            job_content = json.dumps(job_data, indent=2)
            job_filename = f"{job_id}.json"
            remote_path = f"{self.server_base_path}/jobs/pending/{job_filename}"

            # Create job file on server
            stdin, stdout, stderr = self.compute_client.exec_command(
                f"echo '{job_content}' > {remote_path}"
            )
            stderr_content = stderr.read().decode()
            if stderr_content:
                logger.error(f"Error creating job file: {stderr_content}")
                return None

            logger.info(f"Job submitted: {job_id}")

            # Check if processor is running, if not, submit SLURM job
            self._ensure_processor_running()

            return job_id

        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            return None

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current status of a job"""
        try:
            # Check in different directories
            for status_dir in ['pending', 'running', 'completed', 'failed']:
                remote_path = f"{self.server_base_path}/jobs/{status_dir}/{job_id}.json"

                stdin, stdout, stderr = self.compute_client.exec_command(
                    f"cat {remote_path} 2>/dev/null"
                )

                content = stdout.read().decode()
                if content:
                    return json.loads(content)

            return None

        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None

    def download_results(self, job_id: str, local_dir: pathlib.Path) -> bool:
        """Download job results from server"""
        try:
            # Create local directory
            local_dir.mkdir(parents=True, exist_ok=True)

            # Use scp through gateway
            remote_path = f"{self.server_base_path}/results/{job_id}"

            # Build scp command
            scp_cmd = [
                "scp", "-r",
                "-oProxyJump=ash@vdidur.ssec.wisc.edu",
                f"vdidur@orchid-submit:{remote_path}/*",
                str(local_dir)
            ]

            # Execute scp
            result = subprocess.run(scp_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"SCP failed: {result.stderr}")
                return False

            logger.info(f"Results downloaded to {local_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to download results: {e}")
            return False

    def cleanup_job(self, job_id: str) -> bool:
        """Clean up job files on server (carefully!)"""
        try:
            # Only clean up results directory, never code!
            commands = [
                f"rm -rf {self.server_base_path}/results/{job_id}",
                f"rm -f {self.server_base_path}/jobs/completed/{job_id}.json"
            ]

            for cmd in commands:
                stdin, stdout, stderr = self.compute_client.exec_command(cmd)
                stderr_content = stderr.read().decode()
                if stderr_content:
                    logger.warning(f"Cleanup warning: {stderr_content}")

            logger.info(f"Cleaned up job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clean up job: {e}")
            return False

    def _ensure_processor_running(self):
        """Ensure job processor is running on server"""
        try:
            # Check if processor is already running
            stdin, stdout, stderr = self.compute_client.exec_command(
                "squeue -u vdidur -n satproc_job -h | wc -l"
            )

            running_jobs = int(stdout.read().decode().strip())

            if running_jobs == 0:
                # Submit new SLURM job
                logger.info("Starting job processor on server...")
                stdin, stdout, stderr = self.compute_client.exec_command(
                    f"cd {self.server_base_path} && sbatch sbatch/process_job.sbatch"
                )

                output = stdout.read().decode()
                if "Submitted batch job" in output:
                    logger.info("Job processor started successfully")
                else:
                    logger.warning(f"Job processor submission output: {output}")

        except Exception as e:
            logger.error(f"Failed to ensure processor running: {e}")

    def wait_for_job(self, job_id: str, timeout: int = 3600,
                     progress_callback=None) -> Optional[Dict]:
        """
        Wait for job to complete

        Args:
            job_id: Job ID to monitor
            timeout: Maximum wait time in seconds
            progress_callback: Function to call with status updates

        Returns:
            Final job status or None if timeout
        """
        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)

            if status and status != last_status:
                last_status = status

                if progress_callback:
                    progress_callback(status)

                if status['status'] in ['completed', 'failed']:
                    return status

            time.sleep(5)  # Check every 5 seconds

        logger.warning(f"Job {job_id} timed out after {timeout} seconds")
        return None