"""V19 figures (EN and FR): Fig. 11 electrification vs liquid-fuel sweet spot for heavy trucks, Fig. 12 renewable-liquid
supply curve and price levers, Fig. 13 the 2027-2041 transition; Supplementary Fig. S8 cost surface and Monte Carlo.
Run: python -I model/build_figures_sweetspot_v19.py"""
import sys, json, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import matplotlib.pyplot as plt
import build_figures_v12 as F

C, INK, INK2, MUTED, SURF, save, fmt = F.C, F.INK, F.INK2, F.MUTED, F.SURF, F.save, F.fmt
D = F.D
W = json.loads((D / 'v19_sweetspot_results.json').read_text())
SR = json.loads((D / 'v14_system_results.json').read_text())
P = W['policy']; FULL = W['full']; TR = W['transition']
DSL = 1.45

T = dict(
    en=dict(f10a='a  Heavy-truck system cost vs network length', f10b='b  Sweet-spot network vs liquid price', f10c='c  Truck km on liquid fuel',
            ers_km='Electric motorway network, km', bn='€ billion per year', diesel='Diesel trucks (€1.45/L)', opt='Sweet spot',
            liq='Renewable liquid price, € per litre', km='Network, km', gen='Share of HGV km on generator, %', marg='2041 marginal road litre',
            batt='battery', f11a='a  Renewable liquids by use and pathway, 2041', f11b='b  Kelp HTL fuel: price levers', f11c='c  e-fuel: price levers',
            GL='Cumulative supply, billion litres', eurl='€ per litre', pol='Policy\ndemand 2041', full='Full\ndecarbonisation',
            tier=dict(hefa='Waste-lipid HEFA', kelp='Kelp HTL (SMR + wind)', efuel_lc='Low-carbon e-fuel (nuclear/grid)', efuel_rf='RFNBO e-fuel (wind PPA, hourly)'),
            base='Central', all='All levers', delta='Change, € per litre',
            f12a='a  Transport CO₂ by segment', f12b='b  Electric motorways in service', f12c='c  Fleet and fuel shares',
            f12d='d  Renewable liquids by use', f12e='e  Annual cost vs fossil', f12f='f  Electricity for transport',
            mt='Mt CO₂e per year', seg=['Cars, vans, other light', 'Heavy trucks', 'Aviation', 'Shipping'],
            shares=['Electric light vehicles (fleet)', 'Hybrid trucks (fleet)', 'SAF share (ReFuelEU)', 'Shipping GHG-intensity cut (FuelEU)'],
            sup=['Jet (SAF)', 'Marine', 'Road (truck range extenders)'], GLy='billion litres per year', cost=['Heavy-truck system', 'SAF and marine-fuel premium', 'Motorway capex'],
            TWh='TWh per year', el=['Light vehicles', 'Heavy trucks', 'Low-carbon e-fuel', 'RFNBO e-fuel (wind PPA)'], pct='%',
            s8a='a  Truck system cost surface (policy 2041)', s8b='b  Sweet-spot network, 1,000 draws', s8c='c  Sweet-spot battery, 1,000 draws',
            kWh='Long-haul truck battery, kWh', share='Share of draws',
            f10d='d  Sweet-spot network vs off-wire legs', legx='Long-haul off-wire leg, dense network (km)', reg='Regional duty {} km/day',
            polc='Policy 2041', rfoc='RFNBO-only', fullc='Full decarb.', use=dict(jet='Jet', mar='Marine', road='Road', exp='Export'),
            s9a='a  Offshore capacity factor by month', s9b='b  Annual capacity factor, 2015–24', s9c='c  Electricity for hub process load',
            months=['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], cfp='Capacity factor, %', assumed='Generic screening value', era5='ERA5 mean (bar: min–max year)',
            flat_h='SMR + wind, flat €20 firming', eff_h='SMR + wind, weather-based', flat_w='Wind only, flat €20 firming', eff_w='Wind only, weather-based',
            smr='Reactor €105/MWh', eurmwh='€ per MWh of process load'),
    fr=dict(f10a='a  Coût du système poids lourds selon le réseau', f10b='b  Réseau optimal selon le prix du liquide', f10c='c  km poids lourds au carburant',
            ers_km='Autoroutes électriques, km', bn='milliards d’€ par an', diesel='Poids lourds diesel (1,45 €/L)', opt='Optimum',
            liq='Prix du carburant renouvelable, € par litre', km='Réseau, km', gen='Part des km PL au groupe électrogène, %', marg='Litre routier marginal 2041',
            batt='batterie', f11a='a  Liquides renouvelables par usage et filière, 2041', f11b='b  Carburant HTL d’algues : leviers', f11c='c  e-carburant : leviers',
            GL='Offre cumulée, milliards de litres', eurl='€ par litre', pol='Demande\nréglementaire 2041', full='Décarbonation\ntotale',
            tier=dict(hefa='HEFA de lipides usagés', kelp='HTL d’algues (PRM + éolien)', efuel_lc='e-carburant bas-carbone (nucléaire/réseau)', efuel_rf='e-carburant RFNBO (PPA éolien horaire)'),
            base='Central', all='Tous les leviers', delta='Variation, € par litre',
            f12a='a  CO₂ des transports par segment', f12b='b  Autoroutes électriques en service', f12c='c  Parts de flotte et de carburant',
            f12d='d  Liquides renouvelables par usage', f12e='e  Coût annuel vs fossile', f12f='f  Électricité pour les transports',
            mt='Mt CO₂e par an', seg=['Voitures, VUL, autres légers', 'Poids lourds', 'Aérien', 'Maritime'],
            shares=['Véhicules légers électriques (parc)', 'Poids lourds hybrides (parc)', 'Part de CAD (ReFuelEU)', 'Baisse d’intensité GES maritime (FuelEU)'],
            sup=['Kérosène (CAD)', 'Maritime', 'Route (prolongateurs des camions)'], GLy='milliards de litres par an', cost=['Système poids lourds', 'Surcoût CAD et maritime', 'Investissement autoroutes'],
            TWh='TWh par an', el=['Véhicules légers', 'Poids lourds', 'e-carburant bas-carbone', 'e-carburant RFNBO (PPA éolien)'], pct='%',
            s8a='a  Surface de coût du système PL (réglementaire 2041)', s8b='b  Réseau optimal, 1 000 tirages', s8c='c  Batterie optimale, 1 000 tirages',
            kWh='Batterie du camion longue distance, kWh', share='Part des tirages',
            f10d='d  Réseau optimal et trajets hors caténaire', legx='Trajet hors caténaire longue distance, réseau dense (km)', reg='Tournée régionale {} km/jour',
            polc='Réglementaire 2041', rfoc='RFNBO seul', fullc='Décarb. totale', use=dict(jet='Kérosène', mar='Maritime', road='Route', exp='Export'),
            s9a='a  Facteur de charge en mer par mois', s9b='b  Facteur de charge annuel, 2015–24', s9c='c  Électricité de la charge de procédé',
            months=['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], cfp='Facteur de charge, %', assumed='Valeur générique de criblage', era5='Moyenne ERA5 (barre : année min–max)',
            flat_h='PRM + éolien, garantie forfaitaire 20 €', eff_h='PRM + éolien, météo réelle', flat_w='Éolien seul, garantie forfaitaire 20 €', eff_w='Éolien seul, météo réelle',
            smr='Réacteur 105 €/MWh', eurmwh='€ par MWh de charge de procédé'))
KCOL = dict(hefa=C[3], kelp=C[2], efuel_lc=C[0], efuel_rf=C[6])


def ttl(ax, s): ax.set_title(s, fontsize=7, loc='left', weight='bold')


def fig10(lang):
    t = T[lang]
    curve = list(csv.DictReader(open(D / 'v19_cost_vs_network_policy.csv')))
    fig, axs4 = plt.subplots(2, 2, figsize=(7.2, 5.2)); axs = [axs4[0, 0], axs4[0, 1], axs4[1, 0]]
    ax = axs[0]
    L = np.array([float(r['L']) for r in curve]); tc = np.array([float(r['total']) for r in curve]) / 1e9
    ax.plot(L, tc, color=C[0], lw=2)
    ax.axhline(P['hgv_diesel_cost_bn'], color=INK2, lw=1, ls='--'); ax.text(14800, P['hgv_diesel_cost_bn'] + .3, t['diesel'], ha='right', fontsize=5.8, color=INK2)
    d = P['design']; ax.plot(d['L'], d['total'] / 1e9, 'o', ms=6, color=C[1], mec=SURF, mew=1.5, zorder=5)
    ax.annotate(f"{t['opt']}: {fmt(d['L'], lang, 0)} km,\n{fmt(d['B'], lang, 0)} / {fmt(d['B_r'], lang, 0)} kWh", (d['L'], d['total'] / 1e9), xytext=(d['L'] + 900, d['total'] / 1e9 - 3.6),
                fontsize=5.8, arrowprops=dict(arrowstyle='-', color=INK2, lw=.6))
    for i in (2, 5, 12):   # battery labels along the curve
        ax.text(L[i * 4], tc[i * 4] + .6, f"{fmt(float(curve[i * 4]['B']), lang, 0)} kWh", fontsize=5.2, color=INK2, ha='center')
    ax.set_xlabel(t['ers_km']); ax.set_ylabel(t['bn']); ax.set_ylim(0, 20); ax.set_xlim(0, 15000); ttl(ax, t['f10a'])
    sw = W['sweep']; p = [s['price'] for s in sw]
    for ax, key, yl, ttlk, mul in ((axs[1], 'L', t['km'], 'f10b', 1), (axs[2], 'gen_share', t['gen'], 'f10c', 100)):
        ax.plot(p, [s[key] * mul for s in sw], color=C[0], lw=2, marker='o', ms=3.5)
        ax.axvline(P['marginal_eur_l'], color=C[1], lw=1, ls=':')
        ax.set_xlabel(t['liq']); ax.set_ylabel(yl); ttl(ax, t[ttlk])
    axs[1].set_ylim(0, 10500); axs[2].set_ylim(0, 30)
    axs[1].text(P['marginal_eur_l'] + .07, 1200, t['marg'], fontsize=5.4, color=C[1], rotation=90, va='bottom')
    for s in sw[::4]: axs[1].text(s['price'] + .05, s['L'] + 450, f"{fmt(s['B'], lang, 0)}/{fmt(s['B_r'], lang, 0)}", fontsize=5.0, ha='center', color=INK2)
    ax = axs4[1, 1]; LG = W['offwire_legs']
    for rl, col in zip((150, 250, 350), (C[2], C[0], C[6])):
        rr = [l for l in LG if l['regional_leg_km'] == rl]
        ax.plot([l['leg_min_km'] for l in rr], [l['L'] for l in rr], color=col, lw=2, marker='o', ms=3.5, label=t['reg'].format(fmt(rl, lang, 0)))
    ax.set_xlabel(t['legx']); ax.set_ylabel(t['km']); ax.set_ylim(0, 8000); ax.legend(fontsize=5.4, loc='lower left'); ttl(ax, t['f10d'])
    for l in LG:
        if l['regional_leg_km'] == 250: ax.text(l['leg_min_km'], l['L'] - 520, f"{fmt(l['hgv_saving_bn'], lang, 1)}", fontsize=5.0, ha='center', color=INK2)
    fig.tight_layout(); save(fig, lang, 'Figure_11_electrification_liquid_sweet_spot')


def tornado(ax, base, levers, allp, t, lang, col):
    labs = [r['lever'] for r in levers][::-1]; dv = [r['delta'] for r in levers][::-1]
    y = np.arange(len(labs))
    ax.barh(y, dv, color=col, height=.62, edgecolor=SURF, lw=.4)
    for yi, v in zip(y, dv): ax.text(v - .015, yi, fmt(v, lang, 2), va='center', ha='right', fontsize=5.2, color=INK)
    ax.set_yticks(y, [short(l, lang) for l in labs], fontsize=5.3); ax.axvline(0, color=INK2, lw=.7)
    ax.set_xlabel(t['delta']); ax.set_xlim(min(dv) * 1.45, 0.02)
    ax.text(0.0, 1.0, f"{t['base']} {fmt(base, lang, 2)} → {t['all']} {fmt(allp, lang, 2)} €/L", transform=ax.transAxes, fontsize=5.6, weight='bold', va='bottom')


SHORT = {'en': {'Farm-gate': 'Seaweed cost 400→250 €/t', 'HTL fuel yield': 'HTL fuel yield +20 %', 'HTL plant cost': 'HTL plant cost −30 %', 'Finance at': 'Finance 6 %→3 %',
                'Marine harvest': 'Harvest 70→50 €/t', 'Turbine anchors': 'Turbine anchors 50→75 %', 'SMR electricity': 'SMR power 105→80 €/MWh', 'Kelp yield': 'Kelp yield +30 %',
                'CO2 from biogenic': 'Biogenic CO₂ instead of DAC', 'Electrolyser power': 'Power 70→50 €/MWh', 'Plant cost': 'Plant cost −35 %', 'Efficiency': '20→17 kWh/L (SMR steam)', 'DAC 250': 'DAC 250→150 €/t'},
         'fr': {'Farm-gate': 'Algues 400→250 €/t', 'HTL fuel yield': 'Rendement HTL +20 %', 'HTL plant cost': 'Coût unité HTL −30 %', 'Finance at': 'Financement 6 %→3 %',
                'Marine harvest': 'Récolte 70→50 €/t', 'Turbine anchors': 'Ancrage éoliennes 50→75 %', 'SMR electricity': 'Électricité PRM 105→80 €/MWh', 'Kelp yield': 'Rendement algues +30 %',
                'CO2 from biogenic': 'CO₂ biogénique au lieu du DAC', 'Electrolyser power': 'Électricité 70→50 €/MWh', 'Plant cost': 'Coût usine −35 %', 'Efficiency': '20→17 kWh/L (vapeur PRM)', 'DAC 250': 'DAC 250→150 €/t'}}


def short(l, lang):
    for k, v in SHORT[lang].items():
        if l.startswith(k): return v
    return l


def fig11(lang):
    t = T[lang]
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.9), gridspec_kw=dict(width_ratios=[1.6, 1, 1]))
    ax = axs[0]; kinds = ('hefa', 'kelp', 'efuel_lc', 'efuel_rf'); uses = ('jet', 'mar', 'road', 'exp')
    xs = []; xt = []
    for gi, (case, cl) in enumerate(((P, t['polc']), (W['rfnbo_only_sensitivity'], t['rfoc']), (FULL, t['fullc']))):
        for ui, u in enumerate(uses):
            x = gi * 5 + ui; xs.append(x); xt.append(t['use'][u]); bottom = 0
            for k in kinds:
                v = sum(val for key, val in case['alloc_GL'].items() if key.split('|')[1] == u and key.split('|')[0].startswith(k))
                ax.bar(x, v, bottom=bottom, color=KCOL[k], width=.75, edgecolor=SURF, lw=.4, label=t['tier'][k] if (gi == 0 and ui == 0) else None); bottom += v
        ax.text(gi * 5 + 1.5, 9.0, cl, ha='center', fontsize=6.0, weight='bold')
    ax.set_xticks(xs, xt, fontsize=5.4, rotation=90); ax.set_ylabel(t['GLy']); ax.grid(axis='x', visible=False); ax.set_ylim(0, 9.8)
    ax.legend(fontsize=4.6, loc='upper left', bbox_to_anchor=(0.0, 0.86)); ttl(ax, t['f11a'])
    K = W['kelp_levers']; E = W['efuel_levers']
    tornado(axs[1], K['base'], K['levers'], K['all'], t, lang, C[2]); axs[1].set_title(t['f11b'], fontsize=7, loc='left', weight='bold', pad=11)
    tornado(axs[2], E['base_dac'], E['levers'], E['all_dac'], t, lang, C[6]); axs[2].set_title(t['f11c'], fontsize=7, loc='left', weight='bold', pad=11)
    fig.tight_layout(w_pad=.6); save(fig, lang, 'Figure_12_liquid_supply_and_price_levers')


def fig12(lang):
    t = T[lang]; y = [r['year'] for r in TR]
    fig, axs = plt.subplots(2, 3, figsize=(7.4, 4.9))
    ax = axs[0, 0]; segs = ['co2_ldv', 'co2_hgv', 'co2_aviation', 'co2_maritime']; cols = [C[0], C[1], C[6], C[2]]
    ax.stackplot(y, *[[r[s] for r in TR] for s in segs], colors=cols, labels=t['seg'], edgecolor=SURF, lw=.6)
    ax.text(2041, TR[-1]['co2_total'] + 14, f"{fmt(TR[-1]['co2_total'], lang, 0)} Mt\n(−{fmt(100 * TR[-1]['co2_reduction_vs_2024'], lang, 0)} %)", ha='right', fontsize=5.8, weight='bold')
    ax.set_ylabel(t['mt']); ax.set_ylim(0, 160); ax.legend(fontsize=5.0, loc='lower left', ncol=2); ttl(ax, t['f12a'])
    ax = axs[0, 1]; ax.bar(y, [r['ers_km'] for r in TR], color=C[0], width=.7, edgecolor=SURF, lw=.3)
    ax.text(2041, TR[-1]['ers_km'] + 250, fmt(TR[-1]['ers_km'], lang, 0), ha='center', fontsize=5.6); ax.set_ylabel('km'); ax.set_ylim(0, 10000); ttl(ax, t['f12b'])
    ax = axs[0, 2]
    for k, col, lab, dy in zip(('ldv_bev_fleet', 'hybrid_fleet', 'saf_share', 'maritime_reduction'), (C[0], C[1], C[6], C[2]), t['shares'], (0, 0, 2.8, -2.8)):
        v = [100 * r[k] for r in TR]; ax.plot(y, v, color=col, lw=2, label=lab)
        ax.text(2041.3, v[-1] + dy, fmt(v[-1], lang, 0), fontsize=5.4, va='center', color=INK)
    ax.set_ylabel(t['pct']); ax.set_ylim(0, 100); ax.set_xlim(2027, 2042.5); ax.legend(fontsize=5.0, loc='upper left'); ttl(ax, t['f12c'])
    ax = axs[1, 0]
    ax.stackplot(y, [r['jet_GL'] for r in TR], [r['marine_GL'] for r in TR], [r['road_GL'] for r in TR], colors=[C[6], C[2], C[1]], labels=t['sup'], edgecolor=SURF, lw=.6)
    ax.set_ylabel(t['GLy']); ax.legend(fontsize=5.2, loc='upper left'); ttl(ax, t['f12d'])
    ax = axs[1, 1]; w = .28; yy = np.array(y)
    for j, (k, col, lab) in enumerate(zip(('hgv_extra_cost_bn', 'liquid_premium_bn', 'ers_capex_bn'), (C[1], C[6], C[0]), t['cost'])):
        ax.bar(yy + (j - 1) * w, [r[k] for r in TR], width=w, color=col, label=lab, edgecolor=SURF, lw=.2)
    ax.axhline(0, color=INK2, lw=.7); ax.set_ylabel(t['bn']); ax.legend(fontsize=5.0, loc='upper left'); ttl(ax, t['f12e'])
    ax = axs[1, 2]
    W_ = W['assumptions']
    ax.stackplot(y, [r['ldv_TWh'] for r in TR], [r['hgv_TWh'] for r in TR], [r['lowcarbon_TWh'] for r in TR], [r['rfnbo_TWh'] for r in TR],
                 colors=[C[0], C[1], C[3], C[6]], labels=t['el'], edgecolor=SURF, lw=.6)
    ax.set_ylabel(t['TWh']); ax.legend(fontsize=5.2, loc='upper left'); ttl(ax, t['f12f'])
    for a in axs.flat: a.set_xticks([2027, 2031, 2035, 2039, 2041]); a.tick_params(axis='x', labelsize=6)
    fig.tight_layout(); save(fig, lang, 'Figure_13_transition_2027_2041')


def figS9(lang):
    t = T[lang]; wc = SR['weather_contracts']; keys = ['DKQ', 'LEH', 'BRE', 'STN', 'LRO', 'FOS']
    mon = list(csv.DictReader(open(D / 'weather' / 'cf_and_pv_by_site_month_v16.csv')))
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.9), gridspec_kw=dict(width_ratios=[1.1, 1, 1.2]))
    ax = axs[0]
    for k, col in zip(keys, [C[0], C[1], C[2], C[3], C[6], C[4]]):
        v = [float(r['capacity_factor_net']) for r in mon if r['site'] == k]
        ax.plot(range(1, 13), [100 * x for x in v], color=col, lw=1.6, label=F.SN[k].replace('-sur-Mer', ''))
    ax.set_xticks(range(1, 13), t['months'], fontsize=5.6); ax.set_ylabel(t['cfp']); ax.set_ylim(0, 70); ax.legend(fontsize=5.0, ncol=2, loc='lower left'); ttl(ax, t['s9a'])
    ax = axs[1]
    for i, k in enumerate(keys):
        r = next(x for x in wc if x['key'] == k and x['option'] == 'hybrid')
        ax.plot([i, i], [100 * r['cf_min_year'], 100 * r['cf_max_year']], color=C[0], lw=3, solid_capstyle='round')
        ax.plot(i, 100 * r['cf'], 'o', color=C[0], ms=5, mec=SURF, mew=1)
        ax.plot(i, 100 * r['cf_assumed_v16'], 'D', color=C[1], ms=4, mec=SURF, mew=.8, label=t['assumed'] if i == 0 else None)
    ax.plot([], [], 'o', color=C[0], ms=5, label=t['era5'])
    ax.set_xticks(range(6), [F.SN[k].replace('-sur-Mer', '') for k in keys], fontsize=5.6, rotation=30); ax.set_ylabel(t['cfp']); ax.set_ylim(25, 62); ax.legend(fontsize=5.0, loc='upper left'); ttl(ax, t['s9b'])
    ax = axs[2]; x = np.arange(6); w = .2
    for j, (opt, fld, col, lab) in enumerate((('hybrid', 'v16_flat_eur_MWh', '#c9c6be', t['flat_h']), ('hybrid', 'effective_eur_MWh', C[2], t['eff_h']),
                                                ('wind', 'v16_flat_eur_MWh', '#9d9a92', t['flat_w']), ('wind', 'effective_eur_MWh', C[0], t['eff_w']))):
        ax.bar(x + (j - 1.5) * w, [next(r for r in wc if r['key'] == k and r['option'] == opt)[fld] for k in keys], width=w, color=col, label=lab, edgecolor=SURF, lw=.3)
    ax.axhline(105, color=INK2, lw=.8, ls=':'); ax.text(-0.45, 108, t['smr'], fontsize=5.2, ha='left', color=INK2)
    ax.set_xticks(x, [F.SN[k].replace('-sur-Mer', '') for k in keys], fontsize=5.6, rotation=30); ax.set_ylabel(t['eurmwh']); ax.set_ylim(0, 135)
    ax.legend(fontsize=4.9, loc='upper center', bbox_to_anchor=(.5, -.3), ncol=2); ttl(ax, t['s9c'])
    fig.tight_layout(); save(fig, lang, 'Supplementary_Figure_S9_weather_wind_supply')


def figS8(lang):
    t = T[lang]
    Z = np.loadtxt(D / 'v19_cost_surface_policy_bnEUR.csv', delimiter=',')
    L = np.arange(0, 15001, 250.0); B = np.arange(0, 1001, 20.0)
    mc = list(csv.DictReader(open(D / 'v19_sweetspot_monte_carlo.csv')))
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.6), gridspec_kw=dict(width_ratios=[1.3, 1, 1]))
    ax = axs[0]; Zc = np.clip(Z, None, 24)
    im = ax.pcolormesh(B, L, Zc, cmap='Blues_r', shading='auto')
    cs = ax.contour(B, L, Z, levels=[11, 12, 13, 14.38, 16, 20], colors=INK2, linewidths=.5)
    ax.clabel(cs, fontsize=4.8, fmt=lambda v: fmt(v, lang, 0 if abs(v - round(v)) < 1e-6 else 1))
    d = P['design']; ax.plot(d['B'], d['L'], 'o', color=C[1], ms=6, mec=SURF, mew=1.5)
    ax.set_xlabel(t['kWh']); ax.set_ylabel(t['ers_km']); ax.grid(False); ttl(ax, t['s8a'])
    cb = fig.colorbar(im, ax=ax, fraction=.05, pad=.02); cb.ax.tick_params(labelsize=5.5); cb.set_label(t['bn'], fontsize=6)
    for ax, k, xl, ttlk, col in ((axs[1], 'L', t['ers_km'], 's8b', C[0]), (axs[2], 'B', t['kWh'], 's8c', C[2])):
        v = [float(r[k]) for r in mc]
        ax.hist(v, bins=25, color=col, weights=np.ones(len(v)) / len(v), edgecolor=SURF, lw=.4)
        ax.axvline(P['design'][k], color=C[1], lw=1.2, ls='--'); ax.set_xlabel(xl); ax.set_ylabel(t['share']); ttl(ax, t[ttlk])
    fig.tight_layout(); save(fig, lang, 'Supplementary_Figure_S8_sweet_spot_surface_and_uncertainty')


if __name__ == '__main__':
    for lang in ('en', 'fr'):
        fig10(lang); fig11(lang); fig12(lang); figS8(lang); figS9(lang)
    print('V19 figures written')
