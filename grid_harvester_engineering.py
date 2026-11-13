"""Grid Harvester engineering calculation (Supplementary Note S9, Table S17).

First-principles screening of the quantities the system model takes as inputs:
  throughput   m = W_head x V x sigma                 (head width, speed, wet standing crop removed per pass)
  hose flow    Q = m / (c rho),  v = 4Q / (pi D^2)       (c = wet-kelp mass fraction of the slurry)
  pump head    H = H_static + (K + f L/D) v^2/2g (+ 4 tau_y L/(D rho g) for a Bingham slurry), f from Swamee-Jain
  pump energy  E_pump = rho g Q H / eta_pump x t_cycle
  drag energy  E = F x path / eta_prop for the head and hose (hose speed rising linearly from 0 at the swivel to V at
               the head, so the mean v^2 is V^2/3; only a fraction chi of the hose length is in cross-flow) and for a
               conventional vessel of resistance area C_D A harvesting the same 1.44-ha cycle.
All parameters are design assumptions taken from, or consistent with, the companion Spanish study; the calculation
checks internal consistency and shows how the energy advantage depends on them. It is not a validated design.
"""
import sys, json, math
from dataclasses import dataclass, asdict, replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
RHO, G, MU_W = 1025.0, 9.81, 0.0012
KN = 0.514444


@dataclass
class GH:
    head_m: float = 6.0             # harvesting-head width
    span_m: float = 100.0           # cross-track sweep
    speed_kn: float = 3.0           # head speed through the crop
    crop_kg_m2: float = 12.5        # wet kelp removed per pass (partial harvest above the meristem)
    cycle_m2: float = 14_400.0      # 1.44-ha harvest cycle
    dry_matter: float = 0.13
    slurry_c: float = 0.10          # wet-kelp mass fraction in the hose
    hose_d_m: float = 1.20
    hose_l_m: float = 51.6
    hose_cd: float = 1.2            # bare cylinder in cross-flow
    hose_fairing: float = 0.85      # form-drag reduction by segmented fairings
    hose_crossflow: float = 0.30    # share of hose length in cross-flow (rest trails nearly aligned)
    hose_cf: float = 0.003          # skin-friction coefficient
    static_m: float = 0.50
    minor_k: float = 4.0
    eta_pump: float = 0.72
    head_cda_m2: float = 2.0        # drag area of the submerged head and its buoyancy/RCS pods
    eta_prop: float = 0.58          # propulsive efficiency (thrusters and vessel)
    conv_cda_m2: float = 30.0       # resistance area of a conventional harvesting vessel (range 10-30)
    conv_width_m: float = 10.0
    rheology: str = 'water'         # 'water' or 'bingham' (pessimistic macerated slurry)
    hours: float = 2400.0           # harvesting hours a year (weather, maintenance)
    fleet_fuel_GJ_t: float = 0.35   # conventional fleet fuel per dry tonne (harvest, transits, support craft)


def swamee_jain(re, d, eps=5e-5):
    return 64 / max(re, 1) if re < 2300 else 0.25 / math.log10(eps / (3.7 * d) + 5.74 / re ** 0.9) ** 2


def run(g: GH = GH()):
    V = g.speed_kn * KN
    m = g.head_m * V * g.crop_kg_m2                     # kg/s wet
    t_cycle = g.cycle_m2 / g.head_m / V                 # s of sweeping per cycle (turns in place excluded)
    path = g.cycle_m2 / g.head_m
    q = m / (g.slurry_c * RHO); v = q / (math.pi * g.hose_d_m ** 2 / 4)
    ds = g.slurry_c * g.dry_matter * 100
    mu, tau = (MU_W, 0.0) if g.rheology == 'water' else (MU_W * (1 + 3 * ds), 2.0 * ds ** 2)
    re = RHO * v * g.hose_d_m / mu; f = swamee_jain(re, g.hose_d_m)
    H = g.static_m + (g.minor_k + f * g.hose_l_m / g.hose_d_m) * v ** 2 / (2 * G) + 4 * tau * g.hose_l_m / (g.hose_d_m * RHO * G)
    p_pump = RHO * G * q * H / g.eta_pump
    E_pump = p_pump * t_cycle / 1e6
    q2 = 0.5 * RHO * V ** 2
    F_head = q2 * g.head_cda_m2
    F_form = q2 / 3 * g.hose_cd * g.hose_d_m * g.hose_l_m * g.hose_crossflow * (1 - g.hose_fairing)
    F_skin = q2 / 3 * g.hose_cf * math.pi * g.hose_d_m * g.hose_l_m
    E_head, E_form, E_skin = (F * path / g.eta_prop / 1e6 for F in (F_head, F_form, F_skin))
    E_grid = E_pump + E_head + E_form + E_skin
    conv_path = g.cycle_m2 / g.conv_width_m
    E_conv = q2 * g.conv_cda_m2 * conv_path / g.eta_prop / 1e6
    wet_cycle = g.crop_kg_m2 * g.cycle_m2 / 1000; dry_cycle = wet_cycle * g.dry_matter
    saved_MJ_dry = (E_conv - E_grid) / dry_cycle
    return dict(speed_m_s=V, throughput_t_h=m * 3.6, annual_wet_Mt=m * 3.6 * g.hours / 1e6, cycle_s=t_cycle,
                hose_flow_m3_s=q, hose_velocity_m_s=v, reynolds=re, friction_factor=f, pump_head_m=H, pump_kW=p_pump / 1000,
                E_pump_MJ=E_pump, E_head_MJ=E_head, E_hose_form_MJ=E_form, E_hose_skin_MJ=E_skin, E_grid_MJ=E_grid,
                E_conv_MJ=E_conv, ratio=E_conv / E_grid, wet_t_cycle=wet_cycle, dry_t_cycle=dry_cycle,
                saved_kWh_per_dry_t=saved_MJ_dry / 3.6, share_of_fleet_fuel=saved_MJ_dry / (g.fleet_fuel_GJ_t * 1000),
                water_t_per_wet_t=(1 - g.slurry_c) / g.slurry_c)


CASES = [
    ('central', {}),
    ('conv_cda_20', dict(conv_cda_m2=20.0)), ('conv_cda_10', dict(conv_cda_m2=10.0)),
    ('bare_hose', dict(hose_fairing=0.0)), ('hose_crossflow_0.6', dict(hose_crossflow=0.6)),
    ('head_cda_4', dict(head_cda_m2=4.0)), ('slurry_5pct', dict(slurry_c=0.05)), ('slurry_20pct', dict(slurry_c=0.20)),
    ('bingham_slurry', dict(rheology='bingham')), ('speed_2kn', dict(speed_kn=2.0)), ('crop_8kg', dict(crop_kg_m2=8.0)),
    ('worst_combined', dict(conv_cda_m2=10.0, hose_fairing=0.0, hose_crossflow=0.6, head_cda_m2=4.0, rheology='bingham')),
]


def main():
    res = dict(assumptions=asdict(GH()), cases={k: run(replace(GH(), **kw)) for k, kw in CASES})
    rs = [r['ratio'] for r in res['cases'].values()]
    res['ratio_range'] = [min(rs), max(rs)]
    # effect of the assumed 16.1% fleet-fuel saving (mostly electrified support craft, not head hydraulics) on fuel cost
    import france_v12 as M, system_v14 as S
    inp = M.Inputs(); fc = {}
    for hs in (S.Sys().harvester_fuel_saving, 0.0):
        rows = [r for r in S.evaluate(inp, replace(S.Sys(), harvester_fuel_saving=hs))['rows'] if r['option'] == 'hybrid' and r['drones']]
        fc[hs] = sum(r['fuel_eur_l'] for r in rows) / len(rows)
    res['fleet_saving_assumed'] = S.Sys().harvester_fuel_saving
    res['fuel_cost_hybrid_central'] = fc[S.Sys().harvester_fuel_saving]; res['fuel_cost_hybrid_no_fleet_saving'] = fc[0.0]
    (ROOT / 'data' / 'v20_grid_harvester_engineering.json').write_text(json.dumps(res, indent=1))
    return res


if __name__ == '__main__':
    R = main(); c = R['cases']['central']
    print(f"throughput {c['throughput_t_h']:.1f} t/h; hose {c['hose_flow_m3_s']:.2f} m3/s at {c['hose_velocity_m_s']:.2f} m/s; head {c['pump_head_m']:.2f} m; pump {c['pump_kW']:.1f} kW")
    print(f"per 1.44-ha cycle: pump {c['E_pump_MJ']:.1f}, head {c['E_head_MJ']:.1f}, hose form {c['E_hose_form_MJ']:.1f}, skin {c['E_hose_skin_MJ']:.1f} -> grid {c['E_grid_MJ']:.1f} MJ; conventional {c['E_conv_MJ']:.1f} MJ; ratio {c['ratio']:.2f}")
    print(f"saving {c['saved_kWh_per_dry_t']:.2f} kWh/dry t = {100 * c['share_of_fleet_fuel']:.2f}% of fleet fuel; fuel cost {R['fuel_cost_hybrid_central']:.4f} vs {R['fuel_cost_hybrid_no_fleet_saving']:.4f} without the fleet saving")
    for k, r in R['cases'].items(): print(f"  {k:20s} ratio {r['ratio']:.2f}  grid {r['E_grid_MJ']:.1f} MJ  conv {r['E_conv_MJ']:.1f} MJ  t/h {r['throughput_t_h']:.0f}")
