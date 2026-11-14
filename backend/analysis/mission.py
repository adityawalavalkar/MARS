"""Mission analysis and resource estimation module for Mars exploration trajectories.

Calculates vehicle propulsion energy, crew life support consumables (water, O2),
environmental radiation exposure, and multi-factor operational feasibility.
All calculations use documented, configurable physical and physiological models.
Values are clearly distinguished as model estimates versus empirical planetary data.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct execution
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from typing import Any, Dict, List, Optional
import numpy as np

from backend.config import (
    MARS_GRAVITY_MS2,
    DEFAULT_ROVER_MASS_KG,
    DEFAULT_CREW_ROVER_MASS_KG,
    DEFAULT_ASTRONAUT_EVA_MASS_KG,
    DEFAULT_NOMINAL_SPEED_ROVER_KMH,
    DEFAULT_NOMINAL_SPEED_CREWED_KMH,
    DEFAULT_NOMINAL_SPEED_EVA_KMH,
)


def calculate_mission_analysis(
    route_result: Dict[str, Any],
    vehicle_mass_kg: Optional[float] = None,
    crew_size: int = 2,
    rolling_resistance: float = 0.065,  # Nominal Mars sandy regolith coefficient
    drivetrain_efficiency: float = 0.75,  # Mechanical-electrical efficiency
    hotel_load_watts: Optional[float] = None,  # Base power for computers/instruments/thermal
    solar_insolation_wm2: float = 590.0,  # Top of Mars atmosphere ~590 W/m², surface ~300-450 W/m²
    battery_capacity_kwh: Optional[float] = None,
) -> Dict[str, Any]:
    """Execute comprehensive mission operational analysis for a planned route trajectory.

    Parameters:
    - route_result: Output dictionary from MarsPathfinder.plan_route
    - vehicle_mass_kg: Total moving mass in kg (auto-set by mode if None)
    - crew_size: Number of astronauts participating (if crewed/eva mode)
    - rolling_resistance: Regolith friction coefficient
    - drivetrain_efficiency: Rover powertrain efficiency
    - hotel_load_watts: Idle/payload electrical power
    - battery_capacity_kwh: Optional total battery storage for feasibility cutoff
    """
    summary = route_result.get("summary", {})
    path_details = route_result.get("path_details", [])
    mode = summary.get("mode", "rover")

    total_distance_km = summary.get("distance_km", 0.0)
    total_duration_hours = summary.get("duration_hours", 0.0)
    avg_slope_deg = summary.get("avg_slope_deg", 0.0)
    max_slope_deg = summary.get("max_slope_deg", 0.0)
    elevation_gain_m = summary.get("elevation_gain_m", 0.0)
    elevation_loss_m = summary.get("elevation_loss_m", 0.0)

    # Set parameters based on mobility mode
    if mode == "crewed":
        v_mass = vehicle_mass_kg or DEFAULT_CREW_ROVER_MASS_KG
        hotel_pwr = hotel_load_watts or 650.0  # Pressurized cabin life support & comms
        batt_cap = battery_capacity_kwh or 50.0  # 50 kWh crewed rover battery pack
    elif mode == "eva":
        v_mass = vehicle_mass_kg or (DEFAULT_ASTRONAUT_EVA_MASS_KG * crew_size)
        hotel_pwr = hotel_load_watts or 80.0   # PLSS electronics
        batt_cap = battery_capacity_kwh or 8.0   # Suit batteries
    else:  # robotic rover (Perseverance / Curiosity class)
        v_mass = vehicle_mass_kg or DEFAULT_ROVER_MASS_KG
        hotel_pwr = hotel_load_watts or 180.0  # Avionics, MMRTG/battery bus, heaters
        batt_cap = battery_capacity_kwh or 30.0  # Typical mission battery buffer

    # Calculate Step-by-Step Mechanical Propulsion Energy
    total_energy_kwh = 0.0
    energy_propulsion_kwh = 0.0
    energy_hotel_kwh = (hotel_pwr * total_duration_hours) / 1000.0

    for idx in range(1, len(path_details)):
        step = path_details[idx]
        prev = path_details[idx - 1]

        dist_m = step["cumulative_dist_m"] - prev["cumulative_dist_m"]
        elev_diff_m = step["elevation_m"] - prev["elevation_m"]
        slope_rad = math.radians(step["slope_deg"])

        # Gravitational grade resistance on Mars (3.721 m/s²)
        # When climbing (elev_diff > 0), gravity opposes motion.
        # When descending, rolling resistance still acts.
        f_rolling = v_mass * MARS_GRAVITY_MS2 * rolling_resistance * math.cos(slope_rad)
        f_grade = v_mass * MARS_GRAVITY_MS2 * math.sin(slope_rad) if elev_diff_m > 0 else 0.0

        f_total_n = max(0.0, f_rolling + f_grade)
        work_joules = (f_total_n * dist_m) / drivetrain_efficiency
        step_kwh = work_joules / 3.6e6
        energy_propulsion_kwh += step_kwh

    total_energy_kwh = energy_propulsion_kwh + energy_hotel_kwh

    # Life Support Consumables Estimation (Crewed / EVA Modes)
    # Based on NASA Human Integration Design Handbook (HIDH) & xEMU specifications
    consumables: Dict[str, Any] = {}
    if mode in ("crewed", "eva"):
        # Average metabolic rate on Mars walking / rover operation: ~250 W to 380 W
        metabolic_watts = 260.0 + (avg_slope_deg * 12.0)
        # Drinking water: ~0.16 L / person-hour nominal
        drinking_water_liters = round(crew_size * 0.16 * total_duration_hours, 2)
        # Thermal sublimator cooling water: ~0.35 L / person-hour for EVA suits
        cooling_water_liters = round(crew_size * 0.35 * total_duration_hours, 2) if mode == "eva" else 0.0
        total_water_liters = round(drinking_water_liters + cooling_water_liters, 2)

        # Oxygen consumption: 0.078 kg O2 / person-hour (NASA Standard)
        oxygen_kg = round(crew_size * 0.078 * total_duration_hours, 2)

        consumables = {
            "applicable": True,
            "crew_size": crew_size,
            "avg_metabolic_rate_watts": round(metabolic_watts, 1),
            "estimated_drinking_water_liters": drinking_water_liters,
            "estimated_cooling_water_liters": cooling_water_liters,
            "estimated_total_water_liters": total_water_liters,
            "estimated_oxygen_consumed_kg": oxygen_kg,
            "model_reference": (
                "NASA Human Integration Design Handbook (NASA/SP-2010-3407) & "
                "xEMU PLSS Life Support Model (Simulated Estimates)"
            ),
        }
    else:
        consumables = {
            "applicable": False,
            "note": "Robotic rover mission profile; astronaut metabolic consumables not applicable.",
        }

    # Surface Radiation Exposure (NASA MSL Curiosity RAD Empirical Calibration)
    # Gale Crater baseline: absorbed dose ~0.21 mGy/day (~0.00875 mGy/hour).
    # Equivalent dose (accounting for Mars secondary neutron weighting factor wR ~ 3.1):
    # Gale ~0.65 mSv/day (~0.027 mSv/hour). Jezero elevation scaled (+3%): ~0.028 mSv/hour.
    radiation_hourly_absorbed_mgy = 0.00875
    radiation_hourly_equivalent_msv = 0.0280
    estimated_absorbed_dose_mgy = round(total_duration_hours * radiation_hourly_absorbed_mgy, 4)
    estimated_equivalent_dose_msv = round(total_duration_hours * radiation_hourly_equivalent_msv, 4)
    nasa_30day_limit_msv = 250.0  # NASA astronaut 30-day exposure limit
    dose_pct_of_limit = round((estimated_equivalent_dose_msv / nasa_30day_limit_msv) * 100.0, 4)

    radiation_analysis = {
        "absorbed_dose_rate_mgy_per_hour": radiation_hourly_absorbed_mgy,
        "equivalent_dose_rate_msv_per_hour": radiation_hourly_equivalent_msv,
        "equivalent_dose_rate_msv_per_sol": round(radiation_hourly_equivalent_msv * 24.66, 3),
        "cumulative_absorbed_dose_mgy": estimated_absorbed_dose_mgy,
        "cumulative_route_dose_msv": estimated_equivalent_dose_msv,
        "percentage_of_nasa_30day_limit": dose_pct_of_limit,
        "data_source": "Derived from NASA MSL Curiosity RAD Surface Radiation Measurements (Gale-to-Jezero transfer model)",
        "radiation_risk_level": "NOMINAL_LOW" if estimated_equivalent_dose_msv < 1.0 else "ELEVATED",
        "scientific_note": "Equivalent dose in mSv includes biological effectiveness factor (wR ~ 3.1) for secondary neutron radiation.",
    }

    # Multi-Factor Feasibility Evaluation
    feasibility_checks = []

    # Slope check
    if max_slope_deg > 20.0:
        feasibility_checks.append({
            "parameter": "Maximum Terrain Slope",
            "value": f"{max_slope_deg:.1f}°",
            "threshold": "20.0°",
            "status": "FAIL",
            "message": "Maximum route slope exceeds safe vehicle grade limits.",
        })
    elif max_slope_deg > 14.0:
        feasibility_checks.append({
            "parameter": "Maximum Terrain Slope",
            "value": f"{max_slope_deg:.1f}°",
            "threshold": "14.0°",
            "status": "CAUTION",
            "message": "Route passes through moderate scarps requiring reduced speed and slip monitoring.",
        })
    else:
        feasibility_checks.append({
            "parameter": "Maximum Terrain Slope",
            "value": f"{max_slope_deg:.1f}°",
            "threshold": "14.0°",
            "status": "PASS",
            "message": "All route slopes remain within nominal drive envelopes.",
        })

    # Energy capacity check
    energy_margin_pct = round(((batt_cap - total_energy_kwh) / batt_cap) * 100.0, 1)
    if total_energy_kwh > batt_cap:
        feasibility_checks.append({
            "parameter": "Energy Storage Budget",
            "value": f"{total_energy_kwh:.1f} kWh",
            "threshold": f"{batt_cap:.1f} kWh",
            "status": "FAIL",
            "message": "Estimated energy consumption exceeds onboard battery storage capacity without recharge.",
        })
    elif energy_margin_pct < 20.0:
        feasibility_checks.append({
            "parameter": "Energy Storage Budget",
            "value": f"{total_energy_kwh:.1f} kWh",
            "threshold": f"{batt_cap:.1f} kWh",
            "status": "CAUTION",
            "message": f"Low energy reserve margin ({energy_margin_pct}%). Solar or RTG recharge stop advised.",
        })
    else:
        feasibility_checks.append({
            "parameter": "Energy Storage Budget",
            "value": f"{total_energy_kwh:.1f} kWh",
            "threshold": f"{batt_cap:.1f} kWh",
            "status": "PASS",
            "message": f"Healthy energy storage margin ({energy_margin_pct}% remaining).",
        })

    # Duration check (for EVA foot exploration, standard NASA EVA limit is 8 hours)
    if mode == "eva" and total_duration_hours > 8.0:
        feasibility_checks.append({
            "parameter": "EVA Duration Limit",
            "value": f"{total_duration_hours:.1f} hours",
            "threshold": "8.0 hours",
            "status": "FAIL",
            "message": "Exceeds maximum allowable single-sortie astronaut EVA duration.",
        })

    # Overall Feasibility Determination
    has_fail = any(c["status"] == "FAIL" for c in feasibility_checks)
    has_caution = any(c["status"] == "CAUTION" for c in feasibility_checks)

    if has_fail:
        overall_status = "NO-GO"
        status_color = "#d62728"
        summary_verdict = "Mission candidate trajectory rejected: one or more safety criteria exceeded."
    elif has_caution:
        overall_status = "CAUTION"
        status_color = "#ff7f0e"
        summary_verdict = "Mission feasible with operational constraints: heightened monitoring advised."
    else:
        overall_status = "GO"
        status_color = "#2ca02c"
        summary_verdict = "Mission fully feasible: all terrain, energy, and environmental metrics within nominal bounds."

    return {
        "overall_status": overall_status,
        "status_color": status_color,
        "summary_verdict": summary_verdict,
        "trajectory_metrics": {
            "distance_km": total_distance_km,
            "duration_hours": total_duration_hours,
            "duration_sols": round(total_duration_hours / 24.66, 3),
            "elevation_gain_m": elevation_gain_m,
            "elevation_loss_m": elevation_loss_m,
            "average_slope_deg": avg_slope_deg,
            "maximum_slope_deg": max_slope_deg,
            "difficulty_score": summary.get("difficulty_score", 0.0),
        },
        "energy_requirements": {
            "total_energy_kwh": round(total_energy_kwh, 2),
            "propulsion_energy_kwh": round(energy_propulsion_kwh, 2),
            "hotel_load_energy_kwh": round(energy_hotel_kwh, 2),
            "battery_capacity_kwh": batt_cap,
            "energy_margin_pct": energy_margin_pct,
            "model_assumptions": {
                "vehicle_mass_kg": v_mass,
                "gravity_ms2": MARS_GRAVITY_MS2,
                "rolling_resistance_coefficient": rolling_resistance,
                "drivetrain_efficiency": drivetrain_efficiency,
                "hotel_load_watts": hotel_pwr,
            },
        },
        "life_support_consumables": consumables,
        "radiation_exposure": radiation_analysis,
        "feasibility_checks": feasibility_checks,
        "scientific_disclaimer": (
            "All energy, duration, consumable, and radiation values are simulated engineering "
            "model calculations based on NASA published literature. Not measured astronaut data."
        ),
    }


if __name__ == "__main__":
    from backend.analysis.pathfinding import MarsPathfinder
    print("Executing Mission Analysis Test...")
    pf = MarsPathfinder()
    route = pf.plan_route(77.4508, 18.4447, 77.6200, 18.4100, mode="rover")
    report = calculate_mission_analysis(route)
    print(f"Mission Status: {report['overall_status']}")
    print(f"Verdict: {report['summary_verdict']}")
    print(f"Total Energy: {report['energy_requirements']['total_energy_kwh']} kWh")
    print(f"Radiation Dose: {report['radiation_exposure']['cumulative_route_dose_msv']} mSv")
