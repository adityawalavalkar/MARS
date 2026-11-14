# Regional mapping architecture

## Coverage verification

The local `megt44n000hb.img` source was inspected before processing. Its ENVI header and raster metadata report an equirectangular Mars product with 11,520 × 5,632 cells, 463.0576672 m spacing, and geographic extent **0–90°E, 0–44°N**. The regional request (**65–90°E, 12–27°N**) is fully inside that coverage, so no second MOLA download is used.

## Three levels of detail

1. **Regional overview** — `regional_mola_overview.tif` is a 640 × 384, DEFLATE-compressed, tiled GeoTIFF created from the local MOLA source by average resampling. It contains 2×, 4×, and 8× internal overviews. `regional_mola_overview.webp` is a display preview only.
2. **Local exploration** — Leaflet requests NASA Trek CTX WMTS tiles only when the viewport intersects Jezero at zoom 10 or higher. `keepBuffer=4` retains nearby browser tiles; nothing is downloaded or persisted by this project.
3. **Detailed Jezero analysis** — existing Jezero elevation, slope, hazard, A* pathfinding, and 3D mesh products are unchanged. Regional cells are never used for hazards, routing, or 3D analysis.

## Regional APIs

- `GET /api/terrain/regional` — overview metadata, compression, overviews, and availability.
- `GET /api/terrain/regional/features` — GeoJSON display extents for the named regional context.
- `GET /api/terrain/regional/grid?south=&west=&north=&east=&resolution=` — a viewport-only elevation grid. It uses a 12-entry in-process LRU cache and clamps requests to the supported region.

The feature extents are orientation aids, not analysis masks or formal geologic polygons. Gazetteer source links are included in the API response. The entries use the USGS Gazetteer records for [Nili Fossae](https://planetarynames.wr.usgs.gov/Feature/4271), [Isidis Planitia](https://planetarynames.wr.usgs.gov/Feature/2735), [Neretva Vallis](https://planetarynames.wr.usgs.gov/Feature/15879), [Sava Vallis](https://planetarynames.wr.usgs.gov/Feature/15904), and [Pliva Vallis](https://planetarynames.wr.usgs.gov/Feature/15903).

## Regeneration and storage

Run the following only when the regional overview needs to be regenerated:

```powershell
python backend/preprocess_mola.py --regional
```

The command reads the existing raw MOLA tile once and produces the compact derived files in `data/processed/`. `data/raw/`, `data/processed/`, virtual environments, `node_modules`, and build artifacts are ignored by Git.
