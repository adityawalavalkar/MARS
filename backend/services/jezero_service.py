"""Jezero routing + radiation service on the 20 m CTX DEM.

Every constant that is not a measurement is an editable ASSUMPTION and is labelled as such in the API response.
Hazard here is DERIVED (DEM slope + roughness + assumed geologic surface-unit costs); it is not measured rock abundance.
"""
from __future__ import annotations
import heapq, json, math
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
NPZ = ROOT / 'data/processed/jezero/jezero_analysis.npz'
CFG_UNITS = ROOT / 'data/config/unit_hazard_costs.json'
RES_LABEL = '20 m CTX terrain'
NB = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]

# ---- constants: (value, label). Sources are named; everything else is an ASSUMPTION ----
BASELINE_MSV_H = 0.027          # existing RadiationService (MSL RAD, Gale; Jezero-scaled elsewhere)
BASELINE_MSV_SOL = 0.67
SPE = {'nominal_multiplier': 2.0, 'worst_multiplier': 3.0, 'label': 'SIMULATED EVENT',
       'basis': 'MSL RAD Sept 2017 event: dose rate ~x2 (Hassler et al. 2018, doi 10.1029/2018SW001959); x2-3 per Zeitlin et al. 2018'}
DEFAULTS = {
 'walk_speed_kmh': 2.0, 'slope_limit_deg': 25.0, 'slope_weight': 1.0, 'rough_weight': 1.0, 'rad_weight': 2.0,
 'max_shield_reduction': 0.30, 'shield_window_m': 600.0, 'shield_ref_relief_m': 60.0,
 'dose_budget_msv': 0.5, 'amber_margin_frac': 0.30, 'crew': 2,
 'o2_kg_per_person_h': 0.08, 'water_kg_per_person_h': 0.25, 'power_w_per_person': 200.0, 'consumable_reserve_frac': 0.30,
}
ASSUMPTION_NOTES = {
 'walk_speed_kmh': 'ASSUMPTION flat-ground suited walking speed (Tobler slope scaling applied)',
 'slope_limit_deg': 'ASSUMPTION suit slope limit', 'slope_weight': 'ASSUMPTION', 'rough_weight': 'ASSUMPTION',
 'rad_weight': 'ASSUMPTION weight on terrain-shielding exposure in the safer route',
 'max_shield_reduction': 'ASSUMPTION max dose reduction in fully enclosed terrain (not measured)',
 'shield_window_m': 'ASSUMPTION terrain-openness window', 'shield_ref_relief_m': 'ASSUMPTION relief giving full shielding',
 'dose_budget_msv': 'ASSUMPTION per-EVA dose budget', 'amber_margin_frac': 'ASSUMPTION amber threshold (fraction of budget)',
 'o2_kg_per_person_h': 'ASSUMPTION', 'water_kg_per_person_h': 'ASSUMPTION', 'power_w_per_person': 'ASSUMPTION',
 'consumable_reserve_frac': 'ASSUMPTION', 'crew': 'Scenario input'}


class JezeroService:
    _inst = None

    @classmethod
    def get(cls) -> 'JezeroService':
        if cls._inst is None: cls._inst = cls()
        return cls._inst

    def __init__(self):
        d = np.load(NPZ)
        self.dem = np.where(d['dem'] == 65535, np.nan, d['dem'].astype('float32')/10 - 3600)
        self.slope = np.where(d['slope'] == 255, np.nan, d['slope'].astype('float32')/2)
        self.rough = np.where(d['rough'] == 255, np.nan, d['rough'].astype('float32')/8)
        self.unit = d['unit']; self.unit_names = [str(n) for n in d['unit_names']]
        self.x0, self.y0, self.px, self.R, self.phi0 = [float(v) for v in d['origin']]
        self.KX = self.R*math.cos(math.radians(self.phi0)); self.H, self.W = self.dem.shape

    # ---- geometry ----
    def rc(self, lat, lon): return (self.y0-math.radians(lat)*self.R)/self.px, (math.radians(lon)*self.KX-self.x0)/self.px
    def ll(self, r, c): return math.degrees((self.y0-r*self.px)/self.R), math.degrees((self.x0+c*self.px)/self.KX)
    def inside(self, lat, lon):
        r, c = self.rc(lat, lon); return 1 <= r < self.H-1 and 1 <= c < self.W-1 and not math.isnan(self.dem[int(r), int(c)])

    def unit_cost_table(self):
        cfg = json.load(open(CFG_UNITS))['surface_unit_cost']
        return np.array([cfg.get(n, 1.0) for n in self.unit_names], 'float32')

    # ---- window grids (strided so the Python search stays interactive) ----
    def window(self, pts, margin_m=1500.0, max_cells=450):
        rcs = [self.rc(p['lat'], p['lon']) for p in pts]; m = margin_m/self.px
        r0 = int(max(1, min(r for r, _ in rcs)-m)); r1 = int(min(self.H-2, max(r for r, _ in rcs)+m))
        c0 = int(max(1, min(c for _, c in rcs)-m)); c1 = int(min(self.W-2, max(c for _, c in rcs)+m))
        st = max(1, math.ceil(max(r1-r0, c1-c0)/max_cells)); return r0, c0, r1, c1, st

    def build(self, win, prm, spe_mult):
        r0, c0, r1, c1, st = win; sl = (slice(r0, r1, st), slice(c0, c1, st))
        z, s, ro, u = self.dem[sl].astype('float64'), self.slope[sl].astype('float64'), self.rough[sl].astype('float64'), self.unit[sl]
        uc = self.unit_cost_table()[u].astype('float64')
        # terrain-shielding index from DEM openness: ground below its surroundings => more sky blocked (ASSUMED mapping)
        k = max(3, int(prm['shield_window_m']/(self.px*st))); zf = np.where(np.isnan(z), np.nanmedian(z), z)
        relief = np.clip((ndi.uniform_filter(zf, k)-zf)/prm['shield_ref_relief_m'], 0, 1)
        shield = 1.0 - prm['max_shield_reduction']*relief            # dose factor 0.7..1.0 (ASSUMPTION mapping)
        exposure = (shield-(1-prm['max_shield_reduction']))/prm['max_shield_reduction']  # 0 shielded .. 1 open sky
        base = (1 + prm['slope_weight']*(np.nan_to_num(s, nan=90)/prm['slope_limit_deg'])**2 + prm['rough_weight']*np.nan_to_num(ro)/5.0)*uc
        return dict(z=z, s=s, ro=ro, uc=uc, shield=shield, exposure=exposure, base=base, st=st, r0=r0, c0=c0, step=self.px*st, spe=spe_mult)

    # ---- search: A* (cost) from a to b ----
    def astar(self, G, a, b, rad_w, lim):
        z, base, expo = G['z'], G['base'], G['exposure']; h, w = z.shape; step = G['step']
        cost = base*(1 + rad_w*expo); hmin = float(np.nanmin(cost)); tl = math.tan(math.radians(lim))
        zf = z.ravel(); cf = cost.ravel(); n = h*w; INF = 1e18
        gs = np.full(n, INF); par = np.full(n, -1, np.int64); ia, ib = a[0]*w+a[1], b[0]*w+b[1]; gs[ia] = 0
        pq = [(0.0, ia)]; closed = np.zeros(n, bool)
        while pq:
            f, i = heapq.heappop(pq)
            if i == ib: break
            if closed[i]: continue
            closed[i] = True; r, c = divmod(i, w); zi = zf[i]
            for dr, dc in NB:
                rr, cc = r+dr, c+dc
                if rr < 0 or cc < 0 or rr >= h or cc >= w: continue
                j = rr*w+cc
                if closed[j]: continue
                zj = zf[j]
                if zj != zj: continue
                d = step*(1.4142 if dr and dc else 1.0)
                if abs(zj-zi)/d > tl: continue
                g = gs[i] + d*0.5*(cf[i]+cf[j])
                if g < gs[j]:
                    gs[j] = g; par[j] = i
                    ry, rx = rr-b[0], cc-b[1]
                    heapq.heappush(pq, (g + hmin*step*math.hypot(ry, rx), j))
        if par[ib] < 0 and ia != ib: return None
        path = []; i = ib
        while i != -1: path.append(divmod(i, w)); i = par[i]
        return path[::-1]

    @staticmethod
    def tobler(dz, d, v0):  # km/h; normalised so flat = v0
        s = dz/d; return v0*math.exp(-3.5*abs(s+0.05))/math.exp(-0.175)

    def return_field(self, G, shelter, prm, base_rate, lim):
        """Time-optimal walk-home Dijkstra from the shelter on the reversed graph: time (s) and dose (mSv) to reach shelter."""
        z = G['z']; h, w = z.shape; step = G['step']; tl = math.tan(math.radians(lim)); zf = z.ravel(); sh = G['shield'].ravel()
        T = np.full(h*w, 1e18); D = np.zeros(h*w); i0 = shelter[0]*w+shelter[1]; T[i0] = 0; pq = [(0.0, i0)]; done = np.zeros(h*w, bool); v0 = prm['walk_speed_kmh']
        while pq:
            t, i = heapq.heappop(pq)
            if done[i]: continue
            done[i] = True; r, c = divmod(i, w)
            for dr, dc in NB:
                rr, cc = r+dr, c+dc
                if rr < 0 or cc < 0 or rr >= h or cc >= w: continue
                j = rr*w+cc
                if done[j] or zf[j] != zf[j]: continue
                d = step*(1.4142 if dr and dc else 1.0); dz = zf[i]-zf[j]   # walker goes j -> i
                if abs(dz)/d > tl: continue
                dt = d/(self.tobler(dz, d, v0)*1000/3600)
                if t+dt < T[j]:
                    T[j] = t+dt; D[j] = D[i] + dt/3600*base_rate*0.5*(sh[i]+sh[j]); heapq.heappush(pq, (t+dt, j))
        return T.reshape(h, w), D.reshape(h, w)

    # ---- public API ----
    def plan(self, pts: List[Dict], prm: Dict, spe: Dict, shelter: Dict) -> Dict[str, Any]:
        P = {**DEFAULTS, **{k: v for k, v in prm.items() if v is not None}}
        for p in pts + [shelter]:
            if not self.inside(p['lat'], p['lon']): return {'error': True, 'detail': f"Point {p['lat']:.4f},{p['lon']:.4f} is outside the {RES_LABEL} coverage or on nodata"}
        mult = float(spe.get('multiplier', 1.0)) if spe.get('active') else 1.0
        rate = BASELINE_MSV_H*mult
        win = self.window(pts+[shelter]); G = self.build(win, P, mult); lim = P['slope_limit_deg']
        def node(p):
            r, c = self.rc(p['lat'], p['lon']); return int(round((r-G['r0'])/G['st'])), int(round((c-G['c0'])/G['st']))
        nodes = [node(p) for p in pts]; sn = node(shelter)
        T, D = self.return_field(G, sn, P, rate, lim)
        out = {'resolution_label': RES_LABEL, 'grid_step_m': G['step'], 'spe': {'active': mult > 1, 'multiplier': mult, **SPE},
               'baseline_msv_h': BASELINE_MSV_H, 'assumptions': {k: {'value': P[k], 'label': ASSUMPTION_NOTES.get(k, '')} for k in DEFAULTS}}
        for label, rw in (('fast', 0.0), ('safe', P['rad_weight'])):
            path = []; leg_end = [0]
            for a, b in zip(nodes[:-1], nodes[1:]):
                seg = self.astar(G, a, b, rw, lim)
                if seg is None: return {'error': True, 'detail': f'No slope-limited ({lim:.0f} deg) path between waypoints in {RES_LABEL}'}
                path += seg if not path else seg[1:]; leg_end.append(len(path)-1)
            out[label] = self.metrics(G, path, leg_end, pts, P, rate, T, D)
        return out

    def metrics(self, G, path, leg_end, pts, P, rate, T, D):
        z, sh, step = G['z'], G['shield'], G['step']; v0 = P['walk_speed_kmh']
        dist = climb = desc = t = dose = 0.0; coords = []; cum = [0.0]; tcum = [0.0]; dcum = [0.0]; slopes = []; rough = []; ucs = []
        for k, (r, c) in enumerate(path):
            coords.append([round(self.ll(G['r0']+r*G['st'], G['c0']+c*G['st'])[1], 6), round(self.ll(G['r0']+r*G['st'], G['c0']+c*G['st'])[0], 6), round(float(z[r, c]), 1)])
            if k:
                pr, pc = path[k-1]; d2 = step*math.hypot(r-pr, c-pc); dz = float(z[r, c]-z[pr, pc]); d = math.hypot(d2, dz)
                dt = d2/(self.tobler(dz, d2, v0)*1000/3600); dist += d; climb += max(dz, 0); desc += max(-dz, 0); t += dt
                dose += dt/3600*rate*0.5*(sh[r, c]+sh[pr, pc])
                cum.append(dist); tcum.append(t); dcum.append(dose)
            slopes.append(float(G['s'][r, c]) if not math.isnan(G['s'][r, c]) else 0); rough.append(float(G['ro'][r, c]) if not math.isnan(G['ro'][r, c]) else 0); ucs.append(float(G['uc'][r, c]))
        # per-waypoint timeline incl. stays, return-to-shelter and dose budget
        wps = []; stay_t = 0.0; stay_d = 0.0
        for i, p in enumerate(pts):
            k = leg_end[i]; r, c = path[k]; here_rate = rate*float(sh[r, c]); stay_h = float(p.get('stay_min', 0))/60
            arrive_t = tcum[k]+stay_t; arrive_d = dcum[k]+stay_d; stay_t += stay_h*3600; stay_d += stay_h*here_rate
            leave_d = dcum[k]+stay_d; ret_t = float(T[r, c]); ret_d = float(D[r, c]); margin = P['dose_budget_msv']-(leave_d+ret_d)
            st = 'red' if margin < 0 else 'amber' if margin < P['amber_margin_frac']*P['dose_budget_msv'] else 'green'
            wps.append({'id': p.get('id'), 'lat': p['lat'], 'lon': p['lon'], 'arrive_h': round(arrive_t/3600, 3), 'dose_msv': round(leave_d, 4), 'return_time_h': None if ret_t > 1e17 else round(ret_t/3600, 3),
                        'return_dose_msv': round(ret_d, 4), 'dose_margin_msv': round(margin, 4), 'status': st, 'local_dose_rate_msv_h': round(here_rate, 4),
                        'instruction': 'RETURN NOW' if st == 'red' else 'Monitor dose, plan return' if st == 'amber' else 'Proceed'})
        rr, cc = path[-1]; ret_final = float(T[rr, cc])/3600; total_h = t/3600+stay_t/3600+ret_final
        crew = P['crew']; res = 1+P['consumable_reserve_frac']
        ms = float(np.mean(slopes)); mr = float(np.mean(rough)); mu = float(np.mean(ucs))
        diff = 10*(0.5*min(ms/P['slope_limit_deg'], 1)+0.3*min(mr/5.0, 1)+0.2*min(max(mu-1, 0), 1))
        return {'coordinates': coords, 'waypoints': wps, 'distance_km': round(dist/1000, 3), 'climb_m': round(climb), 'descent_m': round(desc),
                'walk_time_h': round(t/3600, 2), 'stay_time_h': round(stay_t/3600, 2), 'return_time_h': round(ret_final, 2), 'total_eva_h': round(total_h, 2),
                'dose_outbound_msv': round(float(dose+stay_d), 4), 'dose_total_msv': round(float(dose+stay_d+D[rr, cc]), 4), 'max_slope_deg': round(max(slopes), 1), 'mean_slope_deg': round(ms, 1),
                'difficulty_0_10': round(diff, 1), 'difficulty_formula': '10 x (0.5 x mean slope/limit + 0.3 x mean roughness/5 deg + 0.2 x clip(mean unit cost - 1)) - derived hazard, ASSUMED weights',
                'consumables': {'o2_kg': round(crew*P['o2_kg_per_person_h']*total_h*res, 2), 'water_kg': round(crew*P['water_kg_per_person_h']*total_h*res, 2), 'power_kwh': round(crew*P['power_w_per_person']*total_h*res/1000, 2), 'basis': 'ASSUMPTION rates x crew x total EVA hours x (1+reserve)'},
                'worst_status': 'red' if any(w['status'] == 'red' for w in wps) else 'amber' if any(w['status'] == 'amber' for w in wps) else 'green'}

    def pov_patch(self, lat, lon, radius_m=1600.0):
        r, c = self.rc(lat, lon); n = int(radius_m/self.px); r0, c0 = int(r)-n, int(c)-n
        if r0 < 0 or c0 < 0 or r0+2*n+1 > self.H or c0+2*n+1 > self.W: return {'error': True, 'detail': 'outside DEM'}
        z = self.dem[r0:r0+2*n+1, c0:c0+2*n+1]; zc = float(np.nanmedian(z)); z = np.where(np.isnan(z), zc, z)
        return {'label': f'synthetic view from {RES_LABEL} DEM', 'cell_m': self.px, 'n': 2*n+1, 'center_index': n, 'ground_m': round(float(self.dem[int(r), int(c)]), 1), 'z': np.round(z, 1).tolist()}
