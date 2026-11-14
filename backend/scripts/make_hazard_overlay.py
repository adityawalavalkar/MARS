"""Derived-hazard overlay PNG (default weights) from the shipped jezero_analysis.npz.
DERIVED hazard = (1 + (slope/limit)^2 + roughness/5 deg) x ASSUMED unit cost. NOT measured rock abundance.
Run: python backend/scripts/make_hazard_overlay.py"""
import json, numpy as np, matplotlib
from PIL import Image
d = np.load('data/processed/jezero/jezero_analysis.npz'); s = np.where(d['slope'] == 255, np.nan, d['slope']/2.0); r = np.where(d['rough'] == 255, np.nan, d['rough']/8.0)
cfg = json.load(open('data/config/unit_hazard_costs.json')); lim = cfg['slope_limit_deg_suit']['value']
uc = np.array([cfg['surface_unit_cost'].get(str(n), 1.0) for n in d['unit_names']], 'float32')[d['unit']]
h = (1+(s/lim)**2+r/5.0)*uc; n = np.clip((h-1.0)/3.0, 0, 1)          # 1 (easy) .. 4 (hard)
o = (matplotlib.colormaps['YlOrRd'](n)*255).astype('uint8'); o[..., 3] = np.where(np.isnan(h), 0, (40+170*n)).astype('uint8')
im = Image.fromarray(o); im = im.resize((im.width//3, im.height//3), Image.BILINEAR); im.save('frontend/public/jezero/hazard.png', optimize=True)
print('hazard.png', im.size, 'p50/p95 index', float(np.nanpercentile(h, 50)), float(np.nanpercentile(h, 95)))
