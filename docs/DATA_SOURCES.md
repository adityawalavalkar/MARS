# Data sources and interpretation

## Terrain and imagery

- **Jezero elevation and derived slope/hazard rasters:** packaged processed MOLA elevation data and locally computed derivatives. MOLA postings are approximately 463 m/pixel for this study raster. Slope and detrended 3×3 residual roughness are regional screening proxies; they do not resolve rover-scale rocks, wheel hazards, or small scarps. The generated hazard classes are planning estimates, not certified safety assessments.
- **Regional and 2D basemap:** NASA Trek MOLA color-shaded global mosaic, `Mars_MGS_MOLA_ClrShade_merge_global_463m`. The frontend uses its WMTS tiles when online and includes a generated Jezero texture for the 3D view. NASA Trek WMTS API documentation: https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars
- **Local context imagery:** NASA Trek CTX Jezero 6 m/pixel mosaic (`JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0`); use is limited to the layer's published coverage and available tile matrices.
- **High resolution context:** NASA Trek HiRISE Jezero 25 cm/pixel mosaic (`JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd`), available only where its footprint and published tile matrices cover the view. These images provide visual context and are not used to calculate the packaged hazard raster.
- **Regional overview source:** NASA PDS MOLA MEGDR product, `megt44n000hb`; see the [MOLA MEGDR catalogue](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html). Packaged regional products are derived from the source and retain the original coordinate reference/metadata.

Please credit NASA/JPL/USGS and the source providers when redistributing imagery. Follow the terms attached to the source product and NASA Trek service.

## Science panels

- **Geology:** map unit names and symbols refer to Sun and Stack (2020), [USGS SIM 3464](https://pubs.usgs.gov/publication/sim3464). API coordinate boxes are coarse lookup aids, not digitized contacts from the official map. Results are marked approximate; points outside those boxes are returned as unmapped.
- **Weather:** modeled Jezero estimate based on MEDA-style inputs and Mars season/time. Client computes local true solar time and areocentric solar longitude with the [NASA GISS Mars24 algorithm](https://www.giss.nasa.gov/tools/mars24/help/algorithm.html). This is not a live MEDA feed or a forecast.
- **Radiation:** modeled Gale-to-Jezero transfer estimate based on MSL RAD calibration, not a live radiation observation. The UI identifies the transfer explicitly.

## Route planning

Routes use the packaged terrain/hazard rasters and configurable slope and safety preferences. Energy and consumable numbers are model estimates and depend on mission mode and crew assumptions. They are not engineering-certified vehicle performance values.
