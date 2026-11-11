"""France V8: cascaded heat utilisation from small modular reactors for desalination, aquaculture and food
production — techno-economic screening for six French coastal sites.

Run:  python -I model/france_v12.py        (deterministic; no network)

Changes from V7 (response to referee report of 11 Nov 2026)
  F1  Consolidated accounts. No heat credit. Every scenario is valued on one system boundary:
      net cash = electricity export x price + external sales - external cash costs - annualised capital.
      Internal transfers (heat, distilled water) are shown but net to zero. The cascade is compared with
      (a) an energy-only hub and (b) a conventional heat-pump-only hub with the same farms.
  F2  Hubs needed for ERS hybrid fuel use the V8 fuel output of each hub (no hard-coded V6 litres).
  F3  Every Monte Carlo input is active (tested); the V6 hp_COP that V7 sampled but did not use is gone.
  F4  Alginate break-even found by root-finding on the full ledger (processing, drying energy, water,
      replacement fuel, fuel-chain electricity); packaging-only and food+packaging reported separately.
  F5  Six site-specific marine systems (Channel, Atlantic and Biscay kelps; Mediterranean Ulva without
      alginate), with species-specific yield, harvest season, alginate and fuel yield, fish and SST.
  F6  Thermal feasibility: MED effects, GOR, steam extraction, turbine work, heat-pump COPs and
      approach temperatures derived from stated temperatures; distribution losses and pumping; HP capex.
  F7  ERS: hybrids burn renewable drop-in fuel at its own cost; long-run diesel scenarios (incl. ETS2)
      replace spot prices; catenary (costed) distinguished from inductive pilots; BEV + megawatt charging
      comparison. ERS is reported in the Supplementary Information.
Scope: screening model in constant 2026 EUR; monthly resolution; not a plant design or bankable plan.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict, replace
from pathlib import Path
import csv, json, math, sys
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'; DATA.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'model'))
from france_model import P as P6, simulate as simulate_v6  # noqa: E402

K = 273.15
DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)
FLAT = DAYS / DAYS.sum()          # constant-rate loads: monthly share proportional to calendar days
GH_PROFILE = np.array([10, 9, 8, 6, 3, 1, .5, .5, 2, 6, 7, 7]) / 60.0
IRRIG_PROFILE = np.array([4, 5, 7, 9, 11, 12, 13, 12, 10, 7, 5, 5]) / 100.0   # greenhouse irrigation, summer peak
HATCH_PROFILE = np.array([.16, .15, .13, .09, .05, .02, .01, .01, .03, .08, .12, .15]); HATCH_PROFILE /= HATCH_PROFILE.sum()
SMOKE_PROFILE = np.array([.06, .05, .05, .06, .06, .06, .06, .06, .08, .12, .18, .16]); SMOKE_PROFILE /= SMOKE_PROFILE.sum()


def norm(a): a = np.asarray(a, float); return a / a.sum()


# ------------------------------------------------------------------------------------------------ sites
@dataclass
class Site:
    key: str; name: str; system: str; seaweed: str
    yield_tDM_ha: float; harvest: tuple; alginate_yield: float; fuel_yield_t_t: float
    fish: str; salmonid: bool; fish_fcr: float; fish_feed_N: float; fish_margin_eur_kg: float
    kelp_capture: float; honey_kg_hive: float; climate_factor: float; sst: tuple; lon: float; lat: float


SITES = [
    Site('DKQ', 'Dunkerque', 'channel_kelp', 'Saccharina latissima (one winter–spring crop)', 5.0, (0, 0, 0, .35, .45, .20, 0, 0, 0, 0, 0, 0), .17, .25,
         'European sea bass', False, 1.8, .075, .70, .30, 15, 1.25, (8, 7, 8, 10, 13, 16, 18, 18.5, 17, 14.5, 11.5, 9.5), 2.38, 51.03),
    Site('LEH', 'Le Havre', 'channel_kelp', 'Saccharina latissima (one winter–spring crop)', 5.5, (0, 0, 0, .35, .45, .20, 0, 0, 0, 0, 0, 0), .17, .25,
         'Atlantic salmon', True, 1.15, .065, .60, .30, 15, 1.15, (9, 8.5, 9, 10.5, 13, 15.5, 17.5, 18.5, 17.5, 15, 12.5, 10.5), 0.12, 49.48),
    Site('BRE', 'Brest', 'atlantic_kelp', 'Laminaria digitata / Saccharina latissima', 8.0, (0, 0, 0, .20, .35, .30, .15, 0, 0, 0, 0, 0), .22, .25,
         'Atlantic salmon', True, 1.15, .065, .60, .35, 18, 1.00, (11, 10.5, 10.5, 11.5, 13, 15, 16.5, 17, 16.5, 15, 13.5, 12), -4.47, 48.39),
    Site('STN', 'Saint-Nazaire', 'atlantic_kelp', 'Saccharina latissima / Laminaria spp.', 7.0, (0, 0, 0, .20, .35, .30, .15, 0, 0, 0, 0, 0), .20, .25,
         'European sea bass', False, 1.8, .075, .70, .35, 20, .95, (10.5, 10, 10.5, 12.5, 15, 18, 19.5, 20, 19, 16.5, 13.5, 11.5), -2.20, 47.27),
    Site('LRO', 'La Rochelle', 'biscay_kelp', 'Saccharina latissima (warm-edge, turbid)', 4.5, (0, 0, .15, .35, .35, .15, 0, 0, 0, 0, 0, 0), .18, .25,
         'Meagre / sea bass', False, 1.7, .075, .70, .30, 22, .85, (10, 9.5, 10.5, 13, 16, 19.5, 21, 21.5, 20, 17, 13.5, 11), -1.15, 46.16),
    Site('FOS', 'Fos-sur-Mer', 'med_ulva', 'Ulva spp. (green; ulvan, no alginate)', 6.0, (.04, .04, .06, .09, .12, .13, .13, .12, .10, .08, .05, .04), 0.0, .18,
         'Gilthead sea bream', False, 1.7, .072, .50, .50, 25, .60, (13, 12.5, 13, 14.5, 17.5, 21, 23.5, 24, 22, 19, 16, 14), 4.94, 43.43),
]


# ------------------------------------------------------------------------------------------------ inputs
@dataclass
class Thermo:
    eta_II_hp: float = 0.50          # heat-pump second-law efficiency
    approach_K: float = 3.0          # minimum heat-exchanger approach
    cop_cap: float = 8.0
    T_ext_steam_C: float = 70.0      # LP extraction saturation temperature (0.31 bar)
    TBT_C: float = 65.0              # MED top brine temperature (scaling limit)
    T_last_C: float = 40.0           # MED last-effect vapour
    dT_effect_K: float = 2.5         # per-effect driving difference incl. boiling-point elevation
    gor_per_effect: float = 0.83
    latent_kJ_kg: float = 2333.0
    eta_turbine: float = 0.85        # LP-turbine efficiency relative to reversible work
    T_cond_main_C: float = 35.0
    end_condenser_fraction: float = 0.85   # MED motive heat leaving via last-effect condenser
    loop_supply_C: float = 36.0; loop_return_C: float = 25.0
    distribution_loss: float = 0.05
    pumping_frac: float = 0.01       # electricity per unit low-T heat distributed
    cond_loop_rise_K: float = 8.0    # main-condenser outlet above sea temperature
    hp_capex_eur_kW: float = 700.0
    hx_loop_capex_eur_kW: float = 200.0
    hp_om_frac: float = 0.02
    peak_factor: float = 1.6
    hp_redundant: bool = False       # True: size heat pumps to every load's full peak (full backup for the loop)
    # firm heat supply during reactor and MED outages
    firm_heat: bool = True           # True: electric boilers cover any load the installed heat pumps cannot carry during an outage
    planned_outage_days: float = 25.0  # refuelling outage, placed in the month of lowest low-temperature demand
    med_forced_outage_frac: float = 0.03  # MED unavailable while the reactor runs
    boiler_capex_eur_kW: float = 100.0
    boiler_eff: float = 0.99
    grid_buy_eur_MWh: float = 130.0  # electricity bought from the grid while the reactor is off
    grid_connection_eur_kW: float = 0.0  # sensitivity: grid connection, transformers and distribution for outage imports
    crf: float = 0.0872
    # sink temperatures (supply, deg C)
    T_gh_base_C: float = 35.0; T_gh_peak_C: float = 50.0; T_dry_C: float = 70.0
    T_prawn_C: float = 31.0; T_hatch_C: float = 18.0


@dataclass
class Water:
    med_water_m3_y: float = 2.0e6
    med_elec_kWh_m3: float = 1.5
    med_capex_eur_per_m3d: float = 2200.0
    med_marine_works_eur: float = 4.0e6
    med_fixed_om_frac: float = 0.04
    brine_eur_m3: float = 0.15
    mains_eur_m3: float = 1.50       # price paid for water when there is no MED (baseline) = transfer price
    demin_cap_m3: float = 300000.0
    price_demin_eur_m3: float = 2.50
    price_bulk_eur_m3: float = 0.85
    gh_water_m3_m2: float = 0.65
    prawn_water_m3_kg: float = 0.40
    hatchery_water_m3: float = 50000.0
    electrolyser_water_m3_t_H2: float = 15.0
    alginate_water_m3_t: float = 80.0
    # seawater reverse osmosis comparator (same output, same sales)
    swro_kWh_m3: float = 3.5             # incl. intake, pretreatment, energy recovery, post-treatment pumping
    swro_capex_eur_per_m3d: float = 1800.0
    swro_marine_works_eur: float = 4.0e6
    swro_fixed_om_frac: float = 0.03
    swro_forced_outage_frac: float = 0.03  # SWRO runs on grid power through reactor outages; own downtime as MED
    swro_consumables_eur_m3: float = 0.10  # membranes, chemicals, cartridge filters
    swro_post_eur_m3: float = 0.03         # remineralisation
    # final polishing to < 1 uS/cm for demineralised sales and electrolyser feed, applied to both technologies
    edi_kWh_m3: float = 0.3                # electrodeionisation / mixed-bed polishing (MED distillate and SWRO permeate)
    edi_eur_m3: float = 0.08
    ro2_kWh_m3: float = 0.5                # second RO pass, needed for SWRO permeate only
    ro2_eur_m3: float = 0.07
    med_full_polish: bool = False          # sensitivity: charge MED the SWRO polishing train as well


@dataclass
class Food:
    gh_price_eur_kg: float = 3.10
    prawn_t_y: float = 1000.0
    prawn_heat_kWh_kg: float = 10.0
    prawn_elec_kWh_kg: float = 8.0
    prawn_price_eur_kg: float = 14.0
    prawn_cost_ex_energy_eur_kg: float = 10.2
    prawn_fcr: float = 1.4
    hatchery_heat_GWh: float = 2.0
    gh_direct_share: float = 0.55
    fish_t_y: float = 2000.0
    fish_margin_shift: float = 0.0                 # Monte Carlo shift on all site margins
    fish_retained_N_frac: float = 0.30
    fish_dissolved_share_of_loss: float = 0.65
    kelp_capture_mult: float = 1.0
    imta_shared_om_eur_kg_fish: float = 0.15
    imta_kelp_saving_eur_tDM: float = 20.0
    imta_colocated_frac_of_harvest: float = 0.10
    hives: float = 600.0
    hives_per_ha_max: float = 3.0
    forage_ha: float = 300.0
    honey_mult: float = 1.0
    honey_price_eur_kg: float = 8.0
    hive_cost_eur_y: float = 120.0
    smoked_target_t: float = 450.0
    smoked_yield: float = 0.50
    honey_frac_smoked: float = 0.03
    honey_smoked_premium_eur_kg: float = 2.50
    smoke_heat_MWh_t: float = 5.5
    prawn_residue_frac: float = 0.40
    salmon_residue_frac: float = 0.50
    residue_dry_frac: float = 0.25
    meal_recovery: float = 0.80
    meal_saving_eur_t: float = 125.0
    # capital (all-in installed cost, annualised with the common CRF); operating costs above exclude capital
    prawn_capex_eur_per_kg_y: float = 12.0
    fish_capex_eur_per_kg_y: float = 5.0
    hive_capex_eur: float = 250.0
    smokehouse_capex_eur: float = 3.0e6      # for the 450 t/yr target, scaled to actual output
    drying_GWh_per_80kt: float = 22.0             # V6 kelp + fertiliser drying, scaled to biomass


@dataclass
class Alginate:
    yield_mult: float = 1.0
    food_price_eur_kg: float = 11.0
    pack_price_eur_kg: float = 4.5
    process_cost_eur_kg: float = 2.4      # operating cost only
    capex_eur_per_t_y: float = 7500.0
    heat_MWh_t: float = 4.0
    elec_MWh_t: float = 0.6
    global_market_eur: float = 0.85e9
    food_share_national: float = 0.02
    french_plastic_pack_t: float = 2.2e6
    pack_share_replaced: float = 0.005
    alg_per_kg_plastic: float = 0.875
    max_divert_frac_of_HTL: float = 0.30
    replacement_fuel_eur_l: float = 2.00
    plastic_avoided_kgCO2_kg: float = 3.5
    process_kgCO2_kg: float = 1.0
    diesel_kgCO2_l: float = 2.66


@dataclass
class ERS:
    network_km_phase1: float = 4900.0
    network_km_full: float = 8850.0
    capture_max: float = 0.55
    capture_scale_km: float = 3700.0
    hgv_vkm_bn: float = 31.0
    diesel_l_per_km: float = 0.32
    elec_kWh_km: float = 1.30
    grid_loss: float = 0.08
    on_wire_share: float = 0.75
    hybrid_share: float = 0.30
    hybrid_l_per_km_off_wire: float = 0.29
    capex_eur_km: float = 3.4e6
    infra_crf: float = 0.0578
    infra_om_frac: float = 0.015
    elec_eur_MWh: float = 105.0
    diesel_longrun_eur_l: float = 1.45       # 2030-2041 central, net of VAT and TICPE refund, incl. ETS2
    diesel_low_eur_l: float = 1.20
    diesel_high_eur_l: float = 1.80
    diesel_spot_nov2026_eur_l: float = 1.70
    diesel_spot_feb2026_eur_l: float = 1.23
    truck_premium_eur: float = 45000.0
    truck_km_y: float = 100000.0
    truck_crf: float = 0.179
    maint_saving_eur_km: float = 0.03
    grid_kgCO2_kWh: float = 0.018
    hgv_MtCO2_2023: float = 27.9
    # battery-electric + megawatt-charging alternative
    bev_kWh_km: float = 1.25
    bev_depot_share: float = 0.70
    bev_depot_eur_kWh: float = 0.14
    bev_mcs_eur_kWh: float = 0.40
    bev_premium_eur: float = 80000.0


@dataclass
class Inputs:
    p6: P6 = field(default_factory=P6)
    th: Thermo = field(default_factory=Thermo)
    w: Water = field(default_factory=Water)
    f: Food = field(default_factory=Food)
    a: Alginate = field(default_factory=Alginate)
    e: ERS = field(default_factory=ERS)
    yield_mult: float = 1.0


# ------------------------------------------------------------------------------------------------ thermal engineering
def cop(th: Thermo, T_sink_C, T_src_C):
    Ts = T_sink_C + th.approach_K + K; Tc = T_src_C - th.approach_K + K
    if Ts - Tc <= 1.0:          # source warm enough for direct exchange: only circulation/booster electricity
        return th.cop_cap
    return min(th.cop_cap, th.eta_II_hp * Ts / (Ts - Tc))


def med_design(th: Thermo):
    n_eff = int((th.TBT_C - th.T_last_C) // th.dT_effect_K)
    gor = th.gor_per_effect * n_eff
    ste = th.latent_kJ_kg / 3.6 / gor                       # kWh_th per m3
    alpha = th.eta_turbine * (1 - (th.T_cond_main_C + K) / (th.T_ext_steam_C + K))
    p_ext_bar = 0.001 * 0.61094 * math.exp(17.625 * th.T_ext_steam_C / (th.T_ext_steam_C + 243.04)) * 1000 / 100  # Magnus (approx.)
    feasible = dict(steam_to_TBT_K=th.T_ext_steam_C - th.TBT_C, last_effect_to_loop_K=th.T_last_C - th.loop_supply_C,
                    loop_to_prawn_K=th.loop_supply_C - 1 - th.T_prawn_C, loop_to_gh_base_K=th.loop_supply_C - 1 - th.T_gh_base_C)
    ok = all(v >= th.approach_K - 1e-9 for k, v in feasible.items() if k != 'loop_to_gh_base_K') and feasible['loop_to_gh_base_K'] >= 0
    return dict(effects=n_eff, gor=gor, ste_kWh_m3=ste, alpha=alpha, p_ext_bar=p_ext_bar, approaches_K=feasible, feasible=ok)


# ------------------------------------------------------------------------------------------------ energy core
def energy_core(p6: P6, alg_dry: float, divert_heat=True):
    E_th = p6.thermal_MW * 8760 * p6.capacity_factor
    dry = p6.area_ha * p6.seaweed_tDM_ha_y
    HTL0 = dry * p6.frac_HTL
    assert 0 <= alg_dry < HTL0
    HTL = HTL0 - alg_dry
    ferment = dry - HTL0
    liquid_t = HTL * p6.biocrude_fuel_yield_t_t
    litres = liquid_t / p6.fuel_density_t_m3 * 1000
    eth_t = ferment * p6.ferment_carbohydrate_frac * p6.ethanol_t_per_t_carbs
    H_HTL = HTL * p6.HTL_heat_MWh_t
    H_hot = H_HTL + eth_t * p6.distil_heat_MWh_t_ethanol
    trim = H_HTL * p6.HTL_high_grade_electric_trim_frac
    H_direct = min(E_th * p6.divert_frac, H_hot - trim)
    gap = trim + (H_hot - trim) - H_direct
    H2_t = liquid_t * p6.hydrogen_t_per_t_liquid
    E_fuel = HTL * p6.HTL_elec_MWh_t + eth_t * p6.ethanol_electric_MWh_t + H2_t * p6.H2_elec_MWh_t + 5000.0
    unit_heat = p6.nuclear_electric_eur_MWh * p6.nuclear_heat_opp_ratio
    cost = (HTL * (p6.seaweed_dry_cost_eur_t + p6.harvest_marine_eur_t)
            + (HTL * p6.HTL_elec_MWh_t + H2_t * p6.H2_elec_MWh_t) * p6.nuclear_electric_eur_MWh
            + H_direct * unit_heat + gap * p6.nuclear_electric_eur_MWh + litres * p6.HTL_other_eur_L)
    return dict(E_th=E_th, dry=dry, HTL_dry=HTL, litres=litres, H_direct=H_direct, trim=gap, H2_t=H2_t,
                E_fuel_loads=E_fuel, fuel_cost_eur_l=cost / litres)


# ------------------------------------------------------------------------------------------------ one hub, one scenario
def hub(site: Site, inp: Inputs, scenario: str = 'cascade', alg_food_t: float = 0.0, alg_pack_t: float = 0.0):
    """scenario: 'cascade' (MED + farms), 'hp_only' (farms, heat pumps on main-condenser loop, mains water),
    'energy_only' (no farms, no MED, no alginate; kelp drying by heat pumps)."""
    p6 = replace(inp.p6, seaweed_tDM_ha_y=site.yield_tDM_ha * inp.yield_mult, biocrude_fuel_yield_t_t=site.fuel_yield_t_t)
    th, w, f, a = inp.th, inp.w, inp.f, inp.a
    farms = scenario in ('cascade', 'hp_only', 'hp_swro'); med_on = scenario == 'cascade'; swro_on = scenario == 'hp_swro'
    plant_on = med_on or swro_on
    if not farms: alg_food_t = alg_pack_t = 0.0
    alg_t = alg_food_t + alg_pack_t
    ay = site.alginate_yield * a.yield_mult
    if alg_t > 0: assert ay > 0, f'{site.name}: no alginate from {site.seaweed}'
    alg_dry = alg_t / ay if alg_t else 0.0
    core = energy_core(p6, alg_dry)
    E_th, H_direct = core['E_th'], core['H_direct']
    F = E_th - H_direct; eta = p6.electrical_efficiency
    md = med_design(th)
    Q_med = (w.med_water_m3_y * md['ste_kWh_m3'] / 1000) if med_on else 0.0
    alpha = md['alpha']
    assert Q_med * (1 - alpha) <= F * (1 - eta)
    E_gen = F * eta - alpha * Q_med
    R_main = F * (1 - eta) - Q_med * (1 - alpha)
    # ---- monthly low-temperature loads (MWh delivered at the user)
    H_gh = p6.greenhouse_ha * 1e4 * p6.greenhouse_heat_kWh_m2_y / 1000 * site.climate_factor
    honey, smoked = honey_salmon(site, f)
    dry_GWh = f.drying_GWh_per_80kt * core['dry'] / 80000.0
    hv = norm(site.harvest)
    loads = {}
    if farms:
        loads.update({
            'prawn_RAS': (f.prawn_t_y * f.prawn_heat_kWh_kg * math.sqrt(site.climate_factor), FLAT, th.T_prawn_C, True),
            'hatchery': (f.hatchery_heat_GWh * 1000, HATCH_PROFILE, th.T_hatch_C, True),
            'greenhouse_base': (H_gh * f.gh_direct_share, GH_PROFILE, th.T_gh_base_C, True),
            'greenhouse_peak': (H_gh * (1 - f.gh_direct_share), GH_PROFILE, th.T_gh_peak_C, False),
            'alginate_drying': (alg_t * a.heat_MWh_t, FLAT, th.T_dry_C, False),
            'smokehouse': (smoked['smoked_t'] * f.smoke_heat_MWh_t, SMOKE_PROFILE, th.T_dry_C, False)})
    loads['kelp_drying'] = (dry_GWh * 1000, hv, th.T_dry_C, False)
    # ---- reactor availability by month: a planned refuelling outage in the month of lowest low-temperature demand, forced outages spread evenly
    dem_m = np.array([sum(v[0] * v[1][m] for v in loads.values()) for m in range(12)])
    m_out = int(np.argmin(dem_m))
    forced_frac = max(0.0, (365 * (1 - p6.capacity_factor) - th.planned_outage_days) / 365)
    out_m = np.full(12, forced_frac); out_m[m_out] += th.planned_outage_days / DAYS[m_out]
    on_m = 1 - out_m
    # ---- dispatch while the reactor runs (MED heat arrives only when the reactor and the MED run)
    Q_del = Q_med * th.end_condenser_fraction * (1 - th.distribution_loss)
    avail = Q_del * (on_m * DAYS) / float(np.dot(on_m, DAYS))   # constant output per operating day; annual output reflects MED availability
    fmed = th.med_forced_outage_frac if med_on else 0.0
    loop_src = (th.loop_supply_C + th.loop_return_C) / 2
    per = {k: dict(med_direct=0., med_hp=0., cond_hp=0., hp_elec=0., cond_elec=0., peak_MW=0., hp_peak_MW=0., hx_peak_MW=0.,
                   out_heat=[0.] * 12, trip_heat=[0.] * 12) for k in loads}
    rows = []; unused = 0.; delivered_med = 0.
    for m in range(12):
        s = avail[m]; r = dict(month=m + 1, reactor_on_frac=on_m[m]); on = on_m[m]
        cond_src = site.sst[m] + th.cond_loop_rise_K
        for k, (tot, prof, Tsink, direct_ok) in loads.items():
            need_full = tot * prof[m]; r[k + '_MWh'] = need_full
            per[k]['peak_MW'] = max(per[k]['peak_MW'], need_full / (24 * DAYS[m]) * th.peak_factor)
            per[k]['out_heat'][m] = need_full * (1 - on)
            need = need_full * on * (1 - fmed)
            per[k]['trip_heat'][m] = need_full * on * fmed   # load falling in MED-trip hours
            if med_on and direct_ok:
                g = min(need, s); s -= g; per[k]['med_direct'] += g
            elif med_on:
                c1 = cop(th, Tsink, loop_src); dpu = 1 - 1 / c1
                g = min(need, s / dpu); s -= g * dpu; per[k]['med_hp'] += g; per[k]['hp_elec'] += g / c1
            else:
                g = 0.0
            rem = need - g
            hp_m = rem + (g if (med_on and not direct_ok) else 0.0)
            per[k]['hp_peak_MW'] = max(per[k]['hp_peak_MW'], hp_m / max(on * (1 - fmed), 1e-9) / (24 * DAYS[m]) * th.peak_factor)
            per[k]['hx_peak_MW'] = max(per[k]['hx_peak_MW'], g / max(on * (1 - fmed), 1e-9) / (24 * DAYS[m]) * th.peak_factor)
            if rem > 0:
                c2 = cop(th, Tsink, cond_src)
                per[k]['cond_hp'] += rem; per[k]['hp_elec'] += rem / c2; per[k]['cond_elec'] += rem / c2
        r['med_available_MWh'] = avail[m]; r['med_unused_MWh'] = s; unused += s; delivered_med += avail[m] - s
        rows.append(r)
    lowT_demand = sum(v[0] for v in loads.values())
    from_med = sum(v['med_direct'] + v['med_hp'] for v in per.values())
    from_cond = sum(v['cond_hp'] for v in per.values())
    hp_elec = sum(v['hp_elec'] for v in per.values())
    pump_elec = (from_med / (1 - th.distribution_loss)) * th.pumping_frac if med_on else 0.0
    # heat equipment capex (annualised): HP capacity where a heat pump runs; loop HX for MED-served loads
    # heat pumps sized to the largest monthly load they actually serve; loop exchangers to the largest MED-served load
    hp_kW = sum((v['peak_MW'] if th.hp_redundant else v['hp_peak_MW']) for v in per.values()) * 1000
    hx_kW = sum(v['hx_peak_MW'] for v in per.values()) * 1000 if med_on else 0.0
    # ---- firm heat during outages. Reactor off: installed heat pumps draw sea water directly (no condenser heat) and run on
    # grid electricity; electric boilers cover the share of each load beyond installed heat-pump capacity. MED trip: the
    # condenser-loop heat pumps take over up to their capacity, boilers cover the rest, on reactor electricity.
    # Non-firm diagnostic (firm_heat=False): installed heat pumps deliver only up to their capacity; the rest is unmet and not valued.
    boiler_kW = 0.0; grid_MWh = 0.0; trip_elec = 0.0; out_heat_tot = 0.0; boiler_heat = 0.0; unmet_heat = 0.0; import_kW = 0.0
    for k, (tot, prof, Tsink, direct_ok) in loads.items():
        v = per[k]; pk = v['peak_MW']
        cap = pk if th.hp_redundant else v['hp_peak_MW']
        sh = 1.0 if pk <= 0 else min(1.0, cap / pk)
        bshare = (1 - sh) if th.firm_heat else 0.0
        if th.firm_heat: boiler_kW += max(0.0, pk - cap) * 1000
        import_kW += cap * 1000 / cop(th, Tsink, min(site.sst)) + max(0.0, pk - cap) * 1000 / th.boiler_eff * th.firm_heat
        for m in range(12):
            q = v['out_heat'][m]; out_heat_tot += q
            grid_MWh += q * sh / cop(th, Tsink, site.sst[m]) + q * bshare / th.boiler_eff
            qt = v['trip_heat'][m]
            trip_elec += qt * sh / cop(th, Tsink, site.sst[m] + th.cond_loop_rise_K) + qt * bshare / th.boiler_eff
            boiler_heat += (q + qt) * bshare
            if not th.firm_heat: unmet_heat += (q + qt) * (1 - sh)
    hp_elec += trip_elec
    heat_capex = hp_kW * th.hp_capex_eur_kW + hx_kW * th.hx_loop_capex_eur_kW + boiler_kW * th.boiler_capex_eur_kW
    heat_annual = heat_capex * (th.crf + th.hp_om_frac)
    grid_cost = grid_MWh * th.grid_buy_eur_MWh
    # ---- electricity
    E_prawn = f.prawn_t_y * f.prawn_elec_kWh_kg if farms else 0.0
    E_med = w.med_water_m3_y * w.med_elec_kWh_m3 / 1000 if med_on else 0.0
    E_alg = alg_t * a.elec_MWh_t
    E_led = p6.greenhouse_ha * 1e4 * p6.greenhouse_light_kWh_m2_y / 1000 if farms else 0.0
    W = w.med_water_m3_y
    off_frac = 1 - on_m.mean()                         # share of the year with the reactor off
    E_farm_nonheat = E_prawn + E_led + E_alg           # loads that continue through reactor outages
    import_kW += E_farm_nonheat / 8760 * 1000
    E_req = core['E_fuel_loads'] + core['trim'] + hp_elec + pump_elec + E_prawn + E_med + E_alg + E_led
    E_net = E_gen - E_req
    pe = p6.nuclear_electric_eur_MWh
    # ---- water (m3)
    uses = {'electrolyser_feed': core['H2_t'] * w.electrolyser_water_m3_t_H2}
    if farms:
        uses.update({'greenhouse_irrigation': p6.greenhouse_ha * 1e4 * w.gh_water_m3_m2, 'prawn_RAS_makeup': f.prawn_t_y * 1000 * w.prawn_water_m3_kg,
                     'hatchery_and_processing': w.hatchery_water_m3, 'alginate_extraction': alg_t * w.alginate_water_m3_t})
    internal_need = sum(uses.values())
    # monthly water balance: MED produces only while the reactor and the MED run; SWRO runs on grid power through reactor
    # outages but has its own downtime. Internal demand falling in plant-off time is bought from the mains (no storage).
    use_prof = {k: (IRRIG_PROFILE if k == 'greenhouse_irrigation' else ((on_m * DAYS) / float(np.dot(on_m, DAYS)) if k == 'electrolyser_feed' else FLAT)) for k in uses}
    if med_on: off_m = (1 - on_m) + on_m * th.med_forced_outage_frac
    elif swro_on: off_m = np.full(12, w.swro_forced_outage_frac)
    else: off_m = np.ones(12)
    outage_mains = sum(uses[k] * float(np.dot(use_prof[k], off_m)) for k in uses)
    # explicit twelve-month balance without storage: plant output in each month is proportional to its operating days
    run_days = (1 - off_m) * DAYS
    prod_m = W * run_days / float(run_days.sum()) if plant_on else np.zeros(12)
    dem_on_m = np.array([sum(uses[k] * use_prof[k][m] * (1 - off_m[m]) for k in uses) for m in range(12)])
    supplied_m = np.minimum(dem_on_m, prod_m) if plant_on else np.zeros(12)
    monthly_shortfall = float((dem_on_m - supplied_m).sum()) if plant_on else 0.0
    supplied = float(supplied_m.sum())
    mains = internal_need - supplied
    water_outage_month_m3 = sum(uses[k] * use_prof[k][m_out] for k in uses) * (th.planned_outage_days / DAYS[m_out]) if med_on else 0.0
    demin = min(w.demin_cap_m3, W - supplied) if plant_on else 0.0
    bulk = (W - supplied - demin) if plant_on else 0.0
    polish_m3 = (demin + uses['electrolyser_feed']) if plant_on else 0.0
    ro2 = swro_on or (med_on and w.med_full_polish)
    pol_kWh = w.edi_kWh_m3 + (w.ro2_kWh_m3 if ro2 else 0.0); pol_eur = w.edi_eur_m3 + (w.ro2_eur_m3 if ro2 else 0.0)
    E_polish = polish_m3 * pol_kWh / 1000; polish_cash = polish_m3 * pol_eur
    E_swro = W * w.swro_kWh_m3 / 1000 if swro_on else 0.0
    E_req += E_swro + E_polish; E_net = E_gen - E_req
    swro_capex = (w.swro_capex_eur_per_m3d * W / (365 * (1 - w.swro_forced_outage_frac)) + w.swro_marine_works_eur) if swro_on else 0.0
    swro_cash = (swro_capex * w.swro_fixed_om_frac + W * (w.swro_consumables_eur_m3 + w.swro_post_eur_m3 + w.brine_eur_m3)
                 + (th.grid_buy_eur_MWh - pe) * off_frac * (E_swro + E_polish)) if swro_on else 0.0
    if swro_on: import_kW += (E_swro + E_polish) / (8760 * (1 - w.swro_forced_outage_frac)) * 1000
    grid_conn_capex = import_kW * th.grid_connection_eur_kW
    nonheat_outage_premium = (th.grid_buy_eur_MWh - pe) * off_frac * E_farm_nonheat
    water = dict(uses=uses, internal_need=internal_need, internal_from_med=supplied, bought_mains=mains, demin_sold=demin, bulk_sold=bulk, polished_m3=polish_m3,
                 outage_mains_m3=outage_mains if plant_on else 0.0, monthly_shortfall_mains_m3=monthly_shortfall, refuelling_outage_internal_m3=water_outage_month_m3)
    # MED sized for its annual output over the time both reactor and MED run
    med_capex = (w.med_capex_eur_per_m3d * w.med_water_m3_y / (365 * p6.capacity_factor * (1 - th.med_forced_outage_frac)) + w.med_marine_works_eur) if med_on else 0.0
    # ---- enterprises (external flows only + metered electricity at pe)
    def elec_of(*keys): return sum(per[k]['hp_elec'] for k in keys if k in per)
    gh_kg = p6.greenhouse_ha * 1e4 * p6.produce_kg_m2_y if farms else 0.0
    imta = imta_balance(site, f, core['dry']) if farms else None
    meal = residue_meal(site, f, smoked) if farms else None
    alg = alginate_block(site, inp, alg_food_t, alg_pack_t, alg_dry, p6) if alg_t else None
    ext = {}   # name -> dict(sales, cash_costs, capital, elec_MWh, transfers_in (water m3 at mains price))
    if farms:
        ext['greenhouse'] = dict(sales=gh_kg * f.gh_price_eur_kg, cash_costs=gh_kg * p6.greenhouse_other_opex_eur_kg,
                                 capital=p6.greenhouse_ha * 1e4 * p6.greenhouse_capex_eur_m2 * p6.greenhouse_capital_recovery_factor,
                                 elec_MWh=E_led + elec_of('greenhouse_base', 'greenhouse_peak'), water_m3=uses['greenhouse_irrigation'])
        ext['prawn'] = dict(sales=f.prawn_t_y * 1000 * f.prawn_price_eur_kg, cash_costs=f.prawn_t_y * 1000 * f.prawn_cost_ex_energy_eur_kg,
                            capital=f.prawn_t_y * 1000 * f.prawn_capex_eur_per_kg_y * th.crf, elec_MWh=E_prawn + elec_of('prawn_RAS', 'hatchery'), water_m3=uses['prawn_RAS_makeup'] + uses['hatchery_and_processing'])
        fm = site.fish_margin_eur_kg + f.fish_margin_shift
        ext['finfish_imta'] = dict(sales=f.fish_t_y * 1000 * (fm + f.imta_shared_om_eur_kg_fish) + imta['colocated_kelp_tDM'] * f.imta_kelp_saving_eur_tDM,
                                   cash_costs=0.0, capital=f.fish_t_y * 1000 * f.fish_capex_eur_per_kg_y * th.crf, elec_MWh=0.0, water_m3=0.0)
        ext['honey'] = dict(sales=honey['honey_sold_t'] * 1000 * f.honey_price_eur_kg, cash_costs=honey['hives'] * f.hive_cost_eur_y,
                            capital=honey['hives'] * f.hive_capex_eur * th.crf, elec_MWh=0.0, water_m3=0.0)
        ext['honey_smoked_salmon'] = dict(sales=smoked['smoked_t'] * 1000 * f.honey_smoked_premium_eur_kg, cash_costs=0.0,
                                          capital=f.smokehouse_capex_eur * smoked['smoked_t'] / f.smoked_target_t * th.crf,
                                          elec_MWh=elec_of('smokehouse'), water_m3=0.0)
        ext['residue_meal'] = dict(sales=meal['meal_t'] * f.meal_saving_eur_t, cash_costs=0.0, capital=0.0, elec_MWh=0.0, water_m3=0.0)
    if alg:
        dE_core = (energy_core(p6, alg_dry)['E_fuel_loads'] + energy_core(p6, alg_dry)['trim']) - (energy_core(p6, 0)['E_fuel_loads'] + energy_core(p6, 0)['trim'])
        dE_gen = (energy_core(p6, 0)['H_direct'] - core['H_direct']) * eta    # steam freed from HTL goes to the turbine
        ext['alginate'] = dict(sales=alg['revenue_eur'], cash_costs=alg['process_cost_eur'] + alg['fuel_replacement_cost_eur'], capital=alg_t * a.capex_eur_per_t_y * th.crf,
                               elec_MWh=E_alg + elec_of('alginate_drying') + dE_core - dE_gen, water_m3=uses['alginate_extraction'])
    ext['fuel_chain_utilities'] = dict(sales=0.0, cash_costs=0.0, capital=0.0, elec_MWh=elec_of('kelp_drying'), water_m3=uses['electrolyser_feed'])
    ext['heat_and_water_infrastructure'] = dict(
        sales=demin * w.price_demin_eur_m3 + bulk * w.price_bulk_eur_m3,
        cash_costs=(med_capex * w.med_fixed_om_frac + w.med_water_m3_y * w.brine_eur_m3 if med_on else 0.0) + mains * w.mains_eur_m3 + swro_cash
                   + polish_cash + grid_cost,
        capital=med_capex * th.crf + swro_capex * th.crf + heat_annual + grid_conn_capex * th.crf,
        elec_MWh=(alpha * Q_med + E_med + pump_elec + E_swro + E_polish + trip_elec), water_m3=0.0)
    # reconciliation line: electricity value of the reactor and fuel chain without MED and without alginate diversion,
    # identical in every scenario, so that the enterprise ledgers sum exactly to consolidated net cash
    c0 = energy_core(p6, 0.0)
    E_gen0 = (E_th - c0['H_direct']) * eta
    ext['outage_grid_purchases'] = dict(sales=0.0, cash_costs=nonheat_outage_premium, capital=0.0, elec_MWh=0.0, water_m3=0.0)
    ext['reactor_and_fuel_chain'] = dict(sales=0.0, cash_costs=0.0, capital=0.0, elec_MWh=-(E_gen0 - c0['E_fuel_loads'] - c0['trim']), water_m3=0.0)
    # internal water transfer: users pay mains price; supplier (MED or mains purchase) receives it -> nets to zero
    for k, v in ext.items():
        v['water_transfer_paid'] = v['water_m3'] * w.mains_eur_m3
        v['water_transfer_received'] = 0.0
    ext['heat_and_water_infrastructure']['water_transfer_received'] = internal_need * w.mains_eur_m3
    for k, v in ext.items():
        v.setdefault('water_transfer_paid', 0.0); v.setdefault('water_transfer_received', 0.0)
        v['net_eur'] = v['sales'] - v['cash_costs'] - v['capital'] - v['elec_MWh'] * pe - v['water_transfer_paid'] + v['water_transfer_received']
    # consolidated net cash on the system boundary (excluding the identical fuel chain and reactor)
    sales_ext = sum(v['sales'] for v in ext.values())
    costs_ext = sum(v['cash_costs'] + v['capital'] for v in ext.values())
    net_cash = E_net * pe + sales_ext - costs_ext
    # first law, single count: gross electricity + direct HTL heat + MED motive heat + heat lifted out of the main condenser
    cond_source = sum(v['cond_hp'] - v['cond_elec'] for v in per.values())
    first_law = (E_gen + H_direct + Q_med + cond_source) / E_th
    out = dict(site=site.name, key=site.key, scenario=scenario, seaweed=site.seaweed, fish=site.fish,
               thermal_GWh=E_th / 1000, gross_elec_GWh=E_gen / 1000, net_export_GWh=E_net / 1000, htl_direct_GWh=H_direct / 1000,
               htl_trim_GWh=core['trim'] / 1000, med_motive_GWh=Q_med / 1000, turbine_penalty_GWh=alpha * Q_med / 1000,
               main_condenser_GWh=R_main / 1000, lowT_demand_GWh=lowT_demand / 1000, lowT_from_med_GWh=from_med / 1000,
               lowT_from_condenser_hp_GWh=from_cond / 1000, hp_elec_GWh=hp_elec / 1000, pumping_GWh=pump_elec / 1000,
               med_unused_GWh=unused / 1000, med_available_delivered_GWh=avail.sum() / 1000, first_law=first_law,
               swro_elec_GWh=E_swro / 1000, polish_elec_GWh=E_polish / 1000, boiler_MW=boiler_kW / 1000, outage_heat_GWh=out_heat_tot / 1000,
               boiler_heat_GWh=boiler_heat / 1000, unmet_heat_GWh=unmet_heat / 1000, grid_import_MW=import_kW / 1000, nonheat_outage_premium_eur=nonheat_outage_premium, lowT_from_outage_backup_GWh=(out_heat_tot + sum(sum(v['trip_heat']) for v in per.values())) / 1000, grid_backup_GWh=grid_MWh / 1000, med_trip_elec_GWh=trip_elec / 1000, planned_outage_month=m_out + 1, swro_capex_MEUR=swro_capex / 1e6, hp_capacity_MW=hp_kW / 1000, loop_hx_MW=hx_kW / 1000, heat_capex_MEUR=heat_capex / 1e6, med_capex_MEUR=med_capex / 1e6,
               kelp_dry_t=core['dry'], kelp_to_HTL_t=core['HTL_dry'], fuel_litres=core['litres'], fuel_cost_eur_l=core['fuel_cost_eur_l'],
               hydrogen_t=core['H2_t'], water=water, enterprises=ext, net_cash_eur=net_cash, E_net_MWh=E_net,
               honey=honey, smoked=smoked, imta=imta, meal=meal, alginate=alg, med_design=md,
               per_user=per)
    return out, rows


def honey_salmon(site: Site, f: Food):
    hives = min(f.hives, f.forage_ha * f.hives_per_ha_max)
    honey_t = hives * site.honey_kg_hive * f.honey_mult / 1000
    if not site.salmonid:
        return dict(hives=hives, honey_t=honey_t, honey_used_t=0.0, honey_sold_t=honey_t, limit_scale=1.0), \
               dict(smoked_t=0.0, smoked_target_t=0.0, honey_limited=False, whole_salmon_t=0.0)
    need = f.smoked_target_t * f.honey_frac_smoked
    scale = min(1.0, honey_t / need)
    sm = f.smoked_target_t * scale
    used = sm * f.honey_frac_smoked
    return dict(hives=hives, honey_t=honey_t, honey_used_t=used, honey_sold_t=honey_t - used, limit_scale=scale), \
           dict(smoked_t=sm, smoked_target_t=f.smoked_target_t, honey_limited=scale < 1, whole_salmon_t=sm / f.smoked_yield)


def imta_balance(site: Site, f: Food, dry):
    feed_N = f.fish_t_y * site.fish_fcr * site.fish_feed_N
    lost = feed_N * (1 - f.fish_retained_N_frac)
    din = lost * f.fish_dissolved_share_of_loss
    cap = din * min(1.0, site.kelp_capture * f.kelp_capture_mult)
    return dict(feed_N_t=feed_N, released_N_t=lost, dissolved_N_t=din, captured_N_t=cap, captured_share=cap / din,
                biomass_equiv_tDM=cap / 0.025, share_of_harvest=cap / 0.025 / dry, colocated_kelp_tDM=dry * f.imta_colocated_frac_of_harvest)


def residue_meal(site: Site, f: Food, smoked):
    prawn_meal = f.prawn_t_y * f.prawn_residue_frac * f.residue_dry_frac * f.meal_recovery
    fish_meal = smoked['whole_salmon_t'] * f.salmon_residue_frac * f.residue_dry_frac * f.meal_recovery
    fish_feed = f.fish_t_y * site.fish_fcr; prawn_feed = f.prawn_t_y * f.prawn_fcr
    return dict(prawn_meal_to_fish_feed_t=prawn_meal, fish_meal_to_prawn_feed_t=fish_meal, meal_t=prawn_meal + fish_meal,
                fish_feed_share=prawn_meal / fish_feed, prawn_feed_share=min(1, fish_meal / prawn_feed))


def alginate_block(site: Site, inp: Inputs, food_t, pack_t, alg_dry, p6: P6):
    a = inp.a
    lost_l = alg_dry * p6.biocrude_fuel_yield_t_t / p6.fuel_density_t_m3 * 1000
    # consolidated: the fuel-chain electricity change is metered separately; only the non-energy HTL cost is avoided here
    repl = lost_l * (a.replacement_fuel_eur_l - p6.HTL_other_eur_L)
    rev = food_t * 1000 * a.food_price_eur_kg + pack_t * 1000 * a.pack_price_eur_kg
    proc = (food_t + pack_t) * 1000 * a.process_cost_eur_kg
    plastic_t = pack_t / a.alg_per_kg_plastic
    co2_low = plastic_t * a.plastic_avoided_kgCO2_kg - (food_t + pack_t) * a.process_kgCO2_kg
    pack_share = pack_t / (food_t + pack_t) if (food_t + pack_t) else 0
    co2_fossil = co2_low - lost_l * a.diesel_kgCO2_l / 1000 * pack_share
    return dict(food_t=food_t, packaging_t=pack_t, total_t=food_t + pack_t, kelp_diverted_tDM=alg_dry, fuel_lost_l=lost_l,
                revenue_eur=rev, process_cost_eur=proc, fuel_replacement_cost_eur=repl, plastic_replaced_t=plastic_t,
                co2_t_low_carbon_fill=co2_low, co2_t_fossil_fill=co2_fossil)


# ------------------------------------------------------------------------------------------------ national
def allocate_alginate(inp: Inputs):
    a = inp.a
    food_total = a.global_market_eur * a.food_share_national / a.food_price_eur_kg / 1000
    pack_total = a.french_plastic_pack_t * a.pack_share_replaced * a.alg_per_kg_plastic
    pot = {}
    for s in SITES:
        dry = inp.p6.area_ha * s.yield_tDM_ha * inp.yield_mult * inp.p6.frac_HTL
        pot[s.key] = dry * a.max_divert_frac_of_HTL * s.alginate_yield * a.yield_mult
    tot = sum(pot.values())
    return {k: (food_total * v / tot, pack_total * v / tot) for k, v in pot.items()}, food_total, pack_total


def national(inp: Inputs | None = None, with_rows=False):
    inp = inp or Inputs()
    alloc, food_total, pack_total = allocate_alginate(inp)
    res = {}
    for s in SITES:
        fa, pa = alloc[s.key]
        c, rows = hub(s, inp, 'cascade', fa, pa)
        h, _ = hub(s, inp, 'hp_only', fa, pa)
        ro, _ = hub(s, inp, 'hp_swro', fa, pa)
        e0, _ = hub(s, inp, 'energy_only')
        cp, _ = hub(s, inp, 'cascade', 0.0, 0.0)     # cascade without alginate (for the alginate increment)
        res[s.key] = dict(cascade=c, hp_only=h, hp_swro=ro, energy_only=e0, no_alginate=cp, rows=rows if with_rows else None,
                          swro_increment=ro['net_cash_eur'] - h['net_cash_eur'], cascade_vs_swro=c['net_cash_eur'] - ro['net_cash_eur'],
                          coproduct_value=c['net_cash_eur'] - e0['net_cash_eur'],
                          cascade_increment=c['net_cash_eur'] - h['net_cash_eur'],
                          alginate_increment=c['net_cash_eur'] - cp['net_cash_eur'])
    tot = lambda k: sum(r[k] for r in res.values())
    return dict(sites=res, alloc=alloc, food_alginate_t=food_total, pack_alginate_t=pack_total,
                coproduct_value=tot('coproduct_value'), cascade_increment=tot('cascade_increment'), alginate_increment=tot('alginate_increment'),
                swro_increment=tot('swro_increment'), cascade_vs_swro=tot('cascade_vs_swro'),
                fuel_litres=sum(r['cascade']['fuel_litres'] for r in res.values()))


def alginate_breakeven(site: Site, inp: Inputs, pack_t: float, food_t: float = 0.0):
    """Packaging price (EUR/kg) at which adding the alginate line leaves consolidated net cash unchanged."""
    base, _ = hub(site, inp, 'cascade', 0.0, 0.0)
    def gap(price):
        i2 = replace(inp, a=replace(inp.a, pack_price_eur_kg=price))
        c, _ = hub(site, i2, 'cascade', food_t, pack_t)
        return c['net_cash_eur'] - base['net_cash_eur']
    lo, hi = 0.0, 40.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if gap(mid) > 0: hi = mid
        else: lo = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------------------------------------ ERS (Supplementary)
def ers_capture(e: ERS, km): return e.capture_max * (1 - math.exp(-km / e.capture_scale_km))


def ers_system(e: ERS, km: float, diesel: float, hybrid_fuel_eur_l: float, fuel_per_hub_l: float, hybrid_fuel_fossil=False):
    cap = ers_capture(e, km); vkm = e.hgv_vkm_bn * 1e9 * cap
    on = vkm * e.on_wire_share; off = vkm - on; off_h = off * e.hybrid_share; off_b = off - off_h
    elec_TWh = (on + off_b) * e.elec_kWh_km * (1 + e.grid_loss) / 1e9
    liq = off_h * e.hybrid_l_per_km_off_wire
    infra = km * e.capex_eur_km * (e.infra_crf + e.infra_om_frac)
    trucks = vkm / e.truck_km_y
    fuel_price = diesel if hybrid_fuel_fossil else hybrid_fuel_eur_l
    cost_ers = infra + elec_TWh * 1e6 * e.elec_eur_MWh + liq * fuel_price + trucks * e.truck_premium_eur * e.truck_crf - vkm * e.maint_saving_eur_km
    cost_dsl = vkm * e.diesel_l_per_km * diesel
    co2_base = vkm * e.diesel_l_per_km * 2.66 / 1e9
    co2_ers = (elec_TWh * 1e9 * e.grid_kgCO2_kWh + (liq * 2.66 if hybrid_fuel_fossil else 0.0)) / 1e9
    # battery-electric trucks with depot + megawatt charging serving the same truck-km
    bev_eur_kWh = e.bev_depot_share * e.bev_depot_eur_kWh + (1 - e.bev_depot_share) * e.bev_mcs_eur_kWh
    cost_bev = vkm * (e.bev_kWh_km * bev_eur_kWh + e.bev_premium_eur * e.truck_crf / e.truck_km_y - e.maint_saving_eur_km)
    co2_bev = vkm * e.bev_kWh_km * e.grid_kgCO2_kWh / 1e9
    return dict(network_km=km, capture_share=cap, ers_vkm_bn=vkm / 1e9, electricity_TWh=elec_TWh, hybrid_fuel_ML=liq / 1e6,
                hubs_for_hybrid_fuel=liq / fuel_per_hub_l, trucks=trucks, infra_bn_y=infra / 1e9,
                cost_ers_eur_vkm=cost_ers / vkm, cost_diesel_eur_vkm=cost_dsl / vkm, cost_bev_mcs_eur_vkm=cost_bev / vkm,
                net_saving_bn_y=(cost_dsl - cost_ers) / 1e9, bev_net_saving_bn_y=(cost_dsl - cost_bev) / 1e9,
                co2_avoided_Mt=co2_base - co2_ers, co2_avoided_bev_Mt=co2_base - co2_bev,
                abatement_eur_t=(cost_ers - cost_dsl) / ((co2_base - co2_ers) * 1e6), share_2023=(co2_base - co2_ers) / e.hgv_MtCO2_2023)


def ers_transition(e: ERS, diesel, hybrid_price, fuel_per_hub):
    out = []
    for y in range(2026, 2042):
        km = (0.0 if y < 2028 else min(e.network_km_phase1, e.network_km_phase1 * (y - 2027) / 6)) if y <= 2033 else \
            min(e.network_km_full, e.network_km_phase1 + (e.network_km_full - e.network_km_phase1) * (y - 2033) / 5)
        up = 1 / (1 + math.exp(-(y - 2034) / 1.8))
        s = ers_system(e, max(km, 1.0), diesel, hybrid_price, fuel_per_hub)
        out.append(dict(year=y, ers_km=km, uptake=up, co2_avoided_Mt=s['co2_avoided_Mt'] * up * (km > 0),
                        hgv_co2_Mt=e.hgv_MtCO2_2023 - s['co2_avoided_Mt'] * up * (km > 0), electricity_TWh=s['electricity_TWh'] * up * (km > 0)))
    return out


# ------------------------------------------------------------------------------------------------ Monte Carlo
MC_SPEC = {   # name: (target, attribute, low, mode, high)
    'yield_mult': ('inp', 'yield_mult', .5, 1.0, 1.6),
    'electricity_eur_MWh': ('p6', 'nuclear_electric_eur_MWh', 65, 105, 180),
    'eta_II_hp': ('th', 'eta_II_hp', .40, .50, .58),
    'dT_effect_K': ('th', 'dT_effect_K', 2.0, 2.5, 3.5),
    'eta_turbine': ('th', 'eta_turbine', .75, .85, .90),
    'end_condenser_fraction': ('th', 'end_condenser_fraction', .70, .85, .92),
    'distribution_loss': ('th', 'distribution_loss', .02, .05, .10),
    'hp_capex_eur_kW': ('th', 'hp_capex_eur_kW', 450, 700, 1100),
    'med_capex_eur_per_m3d': ('w', 'med_capex_eur_per_m3d', 1500, 2200, 3500),
    'price_bulk_eur_m3': ('w', 'price_bulk_eur_m3', .40, .85, 1.50),
    'price_demin_eur_m3': ('w', 'price_demin_eur_m3', 1.5, 2.5, 4.0),
    'mains_eur_m3': ('w', 'mains_eur_m3', 1.0, 1.5, 2.5),
    'gh_price_eur_kg': ('f', 'gh_price_eur_kg', 2.4, 3.1, 3.8),
    'prawn_price_eur_kg': ('f', 'prawn_price_eur_kg', 10, 14, 20),
    'prawn_cost_ex_energy_eur_kg': ('f', 'prawn_cost_ex_energy_eur_kg', 8, 10.2, 14),
    'fish_margin_shift': ('f', 'fish_margin_shift', -1.0, 0.0, 0.8),
    'kelp_capture_mult': ('f', 'kelp_capture_mult', .3, 1.0, 1.6),
    'honey_mult': ('f', 'honey_mult', .5, 1.0, 1.6),
    'honey_price_eur_kg': ('f', 'honey_price_eur_kg', 5, 8, 12),
    'honey_smoked_premium_eur_kg': ('f', 'honey_smoked_premium_eur_kg', .5, 2.5, 5),
    'alginate_yield_mult': ('a', 'yield_mult', .75, 1.0, 1.3),
    'food_alginate_eur_kg': ('a', 'food_price_eur_kg', 8, 11, 15),
    'pack_alginate_eur_kg': ('a', 'pack_price_eur_kg', 3, 4.5, 7),
    'alginate_process_eur_kg': ('a', 'process_cost_eur_kg', 1.6, 2.4, 3.6),
    'replacement_fuel_eur_l': ('a', 'replacement_fuel_eur_l', 1.4, 2.0, 2.8),
    'plastic_kgCO2_kg': ('a', 'plastic_avoided_kgCO2_kg', 2.5, 3.5, 4.5),
    'prawn_capex_eur_kg_y': ('f', 'prawn_capex_eur_per_kg_y', 8, 12, 18),
    'fish_capex_eur_kg_y': ('f', 'fish_capex_eur_per_kg_y', 3, 5, 8),
    'alginate_capex_eur_t_y': ('a', 'capex_eur_per_t_y', 4000, 7500, 12000),
    'swro_kWh_m3': ('w', 'swro_kWh_m3', 2.8, 3.5, 5.0),
    'swro_capex_eur_per_m3d': ('w', 'swro_capex_eur_per_m3d', 1200, 1800, 3000),
    'gh_direct_share': ('f', 'gh_direct_share', .35, .55, .70),
    'grid_buy_eur_MWh': ('th', 'grid_buy_eur_MWh', 90, 130, 200),
    'boiler_capex_eur_kW': ('th', 'boiler_capex_eur_kW', 60, 100, 150),
    'ers_capex_eur_km': ('e', 'capex_eur_km', 2.5e6, 3.4e6, 4.5e6),
    'ers_elec_eur_MWh': ('e', 'elec_eur_MWh', 65, 105, 150),
    'diesel_longrun_eur_l': ('e', 'diesel_longrun_eur_l', 1.10, 1.45, 1.90),
    'ers_truck_premium_eur': ('e', 'truck_premium_eur', 20000, 45000, 80000),
    'ers_capture_max': ('e', 'capture_max', .40, .55, .65),
    'ers_on_wire_share': ('e', 'on_wire_share', .60, .75, .85),
}


def apply(over: dict) -> Inputs:
    inp = Inputs()
    parts = dict(p6=inp.p6, th=inp.th, w=inp.w, f=inp.f, a=inp.a, e=inp.e)
    top = {}
    for k, v in over.items():
        tgt, attr = MC_SPEC[k][0], MC_SPEC[k][1]
        if tgt == 'inp': top[attr] = v
        else: parts[tgt] = replace(parts[tgt], **{attr: v})
    return Inputs(**parts, **top)


# MED capacity (Mm3/yr) maximising cascade minus heat-pump-only at central inputs with firm heat (data/v12_med_rightsizing.csv); fixed ex ante in the Monte Carlo
RIGHT_SIZED_M3 = dict(DKQ=1.05e6, LEH=1.05e6, BRE=1.15e6, STN=1.10e6, LRO=1.00e6, FOS=0.90e6)


def rightsized_increment(inp: Inputs, alloc=None):
    alloc = alloc or allocate_alginate(inp)[0]; tot = 0.0; per = {}
    for s_ in SITES:
        i2 = replace(inp, w=replace(inp.w, med_water_m3_y=RIGHT_SIZED_M3[s_.key]))
        d = hub(s_, i2, 'cascade', *alloc[s_.key])[0]['net_cash_eur'] - hub(s_, i2, 'hp_only', *alloc[s_.key])[0]['net_cash_eur']
        per[s_.key] = d; tot += d
    return tot, per


def headline(inp: Inputs):
    n = national(inp)
    rs_tot, rs_per = rightsized_increment(inp, n['alloc'])
    e = inp.e
    fuel_per_hub = n['fuel_litres'] / len(SITES)
    hyb_price = np.mean([r['cascade']['fuel_cost_eur_l'] for r in n['sites'].values()])
    s = ers_system(e, e.network_km_full, e.diesel_longrun_eur_l, hyb_price, fuel_per_hub)
    bre = n['sites']['BRE']
    pack_be = alginate_breakeven(SITES[2], inp, n['alloc']['BRE'][1]) if inp is not None else None
    imta_N = sum(r['cascade']['imta']['captured_N_t'] for r in n['sites'].values())
    alg_co2 = sum((r['cascade']['alginate'] or {}).get('co2_t_low_carbon_fill', 0.0) for r in n['sites'].values())
    return dict(coproduct_value_MEUR=n['coproduct_value'] / 1e6, cascade_increment_MEUR=n['cascade_increment'] / 1e6,
                swro_increment_MEUR=n['swro_increment'] / 1e6, cascade_vs_swro_MEUR=n['cascade_vs_swro'] / 1e6,
                rightsized_increment_MEUR=rs_tot / 1e6, brest_rightsized_increment_MEUR=rs_per['BRE'] / 1e6,
                imta_captured_N_t=imta_N, alginate_co2_kt_low_carbon_fill=alg_co2 / 1e3,
                alginate_increment_MEUR=n['alginate_increment'] / 1e6,
                brest_coproduct_MEUR=bre['coproduct_value'] / 1e6, brest_cascade_increment_MEUR=bre['cascade_increment'] / 1e6,
                brest_first_law=bre['cascade']['first_law'], brest_net_export_GWh=bre['cascade']['net_export_GWh'],
                brest_pack_breakeven_eur_kg=pack_be,
                ers_net_saving_bn=s['net_saving_bn_y'], ers_co2_Mt=s['co2_avoided_Mt'], ers_abatement_eur_t=s['abatement_eur_t'])


def water_breakeven(inp: Inputs, key='BRE'):
    """Uniform uplift (EUR/m3) on bulk, demineralised and mains water prices at which the cascade equals heat-pump-only."""
    def gap(d):
        i2 = replace(inp, w=replace(inp.w, price_bulk_eur_m3=inp.w.price_bulk_eur_m3 + d, price_demin_eur_m3=inp.w.price_demin_eur_m3 + d,
                                    mains_eur_m3=inp.w.mains_eur_m3 + d))
        site = next(s for s in SITES if s.key == key)
        alloc = allocate_alginate(i2)[0][key]
        return hub(site, i2, 'cascade', *alloc)[0]['net_cash_eur'] - hub(site, i2, 'hp_only', *alloc)[0]['net_cash_eur']
    lo, hi = -2.0, 5.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if gap(mid) > 0: hi = mid
        else: lo = mid
    return (lo + hi) / 2


def monte_carlo(n=2000, seed=20261111):
    rng = np.random.default_rng(seed); rows = []
    for i in range(n):
        over = {k: float(rng.triangular(lo, mo, hi)) for k, (_, _, lo, mo, hi) in MC_SPEC.items()}
        h = headline(apply(over)); h['draw'] = i; rows.append(h)
    return rows


# ------------------------------------------------------------------------------------------------ outputs
def write_csv(name, rows):
    with open(DATA / name, 'w', newline='', encoding='utf8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def slim(h):
    """JSON-friendly copy of a hub result."""
    d = {k: v for k, v in h.items() if k not in ('per_user',)}
    d['per_user'] = {k: {kk: (float(vv) if not isinstance(vv, list) else [float(x) for x in vv]) for kk, vv in v.items()} for k, v in h['per_user'].items()}
    return d


def main(mc_n=2000):
    inp = Inputs()
    n = national(inp, with_rows=True)
    md = med_design(inp.th)
    e = inp.e
    fuel_per_hub = n['fuel_litres'] / len(SITES)
    hyb_price = float(np.mean([r['cascade']['fuel_cost_eur_l'] for r in n['sites'].values()]))
    # per-site summary
    site_rows = []
    for s in SITES:
        r = n['sites'][s.key]; c = r['cascade']; h = r['hp_only']
        alg = c['alginate'] or {}
        be_pack = alginate_breakeven(s, inp, n['alloc'][s.key][1]) if s.alginate_yield > 0 else float('nan')
        be_comb = alginate_breakeven(s, inp, n['alloc'][s.key][1], n['alloc'][s.key][0]) if s.alginate_yield > 0 else float('nan')
        site_rows.append(dict(key=s.key, site=s.name, seaweed=s.seaweed, fish=s.fish, yield_tDM_ha=s.yield_tDM_ha, kelp_dry_t=c['kelp_dry_t'],
                              fuel_ML=c['fuel_litres'] / 1e6, fuel_cost_eur_l=c['fuel_cost_eur_l'], first_law=c['first_law'], first_law_hp_only=h['first_law'],
                              net_export_GWh=c['net_export_GWh'], net_export_hp_only_GWh=h['net_export_GWh'],
                              lowT_demand_GWh=c['lowT_demand_GWh'], lowT_from_med_GWh=c['lowT_from_med_GWh'], hp_elec_GWh=c['hp_elec_GWh'],
                              hp_elec_hp_only_GWh=h['hp_elec_GWh'], med_unused_GWh=c['med_unused_GWh'],
                              hp_capacity_MW=c['hp_capacity_MW'], hp_capacity_hp_only_MW=h['hp_capacity_MW'],
                              coproduct_value_MEUR=r['coproduct_value'] / 1e6, cascade_increment_MEUR=r['cascade_increment'] / 1e6,
                              swro_increment_MEUR=r['swro_increment'] / 1e6, cascade_vs_swro_MEUR=r['cascade_vs_swro'] / 1e6,
                              net_export_swro_GWh=r['hp_swro']['net_export_GWh'],
                              alginate_increment_MEUR=r['alginate_increment'] / 1e6, alginate_t=alg.get('total_t', 0.0),
                              alginate_pack_breakeven_eur_kg=be_pack, alginate_food_plus_pack_breakeven_eur_kg=be_comb,
                              imta_captured_N_t=c['imta']['captured_N_t'], imta_share=c['imta']['captured_share'],
                              honey_t=c['honey']['honey_t'], smoked_t=c['smoked']['smoked_t'], salmonid=s.salmonid))
    write_csv('v12_sites_summary.csv', site_rows)
    # enterprise ledgers (cascade) per site
    led = []
    for s in SITES:
        for name, v in n['sites'][s.key]['cascade']['enterprises'].items():
            led.append(dict(site=s.name, enterprise=name, external_sales_eur=v['sales'], cash_costs_eur=v['cash_costs'], capital_eur=v['capital'],
                            electricity_MWh=v['elec_MWh'], electricity_eur=v['elec_MWh'] * inp.p6.nuclear_electric_eur_MWh,
                            water_transfer_paid_eur=v['water_transfer_paid'], water_transfer_received_eur=v['water_transfer_received'], net_eur=v['net_eur']))
    write_csv('v12_enterprise_ledger_cascade.csv', led)
    # cascade vs heat-pump-only bridge per site
    bridge = []
    pe = inp.p6.nuclear_electric_eur_MWh
    for s in SITES:
        c = n['sites'][s.key]['cascade']; h = n['sites'][s.key]['hp_only']
        ci, hi = c['enterprises']['heat_and_water_infrastructure'], h['enterprises']['heat_and_water_infrastructure']
        bridge.append(dict(site=s.name,
                           heat_pump_electricity_avoided_eur=(h['hp_elec_GWh'] - c['hp_elec_GWh']) * 1000 * pe,
                           mains_water_avoided_eur=(h['water']['bought_mains'] - c['water']['bought_mains']) * inp.w.mains_eur_m3,
                           water_sales_eur=ci['sales'] - hi['sales'],
                           turbine_work_lost_eur=-c['turbine_penalty_GWh'] * 1000 * pe,
                           med_pumping_and_distribution_eur=-(c['pumping_GWh'] * 1000 + inp.w.med_water_m3_y * inp.w.med_elec_kWh_m3 / 1000) * pe,
                           med_capital_om_brine_eur=-(c['med_capex_MEUR'] * 1e6 * (inp.th.crf + inp.w.med_fixed_om_frac) + inp.w.med_water_m3_y * inp.w.brine_eur_m3),
                           heat_equipment_capital_difference_eur=-(c['heat_capex_MEUR'] - h['heat_capex_MEUR']) * 1e6 * (inp.th.crf + inp.th.hp_om_frac),
                           outage_grid_backup_eur=-(c['grid_backup_GWh'] - h['grid_backup_GWh']) * 1000 * inp.th.grid_buy_eur_MWh,
                           water_polishing_eur=-(c['polish_elec_GWh'] * 1000 * pe + c['water']['polished_m3'] * (inp.w.edi_eur_m3 + (inp.w.ro2_eur_m3 if inp.w.med_full_polish else 0.0))),
                           cascade_increment_eur=n['sites'][s.key]['cascade_increment'],
                           swro_increment_eur=n['sites'][s.key]['swro_increment'], cascade_vs_swro_eur=n['sites'][s.key]['cascade_vs_swro']))
    write_csv('v12_cascade_vs_hp_only_bridge.csv', bridge)
    for s in SITES:
        write_csv(f'v12_monthly_{s.key}.csv', n['sites'][s.key]['rows'])
    # MED size sweep at Brest
    sweep = []
    bre_s = SITES[2]; fa_b, pa_b = allocate_alginate(inp)[0]['BRE']
    for m3 in np.round(np.arange(0.5, 3.5001, 0.05), 2) * 1e6:
        i2 = replace(inp, w=replace(inp.w, med_water_m3_y=float(m3)))
        c_, _ = hub(bre_s, i2, 'cascade', fa_b, pa_b); h_, _ = hub(bre_s, i2, 'hp_only', fa_b, pa_b); ro_, _ = hub(bre_s, i2, 'hp_swro', fa_b, pa_b)
        e_, _ = hub(bre_s, i2, 'energy_only')
        i3 = replace(i2, th=replace(i2.th, hp_redundant=True))
        cr_, _ = hub(bre_s, i3, 'cascade', fa_b, pa_b); hr_, _ = hub(bre_s, i3, 'hp_only', fa_b, pa_b)

        sweep.append(dict(med_Mm3=float(m3) / 1e6, lowT_from_med_GWh=c_['lowT_from_med_GWh'], from_cond_hp_GWh=c_['lowT_from_condenser_hp_GWh'],
                          unused_GWh=c_['med_unused_GWh'], hp_capacity_MW=c_['hp_capacity_MW'],
                          cascade_increment_MEUR=(c_['net_cash_eur'] - h_['net_cash_eur']) / 1e6,
                          swro_increment_MEUR=(ro_['net_cash_eur'] - h_['net_cash_eur']) / 1e6,
                          cascade_vs_swro_MEUR=(c_['net_cash_eur'] - ro_['net_cash_eur']) / 1e6,
                          cascade_increment_redundant_hp_MEUR=(cr_['net_cash_eur'] - hr_['net_cash_eur']) / 1e6,
                          boiler_MW=c_['boiler_MW'],
                          coproduct_MEUR=(c_['net_cash_eur'] - e_['net_cash_eur']) / 1e6))
    write_csv('v12_med_size_sweep_brest.csv', sweep)
    # right-sizing: MED capacity that maximises the cascade increment at each site (heat pumps sized to residual load)
    alloc0 = allocate_alginate(inp)[0]; rights = []
    for s_ in SITES:
        fa_s, pa_s = alloc0[s_.key]; best = None
        for m3 in np.round(np.arange(0.2, 3.0001, 0.05), 2) * 1e6:
            i2 = replace(inp, w=replace(inp.w, med_water_m3_y=float(m3)))
            c_, _ = hub(s_, i2, 'cascade', fa_s, pa_s); h_, _ = hub(s_, i2, 'hp_only', fa_s, pa_s); ro_, _ = hub(s_, i2, 'hp_swro', fa_s, pa_s)
            d = dict(key=s_.key, site=s_.name, med_Mm3=float(m3) / 1e6, cascade_increment_MEUR=(c_['net_cash_eur'] - h_['net_cash_eur']) / 1e6,
                     cascade_vs_swro_MEUR=(c_['net_cash_eur'] - ro_['net_cash_eur']) / 1e6, lowT_share_from_med=c_['lowT_from_med_GWh'] / c_['lowT_demand_GWh'])
            if best is None or d['cascade_increment_MEUR'] > best['cascade_increment_MEUR']: best = d
        rights.append(best)
    write_csv('v12_med_rightsizing.csv', rights)
    rs_central = rightsized_increment(inp)[0]
    # non-firm diagnostic: heat the installed equipment cannot deliver during outages (not valued)
    inp_nf = replace(inp, th=replace(inp.th, firm_heat=False)); alloc_c = allocate_alginate(inp)[0]
    for r_ in rights:
        s_ = next(x for x in SITES if x.key == r_['key'])
        i2 = replace(inp_nf, w=replace(inp_nf.w, med_water_m3_y=RIGHT_SIZED_M3[s_.key]))
        hc, _ = hub(s_, i2, 'cascade', *alloc_c[s_.key]); hh, _ = hub(s_, i2, 'hp_only', *alloc_c[s_.key])
        r_['unmet_heat_without_backup_GWh'] = hc['unmet_heat_GWh']; r_['unmet_share_of_demand'] = hc['unmet_heat_GWh'] / hc['lowT_demand_GWh']
        r_['unmet_heat_hp_only_GWh'] = hh['unmet_heat_GWh']
    write_csv('v12_med_rightsizing.csv', rights)
    grid2 = []
    for gs in (0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70):
        for pe_ in (65, 85, 105, 130, 155, 180):
            i2 = replace(inp, f=replace(inp.f, gh_direct_share=gs), p6=replace(inp.p6, nuclear_electric_eur_MWh=pe_))
            grid2.append(dict(gh_direct_share=gs, electricity_eur_MWh=pe_, rightsized_firm_MEUR=rightsized_increment(i2)[0] / 1e6,
                              full_size_MEUR=national(i2)['cascade_increment'] / 1e6))
    write_csv('v12_sensitivity_gh_share_x_electricity.csv', grid2)
    i_pol = replace(inp, w=replace(inp.w, med_full_polish=True)); n_pol = national(i_pol)
    polish_sens = dict(full_size_increment_MEUR=n_pol['cascade_increment'] / 1e6, cascade_vs_swro_MEUR=n_pol['cascade_vs_swro'] / 1e6,
                       rightsized_MEUR=rightsized_increment(i_pol)[0] / 1e6)
    i_gc = replace(inp, th=replace(inp.th, grid_connection_eur_kW=150.0)); n_gc = national(i_gc)
    gridconn_sens = dict(eur_kW=150.0, full_size_increment_MEUR=n_gc['cascade_increment'] / 1e6, rightsized_MEUR=rightsized_increment(i_gc)[0] / 1e6,
                         coproduct_value_MEUR=n_gc['coproduct_value'] / 1e6, swro_increment_MEUR=n_gc['swro_increment'] / 1e6)
    i_ws = replace(inp, w=replace(inp.w, price_bulk_eur_m3=inp.w.price_bulk_eur_m3 * 0.85, price_demin_eur_m3=inp.w.price_demin_eur_m3 * 0.85))
    interruptible_sens = dict(discount=0.15, full_size_increment_MEUR=national(i_ws)['cascade_increment'] / 1e6, rightsized_MEUR=rightsized_increment(i_ws)[0] / 1e6)
    red_central = rightsized_increment(replace(inp, th=replace(inp.th, hp_redundant=True)))[0]
    water_be = {s.key: water_breakeven(inp, s.key) for s in SITES}
    # alginate price sweep at Brest (packaging only, consolidated)
    bre = SITES[2]; pk = n['alloc']['BRE'][1]
    base_b, _ = hub(bre, inp, 'cascade', 0, 0)
    asweep = []
    for price in np.arange(2.0, 12.01, 0.5):
        for repl in (1.4, 2.0, 2.8):
            i2 = replace(inp, a=replace(inp.a, pack_price_eur_kg=float(price), replacement_fuel_eur_l=repl))
            c, _ = hub(bre, i2, 'cascade', 0, pk)
            asweep.append(dict(price_eur_kg=float(price), replacement_fuel_eur_l=repl, margin_MEUR=(c['net_cash_eur'] - base_b['net_cash_eur']) / 1e6,
                               breakeven_eur_kg=alginate_breakeven(bre, i2, pk)))
    write_csv('v12_alginate_price_sweep_brest.csv', asweep)
    # thermal feasibility table
    th = inp.th
    tq = dict(med_design=md, cop={
        'MED loop -> greenhouse peak (50 C)': cop(th, th.T_gh_peak_C, (th.loop_supply_C + th.loop_return_C) / 2),
        'MED loop -> dryers/smokehouse (70 C)': cop(th, th.T_dry_C, (th.loop_supply_C + th.loop_return_C) / 2),
        'condenser loop (Brest, Jan) -> prawn RAS (31 C)': cop(th, th.T_prawn_C, SITES[2].sst[0] + th.cond_loop_rise_K),
        'condenser loop (Brest, Jan) -> greenhouse base (35 C)': cop(th, th.T_gh_base_C, SITES[2].sst[0] + th.cond_loop_rise_K),
        'condenser loop (Brest, Jan) -> greenhouse peak (50 C)': cop(th, th.T_gh_peak_C, SITES[2].sst[0] + th.cond_loop_rise_K),
        'condenser loop (Brest, Jan) -> dryers (70 C)': cop(th, th.T_dry_C, SITES[2].sst[0] + th.cond_loop_rise_K)})
    # ERS
    ers = {}
    for lab, d in (('longrun_central', e.diesel_longrun_eur_l), ('longrun_low', e.diesel_low_eur_l), ('longrun_high', e.diesel_high_eur_l),
                   ('spot_nov2026', e.diesel_spot_nov2026_eur_l), ('spot_feb2026', e.diesel_spot_feb2026_eur_l)):
        ers[lab] = ers_system(e, e.network_km_full, d, hyb_price, fuel_per_hub)
    ers['phase1_central'] = ers_system(e, e.network_km_phase1, e.diesel_longrun_eur_l, hyb_price, fuel_per_hub)
    ers['central_fossil_hybrid_fuel'] = ers_system(e, e.network_km_full, e.diesel_longrun_eur_l, hyb_price, fuel_per_hub, hybrid_fuel_fossil=True)
    write_csv('v12_ers_cases.csv', [dict(case=k, **v) for k, v in ers.items()])
    write_csv('v12_ers_network_curve.csv', [ers_system(e, km, e.diesel_longrun_eur_l, hyb_price, fuel_per_hub) for km in range(250, 12001, 250)])
    traj = ers_transition(e, e.diesel_longrun_eur_l, hyb_price, fuel_per_hub); write_csv('v12_ers_transition.csv', traj)
    # Monte Carlo
    mc = monte_carlo(mc_n); write_csv('v12_monte_carlo.csv', mc)
    q = {k: [float(x) for x in np.nanpercentile([r[k] for r in mc], [5, 50, 95])] for k in mc[0] if k != 'draw'}
    prob = dict(coproduct_positive=float(np.mean([r['coproduct_value_MEUR'] > 0 for r in mc])),
                cascade_beats_hp_only=float(np.mean([r['cascade_increment_MEUR'] > 0 for r in mc])),
                cascade_beats_swro=float(np.mean([r['cascade_vs_swro_MEUR'] > 0 for r in mc])),
                swro_beats_hp_only=float(np.mean([r['swro_increment_MEUR'] > 0 for r in mc])),
                rightsized_beats_hp_only=float(np.mean([r['rightsized_increment_MEUR'] > 0 for r in mc])),
                alginate_positive=float(np.mean([r['alginate_increment_MEUR'] > 0 for r in mc])),
                ers_saving_positive=float(np.mean([r['ers_net_saving_bn'] > 0 for r in mc])),
                brest_export_nonnegative=float(np.mean([r['brest_net_export_GWh'] >= 0 for r in mc])))
    v6 = simulate_v6(P6(), 'nuclear')
    summary = dict(scope='V12 screening model; constant 2026 EUR; consolidated accounts without heat credits; monthly resolution',
                   v6_reference=dict(first_law=v6['useful_energy_fraction'], fuel_cost_eur_l=v6['renewable_fuel_cost_eur_l']),
                   national=dict(coproduct_value_MEUR=n['coproduct_value'] / 1e6, cascade_increment_MEUR=n['cascade_increment'] / 1e6,
                                 swro_increment_MEUR=n['swro_increment'] / 1e6, cascade_vs_swro_MEUR=n['cascade_vs_swro'] / 1e6,
                                 alginate_increment_MEUR=n['alginate_increment'] / 1e6, fuel_ML=n['fuel_litres'] / 1e6,
                                 food_alginate_t=n['food_alginate_t'], pack_alginate_t=n['pack_alginate_t'],
                                 alloc={k: list(v) for k, v in n['alloc'].items()}),
                   sites={k: dict(cascade=slim(v['cascade']), hp_only=slim(v['hp_only']), hp_swro=slim(v['hp_swro']), energy_only=slim(v['energy_only']),
                                  swro_increment=v['swro_increment'], cascade_vs_swro=v['cascade_vs_swro'],
                                  coproduct_value=v['coproduct_value'], cascade_increment=v['cascade_increment'], alginate_increment=v['alginate_increment'])
                          for k, v in n['sites'].items()},
                   site_table=site_rows, med_rightsizing=rights, rightsized_national_MEUR=rs_central / 1e6, grid_connection_sensitivity=gridconn_sens, interruptible_water_sensitivity=interruptible_sens, rightsized_redundant_national_MEUR=red_central / 1e6, polishing_sensitivity=polish_sens, sensitivity_2d=grid2, thermal=tq, water_price_uplift_to_breakeven_eur_m3=water_be, ers=ers, ers_hybrid_fuel_price_eur_l=hyb_price, ers_fuel_per_hub_l=fuel_per_hub,
                   ers_transition=dict(co2_2041_Mt=traj[-1]['hgv_co2_Mt'], cumulative_Mt=sum(t['co2_avoided_Mt'] for t in traj)),
                   monte_carlo=dict(n=len(mc), seed=20261111, inputs=list(MC_SPEC.keys()), quantiles_5_50_95=q, probabilities=prob),
                   inputs=dict(thermo=asdict(th), water=asdict(inp.w), food=asdict(inp.f), alginate=asdict(inp.a), ers=asdict(e),
                               sites=[asdict(s) for s in SITES]))
    (DATA / 'v12_results.json').write_text(json.dumps(summary, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating,)) else str(o)), encoding='utf8')
    return summary


if __name__ == '__main__':
    S = main()
    print(json.dumps(S['national'], indent=1, default=float)[:800])
    for r in S['site_table']:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k not in ('seaweed',)})
    print('MED', S['thermal']['med_design']); print('COP', {k: round(v, 2) for k, v in S['thermal']['cop'].items()})
    print('ERS', {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in S['ers'].items() if k in ('longrun_central', 'spot_nov2026', 'central_fossil_hybrid_fuel')})
    print('hyb price', S['ers_hybrid_fuel_price_eur_l'], 'fuel/hub', S['ers_fuel_per_hub_l'])
    print('MC', json.dumps(S['monte_carlo']['quantiles_5_50_95'], default=float)[:1200]); print(S['monte_carlo']['probabilities'])
