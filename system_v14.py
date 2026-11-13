"""V14 system extension of the V12 hub model (france_v12.py, unchanged).

Adds, for each of the six coastal hubs:
  * the kelp-to-drop-in-fuel chain (hydrothermal liquefaction, HTL) costed per litre under three power-supply options:
      SMR       - the V12 baseline: reactor steam for HTL heat, reactor electricity for HTL and hydrogen;
      wind      - no reactor: co-located offshore wind (contract price + firming adder) supplies all electricity,
                  HTL heat by electric heating;
      hybrid    - reactor steam for heat, offshore wind for electric loads where cheaper than reactor electricity;
    wind and hybrid hubs sit inside an offshore wind array whose foundations anchor part of the kelp longlines;
  * marine operations: a renewable-powered cable-guided Grid Harvester and solar-electric utility drones
    (densities from the marginal-benefit = marginal-cost rule of the Spanish study), with marine fuel and CO2;
  * national electric motorways (ERS) whose hybrid trucks burn the kelp fuel, and the transport CO2 they avoid.
Run: python -I model/system_v14.py   (after model/france_v12.py)
"""
import csv, json, math
from dataclasses import dataclass, field, replace, asdict
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import france_v12 as M
import weather_v17 as WX

ROOT = Path(__file__).resolve().parent
D = ROOT


@dataclass
class Sys:
    # offshore wind co-located with the kelp farm
    turbine_MW: float = 15.0
    turbine_cell_km2: float = 4.0            # ~2 km spacing; one foundation per 4 km2 of farm
    wind_cf_fixed: float = 0.45
    wind_cf_floating: float = 0.40
    wind_price_mult: float = 1.0             # scales all contract prices below
    firming_eur_MWh: float = 20.0            # balancing / firming adder for variable supply to firm process loads
    wind_delivery_eur_MWh: float = 0.0       # V16: network/delivery charges if power is not taken by private wire from the co-located array
    fuel_yield_mult: float = 1.0             # V16: multiplier on every site's HTL fuel yield (t fuel per t HTL feed)
    # V17: weather-based wind supply (ERA5 hourly, 2015-2024) replaces the flat firming adder when the data are present
    weather: bool = True
    ws_mult: float = 1.0                     # reanalysis wind-speed bias multiplier (ERA5 vs coastal observations)
    turbine_loss: float = 0.12               # wake, electrical and availability losses
    surplus_value_eur_MWh: float = 40.0      # value of contracted wind output the hub cannot use (cannibalised capture price)
    balancing_eur_MWh: float = 3.0           # intra-hour balancing on contracted wind output
    drone_pv_eur_Wp: float = 1.2             # marine-grade panel, mounting and charge controller per drone
    electric_heat_eff: float = 0.99          # HTL heat by electric heating when no reactor steam
    # turbine-anchored seaweed
    anchor_cost_share: float = 0.25          # moorings and anchors as share of farm-gate biomass cost (screening value)
    anchor_shared_frac: float = 0.50         # share of farm anchoring replaced by turbine foundations
    interface_frac: float = 0.20             # share of the saving lost to interface works, insurance and access rules
    # marine operations
    fleet_fuel_GJ_t: float = 0.35            # harvesting and support vessels, GJ fuel per dry tonne (conventional)
    marine_fuel_eur_MWh: float = 80.0
    marine_kgCO2_GJ: float = 74.1            # marine gas oil
    dm_frac: float = 0.13                    # dry matter of fresh kelp
    harvester_t_wet_h: float = 416.7
    harvester_hours: float = 2400.0
    harvester_kit_eur: float = 0.73e6        # PV deck, vertical-axis wind unit and battery per Grid Harvester
    harvester_kit_annual: float = 0.155      # capital recovery + maintenance on the kit
    harvester_fuel_saving: float = 0.161     # share of conventional fleet fuel avoided (15% work avoided, 25% electrified)
    drone_capex_eur: float = 8000.0
    drone_life_y: float = 5.0
    drone_maint: float = 0.15
    drone_kWh_day: float = 0.4
    drone_el_eur_kWh: float = 0.12
    drone_rho0: float = 1.0
    drone_seed_share: float = 0.05           # share of farm spend that is reseeding
    drone_seed_avoid: float = 0.50
    drone_fuel_avoid: float = 0.25
    # national
    transport_MtCO2_2024: float = 124.9      # CITEPA/SDES, domestic transport 2024
    finance_rate: float = 0.06


# 2025-26 French offshore wind references (EUR/MWh): Centre Manche 2 fixed-bottom award 66; AO10 weighted-average cap 100
# (floating-heavy); AO7 Oleron fixed-bottom drew no bids at its cap, so a higher Atlantic fixed price is assumed.
WIND = {'DKQ': ('fixed-bottom', 66.0), 'LEH': ('fixed-bottom', 66.0), 'BRE': ('floating', 100.0),
        'STN': ('fixed-bottom', 75.0), 'LRO': ('fixed-bottom', 85.0), 'FOS': ('floating', 100.0)}


def crf(r, n): return r / (1 - (1 + r) ** -n)


def site_p6(inp, s, sy=None):
    m = 1.0 if sy is None else sy.fuel_yield_mult
    return replace(inp.p6, seaweed_tDM_ha_y=s.yield_tDM_ha * inp.yield_mult, biocrude_fuel_yield_t_t=s.fuel_yield_t_t * m)


def marine_ops(sy: Sys, dry_t, farm_spend_eur, area_km2, drones=True, harvester=True, pv_day=None):
    fuel_MWh = dry_t * sy.fleet_fuel_GJ_t / 3.6
    out = dict(fleet_fuel_MWh_conv=fuel_MWh, fleet_co2_t_conv=dry_t * sy.fleet_fuel_GJ_t * sy.marine_kgCO2_GJ / 1000)
    wet = dry_t / sy.dm_frac
    n_h = math.ceil(wet / (sy.harvester_t_wet_h * sy.harvester_hours)) if harvester else 0
    h_cost = n_h * sy.harvester_kit_eur * sy.harvester_kit_annual
    h_fuel_saved = fuel_MWh * sy.harvester_fuel_saving if harvester else 0.0
    rem_fuel = fuel_MWh - h_fuel_saved
    if pv_day:   # V17: solar-electric drone, panel sized for the worst month at the site (ERA5)
        energy = sy.drone_kWh_day / pv_day * 1000 * sy.drone_pv_eur_Wp * crf(sy.finance_rate, sy.drone_life_y)
    else:
        energy = sy.drone_kWh_day * 365 * sy.drone_el_eur_kWh
    unit = sy.drone_capex_eur * (crf(sy.finance_rate, sy.drone_life_y) + sy.drone_maint) + energy
    B = (farm_spend_eur * sy.drone_seed_share * sy.drone_seed_avoid + rem_fuel * sy.drone_fuel_avoid * sy.marine_fuel_eur_MWh) / area_km2
    rho = sy.drone_rho0 * math.log(B / (sy.drone_rho0 * unit)) if (drones and B > sy.drone_rho0 * unit) else 0.0
    f = 1 - math.exp(-rho / sy.drone_rho0)
    d_benefit = B * f * area_km2; d_cost = rho * area_km2 * unit
    d_fuel_saved = rem_fuel * sy.drone_fuel_avoid * f
    fuel_after = rem_fuel - d_fuel_saved
    out.update(harvesters=n_h, harvester_cost_eur=h_cost, harvester_fuel_saved_MWh=h_fuel_saved,
               drones_per_km2=rho, drones=int(round(rho * area_km2)), drone_unit_cost_eur_y=unit, drone_benefit_eur=d_benefit, drone_cost_eur=d_cost,
               drone_fuel_saved_MWh=d_fuel_saved, fleet_fuel_MWh=fuel_after, fleet_co2_t=fuel_after * 3.6 * sy.marine_kgCO2_GJ / 1000,
               net_saving_eur=(h_fuel_saved * sy.marine_fuel_eur_MWh - h_cost) + (d_benefit - d_cost))
    return out


def fuel_cost(inp, sy: Sys, s, option='smr', drones=False, alloc=None):
    """Fuel cost per litre and its components for one hub. option: 'smr', 'wind', 'hybrid'."""
    p6 = site_p6(inp, sy=sy, s=s)
    fa, pa = (alloc or M.allocate_alginate(inp)[0])[s.key]
    alg_dry = (fa + pa) / (s.alginate_yield * inp.a.yield_mult) if (fa + pa) > 0 else 0.0
    core = M.energy_core(p6, alg_dry)
    dry_all = core['dry']; HTL = core['HTL_dry']; L = core['litres']
    area = p6.area_ha / 100
    wtype, wprice = WIND[s.key]
    w_el = wprice * sy.wind_price_mult + sy.firming_eur_MWh + sy.wind_delivery_eur_MWh
    pe = p6.nuclear_electric_eur_MWh
    # farm-gate biomass cost, with turbine anchors for wind and hybrid hubs
    n_turb = math.floor(area / sy.turbine_cell_km2) if option in ('wind', 'hybrid') else 0
    anchored = min(1.0, n_turb * sy.turbine_cell_km2 / area) if n_turb else 0.0
    anchor_cut = p6.seaweed_dry_cost_eur_t * sy.anchor_cost_share * sy.anchor_shared_frac * anchored * (1 - sy.interface_frac)
    farm_gate = p6.seaweed_dry_cost_eur_t - anchor_cut
    wx = sy.weather and WX.available()
    ops = marine_ops(sy, dry_all, dry_all * farm_gate, area, drones=drones, harvester=drones, pv_day=WX.pv_worst(s.key) if wx else None)
    ops_cut_t = ops['net_saving_eur'] / dry_all            # per dry tonne of all kelp
    # energy
    E_proc = HTL * p6.HTL_elec_MWh_t + core['H2_t'] * p6.H2_elec_MWh_t
    wc = None
    if option == 'smr':
        el = pe; heat = core['H_direct'] * pe * p6.nuclear_heat_opp_ratio + core['trim'] * pe
    elif wx:
        # V17: hourly contract against the hub's flat electric load; backup = reactor (hybrid) or grid (wind only)
        w_c = wprice * sy.wind_price_mult + sy.wind_delivery_eur_MWh
        load = E_proc + core['trim'] if option == 'hybrid' else E_proc + (core['H_direct'] + core['trim']) / sy.electric_heat_eff
        backup = pe if option == 'hybrid' else inp.th.grid_buy_eur_MWh
        rmax = n_turb * sy.turbine_MW * 8760 / load
        wc = WX.contract(s.key, w_c, backup, sy.surplus_value_eur_MWh, rmax, sy.ws_mult, sy.turbine_loss, sy.balancing_eur_MWh)
        wc.update(load_MW=load / 8760, backup_eur_MWh=backup, contract_eur_MWh=w_c)
        el = wc['price']
        heat = core['H_direct'] * pe * p6.nuclear_heat_opp_ratio + core['trim'] * el if option == 'hybrid' else (core['H_direct'] + core['trim']) / sy.electric_heat_eff * el
    elif option == 'hybrid':
        el = min(pe, w_el); heat = core['H_direct'] * pe * p6.nuclear_heat_opp_ratio + core['trim'] * el
    else:
        el = w_el; heat = (core['H_direct'] + core['trim']) / sy.electric_heat_eff * el
    comp = dict(feedstock=HTL * (farm_gate - ops_cut_t), harvest=HTL * p6.harvest_marine_eur_t, electricity=E_proc * el,
                heat=heat, other=L * p6.HTL_other_eur_L)
    tot = sum(comp.values())
    cf_site = float(WX.cf_series(s.key, sy.ws_mult, sy.turbine_loss).mean()) if wx else (sy.wind_cf_fixed if wtype == 'fixed-bottom' else sy.wind_cf_floating)
    wind_GWh = n_turb * sy.turbine_MW * 8760 * cf_site / 1000
    return dict(key=s.key, site=s.name, option=option, drones=drones, litres=L, dry_t=dry_all, HTL_dry_t=HTL,
                fuel_eur_l=tot / L, **{f'{k}_eur_l': v / L for k, v in comp.items()},
                farm_gate_eur_t=farm_gate, anchor_cut_eur_t=anchor_cut, anchored_frac=anchored, turbines=n_turb,
                wind_MW=n_turb * sy.turbine_MW, wind_GWh=wind_GWh, wind_type=wtype, wind_price_eur_MWh=wprice * sy.wind_price_mult,
                electricity_price_eur_MWh=el, process_elec_GWh=E_proc / 1000, ops=ops,
                marine_kgCO2_l=ops['fleet_co2_t'] * 1000 * (HTL / dry_all) / L, wind_cf=cf_site, weather=wx, wind_contract=wc)


OPTIONS = [('smr', False), ('smr', True), ('wind', True), ('hybrid', True)]
LABEL = {('smr', False): 'SMR, conventional farm', ('smr', True): 'SMR + harvester and drones',
         ('wind', True): 'Offshore wind only (turbine anchors, drones)', ('hybrid', True): 'SMR + offshore wind (turbine anchors, drones)'}


def evaluate(inp, sy, diesel=None):
    alloc = M.allocate_alginate(inp)[0]
    rows = [fuel_cost(inp, sy, s, o, d, alloc) for s in M.SITES for (o, d) in OPTIONS]
    nat = {}
    for (o, d) in OPTIONS:
        rr = [r for r in rows if r['option'] == o and r['drones'] == d]
        L = sum(r['litres'] for r in rr)
        nat[f'{o}{"_d" if d else ""}'] = dict(fuel_ML=L / 1e6, mean_eur_l=float(np.mean([r['fuel_eur_l'] for r in rr])),
                                             weighted_eur_l=sum(r['fuel_eur_l'] * r['litres'] for r in rr) / L,
                                             marine_kgCO2_l=sum(r['marine_kgCO2_l'] * r['litres'] for r in rr) / L)
    best = {s.key: min((r for r in rows if r['key'] == s.key), key=lambda r: r['fuel_eur_l']) for s in M.SITES}
    # national electric motorways with kelp-fuelled hybrids at the cheapest option per site (litre-weighted)
    e = inp.e; dsl = diesel if diesel is not None else e.diesel_longrun_eur_l
    bL = sum(best[k]['litres'] for k in best); price_best = sum(best[k]['fuel_eur_l'] * best[k]['litres'] for k in best) / bL
    fuel_per_hub = bL / len(M.SITES)
    ers_base = M.ers_system(e, 8850.0, dsl, nat['smr']['mean_eur_l'], fuel_per_hub)
    ers_best = M.ers_system(e, 8850.0, dsl, price_best, fuel_per_hub)
    mk = sum(best[k]['marine_kgCO2_l'] * best[k]['litres'] for k in best) / bL
    marine_Mt = ers_best['hybrid_fuel_ML'] * 1e6 * mk / 1e9
    ers_best = dict(ers_best, co2_avoided_net_marine_Mt=ers_best['co2_avoided_Mt'] - marine_Mt, marine_ops_Mt=marine_Mt,
                    hgv_share=(ers_best['co2_avoided_Mt'] - marine_Mt) / e.hgv_MtCO2_2023,
                    transport_share=(ers_best['co2_avoided_Mt'] - marine_Mt) / sy.transport_MtCO2_2024,
                    kelp_area_km2=ers_best['hubs_for_hybrid_fuel'] * 100.0, fuel_eur_l=price_best)
    return dict(rows=rows, national=nat, best={k: dict(option=v['option'], drones=v['drones'], fuel_eur_l=v['fuel_eur_l']) for k, v in best.items()},
                ers_smr=ers_base, ers_best=ers_best)


MC = {  # name: (object, field, low, mode, high)
    'anchor_cost_share': ('sy', 'anchor_cost_share', .10, .25, .40), 'anchor_shared_frac': ('sy', 'anchor_shared_frac', .25, .50, .75),
    'interface_frac': ('sy', 'interface_frac', .10, .20, .40), 'balancing_eur_MWh': ('sy', 'balancing_eur_MWh', 1, 3, 8),
    'wind_price_mult': ('sy', 'wind_price_mult', .85, 1.0, 1.30), 'harvester_fuel_saving': ('sy', 'harvester_fuel_saving', 0, .161, .30),
    'drone_seed_avoid': ('sy', 'drone_seed_avoid', .2, .5, .7), 'drone_capex_eur': ('sy', 'drone_capex_eur', 5000, 8000, 15000),
    'seaweed_dry_cost_eur_t': ('p6', 'seaweed_dry_cost_eur_t', 300, 400, 1200), 'nuclear_electric_eur_MWh': ('p6', 'nuclear_electric_eur_MWh', 80, 105, 140),
    'diesel_eur_l': ('diesel', None, 1.20, 1.45, 1.80),
    # V16 (referee): transport-system and biomass inputs that drive the national result
    'ers_capex_eur_km': ('e', 'capex_eur_km', 2.5e6, 3.4e6, 4.8e6), 'ers_capture_max': ('e', 'capture_max', .40, .55, .65),
    'ers_on_wire_share': ('e', 'on_wire_share', .60, .75, .85), 'ers_elec_kWh_km': ('e', 'elec_kWh_km', 1.15, 1.30, 1.50),
    'ers_truck_premium_eur': ('e', 'truck_premium_eur', 20000, 45000, 80000), 'kelp_yield_mult': ('inp', 'yield_mult', .6, 1.0, 1.4),
    'fuel_yield_mult': ('sy', 'fuel_yield_mult', .8, 1.0, 1.2), 'wind_delivery_eur_MWh': ('sy', 'wind_delivery_eur_MWh', 0.0, 0.0, 30.0),
    # V17: weather-contract inputs
    'ws_mult': ('sy', 'ws_mult', 0.95, 1.0, 1.08), 'surplus_value_eur_MWh': ('sy', 'surplus_value_eur_MWh', 20, 40, 60),
    'grid_buy_eur_MWh': ('th', 'grid_buy_eur_MWh', 100, 130, 180)}


def apply(inp, sy, dsl, obj, fld, v):
    if obj == 'sy': return inp, replace(sy, **{fld: v}), dsl
    if obj == 'p6': return replace(inp, p6=replace(inp.p6, **{fld: v})), sy, dsl
    if obj == 'e': return replace(inp, e=replace(inp.e, **{fld: v})), sy, dsl
    if obj == 'inp': return replace(inp, **{fld: v}), sy, dsl
    if obj == 'th': return replace(inp, th=replace(inp.th, **{fld: v})), sy, dsl
    return inp, sy, v


def monte_carlo(inp, sy, n=2000, seed=20261112):
    rng = np.random.default_rng(seed); out = []
    for _ in range(n):
        i2, s2, dsl = inp, sy, None; draw = {}
        for k, (obj, fld, lo, mo, hi) in MC.items():
            v = float(rng.triangular(lo, mo, hi)) if hi > lo else lo; draw[k] = v
            i2, s2, dsl = apply(i2, s2, dsl, obj, fld, v)
        ev = evaluate(i2, s2, dsl)
        nat = ev['national']
        out.append(dict(draw, smr_eur_l=nat['smr']['mean_eur_l'], smr_d_eur_l=nat['smr_d']['mean_eur_l'], wind_eur_l=nat['wind_d']['mean_eur_l'],
                        hybrid_eur_l=nat['hybrid_d']['mean_eur_l'], ers_saving_bn=ev['ers_best']['net_saving_bn_y'],
                        co2_net_Mt=ev['ers_best']['co2_avoided_net_marine_Mt'],
                        hybrid_cheapest=float(nat['hybrid_d']['mean_eur_l'] <= min(nat['smr']['mean_eur_l'], nat['smr_d']['mean_eur_l'], nat['wind_d']['mean_eur_l']) + 1e-12)))
    q = lambda k: [float(np.percentile([r[k] for r in out], p)) for p in (5, 50, 95)]
    return out, dict(quantiles={k: q(k) for k in ('smr_eur_l', 'smr_d_eur_l', 'wind_eur_l', 'hybrid_eur_l', 'ers_saving_bn', 'co2_net_Mt')},
                     hybrid_cheapest_share=float(np.mean([r['hybrid_cheapest'] for r in out])),
                     ers_saving_positive_share=float(np.mean([r['ers_saving_bn'] > 0 for r in out])),
                     wind_beats_smr_share=float(np.mean([r['wind_eur_l'] < r['smr_d_eur_l'] for r in out])),
                     hybrid_beats_smr_d_share=float(np.mean([r['hybrid_eur_l'] < r['smr_d_eur_l'] for r in out])))


def write_csv(name, rows):
    rows = [{k: v for k, v in r.items() if not isinstance(v, dict)} for r in rows]
    with open(D / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def main():
    inp = M.Inputs(); sy = Sys()
    ev = evaluate(inp, sy)
    write_csv('v14_fuel_by_site_and_option.csv', ev['rows'])
    write_csv('v14_marine_ops_by_site.csv', [dict(key=r['key'], site=r['site'], **r['ops']) for r in ev['rows'] if r['option'] == 'hybrid'])
    sens = {}
    for name, kw in (('feedstock_1200', dict(p6=dict(seaweed_dry_cost_eur_t=1200.0))), ('wind_price_x1.3', dict(sy=dict(wind_price_mult=1.3))),
                     ('flat_firming_v16', dict(sy=dict(weather=False))), ('ws_minus5', dict(sy=dict(ws_mult=0.95))), ('ws_plus8', dict(sy=dict(ws_mult=1.08))),
                     ('surplus_20', dict(sy=dict(surplus_value_eur_MWh=20.0))), ('no_anchor_sharing', dict(sy=dict(anchor_shared_frac=0.0))),
                     ('smr_80', dict(p6=dict(nuclear_electric_eur_MWh=80.0))), ('smr_140', dict(p6=dict(nuclear_electric_eur_MWh=140.0))),
                     ('delivery_15', dict(sy=dict(wind_delivery_eur_MWh=15.0))), ('delivery_30', dict(sy=dict(wind_delivery_eur_MWh=30.0))),
                     ('interface_0.6', dict(sy=dict(interface_frac=0.6)))):
        i2 = replace(inp, p6=replace(inp.p6, **kw['p6'])) if 'p6' in kw else inp
        s2 = replace(sy, **kw['sy']) if 'sy' in kw else sy
        e2 = evaluate(i2, s2)
        sens[name] = dict({k: v['mean_eur_l'] for k, v in e2['national'].items()}, ers_saving_bn=e2['ers_best']['net_saving_bn_y'])
    # V16: what the combined option owes to cheaper electricity and to the (hypothetical) anchor sharing
    nat = ev['national']; na = sens['no_anchor_sharing']
    decomp = dict(smr_d=nat['smr_d']['mean_eur_l'], hybrid_no_anchor=na['hybrid_d'], hybrid=nat['hybrid_d']['mean_eur_l'],
                  electricity_effect=na['hybrid_d'] - nat['smr_d']['mean_eur_l'], anchor_effect=nat['hybrid_d']['mean_eur_l'] - na['hybrid_d'])
    decomp['anchor_share'] = decomp['anchor_effect'] / (decomp['anchor_effect'] + decomp['electricity_effect'])
    lo, hi = 0.0, 1.0                                   # interface loss at which the combined option loses its edge over SMR + drones
    for _ in range(50):
        mid = (lo + hi) / 2; h = evaluate(inp, replace(sy, interface_frac=mid))['national']['hybrid_d']['mean_eur_l']
        lo, hi = (mid, hi) if h < nat['smr_d']['mean_eur_l'] else (lo, mid)
    decomp['interface_breakeven'] = (lo + hi) / 2
    lo, hi = 0.0, 200.0                                 # delivery charge at which wind electricity no longer helps any hub
    for _ in range(50):
        mid = (lo + hi) / 2; h = evaluate(inp, replace(sy, wind_delivery_eur_MWh=mid, anchor_shared_frac=0.0))['national']['hybrid_d']['mean_eur_l']
        lo, hi = (mid, hi) if h < nat['smr_d']['mean_eur_l'] - 1e-9 else (lo, mid)
    decomp['delivery_breakeven_no_anchor'] = (lo + hi) / 2
    # V16: joint sensitivity of the 8,850 km motorway saving to catenary capital and captured freight
    joint = []
    for cm in (1.0, 1.2, 1.4, 1.6):
        for km_ in (1.0, 0.9, 0.8, 0.7):
            i2 = replace(inp, e=replace(inp.e, capex_eur_km=inp.e.capex_eur_km * cm, capture_max=inp.e.capture_max * km_))
            eb = evaluate(i2, sy)['ers_best']
            joint.append(dict(capex_mult=cm, capture_mult=km_, saving_bn=eb['net_saving_bn_y'], co2_net_Mt=eb['co2_avoided_net_marine_Mt']))
    lo, hi = 1.0, 3.0
    for _ in range(50):
        mid = (lo + hi) / 2; v = evaluate(replace(inp, e=replace(inp.e, capex_eur_km=inp.e.capex_eur_km * mid)), sy)['ers_best']['net_saving_bn_y']
        lo, hi = (mid, hi) if v > 0 else (lo, mid)
    capex_be = (lo + hi) / 2
    write_csv('v14_ers_joint_sensitivity.csv', joint)
    # V17: weather-based wind contracts by site
    wxt = []
    if WX.available():
        for r in ev['rows']:
            if r['option'] in ('hybrid', 'wind') and r['drones'] and r['wind_contract']:
                c = r['wind_contract']; sm = WX.summary(r['key'])
                wxt.append(dict(key=r['key'], option=r['option'], cf=r['wind_cf'], cf_assumed_v16=(sy.wind_cf_fixed if WIND[r['key']][0] == 'fixed-bottom' else sy.wind_cf_floating),
                                cf_min_year=min(sm['cf_by_year'].values()), cf_max_year=max(sm['cf_by_year'].values()), load_MW=c['load_MW'], contracted_MW_per_MW=c['r'],
                                wind_share=c['wind_share'], surplus_share=c['surplus'], residual_share=c['residual'], contract_eur_MWh=c['contract_eur_MWh'],
                                backup_eur_MWh=c['backup_eur_MWh'], effective_eur_MWh=c['price'], v16_flat_eur_MWh=(min(inp.p6.nuclear_electric_eur_MWh, c['contract_eur_MWh'] + 20.0) if r['option'] == 'hybrid' else c['contract_eur_MWh'] + 20.0),
                                longest_shortfall_h=WX.longest_shortfall(r['key'], c['r']), pv_kWh_kWp_year=sm['pv_kWh_kWp_year'], pv_worst_month=sm['pv_worst_month_kWh_kWp_day'],
                                drone_Wp=sy.drone_kWh_day / sm['pv_worst_month_kWh_kWp_day'] * 1000, fuel_eur_l=r['fuel_eur_l']))
        write_csv('v17_wind_contracts_by_site.csv', wxt)
    ers_diesel = {lab: evaluate(inp, sy, d)['ers_best']['net_saving_bn_y'] for lab, d in (('low_1.20', 1.20), ('central_1.45', 1.45), ('high_1.80', 1.80))}
    mc, mcs = monte_carlo(inp, sy)
    write_csv('v14_system_monte_carlo.csv', mc)
    res = dict(scope='V14 system extension: fuel chain under SMR / offshore wind / hybrid supply, turbine-anchored kelp, Grid Harvester and utility drones, electric motorways',
               assumptions=asdict(sy), wind_prices=WIND, national=ev['national'], best=ev['best'], ers_smr=ev['ers_smr'], ers_best=ev['ers_best'],
               sensitivity=sens, ers_by_diesel=ers_diesel, hybrid_decomposition=decomp, weather_contracts=wxt, ers_joint=joint, ers_capex_breakeven_mult=capex_be, monte_carlo=dict(n=len(mc), seed=20261112, inputs=list(MC), **mcs),
               sites={r['key'] + '|' + r['option'] + ('_d' if r['drones'] else ''): {k: v for k, v in r.items()} for r in ev['rows']})
    json.dump(res, open(D / 'v14_system_results.json', 'w'), indent=1, default=float)
    n = ev['national']
    print('fuel EUR/L  smr %.2f | smr+drones %.2f | wind %.2f | hybrid %.2f' % (n['smr']['mean_eur_l'], n['smr_d']['mean_eur_l'], n['wind_d']['mean_eur_l'], n['hybrid_d']['mean_eur_l']))
    print('ERS saving bn: smr fuel %.2f | best fuel %.2f; CO2 net %.2f Mt (%.1f%% transport)' % (ev['ers_smr']['net_saving_bn_y'], ev['ers_best']['net_saving_bn_y'],
          ev['ers_best']['co2_avoided_net_marine_Mt'], 100 * ev['ers_best']['transport_share']))
    print('system results written')


if __name__ == '__main__':
    main()
