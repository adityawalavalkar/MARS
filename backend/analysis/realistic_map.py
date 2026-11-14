"""Realistic Mars terrain map generator for Jezero Crater.

Creates scientific, cartographically authentic visualizations of Mars surface terrain
using NASA MOLA elevation, hillshading (shaded relief), and naturalistic Martian
regolith color palettes. Also generates transparent hazard overlays for web frontend
integration.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct execution
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from typing import Dict, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.patches import Patch, Rectangle
import numpy as np
import rasterio
from rasterio.warp import transform

from backend.config import (
    ELEVATION_RASTER_PATH,
    SLOPE_RASTER_PATH,
    HAZARD_CLASSES_RASTER_PATH,
    MARS_TERRAIN_MAP_PATH,
    MOLA_TEXTURE_PATH,
    HAZARD_OVERLAY_PATH,
    HAZARD_CLASSES,
    HAZARD_NODATA_VALUE,
    MARS_RADIUS_M,
    OCTAVIA_E_BUTLER_LANDING_LAT,
    OCTAVIA_E_BUTLER_LANDING_LON,
    SEITAH_LAT,
    SEITAH_LON,
    NERETVA_VALLIS_INLET_LAT,
    NERETVA_VALLIS_INLET_LON,
    CRATER_RIM_NORTH_LAT,
    CRATER_RIM_NORTH_LON,
)


def compute_hillshade(
    elevation: np.ndarray,
    dx: float,
    dy: float,
    azimuth_deg: float = 315.0,
    altitude_deg: float = 40.0,
    z_factor: float = 2.5,
) -> np.ndarray:
    """Calculate shaded relief (hillshade) from elevation array.

    Parameters:
    - azimuth_deg: Solar azimuth direction (315° = North-West illumination standard)
    - altitude_deg: Sun elevation angle above the Martian horizon (40°)
    - z_factor: Vertical exaggeration factor to highlight crater morphology
    """
    height, width = elevation.shape
    z = elevation.astype(np.float64)

    # Compute gradients along x and y using Sobel / central difference
    grad_y, grad_x = np.gradient(z * z_factor, dy, dx)

    # Slope and aspect angles in radians
    slope = np.pi / 2.0 - np.arctan(np.hypot(grad_x, grad_y))
    aspect = np.arctan2(-grad_x, grad_y)

    # Solar illumination angles in radians
    azimuth_rad = math.radians(360.0 - azimuth_deg + 90.0)
    altitude_rad = math.radians(altitude_deg)

    # Shaded relief formula
    shaded = (
        np.sin(altitude_rad) * np.sin(slope)
        + np.cos(altitude_rad) * np.cos(slope) * np.cos(azimuth_rad - aspect)
    )
    # Clip to valid 0.0 to 1.0 range
    return np.clip(shaded, 0.0, 1.0)


def create_mars_colormap() -> LinearSegmentedColormap:
    """Create authentic Martian regolith color palette based on MGS/MRO spectrometry.

    Colors transition from deep basaltic plains (#28140C) to iron-oxide rich dust (#B85324)
    and bright atmospheric dust-scoured crater rim highs (#ECC69C).
    """
    mars_colors = [
        (0.00, "#1f0e08"),  # Deepest depressions / basaltic shadows
        (0.15, "#3b1a10"),  # Dark basalt plains
        (0.35, "#682e18"),  # Moderate crater floor regolith
        (0.55, "#964522"),  # Iron-oxide oxidized regolith
        (0.72, "#bd5e2e"),  # Jezero delta deposits & apron
        (0.88, "#d9874d"),  # Crater rim scarps
        (1.00, "#f0caa0"),  # High rim ridges & plateau
    ]
    return LinearSegmentedColormap.from_list("MarsAuthentic", mars_colors, N=256)


def generate_mars_terrain_map() -> None:
    """Render scientific Mars terrain map with hillshading, landmarks, scale bar, and overlays."""
    if not ELEVATION_RASTER_PATH.is_file():
        raise FileNotFoundError(f"Elevation raster not found: {ELEVATION_RASTER_PATH}")
    if not HAZARD_CLASSES_RASTER_PATH.is_file():
        raise FileNotFoundError(f"Hazard classes raster not found: {HAZARD_CLASSES_RASTER_PATH}")

    with rasterio.open(ELEVATION_RASTER_PATH) as src:
        elevation = src.read(1)
        elev_nodata = src.nodata
        crs = src.crs
        transform_aff = src.transform
        width, height = src.width, src.height

        geo_crs = crs.geodetic_crs
        left, top = transform_aff.c, transform_aff.f
        right = left + transform_aff.a * width
        bottom = top + transform_aff.e * height
        lons, lats = transform(crs, geo_crs, [left, right], [bottom, top])
        west, south, east, north = min(lons), min(lats), max(lons), max(lats)
        mean_lat = (south + north) / 2.0
        aspect = 1.0 / math.cos(math.radians(mean_lat))

        # Ground pixel spacing
        dx = abs(transform_aff.a) * math.cos(math.radians(mean_lat))
        dy = abs(transform_aff.e)

    with rasterio.open(HAZARD_CLASSES_RASTER_PATH) as haz_src:
        hazards = haz_src.read(1)

    # Compute hillshade
    hillshade = compute_hillshade(elevation, dx, dy, azimuth_deg=315.0, altitude_deg=40.0, z_factor=2.5)

    # Mask elevation for color normalization
    valid_elev_mask = elevation != elev_nodata if elev_nodata is not None else np.ones_like(elevation, dtype=bool)
    min_elev = float(np.min(elevation[valid_elev_mask]))
    max_elev = float(np.max(elevation[valid_elev_mask]))

    norm_elevation = np.clip((elevation - min_elev) / (max_elev - min_elev), 0.0, 1.0)

    # Colorize elevation
    mars_cmap = create_mars_colormap()
    rgb_elevation = mars_cmap(norm_elevation)[:, :, :3]

    # Blend hillshade with elevation color (multiply + ambient lighting)
    # Ambient light 0.35, direct relief 0.65
    illumination = 0.35 + 0.65 * hillshade[:, :, np.newaxis]
    rgb_terrain = np.clip(rgb_elevation * illumination, 0.0, 1.0)

    # Subtle hazard tint overlay:
    # High hazard (>15° or rough) highlighted with red translucent tint
    high_hazard_mask = (hazards == 2)
    rgb_terrain[high_hazard_mask] = (
        0.65 * rgb_terrain[high_hazard_mask] + 0.35 * np.array([0.9, 0.15, 0.15])
    )
    # Moderate hazard highlighted with amber tint
    mod_hazard_mask = (hazards == 1)
    rgb_terrain[mod_hazard_mask] = (
        0.82 * rgb_terrain[mod_hazard_mask] + 0.18 * np.array([0.95, 0.55, 0.1])
    )

    # Boundary NoData shaded in muted dark gray
    nodata_mask = (hazards == HAZARD_NODATA_VALUE)
    rgb_terrain[nodata_mask] = np.array([0.22, 0.22, 0.24])

    # Plot figure
    fig, ax = plt.subplots(figsize=(10.5, 9.5), dpi=200, facecolor="#0e0e12")
    ax.set_facecolor("#0e0e12")

    im = ax.imshow(
        rgb_terrain,
        extent=(west, east, south, north),
        origin="upper",
        interpolation="bilinear",
    )
    ax.set_aspect(aspect)

    # Style axes
    ax.tick_params(colors="#d0d0d8", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color("#555566")
        spine.set_linewidth(1.2)

    ax.set_xlabel("Longitude (°E)", fontsize=11, fontweight="bold", color="#e8e8f0", labelpad=8)
    ax.set_ylabel("Latitude (°N)", fontsize=11, fontweight="bold", color="#e8e8f0", labelpad=8)
    ax.set_title(
        "MARS-NAV: Jezero Crater Topographic & Hazard Terrain Model",
        fontsize=14,
        fontweight="bold",
        color="#ffffff",
        pad=16,
    )

    # Add Gridlines
    ax.grid(color="#ffffff", alpha=0.15, linestyle="--", linewidth=0.7)

    # Scientific Landmark Annotations
    landmarks = [
        (OCTAVIA_E_BUTLER_LANDING_LON, OCTAVIA_E_BUTLER_LANDING_LAT, "Octavia E. Butler Landing\n(Perseverance / Ingenuity)", "#00ffff", "*", 13),
        (77.4200, 18.4550, "Western Delta Fan", "#ffd700", "o", 8),
        (SEITAH_LON, SEITAH_LAT, "Séítah Formation", "#ffa500", "s", 7),
        (NERETVA_VALLIS_INLET_LON, NERETVA_VALLIS_INLET_LAT, "Neretva Vallis Inlet", "#87ceeb", "^", 8),
        (77.6953, 18.4063, "Jezero Crater Floor Center", "#ffffff", "+", 10),
        (CRATER_RIM_NORTH_LON, CRATER_RIM_NORTH_LAT, "Northern Crater Rim", "#ff6b6b", "D", 7),
    ]

    for lon, lat, label, color, marker, size in landmarks:
        ax.plot(lon, lat, marker=marker, color=color, markersize=size, markeredgecolor="black", markeredgewidth=1.2)
        ax.text(
            lon + 0.025,
            lat - 0.015,
            label,
            color=color,
            fontsize=8.5,
            fontweight="semibold",
            bbox={"facecolor": "#121218", "alpha": 0.75, "edgecolor": "#444455", "boxstyle": "round,pad=0.25"},
        )

    # Scale Bar (20 km)
    # 1 degree of latitude on Mars is ~59.27 km
    km_per_deg_lat = (2.0 * math.pi * MARS_RADIUS_M / 360.0) / 1000.0
    scale_bar_km = 20.0
    scale_bar_deg = scale_bar_km / (km_per_deg_lat * math.cos(math.radians(mean_lat)))

    scale_x = west + 0.08
    scale_y = south + 0.08
    ax.plot([scale_x, scale_x + scale_bar_deg], [scale_y, scale_y], color="#ffffff", linewidth=3.5, solid_capstyle="butt")
    ax.text(
        scale_x + scale_bar_deg / 2.0,
        scale_y + 0.025,
        f"{int(scale_bar_km)} km",
        color="#ffffff",
        fontsize=9,
        fontweight="bold",
        ha="center",
    )

    # North Arrow
    arrow_x = east - 0.10
    arrow_y = south + 0.12
    ax.annotate(
        "N",
        xy=(arrow_x, arrow_y + 0.06),
        xytext=(arrow_x, arrow_y),
        arrowprops=dict(facecolor="#ffffff", edgecolor="#111111", width=2.5, headwidth=8.0),
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#ffffff",
    )

    # Custom Legend
    legend_elements = [
        Patch(facecolor="#964522", edgecolor="#ffffff", label="Nominal Regolith (0–5° slope)"),
        Patch(facecolor="#e08520", edgecolor="#ffffff", label="Moderate Risk Area (5–15° slope)"),
        Patch(facecolor="#d62728", edgecolor="#ffffff", label="High Hazard Scarp (>15° slope)"),
        Patch(facecolor="#383838", edgecolor="#ffffff", label="Restricted / Boundary Void"),
    ]
    leg = ax.legend(
        handles=legend_elements,
        loc="upper right",
        framealpha=0.85,
        facecolor="#121218",
        edgecolor="#555566",
        fontsize=8.5,
        labelcolor="#ffffff",
    )

    # Metadata & Attribution banner
    ax.text(
        0.02,
        0.02,
        "NASA Planetary Data System (PDS) | MRO / MGS MOLA MEGDR Topography (~463 m/px)\n"
        f"Elevation Datum: Mars Areoid | Range: {min_elev:.0f} m to {max_elev:.0f} m\n"
        "Illumination: Sun Azimuth 315° NW, Altitude 40° | Vertical Exaggeration: 2.5x",
        transform=ax.transAxes,
        fontsize=8,
        color="#c8c8d8",
        bbox={"facecolor": "#0a0a0f", "alpha": 0.85, "edgecolor": "#444455", "pad": 4},
    )

    fig.tight_layout()
    MARS_TERRAIN_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(MARS_TERRAIN_MAP_PATH, dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)


def generate_mola_texture() -> None:
    """Render an imagery-free, real MOLA hillshade/color texture for the 3D mesh."""
    with rasterio.open(ELEVATION_RASTER_PATH) as src:
        elevation = src.read(1).astype(np.float32)
        nodata = src.nodata
        dx, dy = abs(src.transform.a), abs(src.transform.e)
    valid = np.isfinite(elevation) & ((elevation != nodata) if nodata is not None else True)
    lo, hi = float(np.min(elevation[valid])), float(np.max(elevation[valid]))
    normalized = np.clip((elevation - lo) / max(hi - lo, 1e-6), 0, 1)
    color = create_mars_colormap()(normalized)[..., :3]
    shade = compute_hillshade(elevation, dx, dy, azimuth_deg=315.0, altitude_deg=45.0, z_factor=1.0)
    rgb = np.clip(color * (0.35 + 0.65 * shade[..., None]), 0, 1)
    rgb[~valid] = np.array([0.10, 0.055, 0.035])
    from PIL import Image
    MOLA_TEXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((rgb * 255).astype(np.uint8), "RGB").save(MOLA_TEXTURE_PATH, quality=94, optimize=True)


def generate_transparent_hazard_overlay() -> None:
    """Generate separate transparent PNG hazard overlay for frontend web maps.

    Enables web dashboards (Leaflet, Mapbox, Deck.gl, Cesium) to toggle hazard layers
    over arbitrary optical base imagery (such as HiRISE or CTX).
    """
    if not HAZARD_CLASSES_RASTER_PATH.is_file():
        raise FileNotFoundError(f"Hazard raster not found: {HAZARD_CLASSES_RASTER_PATH}")

    with rasterio.open(HAZARD_CLASSES_RASTER_PATH) as src:
        hazards = src.read(1)
        height, width = hazards.shape

    # Create RGBA array
    rgba = np.zeros((height, width, 4), dtype=np.uint8)

    # Class 0: Safe (Subtle soft green, mostly transparent: alpha 35)
    safe_mask = (hazards == 0)
    rgba[safe_mask] = [44, 160, 44, 40]

    # Class 1: Moderate (Amber warning tint: alpha 120)
    mod_mask = (hazards == 1)
    rgba[mod_mask] = [255, 140, 0, 130]

    # Class 2: High Hazard (Vivid red warning: alpha 200)
    high_mask = (hazards == 2)
    rgba[high_mask] = [220, 20, 60, 210]

    # Class 255: NoData / Restricted (Dark charcoal hatch/tint: alpha 160)
    nodata_mask = (hazards == HAZARD_NODATA_VALUE)
    rgba[nodata_mask] = [80, 80, 80, 160]

    from PIL import Image
    img = Image.fromarray(rgba, mode="RGBA")
    HAZARD_OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(HAZARD_OVERLAY_PATH, format="PNG")


def run_realistic_map_pipeline() -> None:
    """Generate both the realistic Mars terrain map and the transparent hazard overlay."""
    print("Rendering MOLA texture for the 3D mesh...")
    generate_mola_texture()
    print(f"MOLA texture saved to: {MOLA_TEXTURE_PATH}")
    print("Generating authentic Mars terrain map...")
    generate_mars_terrain_map()
    print(f"Mars terrain map saved to: {MARS_TERRAIN_MAP_PATH}")

    print("Generating transparent hazard overlay...")
    generate_transparent_hazard_overlay()
    print(f"Transparent hazard overlay saved to: {HAZARD_OVERLAY_PATH}")


if __name__ == "__main__":
    run_realistic_map_pipeline()
