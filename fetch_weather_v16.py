"""Download and process real hourly wind and solar data for the six French hubs (ERA5 reanalysis via Open-Meteo).

WHY: the hub model assumes offshore capacity factors (45 % fixed-bottom, 40 % floating) and a flat EUR 20/MWh charge for
firming wind power to the hubs' round-the-clock process loads. This script replaces those assumptions with site data:
  * hourly 100 m wind speed -> 150 m hub height -> 15 MW turbine power curve -> capacity factor, by site, year and month;
  * how much of each hub's flat process-electricity load the co-located array covers hour by hour, the residual that
    must be bought, the longest low-wind spell, and the firming cost that residual implies;
  * solar yield (kWh per kWp) for the drones' and the Grid Harvester's photovoltaic panels.

HOW TO RUN (Python >= 3.9, standard library only, internet access; ~6 sites x 10 years = 60 small requests, 2-5 min):
    python fetch_weather_v16.py                       # 2015-2024, writes ./weather_v16/
    python fetch_weather_v16.py --start 2005 --end 2024 --out weather_v16
    python fetch_weather_v16.py --offline             # re-process the cached downloads only
    python fetch_weather_v16.py --selftest            # synthetic data, no internet: checks the processing chain
Run it from the repository root if you can: it then reads each hub's process load from data/v14_system_results.json.
Send back the whole output folder (or just weather_v16/weather_summary_v16.json and the CSV files).

DATA SOURCE AND LICENCE: ERA5 hourly reanalysis (Copernicus Climate Change Service, ECMWF), served by the Open-Meteo
Historical Weather API (https://open-meteo.com/en/docs/historical-weather-api), CC BY 4.0. Cite: Hersbach et al. (2020),
The ERA5 global reanalysis, Q. J. R. Meteorol. Soc. 146, 1999-2049, and Open-Meteo. The free API is for non-commercial use.

CAVEATS: ERA5 is a ~31 km reanalysis; it smooths coastal gradients and slightly under-states offshore extremes. The power
curve is a generic cubic ramp fitted to the IEA 15 MW reference turbine (cut-in 3 m/s, rated 10.59 m/s, cut-out 25 m/s);
wake, electrical and availability losses are a single factor. Coordinates are approximate points in or near the French
offshore wind zones closest to each hub, not project coordinates.
"""
import argparse, csv, gzip, json, math, os, random, statistics, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

SITES = {  # key: (name, lat, lon, foundation, zone used)
    'DKQ': ('Dunkerque', 51.10, 2.23, 'fixed-bottom', 'Dunkerque offshore wind zone'),
    'LEH': ('Le Havre', 49.90, 0.00, 'fixed-bottom', 'between Fécamp and Centre Manche zones'),
    'BRE': ('Brest', 48.30, -5.00, 'floating', 'Mer d’Iroise, west of Brest'),
    'STN': ('Saint-Nazaire', 47.15, -2.60, 'fixed-bottom', 'Saint-Nazaire (Banc de Guérande) zone'),
    'LRO': ('La Rochelle', 45.95, -1.75, 'fixed-bottom', 'Oléron (AO7) zone'),
    'FOS': ('Fos-sur-Mer', 43.20, 4.75, 'floating', 'Golfe du Lion, Provence Grand Large area'),
}
MODEL_CF = {'fixed-bottom': 0.45, 'floating': 0.40}           # what the V14-V15 model assumes
MODEL_PRICE = {'DKQ': 66, 'LEH': 66, 'BRE': 100, 'STN': 75, 'LRO': 85, 'FOS': 100}
API = 'https://archive-api.open-meteo.com/v1/archive'
VARS = 'wind_speed_100m,wind_direction_100m,shortwave_radiation,temperature_2m'


# ------------------------------------------------------------------------------------------------ download
def fetch_year(key, lat, lon, year, raw, retries=5):
    f = raw / f'{key}_{year}.json'
    if f.exists() and f.stat().st_size > 1000:
        return json.loads(f.read_text())
    q = urllib.parse.urlencode(dict(latitude=lat, longitude=lon, start_date=f'{year}-01-01', end_date=f'{year}-12-31',
                                    hourly=VARS, wind_speed_unit='ms', timezone='UTC', models='era5'))
    for k in range(retries):
        try:
            with urllib.request.urlopen(f'{API}?{q}', timeout=120) as r:
                d = json.loads(r.read().decode())
            if 'hourly' not in d: raise ValueError(d.get('reason', 'no hourly data'))
            f.write_text(json.dumps(d)); time.sleep(1.0)
            return d
        except (urllib.error.URLError, ValueError, TimeoutError) as ex:
            wait = 5 * 2 ** k
            print(f'  {key} {year}: {ex}; retry in {wait}s', flush=True); time.sleep(wait)
    raise SystemExit(f'Download failed for {key} {year}. Re-run later; finished years are cached in {raw}.')


# ------------------------------------------------------------------------------------------------ physics
def power_cf(v, cut_in=3.0, rated=10.59, cut_out=25.0):
    if v < cut_in or v >= cut_out: return 0.0
    if v >= rated: return 1.0
    return (v ** 3 - cut_in ** 3) / (rated ** 3 - cut_in ** 3)


def pv_kwh_per_kwp(ghi, t_air, pr=0.80, gamma=-0.004, noct_rise=20.0):
    """One hour of PV output per kWp (horizontal-plane GHI, simple cell-temperature derating)."""
    if ghi <= 0: return 0.0
    t_cell = t_air + ghi / 800.0 * noct_rise
    return ghi / 1000.0 * pr * (1 + gamma * (t_cell - 25.0))


def hub_loads(path='data/v14_system_results.json'):
    """Process-electricity load (MW, flat) and array size of each combined hub, from the model if available."""
    out = {}
    try:
        d = json.loads(Path(path).read_text())
        for k in SITES:
            r = d['sites'][f'{k}|hybrid_d']
            out[k] = dict(load_MW=r['process_elec_GWh'] * 1000 / 8760, array_MW=r['wind_MW'], source=path)
    except (OSError, KeyError, json.JSONDecodeError):
        for k in SITES: out[k] = dict(load_MW=25.0, array_MW=375.0, source='default (model results not found)')
    return out


def analyse(key, years_data, args, load):
    name, lat, lon, ftype, zone = SITES[key]
    shear = (args.hub_height / 100.0) ** args.alpha
    hourly = []                        # (timestamp, ws_hub, cf_net, pv_kWh_per_kWp)
    for d in years_data:
        h = d['hourly']
        for t, ws, ghi, ta in zip(h['time'], h['wind_speed_100m'], h['shortwave_radiation'], h['temperature_2m']):
            if ws is None: continue
            v = ws * shear
            hourly.append((t, v, power_cf(v) * (1 - args.loss), pv_kwh_per_kwp(ghi or 0.0, ta if ta is not None else 12.0)))
    if not hourly: raise SystemExit(f'No data for {key}')
    by_year, by_month = {}, {m: [] for m in range(1, 13)}
    for t, v, cf, pv in hourly:
        by_year.setdefault(int(t[:4]), []).append((v, cf, pv)); by_month[int(t[5:7])].append((cf, pv))
    cf_all = [x[2] for x in hourly]
    # hub coverage: flat process load vs array output
    arr = load['array_MW']; L = load['load_MW']
    gen = [cf * arr for cf in cf_all]
    short = [max(0.0, L - g) for g in gen]
    residual_share = sum(short) / (L * len(gen))
    hours_short = sum(1 for s in short if s > 0) / len(gen)
    longest = run = 0
    for s in short:
        run = run + 1 if s > 0.5 * L else 0; longest = max(longest, run)
    # firming implied by the residual: buy the shortfall at the backup price instead of the contract price
    firm = residual_share * (args.backup_price - MODEL_PRICE[key])
    # a 'flat block' for the whole hub load requires firming of the residual only; the surplus is sold by the array owner
    pv_year = statistics.mean(sum(x[2] for x in ys) for ys in by_year.values())
    pv_month = {m: sum(x[1] for x in v) / (len(v) / 24) for m, v in by_month.items()}           # kWh per kWp per day
    worst_month = min(pv_month, key=pv_month.get)
    return dict(key=key, site=name, lat=lat, lon=lon, foundation=ftype, zone=zone, years=sorted(by_year), hours=len(hourly),
                mean_ws_100m=statistics.mean(x[1] for x in hourly) / shear, mean_ws_hub=statistics.mean(x[1] for x in hourly),
                cf_net=statistics.mean(cf_all), cf_model=MODEL_CF[ftype],
                cf_by_year={y: statistics.mean(x[1] for x in v) for y, v in by_year.items()},
                cf_by_month={m: statistics.mean(x[0] for x in v) for m, v in by_month.items()},
                cf_p10_year=sorted(statistics.mean(x[1] for x in v) for v in by_year.values())[max(0, len(by_year) // 10 - 1)],
                hub_load_MW=L, array_MW=arr, load_source=load['source'],
                residual_share_of_load=residual_share, hours_below_load_share=hours_short, longest_spell_below_half_load_h=longest,
                implied_firming_eur_per_MWh_load=firm, model_firming_eur_MWh=20.0,
                pv_kWh_per_kWp_year=pv_year, pv_kWh_per_kWp_day_by_month=pv_month, pv_worst_month=worst_month,
                drone_pv_Wp_for_0p4kWh_day_worst_month=400.0 / pv_month[worst_month] * 1.0), hourly


def write_outputs(out, results, hourlies):
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'cf_by_site_year_v16.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['site', 'year', 'capacity_factor_net'])
        for r in results:
            for y, v in r['cf_by_year'].items(): w.writerow([r['key'], y, f'{v:.5f}'])
    with open(out / 'cf_and_pv_by_site_month_v16.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['site', 'month', 'capacity_factor_net', 'pv_kWh_per_kWp_day'])
        for r in results:
            for m in range(1, 13): w.writerow([r['key'], m, f"{r['cf_by_month'][m]:.5f}", f"{r['pv_kWh_per_kWp_day_by_month'][m]:.4f}"])
    for k, hh in hourlies.items():
        with gzip.open(out / f'hourly_{k}_v16.csv.gz', 'wt', newline='') as f:
            w = csv.writer(f); w.writerow(['time_utc', 'wind_speed_hub_ms', 'capacity_factor_net', 'pv_kWh_per_kWp'])
            for t, v, cf, pv in hh: w.writerow([t, f'{v:.2f}', f'{cf:.4f}', f'{pv:.4f}'])
    (out / 'weather_summary_v16.json').write_text(json.dumps(dict(results=results, generated=time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())), indent=1, default=str))


def synthetic_year(key, year):
    rnd = random.Random(hash((key, year)) & 0xffffffff); n = 8760
    t = [f'{year}-{1 + i // 730:02d}-{1 + (i % 730) // 24:02d}T{i % 24:02d}:00' for i in range(n)]
    ws, x = [], 9.0
    for i in range(n):
        x = 0.97 * x + 0.03 * (9.5 + 2.5 * math.cos(2 * math.pi * i / n)) + rnd.gauss(0, 0.6); ws.append(max(0.0, x))
    ghi = [max(0.0, 600 * math.sin(math.pi * ((i % 24) - 6) / 12)) * (0.6 + 0.4 * math.sin(math.pi * i / n)) for i in range(n)]
    return dict(hourly=dict(time=t, wind_speed_100m=ws, shortwave_radiation=ghi, temperature_2m=[12.0] * n))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--start', type=int, default=2015); ap.add_argument('--end', type=int, default=2024)
    ap.add_argument('--out', default='weather_v16'); ap.add_argument('--hub-height', type=float, default=150.0)
    ap.add_argument('--alpha', type=float, default=0.11, help='offshore wind-shear exponent (100 m -> hub height)')
    ap.add_argument('--loss', type=float, default=0.12, help='wake + electrical + availability losses')
    ap.add_argument('--backup-price', type=float, default=130.0, help='EUR/MWh paid for the hub load the array cannot cover')
    ap.add_argument('--offline', action='store_true'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    out = Path(a.out); raw = out / 'raw'; raw.mkdir(parents=True, exist_ok=True)
    loads = hub_loads(); results, hourlies = [], {}
    for k, (name, lat, lon, ftype, zone) in SITES.items():
        print(f'{k} {name} ({lat}, {lon}) ...', flush=True)
        yd = []
        for y in range(a.start, a.end + 1):
            if a.selftest: yd.append(synthetic_year(k, y))
            elif a.offline:
                f = raw / f'{k}_{y}.json'
                if f.exists(): yd.append(json.loads(f.read_text()))
            else: yd.append(fetch_year(k, lat, lon, y, raw))
        r, hh = analyse(k, yd, a, loads[k]); results.append(r); hourlies[k] = hh
        print(f"   CF {r['cf_net']:.3f} (model {r['cf_model']:.2f}); load covered {1 - r['residual_share_of_load']:.1%}; "
              f"implied firming {r['implied_firming_eur_per_MWh_load']:.1f} EUR/MWh (model 20); PV {r['pv_kWh_per_kWp_year']:.0f} kWh/kWp", flush=True)
    write_outputs(out, results, hourlies)
    print(f'\nWritten to {out.resolve()}  ({"SYNTHETIC self-test data - not real" if a.selftest else "ERA5 via Open-Meteo, CC BY 4.0"})')


if __name__ == '__main__':
    main()
