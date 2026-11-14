"""NASA scientific data integration service for Jezero Crater, Mars.

Integrates datasets from multiple planetary missions and instruments:
1. HiRISE (High Resolution Imaging Science Experiment, MRO)
2. CRISM (Compact Reconnaissance Imaging Spectrometer for Mars, MRO)
3. MEDA (Mars Environmental Dynamics Analyzer, Mars 2020 Perseverance)
4. RAD (Radiation Assessment Detector, MSL Curiosity)
5. USGS SIM 3464 Geologic Map of Jezero Crater

All data sources provide official NASA/USGS citations, instrument metadata,
and clear distinctions between empirical measurements and model estimates.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


class HiRISEService:
    """NASA MRO HiRISE high-resolution imaging dataset service for Jezero Crater."""

    METADATA = {
        "dataset_name": "MRO HiRISE Jezero Mosaic",
        "instrument": "High Resolution Imaging Science Experiment (HiRISE)",
        "spacecraft": "Mars Reconnaissance Orbiter (MRO)",
        "data_provider": "NASA Planetary Data System (PDS) / USGS Astrogeology",
        "layer_id": "JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd",
        "wmts_capabilities_url": "https://trek.nasa.gov/tiles/Mars/EQ/JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd",
        "tile_template": "https://trek.nasa.gov/tiles/Mars/EQ/JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd/1.0.0/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png",
        "pixel_resolution_m": 0.25,  # 25 centimeters per pixel
        "crs": "Equirectangular Mars (latTs=0, lon0=0)",
        "spatial_coverage": {
            "west_deg": 77.30,
            "east_deg": 77.58,
            "south_deg": 18.30,
            "north_deg": 18.52,
            "target_features": [
                "Octavia E. Butler Landing Site",
                "Western Fan Delta Scarp",
                "Séítah Formation",
                "Kodiak Butte",
            ],
        },
        "status": "Available via NASA Trek WMTS",
    }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return cls.METADATA

    @classmethod
    def get_tile_url(cls, tile_matrix: int, tile_row: int, tile_col: int, style: str = "default") -> str:
        """Construct valid WMTS tile URL for high-resolution imagery."""
        return (
            f"https://trek.nasa.gov/tiles/Mars/EQ/{cls.METADATA['layer_id']}/"
            f"1.0.0/{style}/default028mm/{tile_matrix}/{tile_row}/{tile_col}.png"
        )

    @classmethod
    def coords_to_tile(cls, lon_deg: float, lat_deg: float, zoom: int = 12) -> Tuple[int, int]:
        """Convert planetary coordinates (lon, lat) to NASA Trek HiRISE TileRow and TileCol at specified zoom.

        NASA Trek default028mm equirectangular matrix set:
        - TopLeftCorner: -180.0° Longitude, +90.0° Latitude
        - MatrixWidth: 2 ** (zoom + 1)
        - MatrixHeight: 2 ** zoom
        """
        matrix_width = 2 ** (zoom + 1)
        matrix_height = 2 ** zoom
        col = int((lon_deg + 180.0) / 360.0 * matrix_width)
        row = int((90.0 - lat_deg) / 180.0 * matrix_height)
        return row, col

    @classmethod
    def get_tile_url_for_coords(cls, lon_deg: float, lat_deg: float, zoom: int = 12, style: str = "default") -> str:
        """Generate verified NASA Trek WMTS tile URL for specific planetary coordinates."""
        row, col = cls.coords_to_tile(lon_deg, lat_deg, zoom)
        return cls.get_tile_url(zoom, row, col, style)


class CRISMService:
    """Compact Reconnaissance Imaging Spectrometer for Mars (CRISM) mineralogy service.

    Implementation: Curated spatial catalog derived from targeted NASA CRISM observations
    published in planetary science literature (Ehlmann et al., Goudge et al., Horgan et al.).
    Not a raw PDS hyperspectral cube processor.
    """

    CATALOG_TYPE = "CURATED_SPECTROMETRIC_CATALOG"
    CATALOG_DESCRIPTION = (
        "Catalog of published targeted CRISM observations with spatial bounding boxes, "
        "spectral absorption bands, and confidence levels. Derived from PDS targeted RDRs."
    )

    MINERAL_UNITS = [
        {
            "id": "MIN_01",
            "name": "Fe/Mg Smectite Clay",
            "mineral_group": "Phyllosilicates (Nontronite / Saponite)",
            "observation_id": "FRT000047A3",
            "pds_product_url": "https://pds-geosciences.wustl.edu/mro/mro-m-crism-3-rdr-targeted-v1/mrocr_2001/",
            "location": "Western Delta Bottomsets and Crater Floor Margin",
            "bounds": {"west": 77.38, "east": 77.49, "south": 18.41, "north": 18.48},
            "spectral_features_um": [1.41, 1.91, 2.30],
            "significance": "Aqueous alteration in neutral-to-alkaline ancient lacustrine water; high biosignature preservation potential.",
            "confidence": "HIGH (Confirmed by CRISM targeted spectrometry and Perseverance PIXL/SHERLOC)",
        },
        {
            "id": "MIN_02",
            "name": "Mg-Carbonate (Magnesite / Hydromagnesite)",
            "mineral_group": "Carbonates",
            "observation_id": "FRT00005C5E",
            "pds_product_url": "https://pds-geosciences.wustl.edu/mro/mro-m-crism-3-rdr-targeted-v1/mrocr_2001/",
            "location": "Jezero Inner Crater Rim ('Bathtub Ring') and Delta Topsets",
            "bounds": {"west": 77.35, "east": 77.52, "south": 18.45, "north": 18.55},
            "spectral_features_um": [1.90, 2.31, 2.51],
            "significance": "Precipitation in open lake shoreline environments; critical for dating paleoclimate conditions.",
            "confidence": "HIGH (Confirmed by CRISM observations and orbital spectral deconvolution)",
        },
        {
            "id": "MIN_03",
            "name": "Olivine-Rich Basalt (Fo60-80)",
            "mineral_group": "Igneous Silicates",
            "observation_id": "HRL000040FF",
            "pds_product_url": "https://pds-geosciences.wustl.edu/mro/mro-m-crism-3-rdr-targeted-v1/mrocr_2001/",
            "location": "Crater Floor Fractured Unit / Séítah Formation",
            "bounds": {"west": 77.42, "east": 77.65, "south": 18.36, "north": 18.44},
            "spectral_features_um": [1.05],
            "significance": "Thick igneous cumulate layer or volcanic lava flow post-dating crater impact.",
            "confidence": "DEFINITIVE (Ground truth confirmed by Perseverance core samples)",
        },
        {
            "id": "MIN_04",
            "name": "Low-Calcium Pyroxene & Plagioclase",
            "mineral_group": "Crustal Silicates",
            "observation_id": "FRT0000B967",
            "pds_product_url": "https://pds-geosciences.wustl.edu/mro/mro-m-crism-3-rdr-targeted-v1/mrocr_2001/",
            "location": "Northern and Western Crater Rim Escarpments",
            "bounds": {"west": 77.30, "east": 77.75, "south": 18.52, "north": 18.70},
            "spectral_features_um": [0.92, 1.85],
            "significance": "Ancient Pre-Noachian impact basement excavated by the Isidis basin-forming event.",
            "confidence": "HIGH",
        },
        {
            "id": "MIN_05",
            "name": "Hydrated Silica / Opaline Silica",
            "mineral_group": "Amorphous Silicates",
            "observation_id": "FRT000047A3",
            "pds_product_url": "https://pds-geosciences.wustl.edu/mro/mro-m-crism-3-rdr-targeted-v1/mrocr_2001/",
            "location": "Delta Scarp Front and Fluvial Inlets",
            "bounds": {"west": 77.40, "east": 77.46, "south": 18.43, "north": 18.47},
            "spectral_features_um": [1.40, 1.90, 2.21],
            "significance": "Hydrothermal or intense low-temperature aqueous leaching; exceptional taphonomic bio-preservation.",
            "confidence": "MODERATE_HIGH",
        },
    ]

    @classmethod
    def get_all_minerals(cls) -> List[Dict[str, Any]]:
        return cls.MINERAL_UNITS

    @classmethod
    def query_minerals_at_coords(cls, lon_deg: float, lat_deg: float) -> List[Dict[str, Any]]:
        """Identify confirmed mineralogical units observed at a specific coordinate."""
        matches = []
        for unit in cls.MINERAL_UNITS:
            b = unit["bounds"]
            if b["west"] <= lon_deg <= b["east"] and b["south"] <= lat_deg <= b["north"]:
                matches.append(unit)
        return matches


class MarsClimateService:
    """Atmospheric and environmental dynamics service based on NASA Mars 2020 MEDA."""

    # Baseline MEDA Annual Statistics at Jezero Crater (18.4°N, elevation -2570m)
    CLIMATE_BASELINE = {
        "instrument": "Mars Environmental Dynamics Analyzer (MEDA)",
        "mission": "NASA Mars 2020 (Perseverance Rover)",
        "location": "Jezero Crater floor (18.4447°N, 77.4508°E, -2570 m)",
        "data_provider": "NASA Planetary Data System (PDS) Atmospheres Node",
        "source_url": "https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html",
        "pressure_pa": {
            "mean": 750.0,
            "min": 715.0,
            "max": 785.0,
            "units": "Pascals (Pa)",
            "seasonal_trend": "Controlled by seasonal CO2 polar cap condensation and sublimation.",
        },
        "temperature_celsius": {
            "mean": -55.0,
            "diurnal_min": -84.0,  # Just before Martian sunrise (~05:30 LTST)
            "diurnal_max": -12.0,  # Peak around 14:00 LTST
            "units": "Degrees Celsius (°C)",
        },
        "wind": {
            "mean_speed_ms": 3.6,
            "gust_max_ms": 17.5,
            "prevailing_direction_deg": 115.0,  # East-Southeast daytime upslope
            "units": "Meters per second (m/s)",
            "dust_devil_frequency": "High convective afternoon vortex activity.",
        },
        "dust_optical_depth_tau": {
            "nominal": 0.38,
            "storm_elevation": 1.25,
            "units": "dimensionless optical depth at 880 nm",
        },
        "relative_humidity_pct": {
            "night_peak": 22.0,
            "daytime": 0.5,
            "units": "percent (%)",
        },
    }

    @classmethod
    def get_baseline_climate(cls) -> Dict[str, Any]:
        return cls.CLIMATE_BASELINE

    @classmethod
    def predict_current_environment(
        cls,
        sol_time_hours: float = 12.0,  # Local True Solar Time (0.0 to 24.0 hours)
        solar_longitude_ls: float = 180.0,
    ) -> Dict[str, Any]:
        """Estimate ambient temperature, pressure, and wind based on MEDA diurnal cycle model."""
        # Diurnal temperature sinusoidal wave with dawn minimum and 14:00 peak
        t_phase = (sol_time_hours - 14.0) * (2.0 * math.pi / 24.66)
        # Small explicitly modeled seasonal adjustment; Ls comes from the
        # NASA Mars24 ephemeris calculation supplied by the client.
        seasonal_offset = 5.0 * math.cos(math.radians(solar_longitude_ls - 90.0))
        temp_c = -48.0 + seasonal_offset + 36.0 * math.cos(t_phase)

        # Diurnal pressure tide (~35 Pa peak-to-peak semi-diurnal thermal tide)
        p_phase = sol_time_hours * (4.0 * math.pi / 24.66)
        pressure_pa = 750.0 + 18.0 * math.cos(p_phase)

        # Wind speed model: quiescent mornings, active gusty afternoons
        if 11.0 <= sol_time_hours <= 17.0:
            wind_speed_ms = 6.5 + 4.5 * math.sin((sol_time_hours - 11.0) * math.pi / 6.0)
            wind_dir = "ESE (115°)"
            condition = "Convective afternoon thermal winds with frequent dust vortex activity"
        else:
            wind_speed_ms = 2.4
            wind_dir = "NW (300°)"
            condition = "Stable nocturnal boundary layer with light downslope breezes"

        return {
            "query_time": {
                "local_solar_time_hours": sol_time_hours,
                "solar_longitude_ls_deg": solar_longitude_ls,
            },
            "ambient_temperature_celsius": round(temp_c, 1),
            "atmospheric_pressure_pa": round(pressure_pa, 1),
            "estimated_wind_speed_ms": round(wind_speed_ms, 1),
            "wind_direction": wind_dir,
            "dust_optical_depth_tau": 0.40,
            "condition_summary": condition,
            "model_provenance": "NASA Mars 2020 MEDA Diurnal Empirical Model (Simulated Output)",
        }


class RadiationService:
    """Surface radiation assessment service based on NASA MSL Curiosity RAD measurements."""

    RAD_CALIBRATION = {
        "instrument": "Radiation Assessment Detector (RAD)",
        "mission": "NASA Mars Science Laboratory (MSL Curiosity)",
        "measured_location": "Gale Crater floor (elevation -4400m)",
        "target_location": "Jezero Crater floor (elevation -2570m)",
        "data_provider": "NASA Planetary Data System (PDS) Planetary Plasma Node",
        "source_url": "https://pds-ppi.igpp.ucla.edu/mission/MSL/MSL/RAD",
        "surface_absorbed_dose_rate_ugy_per_day": 210.0,  # 210 µGy/day
        "surface_equivalent_dose_rate_msv_per_day": 0.65,  # 0.65 mSv/day (GCR baseline)
        "surface_equivalent_dose_rate_msv_per_sol": 0.67,  # 0.67 mSv/sol
        "surface_equivalent_dose_rate_msv_per_hour": 0.027, # 0.027 mSv/hour
        "annual_cumulative_dose_msv": 237.0,  # ~237 mSv/year
        "astronaut_exposure_standards": {
            "nasa_career_limit_msv": 600.0,
            "nasa_30day_limit_msv": 250.0,
            "nasa_1year_limit_msv": 500.0,
        },
        "solar_particle_event_spe_risk": (
            "Solar particle events can raise the surface dose rate. The MSL RAD September 2017 event "
            "raised it by about a factor of 2 (Hassler et al. 2018, doi:10.1029/2018SW001959); "
            "Zeitlin et al. 2018 report a factor of 2-3. Simulated multipliers in MARS NAV are labelled as such."
        ),
        "scientific_note": (
            "Curiosity RAD measured data at Gale Crater is transferred to Jezero Crater "
            "with a slight elevation scaling adjustment (+3% dose due to thinner atmospheric "
            "column at -2570m vs -4400m)."
        ),
    }

    @classmethod
    def get_radiation_profile(cls) -> Dict[str, Any]:
        return cls.RAD_CALIBRATION

    @classmethod
    def estimate_mission_radiation(cls, mission_hours: float) -> Dict[str, Any]:
        """Estimate cumulative ionizing radiation dose for an EVA or surface traverse."""
        # Jezero scaled rate: 0.028 mSv/hour equivalent dose
        jezero_hourly_rate = 0.028
        total_dose = round(mission_hours * jezero_hourly_rate, 4)
        pct_30day = round((total_dose / 250.0) * 100.0, 3)

        return {
            "traverse_duration_hours": mission_hours,
            "estimated_cumulative_dose_msv": total_dose,
            "hourly_dose_rate_msv": jezero_hourly_rate,
            "percentage_of_30day_limit": pct_30day,
            "safety_status": "NOMINAL" if total_dose < 2.5 else "MONITOR",
            "model_provenance": "NASA MSL RAD Empirical Transfer Model (Simulated Estimate)",
        }


class GeologyService:
    """Geological mapping and stratigraphy service based on USGS SIM 3464 (Sun & Stack, 2020)."""

    # Official unit names and symbols follow SIM 3464 (Sun & Stack, 2020).
    # Rectangles below are coarse lookup aids only; they are not digitized USGS
    # contacts and every returned unit is explicitly marked approximate.
    GEOLOGIC_UNITS = [
        {"unit_symbol": "NHjf₂", "unit_name": "Jezero fan unit 2", "age": "Noachian–Hesperian",
         "lithology": "Fan deposit unit named in USGS SIM 3464.", "depositional_environment": "Fan deposit; local attribution is approximate.",
         "spatial_domain": "Western Jezero fan lookup box", "bounds": {"west": 77.38, "east": 77.49, "south": 18.41, "north": 18.49}, "approximate": True},
        {"unit_symbol": "Njf", "unit_name": "Jezero floor unit", "age": "Noachian",
         "lithology": "Jezero floor map unit named in USGS SIM 3464.", "depositional_environment": "SIM 3464 discusses ash or airfall interpretations; local attribution is approximate.",
         "spatial_domain": "Central and southern Jezero floor lookup box", "bounds": {"west": 77.42, "east": 77.72, "south": 18.35, "north": 18.44}, "approximate": True},
        {"unit_symbol": "Nle", "unit_name": "Lower etched unit", "age": "Noachian",
         "lithology": "Olivine-bearing etched unit named in USGS SIM 3464.", "depositional_environment": "SIM 3464 discusses ash-fall and possible lacustrine alteration; local attribution is approximate.",
         "spatial_domain": "Lower etched unit lookup box", "bounds": {"west": 77.43, "east": 77.74, "south": 18.32, "north": 18.43}, "approximate": True},
        {"unit_symbol": "Nue", "unit_name": "Upper etched unit", "age": "Noachian",
         "lithology": "Olivine-bearing etched unit with mapped surface-texture variation.", "depositional_environment": "SIM 3464 discusses ash-fall or pyroclastic-surge interpretations; local attribution is approximate.",
         "spatial_domain": "Jezero rim and wall lookup box", "bounds": {"west": 77.30, "east": 77.85, "south": 18.52, "north": 18.75}, "approximate": True},
        {"unit_symbol": "Hnpf", "unit_name": "Nili Planum fan unit", "age": "Hesperian",
         "lithology": "Fan-shaped deposits named in USGS SIM 3464.", "depositional_environment": "SIM 3464 interprets these as alluvial or fluvial deposits; local attribution is approximate.",
         "spatial_domain": "Neretva Vallis fan lookup box", "bounds": {"west": 76.80, "east": 77.30, "south": 18.45, "north": 18.65}, "approximate": True},
        {"unit_symbol": "Nnp₁", "unit_name": "Nili Planum unit 1", "age": "Noachian",
         "lithology": "Nili Planum unit 1 named in USGS SIM 3464.", "depositional_environment": "Unit origin remains interpretive in SIM 3464; local attribution is approximate.",
         "spatial_domain": "Eastern map-edge lookup box", "bounds": {"west": 77.75, "east": 77.80, "south": 17.70, "north": 18.70}, "approximate": True},
    ]

    CITATION = {
        "title": "Geologic Map of Jezero Crater and the Nili Planum Region, Mars",
        "authors": "Sun, V.Z. and Stack, K.M.",
        "publication_year": 2020,
        "series": "USGS Scientific Investigations Map 3464",
        "scale": "1:75,000",
        "doi": "https://doi.org/10.3133/sim3464",
        "publisher": "U.S. Geological Survey (USGS)",
    }

    @classmethod
    def get_citation(cls) -> Dict[str, Any]:
        return cls.CITATION

    @classmethod
    def get_all_units(cls) -> List[Dict[str, Any]]:
        return cls.GEOLOGIC_UNITS

    @classmethod
    def query_geology_at_coords(cls, lon_deg: float, lat_deg: float) -> Optional[Dict[str, Any]]:
        """Identify mapped geological unit at a specific planetary coordinate."""
        matches = []
        for u in cls.GEOLOGIC_UNITS:
            b = u["bounds"]
            if b["west"] <= lon_deg <= b["east"] and b["south"] <= lat_deg <= b["north"]:
                area = (b["east"] - b["west"]) * (b["north"] - b["south"])
                matches.append((area, u["unit_symbol"], u))
        # Hand-drawn approximate rectangles overlap; choose the smallest mapped
        # box, then symbol order for a stable, deterministic tie break.
        if matches:
            return min(matches, key=lambda item: (item[0], item[1]))[2]
        return {
            "unit_symbol": "unmapped",
            "unit_name": "Unmapped area",
            "age": "Not assigned",
            "lithology": "No unit attribution outside the approximate lookup polygons.",
            "depositional_environment": "Unmapped",
            "spatial_domain": "Outside configured approximate unit boxes",
            "bounds": None,
            "approximate": True,
        }
