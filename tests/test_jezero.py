import json
from backend.services.jezero_service import JezeroService
def test_default_scenario_routes_and_serialises():
    S = JezeroService.get(); T = json.load(open('frontend/public/jezero/science_targets.json')); st = T['start']; d = T['targets'][0]
    r = S.plan([{'lat': st['lat'], 'lon': st['lon']}, {'lat': d['lat'], 'lon': d['lon'], 'stay_min': 15}], {}, {'active': True, 'multiplier': 2.0}, {'lat': st['lat'], 'lon': st['lon']})
    json.dumps(r)
    assert 3 < r['fast']['distance_km'] < 12 and r['fast']['max_slope_deg'] <= 25.5 and r['spe']['multiplier'] == 2.0
def test_outside_dem_rejected():
    S = JezeroService.get(); r = S.plan([{'lat': 0, 'lon': 0}, {'lat': 18.4, 'lon': 77.4}], {}, {}, {'lat': 18.4, 'lon': 77.4}); assert r['error']
