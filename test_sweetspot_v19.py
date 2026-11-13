"""Consistency tests for the V19 national model.  Run: python -I model/test_sweetspot_v19.py"""
import json, sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import france_v12 as M
import system_v14 as S
import sweetspot_v19 as W

checks = []
def ok(name, cond): checks.append((name, bool(cond))); print(('PASS ' if cond else 'FAIL ') + name)

inp = M.Inputs(); sy = S.Sys(); n = W.Nat(); e = inp.e
R = json.loads((W.D / 'v19_sweetspot_results.json').read_text())
kelp = W.kelp_tiers(inp, sy, n); ev = S.evaluate(inp, sy); tiers = W.supply_curve(n, kelp, sy=sy); A, Mar = W.base_litres(n)
P, F, PO = R['policy'], R['full'], R['pooled']

# --- mandates as step functions
ok('ReFuelEU SAF steps: 2039 = 20 %, 2040-2044 = 34 %', W.mandate(W.REFUEL, 2039) == .20 and W.mandate(W.REFUEL, 2041) == .34 and W.mandate(W.REFUEL, 2044) == .34)
ok('ReFuelEU synthetic minima (Annex I): 0.7 % 2030-31, 1.2 % 2032-33, 2 % 2034, 5 % 2035, 10 % 2040', [W.mandate(W.SYNTH_MIN, y) for y in (2030, 2031, 2032, 2033, 2034, 2035, 2040, 2041)] == [.007, .007, .012, .012, .02, .05, .10, .10])
SP = {y: W.synth_share(n, y) for y in range(2027, 2042)}
ok('synthetic path never below the annual minimum', all(SP[y] >= W.mandate(W.SYNTH_MIN, y) - 1e-12 for y in SP))
for yrs, avg in W.SYNTH_PERIODS:
    Ay = {y: W.base_litres(n, y)[0] for y in yrs}
    ok(f'synthetic path meets the {yrs[0]}-{yrs[-1]} volume-weighted average of {avg:.1%}', abs(sum(SP[y] * Ay[y] for y in yrs) / sum(Ay.values()) - avg) < 1e-12)
ok('flat schedule (period average every year) is a compliant but dearer path', R['transition_flat_synth_cost_bn'] >= R['transition_cost_bn'] - 1e-9)
ok('synthetic low-carbon e-fuel meets the 70 % lifecycle-savings threshold', R['lc_gCO2_MJ'] <= (1 - n.lc_saving_min) * n.fossil_comparator_g_MJ)
ok('FuelEU steps: 2041 = 31 %', W.mandate(W.FUELEU, 2041) == .31)
ok('2024 split sums to ~147 Mt', 145.5 < n.co2_passenger_land + n.co2_freight_land + n.co2_aviation + n.co2_maritime < 147.5)
# --- kelp tiers reproduce the weather-based hub model
for s in M.SITES:
    t = next(t for t in kelp if t['name'] == f'kelp_{s.key}'); r = next(r for r in ev['rows'] if r['key'] == s.key and r['option'] == 'hybrid' and r['drones'])
    ok(f'{s.key}: kelp tier = weather-based hybrid hub fuel cost', abs(t['price'] - r['fuel_eur_l']) < 1e-12 and abs(t['cap'] - 6 * r['litres']) < 1e-6)
# --- truck model
h0 = W.hgv(n, e, 0.0, 0.0, 0.0)
ok('no network, no batteries: all truck-km on the generator', abs(float(h0['gen_share']) - 1) < 1e-12)
hh = W.hgv(n, e, np.array([0, 4000, 8000, 12000.]), 300.0, np.full(4, 300.0))
ok('generator share falls with network length', np.all(np.diff(hh['gen_share']) < 0))
ok('regional trucks do not use the wire (their generator share is independent of network length)', np.allclose(hh['gen_share_r'], hh['gen_share_r'][0]))
hb = W.hgv(n, e, 6000.0, np.array([100, 300, 600.]), np.array([100, 300, 600.]))
ok('generator share falls with both batteries', np.all(np.diff(hb['gen_share']) < 0))
ok('class shares recombine to the fleet share', np.allclose(hb['gen_share'], (1 - n.regional_share) * hb['gen_share_lh'] + n.regional_share * hb['gen_share_r']))
ok('non-fuel cost = infrastructure + vehicles + energy', np.allclose(hb['nonfuel'], hb['infra'] + hb['vehicles'] + hb['energy']))
ok('long-haul wire share never exceeds the cap', float(W.hgv(n, e, 1e6, 0, 0)['wire_share_lh']) <= n.max_lh_capture * e.on_wire_share + 1e-12)
# --- fuel LP
lp = W.lp_fuels(n, tiers, A, Mar, 0.5e9, .34, .10, .31)
q = lp['q']
ok('LP: SAF minimum met', lp['use']['jet'] >= .34 * A - 1)
ok('LP: synthetic minimum met by RFNBO or certified low-carbon e-jet (central case)', sum(v for (p, u), v in q.items() if u == 'jet' and p.startswith('efuel_')) >= .10 * A - 1)
lpR = W.lp_fuels(replace(n, lc_counts_synthetic=False), tiers, A, Mar, 0.5e9, .34, .10, .31)
ok('LP: RFNBO-only scenario meets the synthetic minimum with RFNBO jet', sum(v for (p, u), v in lpR['q'].items() if u == 'jet' and p.startswith('efuel_rf')) >= .10 * A - 1)
ok('LP: RFNBO-only procurement never cheaper than the central case', lpR['cost'] >= lp['cost'] - 1)
gc = {}
for t in tiers: gc.update(t.get('groups', {}))
for g, cap in gc.items():
    used = sum(sum(q[(t['name'], u)] for u in W.USES) for t in tiers if g in t.get('groups', {}))
    ok(f'LP: shared cap {g} respected', used <= cap + 1)
RS = W.rfnbo_sites(n, sy)
ok('RFNBO: hourly matching lowers electrolyser utilisation below the baseload reference at every coast', all(r['utilisation'] < n.u_ref for r in RS))
ok('RFNBO: hourly-matched e-fuel dearer than baseload low-carbon e-fuel (same CO2 source)', all(r['price'] > n.efuel_kWh_l * n.efuel_el_eur_MWh / 1000 + n.efuel_capex_eur_l for r in RS))
ok('RFNBO: utilisation equals the ERA5 coverage at the chosen contract', all(abs(r['utilisation'] - S.WX.coverage_table(r['key'])[1][list(S.WX.R_GRID).index(r['r'])]) < 1e-9 for r in RS))
ok('RFNBO import backstop priced above every domestic RFNBO tier', next(t for t in tiers if t['name'] == 'efuel_rf_import')['price'] > max(t['price'] for t in tiers if t['kind'] == 'efuel_rf' and t['name'] != 'efuel_rf_import'))
ok('RFNBO-only procurement adds a synthetic premium and raises liquid cost', R['rfnbo_only_sensitivity']['marginal_synth'] > P['marginal_synth'] and R['rfnbo_only_sensitivity']['liquid_cost_bn'] > P['liquid_cost_bn'])
ok('RFNBO-only transition costs more than the central transition', R['transition_rfnbo_only_cost_bn'] > R['transition_cost_bn'])
ok('LP: no kelp HTL in jet (no ASTM annex)', all(v < 1 for (p, u), v in q.items() if u == 'jet' and p.startswith('kelp')))
for t in tiers:
    tot = sum(q[(t['name'], u)] for u in W.USES)
    ok(f"LP: {t['name']} within supply cap", tot <= min(t['cap'], 1e14) + 1)
    f = {'hefa': n.jet_frac_hefa, 'kelp': n.jet_frac_kelp}.get(t['kind'], n.jet_frac_efuel)
    ok(f"LP: {t['name']} jet fraction respected", q[(t['name'], 'jet')] <= f * tot + 1)
red = sum(q[(t['name'], 'mar')] * (n.fueleu_ref_g_MJ - t['kg'] * 1000 / W.MJ_L) for t in tiers) / (n.fueleu_ref_g_MJ * Mar)
ok('LP: FuelEU intensity reduction met (>= 31 %)', red >= .31 - 1e-6)
ok('LP: road requirement met', lp['use']['road'] >= 0.5e9 - 1)
lpA = W.lp_fuels(n, tiers, A, Mar, 0.5e9, .34, .10, .31); lpB = W.lp_fuels(n, tiers, A, Mar, 0.6e9, .34, .10, .31)
ok('LP: road dual equals the incremental cost of road fuel', abs((lpB['cost'] - lpA['cost']) / 0.1e9 - lpA['marginal_road']) < 0.02 or abs((lpB['cost'] - lpA['cost']) / 0.1e9 - lpB['marginal_road']) < 0.02)
fc, g, cst = W.lp_cost_fn(n, tiers, A, Mar, .34, .10, .31)
ok('LP cost is convex in truck demand', np.all(np.diff(np.diff(cst)) > -1e-3 * np.abs(cst).max()))
ok('the fuel-specific model needs at least the mandated SAF and marine volumes', P['liquid_total_GL'] >= .34 * A / 1e9 + .31 * Mar / 1e9 - 1e-6)
HS = R['hub_scan']
ok('kelp build size is the cost minimum of the scan', R['hubs_best'] == min(HS, key=lambda r: r['cost_bn'])['hubs'] and R['hub_start_best'] == min(HS, key=lambda r: r['cost_bn'])['start'])
ok('hub scan covers every integer 0-36 under both commissioning schedules', sorted((r['start'], r['hubs']) for r in HS) == sorted((s_, float(h_)) for s_ in ('wind_first', 'smr_first') for h_ in range(37)))
KW = W.kelp_tiers(inp, sy, n, option='wind')
for s in M.SITES:
    t = next(t for t in KW if t['name'] == f'kelp_{s.key}'); r = next(r for r in ev['rows'] if r['key'] == s.key and r['option'] == 'wind' and r['drones'])
    ok(f'{s.key}: wind-only tier = weather-based wind-only hub cost', abs(t['price'] - r['fuel_eur_l']) < 1e-12)
ok('pricing early hubs as wind-only raises transition cost', R['transition_cost_bn'] >= R['transition_hybrid_early_cost_bn'] - 1e-9 or R['early_kelp_wind_GL'] == 0)
ok('at central costs building 28 hubs costs more than the chosen build', R['transition_28hubs_cost_bn'] > R['transition_cost_bn'])
ok('with all cost levers the optimal build is larger than at central costs', R['hubs_best_optimised'] > R['hubs_best'])
# --- sweet spot
best, surf, _ = W.sweet_spot(n, e, fc)
ok('reported policy design is the grid minimum', abs(best['total'] - P['design']['total']) < 1 and best['L'] == P['design']['L'])
ok('policy optimum interior in all three dimensions', 0 < P['design']['L'] < W.L_GRID[-1] and 0 < P['design']['B'] < W.B_GRID[-1] and 0 < P['design']['B_r'] < W.BR_GRID[-1])
ok('policy optimum beats diesel trucks', P['hgv_saving_bn'] > 0)
ok('the network adds value over battery-only trucks', P['ers_value_bn'] > 0)
ok('full decarbonisation needs more renewable liquid than the policy case', F['liquid_total_GL'] > P['liquid_total_GL'])
sw = R['sweep']
ok('fixed-price sweep: generator share falls as the liquid price rises', all(b['gen_share'] <= a['gen_share'] + 1e-12 for a, b in zip(sw, sw[1:])))
# --- off-wire legs (referee)
LG = {(l['leg_min_km'], l['regional_leg_km']): l for l in R['offwire_legs']}
ok('longer long-haul legs never enlarge the network', all(LG[(b, r)]['L'] <= LG[(a, r)]['L'] for r in (150, 250, 350) for a, b in ((40, 60), (60, 90), (90, 120), (120, 160), (160, 200))))
ok('longer legs never raise the saving', all(LG[(b, r)]['hgv_saving_bn'] <= LG[(a, r)]['hgv_saving_bn'] + 1e-9 for r in (150, 250, 350) for a, b in ((40, 60), (60, 90), (90, 120), (120, 160), (160, 200))))
ok('central leg cell reproduces the policy design', LG[(60, 250)]['L'] == P['design']['L'])
ok('electrification still beats diesel at 200 km legs and 350 km regional duty', LG[(200, 350)]['hgv_saving_bn'] > 0)
# --- joint sensitivity
JG = {(j['capex_mult'], j['capture_mult']): j for j in R['joint_sensitivity']}
ok('joint grid: network never grows with catenary cost', all(JG[(b, c)]['L'] <= JG[(a, c)]['L'] for c in (1.0, .9, .8, .7) for a, b in ((1.0, 1.2), (1.2, 1.4), (1.4, 1.6))))
ok('joint grid: saving falls with catenary cost', all(JG[(b, c)]['hgv_saving_bn'] < JG[(a, c)]['hgv_saving_bn'] for c in (1.0, .9, .8, .7) for a, b in ((1.0, 1.2), (1.2, 1.4), (1.4, 1.6))))
# --- levers
KL, EL = R['kelp_levers'], R['efuel_levers']
ok('every kelp lever lowers the price', all(r['delta'] < 0 for r in KL['levers']))
ok('every e-fuel lever lowers the price', all(r['delta'] < 0 for r in EL['levers']))
ok('kelp base = litre-weighted weather-based hybrid mean', abs(KL['base'] - W.kelp_mean_price(inp, sy)) < 1e-12)
ok('all kelp levers together beat the best single lever', KL['all'] < KL['base'] + KL['levers'][0]['delta'])
# --- transition
T = R['transition']
ok('transition covers 2027-2041', [t['year'] for t in T] == list(range(2027, 2042)))
ok('network ends at the sweet spot and never shrinks', all(b['ers_km'] >= a['ers_km'] for a, b in zip(T, T[1:])) and abs(T[-1]['ers_km'] - P['design']['L']) < 1e-6)
ok('segment CO2 sums to total', all(abs(t['co2_ldv'] + t['co2_hgv'] + t['co2_aviation'] + t['co2_maritime'] - t['co2_total']) < 1e-9 for t in T))
ok('SAF meets the ReFuelEU step every year', all(t['jet_GL'] >= t['saf_share'] * A / 1e9 - 1e-6 for t in T))
ok('supply mix covers mandated uses every year', all(abs(t['hefa_GL'] + t['kelp_GL'] + t['efuel_GL'] - t['renewable_GL']) < 1e-6 for t in T))
ok('total transport CO2 falls every year', all(b['co2_total'] < a['co2_total'] for a, b in zip(T, T[1:])))
ok('2041 CO2 at least 40 % below 2024', T[-1]['co2_reduction_vs_2024'] > .40)
kmin, kmax = min(k['price'] for k in kelp), max(k['price'] for k in kelp)
wmin, wmax = min(k['price'] for k in KW), max(k['price'] for k in KW)
ok('built kelp hubs pay their fixed cost every year (hybrid prices from SMR start)', all((t['kelp_capacity_GL'] == 0 and t['kelp_fixed_cost_bn'] == 0) or (kmin * n.kelp_fixed_share - 1e-9 <= t['kelp_fixed_cost_bn'] / t['kelp_capacity_GL'] <= kmax * n.kelp_fixed_share + 1e-9) for t in T if t['year'] >= n.kelp_wind_only_until))
ok('hubs before the reactor enters service pay wind-only fixed costs', all(t['kelp_capacity_GL'] == 0 or (wmin * n.kelp_fixed_share - 1e-9 <= t['kelp_fixed_cost_bn'] / t['kelp_capacity_GL'] <= wmax * n.kelp_fixed_share + 1e-9) for t in T if t['year'] < n.kelp_wind_only_until))
ok('synthetic share in the transition follows the compliant path', all(abs(t['synthetic_share'] - SP[t['year']]) < 1e-12 for t in T))
ok('kelp utilisation within [0, 1]', all(0 <= t['kelp_utilisation'] <= 1 + 1e-9 for t in T))
ok('electricity split adds up', all(abs(t['ldv_TWh'] + t['hgv_TWh'] + t['rfnbo_TWh'] + t['lowcarbon_TWh'] - t['elec_TWh']) < 1e-6 for t in T))
# --- Monte Carlo
MQ = R['monte_carlo']
ok('Monte Carlo samples off-wire legs and regional duty', 'leg_min_km' in MQ['inputs'] and 'regional_leg_km' in MQ['inputs'] and 'regional_share' in MQ['inputs'])
ok('Monte Carlo quantiles ordered', all(MQ[k][0] <= MQ[k][1] <= MQ[k][2] for k in ('L', 'B', 'B_r', 'gen_share', 'hgv_saving_bn')))
ok('network adds value in every draw', MQ['share_ers_value_pos'] == 1.0)

npass = sum(c for _, c in checks)
print(f'\n{npass}/{len(checks)} checks passed')
sys.exit(0 if npass == len(checks) else 1)
