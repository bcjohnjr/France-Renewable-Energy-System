"""Consistency tests for the Grid Harvester engineering calculation and turn-loss geometry (V20)."""
import sys, json, math
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_harvester_engineering as E
import system_v14 as S

ROOT = Path(__file__).resolve().parent
OK = []
def ok(name, cond):
    OK.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name)

R = E.main(); c = R['cases']['central']; g = E.GH()
ok('throughput derived from head width x speed x crop equals the system-model input (416.7 t/h)', abs(c['throughput_t_h'] - S.Sys().harvester_t_wet_h) < 0.1)
ok('hose velocity at the 10% slurry design is 1.0 m/s (+/-2%)', abs(c['hose_velocity_m_s'] - 1.0) < 0.02)
ok('hose flow is turbulent and friction factor in the smooth-pipe range', c['reynolds'] > 1e5 and 0.007 < c['friction_factor'] < 0.02)
ok('pump energy = rho g Q H / eta x cycle time', abs(c['E_pump_MJ'] - E.RHO * E.G * c['hose_flow_m3_s'] * c['pump_head_m'] / g.eta_pump * c['cycle_s'] / 1e6) < 1e-9)
ok('grid energy is the sum of its parts', abs(c['E_grid_MJ'] - (c['E_pump_MJ'] + c['E_head_MJ'] + c['E_hose_form_MJ'] + c['E_hose_skin_MJ'])) < 1e-9)
ok('conventional vessel at C_DA 30 m2 needs 90.9 MJ per 1.44-ha cycle (Spanish study)', abs(c['E_conv_MJ'] - 90.9) < 0.5)
ok('central energy ratio within 5% of the Spanish study (2.68)', abs(c['ratio'] / 2.68 - 1) < 0.05)
ok('ratio falls as the conventional vessel becomes more streamlined', R['cases']['central']['ratio'] > R['cases']['conv_cda_20']['ratio'] > R['cases']['conv_cda_10']['ratio'])
ok('ratio rises with slurry concentration', R['cases']['slurry_5pct']['ratio'] < c['ratio'] < R['cases']['slurry_20pct']['ratio'])
ok('a bare hose and a pulp-like slurry each cost energy', R['cases']['bare_hose']['E_grid_MJ'] > c['E_grid_MJ'] and R['cases']['bingham_slurry']['E_grid_MJ'] > c['E_grid_MJ'])
ok('worst combined case loses the energy advantage (ratio < 1)', R['cases']['worst_combined']['ratio'] < 1)
ok('harvesting-energy saving is below 1 kWh per dry tonne', 0 < c['saved_kWh_per_dry_t'] < 1)
ok('head hydraulics save under 1% of fleet fuel, far below the 16.1% fleet saving assumed', c['share_of_fleet_fuel'] < 0.01 < S.Sys().harvester_fuel_saving)
ok('removing the assumed fleet saving raises fuel cost by under 1 cent per litre', 0 < R['fuel_cost_hybrid_no_fleet_saving'] - R['fuel_cost_hybrid_central'] < 0.01)
ok('one harvester-year (2,400 h) handles 1.0 Mt wet', abs(c['annual_wet_Mt'] - 1.0) < 0.01)
T = json.loads((ROOT / 'v19_grid_harvester_turns.json').read_text())
ok('turn losses: conventional 1.5%, forward 2.5%, in place 0.6%', [round(T['conventional']['missed_pct'], 1), round(T['grid']['forward']['missed_pct'], 1), round(T['grid']['in_place']['missed_pct'], 1)] == [1.5, 2.5, 0.6])
ok('turning in place misses (2 - pi/2) R^2 per turn', abs(T['grid']['in_place']['missed_m2'] - T['grid']['turns'] * (2 - math.pi / 2) * 9) < 1e-9)
print(f'{sum(OK)}/{len(OK)} checks passed')
