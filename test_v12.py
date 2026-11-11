"""Consistency tests for the V12 model.  Run: python -I model/test_v12.py"""
import math, sys
import numpy as np
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from france_model import P as P6, simulate as sim6
import france_v12 as m

checks = []
def ok(name, cond):
    checks.append((name, bool(cond))); print(('PASS ' if cond else 'FAIL ') + name)

inp = m.Inputs(); N = m.national(inp)
v6 = sim6(P6(), 'nuclear'); core = m.energy_core(P6(), 0.0)
ok('F0 V6 fuel cost reproduced exactly (Brest-type kelp, no diversion)', math.isclose(core['fuel_cost_eur_l'], v6['renewable_fuel_cost_eur_l'], rel_tol=1e-12))
ok('F0 V6 litres reproduced', math.isclose(core['litres'], v6['hydrocarbon_fuel_l'], rel_tol=1e-12))

for key, r in N['sites'].items():
    for sc in ('cascade', 'hp_only', 'hp_swro', 'energy_only'):
        h = r[sc]
        bal = h['htl_direct_GWh'] + h['gross_elec_GWh'] + h['med_motive_GWh'] + h['main_condenser_GWh']
        ok(f'{key}/{sc}: reactor energy closes', abs(bal - h['thermal_GWh']) < 1e-6)
        ok(f'{key}/{sc}: each low-T MWh served once (loop, condenser heat pumps or outage backup)', abs(h['lowT_from_med_GWh'] + h['lowT_from_condenser_hp_GWh'] + h['lowT_from_outage_backup_GWh'] - h['lowT_demand_GWh']) < 1e-6)
        paid = sum(v['water_transfer_paid'] for v in h['enterprises'].values()); rec = sum(v['water_transfer_received'] for v in h['enterprises'].values())
        ok(f'{key}/{sc}: internal water transfers net to zero', abs(paid - rec) < 1e-6)
        ok(f'{key}/{sc}: no heat credit in any sales line', all('heat' not in k or v['sales'] == h['water']['demin_sold'] * inp.w.price_demin_eur_m3 + h['water']['bulk_sold'] * inp.w.price_bulk_eur_m3
                                                              for k, v in h['enterprises'].items()))
    c, e0 = r['cascade'], r['energy_only']
    w = c['water']
    ok(f'{key}: distillate ledger closes', abs(w['internal_from_med'] + w['demin_sold'] + w['bulk_sold'] - inp.w.med_water_m3_y) < 1e-6)
    ok(f'{key}: MED heat used <= available', c['lowT_from_med_GWh'] <= c['med_available_delivered_GWh'] + 1e-9)
    s_c = sum(v['net_eur'] for v in c['enterprises'].values()); s_e = sum(v['net_eur'] for v in e0['enterprises'].values())
    ok(f'{key}: enterprise ledger sums to consolidated co-product value', abs((s_c - s_e) - r['coproduct_value']) < 1.0)
    ok(f'{key}: honey used <= produced', c['honey']['honey_used_t'] <= c['honey']['honey_t'] + 1e-12)
    ok(f'{key}: kelp-captured N <= dissolved N', c['imta']['captured_N_t'] <= c['imta']['dissolved_N_t'] + 1e-12)

site = {s.key: s for s in m.SITES}
ok('F5 Ulva site produces no alginate', N['alloc']['FOS'] == (0.0, 0.0) and N['sites']['FOS']['cascade']['alginate'] is None)
try:
    m.hub(site['FOS'], inp, 'cascade', 0.0, 100.0); ok('F5 forcing alginate from Ulva raises', False)
except AssertionError:
    ok('F5 forcing alginate from Ulva raises', True)
ok('F5 smokehouse only at salmonid sites', all((r['cascade']['smoked']['smoked_t'] > 0) == site[k].salmonid for k, r in N['sites'].items()))
md = m.med_design(inp.th)
ok('F6 MED design feasible with stated approaches', md['feasible'])
ok('F6 derived MED thermal energy 60-100 kWh/m3', 60 <= md['ste_kWh_m3'] <= 100)
for Tsink, Tsrc in ((50, 30), (70, 30), (70, 18), (31, 18)):
    carnot = (Tsink + 273.15) / (Tsink - Tsrc)
    ok(f'F6 COP {Tsink}<-{Tsrc} C below Carnot', m.cop(inp.th, Tsink, Tsrc) < carnot)
be = m.alginate_breakeven(site['BRE'], inp, N['alloc']['BRE'][1])
i2 = replace(inp, a=replace(inp.a, pack_price_eur_kg=be))
c_be = m.hub(site['BRE'], i2, 'cascade', 0, N['alloc']['BRE'][1])[0]['net_cash_eur']; c0 = m.hub(site['BRE'], i2, 'cascade', 0, 0)[0]['net_cash_eur']
ok('F4 at the break-even price the packaging line adds zero net cash', abs(c_be - c0) < 50.0)
S = m.main.__globals__  # noqa
fuel_per_hub = N['fuel_litres'] / 6
hyb = sum(r['cascade']['fuel_cost_eur_l'] for r in N['sites'].values()) / 6
s = m.ers_system(inp.e, inp.e.network_km_full, inp.e.diesel_longrun_eur_l, hyb, fuel_per_hub)
ok('F2 hubs for hybrid fuel use modelled fuel per hub', abs(s['hubs_for_hybrid_fuel'] - s['hybrid_fuel_ML'] * 1e6 / fuel_per_hub) < 1e-9 and fuel_per_hub < 21.25e6)
sf = m.ers_system(inp.e, inp.e.network_km_full, inp.e.diesel_longrun_eur_l, hyb, fuel_per_hub, hybrid_fuel_fossil=True)
ok('F7 hybrid fuel priced at renewable cost, not diesel', s['cost_ers_eur_vkm'] != sf['cost_ers_eur_vkm'] and s['co2_avoided_Mt'] > sf['co2_avoided_Mt'])
base = m.headline(m.apply({}))
inactive = []
for k, (_, _, lo, mo, hi) in m.MC_SPEC.items():
    h = m.headline(m.apply({k: hi}))
    if all(abs(h[x] - base[x]) < 1e-9 for x in base if base[x] is not None): inactive.append(k)
ok(f'F3 every Monte Carlo input is active (inactive: {inactive})', not inactive)
ok('F3 Monte Carlo deterministic', m.monte_carlo(3) == m.monte_carlo(3))

# --- V12 additions: SWRO comparator, enterprise capital, residual heat-pump sizing
for key, r in N['sites'].items():
    ro, c, h = r['hp_swro'], r['cascade'], r['hp_only']
    W = inp.w.med_water_m3_y; pol = ro['water']['polished_m3']
    ok(f'{key}: SWRO electricity = W*kWh/m3', abs(ro['swro_elec_GWh'] * 1e3 - W * inp.w.swro_kWh_m3 / 1e3) < 1e-6)
    ok(f'{key}: MED and SWRO polish the same volume', abs(c['water']['polished_m3'] - pol) < 1e-6 and pol > 0)
    ok(f'{key}: SWRO polishing = EDI + second RO pass; MED = EDI', abs(ro['polish_elec_GWh'] * 1e6 - pol * (inp.w.edi_kWh_m3 + inp.w.ro2_kWh_m3)) < 1e-3
       and abs(c['polish_elec_GWh'] * 1e6 - pol * inp.w.edi_kWh_m3) < 1e-3)
    ok(f'{key}: SWRO makes the same annual water, meets the same internal uses and the same demineralised sales as MED', abs(ro['water']['internal_need'] - c['water']['internal_need']) < 1e-6 and abs(ro['water']['demin_sold'] - c['water']['demin_sold']) < 1e-6
       and abs(ro['water']['internal_from_med'] + ro['water']['demin_sold'] + ro['water']['bulk_sold'] - inp.w.med_water_m3_y) < 1e-6)
    ok(f'{key}: SWRO heat supply identical to heat-pump-only', abs(ro['hp_elec_GWh'] - h['hp_elec_GWh']) < 1e-9 and abs(ro['hp_capacity_MW'] - h['hp_capacity_MW']) < 1e-9)
    ent = c['enterprises']
    for e in ('prawn', 'finfish_imta', 'honey'):
        ok(f'{key}: {e} carries capital', ent[e]['capital'] > 0)
    if site[key].salmonid: ok(f'{key}: smokehouse carries capital', ent['honey_smoked_salmon']['capital'] > 0)
    if c['alginate'] is not None and ent['alginate']['sales'] > 0: ok(f'{key}: alginate plant carries capital', ent['alginate']['capital'] > 0)
    ok(f'{key}: cascade heat-pump capacity <= heat-pump-only capacity', c['hp_capacity_MW'] <= h['hp_capacity_MW'] + 1e-9)
# --- V12 additions: full ledger reconciliation and firm heat
for key, r in N['sites'].items():
    rf = None
    for sc in ('cascade', 'hp_only', 'hp_swro', 'energy_only'):
        h = r[sc]; tot = sum(v['net_eur'] for v in h['enterprises'].values())
        ok(f'{key}/{sc}: enterprise ledgers sum exactly to consolidated net cash', abs(tot - h['net_cash_eur']) < 1e-3)
        line = h['enterprises']['reactor_and_fuel_chain']['net_eur']
        if rf is None: rf = line
        ok(f'{key}/{sc}: reactor-and-fuel-chain line identical across scenarios', abs(line - rf) < 1e-3)
        cap_ok = all((v['hp_peak_MW'] if not inp.th.hp_redundant else v['peak_MW']) * 1.0 <= v['peak_MW'] + 1e-9 for v in h['per_user'].values())
        need = sum(max(0.0, v['peak_MW'] - v['hp_peak_MW']) for v in h['per_user'].values())
        ok(f'{key}/{sc}: firm heat — heat pumps plus boilers cover every peak', cap_ok and abs(h['boiler_MW'] - need) < 1e-9)
        ff = (365 * (1 - inp.p6.capacity_factor) - inp.th.planned_outage_days) / 365
        ok(f'{key}/{sc}: outage heat between forced-outage share and full unavailability share of demand (refuelling in low-demand month)',
           h['lowT_demand_GWh'] * ff - 1e-9 <= h['outage_heat_GWh'] <= h['lowT_demand_GWh'] * (1 - inp.p6.capacity_factor) + 1e-9)
    ok(f'{key}: heat-pump-only needs no boilers', r['hp_only']['boiler_MW'] < 1e-9)
    ok(f'{key}: cascade buys more backup grid electricity than heat-pump-only', r['cascade']['grid_backup_GWh'] > r['hp_only']['grid_backup_GWh'])
# --- V12 additions: non-firm diagnostic delivers only installed capacity; water outage balance; MED sizing with its own downtime
nf = replace(inp, th=replace(inp.th, firm_heat=False))
for key in N['sites']:
    s_ = site[key]; fa, pa = N['alloc'][key]
    i2 = replace(nf, w=replace(nf.w, med_water_m3_y=m.RIGHT_SIZED_M3[key]))
    hc, _ = m.hub(s_, i2, 'cascade', fa, pa); hf, _ = m.hub(s_, replace(inp, w=replace(inp.w, med_water_m3_y=m.RIGHT_SIZED_M3[key])), 'cascade', fa, pa)
    ok(f'{key}: non-firm installs no boilers and leaves unmet heat', hc['boiler_MW'] == 0 and hc['unmet_heat_GWh'] > 0)
    ok(f'{key}: non-firm unmet heat equals the heat the firm design takes from boilers (no heat from uninstalled heat pumps)', abs(hc['unmet_heat_GWh'] - hf['boiler_heat_GWh']) < 1e-9)
    ok(f'{key}: non-firm outage grid electricity below firm (heat pumps capped at installed capacity)', hc['grid_backup_GWh'] < hf['grid_backup_GWh'])
    ok(f'{key}: firm design leaves no unmet heat', hf['unmet_heat_GWh'] == 0)
    for sc in ('cascade', 'hp_only', 'hp_swro'):
        wv = N['sites'][key][sc]['water']
        ok(f'{key}/{sc}: internal water = plant supply + mains (incl. outage purchases)', abs(wv['internal_from_med'] + wv['bought_mains'] - wv['internal_need']) < 1e-6)
    wc = N['sites'][key]['cascade']['water']
    ok(f'{key}: cascade buys mains water during MED/reactor outages', wc['outage_mains_m3'] > 0 and wc['refuelling_outage_internal_m3'] > 0)
    ok(f'{key}: distillate ledger = annual MED output', abs(wc['internal_from_med'] + wc['demin_sold'] + wc['bulk_sold'] - inp.w.med_water_m3_y) < 1e-6)
# --- V12 additions: day-weighted monthly allocation and explicit monthly water balance
for key in N['sites']:
    for sc in ('cascade', 'hp_swro'):
        wv = N['sites'][key][sc]['water']
        ok(f'{key}/{sc}: no month has in-operation internal demand above that month\'s plant output (central size)', wv['monthly_shortfall_mains_m3'] < 1e-6)
    rows = N['sites'][key]['rows'] if N['sites'][key]['rows'] else m.hub(site[key], inp, 'cascade', *N['alloc'][key])[1]
    av = np.array([r_['med_available_MWh'] for r_ in rows]); on = np.array([r_['reactor_on_frac'] for r_ in rows])
    ok(f'{key}: MED loop heat per month proportional to reactor operating days', np.allclose(av / av.sum(), on * m.DAYS / np.dot(on, m.DAYS)))
ok('F11 constant loads allocated by calendar days', abs(m.FLAT[1] - 28 / 365) < 1e-12 and abs(m.FLAT.sum() - 1) < 1e-12)
c0 = N['sites']['BRE']['cascade']
expect = (inp.w.med_capex_eur_per_m3d * inp.w.med_water_m3_y / (365 * inp.p6.capacity_factor * (1 - inp.th.med_forced_outage_frac)) + inp.w.med_marine_works_eur) / 1e6
ok('F10 MED capacity sized for reactor availability x (1 - MED downtime)', abs(c0['med_capex_MEUR'] - expect) < 1e-9)
import numpy as np
fa_b, pa_b = N['alloc']['BRE']
def inc(m3, red=False):
    i2 = replace(inp, w=replace(inp.w, med_water_m3_y=m3), th=replace(inp.th, hp_redundant=red))
    return m.hub(site['BRE'], i2, 'cascade', fa_b, pa_b)[0]['net_cash_eur'] - m.hub(site['BRE'], i2, 'hp_only', fa_b, pa_b)[0]['net_cash_eur']
xs = np.arange(1.20e6, 1.3501e6, 0.01e6); ys = [inc(x) for x in xs]
ok(f'F8 no step in cascade increment across 1.20-1.35 Mm3 (max step {max(abs(np.diff(ys))):.0f} EUR per 0.01 Mm3)', max(abs(np.diff(ys))) < 25e3)
ok('F8 redundant heat-pump sizing lowers the cascade increment', inc(2.0e6, True) < inc(2.0e6))
nf = sum(not c for _, c in checks)
print(f'{len(checks) - nf}/{len(checks)} checks passed'); sys.exit(1 if nf else 0)
