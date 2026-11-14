"""Terrain hazard assessment module for Jezero Crater, Mars.

Combines MOLA elevation gradients (Horn 3x3 slope) with detrended local
terrain residuals to compute:
1. Categorical hazard classifications: Safe (0), Moderate (1), High (2), Restricted/NoData (255)
2. Continuous hazard scores (0.0 to 1.0) for cost-weighted pathfinding.

Thresholds are project-defined engineering guidelines for surface traverse models,
not official NASA astronaut safety limits.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct execution
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from typing import Any, Dict, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import numpy as np
import rasterio
from rasterio.warp import transform

from backend.config import (
    ELEVATION_RASTER_PATH,
    SLOPE_RASTER_PATH,
    HAZARD_CLASSES_RASTER_PATH,
    HAZARD_SCORE_RASTER_PATH,
    HAZARD_MAP_PATH,
    HAZARD_CLASSES,
    HAZARD_NODATA_VALUE,
    HAZARD_SCORE_NODATA_VALUE,
    SLOPE_GENTLE_MAX,
    SLOPE_MODERATE_MAX,
    SLOPE_NODATA_VALUE,
)


def compute_terrain_roughness(elevation: np.ndarray, nodata: float | None) -> np.ndarray:
    """Return RMS residual after detrending each 3x3 elevation window by a plane.

    Unlike raw local elevation standard deviation, planar slopes are removed
    before measuring residual roughness. At the included 463 m/pixel MOLA
    resolution this remains a regional-scale proxy, not rover-scale roughness.
    """
    height, width = elevation.shape
    roughness = np.zeros((height, width), dtype=np.float32)

    z = elevation.astype(np.float64, copy=False)
    valid = np.ones(z.shape, dtype=bool) if nodata is None else (z != nodata)

    # Fast 3x3 neighborhood standard deviation using vector slicing
    # Interior 3x3 valid mask
    interior_valid = (
        valid[:-2, :-2] & valid[:-2, 1:-1] & valid[:-2, 2:] &
        valid[1:-1, :-2] & valid[1:-1, 1:-1] & valid[1:-1, 2:] &
        valid[2:, :-2] & valid[2:, 1:-1] & valid[2:, 2:]
    )

    stack = np.stack([
        z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:],
        z[1:-1, :-2], z[1:-1, 1:-1], z[1:-1, 2:],
        z[2:, :-2], z[2:, 1:-1], z[2:, 2:],
    ], axis=0)

    # Coordinates are symmetric, so the least-squares plane intercept is the
    # 3x3 mean. The row/column plane terms are orthogonal to the intercept.
    mean = np.mean(stack, axis=0)
    x = np.array([-1, 0, 1] * 3, dtype=np.float64)[:, None, None]
    y = np.repeat([-1, 0, 1], 3).astype(np.float64)[:, None, None]
    centered = stack - mean
    slope_x = np.sum(centered * x, axis=0) / 6.0
    slope_y = np.sum(centered * y, axis=0) / 6.0
    residual = centered - slope_x[None, ...] * x - slope_y[None, ...] * y
    rms_residual = np.sqrt(np.mean(residual ** 2, axis=0))
    roughness[1:-1, 1:-1] = np.where(interior_valid, rms_residual, 0.0)
    return roughness


def classify_terrain_hazards(
    slope: np.ndarray,
    roughness: np.ndarray,
    elevation: np.ndarray,
    elev_nodata: float | None,
    slope_gentle_max: float = SLOPE_GENTLE_MAX,
    slope_moderate_max: float = SLOPE_MODERATE_MAX,
    roughness_high_threshold: float = 35.0,  # meters local elevation variation
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate categorical hazard classes and continuous hazard scores.

    Classes:
    - 0: Safe / Low Hazard (slope <= 5.0°)
    - 1: Moderate Hazard (5.0° < slope <= 15.0°)
    - 2: Severe / High Hazard (slope > 15.0°)
    - 255: Restricted / NoData (Uncalculated edge or missing data)

    Scores:
    - 0.0 (safest) to 1.0 (most hazardous), or -9999.0 for NoData.
    """
    height, width = slope.shape

    # Identify invalid/NoData pixels
    invalid_mask = (
        ~np.isfinite(slope)
        | (slope == SLOPE_NODATA_VALUE)
        | (slope < 0)
    )
    if elev_nodata is not None:
        invalid_mask |= (elevation == elev_nodata)

    valid_mask = ~invalid_mask

    # Initialize outputs
    hazard_classes = np.full((height, width), HAZARD_NODATA_VALUE, dtype=np.uint8)
    hazard_score = np.full((height, width), HAZARD_SCORE_NODATA_VALUE, dtype=np.float32)

    # Class 0: Safe
    safe_mask = valid_mask & (slope <= slope_gentle_max)
    hazard_classes[safe_mask] = 0

    # Class 1: Moderate
    moderate_mask = (
        valid_mask
        & (slope > slope_gentle_max) & (slope <= slope_moderate_max)
    )
    hazard_classes[moderate_mask] = 1

    # Class 2: High / Severe
    high_mask = valid_mask & (slope > slope_moderate_max)
    hazard_classes[high_mask] = 2

    # Continuous score calculation on valid pixels:
    # 70% weighted by slope (normalized to 25° max traverse limit) + 30% weighted by roughness (normalized to 50m)
    norm_slope = np.clip(np.where(valid_mask, slope, 0.0) / 25.0, 0.0, 1.0)
    norm_roughness = np.clip(np.where(valid_mask, roughness, 0.0) / 50.0, 0.0, 1.0)
    score_valid = (0.70 * norm_slope) + (0.30 * norm_roughness)
    hazard_score[valid_mask] = score_valid[valid_mask].astype(np.float32)

    return hazard_classes, hazard_score


def write_hazard_rasters(
    hazard_classes: np.ndarray,
    hazard_score: np.ndarray,
    profile: dict,
    classes_dest: Path = HAZARD_CLASSES_RASTER_PATH,
    score_dest: Path = HAZARD_SCORE_RASTER_PATH,
) -> None:
    """Save georeferenced GeoTIFFs for hazard classes and hazard scores."""
    # Write categorical hazard classes (uint8)
    class_profile = profile.copy()
    class_profile.update(
        driver="GTiff",
        dtype="uint8",
        nodata=HAZARD_NODATA_VALUE,
        count=1,
        compress="lzw",
    )
    classes_dest.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(classes_dest, "w", **class_profile) as dst:
        dst.write(hazard_classes, 1)
        dst.set_band_description(1, "Jezero Crater Terrain Hazard Classification (0=Safe, 1=Moderate, 2=High, 255=NoData)")
        dst.update_tags(
            classes="0: Safe, 1: Moderate, 2: High, 255: NoData",
            note="Project-defined model bins for Mars surface navigation. Not official NASA astronaut safety standard.",
        )

    # Write continuous hazard score (float32)
    score_profile = profile.copy()
    score_profile.update(
        driver="GTiff",
        dtype="float32",
        nodata=HAZARD_SCORE_NODATA_VALUE,
        count=1,
        compress="lzw",
    )
    score_dest.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(score_dest, "w", **score_profile) as dst:
        dst.write(hazard_score, 1)
        dst.set_band_description(1, "Jezero Crater Continuous Terrain Hazard Score (0.0 to 1.0)")
        dst.update_tags(
            range="0.0 (minimal risk) to 1.0 (extreme risk), -9999 for NoData",
            units="normalized score",
        )


def write_hazard_map(
    hazard_classes: np.ndarray,
    extent_deg: Tuple[float, float, float, float],
    aspect: float,
    stats: Dict[str, Any],
    destination: Path = HAZARD_MAP_PATH,
) -> None:
    """Render publication-grade terrain hazard classification map."""
    west, south, east, north = extent_deg

    # Color mapping for classes: 0 -> Green, 1 -> Orange, 2 -> Red, 255 -> Gray
    cmap = ListedColormap([
        HAZARD_CLASSES[0]["color"],
        HAZARD_CLASSES[1]["color"],
        HAZARD_CLASSES[2]["color"],
        HAZARD_CLASSES[255]["color"],
    ])

    # Re-map 255 to 3 for plotting with 4-entry colormap
    plot_data = np.zeros_like(hazard_classes, dtype=np.uint8)
    plot_data[hazard_classes == 0] = 0
    plot_data[hazard_classes == 1] = 1
    plot_data[hazard_classes == 2] = 2
    plot_data[hazard_classes == HAZARD_NODATA_VALUE] = 3

    fig, ax = plt.subplots(figsize=(9, 8), dpi=150)
    im = ax.imshow(
        plot_data,
        cmap=cmap,
        vmin=0,
        vmax=3,
        extent=(west, east, south, north),
        origin="upper",
        interpolation="nearest",
    )
    ax.set_aspect(aspect)
    ax.set_xlabel("Longitude (°E)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Latitude (°N)", fontsize=11, fontweight="bold")
    ax.set_title("MARS-NAV: Jezero Crater Terrain Hazard Assessment", fontsize=13, fontweight="bold", pad=12)

    # Prominent Landmark Annotations
    ax.plot(77.4508, 18.4447, marker="*", color="cyan", markersize=12, markeredgecolor="black", label="Perseverance Site")
    ax.plot(77.6953, 18.4063, marker="+", color="white", markersize=9, markeredgewidth=1.5, label="Crater Center")

    # Legend
    legend_elements = [
        Patch(facecolor=HAZARD_CLASSES[0]["color"], edgecolor="black", label=f"Safe / Low ({stats['safe_pct']:.1f}%) — Slope ≤ 5°"),
        Patch(facecolor=HAZARD_CLASSES[1]["color"], edgecolor="black", label=f"Moderate ({stats['moderate_pct']:.1f}%) — Slope 5–15°"),
        Patch(facecolor=HAZARD_CLASSES[2]["color"], edgecolor="black", label=f"High / Severe ({stats['high_pct']:.1f}%) — Slope > 15°"),
        Patch(facecolor=HAZARD_CLASSES[255]["color"], edgecolor="black", label=f"Restricted / NoData ({stats['nodata_pct']:.1f}%)"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", framealpha=0.9, fontsize=9)

    # Scientific disclaimer note
    ax.text(
        0.02,
        0.02,
        "NASA MOLA MEGDR derived product (~463 m/pixel); rover-scale hazards are unresolved.\n"
        "Thresholds are project-defined model parameters, not official NASA safety limits.\n"
        "NoData & outer boundary pixels are strictly non-traversable.",
        transform=ax.transAxes,
        fontsize=8,
        color="#111111",
        bbox={"facecolor": "white", "alpha": 0.88, "edgecolor": "#cccccc", "pad": 4},
    )

    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=200)
    plt.close(fig)


def run_hazard_assessment() -> Dict[str, Any]:
    """Execute full terrain hazard assessment pipeline."""
    if not ELEVATION_RASTER_PATH.is_file():
        raise FileNotFoundError(f"Elevation raster missing: {ELEVATION_RASTER_PATH}")
    if not SLOPE_RASTER_PATH.is_file():
        raise FileNotFoundError(f"Slope raster missing: {SLOPE_RASTER_PATH}")

    with rasterio.open(ELEVATION_RASTER_PATH) as elev_src:
        elevation = elev_src.read(1)
        elev_nodata = elev_src.nodata
        profile = elev_src.profile.copy()
        crs = elev_src.crs
        transform_aff = elev_src.transform
        width, height = elev_src.width, elev_src.height

        # Calculate geographic extent
        geo_crs = crs.geodetic_crs
        left, top = transform_aff.c, transform_aff.f
        right = left + transform_aff.a * width
        bottom = top + transform_aff.e * height
        lons, lats = transform(crs, geo_crs, [left, right], [bottom, top])
        extent_deg = (min(lons), min(lats), max(lons), max(lats))
        mean_lat = (extent_deg[1] + extent_deg[3]) / 2.0
        aspect = 1.0 / math.cos(math.radians(mean_lat))

    with rasterio.open(SLOPE_RASTER_PATH) as slope_src:
        slope = slope_src.read(1)

    # Compute roughness
    roughness = compute_terrain_roughness(elevation, elev_nodata)

    # Classify hazards
    hazard_classes, hazard_score = classify_terrain_hazards(
        slope, roughness, elevation, elev_nodata
    )

    # Write rasters
    write_hazard_rasters(hazard_classes, hazard_score, profile)

    # Calculate statistics
    total_pixels = hazard_classes.size
    safe_count = int(np.sum(hazard_classes == 0))
    moderate_count = int(np.sum(hazard_classes == 1))
    high_count = int(np.sum(hazard_classes == 2))
    nodata_count = int(np.sum(hazard_classes == HAZARD_NODATA_VALUE))
    valid_count = total_pixels - nodata_count

    stats = {
        "total_pixels": total_pixels,
        "valid_pixels": valid_count,
        "safe_count": safe_count,
        "moderate_count": moderate_count,
        "high_count": high_count,
        "nodata_count": nodata_count,
        "safe_pct": round(100.0 * safe_count / total_pixels, 2),
        "moderate_pct": round(100.0 * moderate_count / total_pixels, 2),
        "high_pct": round(100.0 * high_count / total_pixels, 2),
        "nodata_pct": round(100.0 * nodata_count / total_pixels, 2),
        "valid_safe_pct": round(100.0 * safe_count / valid_count, 2) if valid_count else 0,
        "valid_moderate_pct": round(100.0 * moderate_count / valid_count, 2) if valid_count else 0,
        "valid_high_pct": round(100.0 * high_count / valid_count, 2) if valid_count else 0,
        "extent_deg": extent_deg,
    }

    # Generate hazard map
    write_hazard_map(hazard_classes, extent_deg, aspect, stats, HAZARD_MAP_PATH)

    return stats


if __name__ == "__main__":
    print("Executing Mars Hazard Assessment...")
    results = run_hazard_assessment()
    print("Hazard Assessment complete! Statistics:")
    for k, v in results.items():
        print(f"  {k}: {v}")
