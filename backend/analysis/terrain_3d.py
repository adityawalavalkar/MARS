"""Interactive 3D terrain model generator for Jezero Crater, Mars.

Generates an interactive WebGL 3D elevation surface from NASA MOLA MEGDR data,
styled with authentic Martian regolith colors, realistic lighting, and topographic
landmarks. Produces a standalone HTML visualizer and an exportable JSON terrain
mesh for frontend 3D engines (Three.js, Cesium, Babylon.js).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct execution
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from typing import Any, Dict
import numpy as np
import plotly.graph_objects as go
import rasterio
from rasterio.warp import transform

from backend.config import (
    ELEVATION_RASTER_PATH,
    TERRAIN_3D_HTML_PATH,
    TERRAIN_MESH_JSON_PATH,
    OCTAVIA_E_BUTLER_LANDING_LAT,
    OCTAVIA_E_BUTLER_LANDING_LON,
    SEITAH_LAT,
    SEITAH_LON,
    NERETVA_VALLIS_INLET_LAT,
    NERETVA_VALLIS_INLET_LON,
)


def generate_3d_terrain_model(
    vertical_exaggeration: float = 3.5,
    downsample_factor: int = 1,
) -> Dict[str, Any]:
    """Generate interactive 3D WebGL HTML and frontend JSON mesh asset.

    Parameters:
    - vertical_exaggeration: Visual vertical exaggeration multiplier (default 3.5x).
      Crucial because a 3,000m depth across 120km width is subtle at true 1:1 scale.
    - downsample_factor: Step size for grid downsampling (1 = full 256x256 resolution).
    """
    if not ELEVATION_RASTER_PATH.is_file():
        raise FileNotFoundError(f"Elevation raster not found: {ELEVATION_RASTER_PATH}")

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
        lons_bound, lats_bound = transform(crs, geo_crs, [left, right], [bottom, top])
        west, south, east, north = min(lons_bound), min(lats_bound), max(lons_bound), max(lats_bound)

    # Replace any nodata with minimum elevation
    valid_mask = elevation != elev_nodata if elev_nodata is not None else np.ones_like(elevation, dtype=bool)
    min_elev = float(np.min(elevation[valid_mask]))
    max_elev = float(np.max(elevation[valid_mask]))
    mean_elev = float(np.mean(elevation[valid_mask]))

    clean_elev = np.where(valid_mask, elevation, min_elev)

    # Subsample if requested
    if downsample_factor > 1:
        z_grid = clean_elev[::downsample_factor, ::downsample_factor]
    else:
        z_grid = clean_elev

    grid_h, grid_w = z_grid.shape
    x_lons = np.linspace(west, east, grid_w)
    y_lats = np.linspace(north, south, grid_h)

    # Martian regolith colorscale (normalized 0.0 to 1.0)
    # Dark basalt crater floor -> terracotta -> iron oxide -> bright rim ridges
    mars_colorscale = [
        [0.0, "rgb(35, 15, 8)"],
        [0.18, "rgb(65, 28, 16)"],
        [0.38, "rgb(115, 48, 24)"],
        [0.60, "rgb(168, 78, 38)"],
        [0.80, "rgb(212, 125, 68)"],
        [1.0, "rgb(240, 198, 155)"],
    ]

    # Create 3D Surface
    surface = go.Surface(
        x=x_lons,
        y=y_lats,
        z=z_grid,
        colorscale=mars_colorscale,
        cmin=min_elev,
        cmax=max_elev,
        colorbar=dict(
            title=dict(
                text="Elevation (m)",
                side="right",
                font=dict(color="#ffffff", size=12),
            ),
            tickfont=dict(color="#d0d0d8", size=10),
            len=0.75,
            thickness=18,
            outlinewidth=0,
        ),
        lighting=dict(
            ambient=0.45,
            diffuse=0.8,
            specular=0.25,
            roughness=0.85,
            fresnel=0.1,
        ),
        lightposition=dict(x=-1000, y=-1000, z=2000),
        hovertemplate=(
            "<b>Longitude:</b> %{x:.3f}°E<br>"
            "<b>Latitude:</b> %{y:.3f}°N<br>"
            "<b>Elevation:</b> %{z:.0f} m relative to areoid<br>"
            "<extra></extra>"
        ),
    )

    fig = go.Figure(data=[surface])

    # Add 3D markers for mission-critical landing and geological points
    landmark_points = [
        (OCTAVIA_E_BUTLER_LANDING_LON, OCTAVIA_E_BUTLER_LANDING_LAT, -2570, "Octavia E. Butler Landing (Perseverance)", "cyan"),
        (77.4200, 18.4550, -2500, "Western Delta Fan Deposits", "gold"),
        (SEITAH_LON, SEITAH_LAT, -2590, "Séítah Formation", "orange"),
        (NERETVA_VALLIS_INLET_LON, NERETVA_VALLIS_INLET_LAT, -2420, "Neretva Vallis Fluvial Inlet", "deepskyblue"),
        (77.6953, 18.4063, -2650, "Jezero Floor Center", "white"),
        (77.5800, 18.6200, -1450, "Northern Rim Ridge", "red"),
    ]

    lons_mk, lats_mk, elevs_mk, texts_mk, colors_mk = zip(*landmark_points)

    fig.add_trace(
        go.Scatter3d(
            x=lons_mk,
            y=lats_mk,
            z=elevs_mk,
            mode="markers+text",
            marker=dict(size=6, color=colors_mk, symbol="diamond"),
            text=texts_mk,
            textposition="top right",
            textfont=dict(color="#ffffff", size=10),
            hoverinfo="text",
            showlegend=False,
        )
    )

    # 3D Scene styling
    fig.update_layout(
        title=dict(
            text=f"MARS-NAV: Jezero Crater 3D Terrain Model ({vertical_exaggeration:.1f}x Vertical Exaggeration)",
            font=dict(color="#ffffff", size=16),
            x=0.05,
            y=0.96,
        ),
        template="plotly_dark",
        paper_bgcolor="#0c0c12",
        scene=dict(
            xaxis=dict(
                title=dict(text="Longitude (°E)", font=dict(color="#ffffff")),
                tickfont=dict(color="#d0d0d8"),
                backgroundcolor="#12121c",
                gridcolor="#333344",
                showbackground=True,
            ),
            yaxis=dict(
                title=dict(text="Latitude (°N)", font=dict(color="#ffffff")),
                tickfont=dict(color="#d0d0d8"),
                backgroundcolor="#12121c",
                gridcolor="#333344",
                showbackground=True,
            ),
            zaxis=dict(
                title=dict(text="Elevation (m)", font=dict(color="#ffffff")),
                tickfont=dict(color="#d0d0d8"),
                backgroundcolor="#12121c",
                gridcolor="#333344",
                showbackground=True,
            ),
            aspectratio=dict(x=1.0, y=1.0, z=0.35),
            camera=dict(
                eye=dict(x=1.35, y=-1.35, z=0.85),
                center=dict(x=0, y=0, z=-0.1),
            ),
        ),
        margin=dict(l=10, r=10, t=50, b=10),
    )

    # Save HTML (fully self-contained, offline-ready with inlined Plotly.js)
    TERRAIN_3D_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(TERRAIN_3D_HTML_PATH), include_plotlyjs=True, full_html=True)

    # Export lightweight JSON mesh asset for frontend Three.js integration
    # Downsample to 64x64 or 128x128 for rapid web transfer
    mesh_step = 2
    mesh_z = clean_elev[::mesh_step, ::mesh_step].round(1).tolist()
    mesh_lons = np.linspace(west, east, len(mesh_z[0])).round(4).tolist()
    mesh_lats = np.linspace(north, south, len(mesh_z)).round(4).tolist()

    mesh_asset = {
        "metadata": {
            "name": "Jezero Crater 3D Terrain Mesh",
            "source": "NASA MOLA MEGDR megt44n000hb",
            "crs": "Equirectangular Mars",
            "vertical_exaggeration": vertical_exaggeration,
            "elevation_datum": "Mars Areoid (meters)",
            "elevation_min_m": min_elev,
            "elevation_max_m": max_elev,
            "elevation_mean_m": mean_elev,
            "grid_dimensions": {"rows": len(mesh_z), "cols": len(mesh_z[0])},
            "bounds": {
                "west_deg": round(west, 5),
                "east_deg": round(east, 5),
                "south_deg": round(south, 5),
                "north_deg": round(north, 5),
            },
        },
        "lons": mesh_lons,
        "lats": mesh_lats,
        "elevations": mesh_z,
        "landmarks": [
            {"name": name, "lon": lon, "lat": lat, "elevation_m": elev}
            for lon, lat, elev, name, _ in landmark_points
        ],
    }

    TERRAIN_MESH_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TERRAIN_MESH_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(mesh_asset, f, indent=2)

    return {
        "html_path": str(TERRAIN_3D_HTML_PATH),
        "json_path": str(TERRAIN_MESH_JSON_PATH),
        "min_elevation_m": min_elev,
        "max_elevation_m": max_elev,
        "grid_shape": (grid_h, grid_w),
    }


if __name__ == "__main__":
    print("Generating Jezero 3D Terrain Model...")
    res = generate_3d_terrain_model()
    print(f"3D HTML generated at: {res['html_path']}")
    print(f"Mesh JSON generated at: {res['json_path']}")
