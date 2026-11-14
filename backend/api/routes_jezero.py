"""Jezero 20 m CTX routing, radiation and mission-scenario endpoints. Existing /api routes are unchanged."""
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.jezero_service import JezeroService, DEFAULTS, ASSUMPTION_NOTES, SPE, BASELINE_MSV_H, BASELINE_MSV_SOL, RES_LABEL
from backend.services.science_service import RadiationService

router = APIRouter(prefix='/api/jezero', tags=['Jezero 20 m'])

class Pt(BaseModel):
    lat: float; lon: float; id: Optional[str] = None; stay_min: float = 0.0
class SpeIn(BaseModel):
    active: bool = False; multiplier: float = 2.0
class PlanIn(BaseModel):
    points: List[Pt]; shelter: Pt; spe: SpeIn = SpeIn(); params: dict = {}

@router.get('/config')
def config():
    rp = RadiationService.get_radiation_profile()
    return {'resolution_label': RES_LABEL, 'defaults': DEFAULTS, 'assumption_labels': ASSUMPTION_NOTES, 'spe': SPE,
            'baseline': {'msv_per_hour': BASELINE_MSV_H, 'msv_per_sol': BASELINE_MSV_SOL, 'source': rp['source_url'], 'note': rp['scientific_note']}}

@router.post('/route')
def route(body: PlanIn):
    if len(body.points) < 2: return {'error': True, 'detail': 'Need at least a start and an end point'}
    return JezeroService.get().plan([p.model_dump() for p in body.points], body.params, body.spe.model_dump(), body.shelter.model_dump())

@router.get('/pov')
def pov(lat: float, lon: float, radius_m: float = 1600.0):
    return JezeroService.get().pov_patch(lat, lon, min(radius_m, 2400.0))
