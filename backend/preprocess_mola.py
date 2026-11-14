"""Crop the MOLA MEGDR tile to a window around Jezero Crater.

The source raster is opened read-only. Jezero is located by transforming
planetocentric latitude and longitude through the dataset CRS, and only
that window is read into memory.
"""

from __future__ import annotations

import math
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds
from rasterio.warp import transform

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SOURCE_PATH = REPO_ROOT / "data" / "raw" / "MOLA" / "megt44n000hb.img"
ELEVATION_PATH = REPO_ROOT / "data" / "processed" / "jezero_mola_elevation.tif"
MAP_PATH = REPO_ROOT / "data" / "processed" / "jezero_elevation_map.png"
from backend.config import (
    MOLA_SOURCE_COVERAGE,
    REGIONAL_BOUNDS,
    REGIONAL_OVERVIEW_MAX_WIDTH,
    REGIONAL_OVERVIEW_PATH,
    REGIONAL_PREVIEW_WEBP_PATH,
)

# Jezero is about 45 km across. One degree of latitude on this sphere is
# about 59 km, so a one-degree margin keeps the rim and nearby plains.
JEZERO_LATITUDE_DEG = 18.4
JEZERO_LONGITUDE_DEG = 77.7
HALF_WINDOW_DEG = 1.0


def geographic_window(src: rasterio.DatasetReader) -> tuple[Window, dict]:
    """Map the Jezero latitude/longitude box into a source pixel window."""
    geographic_crs = src.crs.geodetic_crs
    if geographic_crs is None:
        raise RuntimeError("The MOLA raster has no geographic CRS to transform from.")

    west = JEZERO_LONGITUDE_DEG - HALF_WINDOW_DEG
    east = JEZERO_LONGITUDE_DEG + HALF_WINDOW_DEG
    south = JEZERO_LATITUDE_DEG - HALF_WINDOW_DEG
    north = JEZERO_LATITUDE_DEG + HALF_WINDOW_DEG

    longitudes = [west, east, west, east, JEZERO_LONGITUDE_DEG]
    latitudes = [south, south, north, north, JEZERO_LATITUDE_DEG]
    eastings, northings = transform(geographic_crs, src.crs, longitudes, latitudes)

    center_x = eastings[-1]
    center_y = northings[-1]
    if not (
        src.bounds.left <= center_x <= src.bounds.right
        and src.bounds.bottom <= center_y <= src.bounds.top
    ):
        raise RuntimeError(
            "Jezero projects outside the MOLA tile. "
            f"Projected centre is ({center_x:.1f} m, {center_y:.1f} m); "
            f"tile bounds are {src.bounds}."
        )

    pixel_window = from_bounds(
        min(eastings[:-1]),
        min(northings[:-1]),
        max(eastings[:-1]),
        max(northings[:-1]),
        transform=src.transform,
    )
    # Expand to whole pixels so the requested box is fully covered.
    pixel_window = pixel_window.round_offsets(op="floor").round_lengths(op="ceil")
    pixel_window = pixel_window.intersection(Window(0, 0, src.width, src.height))
    if pixel_window.width <= 0 or pixel_window.height <= 0:
        raise RuntimeError("The Jezero window does not intersect the MOLA tile.")

    info = {
        "geographic_crs": geographic_crs,
        "requested_bounds_deg": (west, south, east, north),
        "center_projected_m": (center_x, center_y),
        "center_rowcol": src.index(center_x, center_y),
    }
    return pixel_window, info


def window_geographic_bounds(src, window: Window, geographic_crs) -> tuple[float, float, float, float]:
    """Return west, south, east, north degrees for the outer edges of a window."""
    window_transform = src.window_transform(window)
    left = window_transform.c
    top = window_transform.f
    right = left + window_transform.a * window.width
    bottom = top + window_transform.e * window.height
    longitudes, latitudes = transform(
        src.crs,
        geographic_crs,
        [left, right],
        [bottom, top],
    )
    return (
        min(longitudes),
        min(latitudes),
        max(longitudes),
        max(latitudes),
    )


def elevation_statistics(elevation: np.ndarray, nodata) -> dict:
    """Summarise valid elevations. Nodata pixels are excluded."""
    values = elevation.astype(np.float64)
    if nodata is None:
        valid = values
    else:
        valid = values[values != nodata]
    missing = int(values.size - valid.size)
    if valid.size == 0:
        return {
            "minimum_m": None,
            "maximum_m": None,
            "mean_m": None,
            "std_m": None,
            "valid_pixels": 0,
            "missing_pixels": missing,
        }
    return {
        "minimum_m": float(valid.min()),
        "maximum_m": float(valid.max()),
        "mean_m": float(valid.mean()),
        "std_m": float(valid.std()),
        "valid_pixels": int(valid.size),
        "missing_pixels": missing,
    }


def write_elevation(src, window: Window, elevation: np.ndarray, destination: Path) -> None:
    profile = src.profile.copy()
    profile.update(
        driver="GTiff",
        height=int(window.height),
        width=int(window.width),
        transform=src.window_transform(window),
        compress="lzw",
        tiled=False,
        blockxsize=int(window.width),
        blockysize=1,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(destination, "w", **profile) as dst:
        dst.write(elevation, 1)


def geographic_bounds_to_window(src: rasterio.DatasetReader, bounds: dict[str, float]) -> tuple[Window, tuple[float, float, float, float]]:
    """Convert a geographic bounding box to a clipped source window.

    This uses the source CRS and does not assume a particular raw image layout.
    """
    geographic_crs = src.crs.geodetic_crs
    if geographic_crs is None:
        raise RuntimeError("The MOLA raster has no geographic CRS to transform from.")
    west, east, south, north = bounds["west"], bounds["east"], bounds["south"], bounds["north"]
    x, y = transform(geographic_crs, src.crs, [west, east, west, east], [south, south, north, north])
    window = from_bounds(min(x), min(y), max(x), max(y), transform=src.transform)
    window = window.round_offsets(op="floor").round_lengths(op="ceil").intersection(Window(0, 0, src.width, src.height))
    if window.width <= 0 or window.height <= 0:
        raise RuntimeError("Requested regional bounds do not overlap the local MOLA source.")
    return window, window_geographic_bounds(src, window, geographic_crs)


def verify_regional_coverage(src: rasterio.DatasetReader, bounds: dict[str, float] = REGIONAL_BOUNDS) -> None:
    """Fail clearly if the single local source cannot satisfy the overview region."""
    geographic_crs = src.crs.geodetic_crs
    x, y = transform(
        src.crs,
        geographic_crs,
        [src.bounds.left, src.bounds.right],
        [src.bounds.bottom, src.bounds.top],
    )
    source = {"west": min(x), "east": max(x), "south": min(y), "north": max(y)}
    tolerance = 1e-5  # transformation roundoff at the exact 90°E source edge
    if not (
        source["west"] - tolerance <= bounds["west"]
        and source["east"] + tolerance >= bounds["east"]
        and source["south"] - tolerance <= bounds["south"]
        and source["north"] + tolerance >= bounds["north"]
    ):
        raise RuntimeError(f"Regional request {bounds} is outside local MOLA coverage {source}.")


def build_regional_overview() -> dict:
    """Create the lightweight tiled regional dataset from the existing local MOLA tile.

    No raw Mars data is downloaded or duplicated.  The generated overview uses
    average resampling for display only and must never be used by navigation.
    """
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(f"MOLA source raster not found: {SOURCE_PATH}")
    with rasterio.open(SOURCE_PATH) as src:
        verify_regional_coverage(src)
        window, geographic_bounds = geographic_bounds_to_window(src, REGIONAL_BOUNDS)
        width = min(REGIONAL_OVERVIEW_MAX_WIDTH, int(window.width))
        height = max(2, round(width * window.height / window.width))
        data = src.read(
            1,
            window=window,
            out_shape=(1, height, width),
            out_dtype="float32",
            resampling=Resampling.average,
        )
        profile = src.profile.copy()
        window_transform = src.window_transform(window)
        transform_out = window_transform * window_transform.scale(window.width / width, window.height / height)
        profile.update(
            driver="GTiff", dtype="float32", count=1, width=width, height=height,
            transform=transform_out, nodata=src.nodata, compress="deflate", predictor=3,
            tiled=True, blockxsize=min(256, width), blockysize=min(256, height),
            BIGTIFF="IF_SAFER",
        )
        REGIONAL_OVERVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(REGIONAL_OVERVIEW_PATH, "w", **profile) as dst:
            dst.write(data, 1)
            dst.set_band_description(1, "MOLA MEGDR regional elevation overview (display only)")
            dst.update_tags(
                product_level="regional overview",
                geographic_bounds=str(REGIONAL_BOUNDS),
                source_coverage=str(MOLA_SOURCE_COVERAGE),
                navigation_note="Not used for Jezero hazards, A* pathfinding, or 3D analysis.",
            )
            dst.build_overviews([2, 4, 8], Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")

    valid = data[data != src.nodata] if src.nodata is not None else data
    if valid.size:
        # A compact visualization only; the GeoTIFF retains measured elevations.
        lo, hi = np.percentile(valid, [2, 98])
        preview = np.ma.masked_equal(data, src.nodata) if src.nodata is not None else data
        plt.imsave(REGIONAL_PREVIEW_WEBP_PATH, preview, cmap="terrain", vmin=lo, vmax=hi, format="webp")
    return {
        "path": str(REGIONAL_OVERVIEW_PATH), "preview": str(REGIONAL_PREVIEW_WEBP_PATH),
        "width": width, "height": height, "bounds": geographic_bounds,
        "source_coverage": MOLA_SOURCE_COVERAGE,
    }


def write_map(
    elevation: np.ndarray,
    nodata,
    bounds_deg: tuple[float, float, float, float],
    stats: dict,
    destination: Path,
) -> None:
    west, south, east, north = bounds_deg
    display = np.ma.masked_equal(elevation, nodata) if nodata is not None else elevation

    fig, ax = plt.subplots(figsize=(8.2, 7.2))
    image = ax.imshow(
        display,
        cmap="terrain",
        extent=(west, east, south, north),
        origin="upper",
        interpolation="nearest",
    )
    # One degree of longitude is shorter than one degree of latitude.
    ax.set_aspect(1.0 / math.cos(math.radians(JEZERO_LATITUDE_DEG)))
    ax.plot(
        JEZERO_LONGITUDE_DEG,
        JEZERO_LATITUDE_DEG,
        marker="+",
        color="black",
        markersize=10,
        markeredgewidth=1.2,
        label="Jezero centre",
    )
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title("Jezero Crater — MOLA elevation")
    ax.legend(loc="upper right", frameon=True)
    colorbar = fig.colorbar(image, ax=ax, shrink=0.86, pad=0.02)
    colorbar.set_label("Elevation (m relative to the areoid)")
    if stats["minimum_m"] is not None:
        ax.text(
            0.02,
            0.02,
            f"{stats['minimum_m']:.0f} m to {stats['maximum_m']:.0f} m",
            transform=ax.transAxes,
            fontsize=9,
            color="black",
            bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none", "pad": 3},
        )
    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=150)
    plt.close(fig)


def main() -> None:
    print("MARS NAV - JEZERO MOLA PREPROCESSING")
    print("-" * 40)

    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(f"MOLA source raster not found: {SOURCE_PATH}")

    with rasterio.open(SOURCE_PATH) as src:
        print("Source:", SOURCE_PATH)
        print("Size:", src.width, "x", src.height, "pixels")
        print("Data type:", src.dtypes[0])
        print("NoData:", src.nodata)
        print("Pixel size (m):", src.res)
        print("CRS:", src.crs)
        print("Bounds (m):", src.bounds)

        window, info = geographic_window(src)
        west, south, east, north = info["requested_bounds_deg"]
        center_row, center_col = info["center_rowcol"]
        center_x, center_y = info["center_projected_m"]
        print("Jezero (deg):", JEZERO_LATITUDE_DEG, "N,", JEZERO_LONGITUDE_DEG, "E")
        print("Jezero projected (m):", f"{center_x:.1f}, {center_y:.1f}")
        print("Jezero pixel (row, col):", center_row, center_col)
        print(
            "Requested window (deg):",
            f"{south:.4f}–{north:.4f} N,",
            f"{west:.4f}–{east:.4f} E",
        )
        print(
            "Pixel window:",
            f"row {int(window.row_off)}, col {int(window.col_off)},",
            f"{int(window.height)} rows x {int(window.width)} cols",
        )

        elevation = src.read(1, window=window)
        nodata = src.nodata
        crop_bounds = window_geographic_bounds(src, window, info["geographic_crs"])
        stats = elevation_statistics(elevation, nodata)
        write_elevation(src, window, elevation, ELEVATION_PATH)

    write_map(elevation, nodata, crop_bounds, stats, MAP_PATH)

    print("Crop bounds (deg):",
          f"{crop_bounds[1]:.6f}–{crop_bounds[3]:.6f} N,",
          f"{crop_bounds[0]:.6f}–{crop_bounds[2]:.6f} E")
    print("Minimum elevation (m):", stats["minimum_m"])
    print("Maximum elevation (m):", stats["maximum_m"])
    print("Mean elevation (m):", None if stats["mean_m"] is None else round(stats["mean_m"], 2))
    print("Std. deviation (m):", None if stats["std_m"] is None else round(stats["std_m"], 2))
    print("Valid pixels:", stats["valid_pixels"])
    print("NoData pixels:", stats["missing_pixels"])
    print("Elevation raster:", ELEVATION_PATH)
    print("Elevation map:", MAP_PATH)
    print("\nPreprocessing completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create MOLA products without downloading duplicate raw data.")
    parser.add_argument("--regional", action="store_true", help="Build only the tiled regional display overview.")
    args = parser.parse_args()
    if args.regional:
        print(build_regional_overview())
    else:
        main()
