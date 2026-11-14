"""Geospatial calculations and coordinate transformations for Mars.

Supports conversions between planetary degrees (lon/lat), equirectangular
projected coordinates (meters), and raster pixel indices (row/col).
"""

from __future__ import annotations

import math
from typing import Tuple, Union
import numpy as np
import rasterio
from rasterio.warp import transform

from backend.config import MARS_RADIUS_M


def great_circle_distance_mars(
    lon1_deg: float, lat1_deg: float, lon2_deg: float, lat2_deg: float
) -> float:
    """Calculate the great-circle ground distance between two points on Mars in meters.

    Uses the Haversine formula with the Mars mean radius configured for this
    project (R = 3,389,500 meters). Raster reprojection still honors its source CRS.
    """
    phi1 = math.radians(lat1_deg)
    phi2 = math.radians(lat2_deg)
    dphi = math.radians(lat2_deg - lat1_deg)
    dlambda = math.radians(lon2_deg - lon1_deg)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return MARS_RADIUS_M * c


def coords_to_pixel(
    lon_deg: float,
    lat_deg: float,
    src: rasterio.DatasetReader,
) -> Tuple[int, int]:
    """Convert planetary longitude and latitude (degrees) to raster (row, col) pixel indices.

    Transforms geographic coordinates through the raster CRS into projected space,
    then inverts the affine transform to obtain raster indices.
    """
    geographic_crs = src.crs.geodetic_crs
    if geographic_crs is None:
        raise ValueError("Raster has no geographic geodetic CRS.")

    # Transform lon/lat into projected easting/northing
    eastings, northings = transform(geographic_crs, src.crs, [lon_deg], [lat_deg])
    easting = eastings[0]
    northing = northings[0]

    # Invert affine transform to get row and column
    row, col = src.index(easting, northing)
    return int(row), int(col)


def pixel_to_coords(
    row: int,
    col: int,
    src: rasterio.DatasetReader,
) -> Tuple[float, float]:
    """Convert raster (row, col) pixel indices to planetary longitude and latitude (degrees)."""
    geographic_crs = src.crs.geodetic_crs
    if geographic_crs is None:
        raise ValueError("Raster has no geographic geodetic CRS.")

    # Center of the pixel
    easting, northing = src.xy(row, col)
    longitudes, latitudes = transform(src.crs, geographic_crs, [easting], [northing])
    return float(longitudes[0]), float(latitudes[0])


def is_within_raster(row: int, col: int, height: int, width: int) -> bool:
    """Check if row and col are within raster grid dimensions."""
    return 0 <= row < height and 0 <= col < width


def euclidean_ground_distance(
    row1: int,
    col1: int,
    row2: int,
    col2: int,
    dx_per_row: np.ndarray,
    dy: float,
) -> float:
    """Calculate physical ground distance between two pixel cells in meters.

    Accounts for latitude-dependent east-west spacing (dx) and meridian spacing (dy).
    """
    d_row = abs(row2 - row1)
    d_col = abs(col2 - col1)

    mean_row = int(round((row1 + row2) / 2.0))
    # Clip row to valid dx array index
    safe_row = max(0, min(mean_row, len(dx_per_row) - 1))
    dx = float(dx_per_row[safe_row])

    dist_x = d_col * dx
    dist_y = d_row * dy
    return math.hypot(dist_x, dist_y)
