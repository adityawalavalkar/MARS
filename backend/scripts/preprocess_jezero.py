"""Jezero preprocessing (20 m CTX DEM). Run: python backend/scripts/preprocess_jezero.py --raw <dir with uploads> --geo <shp dir> --nom <nomenclature dir>
Outputs -> data/processed/jezero/ and frontend/public/jezero/ (overlays + manifest).
CRS handling (sphere R=3396190 m, east longitude):
  DEM: equirectangular, std parallel 18.4663  -> lon=x/(R cos(phi0)), lat=y/R
  TI, CRISM, geology: std parallel 0           -> lon=x/R, lat=y/R
"""
import argparse, json, os, math
import numpy as np, rasterio, shapefile
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
R = 3396190.0; PHI0 = math.radians(18.4663); KX = R*math.cos(PHI0)
ap = argparse.ArgumentParser()
ap.add_argument('--raw', default='/mnt/user-data/uploads'); ap.add_argument('--geo', default='/home/claude/w/geo')
ap.add_argument('--nom', default='/home/claude/w/nom'); ap.add_argument('--cfg', default='data/config')
ap.add_argument('--out', default='data/processed/jezero'); ap.add_argument('--pub', default='frontend/public/jezero')
ap.add_argument('--mesh', type=int, default=512); a = ap.parse_args()
os.makedirs(a.out, exist_ok=True); os.makedirs(a.pub, exist_ok=True)
OV_DOWN = 3  # display overlays are downsampled (analysis rasters stay at 20 m)
def png(arr, path, down=1):
    im = Image.fromarray(arr)
    if down > 1: im = im.resize((im.width//down, im.height//down), Image.BILINEAR if arr.shape[-1] == 4 else Image.NEAREST)
    im.save(path, optimize=True)
man = {'dem_label': '20 m CTX terrain (M20_JezeroCrater_CTXDEM_20m)'}

# ---------- 1. DEM ----------
with rasterio.open(f'{a.raw}/M20_JezeroCrater_CTXDEM_20m.tif') as d:
    z = d.read(1).astype('float64'); T = d.transform; nod = d.nodata
mask = ~np.isfinite(z) | (z < -1e30) | (z <= nod*0.99 if nod else False)
z[mask] = np.nan; H, W = z.shape; px = 20.0
x0, y0 = T.c, T.f
lon_w, lon_e = x0/KX, (x0+W*px)/KX; lat_n, lat_s = y0/R, (y0-H*px)/R
rad2d = 180/math.pi
B = [lat_s*rad2d, lon_w*rad2d, lat_n*rad2d, lon_e*rad2d]  # S,W,N,E
man['overlay_downsample'] = OV_DOWN
man['dem'] = {'shape': [H, W], 'pixel_m': px, 'bounds_swne': B, 'z_min': float(np.nanmin(z)), 'z_max': float(np.nanmax(z)), 'z_median': float(np.nanmedian(z)), 'nodata_frac': float(mask.mean())}
zf = np.where(mask, np.nanmedian(z), z)  # fill only for filters; mask re-applied after
def horn(zf):
    p = np.pad(zf, 1, mode='edge')
    dzdx = ((p[:-2,2:]+2*p[1:-1,2:]+p[2:,2:])-(p[:-2,:-2]+2*p[1:-1,:-2]+p[2:,:-2]))/(8*px)
    dzdy = ((p[2:,:-2]+2*p[2:,1:-1]+p[2:,2:])-(p[:-2,:-2]+2*p[:-2,1:-1]+p[:-2,2:]))/(8*px)  # + = south higher (row down)
    return dzdx, dzdy
dzdx, dzdy = horn(zf)
slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
aspect = (np.degrees(np.arctan2(-dzdx, dzdy)) % 360)  # downslope azimuth, deg clockwise from N
az, alt = math.radians(315), math.radians(45); sl = np.arctan(np.hypot(dzdx, dzdy)); asp = np.arctan2(dzdy, -dzdx)
hs = np.clip(math.sin(alt)*np.cos(sl) + math.cos(alt)*np.sin(sl)*np.cos(az-asp), 0, 1)
m3 = ndi.uniform_filter(slope, 3); rough = np.sqrt(np.maximum(ndi.uniform_filter(slope**2, 3)-m3**2, 0))  # std of slope, 3x3
bad = ndi.binary_dilation(mask, iterations=1)  # edge pixels touching nodata are unreliable
for arr in (slope, aspect, hs, rough): arr[bad] = np.nan
np.save(f'{a.out}/dem_z.npy', z.astype('float32')); np.save(f'{a.out}/slope_deg.npy', slope.astype('float32'))
np.save(f'{a.out}/roughness.npy', rough.astype('float32')); np.save(f'{a.out}/aspect_deg.npy', aspect.astype('float32'))
man['slope_stats_deg'] = {'median': float(np.nanmedian(slope)), 'p95': float(np.nanpercentile(slope, 95)), 'max': float(np.nanmax(slope))}
rgba = np.zeros((H, W, 4), 'uint8'); g = np.nan_to_num(hs*255).astype('uint8'); rgba[..., :3] = g[..., None]; rgba[..., 3] = np.where(np.isnan(hs), 0, 255)
png(rgba, f'{a.pub}/hillshade.png', OV_DOWN)
import matplotlib; matplotlib.use('Agg'); from matplotlib import cm
def cmap_png(arr, vmin, vmax, name, path, down=1):
    n = np.clip((arr-vmin)/(vmax-vmin), 0, 1); o = (matplotlib.colormaps[name](np.nan_to_num(n))*255).astype('uint8'); o[..., 3] = np.where(np.isnan(arr), 0, 255); png(o, path, down)
cmap_png(slope, 0, 30, 'magma', f'{a.pub}/slope.png', OV_DOWN); cmap_png(z, -3505, -476, 'terrain', f'{a.pub}/elevation.png', OV_DOWN)
# coarse 3D mesh (block-mean, NaN-aware)
M = a.mesh; ys = np.linspace(0, H, M+1).astype(int); xs = np.linspace(0, W, M+1).astype(int)
mesh = np.array([[np.nanmean(z[ys[i]:ys[i+1], xs[j]:xs[j+1]]) if np.isfinite(z[ys[i]:ys[i+1], xs[j]:xs[j+1]]).any() else np.nan for j in range(M)] for i in range(M)])
mesh = np.where(np.isnan(mesh), np.nanmin(z), mesh)
json.dump({'label': '512x512 mesh of 20 m CTX DEM (block mean). Elevations in metres; vertical exaggeration is applied in the frontend (VERT_EXAG constant).', 'rows': M, 'cols': M, 'bounds_swne': B, 'width_m': W*px, 'height_m': H*px, 'z_min': float(mesh.min()), 'z_max': float(mesh.max()), 'z': np.round(mesh, 1).tolist()}, open(f'{a.out}/jezero_terrain_mesh_20m.json', 'w'))
def lonlat_to_rc(lon, lat): return (y0-math.radians(lat)*R)/px, (math.radians(lon)*KX-x0)/px

# ---------- 2. Thermal inertia ----------
with rasterio.open(f'{a.raw}/Jezero_Thermal_Inertia_v1.tiff') as d:
    ti = d.read(1).astype('float64'); Tt = d.transform
ti[(ti == 0) | ~np.isfinite(ti)] = np.nan; h, w = ti.shape
tb = [math.degrees((Tt.f-h*100)/R), math.degrees(Tt.c/R), math.degrees(Tt.f/R), math.degrees((Tt.c+w*100)/R)]
cmap_png(ti, 42, 600, 'viridis', f'{a.pub}/thermal_inertia.png')
man['thermal_inertia'] = {'bounds_swne': tb, 'unit': 'J m-2 K-1 s-0.5', 'valid_min': float(np.nanmin(ti)), 'valid_max': float(np.nanmax(ti)), 'median': float(np.nanmedian(ti)), 'colour_range': [42, 600], 'note': 'Display only. Colour stretch clipped at 600 for contrast. Not used for hazard.'}

# ---------- 3. CRISM ----------
KEY = {'Olivine': ((255,0,0),(153,0,0)), 'Mg-carbonate': ((0,255,0),(0,153,0)), 'Fe/Mg-smectite': ((0,255,255),(0,153,153)),
 'Olivine+smectite': ((255,128,114),(153,77,68)), 'Olv.smect+2.2um': ((128,128,0),(77,77,0)), 'Carb.+2.2um': ((255,215,0),(153,129,0)),
 'High-Ca pyroxene': ((255,128,0),(153,77,0)), 'Low-Ca pyroxene': ((218,165,32),(130,99,19)), 'Kaolinite': ((139,69,19),(83,41,11)), 'Mg-smectite 2': ((0,0,255),(0,0,153))}
names = list(KEY); pal = np.array([c for n in names for c in KEY[n]], float)  # 20 entries: [class*2 + conf]
with rasterio.open(f'{a.raw}/jezeroFinal.tif') as d:
    rgb = np.moveaxis(d.read(), 0, -1).astype(float); Tc = d.transform
ch, cw = rgb.shape[:2]; flat = rgb.reshape(-1, 3); black = (flat.sum(1) == 0)
idx = np.zeros(len(flat), int); 
for s in range(0, len(flat), 200000): idx[s:s+200000] = np.argmin(((flat[s:s+200000, None, :]-pal[None])**2).sum(2), 1)
cls = (idx//2).reshape(ch, cw); conf = (idx % 2).reshape(ch, cw); bk = black.reshape(ch, cw); cls[bk] = -1
out = np.zeros((ch, cw, 4), 'uint8'); ok = ~bk; out[ok, :3] = pal[idx.reshape(ch, cw)[ok]].astype('uint8'); out[ok, 3] = 255
png(out, f'{a.pub}/crism_minerals.png'); np.save(f'{a.out}/crism_class.npy', cls.astype('int8')); np.save(f'{a.out}/crism_conf.npy', conf.astype('int8'))
cb = [math.degrees((Tc.f-ch*36)/R), math.degrees(Tc.c/R), math.degrees(Tc.f/R), math.degrees((Tc.c+cw*36)/R)]
man['crism'] = {'label': 'preliminary mineral attribution (Parente/Itoh/Saranathan CRISM map)', 'bounds_swne': cb, 'classes': [{'name': n, 'high_conf_rgb': KEY[n][0], 'medium_conf_rgb': KEY[n][1], 'pixel_count': int((cls == i).sum())} for i, n in enumerate(names)], 'unidentified_frac': float(bk.mean()), 'note': 'Black = unidentified (transparent). Classes assigned by nearest key colour.'}

# ---------- 4. Geology ----------
gp = [f for f in os.listdir(a.geo) if f.endswith('.shp')][0]; sr = shapefile.Reader(f'{a.geo}/{gp}', encoding='utf-8')
def dp(pts, eps):  # Douglas-Peucker (iterative-safe via recursion; rings are small)
    if len(pts) < 3: return pts
    A = np.asarray(pts, float); v = A[-1]-A[0]; n = np.hypot(*v); d = A[1:-1]-A[0]
    dd = np.abs(v[0]*d[:, 1]-v[1]*d[:, 0])/n if n else np.hypot(d[:, 0], d[:, 1])
    k = int(np.argmax(dd))
    if dd[k] > eps: return dp(pts[:k+2], eps)[:-1] + dp(pts[k+1:], eps)
    return [pts[0], pts[-1]]
feats = []; SURF = json.load(open(f'{a.cfg}/unit_hazard_costs.json'))['surface_unit_cost']
surf_names = list(SURF.keys()); sid = np.zeros((H, W), 'uint8'); canvas = Image.fromarray(sid); dr = ImageDraw.Draw(canvas)
order = {n: i for i, n in enumerate(surf_names)}
class _SR:  # shape+record, tolerant of null/empty geometries in the source file
    def __init__(s_, shape, record): s_.shape, s_.record = shape, record
recs = []; skipped = 0
for i_ in range(len(sr)):
    try: shp = sr.shape(i_)
    except Exception: skipped += 1; continue
    if not shp.points: skipped += 1; continue
    recs.append(_SR(shp, sr.record(i_)))
print('geology polygons read', len(recs), 'skipped empty', skipped)
# paint larger surface classes first (aeolian/talus last) so higher-cost cover wins overlaps
recs_sorted = sorted(recs, key=lambda r: SURF.get((r.record['SurfUName'] or '').strip(), 1.0))
for sh in recs_sorted:
    s = (sh.record['SurfUName'] or '').strip(); pts = sh.shape.points; parts = list(sh.shape.parts)+[len(pts)]
    for k in range(len(parts)-1):
        ring = pts[parts[k]:parts[k+1]]; rc = [(lonlat_to_rc(math.degrees(px_/R), math.degrees(py_/R))) for px_, py_ in ring]
        if s in order and len(rc) > 2: dr.polygon([(c, r) for r, c in rc], fill=order[s])
for sh in recs:
    pts = sh.shape.points; parts = list(sh.shape.parts)+[len(pts)]; rings = []
    for k in range(len(parts)-1):
        ring = [[math.degrees(x/R), math.degrees(y/R)] for x, y in pts[parts[k]:parts[k+1]]]
        ring = dp(ring, 2e-5)  # ~1.2 m tolerance
        if len(ring) >= 4: rings.append([[round(u, 5), round(v, 5)] for u, v in ring])
    if rings: feats.append({'type': 'Feature', 'properties': {'quadname': sh.record['quadname'], 'SurfUName': (sh.record['SurfUName'] or '').strip(), 'BedrkUName': (sh.record['BedrkUName'] or '').strip()}, 'geometry': {'type': 'Polygon', 'coordinates': rings}})
json.dump({'type': 'FeatureCollection', 'name': 'Stack et al. 2020 Jezero photogeologic map (Mars 2020 Science Team)', 'features': feats}, open(f'{a.pub}/geology_units.geojson', 'w'))
sid = np.array(canvas); np.save(f'{a.out}/surface_unit_id.npy', sid)
cost_tab = np.array([SURF[n] for n in surf_names], 'float32'); np.save(f'{a.out}/unit_cost_raster.npy', cost_tab[sid])
man['geology'] = {'features': len(feats), 'surface_unit_index': surf_names, 'painted_frac': float((sid > 0).mean()), 'note': 'Unit cost raster uses ASSUMED costs from data/config/unit_hazard_costs.json. Derived hazard, not measured rock abundance. Geology covers only ~77.22-77.56E, 18.32-18.62N; outside it cost=1.0 (unmapped).'}

# ---------- 5. Nomenclature ----------
nr = shapefile.Reader(f'{a.nom}/MARS_nomenclature_center_pts.shp', encoding='utf-8'); keep = ('Planitia', 'Planum', 'Terra', 'Mons', 'Chasma', 'Vallis', 'Fossa')
JEZ = {'Jezero', 'Belva', 'Hartwell', 'Neretva Vallis', 'Sava Vallis'}; nom = []
for rec in nr.records():
    t, n, lo, la, dm = rec['type'], rec['clean_name'], rec['center_lon'], rec['center_lat'], rec['diameter']
    local = n in JEZ and 76 <= lo <= 79 and 17.5 <= la <= 19.6
    big = any(t.startswith(k) for k in keep) and (dm or 0) >= 150 and 0 <= lo <= 90 and 0 <= la <= 44
    if local or big: nom.append({'name': n, 'type': t.split(',')[0], 'lon': round(lo, 4), 'lat': round(la, 4), 'diameter_km': round(dm, 1), 'tier': 'local' if local else 'regional'})
json.dump({'source': 'IAU/USGS Gazetteer of Planetary Nomenclature, MARS_nomenclature_center_pts (plain sphere, lon 0-360E)', 'features': nom}, open(f'{a.pub}/nomenclature.json', 'w'), ensure_ascii=False, indent=0)
man['nomenclature_count'] = len(nom)

# ---------- 6. Science targets + nearest CRISM ----------
cfg = json.load(open(f'{a.cfg}/science_targets.json')); cl_px = 36.0
def crism_at(lon, lat):
    c = (math.radians(lon)*R-Tc.c)/36; r = (Tc.f-math.radians(lat)*R)/36; r0, c0 = int(r), int(c)
    if not (0 <= r0 < ch and 0 <= c0 < cw): return None, None, None
    best = None
    for rad in range(0, 40):
        sub = cls[max(0, r0-rad):r0+rad+1, max(0, c0-rad):c0+rad+1]; rr, cc = np.nonzero(sub >= 0)
        if len(rr):
            dd = np.hypot(rr+max(0, r0-rad)-r, cc+max(0, c0-rad)-c); k = int(np.argmin(dd)); best = (int(sub[rr[k], cc[k]]), float(dd[k]*cl_px)); break
    return (names[best[0]], best[1], 'at pixel' if best[1] < 18 else 'nearest identified pixel') if best else (None, None, None)
def dem_at(lon, lat):
    r, c = lonlat_to_rc(lon, lat); r, c = int(r), int(c); return float(z[r, c]) if 0 <= r < H and 0 <= c < W and np.isfinite(z[r, c]) else None
for t in cfg['targets']:
    n, dm, how = crism_at(t['lon'], t['lat']); t['crism_class'] = n; t['crism_distance_m'] = None if dm is None else round(dm); t['crism_match'] = how; t['dem_elev_m'] = dem_at(t['lon'], t['lat'])
cfg['start']['dem_elev_m'] = dem_at(cfg['start']['lon'], cfg['start']['lat'])
json.dump(cfg, open(f'{a.pub}/science_targets.json', 'w'), indent=1); json.dump(man, open(f'{a.pub}/manifest.json', 'w'), indent=1)
print(json.dumps({k: man[k] for k in ('dem', 'slope_stats_deg', 'thermal_inertia')}, indent=1)); print('geology', man['geology']['features'], 'painted', man['geology']['painted_frac'], 'nom', len(nom))
for t in cfg['targets']: print(t['id'], t['crism_class'], t['crism_distance_m'], t['dem_elev_m'])

# ---------- 7. Compact analysis cache for the backend router (shipped with the repo) ----------
dem_u16 = np.where(np.isnan(z), 65535, np.clip((z+3600)*10, 0, 65534)).astype('uint16')   # z = v/10 - 3600 m
slope_u8 = np.where(np.isnan(slope), 255, np.clip(slope*2, 0, 254)).astype('uint8')       # 0.5 deg steps
rough_u8 = np.where(np.isnan(rough), 255, np.clip(rough*8, 0, 254)).astype('uint8')       # 0.125 deg steps
np.savez_compressed(f'{a.out}/jezero_analysis.npz', dem=dem_u16, slope=slope_u8, rough=rough_u8, unit=sid,
                    unit_names=np.array(surf_names), origin=np.array([x0, y0, px, R, math.degrees(PHI0)]))
print('packed jezero_analysis.npz')
