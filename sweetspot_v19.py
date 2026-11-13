"""V18 national sweet spot between electrification and liquid fuels for French transport, with fuel-specific balances,
two heavy-truck classes, and a 2027-2041 transition.  Supersedes sweetspot_v15.py (kept for provenance).

Changes from V15
  * Heavy trucks in two classes (SDES TRM: ~30% of HGV vehicle-km on regional hauls < 150 km):
      regional  - depot-charged battery trucks with a range extender; off-wire duty = a day's driving; no catenary use;
      long-haul - pantograph + battery + range extender; off-wire legs exponential with a mean that falls with network length.
    Each class has its own battery size; the optimum is searched jointly with the network length.
  * Renewable liquids are no longer one interchangeable pool. A linear programme allocates each pathway's output to
    aviation (jet), shipping, road and an export/chemicals sink, with
      - a maximum jet fraction per pathway (HEFA 0.7, Fischer-Tropsch e-fuel 0.6, kelp HTL 0: no ASTM D7566 annex),
      - ReFuelEU step minima for SAF and for synthetic aviation fuel (RFNBO e-kerosene only),
      - FuelEU Maritime as a well-to-wake GHG-intensity reduction (not a volume share), with pathway intensities,
      - renewable road fuel for the hybrid trucks' generators.
    The V15 pooled merit order is kept as a comparison.
  * ReFuelEU and FuelEU applied as step functions (34% SAF, 10% synthetic, 31% maritime intensity cut from 2040).
V18 (referee on V17): e-fuel split into RFNBO (offshore-wind PPA, hourly matching, ERA5 profile; counts for the
  ReFuelEU synthetic sub-mandate) and low-carbon (nuclear/grid baseload; counts for the SAF share, FuelEU and road);
  kelp hubs built only as pilots at central cost, with idle-capacity charges; electricity and capacity boundary reported.
Run: python -I model/sweetspot_v19.py   (after france_v12.py and system_v14.py)
"""
import csv, json, math
from dataclasses import dataclass, replace, asdict
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import linprog
sys.path.insert(0, str(Path(__file__).resolve().parent))
import france_v12 as M
import system_v14 as S
import weather_v17 as WX

ROOT = Path(__file__).resolve().parent
D = ROOT
YEARS = list(range(2027, 2042))
MJ_L = 34.4                                   # drop-in litre, diesel/jet equivalent


@dataclass
class Nat:
    # 2024p transport GHG, Mt CO2e, incl. international bunkers (SGPE baromètre / Citepa Secten)
    co2_passenger_land: float = 72.5
    co2_freight_land: float = 46.0
    co2_aviation: float = 21.4
    co2_maritime: float = 6.9
    co2_hgv: float = 27.9
    jet_kgCO2_l: float = 2.53
    marine_kgCO2_l: float = 2.75
    diesel_kgCO2_l: float = 2.66
    demand_growth_aviation: float = 0.0
    demand_growth_maritime: float = 0.0
    # light road
    ldv_bev_fleet_2024: float = 0.025
    ldv_bev_fleet_2026: float = 0.035
    ldv_bev_sales_2027: float = 0.30
    ldv_bev_sales_2035: float = 1.00
    ldv_fleet_life_y: float = 15.0
    ldv_full_electric_TWh: float = 95.0
    # heavy trucks: two classes
    regional_share: float = 0.30              # share of HGV vehicle-km on regional hauls (SDES TRM: 26% of t-km < 150 km; more vkm per t-km)
    regional_leg_km: float = 250.0            # regional truck's daily driving between depot charges
    regional_km_y: float = 60000.0
    regional_premium_eur: float = 20000.0     # e-axle, power electronics and range extender, no pantograph
    hgv_life_y: float = 7.0
    hyb_sales_mid_year: float = 2032.0
    hyb_sales_slope_y: float = 1.6
    hyb_premium_eur: float = 30000.0          # long-haul: pantograph, e-axle, power electronics, range extender
    batt_eur_kWh_2041: float = 120.0
    batt_eur_kWh_2027: float = 190.0
    batt_life_y: float = 8.0
    batt_dod: float = 0.80
    gen_l_per_km: float = 0.29
    leg_min_km: float = 60.0                  # long-haul off-wire leg with a dense network (access, gaps)
    leg_max_km: float = 400.0                 # long-haul off-wire leg with no network
    max_lh_capture: float = 0.95
    # renewable liquid supply, 2041 central (EUR per drop-in litre)
    hefa_eur_l: float = 1.55
    hefa_cap_GL: float = 1.2
    hefa_kgCO2_l: float = 0.50
    hubs_per_coast: int = 6
    efuel_kWh_l: float = 20.0
    efuel_el_eur_MWh: float = 70.0
    efuel_capex_eur_l: float = 0.70
    efuel_co2_kg_l: float = 3.0
    co2_bio_eur_t: float = 60.0
    co2_dac_eur_t: float = 250.0
    co2_bio_cap_Mt: float = 4.0
    grid_kgCO2_kWh: float = 0.018
    # product slates and eligibility (V17)
    jet_frac_hefa: float = 0.70               # max-jet HEFA mode
    jet_frac_efuel: float = 0.60              # Fischer-Tropsch jet cut
    jet_frac_kelp: float = 0.0                # HTL jet has no ASTM D7566 annex (IEA Bioenergy Task 34, 2026)
    jet_adder_hefa: float = 0.10              # extra hydrocracking/isomerisation for SPK
    jet_adder_kelp: float = 0.10              # only if jet_frac_kelp > 0 (co-processing sensitivity)
    marine_adder_kelp: float = -0.10          # mild hydrotreatment suffices for ISO 8217 marine grades
    export_value_eur_l: float = 0.90          # value of co-products not needed by mandated uses (naphtha, surplus diesel)
    # V18: RFNBO vs low-carbon e-fuel (Delegated Regulation 2023/1184; ReFuelEU Art. 3)
    rfnbo_gw_per_coast: float = 2.0           # offshore wind under PPA available to RFNBO plants per coast (12 GW in all)
    rfnbo_buffer_eur_l: float = 0.10          # hydrogen buffer keeping Fischer-Tropsch steady under hourly matching
    rfnbo_import_premium_eur_l: float = 0.30  # imported RFNBO over the dearest domestic RFNBO (shipping, margin)
    u_ref: float = 0.685                      # baseload electrolyser utilisation behind efuel_capex_eur_l (6,000 h)
    lc_counts_synthetic: bool = True          # V19: certified synthetic low-carbon aviation fuel (>=70% savings) counts toward SAF and synthetic minima (ReFuelEU Art. 4; Commission FAQ); False = RFNBO-only procurement scenario
    lc_saving_min: float = 0.70               # lifecycle-savings threshold for synthetic low-carbon aviation fuel
    fossil_comparator_g_MJ: float = 94.0      # RED/ReFuelEU fossil fuel comparator
    jet_MJ_l: float = 34.4
    lc_el_gCO2_kWh: float = 20.0              # life-cycle intensity of nuclear/grid baseload electricity used for low-carbon e-fuel (France)
    synth_schedule: str = 'annual_min_backloaded'   # 2030-2034: annual minima with period averages met in the last year of each period; 'flat' = period average every year (V18)
    kelp_wind_only_until: int = 2035          # hubs run on offshore wind alone before the reactor enters service
    hub_start: str = 'wind_first'             # 'wind_first': pilots from 2030 on wind, SMR from 2035; 'smr_first': no hubs before 2035
    # V18: kelp-hub deployment
    pilot_hubs: float = 6.0                   # hubs built at central cost (one per coast); expansion only once cost levers are met
    kelp_fixed_share: float = 0.6             # share of hub fuel cost that is fixed (capital, farm, crew) and paid when idle
    fueleu_ref_g_MJ: float = 91.16
    # fossil references
    jet_fossil_eur_l: float = 0.75
    marine_fossil_eur_l: float = 0.70
    rate: float = 0.06


# step minima "from 1 January" (ReFuelEU Annex I; FuelEU Art. 4)
REFUEL = {2025: .02, 2030: .06, 2035: .20, 2040: .34, 2045: .42, 2050: .70}
SYNTH = {2025: 0.0, 2030: .012, 2032: .02, 2035: .05, 2040: .10, 2045: .15, 2050: .35}   # period averages 2030-34; minima from 2035
SYNTH_MIN = {2025: 0.0, 2030: .007, 2032: .012, 2034: .02, 2035: .05, 2040: .10, 2045: .15, 2050: .35}   # Annex I annual minima
SYNTH_PERIODS = (((2030, 2031), .012), ((2032, 2033, 2034), .02))                                            # Annex I period averages
FUELEU = {2025: .02, 2030: .06, 2035: .145, 2040: .31, 2045: .62, 2050: .80}


def mandate(tab, y):
    v = 0.0
    for k in sorted(tab):
        if y >= k: v = tab[k]
    return v


def synth_share(n, y):
    """Synthetic minimum share in year y. 2030-2034: annual minima, with the volume-weighted period average met in the
    last year of each period (e-fuel costs fall over time, so back-loading is the cheapest compliant path); 'flat' applies
    the period average every year."""
    for yrs, avg in SYNTH_PERIODS:
        if y in yrs:
            if n.synth_schedule == 'flat': return avg
            if y != yrs[-1]: return mandate(SYNTH_MIN, y)
            A = {yy: base_litres(n, yy)[0] for yy in yrs}
            return (avg * sum(A.values()) - sum(mandate(SYNTH_MIN, yy) * A[yy] for yy in yrs[:-1])) / A[y]
    return mandate(SYNTH_MIN, y)


def lc_gCO2_MJ(n):
    return n.efuel_kWh_l * n.lc_el_gCO2_kWh / n.jet_MJ_l


def crf(r, n): return r / (1 - (1 + r) ** -n)
def logistic(y, mid, slope, lo=0.0, hi=1.0): return lo + (hi - lo) / (1 + math.exp(-(y - mid) / slope))


def base_litres(n: Nat, y=2041):
    t = y - 2024
    return (n.co2_aviation * 1e9 / n.jet_kgCO2_l * (1 + n.demand_growth_aviation) ** t,
            n.co2_maritime * 1e9 / n.marine_kgCO2_l * (1 + n.demand_growth_maritime) ** t)


# ------------------------------------------------------------------------------------------------ heavy trucks, two classes
def hgv(n: Nat, e: M.ERS, L, B_lh, B_r, batt_eur_kWh=None):
    L = np.asarray(L, float); B_lh = np.asarray(B_lh, float); B_r = np.asarray(B_r, float)
    vkm = e.hgv_vkm_bn * 1e9; s_r = n.regional_share
    v_lh, v_r = vkm * (1 - s_r), vkm * s_r
    cap = e.capture_max * (1 - np.exp(-L / e.capture_scale_km))
    w_lh = np.minimum(n.max_lh_capture, cap / (1 - s_r)) * e.on_wire_share
    leg = n.leg_min_km + (n.leg_max_km - n.leg_min_km) * np.exp(-L / e.capture_scale_km)
    R_lh = B_lh * n.batt_dod / e.elec_kWh_km; R_r = B_r * n.batt_dod / e.elec_kWh_km
    g_lh = (1 - w_lh) * np.exp(-R_lh / leg); g_r = np.exp(-R_r / n.regional_leg_km)
    litres = (v_lh * g_lh + v_r * g_r) * n.gen_l_per_km
    el_km = v_lh * (1 - g_lh) + v_r * (1 - g_r)
    elec_TWh = el_km * e.elec_kWh_km * (1 + e.grid_loss) / 1e9
    pb = n.batt_eur_kWh_2041 if batt_eur_kWh is None else batt_eur_kWh; cb = crf(n.rate, n.batt_life_y)
    t_lh, t_r = v_lh / e.truck_km_y, v_r / n.regional_km_y
    infra = L * e.capex_eur_km * (e.infra_crf + e.infra_om_frac)
    veh = t_lh * (n.hyb_premium_eur * e.truck_crf + B_lh * pb * cb) + t_r * (n.regional_premium_eur * e.truck_crf + B_r * pb * cb)
    energy = elec_TWh * 1e6 * e.elec_eur_MWh - el_km * e.maint_saving_eur_km
    return dict(capture=cap, wire_share=w_lh * (1 - s_r), wire_share_lh=w_lh, leg_km=leg, range_lh_km=R_lh, range_r_km=R_r,
                gen_share=(v_lh * g_lh + v_r * g_r) / vkm, gen_share_lh=g_lh, gen_share_r=g_r, litres=litres, elec_TWh=elec_TWh,
                infra=infra, vehicles=veh, energy=energy, nonfuel=infra + veh + energy)


def diesel_baseline(n, e, diesel=None):
    d = e.diesel_longrun_eur_l if diesel is None else diesel
    vkm = e.hgv_vkm_bn * 1e9
    return dict(cost=vkm * e.diesel_l_per_km * d, litres=vkm * e.diesel_l_per_km, co2_Mt=vkm * e.diesel_l_per_km * n.diesel_kgCO2_l / 1e9)


# ------------------------------------------------------------------------------------------------ supply
def efuel_price(n: Nat, co2_eur_t):
    return n.efuel_kWh_l * n.efuel_el_eur_MWh / 1000 + n.efuel_capex_eur_l + n.efuel_co2_kg_l * co2_eur_t / 1000


def kelp_tiers(inp, sy, n: Nat, hubs_per_coast=None, option='hybrid'):
    ev = S.evaluate(inp, sy); k = n.hubs_per_coast if hubs_per_coast is None else hubs_per_coast; out = []
    for s in M.SITES:
        r = next(r for r in ev['rows'] if r['key'] == s.key and r['option'] == option and r['drones'])
        kg = r['marine_kgCO2_l'] + r['process_elec_GWh'] * 1e6 * inp.p6.SMR_electric_kgCO2_per_MWh / 1000 / r['litres']
        out.append(dict(name=f'kelp_{s.key}', kind='kelp', price=r['fuel_eur_l'], cap=r['litres'] * k, kg=kg, hubs=k, litres_per_hub=r['litres']))
    return out


RF_CACHE = {}


def rfnbo_sites(n: Nat, sy):
    """Per-coast RFNBO e-fuel from hourly-matched offshore wind (ERA5). Price excludes CO2."""
    key = (n.efuel_kWh_l, n.efuel_capex_eur_l, n.u_ref, n.rfnbo_buffer_eur_l, n.rfnbo_gw_per_coast, sy.wind_price_mult, sy.wind_delivery_eur_MWh,
           sy.balancing_eur_MWh, sy.surplus_value_eur_MWh, sy.ws_mult, sy.turbine_loss)
    if key in RF_CACHE: return RF_CACHE[key]
    out = []
    for k in WX.KEYS:
        w = S.WIND[k][1] * sy.wind_price_mult + sy.wind_delivery_eur_MWh
        r = WX.rfnbo_efuel(k, w, sy.balancing_eur_MWh, sy.surplus_value_eur_MWh, n.efuel_kWh_l, n.efuel_capex_eur_l, n.u_ref, n.rfnbo_buffer_eur_l, sy.ws_mult, sy.turbine_loss)
        wind_MW = n.rfnbo_gw_per_coast * 1000; elz = wind_MW / r['r']
        litres = elz * r['utilisation'] * 8760 * 1000 / n.efuel_kWh_l
        r.update(cap_L=litres, elz_MW_per_GL=elz / (litres / 1e9), wind_MW_per_GL=wind_MW / (litres / 1e9))
        out.append(r)
    RF_CACHE[key] = out
    return out


def supply_curve(n: Nat, kelp, sy=None, hefa_cap=None, bio_cap_Mt=None, kelp_cap_mult=1.0, efuel_mult=1.0, rf_scale=1.0):
    sy = S.Sys() if sy is None else sy
    kg_e = n.efuel_kWh_l * n.grid_kgCO2_kWh
    bio = (n.co2_bio_cap_Mt if bio_cap_Mt is None else bio_cap_Mt) * 1e9 / n.efuel_co2_kg_l
    t = [dict(name='hefa', kind='hefa', price=n.hefa_eur_l, cap=(n.hefa_cap_GL if hefa_cap is None else hefa_cap) * 1e9, kg=n.hefa_kgCO2_l, groups={})]
    t += [dict(k, cap=k['cap'] * kelp_cap_mult, groups={}) for k in kelp]
    lc_elz = 1e9 * n.efuel_kWh_l / (n.u_ref * 8760) / 1000
    t.append(dict(name='efuel_lc_bio', kind='efuel_lc', price=efuel_price(n, n.co2_bio_eur_t) * efuel_mult, cap=1e15, kg=kg_e, groups={'bio': bio}, elz_MW_per_GL=lc_elz))
    t.append(dict(name='efuel_lc_dac', kind='efuel_lc', price=efuel_price(n, n.co2_dac_eur_t) * efuel_mult, cap=1e15, kg=kg_e, groups={}, elz_MW_per_GL=lc_elz))
    for r in rfnbo_sites(n, sy):
        g = f"rf_{r['key']}"; cap = r['cap_L'] * rf_scale
        for src, co2 in (('bio', n.co2_bio_eur_t), ('dac', n.co2_dac_eur_t)):
            t.append(dict(name=f"efuel_rf_{src}_{r['key']}", kind='efuel_rf', price=(r['price'] + n.efuel_co2_kg_l * co2 / 1000) * efuel_mult, cap=1e15,
                          kg=kg_e * 0.0 + n.efuel_kWh_l * 0.012, groups=({'bio': bio, g: cap} if src == 'bio' else {g: cap}),
                          elz_MW_per_GL=r['elz_MW_per_GL'], wind_MW_per_GL=r['wind_MW_per_GL'], utilisation=r['utilisation']))
    # imported RFNBO e-kerosene/e-diesel when domestic hourly-matched capacity binds (assumed premium over the dearest domestic RFNBO)
    rf_max = max(x['price'] for x in t if x['kind'] == 'efuel_rf')
    t.append(dict(name='efuel_rf_import', kind='efuel_rf', price=rf_max + n.rfnbo_import_premium_eur_l * efuel_mult, cap=1e15, kg=n.efuel_kWh_l * 0.012, groups={}))
    return sorted(t, key=lambda x: x['price'])


# ------------------------------------------------------------------------------------------------ V15 pooled comparison
def dispatch(tiers, demand_l):
    left = demand_l; use = {}; cost = 0.0; kg = 0.0; marg = tiers[0]['price']
    for t in tiers:
        q = min(left, t['cap'])
        if q > 0: use[t['name']] = q; cost += q * t['price']; kg += q * t['kg']; marg = t['price']; left -= q
        if left <= 0: break
    return dict(cost=cost, use=use, marginal=marg, avg=cost / demand_l if demand_l else 0.0, kg=kg)


def pooled_cost_fn(tiers, other):
    tiers = [dict(t, cap=min([t['cap']] + list(t.get('groups', {}).values()))) for t in tiers if not t['name'].startswith('efuel_rf_bio')]
    caps = np.array([min(t['cap'], 1e14) for t in tiers]); pr = np.array([t['price'] for t in tiers])
    qk = np.concatenate([[0], np.cumsum(caps)]); ck = np.concatenate([[0], np.cumsum(caps * pr)])
    f = lambda q: np.interp(q, qk, ck)
    return lambda q: f(other + q) - f(other)


# ------------------------------------------------------------------------------------------------ V17 fuel-specific LP
USES = ('jet', 'mar', 'road', 'exp')


def lp_fuels(n: Nat, tiers, A, Mar, truck_l, s_av, s_syn, red_mar, full=False):
    """Least-cost allocation of renewable liquids to jet, marine, road and export. Returns cost, use and dual prices.
    Policy: SAF >= s_av*A; synthetic jet >= s_syn*A; marine WtW intensity cut >= red_mar; road >= truck_l.
    Full (full=True): all jet, all marine and all truck fuel renewable."""
    P = len(tiers); U = len(USES); nv = P * U
    idx = lambda p, u: p * U + USES.index(u)
    c = np.zeros(nv); bounds = []
    jf = {'hefa': n.jet_frac_hefa, 'kelp': n.jet_frac_kelp, 'efuel_lc': n.jet_frac_efuel, 'efuel_rf': n.jet_frac_efuel}
    for p, t in enumerate(tiers):
        k = t['kind']
        for u in USES:
            add = 0.0
            if u == 'jet': add = n.jet_adder_hefa if k == 'hefa' else (n.jet_adder_kelp if k == 'kelp' else 0.0)
            if u == 'mar' and k == 'kelp': add = n.marine_adder_kelp
            c[idx(p, u)] = t['price'] + add - (n.export_value_eur_l if u == 'exp' else 0.0)
            bounds.append((0, 0) if (u == 'jet' and jf[k] <= 0) else (0, None))
    A_ub, b_ub, names = [], [], []
    for p, t in enumerate(tiers):                                   # supply caps
        r = np.zeros(nv); r[[idx(p, u) for u in USES]] = 1; A_ub.append(r); b_ub.append(min(t['cap'], 1e14)); names.append(f'cap_{t["name"]}')
        f = jf[t['kind']]                                            # jet fraction
        if f > 0:
            r = np.zeros(nv); r[[idx(p, u) for u in USES]] = -f; r[idx(p, 'jet')] += 1; A_ub.append(r); b_ub.append(0.0); names.append(f'jetfrac_{t["name"]}')
    gcaps = {}
    for t in tiers: gcaps.update(t.get('groups', {}))
    for g, cap in gcaps.items():                                   # shared caps: biogenic CO2; offshore wind per coast for RFNBO
        r = np.zeros(nv)
        for p, t in enumerate(tiers):
            if g in t.get('groups', {}): r[[idx(p, u) for u in USES]] = 1
        A_ub.append(r); b_ub.append(min(cap, 1e14)); names.append(f'group_{g}')
    r = np.zeros(nv); r[[idx(p, 'jet') for p in range(P)]] = -1; A_ub.append(r); b_ub.append(-(A if full else s_av * A)); names.append('saf')
    if not full and s_syn > 0:
        r = np.zeros(nv)
        for p, t in enumerate(tiers):
            if t['kind'] == 'efuel_rf' or (n.lc_counts_synthetic and t['kind'] == 'efuel_lc'): r[idx(p, 'jet')] = -1
        A_ub.append(r); b_ub.append(-s_syn * A); names.append('synthetic')
    r = np.zeros(nv)
    if full:
        r[[idx(p, 'mar') for p in range(P)]] = -1; A_ub.append(r); b_ub.append(-Mar); names.append('marine')
    else:   # sum q (I_f - I_p) >= red * I_f * Mar   (g/MJ x litres; MJ per litre cancels)
        for p, t in enumerate(tiers): r[idx(p, 'mar')] = -(n.fueleu_ref_g_MJ - t['kg'] * 1000 / MJ_L)
        A_ub.append(r); b_ub.append(-red_mar * n.fueleu_ref_g_MJ * Mar); names.append('marine')
    r = np.zeros(nv); r[[idx(p, 'road') for p in range(P)]] = -1; A_ub.append(r); b_ub.append(-truck_l); names.append('road')
    for u, lim in (('jet', A), ('mar', Mar)):                        # cannot burn more than the demand
        r = np.zeros(nv); r[[idx(p, u) for p in range(P)]] = 1; A_ub.append(r); b_ub.append(lim); names.append(f'max_{u}')
    # solve in billions of litres (coefficients O(1)); objective in EUR bn; duals in EUR per litre
    res = linprog(c, A_ub=np.array(A_ub), b_ub=np.array(b_ub) / 1e9, bounds=bounds, method='highs')
    if res.status != 0: raise RuntimeError(res.message)
    x = res.x * 1e9
    q = {(t['name'], u): float(x[idx(p, u)]) for p, t in enumerate(tiers) for u in USES}
    duals = {nm: -float(m) for nm, m in zip(names, res.ineqlin.marginals)}   # EUR per litre (or per litre-g/MJ for marine)
    use_by = {u: sum(v for (p, uu), v in q.items() if uu == u) for u in USES}
    kg_by = {u: sum(v * next(t['kg'] for t in tiers if t['name'] == p) for (p, uu), v in q.items() if uu == u) for u in USES}
    marine_eur_l_efuel = duals['marine'] * (n.fueleu_ref_g_MJ - next(t['kg'] for t in tiers if t['kind'] == 'efuel_lc') * 1000 / MJ_L) if not full else duals['marine']
    tot_t = {t['name']: sum(q[(t['name'], u)] for u in USES) for t in tiers}
    rf_GL = sum(v for k, v in tot_t.items() if k.startswith('efuel_rf')) / 1e9; lc_GL = sum(v for k, v in tot_t.items() if k.startswith('efuel_lc')) / 1e9
    elz_GW = sum(tot_t[t['name']] / 1e9 * t.get('elz_MW_per_GL', 0) for t in tiers) / 1000
    wind_GW = sum(tot_t[t['name']] / 1e9 * t.get('wind_MW_per_GL', 0) for t in tiers) / 1000
    return dict(cost=float(res.fun) * 1e9, q=q, rfnbo_GL=rf_GL, lowcarbon_GL=lc_GL, electrolyser_GW=elz_GW, rfnbo_wind_GW=wind_GW,
                rfnbo_TWh=rf_GL * n.efuel_kWh_l, lowcarbon_TWh=lc_GL * n.efuel_kWh_l, use=use_by, kg=kg_by, duals=duals,
                marginal_road=duals['road'], marginal_saf=duals['saf'], marginal_synth=duals.get('synthetic', 0.0),
                marginal_marine_eur_t=duals['marine'] / (1e-6 * MJ_L) if not full else None, marginal_marine_eur_l=marine_eur_l_efuel)


def lp_cost_fn(n, tiers, A, Mar, s_av, s_syn, red_mar, full=False, qmax=12e9):
    """Incremental cost of truck road fuel on top of the mandated aviation and marine demand (piecewise linear in demand)."""
    grid = np.concatenate([np.arange(0, 3e9, 0.05e9), np.arange(3e9, qmax + 1, 0.5e9)])
    cost = np.array([lp_fuels(n, tiers, A, Mar, q, s_av, s_syn, red_mar, full)['cost'] for q in grid])
    base = cost[0]
    return (lambda q: np.interp(q, grid, cost) - base), grid, cost


# ------------------------------------------------------------------------------------------------ sweet spot (3-D grid)
L_GRID = np.arange(0, 15001, 250.0)
B_GRID = np.arange(0, 1001, 20.0)
BR_GRID = np.arange(0, 1001, 20.0)


def sweet_spot(n, e, fuel_cost, batt_eur_kWh=None, L_grid=None):
    Lg = L_GRID if L_grid is None else np.atleast_1d(L_grid)
    LL, BB, RR = np.meshgrid(Lg, B_GRID, BR_GRID, indexing='ij')
    h = hgv(n, e, LL, BB, RR, batt_eur_kWh)
    tot = h['nonfuel'] + fuel_cost(h['litres'])
    i, j, k = np.unravel_index(np.argmin(tot), tot.shape)
    best = {kk: float(v[i, j, k]) for kk, v in h.items()}
    best.update(L=float(Lg[i]), B=float(B_GRID[j]), B_r=float(BR_GRID[k]), total=float(tot[i, j, k]))
    flat = tot.reshape(len(Lg), -1); am = flat.argmin(axis=1)
    curve = [dict(L=float(Lg[a]), B=float(B_GRID[np.unravel_index(am[a], tot.shape[1:])[0]]), B_r=float(BR_GRID[np.unravel_index(am[a], tot.shape[1:])[1]]),
                  total=float(flat[a, am[a]]), litres=float(h['litres'].reshape(len(Lg), -1)[a, am[a]])) for a in range(len(Lg))]
    surf = tot.min(axis=2)       # L x B_lh with regional battery optimised
    return best, surf, curve


def evaluate_case(n, e, inp, sy, mode='policy', y=2041, kelp=None, method='lp', fixed_price=None, **supply_kw):
    A, Mar = base_litres(n, y)
    full = mode == 'full'
    s_av, s_syn, red = (1.0, 0.0, 1.0) if full else (mandate(REFUEL, y), mandate(SYNTH, y), mandate(FUELEU, y))
    kelp = kelp_tiers(inp, sy, n) if kelp is None else kelp
    tiers = supply_curve(n, kelp, sy=sy, **supply_kw)
    if fixed_price is not None:
        fc = lambda q: q * fixed_price
    elif method == 'pooled':
        other = A * s_av + Mar * (1.0 if full else red); fc = pooled_cost_fn(tiers, other)
    else:
        fc, _, _ = lp_cost_fn(n, tiers, A, Mar, s_av, s_syn, red, full)
    best, surf, curve = sweet_spot(n, e, fc)
    base = diesel_baseline(n, e)
    out = dict(year=y, mode=mode, method=method, aviation_GL=A / 1e9, maritime_GL=Mar / 1e9, share_aviation=s_av, share_synthetic=s_syn, marine_reduction=red,
               design=best, curve=curve, surface=surf)
    nb, _, _ = sweet_spot(n, e, fc, L_grid=[0.0])
    out['no_ers'] = dict(L=0.0, B=nb['B'], B_r=nb['B_r'], total_bn=nb['total'] / 1e9, litres_GL=nb['litres'] / 1e9, gen_share=nb['gen_share'])
    out['ers_value_bn'] = nb['total'] / 1e9 - best['total'] / 1e9
    if method == 'lp' and fixed_price is None:
        lp = lp_fuels(n, tiers, A, Mar, best['litres'], s_av, s_syn, red, full)
        lp0 = lp_fuels(n, tiers, A, Mar, 0.0, s_av, s_syn, red, full)
        q = lp['q']
        out.update(liquid_cost_bn=lp['cost'] / 1e9, liquid_cost_without_trucks_bn=lp0['cost'] / 1e9,
                   use_GL={u: v / 1e9 for u, v in lp['use'].items()},
                   supply_GL={t['name']: sum(q[(t['name'], u)] for u in USES) / 1e9 for t in tiers},
                   alloc_GL={f'{p}|{u}': v / 1e9 for (p, u), v in q.items() if v > 1e3},
                   marginal_road=lp['marginal_road'], marginal_saf=lp['marginal_saf'], marginal_synth=lp['marginal_synth'],
                   marginal_marine_eur_t=lp['marginal_marine_eur_t'], marginal_marine_eur_l=lp['marginal_marine_eur_l'],
                   kg_by_use=lp['kg'], liquid_total_GL=sum(lp['use'].values()) / 1e9,
                   renewable_mandated_GL=(lp['use']['jet'] + lp['use']['mar'] + lp['use']['road']) / 1e9,
                   kelp_hubs=sum(sum(q[(t['name'], u)] for u in USES) / t['litres_per_hub'] for t in tiers if t['kind'] == 'kelp'),
                   efuel_TWh=sum(sum(q[(t['name'], u)] for u in USES) for t in tiers if t['kind'].startswith('efuel')) * n.efuel_kWh_l / 1e9,
                   rfnbo_GL=lp['rfnbo_GL'], lowcarbon_GL=lp['lowcarbon_GL'], rfnbo_TWh=lp['rfnbo_TWh'], lowcarbon_TWh=lp['lowcarbon_TWh'],
                   electrolyser_GW=lp['electrolyser_GW'], rfnbo_wind_GW=lp['rfnbo_wind_GW'],
                   rfnbo_sites=[dict(key=r['key'], price_ex_co2=r['price'], utilisation=r['utilisation'], r=r['r'], cap_GL=r['cap_L'] / 1e9) for r in rfnbo_sites(n, sy)])
        out['kelp_area_km2'] = out['kelp_hubs'] * 100.0
        out['marginal_eur_l'] = lp['marginal_road']
        tl = best['litres']; truck_fuel = fc(tl)
    else:
        tl = best['litres']; truck_fuel = fc(tl)
        out['marginal_eur_l'] = (fc(tl + 1e6) - fc(tl)) / 1e6
    hgv_cost = best['nonfuel'] + truck_fuel
    hgv_co2 = best['elec_TWh'] * n.grid_kgCO2_kWh + tl * 0.3 / 1e9
    out.update(hgv_cost_bn=hgv_cost / 1e9, hgv_diesel_cost_bn=base['cost'] / 1e9, hgv_saving_bn=(base['cost'] - hgv_cost) / 1e9,
               hgv_co2_Mt=hgv_co2, hgv_co2_avoided_Mt=base['co2_Mt'] - hgv_co2, truck_fuel_cost_bn=truck_fuel / 1e9,
               truck_fuel_avg_eur_l=truck_fuel / tl if tl > 0 else 0.0,
               tiers=[dict(name=t['name'], kind=t['kind'], price=t['price'], cap_GL=min([t['cap'], 1e14] + list(t.get('groups', {}).values())) / 1e9, kg=t['kg']) for t in tiers])
    return out


# ------------------------------------------------------------------------------------------------ levers (hub chain unchanged from V15)
def kelp_mean_price(inp, sy):
    ev = S.evaluate(inp, sy); rr = [r for r in ev['rows'] if r['option'] == 'hybrid' and r['drones']]
    return sum(r['fuel_eur_l'] * r['litres'] for r in rr) / sum(r['litres'] for r in rr)


def kelp_levers(inp, sy):
    p6 = inp.p6; base = kelp_mean_price(inp, sy); fin = crf(0.03, 20) / crf(0.06, 20)
    L = [('Farm-gate seaweed cost 400 -> 250 EUR/t (mechanised longlines, learning)', dict(p6=dict(seaweed_dry_cost_eur_t=250.0))),
         ('HTL fuel yield +20 % (catalytic HTL, aqueous-phase recycle)', dict(sy=dict(fuel_yield_mult=1.2))),
         ('HTL plant cost 0.45 -> 0.32 EUR/L (nth-of-a-kind, 3x scale)', dict(p6=dict(HTL_other_eur_L=0.32))),
         ('Finance at 3 % instead of 6 % (farm and HTL capital)', dict(p6=dict(seaweed_dry_cost_eur_t=400 * (0.5 + 0.5 * fin), HTL_other_eur_L=0.45 * (0.4 + 0.6 * fin)))),
         ('Marine harvest 70 -> 50 EUR/t (electric Grid Harvester at scale)', dict(p6=dict(harvest_marine_eur_t=50.0))),
         ('Turbine anchors carry 75 % of farm moorings', dict(sy=dict(anchor_shared_frac=0.75))),
         ('SMR electricity 105 -> 80 EUR/MWh (series build)', dict(p6=dict(nuclear_electric_eur_MWh=80.0))),
         ('Kelp yield +30 % (breeding)', dict(yield_mult=1.3))]
    out = []
    for lab, kw in L:
        i2 = replace(inp, p6=replace(p6, **kw.get('p6', {})), yield_mult=kw.get('yield_mult', inp.yield_mult)); s2 = replace(sy, **kw.get('sy', {}))
        p = kelp_mean_price(i2, s2); out.append(dict(lever=lab, price=p, delta=p - base))
    i_all = replace(inp, p6=replace(p6, seaweed_dry_cost_eur_t=250 * (0.5 + 0.5 * fin), HTL_other_eur_L=0.32 * (0.4 + 0.6 * fin), harvest_marine_eur_t=50.0, nuclear_electric_eur_MWh=80.0), yield_mult=1.3)
    s_all = replace(sy, anchor_shared_frac=0.75, fuel_yield_mult=1.2)
    return base, sorted(out, key=lambda r: r['delta']), kelp_mean_price(i_all, s_all), i_all, s_all


def efuel_levers(n: Nat):
    base = efuel_price(n, n.co2_dac_eur_t)   # low-carbon (baseload) e-fuel with DAC CO2
    L = [('CO2 from biogenic point sources instead of DAC', dict(co2_dac_eur_t=n.co2_bio_eur_t)),
         ('Electrolyser power 70 -> 50 EUR/MWh (surplus nuclear and wind, 92 TWh exported in 2025)', dict(efuel_el_eur_MWh=50.0)),
         ('Plant cost 0.70 -> 0.45 EUR/L (electrolyser learning, scale)', dict(efuel_capex_eur_l=0.45)),
         ('Efficiency 20 -> 17 kWh/L (SMR/HTL steam to high-temperature electrolysis)', dict(efuel_kWh_l=17.0)),
         ('DAC 250 -> 150 EUR/t', dict(co2_dac_eur_t=150.0))]
    out = []
    for lab, kw in L:
        n2 = replace(n, **kw); p = efuel_price(n2, n2.co2_dac_eur_t); out.append(dict(lever=lab, price=p, delta=p - base))
    n_all = replace(n, co2_dac_eur_t=150.0, efuel_el_eur_MWh=50.0, efuel_capex_eur_l=0.45, efuel_kWh_l=17.0)
    return base, sorted(out, key=lambda r: r['delta']), efuel_price(n_all, n_all.co2_dac_eur_t), efuel_price(n_all, n_all.co2_bio_eur_t), n_all


# ------------------------------------------------------------------------------------------------ transition
def transition(n: Nat, e: M.ERS, inp, sy, L_star, B_star, Br_star, hubs_star, kelp=None, full_build_2041=False, kelp_wind=None):
    rows = []; ldv = n.ldv_bev_fleet_2026; hyb = 0.0
    kelp = kelp_tiers(inp, sy, n) if kelp is None else kelp
    kelp_wind = kelp_tiers(inp, sy, n, option='wind') if kelp_wind is None else kelp_wind
    order = [t['name'] for t in sorted(kelp, key=lambda t: t['price'])]     # hubs are sited at the coasts cheapest once the reactor runs
    km_prev = 0.0; cum_co2 = 0.0; cum_capex = 0.0
    base_total = n.co2_passenger_land + n.co2_freight_land + n.co2_aviation + n.co2_maritime
    s0 = logistic(2027, 2034.0, 1.8)
    for y in YEARS:
        sales = n.ldv_bev_sales_2027 + (n.ldv_bev_sales_2035 - n.ldv_bev_sales_2027) * min(1, max(0, (y - 2027) / 8))
        ldv = ldv * (1 - 1 / n.ldv_fleet_life_y) + sales / n.ldv_fleet_life_y
        km = L_star * max(0.0, (logistic(y, 2034.0, 1.8) - s0) / (logistic(2041, 2034.0, 1.8) - s0))
        sales_h = logistic(y, n.hyb_sales_mid_year, n.hyb_sales_slope_y, 0.0, 0.98)
        hyb = hyb * (1 - 1 / n.hgv_life_y) + sales_h / n.hgv_life_y
        pb = n.batt_eur_kWh_2027 + (n.batt_eur_kWh_2041 - n.batt_eur_kWh_2027) * (y - 2027) / 14
        h = hgv(n, e, km, B_star, Br_star, pb)
        hyb_liq = float(h['litres']) * hyb
        diesel_l = e.hgv_vkm_bn * 1e9 * (1 - hyb) * e.diesel_l_per_km
        A, Mar = base_litres(n, y); sav, ssyn, red = mandate(REFUEL, y), synth_share(n, y), mandate(FUELEU, y)
        hefa_cap = n.hefa_cap_GL * min(1.0, 0.35 + 0.65 * (y - 2027) / 3) * 1e9
        # V18: pilots one per coast 2030-2035 (wind-first, SMR from 2035); expansion to hubs_star only if the cost levers are met
        if n.hub_start == 'smr_first':   # V19: no wind-only stage; hubs built with the reactor from 2035, reaching hubs_star in 2040
            hubs = 0.0 if y < 2035 else min(hubs_star, max(hubs_star, 6.0) * (y - 2034) / 6)
        else:
            hubs = 0.0 if y < 2030 else (min(hubs_star, y - 2029) if hubs_star <= 6 else (min(6.0, y - 2029) if y < 2035 else 6 + (hubs_star - 6) * (y - 2035) / 6))
        src = {t['name']: t for t in (kelp_wind if y < n.kelp_wind_only_until else kelp)}   # V19: wind-only economics before the SMR enters service
        kelp_sorted = [src[k] for k in order]
        bio_cap = n.co2_bio_cap_Mt * min(1.0, max(0.0, (y - 2029) / 11))
        ef_mult = 1.0 + 0.6 * max(0, 2041 - y) / 14
        tiers = [dict(name='hefa', kind='hefa', price=n.hefa_eur_l, cap=hefa_cap, kg=n.hefa_kgCO2_l)]
        left = hubs
        for t in kelp_sorted:            # built hubs dispatch on variable cost; their fixed cost is charged below whether used or not
            q = min(left, t['hubs']); left -= q
            tiers.append(dict(t, cap=t['litres_per_hub'] * max(q, 0.0), price=t['price'] * (1 - n.kelp_fixed_share), full_price=t['price']))
        ef = [t for t in supply_curve(n, [], sy=sy, bio_cap_Mt=bio_cap, efuel_mult=ef_mult, rf_scale=min(1.0, max(0.0, (y - 2029) / 12))) if t['kind'].startswith('efuel')]
        for t in tiers: t['groups'] = {}
        tiers = tiers + ef
        lp = lp_fuels(n, tiers, A, Mar, hyb_liq, sav, ssyn, red)
        kelp_cap = sum(t['cap'] for t in tiers if t['kind'] == 'kelp'); kelp_used = sum(v for (p_, uu), v in lp['q'].items() if p_.startswith('kelp'))
        kelp_fixed = sum(t['full_price'] * n.kelp_fixed_share * t['cap'] for t in tiers if t['kind'] == 'kelp')
        idle_cost = kelp_fixed * (1 - kelp_used / kelp_cap) if kelp_cap > 0 else 0.0
        u, kgu = lp['use'], lp['kg']
        sup = lambda kind: sum(v for (p, uu), v in lp['q'].items() if uu != 'exp' and p.startswith(kind)) / 1e9
        co2_ldv = (n.co2_passenger_land + n.co2_freight_land - n.co2_hgv) * (1 - ldv) / (1 - n.ldv_bev_fleet_2024) + n.ldv_full_electric_TWh * (ldv - n.ldv_bev_fleet_2024) * n.grid_kgCO2_kWh
        co2_hgv = (diesel_l * n.diesel_kgCO2_l + kgu['road']) / 1e9 + float(h['elec_TWh']) * hyb * n.grid_kgCO2_kWh
        co2_av = ((A - u['jet']) * n.jet_kgCO2_l + kgu['jet']) / 1e9
        co2_ma = ((Mar - u['mar']) * n.marine_kgCO2_l + kgu['mar']) / 1e9
        tot = co2_ldv + co2_hgv + co2_av + co2_ma; cum_co2 += base_total - tot
        road_cost = lp['cost'] - lp_fuels(n, tiers, A, Mar, 0.0, sav, ssyn, red)['cost']
        hgv_extra = (float(h['infra']) + (float(h['vehicles']) + float(h['energy'])) * hyb + road_cost - e.hgv_vkm_bn * 1e9 * hyb * e.diesel_l_per_km * e.diesel_longrun_eur_l) / 1e9
        liq_premium = (lp['cost'] - road_cost + kelp_fixed - (u['jet'] * n.jet_fossil_eur_l + u['mar'] * n.marine_fossil_eur_l)) / 1e9
        ers_capex = (km - km_prev) * e.capex_eur_km / 1e9; cum_capex += ers_capex
        rows.append(dict(year=y, ldv_bev_fleet=ldv, ers_km=km, ers_built_km=km - km_prev, hybrid_fleet=hyb, hybrid_sales=sales_h, battery_eur_kWh=pb,
                         gen_share=float(h['gen_share']), hyb_fuel_GL=hyb_liq / 1e9, diesel_GL=diesel_l / 1e9, saf_share=sav, synthetic_share=ssyn, maritime_reduction=red,
                         jet_GL=u['jet'] / 1e9, marine_GL=u['mar'] / 1e9, road_GL=u['road'] / 1e9, export_GL=u['exp'] / 1e9,
                         renewable_GL=(u['jet'] + u['mar'] + u['road']) / 1e9, hubs=hubs, hefa_GL=sup('hefa'), kelp_GL=sup('kelp'), efuel_GL=sup('efuel'),
                         marginal_road=lp['marginal_road'], marginal_saf=lp['marginal_saf'], co2_ldv=co2_ldv, co2_hgv=co2_hgv, co2_aviation=co2_av, co2_maritime=co2_ma,
                         co2_total=tot, co2_reduction_vs_2024=1 - tot / base_total, cum_co2_avoided_Mt=cum_co2,
                         elec_TWh=n.ldv_full_electric_TWh * ldv + float(h['elec_TWh']) * hyb + sum(v for (p, uu), v in lp['q'].items() if p.startswith('efuel')) * n.efuel_kWh_l / 1e9,
                         kelp_capacity_GL=kelp_cap / 1e9, kelp_utilisation=(kelp_used / kelp_cap if kelp_cap > 0 else 0.0), kelp_idle_cost_bn=idle_cost / 1e9, kelp_fixed_cost_bn=kelp_fixed / 1e9,
                         rfnbo_GL=lp['rfnbo_GL'], lowcarbon_GL=lp['lowcarbon_GL'], rfnbo_TWh=lp['rfnbo_TWh'], lowcarbon_TWh=lp['lowcarbon_TWh'],
                         electrolyser_GW=lp['electrolyser_GW'], rfnbo_wind_GW=lp['rfnbo_wind_GW'], ldv_TWh=n.ldv_full_electric_TWh * ldv, hgv_TWh=float(h['elec_TWh']) * hyb,
                         hgv_extra_cost_bn=hgv_extra, liquid_premium_bn=liq_premium, ers_capex_bn=ers_capex, cum_ers_capex_bn=cum_capex))
        km_prev = km
    return rows


# ------------------------------------------------------------------------------------------------ Monte Carlo
MC = {'capex_eur_km': ('e', 2.0e6, 3.4e6, 4.8e6), 'elec_eur_MWh': ('e', 65, 105, 150), 'capture_max': ('e', .40, .55, .65), 'on_wire_share': ('e', .60, .75, .85),
      'batt_eur_kWh_2041': ('n', 80, 120, 200), 'hyb_premium_eur': ('n', 20000, 30000, 50000),
      'leg_min_km': ('n', 40, 60, 200), 'leg_max_km': ('n', 300, 400, 500), 'regional_share': ('n', 0.20, 0.30, 0.40), 'regional_leg_km': ('n', 150, 250, 350),
      'efuel_el_eur_MWh': ('n', 45, 70, 110), 'efuel_capex_eur_l': ('n', 0.45, 0.70, 1.20), 'co2_dac_eur_t': ('n', 120, 250, 450), 'hefa_cap_GL': ('n', 0.6, 1.2, 2.0),
      'export_value_eur_l': ('n', 0.60, 0.90, 1.20), 'rfnbo_gw_per_coast': ('n', 1.0, 2.0, 4.0), 'jet_frac_efuel': ('n', 0.50, 0.60, 0.75), 'demand_growth_aviation': ('n', -0.01, 0.0, 0.015)}


def monte_carlo(n, e, inp, sy, kelp, draws=400, seed=20261112):
    rng = np.random.default_rng(seed); out = []
    for _ in range(draws):
        n2, e2 = n, e; dr = {}
        for k, (o, lo, mo, hi) in MC.items():
            v = float(rng.triangular(lo, mo, hi)); dr[k] = v
            if o == 'n': n2 = replace(n2, **{k: v})
            else: e2 = replace(e2, **{k: v})
        r = evaluate_case(n2, e2, inp, sy, 'policy', kelp=kelp)
        out.append(dict(dr, L=r['design']['L'], B=r['design']['B'], B_r=r['design']['B_r'], gen_share=r['design']['gen_share'], hgv_saving_bn=r['hgv_saving_bn'],
                        marginal_road=r['marginal_road'], marginal_saf=r['marginal_saf'], marginal_synth=r['marginal_synth'], ers_value_bn=r['ers_value_bn'], liquid_cost_bn=r['liquid_cost_bn']))
    q = lambda k: [float(np.percentile([o[k] for o in out], p)) for p in (5, 50, 95)]
    return out, dict(L=q('L'), B=q('B'), B_r=q('B_r'), gen_share=q('gen_share'), hgv_saving_bn=q('hgv_saving_bn'), marginal_road=q('marginal_road'),
                     marginal_saf=q('marginal_saf'), marginal_synth=q('marginal_synth'), ers_value_bn=q('ers_value_bn'), share_L_ge_5000=float(np.mean([o['L'] >= 5000 for o in out])),
                     share_saving_pos=float(np.mean([o['hgv_saving_bn'] > 0 for o in out])), share_ers_value_pos=float(np.mean([o['ers_value_bn'] > 0 for o in out])))


def write_csv(name, rows):
    rows = [{k: v for k, v in r.items() if not isinstance(v, (dict, list, np.ndarray))} for r in rows]
    with open(D / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def strip(r): return {k: v for k, v in r.items() if k not in ('curve', 'surface')}


def main():
    inp = M.Inputs(); sy = S.Sys(); n = Nat(); e = inp.e
    kelp = kelp_tiers(inp, sy, n)
    pol = evaluate_case(n, e, inp, sy, 'policy', kelp=kelp)
    full = evaluate_case(n, e, inp, sy, 'full', kelp=kelp)
    pooled = evaluate_case(n, e, inp, sy, 'policy', kelp=kelp, method='pooled')
    pooled_full = evaluate_case(n, e, inp, sy, 'full', kelp=kelp, method='pooled')
    kelp_jet = evaluate_case(replace(n, jet_frac_kelp=0.20), e, inp, sy, 'policy', kelp=kelp)
    rf_only = evaluate_case(replace(n, lc_counts_synthetic=False), e, inp, sy, 'policy', kelp=kelp)   # V19: RFNBO-only procurement scenario
    # sweet spot vs liquid price
    sweep = []
    for p in np.arange(1.0, 4.51, 0.25):
        b, _, _ = sweet_spot(n, e, lambda q, p=p: q * float(p))
        sweep.append(dict(price=float(p), L=b['L'], B=b['B'], B_r=b['B_r'], gen_share=b['gen_share'], litres_GL=b['litres'] / 1e9, elec_TWh=b['elec_TWh'], cost_bn=b['total'] / 1e9))
    write_csv('v19_sweetspot_vs_liquid_price.csv', sweep)
    np.savetxt(D / 'v19_cost_surface_policy_bnEUR.csv', pol['surface'] / 1e9, delimiter=',', fmt='%.4f',
               header='rows: ERS km ' + ' '.join(str(int(x)) for x in L_GRID) + ' | cols: long-haul battery kWh ' + ' '.join(str(int(x)) for x in B_GRID) + ' | regional battery optimised')
    write_csv('v19_cost_vs_network_policy.csv', pol['curve'])
    # off-wire journey sensitivity (referee): long-haul minimum leg x regional duty
    legs = []
    for lm in (40, 60, 90, 120, 160, 200):
        for rl in (150, 250, 350):
            r = evaluate_case(replace(n, leg_min_km=float(lm), regional_leg_km=float(rl)), e, inp, sy, 'policy', kelp=kelp)
            legs.append(dict(leg_min_km=lm, regional_leg_km=rl, L=r['design']['L'], B=r['design']['B'], B_r=r['design']['B_r'], gen_share=r['design']['gen_share'],
                             litres_GL=r['design']['litres'] / 1e9, hgv_saving_bn=r['hgv_saving_bn'], ers_value_bn=r['ers_value_bn'], marginal_road=r['marginal_road']))
    write_csv('v19_offwire_leg_sensitivity.csv', legs)
    print('legs', [(l['leg_min_km'], l['regional_leg_km'], l['L'], l['B'], l['B_r'], round(l['gen_share'], 3), round(l['hgv_saving_bn'], 2)) for l in legs])
    # levers
    kb, kl, kall, i_all, s_all = kelp_levers(inp, sy)
    eb, el, eall_dac, eall_bio, n_ef = efuel_levers(n)
    kelp_opt = kelp_tiers(i_all, s_all, n)
    pol_opt = evaluate_case(n_ef, e, inp, sy, 'policy', kelp=kelp_opt)
    full_opt = evaluate_case(n_ef, e, inp, sy, 'full', kelp=kelp_opt)
    n_dem = replace(n, co2_aviation=n.co2_aviation * 0.75, co2_maritime=n.co2_maritime * 0.85 * 0.80)
    full_dem = evaluate_case(n_dem, e, inp, sy, 'full', kelp=kelp)
    write_csv('v19_liquid_price_levers.csv', [dict(chain='kelp HTL hub', **r) for r in kl] + [dict(chain='e-fuel (DAC CO2)', **r) for r in el])
    # pool effect of truck electrification (full case, fuel-specific LP)
    A, Mar = base_litres(n); tiers_c = supply_curve(n, kelp, sy=sy); pool = {}
    for lab, lit in (('sweet_spot', full['design']['litres']), ('no_ers', full['no_ers']['litres_GL'] * 1e9), ('generator_only', e.hgv_vkm_bn * 1e9 * n.gen_l_per_km)):
        r = lp_fuels(n, tiers_c, A, Mar, lit, 1, 0, 1, True)
        pool[lab] = dict(truck_GL=lit / 1e9, pool_cost_bn=r['cost'] / 1e9, marginal_road=r['marginal_road'])
    # joint capital x capture
    joint = []
    for cm in (1.0, 1.2, 1.4, 1.6):
        for km_ in (1.0, 0.9, 0.8, 0.7):
            r = evaluate_case(n, replace(e, capex_eur_km=e.capex_eur_km * cm, capture_max=e.capture_max * km_), inp, sy, 'policy', kelp=kelp)
            joint.append(dict(capex_mult=cm, capture_mult=km_, L=r['design']['L'], B=r['design']['B'], B_r=r['design']['B_r'], gen_share=r['design']['gen_share'],
                              hgv_saving_bn=r['hgv_saving_bn'], ers_value_bn=r['ers_value_bn']))
    write_csv('v19_sweetspot_joint_sensitivity.csv', joint)
    # transition
    # V18: kelp-hub build size chosen by total 2027-2041 transition cost (built hubs dispatch on variable cost, fixed cost always paid)
    # V19: every integer build 0-36 under two commissioning schedules; early hubs priced on wind-only economics
    tcost = lambda t_: sum(x['liquid_premium_bn'] + x['hgv_extra_cost_bn'] for x in t_)
    def scan(nn, ii, ss, kk, des, kw=None):
        out = []
        for start in ('wind_first', 'smr_first'):
            for hs in range(0, 37):
                t_ = transition(replace(nn, hub_start=start), e, ii, ss, des['L'], des['B'], des['B_r'], float(hs), kelp=kk, kelp_wind=kw)
                out.append(dict(start=start, hubs=float(hs), cost_bn=tcost(t_), co2_cum_Mt=sum(x['co2_total'] for x in t_), kelp_2041_GL=t_[-1]['kelp_GL']))
        return out
    kelp_w = kelp_tiers(inp, sy, n, option='wind')
    hub_scan = scan(n, inp, sy, kelp, pol['design'], kelp_w)
    best = min(hub_scan, key=lambda r: r['cost_bn']); hubs_best, start_best = best['hubs'], best['start']
    n = replace(n, hub_start=start_best)
    tr = transition(n, e, inp, sy, pol['design']['L'], pol['design']['B'], pol['design']['B_r'], hubs_best, kelp=kelp, kelp_wind=kelp_w)
    tr_28 = transition(n, e, inp, sy, pol['design']['L'], pol['design']['B'], pol['design']['B_r'], max(pol['kelp_hubs'], 6.0), kelp=kelp, kelp_wind=kelp_w)
    tr_flat = transition(replace(n, synth_schedule='flat'), e, inp, sy, pol['design']['L'], pol['design']['B'], pol['design']['B_r'], hubs_best, kelp=kelp, kelp_wind=kelp_w)
    tr_rf = transition(replace(n, lc_counts_synthetic=False), e, inp, sy, pol['design']['L'], pol['design']['B'], pol['design']['B_r'], hubs_best, kelp=kelp, kelp_wind=kelp_w)
    tr_hyb_early = transition(n, e, inp, sy, pol['design']['L'], pol['design']['B'], pol['design']['B_r'], hubs_best, kelp=kelp, kelp_wind=kelp)   # V18 pricing, for the record
    write_csv('v19_transition_2027_2041.csv', tr)
    kelp_opt_w = kelp_tiers(i_all, s_all, n, option='wind')
    hub_scan_opt = scan(n_ef, i_all, s_all, kelp_opt, pol_opt['design'], kelp_opt_w)
    best_o = min(hub_scan_opt, key=lambda r: r['cost_bn']); hubs_best_opt, start_best_opt = best_o['hubs'], best_o['start']
    tr_opt = transition(replace(n_ef, hub_start=start_best_opt), e, i_all, s_all, pol_opt['design']['L'], pol_opt['design']['B'], pol_opt['design']['B_r'], hubs_best_opt, kelp=kelp_opt, kelp_wind=kelp_opt_w)
    mc, mcs = monte_carlo(n, e, inp, sy, kelp)
    write_csv('v19_sweetspot_monte_carlo.csv', mc)
    res = dict(scope='V19: national sweet spot with fuel-specific balances (aviation, shipping, road), two truck classes, step mandates, 2027-2041 transition',
               assumptions=asdict(n), refuel=REFUEL, synthetic=SYNTH, fueleu=FUELEU, policy=strip(pol), full=strip(full), pooled=strip(pooled), pooled_full=strip(pooled_full),
               kelp_jet_sensitivity=strip(kelp_jet), rfnbo_only_sensitivity=strip(rf_only), synth_path={y: synth_share(n, y) for y in YEARS}, lc_gCO2_MJ=lc_gCO2_MJ(n),
               hub_scan=hub_scan, hubs_best=hubs_best, hub_start_best=start_best, hub_scan_optimised=hub_scan_opt, hubs_best_optimised=hubs_best_opt, hub_start_best_optimised=start_best_opt,
               transition_flat_synth_cost_bn=tcost(tr_flat), transition_rfnbo_only_cost_bn=tcost(tr_rf), transition_rfnbo_only_2041=tr_rf[-1], transition_hybrid_early_cost_bn=tcost(tr_hyb_early),
               kelp_wind_tiers=[dict(name=t['name'], price=t['price']) for t in kelp_w],
               early_kelp_wind_GL=sum(t['kelp_GL'] for t in tr if t['year'] < n.kelp_wind_only_until),
               transition_28hubs_cost_bn=sum(x['liquid_premium_bn'] + x['hgv_extra_cost_bn'] for x in tr_28), transition_cost_bn=sum(x['liquid_premium_bn'] + x['hgv_extra_cost_bn'] for x in tr),
               transition_28hubs_2041=tr_28[-1], transition_28hubs_idle_cost_bn=sum(t['kelp_idle_cost_bn'] for t in tr_28), transition_idle_cost_bn=sum(t['kelp_idle_cost_bn'] for t in tr),
               transition_optimised_kelp=[dict(year=t['year'], hubs=t['hubs'], kelp_GL=t['kelp_GL'], util=t['kelp_utilisation']) for t in tr_opt], policy_optimised=strip(pol_opt), full_optimised=strip(full_opt), full_demand_measures=strip(full_dem), sweep=sweep,
               offwire_legs=legs, kelp_levers=dict(base=kb, levers=kl, all=kall),
               efuel_levers=dict(base_dac=eb, base_bio=efuel_price(n, n.co2_bio_eur_t), levers=el, all_dac=eall_dac, all_bio=eall_bio),
               demand_levers=dict(base_cost_bn=full['liquid_cost_bn'], measures_cost_bn=full_dem['liquid_cost_bn'], base_GL=full['liquid_total_GL'], measures_GL=full_dem['liquid_total_GL']),
               pool_effect=pool, joint_sensitivity=joint, transition=tr, transition_optimised_2041=tr_opt[-1],
               monte_carlo=dict(n=len(mc), seed=20261112, inputs=list(MC), **mcs),
               baseline_2024=dict(total=n.co2_passenger_land + n.co2_freight_land + n.co2_aviation + n.co2_maritime))
    json.dump(res, open(D / 'v19_sweetspot_results.json', 'w'), indent=1, default=float)
    print('RFNBO sites', [(r['key'], round(r['price_ex_co2'], 2), round(r['utilisation'], 2), round(r['cap_GL'], 2)) for r in pol['rfnbo_sites']])
    print('rf_only SAF %.2f synth %.2f cost %.2f vs %.2f' % (rf_only['marginal_saf'], rf_only['marginal_synth'], rf_only['liquid_cost_bn'], pol['liquid_cost_bn']), 'policy synth dual', pol['marginal_synth'], 'rf GL', pol['rfnbo_GL'], 'lc GL', pol['lowcarbon_GL'], 'elz GW', pol['electrolyser_GW'], 'wind GW', pol['rfnbo_wind_GW'])
    print('28-hub transition 2041 util %.2f idle cost total %.2f; pilots idle total %.2f' % (tr_28[-1]['kelp_utilisation'], sum(t['kelp_idle_cost_bn'] for t in tr_28), sum(t['kelp_idle_cost_bn'] for t in tr)))
    print('flat synth', tcost(tr_flat), 'central', tcost(tr), 'rf_only', tcost(tr_rf), 'hybrid-early', tcost(tr_hyb_early), 'synth path', [(y, round(synth_share(n, y), 4)) for y in range(2030, 2036)])
    print('hub scan', [(r['start'][0], r['hubs'], round(r['cost_bn'], 3)) for r in hub_scan if r['hubs'] % 6 == 0 or r['hubs'] < 9], 'best', hubs_best, start_best, '| optimised', [(r['start'][0], r['hubs'], round(r['cost_bn'], 3)) for r in hub_scan_opt if r['hubs'] % 6 == 0], 'best', hubs_best_opt, start_best_opt)
    print('opt transition kelp', [(t['year'], round(t['hubs'], 1), round(t['kelp_utilisation'], 2)) for t in tr_opt])
    for lab, r in (('POLICY', pol), ('FULL', full), ('POOLED', pooled), ('POOLED_FULL', pooled_full), ('KELPJET', kelp_jet), ('OPT', pol_opt), ('FULLOPT', full_opt)):
        d = r['design']
        print('%-11s L=%5d B=%4d Br=%4d gen=%.3f (lh %.3f r %.3f) truckGL %.2f saving %.2f ERSval %.2f marg %.2f liquid %s' % (
            lab, d['L'], d['B'], d['B_r'], d['gen_share'], d['gen_share_lh'], d['gen_share_r'], d['litres'] / 1e9, r['hgv_saving_bn'], r['ers_value_bn'], r['marginal_eur_l'],
            '' if 'liquid_cost_bn' not in r else 'cost %.1f GL %.2f use %s supply %s hubs %.1f SAF %.2f synth %.2f mar %.0f EUR/t road %.2f' % (
                r['liquid_cost_bn'], r['liquid_total_GL'], {k: round(v, 2) for k, v in r['use_GL'].items()}, {k: round(v, 2) for k, v in r['supply_GL'].items() if v > 0.001},
                r['kelp_hubs'], r['marginal_saf'], r['marginal_synth'], r['marginal_marine_eur_t'] or 0, r['marginal_road'])))
    print('pool', pool)
    print('kelp', kb, kall, 'efuel', eb, eall_dac)
    for t in tr[::2] + [tr[-1]]:
        print(t['year'], 'km %5.0f hyb %.2f ldv %.2f jet %.2f mar %.2f road %.2f exp %.2f hubs %.0f CO2 %.1f (-%.0f%%) cum %.0f hgvX %.2f liqX %.2f roadmarg %.2f' % (
            t['ers_km'], t['hybrid_fleet'], t['ldv_bev_fleet'], t['jet_GL'], t['marine_GL'], t['road_GL'], t['export_GL'], t['hubs'], t['co2_total'],
            100 * t['co2_reduction_vs_2024'], t['cum_co2_avoided_Mt'], t['hgv_extra_cost_bn'], t['liquid_premium_bn'], t['marginal_road']))
    print('MC', mcs)
    print('joint', [(j['capex_mult'], j['capture_mult'], j['L'], round(j['hgv_saving_bn'], 2)) for j in joint])


if __name__ == '__main__':
    main()
