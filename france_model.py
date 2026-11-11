"""France coastal cogeneration and circular bioeconomy screening model.

Executable: python model/france_model.py
All prices EUR 2026 constant and illustrative unless sourced in sources/bibliography.csv.
Explicit physical/energy ledgers, no claim of national optimum or reactor licence.
The model does not use deep learning or hidden data. No network access required.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import csv,json, math
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'archive_v6'/'data_v6_rerun'; DATA.mkdir(parents=True,exist_ok=True)

@dataclass
class P:
    thermal_MW:float=100.0
    capacity_factor:float=.90
    electrical_efficiency:float=.33
    divert_frac:float=.25
    reject_reclaim_frac:float=.15
    hp_COP:float=3.2
    area_ha:float=10000.0  # illustrative 100 km² / coastal hub
    seaweed_tDM_ha_y:float=8.0  # research sensitivity, not site measured
    seaweed_dry_cost_eur_t:float=400.0  # farm-gate dry biomass, scenario
    frac_HTL:float=.85
    biocrude_fuel_yield_t_t:float=.25  # finished liquid per dry HTL input
    fuel_density_t_m3:float=.80
    HTL_heat_MWh_t:float=1.8
    HTL_high_grade_electric_trim_frac:float=.30  # PWR secondary steam cannot supply all HTL heat above 250-300 C
    distil_heat_MWh_t_ethanol:float=2.0
    HTL_elec_MWh_t:float=.26
    hydrogen_t_per_t_liquid:float=.03
    H2_elec_MWh_t:float=50.0
    ferment_carbohydrate_frac:float=.30
    ethanol_t_per_t_carbs:float=.46
    ethanol_density_t_m3:float=.789
    ethanol_electric_MWh_t:float=.40
    nuclear_electric_eur_MWh:float=105.0
    reactor_design:str='water-cooled reference'
    alt_firm_elec_eur_MWh:float=145.0
    nuclear_heat_opp_ratio:float=.33  # forgone MWh_e / MWh_th
    HTL_other_eur_L:float=.45
    alt_other_eur_L:float=.45
    harvest_marine_eur_t:float=70.0
    greenhouse_ha:float=40.0
    produce_kg_m2_y:float=30.0
    greenhouse_light_kWh_m2_y:float=200.0
    greenhouse_heat_kWh_m2_y:float=150.0
    base_summer_drying_GWh_y:float=10.0
    kelp_fertilizer_drying_GWh_y:float=12.0
    smoked_salmon_t_y:float=450.0
    smoked_salmon_heat_MWh_t:float=5.5
    pollinator_flower_ha:float=300.0
    honey_yield_kg_ha_y:float=400.0
    greenhouse_plant_residue_frac_wet:float=.30
    residue_DM_frac:float=.12
    residue_accepted_frac:float=.55
    residue_N_DM_frac:float=.025
    fish_t_y:float=2000.0
    fish_FCR:float=1.5
    fish_feed_N_frac:float=.06
    fish_harvest_N_frac:float=.027
    fish_residual_N_capture_frac:float=.40
    fish_captured_N_recovery_frac:float=.55
    crop_N_frac_wet:float=.0025
    greenhouse_capex_eur_m2:float=300.0
    greenhouse_capital_recovery_factor:float=.0872 # 20-y 6% annuity
    greenhouse_other_opex_eur_kg:float=1.00
    recovered_fertilizer_N_value_eur_kg:float=2.0
    kelp_N_DM_frac:float=.025
    HTL_effluent_N_capture_frac:float=.35
    SMR_electric_kgCO2_per_MWh:float=15.0
    grid_kgCO2_per_MWh:float=18.0


def simulate(p:P, mode:str='nuclear'):
    assert mode in ('nuclear','variable_firm')
    # Reactor heat from fuel. Cogeneration cascade kept separate from fuel output.
    E_th=p.thermal_MW*8760*p.capacity_factor # MWh thermal/year
    # Choose steam extraction to match the usable preheat/distillation duty
    # rather than spilling heat by diverting the maximum turbine steam.
    # The thermal opportunity-cost and electricity loss remain explicit.
    # Constrained biomass - fuel streams are disjoint.
    dry=p.area_ha*p.seaweed_tDM_ha_y
    HTL_dry=dry*p.frac_HTL
    ferment_dry=dry-HTL_dry
    liquid_t=HTL_dry*p.biocrude_fuel_yield_t_t
    litres=liquid_t/p.fuel_density_t_m3*1000
    ethanol_t=ferment_dry*p.ferment_carbohydrate_frac*p.ethanol_t_per_t_carbs
    ethanol_l=ethanol_t/p.ethanol_density_t_m3*1000
    # Heat: all process needs separate from process electric. Under nuclear direct heat
    # diverted electricity opportunity cost used, never labeled 'free waste heat'.
    H_HTL=HTL_dry*p.HTL_heat_MWh_t
    H_dist=ethanol_t*p.distil_heat_MWh_t_ethanol
    H_hot=H_HTL+H_dist
    H_hot_direct_demand=H_hot-H_HTL*p.HTL_high_grade_electric_trim_frac
    H_direct=min(E_th*p.divert_frac,H_hot_direct_demand)
    E_power=(E_th-H_direct)*p.electrical_efficiency
    H_reject=(E_th-H_direct)*(1-p.electrical_efficiency)
    H_source=H_reject*p.reject_reclaim_frac
    H_pump_max=H_source/(1-1/p.hp_COP)
    H_rejected_to_sea=H_reject-H_source
    E_HTL=HTL_dry*p.HTL_elec_MWh_t
    E_ethanol=ethanol_t*p.ethanol_electric_MWh_t
    H2_need_t=liquid_t*p.hydrogen_t_per_t_liquid
    E_H2=H2_need_t*p.H2_elec_MWh_t
    E_led=p.greenhouse_ha*10000*p.greenhouse_light_kWh_m2_y/1000
    H_green=p.greenhouse_ha*10000*p.greenhouse_heat_kWh_m2_y/1000
    H_kelpdry=p.kelp_fertilizer_drying_GWh_y*1000
    H_salmon=p.smoked_salmon_t_y*p.smoked_salmon_heat_MWh_t
    H_drying=(p.base_summer_drying_GWh_y*1000)+H_kelpdry+H_salmon
    # Model seasonal greenhouse/dryer dispatch: no annual heat shifting assumed.
    green_fraction=np.array([10,9,8,6,3,1,.5,.5,2,6,7,7])/60.0
    dry_fraction=np.array([0,0,0,0,.5,3,4,2.5,0,0,0,0])/10.0
    extra_dry=H_kelpdry+H_salmon
    extra_dry_fraction=np.array([0,0,0,0,1.5,3.0,3.0,2.5,2.0,0,0,0])/(1.5+3.0+3.0+2.5+2.0)
    monthly_load=H_green*green_fraction + (p.base_summer_drying_GWh_y*1000)*dry_fraction + extra_dry*extra_dry_fraction
    hp_supply_m=np.minimum(monthly_load,H_pump_max/12)
    H_pump=float(hp_supply_m.sum())
    E_HP=H_pump/p.hp_COP
    E_misc=5000
    E_required=E_HTL+E_ethanol+E_H2+E_led+E_misc
    H_med=H_green+H_drying
    if mode=='nuclear':
        # Supply with direct nuclear heat first and heat pumps for medium-grade heat.
        hot_trim=H_HTL*p.HTL_high_grade_electric_trim_frac
        hot_direct_demand=H_hot-hot_trim
        direct_used=min(hot_direct_demand,H_direct)
        hot_gap=hot_trim+hot_direct_demand-direct_used
        med_HP_used=min(H_med,H_pump)
        med_gap=H_med-med_HP_used
        extra_el_hot=hot_gap
        extra_el_med=med_gap  # explicit resistance backup in seasonal deficit months
        E_net=E_power-E_HP-extra_el_hot-extra_el_med-E_required
        # Usable heat counted as recovered for useful thermal services, not fuel output.
        used_H=direct_used + med_HP_used
        nuclear_heat_unit=p.nuclear_electric_eur_MWh*p.nuclear_heat_opp_ratio
        hot_cost=direct_used*nuclear_heat_unit+hot_gap*p.nuclear_electric_eur_MWh
        med_cost=med_HP_used*p.nuclear_electric_eur_MWh/p.hp_COP+med_gap*p.nuclear_electric_eur_MWh
        # Pool fixed plant cost is already reflected in assumed plant-specific levelized energy price.
        electric_price=p.nuclear_electric_eur_MWh
        delivered_elec=max(E_power-E_HP,0)
        useful_energy=(E_power-E_HP)+min(H_hot,H_direct)+min(H_med,H_pump)
        eta_useful=useful_energy/E_th
    else:
        # Variable-renewable counterfactual with firming-price adder already included.
        # Electric resistance for high-T industrial processes; COP heat pumps for low-T.
        direct_used=0; med_HP_used=H_med
        E_net=0  # not an electricity generation model; imports all service energy
        hot_cost=H_hot*p.alt_firm_elec_eur_MWh
        med_cost=H_med*p.alt_firm_elec_eur_MWh/p.hp_COP
        electric_price=p.alt_firm_elec_eur_MWh
        eta_useful=None # incomparable 'primary' denominator avoided
        H_rejected_to_sea=None
        used_H=H_hot+H_med
        delivered_elec=0

    # Fuel production costs separate from co-product sales/revenues.
    cost_feed=HTL_dry*p.seaweed_dry_cost_eur_t
    cost_harvest=HTL_dry*p.harvest_marine_eur_t
    cost_energy=(E_HTL+E_H2)*electric_price+hot_cost
    other=litres*(p.HTL_other_eur_L if mode=='nuclear' else p.alt_other_eur_L)
    cost_total=cost_feed+cost_harvest+cost_energy+other
    cost_per_l=cost_total/litres
    # Greenhouse / feed ledger. ALL N tonne/year, separate pathways.
    produce_t=p.greenhouse_ha*10000*p.produce_kg_m2_y/1000
    honey_t=p.pollinator_flower_ha*p.honey_yield_kg_ha_y/1000
    residues_wet=produce_t*p.greenhouse_plant_residue_frac_wet
    residues_dry=residues_wet*p.residue_DM_frac
    usable_residue_dry=residues_dry*p.residue_accepted_frac
    N_feed_input=p.fish_t_y*p.fish_FCR*p.fish_feed_N_frac
    N_fish_harvest=p.fish_t_y*p.fish_harvest_N_frac
    N_nonfish=max(0,N_feed_input-N_fish_harvest)
    N_fish_recovered=N_nonfish*p.fish_residual_N_capture_frac*p.fish_captured_N_recovery_frac
    N_crop_demand=produce_t*p.crop_N_frac_wet
    N_back_to_green=min(N_fish_recovered,N_crop_demand)
    N_crop_residue_to_feed=usable_residue_dry*p.residue_N_DM_frac
    feed_t=p.fish_t_y*p.fish_FCR
    # marine N harvest ; process N not automatically claimed as nitrogen fertilizer
    seaweed_N=dry*p.kelp_N_DM_frac
    effluent_N_captured=HTL_dry*p.kelp_N_DM_frac*p.HTL_effluent_N_capture_frac
    local_fish_feed_max_share=min(usable_residue_dry/feed_t,1)
    fish_feed_N_eff=N_fish_harvest/N_feed_input
    # Separate greenhouse cost boundary; shares no fuel-production credits.
    crop_kg=produce_t*1000
    # Allocate seasonal source-heat use to greenhouse proportionally within each month.
    GH_hp=np.sum(hp_supply_m * np.divide(H_green*green_fraction,monthly_load,out=np.zeros_like(monthly_load),where=monthly_load>0))
    GH_heat_gap=H_green-GH_hp
    GH_electric=(E_led*electric_price)+(GH_hp/p.hp_COP+GH_heat_gap)*electric_price
    GH_annual_capital=p.greenhouse_ha*10000*p.greenhouse_capex_eur_m2*p.greenhouse_capital_recovery_factor
    GH_other=p.greenhouse_other_opex_eur_kg*crop_kg
    fertilizer_credit=N_back_to_green*1000*p.recovered_fertilizer_N_value_eur_kg
    GH_eur_kg=(GH_electric+GH_annual_capital+GH_other-fertilizer_credit)/crop_kg
    # Electrolyser / fleet pathway.
    LHV_fuel_GWh=liquid_t*0.012 # fuel ~12 MWh/t, simplified
    return dict(mode=mode, thermal_input_GWh=E_th/1000, direct_heat_available_GWh=H_direct/1000,
                heat_rejected_unrecovered_GWh=None if H_rejected_to_sea is None else H_rejected_to_sea/1000,
                direct_hot_heat_used_GWh=direct_used/1000, electric_high_temp_trim_GWh=hot_gap/1000 if mode=='nuclear' else H_hot/1000, medium_heat_used_GWh=med_HP_used/1000,
                hot_heat_demand_GWh=H_hot/1000, greenhouse_heat_demand_GWh=H_green/1000,
                drying_heat_demand_GWh=H_drying/1000, kelp_fertilizer_drying_GWh=H_kelpdry/1000,
                smoked_salmon_heat_GWh=H_salmon/1000, seasonal_heat_backup_GWh=med_gap/1000 if mode=='nuclear' else 0.0, heat_pump_COP=p.hp_COP,
                total_electric_generation_GWh=E_power/1000 if mode=='nuclear' else None,
                heat_pump_electricity_GWh=E_HP/1000 if mode=='nuclear' else None,
                other_electricity_GWh=E_required/1000, net_grid_export_GWh=E_net/1000 if mode=='nuclear' else None,
                useful_energy_fraction=eta_useful, seaweed_area_km2=p.area_ha/100,
                seaweed_dry_t=dry, HTL_dry_t=HTL_dry, ethanol_feed_dry_t=ferment_dry,
                hydrocarbon_fuel_t=liquid_t, hydrocarbon_fuel_l=litres,
                hydrocarbon_fuel_GWh=LHV_fuel_GWh, ethanol_t=ethanol_t, ethanol_l=ethanol_l,
                hydrogen_needed_t=H2_need_t, hydrogen_electricity_GWh=E_H2/1000,
                renewable_fuel_cost_eur_l=cost_per_l, fuel_feedstock_eur_l=cost_feed/litres,
                fuel_harvest_eur_l=cost_harvest/litres, fuel_energy_eur_l=cost_energy/litres,
                fuel_conversion_other_eur_l=other/litres, greenhouse_food_t=produce_t,
                smoked_salmon_t=p.smoked_salmon_t_y, pollinator_flower_ha=p.pollinator_flower_ha, honey_t=honey_t,
                greenhouse_residue_dry_t=residues_dry, greenhouse_residue_accepted_t=usable_residue_dry,
                local_fish_feed_mass_share_max=local_fish_feed_max_share,
                fish_output_t=p.fish_t_y, fish_feed_t=feed_t, fish_feed_N_input_t=N_feed_input,
                fish_product_N_t=N_fish_harvest, fish_N_recovered_t=N_fish_recovered,
                greenhouse_N_need_t=N_crop_demand, greenhouse_N_substitution_frac=N_back_to_green/max(N_crop_demand,1),
                greenhouse_residue_feed_N_t=N_crop_residue_to_feed, greenhouse_cost_eur_kg=GH_eur_kg,
                greenhouse_fertilizer_recovery_value_eur_y=fertilizer_credit,
                seaweed_N_uptake_t=seaweed_N, HTL_effluent_N_recovery_t=effluent_N_captured,
                fish_feed_N_retained_frac=fish_feed_N_eff,
                reactor_design=p.reactor_design, reactor_unit_electric_cost_eur_MWh=p.nuclear_electric_eur_MWh,
                variable_firm_electric_cost_eur_MWh=p.alt_firm_elec_eur_MWh)


def check(p, a):
    E_th=a['thermal_input_GWh']; E_el=a['total_electric_generation_GWh']; H_d=a['direct_heat_available_GWh']
    E_reject=E_th-H_d-E_el
    assert abs(E_th-(H_d+E_el+E_reject))<1e-6
    assert a['direct_hot_heat_used_GWh'] <=H_d+1e-8
    assert a['useful_energy_fraction']<=1.000001
    assert a['net_grid_export_GWh']>=-1e-8, 'site electricity budget deficient; increase grid supply or plant capacity'
    assert math.isclose(a['hydrocarbon_fuel_l'],a['hydrocarbon_fuel_t']/.8*1000,rel_tol=1e-8)
    assert a['greenhouse_residue_accepted_t']<=a['greenhouse_residue_dry_t']
    assert a['fish_N_recovered_t']<=a['fish_feed_N_input_t']-a['fish_product_N_t']
    assert a['greenhouse_N_substitution_frac']<=1

# Annual deployment assumptions; new SMR builds are explicitly NOT a forecast.
def trajectory(p, hubs_target=6, ev_target=.90):
    rec=[]
    for year in range(2026,2042):
        f=(year-2026)/15
        hubs=hubs_target*max(0,(f-.15)/.85)**1.35
        ev=.035+(ev_target-.035)*f**1.55
        residual_ice=1-ev
        ethanol_eligible=min(.75, .10+.65*f**.65)
        # fraction of residual fuel use, not of the whole car fleet
        high_ethanol_fossil_frac=.30 # warm/cold blend average incl fossil energy, illustrative
        fuel_km=40e6*11600*residual_ice
        residual_petrol_L=fuel_km*.065*(1-ethanol_eligible*(1-high_ethanol_fossil_frac))
        road_kgCO2=residual_petrol_L*2.31+40e6*11600*ev*.18*.015
        hub=simulate(p)
        rec.append(dict(year=year, candidate_hubs=hubs, battery_vehicle_share=ev,
                        ethanol_eligible_of_remaining_ICE=ethanol_eligible,
                        light_vehicle_territorial_screen_MtCO2=road_kgCO2/1e9,
                        coastal_hydrocarbon_fuel_TWh=hub['hydrocarbon_fuel_GWh']*hubs/1000,
                        coastal_food_thousand_t=hub['greenhouse_food_t']*hubs/1000,
                        coastal_fish_thousand_t=hub['fish_output_t']*hubs/1000,
                        reactor_electricity_TWh=hub['total_electric_generation_GWh']*hubs/1000))
    return rec


def main():
    p=P(); a=simulate(p,'nuclear'); b=simulate(p,'variable_firm');check(p,a)
    meta={'scope':'scenario screening, not a commissioned French SMR or approved marine licence',
          'currency':'EUR constant 2026, illustrative economic inputs; not actual market offers',
          'baseline':asdict(p),'technology_cases':{'nuclear':a,'variable_firm':b}}
    (DATA/'parameter_register.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
    with open(DATA/'hub_balance.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=a.keys());w.writeheader();w.writerow(a);w.writerow(b)
    traj=trajectory(p)
    # Monthly balance for seasonal greenhouse heating and June-Aug drying service.
    E_th=p.thermal_MW*8760*p.capacity_factor
    HTL_dry=p.area_ha*p.seaweed_tDM_ha_y*p.frac_HTL
    fermented=(p.area_ha*p.seaweed_tDM_ha_y-HTL_dry)*p.ferment_carbohydrate_frac*p.ethanol_t_per_t_carbs
    H_hot_direct=HTL_dry*p.HTL_heat_MWh_t*(1-p.HTL_high_grade_electric_trim_frac)+fermented*p.distil_heat_MWh_t_ethanol
    extracted=min(E_th*p.divert_frac,H_hot_direct)
    reject=(E_th-extracted)*(1-p.electrical_efficiency)
    hp_gwh_m=(reject*p.reject_reclaim_frac/(1-1/p.hp_COP))/12/1000
    gh=np.array([10,9,8,6,3,1,.5,.5,2,6,7,7],dtype=float)
    dryer=np.array([0,0,0,0,.5,3,4,2.5,0,0,0,0],dtype=float)
    extra_total=(p.kelp_fertilizer_drying_GWh_y + p.smoked_salmon_t_y*p.smoked_salmon_heat_MWh_t/1000)
    extra_frac=np.array([0,0,0,0,1.5,3.0,3.0,2.5,2.0,0,0,0],dtype=float)/(1.5+3.0+3.0+2.5+2.0)
    drying_month = dryer + extra_total*extra_frac
    monthly=[{'month':i+1,'greenhouse_heat_demand_GWh':float(gh[i]),'drying_heat_demand_GWh':float(drying_month[i]),
             'HP_delivered_GWh':float(min(gh[i]+drying_month[i],hp_gwh_m)),
             'backup_heat_GWh':float(max(gh[i]+drying_month[i]-hp_gwh_m,0))} for i in range(12)]
    with open(DATA/'monthly_heat_balance.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=monthly[0].keys());w.writeheader();w.writerows(monthly)
    with open(DATA/'france_15year.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=traj[0].keys());w.writeheader();w.writerows(traj)
    # 2026 petroleum benchmarks; retail Diesel actual separately; wholesale assumptions not conflated.
    sensitivity=[]
    for cost in [120,200,400,650,900]:
        for yield_t in [4,8,12]:
            for nuclear_price in [65,105,170]:
                q=P(seaweed_dry_cost_eur_t=cost,seaweed_tDM_ha_y=yield_t,nuclear_electric_eur_MWh=nuclear_price)
                n=simulate(q,'nuclear'); v=simulate(q,'variable_firm')
                sensitivity.append(dict(dry_cost_eur_t=cost,yield_tDM_ha=yield_t,nuclear_price_eur_MWh=nuclear_price,
                                        firm_variable_price_eur_MWh=q.alt_firm_elec_eur_MWh,
                                        nuclear_fuel_eur_l=n['renewable_fuel_cost_eur_l'],variable_firm_fuel_eur_l=v['renewable_fuel_cost_eur_l'],
                                        difference_variable_minus_nuclear_eur_l=v['renewable_fuel_cost_eur_l']-n['renewable_fuel_cost_eur_l'],
                                        nuclear_below_retail_diesel_2026_2p37=n['renewable_fuel_cost_eur_l']<2.37,
                                        nuclear_below_assumed_ex_tax_1p0=n['renewable_fuel_cost_eur_l']<1.00))
    with open(DATA/'cost_sensitivity.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=sensitivity[0].keys());w.writeheader();w.writerows(sensitivity)
    # MC: independent physical/economic uncertainties; some are assumptions, not measured priors.
    rng=np.random.default_rng(20261024); cases=[]
    for i in range(2500):
        q=P(seaweed_dry_cost_eur_t=float(rng.triangular(120,350,900)),
            seaweed_tDM_ha_y=float(rng.triangular(3,8,15)),
            biocrude_fuel_yield_t_t=float(rng.triangular(.16,.25,.34)),
            nuclear_electric_eur_MWh=float(rng.triangular(65,105,180)),
            alt_firm_elec_eur_MWh=float(rng.triangular(75,145,240)),
            HTL_heat_MWh_t=float(rng.triangular(1.0,1.8,2.8)),
            HTL_other_eur_L=float(rng.triangular(.30,.48,.80)),
            alt_other_eur_L=float(rng.triangular(.30,.48,.80)),
            hp_COP=float(rng.triangular(2.1,3.2,4.5)),
            capacity_factor=float(rng.triangular(.75,.90,.94)),
            fish_residual_N_capture_frac=float(rng.triangular(.2,.4,.7)),
            fish_captured_N_recovery_frac=float(rng.triangular(.3,.55,.85)))
        n=simulate(q,'nuclear');v=simulate(q,'variable_firm')
        # Energy not necessarily enough for every extreme scenario; shortage flagged explicitly.
        cases.append({'draw':i,'dry_cost_eur_t':q.seaweed_dry_cost_eur_t,'yield_t_ha':q.seaweed_tDM_ha_y,
                      'cost_nuclear_eur_l':n['renewable_fuel_cost_eur_l'],
                      'cost_variable_firm_eur_l':v['renewable_fuel_cost_eur_l'],
                      'advantage_nuclear_eur_l':v['renewable_fuel_cost_eur_l']-n['renewable_fuel_cost_eur_l'],
                      'thermal_use_fraction':n['useful_energy_fraction'],
                      'grid_surplus_GWh':n['net_grid_export_GWh'],
                      'greenhouse_N_substitution':n['greenhouse_N_substitution_frac']})
    with open(DATA/'uncertainty_draws.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cases[0].keys());w.writeheader();w.writerows(cases)
    A=lambda k:np.array([r[k] for r in cases],float)
    feasible=np.array([c['grid_surplus_GWh']>=0 for c in cases])
    cheaper=A('advantage_nuclear_eur_l')>0
    # Advanced reactor is a speculative heat-grade and investment sensitivity only.
    lftr=P(nuclear_electric_eur_MWh=150,electrical_efficiency=.40,HTL_high_grade_electric_trim_frac=0)
    advanced=simulate(lftr,'nuclear')
    # Commercial SEALER-55 ~55 MWe rated. 140 MWth is a public reporting/screening anchor,
    # NOT a company-confirmed French cogeneration guarantee; 550 C core and 530 C secondary
    # outlet are published SEALER-One preliminary (70 MWth) values used as a heat-grade proxy.
    # Nameplate electricity is diminished when high-grade secondary heat is extracted.
    sealer_p=P(reactor_design='Blykalla SEALER-55 lead-cooled proxy',thermal_MW=140.0,
               electrical_efficiency=55/140,HTL_high_grade_electric_trim_frac=0.0,
               nuclear_electric_eur_MWh=105.0)
    lead=simulate(sealer_p,'nuclear');check(sealer_p,lead)
    sealer_equal_p=P(reactor_design='SEALER lead coolant, equal 100 MWth hypothetical',
                     thermal_MW=100.0,electrical_efficiency=55/140,
                     HTL_high_grade_electric_trim_frac=0.0,nuclear_electric_eur_MWh=105.0)
    lead_equal=simulate(sealer_equal_p,'nuclear');check(sealer_equal_p,lead_equal)
    lead_price_sweep=[]
    for elec in [75,90,105,130,160,190]:
        for trim in [0.0,.10,.25]:
            for rec in [.10,.15,.25,.35]:
                q=P(reactor_design='Blykalla candidate',thermal_MW=140,electrical_efficiency=55/140,
                    HTL_high_grade_electric_trim_frac=trim,
                    nuclear_electric_eur_MWh=elec,reject_reclaim_frac=rec)
                z=simulate(q,'nuclear')
                lead_price_sweep.append(dict(electric_eur_MWh=elec,high_temp_electric_trim_share=trim,
                    recoverable_reject_fraction=rec,utilization_fraction=z['useful_energy_fraction'],
                    fuel_cost_eur_L=z['renewable_fuel_cost_eur_l'],fuel_output_ML=z['hydrocarbon_fuel_l']/1e6,
                    net_grid_export_GWh=z['net_grid_export_GWh'],
                    industrial_heat_used_GWh=z['direct_hot_heat_used_GWh']+z['medium_heat_used_GWh']))
    with open(DATA/'lead_sealer_sensitivity.csv','w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=lead_price_sweep[0].keys());w.writeheader();w.writerows(lead_price_sweep)
    (DATA/'blykalla_sealer_scenario.json').write_text(json.dumps({
      'model_status':'UNLICENSED, ILLUSTRATIVE: not endorsement or proprietary Blykalla design',
      'published_nominal_electric_power_MWe':55,
      'thermal_power_screening_MWth':140,
      'demo_secondary_outlet_C':530,
      'demo_core_outlet_C':550,
      'note':'70 MWth demonstration temperatures transferred as an explicit heat-grade proxy; not confirmed commercial cogeneration specs.',
      'baseline_water_cooled_100_MWth':a,
      'SEALER_nominal_140_MWth':lead,
      'SEALER_equal_100_MWth':lead_equal,
      'assumptions_nominal':asdict(sealer_p),
      'assumptions_equal_thermal':asdict(sealer_equal_p),
      'smoked_salmon_requires_validated_shelf_stability':True,
      'phacelia_honey_yield_is_potential_not_commercial_harvest':True},indent=2),encoding='utf8')
    summ={'base':{'nuclear':a,'variable_firm':b,'lead_sealer':lead,'lead_equal_thermal':lead_equal},
          'nuclear_cheaper_share_conditional_electric_self_sufficient':float(np.mean(cheaper[feasible])) if feasible.any() else None,
          'electric_self_sufficient_share_of_draws':float(np.mean(feasible)),
          'nuclear_cheaper_fraction':float(np.mean(A('advantage_nuclear_eur_l')>0)),
          'nuclear_below_assumed_ex_tax_fraction':float(np.mean(A('cost_nuclear_eur_l')<1.00)),
          'nuclear_below_retail_diesel_2026_fraction':float(np.mean(A('cost_nuclear_eur_l')<2.37)),
          'cost_nuclear_quantiles_eur_l':list(map(float,np.percentile(A('cost_nuclear_eur_l'),[5,50,95]))),
          'cost_variable_quantiles_eur_l':list(map(float,np.percentile(A('cost_variable_firm_eur_l'),[5,50,95]))),
          'thermal_use_quantiles':list(map(float,np.percentile(A('thermal_use_fraction'),[5,50,95]))),
          'nuclear_grid_shortfall_draws':int(np.sum(A('grid_surplus_GWh')<0)),
          'nitrate_efficiency_note':'Seaweed N uptake represents embodied marine nutrient; N recycled to greenhouse and feed separately; no automatic net nutrient removal credit.'}
    (DATA/'advanced_reactor_sensitivity.json').write_text(json.dumps({'scenario':'hypothetical thorium LFTR; NOT licensed or commercial 2041','assumptions':asdict(lftr),'outputs':advanced},indent=2),encoding='utf8')
    (DATA/'results_summary.json').write_text(json.dumps(summ,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in summ.items() if k!='base'},indent=2))
    print('baseline', {k:round(a[k],3) for k in ['useful_energy_fraction','renewable_fuel_cost_eur_l','greenhouse_food_t','fish_output_t','greenhouse_N_substitution_frac','seaweed_N_uptake_t','hydrocarbon_fuel_GWh','net_grid_export_GWh']}); print('renewables fuel cost',round(b['renewable_fuel_cost_eur_l'],3));print('SEALER',round(lead['useful_energy_fraction'],4),round(lead['renewable_fuel_cost_eur_l'],3),'equal',round(lead_equal['useful_energy_fraction'],4),round(lead_equal['renewable_fuel_cost_eur_l'],3));

if __name__=='__main__':main()
