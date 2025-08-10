"""
Main processor for temperature super-resolution
Handles both 8x single strip and 8x polar enhancements
"""

import torch
import numpy as np
import cv2
import pathlib
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import logging
from tqdm import tqdm
import gc
import pyproj
import sys

from .temperature_sr_model import TemperatureSRModel
from .data_preprocessing import TemperatureDataPreprocessor
from .config import load_config

logger = logging.getLogger(__name__)


class TemperatureSRProcessor:
    """Temperature Super-Resolution Processor for 8x enhancement"""

    def __init__(self, model_path: Path, device: str = None):
        """
        Initialize SR processor

        Args:
            model_path: Path to trained model checkpoint
            device: Device to run on ('cuda' or 'cpu')
        """
        if device is None:
            from utils.device_utils import get_best_device
            self.device, device_name = get_best_device()
            print(f"SR Processor using: {device_name}")
        else:
            self.device = torch.device(device)
        self.model = self._load_model(model_path)
        self.preprocessor = TemperatureDataPreprocessor()

    def _load_model(self, model_path: Path) -> TemperatureSRModel:
        """Load trained temperature SR model"""
        # Load configuration
        opt = load_config()
        opt['is_train'] = False
        opt['dist'] = False

        # Create model
        model = TemperatureSRModel(opt)

        # Load checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)

        if isinstance(checkpoint, dict) and 'params' in checkpoint:
            model.net_g.load_state_dict(checkpoint['params'], strict=True)
        elif isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            model.net_g.load_state_dict(checkpoint['state_dict'], strict=True)
        else:
            model.net_g.load_state_dict(checkpoint, strict=True)

        model.net_g.eval()
        model.net_g.to(self.device)

        logger.info(f"Model loaded from {model_path}")
        return model

    def extract_coordinates_from_h5(self, h5_path: pathlib.Path) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract latitude and longitude coordinates from HDF5 file
        """
        import h5py

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

    def process_single_strip_8x(self, temperature_data: np.ndarray,
                                coordinates_lat: np.ndarray,
                                coordinates_lon: np.ndarray,
                                metadata: Dict) -> Dict:
        """
        Process single strip with 8x enhancement

        Args:
            temperature_data: Temperature array
            coordinates_lat: Latitude coordinates
            coordinates_lon: Longitude coordinates
            metadata: Metadata dictionary

        Returns:
            Dictionary with enhanced data and statistics
        """
        logger.info("Starting 8x enhancement for single strip")

        # Store original stats
        orig_stats = {
            'min_temp': float(np.min(temperature_data)),
            'max_temp': float(np.max(temperature_data)),
            'avg_temp': float(np.mean(temperature_data)),
            'shape': temperature_data.shape
        }

        # Stage 1: First 2x enhancement
        logger.info("Stage 1: First 2x enhancement")
        sr_2x, stats_2x = self._enhance_2x(temperature_data)

        # Stage 2: Second 2x enhancement (4x total)
        logger.info("Stage 2: Second 2x enhancement (4x total)")
        sr_4x, stats_4x = self._enhance_2x(sr_2x)

        # Stage 3: Third 2x enhancement (8x total)
        logger.info("Stage 3: Third 2x enhancement (8x total)")
        sr_8x, stats_8x = self._enhance_2x(sr_4x)

        # Upscale coordinates by 8x
        logger.info("Upscaling coordinates 8x")
        coords_lat_8x = self._upscale_coordinates(coordinates_lat, scale=8)
        coords_lon_8x = self._upscale_coordinates(coordinates_lon, scale=8)

        # Create bicubic baseline for comparison
        bicubic_8x = cv2.resize(temperature_data,
                                (temperature_data.shape[1] * 8, temperature_data.shape[0] * 8),
                                interpolation=cv2.INTER_CUBIC)

        # Compile statistics
        final_stats = {
            'original': orig_stats,
            'stage_2x': stats_2x,
            'stage_4x': stats_4x,
            'stage_8x': stats_8x,
            'enhancement_ratio': {
                'min_preserved': stats_8x['min_temp'] / orig_stats['min_temp'],
                'max_preserved': stats_8x['max_temp'] / orig_stats['max_temp'],
                'avg_preserved': stats_8x['avg_temp'] / orig_stats['avg_temp']
            }
        }

        logger.info(f"Enhancement complete: {orig_stats['shape']} → {sr_8x.shape}")
        logger.info(f"Temperature range: [{orig_stats['min_temp']:.1f}, {orig_stats['max_temp']:.1f}] → "
                    f"[{stats_8x['min_temp']:.1f}, {stats_8x['max_temp']:.1f}] K")

        return {
            'temperature_8x': sr_8x,
            'coordinates_lat_8x': coords_lat_8x,
            'coordinates_lon_8x': coords_lon_8x,
            'temperature_bicubic_8x': bicubic_8x,
            'statistics': final_stats,
            'metadata': {**metadata, 'enhancement': '8x', 'method': 'cascaded_swinir'}
        }

    def calculate_swinir_patch_size(self, input_shape: Tuple[int, int],
                                    target_patch_size: Tuple[int, int] = (1000, 110)) -> Tuple[int, int]:
        """Calculate optimal patch size for SwinIR"""
        h, w = input_shape
        window_size = 8  # SwinIR window size

        # Ensure patch dimensions are divisible by window_size * scale
        factor = window_size * 2  # scale = 2

        patch_h = (target_patch_size[0] // factor) * factor
        patch_w = (target_patch_size[1] // factor) * factor

        # Ensure patches are not larger than input
        patch_h = min(patch_h, h)
        patch_w = min(patch_w, w)

        return (patch_h, patch_w)

    def _enhance_2x(self, temperature: np.ndarray,
                    patch_size: Tuple[int, int] = (1000, 110),
                    overlap_ratio: float = 0.75) -> Tuple[np.ndarray, Dict]:
        """Single 2x enhancement step with proper patch sizing"""
        h, w = temperature.shape

        # Calculate statistics before enhancement
        stats_before = {
            'min_temp': float(np.min(temperature)),
            'max_temp': float(np.max(temperature)),
            'avg_temp': float(np.mean(temperature))
        }

        # Normalize to [0, 1] for SwinIR
        temp_min, temp_max = stats_before['min_temp'], stats_before['max_temp']

        if temp_max > temp_min:
            normalized = (temperature - temp_min) / (temp_max - temp_min)
        else:
            normalized = np.zeros_like(temperature)

        # Adapt patch size to ensure divisibility
        patch_size = self.calculate_swinir_patch_size((h, w), patch_size)

        # Process with patch-based approach
        patches = self._extract_patches(normalized, patch_size, overlap_ratio)
        sr_patches = []

        with torch.no_grad():
            for patch_info in tqdm(patches, desc="Processing patches", leave=False):
                patch = patch_info['data']

                # Convert to tensor - no padding needed as patch is already correct size
                patch_tensor = torch.from_numpy(patch).float()
                patch_tensor = patch_tensor.unsqueeze(0).unsqueeze(0).to(self.device)

                # Super-resolution
                sr_patch = self.model.net_g(patch_tensor)
                sr_patch = torch.clamp(sr_patch, 0, 1)
                sr_patch = sr_patch.squeeze().cpu().numpy()

                sr_patches.append({
                    'data': sr_patch,
                    'position': patch_info['position'],
                    'size': sr_patch.shape
                })

        # Reconstruct full image
        sr_normalized = self._reconstruct_from_patches(sr_patches, (h * 2, w * 2))

        # Denormalize back to temperature
        sr_temperature = sr_normalized * (temp_max - temp_min) + temp_min

        # Calculate statistics after enhancement
        stats_after = {
            'min_temp': float(np.min(sr_temperature)),
            'max_temp': float(np.max(sr_temperature)),
            'avg_temp': float(np.mean(sr_temperature)),
            'shape': sr_temperature.shape
        }

        # Clear memory
        torch.cuda.empty_cache()
        gc.collect()

        return sr_temperature, stats_after

    def _extract_patches(self, image: np.ndarray,
                         patch_size: Tuple[int, int],
                         overlap_ratio: float) -> List[Dict]:
        """Extract overlapping patches from image"""
        h, w = image.shape
        patch_h, patch_w = patch_size

        # Ensure patch size doesn't exceed image size
        patch_h = min(patch_h, h)
        patch_w = min(patch_w, w)

        # Calculate stride
        stride_h = int(patch_h * (1 - overlap_ratio))
        stride_w = int(patch_w * (1 - overlap_ratio))

        patches = []

        for y in range(0, h - patch_h + 1, stride_h):
            for x in range(0, w - patch_w + 1, stride_w):
                # Ensure we don't go out of bounds
                if y + patch_h > h:
                    y = h - patch_h
                if x + patch_w > w:
                    x = w - patch_w

                patch = image[y:y + patch_h, x:x + patch_w]
                patches.append({
                    'data': patch,
                    'position': (y, x),
                    'size': (patch_h, patch_w)
                })

        # Add edge patches if needed
        if (h - 1) % stride_h != 0:
            y = h - patch_h
            for x in range(0, w - patch_w + 1, stride_w):
                if x + patch_w > w:
                    x = w - patch_w
                patch = image[y:y + patch_h, x:x + patch_w]
                patches.append({
                    'data': patch,
                    'position': (y, x),
                    'size': (patch_h, patch_w)
                })

        if (w - 1) % stride_w != 0:
            x = w - patch_w
            for y in range(0, h - patch_h + 1, stride_h):
                if y + patch_h > h:
                    y = h - patch_h
                patch = image[y:y + patch_h, x:x + patch_w]
                patches.append({
                    'data': patch,
                    'position': (y, x),
                    'size': (patch_h, patch_w)
                })

        return patches

    def _reconstruct_from_patches(self, patches: List[Dict],
                                  output_shape: Tuple[int, int]) -> np.ndarray:
        """Reconstruct full image from patches with blending"""
        h, w = output_shape
        output = np.zeros((h, w), dtype=np.float64)
        weight = np.zeros((h, w), dtype=np.float64)

        for patch_info in patches:
            patch = patch_info['data']
            y, x = patch_info['position']
            y *= 2  # Scale position for 2x output
            x *= 2

            patch_h, patch_w = patch.shape

            # Create Gaussian weight for smooth blending
            weight_patch = self._create_gaussian_weight(patch.shape)

            # Add to output with weights
            output[y:y + patch_h, x:x + patch_w] += patch * weight_patch
            weight[y:y + patch_h, x:x + patch_w] += weight_patch

        # Normalize by weights
        mask = weight > 0
        output[mask] = output[mask] / weight[mask]

        return output

    def _create_gaussian_weight(self, shape: Tuple[int, int], sigma_ratio: float = 0.3) -> np.ndarray:
        """Create 2D Gaussian weight map for smooth blending"""
        h, w = shape

        # Create coordinate grids
        y, x = np.ogrid[:h, :w]
        center_y, center_x = h / 2, w / 2

        # Calculate Gaussian weights
        sigma_y = h * sigma_ratio
        sigma_x = w * sigma_ratio

        gaussian = np.exp(-((y - center_y) ** 2 / (2 * sigma_y ** 2) +
                            (x - center_x) ** 2 / (2 * sigma_x ** 2)))

        # Normalize to [0, 1]
        gaussian = (gaussian - gaussian.min()) / (gaussian.max() - gaussian.min())

        return gaussian.astype(np.float32)

    def _upscale_coordinates(self, coords: np.ndarray, scale: int = 8) -> np.ndarray:
        """
        Upscale coordinate array by given scale factor

        The corner coordinates remain the same, with interpolated values in between
        """
        if len(coords.shape) == 1:
            # 1D coordinate array
            n = len(coords)
            new_n = (n - 1) * scale + 1

            # Create interpolation indices
            old_indices = np.arange(n)
            new_indices = np.linspace(0, n - 1, new_n)

            # Interpolate
            upscaled = np.interp(new_indices, old_indices, coords)

        else:
            # 2D coordinate array
            h, w = coords.shape
            new_h = (h - 1) * scale + 1
            new_w = (w - 1) * scale + 1

            # Use cv2 for 2D interpolation
            upscaled = cv2.resize(coords, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        return upscaled

    def process_polar_8x_enhanced(self, h5_files: List[Path],
                                  orbit_type: str,
                                  pole: str = "N") -> Dict:
        """
        Process multiple files for 8x enhanced polar image

        Args:
            h5_files: List of HDF5 file paths
            orbit_type: 'A' or 'D'
            pole: 'N' or 'S'

        Returns:
            Dictionary with enhanced polar data
        """
        from core.data_handler import DataHandler
        from core.image_processor import ImageProcessor

        data_handler = DataHandler()
        enhanced_swaths = []

        logger.info(f"Processing {len(h5_files)} files for 8x enhanced polar image")

        # Process each file individually
        for idx, h5_file in enumerate(h5_files):
            logger.info(f"Processing file {idx + 1}/{len(h5_files)}: {h5_file.name}")

            # Extract temperature data
            temp_data, scale_factor = data_handler.extract_temperature_data(h5_file)

            if temp_data is None:
                logger.warning(f"Failed to extract data from {h5_file.name}")
                continue

            # Extract coordinates
            lat, lon = self.extract_coordinates_from_h5(h5_file)

            # Enhance temperature to 8x
            enhanced_result = self.process_single_strip_8x(
                temp_data, lat, lon,
                {'orbit_type': orbit_type, 'scale_factor': scale_factor}
            )

            enhanced_swaths.append({
                'temperature': enhanced_result['temperature_8x'],
                'lat': enhanced_result['coordinates_lat_8x'],
                'lon': enhanced_result['coordinates_lon_8x'],
                'metadata': enhanced_result['metadata']
            })

            # Clear memory
            gc.collect()
            torch.cuda.empty_cache()

        # Create enhanced polar image with 8x larger grid
        logger.info("Creating 8x enhanced polar projection")

        # Create custom image processor for 8x grid
        enhanced_processor = EnhancedPolarProcessor(scale_factor=8)

        # Combine all enhanced swaths into polar projection
        polar_temperature_8x = enhanced_processor.create_enhanced_polar_image(
            enhanced_swaths, orbit_type, pole
        )

        # Apply percentile normalization (1-99 percentile)
        p_low, p_high = 1, 99
        temp_min, temp_max = np.percentile(polar_temperature_8x[~np.isnan(polar_temperature_8x)],
                                           [p_low, p_high])

        # Calculate statistics
        valid_mask = ~np.isnan(polar_temperature_8x)
        stats = {
            'min_temp': float(np.min(polar_temperature_8x[valid_mask])),
            'max_temp': float(np.max(polar_temperature_8x[valid_mask])),
            'avg_temp': float(np.mean(polar_temperature_8x[valid_mask])),
            'percentile_1': float(temp_min),
            'percentile_99': float(temp_max),
            'valid_pixels': int(np.sum(valid_mask)),
            'total_pixels': int(polar_temperature_8x.size),
            'coverage_percent': float(100 * np.sum(valid_mask) / polar_temperature_8x.size)
        }

        logger.info(f"Enhanced polar image created: {polar_temperature_8x.shape}")
        logger.info(f"Temperature range: [{stats['min_temp']:.1f}, {stats['max_temp']:.1f}] K")
        logger.info(f"Coverage: {stats['coverage_percent']:.1f}%")

        return {
            'temperature_8x': polar_temperature_8x,
            'statistics': stats,
            'percentile_range': (temp_min, temp_max),
            'metadata': {
                'orbit_type': orbit_type,
                'pole': pole,
                'num_swaths': len(enhanced_swaths),
                'enhancement': '8x',
                'grid_size': polar_temperature_8x.shape
            }
        }


class EnhancedPolarProcessor:
    """Processor for creating 8x enhanced polar projections"""

    def __init__(self, scale_factor: int = 8):
        self.scale_factor = scale_factor

        # Original EASE-Grid 2.0 parameters
        self.PIXEL_SIZE_M = 10000.0  # 10 km
        self.GRID_WIDTH = 1800
        self.GRID_HEIGHT = 1800

        # Enhanced grid parameters
        self.ENHANCED_PIXEL_SIZE_M = self.PIXEL_SIZE_M / scale_factor  # 1.25 km for 8x
        self.ENHANCED_GRID_WIDTH = self.GRID_WIDTH * scale_factor  # 14400 for 8x
        self.ENHANCED_GRID_HEIGHT = self.GRID_HEIGHT * scale_factor  # 14400 for 8x

        # Map origin remains the same
        self.MAP_ORIGIN_X = -9000000.0
        self.MAP_ORIGIN_Y = 9000000.0

        # Grid registration offset
        self.GRID_ORIGIN_COL = -0.5
        self.GRID_ORIGIN_ROW = -0.5

        # Set up projections
        import pyproj
        self.ease2_north = pyproj.CRS.from_epsg(6931)
        self.ease2_south = pyproj.CRS.from_epsg(6932)
        self.wgs84 = pyproj.CRS.from_epsg(4326)

        # Transformer will be set based on pole
        self.transformer = None

    def create_enhanced_polar_image(self, enhanced_swaths: List[Dict],
                                    orbit_type: str, pole: str = "N") -> np.ndarray:
        """Create 8x enhanced polar image from enhanced swaths"""

        # Set up transformer based on pole
        if pole == "N":
            self.transformer = pyproj.Transformer.from_crs(
                self.wgs84, self.ease2_north, always_xy=True
            )
        else:  # pole == "S"
            self.transformer = pyproj.Transformer.from_crs(
                self.wgs84, self.ease2_south, always_xy=True
            )

        # Create enhanced grids
        grid = np.zeros((self.ENHANCED_GRID_HEIGHT, self.ENHANCED_GRID_WIDTH), dtype=np.float64)
        weight = np.zeros((self.ENHANCED_GRID_HEIGHT, self.ENHANCED_GRID_WIDTH), dtype=np.float64)
        count = np.zeros((self.ENHANCED_GRID_HEIGHT, self.ENHANCED_GRID_WIDTH), dtype=np.int32)

        # Process each enhanced swath
        for swath_idx, swath in enumerate(enhanced_swaths):
            self._add_enhanced_swath_to_grid(
                swath, grid, weight, count, swath_idx, pole
            )

        # Finalize grid
        final_grid = self._finalize_grid(grid, weight)

        # Apply hole filling
        final_grid = self._fill_holes_enhanced(final_grid)

        return final_grid

    def _add_enhanced_swath_to_grid(self, swath: Dict, grid: np.ndarray,
                                    weight: np.ndarray, count: np.ndarray,
                                    swath_idx: int, pole: str = "N"):
        """Add enhanced swath data to grid"""
        temp = swath['temperature']
        lat = swath['lat']
        lon = swath['lon']

        # Filter for correct hemisphere
        if pole == "N":
            hemisphere_mask = lat >= 0
        else:  # pole == "S"
            hemisphere_mask = lat <= 0

        if not np.any(hemisphere_mask):
            return

        # Transform to EASE-Grid 2.0
        x_ease2, y_ease2 = self._latlon_to_ease2(lat, lon)

        # Get grid bounds
        x_min, x_max, y_min, y_max = self._get_grid_bounds()

        # Valid data mask
        valid_mask = (
                hemisphere_mask &
                ~np.isnan(temp) &
                (x_ease2 >= x_min) & (x_ease2 <= x_max) &
                (y_ease2 >= y_min) & (y_ease2 <= y_max)
        )

        if not np.any(valid_mask):
            return

        # Extract valid values
        if len(temp.shape) == 2:
            x_vals = x_ease2[valid_mask]
            y_vals = y_ease2[valid_mask]
            temp_vals = temp[valid_mask]
        else:
            # Handle 1D arrays
            x_vals = x_ease2[valid_mask]
            y_vals = y_ease2[valid_mask]
            temp_vals = temp[valid_mask]

        # Convert to pixel indices (enhanced resolution)
        px_x, px_y = self._meters_to_pixels_enhanced(x_vals, y_vals)

        # Check bounds
        valid_pixels = (
                (px_x >= 0) & (px_x < self.ENHANCED_GRID_WIDTH) &
                (px_y >= 0) & (px_y < self.ENHANCED_GRID_HEIGHT)
        )

        px_x = px_x[valid_pixels]
        px_y = px_y[valid_pixels]
        temp_vals = temp_vals[valid_pixels]

        # Accumulate data
        for i in range(len(temp_vals)):
            x_idx, y_idx = px_x[i], px_y[i]
            value = temp_vals[i]

            grid[y_idx, x_idx] += value
            weight[y_idx, x_idx] += 1.0
            count[y_idx, x_idx] += 1

    def _latlon_to_ease2(self, lat, lon):
        """Transform coordinates to EASE-Grid 2.0 (North or South based on current transformer)"""
        x, y = self.transformer.transform(lon, lat)
        x = np.where(np.isinf(x), np.nan, x)
        y = np.where(np.isinf(y), np.nan, y)
        return x, y

    def _meters_to_pixels_enhanced(self, x_m, y_m):
        """Convert EASE-Grid 2.0 coordinates to enhanced pixel indices"""
        px_x = ((x_m - self.MAP_ORIGIN_X) / self.ENHANCED_PIXEL_SIZE_M +
                self.GRID_ORIGIN_COL).astype(np.int32)
        px_y = ((self.MAP_ORIGIN_Y - y_m) / self.ENHANCED_PIXEL_SIZE_M +
                self.GRID_ORIGIN_ROW).astype(np.int32)
        return px_x, px_y

    def _get_grid_bounds(self):
        """Get grid bounds in meters"""
        x_min = self.MAP_ORIGIN_X
        x_max = self.MAP_ORIGIN_X + self.ENHANCED_GRID_WIDTH * self.ENHANCED_PIXEL_SIZE_M
        y_min = self.MAP_ORIGIN_Y - self.ENHANCED_GRID_HEIGHT * self.ENHANCED_PIXEL_SIZE_M
        y_max = self.MAP_ORIGIN_Y
        return x_min, x_max, y_min, y_max

    def _finalize_grid(self, grid, weight):
        """Finalize grid by averaging accumulated values"""
        final_grid = np.full(grid.shape, np.nan, dtype=np.float32)
        valid_mask = weight > 0

        if np.any(valid_mask):
            final_grid[valid_mask] = (grid[valid_mask] / weight[valid_mask]).astype(np.float32)

        return final_grid

    def _fill_holes_enhanced(self, data):
        """Fill holes in enhanced resolution data"""
        filled_data = data.copy()
        rows, cols = data.shape

        empty_mask = np.isnan(data)
        if not np.any(empty_mask):
            return filled_data

        # Scale parameters for enhanced resolution
        MIN_RADIUS = 2 * self.scale_factor
        MAX_RADIUS = 6 * self.scale_factor
        DISTANCE_SCALE = 400 * self.scale_factor

        # Calculate distance from center
        center_y, center_x = rows // 2, cols // 2
        y_indices, x_indices = np.meshgrid(range(rows), range(cols), indexing='ij')
        distance_from_center = np.sqrt((x_indices - center_x) ** 2 + (y_indices - center_y) ** 2)

        filled_count = 0

        # Process in batches for memory efficiency
        batch_size = 100
        empty_indices = np.where(empty_mask)
        num_empty = len(empty_indices[0])

        for batch_start in range(0, num_empty, batch_size):
            batch_end = min(batch_start + batch_size, num_empty)

            for idx in range(batch_start, batch_end):
                y = empty_indices[0][idx]
                x = empty_indices[1][idx]

                dist_from_center = distance_from_center[y, x]

                # Adaptive radius
                radius_factor = min(dist_from_center / DISTANCE_SCALE, 1.0)
                search_radius = int(MIN_RADIUS + radius_factor * (MAX_RADIUS - MIN_RADIUS))

                # Define neighborhood
                y_min = max(0, y - search_radius)
                y_max = min(rows, y + search_radius + 1)
                x_min = max(0, x - search_radius)
                x_max = min(cols, x + search_radius + 1)

                neighborhood = data[y_min:y_max, x_min:x_max]
                valid_mask = ~np.isnan(neighborhood)
                valid_count = np.sum(valid_mask)

                if valid_count >= 3:
                    # Get valid coordinates
                    valid_y, valid_x = np.where(valid_mask)
                    valid_y += y_min
                    valid_x += x_min

                    # Calculate weights based on distance
                    distances = np.sqrt((valid_y - y) ** 2 + (valid_x - x) ** 2)
                    weights = 1.0 / ((distances + 0.1) ** 2)
                    weights /= weights.sum()

                    # Weighted average
                    valid_values = data[valid_y, valid_x]
                    filled_value = np.sum(valid_values * weights)
                    filled_data[y, x] = filled_value
                    filled_count += 1

        logger.info(f"Filled {filled_count} holes in enhanced data")
        return filled_data