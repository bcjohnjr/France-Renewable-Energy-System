"""Consistency tests for the V14 system extension.  Run: python -I model/test_system_v14.py"""
import math, sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import france_v12 as M
import system_v14 as S

checks = []
def ok(name, cond): checks.append((name, bool(cond))); print(('PASS ' if cond else 'FAIL ') + name)

inp = M.Inputs(); sy = S.Sys()
ev = S.evaluate(inp, sy)
v12 = M.national(inp)
rows = {(r['key'], r['option'], r['drones']): r for r in ev['rows']}
import json as _j, weather_v17 as WX
WSUM = {r['key']: r['cf_net'] for r in _j.loads((S.ROOT / 'weather_summary_v16.json').read_text())['results']}
ok('weather data present for all six hubs', WX.available())
for k_ in WX.KEYS:
    ok(f'{k_}: contract with zero wind equals the backup price', abs(WX.contract(k_, 70, 105, 40, 0.0)['price'] - 105) < 1e-12)
    mean, used, sur = WX.coverage_table(k_)
    ok(f'{k_}: wind used never exceeds load or output, and rises with contracted capacity', bool(np.all(used <= 1 + 1e-12) and np.all(used <= WX.R_GRID * mean + 1e-12) and np.all(np.diff(used) >= -1e-12)))
for s in M.SITES:
    k = s.key
    base = rows[(k, 'smr', False)]
    ok(f'{k}: SMR conventional fuel cost reproduces the V12 hub model', abs(base['fuel_eur_l'] - v12['sites'][k]['cascade']['fuel_cost_eur_l']) < 1e-9)
    ok(f'{k}: SMR conventional litres reproduce the V12 hub model', abs(base['litres'] - v12['sites'][k]['cascade']['fuel_litres']) < 1e-6)
    for (o, d) in S.OPTIONS:
        r = rows[(k, o, d)]
        comp = sum(r[f'{c}_eur_l'] for c in ('feedstock', 'harvest', 'electricity', 'heat', 'other'))
        ok(f'{k}/{o}{"+d" if d else ""}: cost components sum to the total', abs(comp - r['fuel_eur_l']) < 1e-9)
        ok(f'{k}/{o}{"+d" if d else ""}: no turbine anchors without turbines', (r['turbines'] == 0) == (r['anchor_cut_eur_t'] == 0))
    w = rows[(k, 'wind', True)]; h = rows[(k, 'hybrid', True)]; sd = rows[(k, 'smr', True)]
    ok(f'{k}: wind and hybrid hubs have turbines anchoring the whole farm', w['turbines'] == 25 and abs(w['anchored_frac'] - 1) < 1e-12)
    ok(f'{k}: anchor saving = cost x share x shared x (1 - interface)', abs(w['anchor_cut_eur_t'] - inp.p6.seaweed_dry_cost_eur_t * sy.anchor_cost_share * sy.anchor_shared_frac * (1 - sy.interface_frac)) < 1e-9)
    c = h['wind_contract']
    ok(f'{k}: weather contract never dearer than reactor power for the hybrid (r = 0 is allowed)', h['electricity_price_eur_MWh'] <= inp.p6.nuclear_electric_eur_MWh + 1e-9)
    ok(f'{k}: hourly balance closes (wind used + residual = load)', abs(c['used'] + c['residual'] - 1) < 1e-12 and c['surplus'] >= -1e-12)
    ok(f'{k}: contract cost identity', abs(c['r'] * c['cf'] * (c['contract_eur_MWh'] + sy.balancing_eur_MWh) - c['surplus'] * sy.surplus_value_eur_MWh + c['residual'] * c['backup_eur_MWh'] - c['price']) < 1e-9)
    ok(f'{k}: ERA5 capacity factor reproduces the downloaded summary', abs(h['wind_cf'] - WSUM[k]) < 5e-4)
    ok(f'{k}: wind-only hub backed by grid power at the grid price', abs(w['wind_contract']['backup_eur_MWh'] - inp.th.grid_buy_eur_MWh) < 1e-12)
    ok(f'{k}: hybrid never costs more than SMR with drones (same steam, cheaper or equal power, anchors)', h['fuel_eur_l'] <= sd['fuel_eur_l'] + 1e-12)
    ok(f'{k}: wind-only buys all HTL heat as electricity', w['heat_eur_l'] > rows[(k, 'smr', True)]['heat_eur_l'] or S.WIND[k][1] + sy.firming_eur_MWh < inp.p6.nuclear_electric_eur_MWh * inp.p6.nuclear_heat_opp_ratio)
    ops = h['ops']
    ok(f'{k}: Grid Harvester count covers the wet harvest', ops['harvesters'] == math.ceil(h['dry_t'] / sy.dm_frac / (sy.harvester_t_wet_h * sy.harvester_hours)))
    if ops['drones_per_km2'] > 0:
        marg = (ops['drone_benefit_eur'] / (1 - math.exp(-ops['drones_per_km2'] / sy.drone_rho0)) / 100) / sy.drone_rho0 * math.exp(-ops['drones_per_km2'] / sy.drone_rho0)
        ok(f'{k}: drone density sets marginal benefit = marginal cost', abs(marg - ops['drone_unit_cost_eur_y']) < 1e-6)
    ok(f'{k}: marine fuel falls with harvester and drones', ops['fleet_fuel_MWh'] < ops['fleet_fuel_MWh_conv'])
    ok(f'{k}: marine CO2 = fuel x emission factor', abs(ops['fleet_co2_t'] - ops['fleet_fuel_MWh'] * 3.6 * sy.marine_kgCO2_GJ / 1000) < 1e-9)
ers_v12 = M.ers_system(inp.e, 8850.0, inp.e.diesel_longrun_eur_l, float(np.mean([v12['sites'][s.key]['cascade']['fuel_cost_eur_l'] for s in M.SITES])), v12['fuel_litres'] / 6)
ok('ERS with SMR fuel price reproduces the V12 motorway result', abs(ev['ers_smr']['net_saving_bn_y'] - ers_v12['net_saving_bn_y']) < 1e-9)
ok('ERS net CO2 subtracts marine-operation emissions of the kelp fuel', abs(ev['ers_best']['co2_avoided_net_marine_Mt'] - (ev['ers_best']['co2_avoided_Mt'] - ev['ers_best']['marine_ops_Mt'])) < 1e-12 and ev['ers_best']['marine_ops_Mt'] > 0)
ok('cheaper kelp fuel raises the ERS saving', ev['ers_best']['net_saving_bn_y'] > ev['ers_smr']['net_saving_bn_y'])
# Monte Carlo inputs all active
base_out = S.evaluate(inp, sy)['national']['hybrid_d']['mean_eur_l']
for k, (obj, fld, lo, mo, hi) in S.MC.items():
    i2, s2, d2 = S.apply(inp, sy, None, obj, fld, hi)
    e2 = S.evaluate(i2, s2, d2)
    moved = abs(e2['national']['hybrid_d']['mean_eur_l'] - base_out) > 1e-9 or abs(e2['ers_best']['net_saving_bn_y'] - ev['ers_best']['net_saving_bn_y']) > 1e-9 \
        or any(abs(e2['national'][o]['mean_eur_l'] - ev['national'][o]['mean_eur_l']) > 1e-9 for o in ev['national'])
    ok(f'MC input {k} changes at least one output', moved)
# V16 additions
R14 = __import__('json').loads((S.D / 'v14_system_results.json').read_text()); dc = R14['hybrid_decomposition']
ok('decomposition closes: SMR+drones + electricity + anchors = combined', abs(dc['smr_d'] + dc['electricity_effect'] + dc['anchor_effect'] - dc['hybrid']) < 1e-12)
ok('anchor sharing is the larger part of the combined-option advantage', dc['anchor_share'] > 0.5)
ok('without anchors, wind delivery charges of 1-60 EUR/MWh erase the electricity advantage', 1 < dc['delivery_breakeven_no_anchor'] < 60)
ok('delivery charges raise wind and combined fuel cost', R14['sensitivity']['delivery_30']['hybrid_d'] > R14['sensitivity']['delivery_15']['hybrid_d'] > ev['national']['hybrid_d']['mean_eur_l'])
J = R14['ers_joint']
ok('joint grid: central cell reproduces the motorway saving', abs(next(j['saving_bn'] for j in J if j['capex_mult'] == 1.0 and j['capture_mult'] == 1.0) - ev['ers_best']['net_saving_bn_y']) < 1e-9)
G = {(j['capex_mult'], j['capture_mult']): j['saving_bn'] for j in J}
ok('joint grid: saving falls with catenary capital at every capture level', all(G[(a, c)] > G[(b, c)] for c in (1.0, .9, .8, .7) for a, b in ((1.0, 1.2), (1.2, 1.4), (1.4, 1.6))))
ok('joint grid: saving falls with lower capture at every capital level', all(G[(m, a)] > G[(m, b)] for m in (1.0, 1.2, 1.4, 1.6) for a, b in ((1.0, .9), (.9, .8), (.8, .7))))
ok('joint grid: +40 % capital and -20 % capture turns the saving negative', next(j['saving_bn'] for j in J if j['capex_mult'] == 1.4 and j['capture_mult'] == 0.8) < 0)
ok('capital break-even multiplier above 1', R14['ers_capex_breakeven_mult'] > 1)
nf = sum(not c for _, c in checks)
print(f'{len(checks) - nf}/{len(checks)} checks passed')
sys.exit(1 if nf else 0)
