"""
Enhanced processor for ML-based temperature super-resolution
"""

import numpy as np
import pathlib
from typing import Dict, List, Optional, Tuple
import logging
import h5py

from ml_models import TemperatureSRProcessor
from ml_models.sr_processor import EnhancedPolarProcessor

logger = logging.getLogger(__name__)


class EnhancedProcessor:
    """Processor for ML-enhanced satellite data"""

    def __init__(self, model_path: pathlib.Path, device: str = None):
        """
        Initialize enhanced processor

        Args:
            model_path: Path to trained ML model
            device: Device to use, auto-detected if None
        """
        if device is None:
            from utils.device_utils import get_best_device
            device_obj, device_name = get_best_device()
            print(f"Enhanced Processor using: {device_name}")
            device = str(device_obj)

        self.sr_processor = TemperatureSRProcessor(model_path, device=device)

    def extract_coordinates_from_h5(self, h5_path: pathlib.Path) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract latitude and longitude coordinates from HDF5 file

        Args:
            h5_path: Path to HDF5 file

        Returns:
            Tuple of (latitude, longitude) arrays
        """
        with h5py.File(h5_path, "r") as h5:
            lat_89 = None
            lon_89 = None

            # Find 89 GHz coordinates
            for suffix in ["89A", "89B"]:
                lat_key = f"Latitude of Observation Point for {suffix}"
                lon_key = f"Longitude of Observation Point for {suffix}"

                if lat_key in h5 and lon_key in h5:
                    lat_89 = h5[lat_key][:]
                    lon_89 = h5[lon_key][:]
                    break

            if lat_89 is None:
                raise ValueError("Coordinates not found in file!")

            # Downsample if needed for 36.5 GHz
            if lat_89.shape[1] == 486:  # High resolution
                lat_36 = lat_89[:, ::2]
                lon_36 = lon_89[:, ::2]
            else:
                lat_36 = lat_89
                lon_36 = lon_89

            return lat_36, lon_36

    def save_enhanced_results(self, results: Dict, output_dir: pathlib.Path,
                              sample_name: str, percentile_filter: bool = True):
        """
        Save enhanced results with proper formatting

        Args:
            results: Dictionary with enhanced data
            output_dir: Output directory
            sample_name: Name for the sample
            percentile_filter: Apply 1-99 percentile filter for images
        """
        import matplotlib.pyplot as plt
        from PIL import Image

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get temperature data
        temp_8x = results['temperature_8x']

        # Save NPZ with all data
        npz_path = output_dir / f"{sample_name}_enhanced_8x.npz"
        np.savez_compressed(
            npz_path,
            temperature=temp_8x,
            coordinates_lat=results.get('coordinates_lat_8x'),
            coordinates_lon=results.get('coordinates_lon_8x'),
            statistics=results['statistics'],
            metadata=results['metadata']
        )
        logger.info(f"Saved enhanced data to {npz_path}")

        # Apply percentile filter if requested
        if percentile_filter:
            p_low, p_high = 1, 99
            temp_min, temp_max = np.nanpercentile(temp_8x, [p_low, p_high])
        else:
            temp_min, temp_max = np.nanmin(temp_8x), np.nanmax(temp_8x)

        # Clip temperature data
        temp_clipped = np.clip(temp_8x, temp_min, temp_max)

        # Normalize for visualization
        temp_norm = (temp_clipped - temp_min) / (temp_max - temp_min)

        # Save color image with exact pixel correspondence
        color_path = output_dir / f"{sample_name}_enhanced_8x_color.png"
        h, w = temp_8x.shape
        dpi = 100

        # Create figure with exact pixel dimensions
        fig = plt.figure(figsize=(w / dpi, h / dpi), dpi=dpi)
        ax = plt.axes([0, 0, 1, 1])  # Fill entire figure
        ax.axis('off')

        # Apply percentile filter if requested
        if percentile_filter:
            p_low, p_high = 1, 99
            temp_min, temp_max = np.nanpercentile(temp_8x, [p_low, p_high])
        else:
            temp_min, temp_max = np.nanmin(temp_8x), np.nanmax(temp_8x)

        # Get turbo colormap and set NaN to black
        import matplotlib.cm as cm
        turbo = cm.get_cmap('turbo')
        turbo.set_bad(color='black')

        # Plot with exact pixel mapping
        ax.imshow(
            temp_8x,
            cmap=turbo,
            vmin=temp_min,
            vmax=temp_max,
            interpolation='nearest',  # No smoothing
            aspect='auto'
        )

        # Save without any margins
        plt.savefig(color_path, dpi=dpi, bbox_inches='tight', pad_inches=0)
        plt.close()

        # Save grayscale image
        gray_img = (temp_norm * 255).astype(np.uint8)
        gray_path = output_dir / f"{sample_name}_enhanced_8x_gray.png"
        Image.fromarray(gray_img, mode='L').save(gray_path)

        logger.info(f"Saved images to {output_dir}")

        # Log statistics
        stats = results['statistics']
        logger.info("Enhancement Statistics:")
        logger.info(f"  Original: {stats['original']['shape']} -> "
                    f"Enhanced: {temp_8x.shape}")
        logger.info(f"  Temperature range: [{stats['original']['min_temp']:.1f}, "
                    f"{stats['original']['max_temp']:.1f}] -> "
                    f"[{stats['stage_8x']['min_temp']:.1f}, "
                    f"{stats['stage_8x']['max_temp']:.1f}] K")
        logger.info(f"  Average temperature: {stats['original']['avg_temp']:.1f} -> "
                    f"{stats['stage_8x']['avg_temp']:.1f} K")