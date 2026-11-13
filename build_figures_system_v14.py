"""V14 system figures (EN and FR): Fig. 8 integrated offshore hub schematic, Fig. 10 fuel cost and transport CO2,
Supplementary Fig. S7 uncertainty of fuel cost and motorway saving.  Run: python -I model/build_figures_system_v14.py"""
import sys, json, csv, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon
from matplotlib.lines import Line2D
import build_figures_v12 as F

C, INK, INK2, MUTED, SURF, save, fmt = F.C, F.INK, F.INK2, F.MUTED, F.SURF, F.save, F.fmt
D = F.D
SR = json.loads((D / 'v14_system_results.json').read_text())
V12 = F.R
KEYS = ['DKQ', 'LEH', 'BRE', 'STN', 'LRO', 'FOS']

T = dict(
    en=dict(f8='Integrated offshore hub (schematic, not to scale)', turb='Wind turbine (foundation = kelp anchor)', kelp='Kelp longlines',
            pen='Fish pens (IMTA)', harv='Grid Harvester on transport cable', drone='Utility drones', smr='Coastal SMR\n(heat, power)',
            htl='HTL fuel plant\n+ farms', cable='Export cable', port='Port', ship='Wet-kelp carrier',
            f9a='a  Kelp drop-in fuel, mean of six hubs', f9b='b  By site', f9c='c  Transport CO₂ with electric motorways',
            opts=['SMR,\nconv.', 'SMR +\ndrones', 'Wind\nonly', 'SMR +\nwind'],
            optl=['SMR, conventional farm', 'SMR + harvester, drones', 'Offshore wind only', 'SMR + offshore wind'],
            comp=dict(feedstock='Kelp at farm gate', harvest='Harvest', electricity='Electricity', heat='Process heat', other='Conversion, other'),
            eurl='€ per litre', diesel='Diesel, long-run 2030–41 (incl. ETS2)', mt='Mt CO₂e per year', transport='All domestic\ntransport 2024',
            hgv='Heavy goods\nvehicles', avoided='Avoided by ERS\n+ kelp hybrids', rest='Remaining',
            s7='Uncertainty of the system extension (2,000 model draws)', s7a='a  Fuel cost, mean of six hubs', s7b='b  Electric-motorway net saving',
            bn='€ billion per year', share='Share of draws'),
    fr=dict(f8='Pôle offshore intégré (schéma, hors échelle)', turb='Éolienne (fondation = ancrage des algues)', kelp='Filières de laminaires',
            pen='Cages à poissons (AMTI)', harv='Grid Harvester sur câble de transport', drone='Drones de service', smr='PRM côtier\n(chaleur, électricité)',
            htl='Unité HTL\n+ exploitations', cable='Câble d’export', port='Port', ship='Transport d’algues fraîches',
            f9a='a  Carburant d’algues, moyenne', f9b='b  Par site', f9c='c  CO₂ des transports, autoroutes électriques',
            opts=['PRM,\nclass.', 'PRM +\ndrones', 'Éolien\nseul', 'PRM +\néolien'],
            optl=['PRM, ferme classique', 'PRM + récolteuse, drones', 'Éolien en mer seul', 'PRM + éolien en mer'],
            comp=dict(feedstock='Algues bord de ferme', harvest='Récolte', electricity='Électricité', heat='Chaleur de procédé', other='Conversion, autres'),
            eurl='€ par litre', diesel='Gazole, long terme 2030–41 (avec SEQE2)', mt='Mt CO₂e par an', transport='Ensemble des\ntransports 2024',
            hgv='Poids\nlourds', avoided='Évités par ERS\n+ hybrides aux algues', rest='Restant',
            s7='Incertitude de l’extension système (2 000 tirages du modèle)', s7a='a  Coût du carburant, moyenne des six pôles', s7b='b  Gain net des autoroutes électriques',
            bn='milliards d’€ par an', share='Part des tirages'))
OPT = ['smr', 'smr_d', 'wind_d', 'hybrid_d']
OCOL = [C[7], C[3], C[0], C[2]]


def fig8(lang):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(7.2, 3.9)); ax.set_xlim(0, 100); ax.set_ylim(0, 54); ax.axis('off'); ax.set_aspect('equal')
    ax.add_patch(Rectangle((0, 0), 100, 54, fc='#e7f0f5', ec='none', zorder=0))
    ax.add_patch(Polygon([(0, 0), (0, 54), (14, 54), (16, 40), (13, 26), (15, 10), (12, 0)], fc='#e4e2dc', ec='#c4c1b8', lw=.6, zorder=1))
    # turbines on a grid with kelp lines between
    xs = np.arange(30, 95, 12); ys = np.arange(8, 50, 10)
    for y in ys:
        for x0, x1 in zip(xs[:-1], xs[1:]):
            for dy in (-2.4, -1.2, 0, 1.2, 2.4):
                ax.plot([x0 + 1, x1 - 1], [y + dy + 5 if y + 5 < 50 else y + dy, y + dy + 5 if y + 5 < 50 else y + dy], color=C[5], lw=.7, alpha=.75, zorder=2)
    for x in xs:
        for y in ys:
            ax.add_patch(Circle((x, y), 1.0, fc='white', ec=INK2, lw=.8, zorder=4))
            ax.plot([x, x], [y, y + 2.6], color=INK2, lw=.8, zorder=4)
            for a in (90, 210, 330):
                ax.plot([x, x + 2.2 * math.cos(math.radians(a))], [y + 2.6, y + 2.6 + 2.2 * math.sin(math.radians(a))], color=INK2, lw=.8, zorder=4)
    for (px, py) in ((48, 23), (72, 33), (60, 43)):
        ax.add_patch(Circle((px, py), 2.4, fc='#ffd9c7', ec=C[1], lw=1, zorder=3))
    ax.plot([24, 96], [18.2, 18.2], color=INK, lw=1.2, ls=(0, (4, 2)), zorder=5)
    ax.add_patch(FancyBboxPatch((52, 16.6), 6, 3.2, boxstyle='round,pad=0.2', fc=C[6], ec='none', zorder=6))
    for (dx, dy) in ((40, 30), (66, 25), (82, 40), (36, 45), (86, 12)):
        ax.add_patch(Polygon([(dx - 1.2, dy), (dx, dy + .8), (dx + 1.2, dy), (dx, dy - .8)], fc=C[3], ec=INK2, lw=.4, zorder=6))
    ax.add_patch(FancyBboxPatch((2, 30), 10, 9, boxstyle='round,pad=0.3', fc='#d6e6fb', ec=C[0], lw=1, zorder=6))
    ax.text(7, 34.5, t['smr'], ha='center', va='center', fontsize=6.2, zorder=7)
    ax.add_patch(FancyBboxPatch((2, 14), 10, 9, boxstyle='round,pad=0.3', fc='#d8f2e6', ec=C[2], lw=1, zorder=6))
    ax.text(7, 18.5, t['htl'], ha='center', va='center', fontsize=6.2, zorder=7)
    ax.plot([30, 15], [8, 8], color=C[0], lw=1.3, zorder=3); ax.text(22, 6.3, t['cable'], fontsize=5.6, ha='center', color=C[0])
    ax.annotate('', xy=(13, 19), xytext=(28, 21), arrowprops=dict(arrowstyle='->', color=C[6], lw=1.1), zorder=6)
    ax.text(20.5, 22.3, t['ship'], fontsize=5.6, ha='center', color=C[6])
    lg = [Line2D([], [], marker='o', ls='', mfc='white', mec=INK2, label=t['turb']), Line2D([], [], color=C[5], lw=1.4, label=t['kelp']),
          Line2D([], [], marker='o', ls='', mfc='#ffd9c7', mec=C[1], ms=8, label=t['pen']), Line2D([], [], color=INK, ls='--', lw=1.2, label=t['harv']),
          Line2D([], [], marker='D', ls='', mfc=C[3], mec=INK2, ms=5, label=t['drone'])]
    ax.legend(handles=lg, loc='upper center', bbox_to_anchor=(.55, -.02), ncol=3, fontsize=6.2)
    ax.set_title(t['f8'], fontsize=7.6, loc='left', weight='bold')
    fig.tight_layout(); save(fig, lang, 'Figure_8_integrated_offshore_hub_schematic')


def fig9(lang):
    t = T[lang]; nat = SR['national']; sites = SR['sites']
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 3.0), gridspec_kw=dict(width_ratios=[1.1, 1.4, 1]))
    ax = axs[0]; comps = ['feedstock', 'harvest', 'electricity', 'heat', 'other']; cc = [C[5], C[3], C[0], C[1], MUTED]
    for i, o in enumerate(OPT):
        bottom = 0
        rr = [sites[f'{k}|{o}'] for k in KEYS]
        for c, col in zip(comps, cc):
            v = float(np.mean([r[f'{c}_eur_l'] for r in rr]))
            ax.bar(i, v, bottom=bottom, color=col, width=.62, edgecolor=SURF, lw=.4, label=t['comp'][c] if i == 0 else None); bottom += v
        ax.text(i, bottom + .05, fmt(bottom, lang, 2), ha='center', va='bottom', fontsize=6.2)
    dsl = V12['inputs']['e']['diesel_longrun_eur_l'] if 'inputs' in V12 and 'e' in V12['inputs'] else 1.45
    ax.axhline(dsl, color=INK, lw=.9, ls='--', label=t['diesel'])
    ax.set_xticks(range(4), t['opts'], fontsize=5.8); ax.set_ylabel(t['eurl']); ax.set_ylim(0, 3.3)
    ax.legend(fontsize=5.2, loc='upper center', bbox_to_anchor=(.5, -.2), ncol=2); ax.set_title(t['f9a'], fontsize=7, loc='left', weight='bold')
    ax = axs[1]; x = np.arange(len(KEYS))
    for j, (o, col) in enumerate(zip(OPT, OCOL)):
        ax.bar(x + (j - 1.5) * .2, [sites[f'{k}|{o}']['fuel_eur_l'] for k in KEYS], width=.19, color=col, label=t['optl'][j], edgecolor=SURF, lw=.3)
    ax.set_xticks(x, [F.SN[k].replace('-sur-Mer', '') for k in KEYS], fontsize=5.8, rotation=30); ax.set_ylim(0, 4.0); ax.set_ylabel(t['eurl'])
    ax.legend(fontsize=5.2, loc='upper center', bbox_to_anchor=(.5, -.28), ncol=2); ax.set_title(t['f9b'], fontsize=7, loc='left', weight='bold')
    ax = axs[2]; eb = SR['ers_best']; tr = SR['assumptions']['transport_MtCO2_2024']; hgv = eb['co2_avoided_net_marine_Mt'] / eb['hgv_share']
    av = eb['co2_avoided_net_marine_Mt']
    ax.bar(0, tr - av, color='#d9d7d1', width=.6); ax.bar(0, av, bottom=tr - av, color=C[2], width=.6)
    ax.bar(1, hgv - av, color='#d9d7d1', width=.6, label=t['rest']); ax.bar(1, av, bottom=hgv - av, color=C[2], width=.6, label=t['avoided'])
    ax.text(0, tr + 2, fmt(tr, lang, 1), ha='center', fontsize=6.2); ax.text(1, hgv + 2, fmt(hgv, lang, 1), ha='center', fontsize=6.2)
    ax.text(1.36, hgv - av / 2, f"−{fmt(av, lang, 1)}\n({fmt(100 * eb['hgv_share'], lang, 0)} %)" if lang == 'fr' else f"−{fmt(av, lang, 1)}\n({fmt(100 * eb['hgv_share'], lang, 0)}%)", ha='left', va='center', fontsize=5.8, color=INK)
    ax.text(0, tr - av / 2, f"−{fmt(100 * eb['transport_share'], lang, 0)} %" if lang == 'fr' else f"−{fmt(100 * eb['transport_share'], lang, 0)}%", ha='center', va='center', fontsize=5.8, color='white', weight='bold')
    ax.set_xticks([0, 1], [t['transport'], t['hgv']], fontsize=5.8); ax.set_ylabel(t['mt']); ax.set_ylim(0, 140); ax.set_xlim(-.5, 2.0)
    ax.legend(fontsize=5.2, loc='upper center', bbox_to_anchor=(.5, -.2), ncol=1); ax.set_title(t['f9c'], fontsize=7, loc='left', weight='bold')
    fig.tight_layout(); save(fig, lang, 'Figure_10_fuel_cost_and_transport_CO2')


def figS7(lang):
    t = T[lang]; mc = list(csv.DictReader(open(D / 'v14_system_monte_carlo.csv')))
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7))
    ax = axs[0]; bins = np.linspace(2.0, 6.0, 41)
    for k, col, lab in (('smr_d_eur_l', OCOL[1], t['optl'][1]), ('wind_eur_l', OCOL[2], t['optl'][2]), ('hybrid_eur_l', OCOL[3], t['optl'][3])):
        ax.hist([float(r[k]) for r in mc], bins=bins, histtype='step', color=col, lw=1.4, label=lab, weights=np.ones(len(mc)) / len(mc))
    ax.set_xlabel(t['eurl']); ax.set_ylabel(t['share']); ax.legend(fontsize=5.6); ax.set_title(t['s7a'], fontsize=7, loc='left', weight='bold')
    ax = axs[1]; v = [float(r['ers_saving_bn']) for r in mc]
    ax.hist(v, bins=40, color=C[2], alpha=.85, weights=np.ones(len(mc)) / len(mc)); ax.axvline(0, color=C[7], lw=1)
    for qq, ls in ((5, ':'), (50, '-'), (95, ':')): ax.axvline(np.percentile(v, qq), color=INK, lw=.9, ls=ls)
    ax.set_xlabel(t['bn']); ax.set_ylabel(t['share']); ax.set_title(t['s7b'], fontsize=7, loc='left', weight='bold')
    fig.suptitle(t['s7'], fontsize=7.6, weight='bold', x=.01, ha='left'); fig.tight_layout(); save(fig, lang, 'Supplementary_Figure_S7_system_uncertainty')


if __name__ == '__main__':
    for lang in ('en', 'fr'):
        for f in (fig8, fig9, figS7): f(lang)
    print('system figures written')
