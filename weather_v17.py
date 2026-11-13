"""V17: hourly ERA5 wind and solar data (downloaded with fetch_weather_v16.py) turned into a weather-based wind-supply
contract for each hub.

Contract model (per hub, per MWh of the hub's flat electric process load):
  the hub contracts r MW of the co-located array per MW of load and pays the contract price (plus delivery and an hourly
  balancing charge) on all contracted output; each hour it uses min(output, load), sells any surplus back at a surplus value
  (cannibalised capture price) and buys the residual from its backup (reactor electricity for SMR + wind hubs, the grid for
  wind-only hubs). r is chosen to minimise the cost per MWh of load, subject to the array size.
  cost(r) = r*CF*(w + bal) - surplus(r)*v + residual(r)*b,  used(r) = E[min(r*cf_t, 1)].
Solar: worst-month photovoltaic yield sizes each utility drone's panel.
"""
import csv, gzip, json, math
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
W = ROOT
KEYS = ('DKQ', 'LEH', 'BRE', 'STN', 'LRO', 'FOS')
R_GRID = np.concatenate([np.arange(0, 3, 0.01), np.arange(3, 40.01, 0.05)])


def available():
    return all((W / f'hourly_{k}_v16.csv.gz').exists() for k in KEYS)


@lru_cache(maxsize=None)
def hourly(key):
    t, ws, pv = [], [], []
    with gzip.open(W / f'hourly_{key}_v16.csv.gz', 'rt') as f:
        for r in csv.DictReader(f):
            t.append(r['time_utc']); ws.append(float(r['wind_speed_hub_ms'])); pv.append(float(r['pv_kWh_per_kWp']))
    return tuple(t), np.array(ws), np.array(pv)


def power_cf(v, cut_in=3.0, rated=10.59, cut_out=25.0):
    """Generic cubic ramp fitted to the IEA 15 MW reference turbine (as in fetch_weather_v16.py)."""
    v = np.asarray(v, float)
    p = np.where(v >= rated, 1.0, (v ** 3 - cut_in ** 3) / (rated ** 3 - cut_in ** 3))
    return np.where((v < cut_in) | (v >= cut_out), 0.0, p)


@lru_cache(maxsize=24)
def cf_series(key, ws_mult=1.0, loss=0.12):
    _, ws, _ = hourly(key)
    return power_cf(ws * ws_mult) * (1 - loss)


@lru_cache(maxsize=48)
def coverage_table(key, ws_mult=1.0, loss=0.12):
    """used(r), surplus(r) per unit load on R_GRID, from the sorted hourly capacity factors."""
    _, ws, _ = hourly(key)
    cf = np.sort(power_cf(ws * ws_mult) * (1 - loss)); n = len(cf); cs = np.concatenate([[0.0], np.cumsum(cf)])
    mean = cs[-1] / n
    with np.errstate(divide='ignore'):
        k = np.searchsorted(cf, np.where(R_GRID > 0, 1.0 / np.maximum(R_GRID, 1e-12), np.inf))   # hours with r*cf < 1
    used = np.where(R_GRID > 0, (R_GRID * cs[k] + (n - k)) / n, 0.0)
    out = R_GRID * mean
    return mean, used, out - used


def contract(key, w, b, v, rmax, ws_mult=1.0, loss=0.12, bal=0.0):
    """Cheapest supply per MWh of flat load: returns effective price and the hourly balance at the optimum."""
    mean, used, surplus = coverage_table(key, ws_mult, loss)
    ok = R_GRID <= rmax + 1e-12
    cost = R_GRID * mean * (w + bal) - surplus * v + (1 - used) * b
    cost = np.where(ok, cost, np.inf)
    i = int(np.argmin(cost))
    return dict(price=float(cost[i]), r=float(R_GRID[i]), cf=float(mean), used=float(used[i]), surplus=float(surplus[i]),
                residual=float(1 - used[i]), wind_share=float(used[i]), implied_firming=float(cost[i] - w) if used[i] > 0 else 0.0)


def longest_shortfall(key, r, ws_mult=1.0, loss=0.12, frac=0.5):
    """Longest run of hours in which contracted output covers less than `frac` of the load."""
    s = cf_series(key, ws_mult, loss) * r < frac
    best = run = 0
    for x in s:
        run = run + 1 if x else 0
        if run > best: best = run
    return best


@lru_cache(maxsize=None)
def pv_month(key):
    """Mean PV yield, kWh per kWp per day, by calendar month."""
    t, _, pv = hourly(key)
    m = np.array([int(x[5:7]) for x in t]); out = {}
    for mm in range(1, 13):
        sel = m == mm; out[mm] = float(pv[sel].sum() / (sel.sum() / 24))
    return out


def pv_worst(key): return min(pv_month(key).values())


def summary(key, ws_mult=1.0, loss=0.12):
    cf = cf_series(key, ws_mult, loss); t, _, pv = hourly(key)
    yrs = {}
    for x, c in zip(t, cf): yrs.setdefault(int(x[:4]), []).append(c)
    return dict(cf=float(cf.mean()), cf_by_year={y: float(np.mean(v)) for y, v in yrs.items()}, pv_kWh_kWp_year=float(pv.sum() / len(yrs)),
                pv_worst_month_kWh_kWp_day=pv_worst(key), hours=len(cf))


def rfnbo_efuel(key, w, bal, v, kWh_l, plant_eur_l, u_ref, buffer_eur_l, ws_mult=1.0, loss=0.12, rmax=8.0):
    """V18: RFNBO e-fuel with hourly matching to a renewable PPA (Delegated Regulation 2023/1184, hourly from 2030).
    The electrolyser (1 MW) follows r MW of contracted offshore wind; it pays the contract on all output, sells the surplus,
    and its plant cost per litre scales with its utilisation u = E[min(r*cf, 1)] relative to the baseload reference u_ref.
    A hydrogen buffer keeps the Fischer-Tropsch unit steady. Returns cost per litre excluding CO2."""
    mean, used, surplus = coverage_table(key, ws_mult, loss)
    ok = (R_GRID > 0) & (R_GRID <= rmax)
    with np.errstate(divide='ignore', invalid='ignore'):
        e_mwh = np.where(ok, (R_GRID * mean * (w + bal) - surplus * v) / used, np.inf)        # EUR per MWh into the electrolyser
        cost = np.where(ok, kWh_l * e_mwh / 1000 + plant_eur_l * u_ref / used + buffer_eur_l, np.inf)
    i = int(np.nanargmin(cost))
    return dict(price=float(cost[i]), r=float(R_GRID[i]), utilisation=float(used[i]), e_eur_MWh=float(e_mwh[i]), key=key, w=w)
