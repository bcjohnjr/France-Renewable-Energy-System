"""V12 figures in English and French.  Run: python -I model/build_figures_v12.py"""
import sys, json, csv, math
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, FancyArrowPatch, Patch, Rectangle
from matplotlib.lines import Line2D
from matplotlib import font_manager
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'model'))
import geo_france as g
import france_v12 as m

D = ROOT / 'data'
R = json.loads((D / 'v12_results.json').read_text())
FONT = 'Inter' if any('Inter' == f.name for f in font_manager.fontManager.ttflist) else 'DejaVu Sans'
plt.rcParams.update({'font.family': FONT, 'font.size': 8.5, 'pdf.fonttype': 42, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#8a8984', 'axes.labelcolor': '#2b2b29', 'xtick.color': '#52514e', 'ytick.color': '#52514e',
                     'axes.grid': True, 'grid.color': '#e6e4df', 'grid.linewidth': .6, 'axes.axisbelow': True, 'legend.frameon': False})
C = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
INK, INK2, MUTED, SURF = '#0b0b0b', '#52514e', '#8a8984', '#fcfcfb'
SEA, LAND, FR_LAND = '#e7f0f5', '#e4e2dc', '#faf8f2'
SITES = m.SITES
SN = {s.key: s.name for s in SITES}


def fmt(x, lang, nd=1):
    s = f'{x:,.{nd}f}'.replace('-', '−')
    return s.replace(',', ' ').replace('.', ',') if lang == 'fr' else s


def _fr_ticks(fig):
    from matplotlib.ticker import ScalarFormatter, FuncFormatter
    f = FuncFormatter(lambda x, p: (f'{x:,.10g}').replace(',', ' ').replace('.', ',').replace('-', '−'))
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            if isinstance(axis.get_major_formatter(), ScalarFormatter): axis.set_major_formatter(f)


def save(fig, lang, name):
    if lang == 'fr': _fr_ticks(fig)
    out = ROOT / 'figures' / lang; out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f'{name}.pdf', bbox_inches='tight', facecolor='white')
    fig.savefig(out / f'{name}.png', dpi=300, bbox_inches='tight', facecolor='white')
    Image.open(out / f'{name}.png').convert('RGB').save(out / f'{name}.tif', compression='tiff_lzw', dpi=(300, 300))
    plt.close(fig)


def base_map(ax):
    ax.set_facecolor(SEA)
    for poly in (g.CONTINENT, g.IBERIA, g.SARDINIA): ax.add_patch(Polygon(poly, fc=LAND, ec='#c4c1b8', lw=.4, zorder=1))
    ax.set_xlim(-6.2, 9.9); ax.set_ylim(41.25, 51.55); ax.set_aspect(1 / math.cos(math.radians(46.4)))
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values(): s.set_visible(True); s.set_color('#c4c1b8'); s.set_linewidth(.6)


def france_on_top(ax, z=3):
    for poly in (g.FRANCE, g.CORSICA): ax.add_patch(Polygon(poly, fc=FR_LAND, ec='#6d7a83', lw=.7, zorder=z))
    ax.add_patch(Polygon(g.ENGLAND, fc=LAND, ec='#c4c1b8', lw=.4, zorder=z))


T = {
 'en': dict(
  f1='Six candidate coastal SMR heat-cascade hubs and their marine systems (schematic)',
  zones={'atlantic_kelp': 'Atlantic kelp (alginate)', 'channel': 'Channel seasonal kelp (alginate)', 'biscay_mixed': 'Biscay warm-edge kelp (alginate)', 'med_ulva': 'Mediterranean Ulva (no alginate)'},
  hub='Candidate hub', alg='Existing alginate plants', aqua='Gravelines NPP warm-water fish farm (since 1991)',
  note='Hand-digitised outlines; zones and hubs are screening illustrations, not reactor sites or concessions.',
  site_lab={'DKQ': 'Channel kelp · sea bass · honey', 'LEH': 'Channel kelp · salmon · honey-smoked salmon', 'BRE': 'Atlantic kelp · salmon · honey-smoked salmon',
            'STN': 'Atlantic kelp · sea bass · honey', 'LRO': 'Biscay kelp · meagre/bass · honey', 'FOS': 'Ulva (no alginate) · sea bream · honey'},
  f2a='a  Whole hub: where reactor heat goes, by temperature', f2b='b  Low-temperature end: MED condenser, loop and users',
  duty='Annual-average heat duty (MW)', temp='Temperature (°C)',
  htl='HTL steam (direct)', trim='HTL electric trim', ext='LP extraction → MED', effects='MED effects 65 → 40 °C', cond='Main condenser to sea',
  vap='MED last-effect vapour (40 °C)', loop='Distribution loop 25 → 36 °C', dT='ΔT', direct='direct use', hpl='heat-pump lift',
  users={'prawn_RAS': 'Prawn RAS', 'hatchery': 'Hatchery', 'greenhouse_base': 'Greenhouse base', 'greenhouse_peak': 'Greenhouse peak',
         'alginate_drying': 'Alginate drying', 'smokehouse': 'Smokehouse', 'kelp_drying': 'Kelp & fertiliser drying'},
  f3title='Annual heat cascade at the Brest hub (GWh per year)', reactor='Reactor heat', elec='Electricity\n(gross)', htlb='HTL steam\n>250 °C',
  trimb='Electric HTL\ntrim', medb='MED distillation\n~70 °C', water='Distilled water', lowt='~36 °C MED\ncondenser loop', condb='Main condenser\nto sea',
  hpb='Condenser-loop\nheat pump', bkb='Outage backup\n(boilers, HP)', unusedb='Unused / to sea', penalty='turbine work lost', Mm3='Mm³',
  leg_direct='direct use of loop water', leg_hp='lifted by heat pump',
  f4a='a  Monthly low-temperature demand at Brest', f4b='b  Use of 2.0 Mm³ of distilled water at Brest', month='Month', gwh='GWh per month',
  avail='MED condenser heat available', m3='thousand m³ per year',
  wuses={'greenhouse_irrigation': 'Greenhouse irrigation', 'prawn_RAS_makeup': 'Prawn RAS make-up', 'hatchery_and_processing': 'Hatchery & processing',
         'electrolyser_feed': 'Electrolyser feed', 'alginate_extraction': 'Alginate extraction', 'demin_sold': 'Port-industry demin. water (sold)', 'bulk_sold': 'Bulk supply (sold)', 'outage_mains': 'Mains bought during outages'},
  f5a='a  Consolidated co-product value by site', f5b='b  Net cash relative to heat-pump-only', c20='Cascade, 2.0 Mm³ (firm heat)', crs='Cascade, right-sized (firm heat)', crsn='Cascade, right-sized, no outage backup (conditional)', swro='HP + SWRO, 2.0 Mm³ (firm heat)', s5='Cascade minus heat-pump-only at Brest (2.0 Mm³, firm heat)', f5c='c  First-law utilisation',
  meur='M€ per year', ent={'greenhouse': 'Greenhouses', 'prawn': 'Prawns', 'finfish_imta': 'Finfish (IMTA)', 'honey': 'Honey', 'honey_smoked_salmon': 'Honey-smoked salmon',
       'residue_meal': 'Residue meal', 'alginate': 'Alginate', 'fuel_chain_utilities': 'Fuel-chain utilities', 'heat_and_water_infrastructure': 'Heat & water infrastructure'},
  bridge={'heat_pump_electricity_avoided_eur': 'HP electricity\navoided', 'mains_water_avoided_eur': 'Mains water\navoided', 'water_sales_eur': 'Water\nsales',
          'turbine_work_lost_eur': 'Turbine work\nlost', 'med_pumping_and_distribution_eur': 'MED & loop\npumping', 'med_capital_om_brine_eur': 'MED capital,\nO&M, brine',
          'heat_equipment_capital_difference_eur': 'Heat-pump &\nboiler capital', 'outage_grid_backup_eur': 'Outage grid\nelectricity', 'water_polishing_eur': 'Water\npolishing', 'cascade_increment_eur': 'Net'},
  casc='Cascade', hponly='Heat-pump only', total='Total',
  f6a='a  Fish nitrogen captured by co-located seaweed', f6b='b  Honey limits honey-smoked salmon', tN='t N per year', dis='dissolved N released', capd='captured by seaweed',
  hives='Hives per hub', smoked_t='Honey-smoked salmon (t per year)', target='Smokehouse target', central='central case',
  f7a='a  Packaging-alginate margin at Brest (consolidated)', f7b='b  Break-even price by site', f7c='c  Climate effect per kg plastic replaced',
  price='Packaging alginate price (€ per kg)', repl='Replacement fuel', pack='packaging only', comb='with food-grade revenue', bekg='€ per kg',
  kgco2='kg CO₂e per kg plastic', lowc='Low-carbon\nfuel fills gap', foss='Diesel\nfills gap', plastic='Plastic avoided', algproc='Alginate processing', fuelgap='Extra fossil diesel', net='Net',
  s1='Model-draw distributions (2,000 draws, {n} active inputs)', s1p=['National co-product value (M€/yr)', 'Right-sized cascade − HP-only,\nfirm heat (M€/yr)', '2.0 Mm³ cascade − HP-only,\nfirm heat (M€/yr)', 'Brest packaging break-even (€/kg)'],
  s2a='a  Low-temperature supply by MED size (Brest)', s2b='b  Cascade increment by MED size (Brest)', hpcap='Installed HP capacity (MW, right axis)', mw='MW', red='Cascade − HP-only, redundant HPs', nfirm='Cascade − HP-only, no outage backup (conditional)', s6='Cascade minus heat-pump-only with firm heat, six sites (M€ per year)', s6a='a  Right-sized plants (0.9–1.15 Mm³)', s6b='b  2.0 Mm³ plants', ghs='Greenhouse heat used directly at 35 °C (%)', pel='Electricity value (€/MWh)', vsro='Cascade − HP + SWRO (same output)', medsize='MED distillate (Mm³ per year)', gwhy='GWh per year',
  frommed='From MED condenser', fromhp='Condenser-loop heat pump', unused='Unused MED heat', cop_='Co-product value', inc='Cascade − HP-only, firm heat (HPs on residual load + boilers)',
  s3='Electric-motorway (catenary ERS) corridors, schematic', tier1='Phase 1 (GT1 2030 scale)', tier2='Phase 2 (GT1 full network)', pilot='Pilot sites (A10 = inductive, not catenary)',
  s4a='a  Share of HGV-km captured', s4b='b  Cost per truck-km by diesel scenario', s4c='c  HGV CO₂ with ERS, 2026–2041',
  netkm='ERS network (route-km)', share='Share of HGV-km (%)', ekm='€ per truck-km', diesel='Diesel', ers='ERS (catenary)', bev='BEV + depot/MCS',
  sc={'longrun_low': 'Long-run\nlow', 'longrun_central': 'Long-run\ncentral', 'longrun_high': 'Long-run\nhigh', 'spot_nov2026': 'Spot\nNov 2026'},
  year='Year', mt='Mt CO₂ per year', base23='2023 level (27.9 Mt)', hgv='HGV CO₂ with ERS'),
 'fr': dict(
  f1='Six pôles côtiers candidats de chaleur en cascade (PRM) et leurs systèmes marins (schématique)',
  zones={'atlantic_kelp': 'Laminaires atlantiques (alginate)', 'channel': 'Laminaires saisonnières de Manche (alginate)', 'biscay_mixed': 'Laminaires du golfe de Gascogne (alginate)', 'med_ulva': 'Ulves méditerranéennes (sans alginate)'},
  hub='Pôle candidat', alg='Usines d’alginate existantes', aqua='Ferme piscicole à eau chaude du CNPE de Gravelines (depuis 1991)',
  note='Contours numérisés à la main ; zones et pôles illustratifs, ni sites de réacteurs ni concessions.',
  site_lab={'DKQ': 'Laminaires Manche · bar · miel', 'LEH': 'Laminaires Manche · saumon · saumon fumé au miel', 'BRE': 'Laminaires atlantiques · saumon · saumon fumé au miel',
            'STN': 'Laminaires atlantiques · bar · miel', 'LRO': 'Laminaires Gascogne · maigre/bar · miel', 'FOS': 'Ulves (sans alginate) · dorade · miel'},
  f2a='a  Pôle entier : destination de la chaleur selon la température', f2b='b  Basses températures : condenseur MED, boucle et usagers',
  duty='Puissance thermique moyenne annuelle (MW)', temp='Température (°C)',
  htl='Vapeur HTL (directe)', trim='Appoint électrique HTL', ext='Soutirage BP → MED', effects='Effets MED 65 → 40 °C', cond='Condenseur principal vers la mer',
  vap='Vapeur du dernier effet MED (40 °C)', loop='Boucle de distribution 25 → 36 °C', dT='ΔT', direct='usage direct', hpl='relevage par PAC',
  users={'prawn_RAS': 'Crevettes RAS', 'hatchery': 'Écloserie', 'greenhouse_base': 'Serres (base)', 'greenhouse_peak': 'Serres (pointe)',
         'alginate_drying': 'Séchage alginate', 'smokehouse': 'Fumoir', 'kelp_drying': 'Séchage algues & engrais'},
  f3title='Cascade thermique annuelle du pôle de Brest (GWh par an)', reactor='Chaleur du\nréacteur', elec='Électricité\n(brute)', htlb='Vapeur HTL\n>250 °C',
  trimb='Appoint\nélectrique HTL', medb='Distillation MED\n~70 °C', water='Eau distillée', lowt='Boucle ~36 °C du\ncondenseur MED', condb='Condenseur\nprincipal (mer)',
  hpb='PAC boucle du\ncondenseur', bkb='Secours arrêts\n(chaudières, PAC)', unusedb='Non utilisée / mer', penalty='travail turbine perdu', Mm3='Mm³',
  leg_direct='usage direct de l’eau de boucle', leg_hp='relevée par pompe à chaleur',
  f4a='a  Demande mensuelle basse température à Brest', f4b='b  Usages des 2,0 Mm³ d’eau distillée à Brest', month='Mois', gwh='GWh par mois',
  avail='Chaleur disponible au condenseur MED', m3='milliers de m³ par an',
  wuses={'greenhouse_irrigation': 'Irrigation des serres', 'prawn_RAS_makeup': 'Appoint RAS crevettes', 'hatchery_and_processing': 'Écloserie & transformation',
         'electrolyser_feed': 'Alimentation électrolyseur', 'alginate_extraction': 'Extraction d’alginate', 'demin_sold': 'Eau déminéralisée portuaire (vendue)', 'bulk_sold': 'Vrac (vendu)', 'outage_mains': 'Réseau acheté pendant les arrêts'},
  f5a='a  Valeur consolidée des coproduits par site', f5b='b  Trésorerie relative à « PAC seules »', c20='Cascade, 2,0 Mm³ (chaleur garantie)', crs='Cascade, taille optimale (chaleur garantie)', crsn='Cascade, taille optimale, sans secours (conditionnel)', swro='PAC + OIEM, 2,0 Mm³ (chaleur garantie)', s5='Cascade moins PAC seules à Brest (2,0 Mm³, chaleur garantie)', f5c='c  Rendement premier principe',
  meur='M€ par an', ent={'greenhouse': 'Serres', 'prawn': 'Crevettes', 'finfish_imta': 'Poissons (AMTI)', 'honey': 'Miel', 'honey_smoked_salmon': 'Saumon fumé au miel',
       'residue_meal': 'Farines', 'alginate': 'Alginate', 'fuel_chain_utilities': 'Utilités filière carburant', 'heat_and_water_infrastructure': 'Infrastructures chaleur & eau'},
  bridge={'heat_pump_electricity_avoided_eur': 'Électricité PAC\névitée', 'mains_water_avoided_eur': 'Eau du réseau\névitée', 'water_sales_eur': 'Ventes\nd’eau',
          'turbine_work_lost_eur': 'Travail turbine\nperdu', 'med_pumping_and_distribution_eur': 'Pompage MED\n& boucle', 'med_capital_om_brine_eur': 'Capital MED,\nE&M, saumure',
          'heat_equipment_capital_difference_eur': 'Capital PAC\net chaudières', 'outage_grid_backup_eur': 'Électricité réseau\npendant arrêts', 'water_polishing_eur': 'Affinage\nde l’eau', 'cascade_increment_eur': 'Net'},
  casc='Cascade', hponly='PAC seules', total='Total',
  f6a='a  Azote des poissons capté par les algues co-localisées', f6b='b  Le miel limite le saumon fumé au miel', tN='t N par an', dis='N dissous rejeté', capd='capté par les algues',
  hives='Ruches par pôle', smoked_t='Saumon fumé au miel (t par an)', target='Objectif du fumoir', central='cas central',
  f7a='a  Marge de l’alginate « emballage » à Brest (consolidée)', f7b='b  Seuil de rentabilité par site', f7c='c  Effet climat par kg de plastique remplacé',
  price='Prix de l’alginate emballage (€ par kg)', repl='Carburant de remplacement', pack='emballage seul', comb='avec recettes alimentaires', bekg='€ par kg',
  kgco2='kg CO₂e par kg de plastique', lowc='Carburant\nbas-carbone', foss='Gazole\nfossile', plastic='Plastique évité', algproc='Procédé alginate', fuelgap='Gazole fossile supplémentaire', net='Net',
  s1='Distributions des tirages du modèle (2 000 tirages, {n} paramètres actifs)', s1p=['Valeur nationale des coproduits (M€/an)', 'Cascade optimale − PAC,\nchaleur garantie (M€/an)', 'Cascade 2,0 Mm³ − PAC,\nchaleur garantie (M€/an)', 'Seuil emballage Brest (€/kg)'],
  s2a='a  Chaleur basse température selon la taille MED (Brest)', s2b='b  Apport de la cascade selon la taille MED (Brest)', hpcap='Puissance PAC installée (MW, axe droit)', mw='MW', red='Cascade − PAC, PAC redondantes', nfirm='Cascade − PAC, sans secours (conditionnel)', s6='Cascade moins PAC seules avec chaleur garantie, six sites (M€ par an)', s6a='a  Unités bien dimensionnées (0,9–1,15 Mm³)', s6b='b  Unités de 2,0 Mm³', ghs='Chaleur des serres utilisée directement à 35 °C (%)', pel='Valeur de l’électricité (€/MWh)', vsro='Cascade − (PAC + OIEM) même production', medsize='Distillat MED (Mm³ par an)', gwhy='GWh par an',
  frommed='Condenseur MED', fromhp='PAC boucle du condenseur', unused='Chaleur MED inutilisée', cop_='Valeur des coproduits', inc='Cascade − PAC, chaleur garantie (PAC résiduelles + chaudières)',
  s3='Corridors d’autoroutes électriques (ERS caténaire), schématiques', tier1='Phase 1 (échelle GT1 2030)', tier2='Phase 2 (réseau complet GT1)', pilot='Sites pilotes (A10 = induction, pas caténaire)',
  s4a='a  Part des km-PL captés', s4b='b  Coût par km-PL selon le scénario gazole', s4c='c  CO₂ PL avec ERS, 2026–2041',
  netkm='Réseau ERS (km de route)', share='Part des km-PL (%)', ekm='€ par km-PL', diesel='Diesel', ers='ERS (caténaire)', bev='BEV + dépôt/MCS',
  sc={'longrun_low': 'Long terme\nbas', 'longrun_central': 'Long terme\ncentral', 'longrun_high': 'Long terme\nhaut', 'spot_nov2026': 'Spot\nnov. 2026'},
  year='Année', mt='Mt CO₂ par an', base23='Niveau 2023 (27,9 Mt)', hgv='CO₂ PL avec ERS')}


def fig1(lang):
    t = T[lang]; fig, ax = plt.subplots(figsize=(6.6, 5.9)); base_map(ax)
    zc = {'atlantic_kelp': C[2], 'channel': '#8fd3b8', 'biscay_mixed': C[3], 'med_ulva': C[4]}
    for pts, k in g.MARINE: ax.add_patch(Polygon(pts, fc=zc[k], ec='none', alpha=.55, zorder=2))
    france_on_top(ax)
    off = {'DKQ': (1.0, -.95), 'LEH': (1.7, -1.0), 'BRE': (-.3, 1.05), 'STN': (.9, -.3), 'LRO': (.9, -.6), 'FOS': (-4.0, -1.25)}
    for s in SITES:
        ax.plot(s.lon, s.lat, 'h', ms=9, mfc=C[1], mec='white', zorder=8); dx, dy = off[s.key]
        ax.annotate(f"{s.name}\n{t['site_lab'][s.key]}", (s.lon, s.lat), (s.lon + dx, s.lat + dy), fontsize=5.8, zorder=9, color=INK,
                    bbox=dict(fc='white', ec='#c4c1b8', lw=.4, pad=1.5), arrowprops=dict(arrowstyle='-', color=INK2, lw=.5))
    for name, x, y in g.ALGINATE_INDUSTRY: ax.plot(x, y, 's', ms=4.5, mfc=C[6], mec='white', mew=.6, zorder=8)
    ax.plot(2.13, 51.01, 'D', ms=5, mfc=C[0], mec='white', mew=.6, zorder=8)
    h = [Line2D([], [], marker='h', ls='', ms=8, mfc=C[1], mec='white', label=t['hub'])] + \
        [Patch(fc=zc[k], alpha=.55, label=v) for k, v in t['zones'].items()] + \
        [Line2D([], [], marker='s', ls='', ms=5, mfc=C[6], mec='white', label=t['alg']),
         Line2D([], [], marker='D', ls='', ms=5, mfc=C[0], mec='white', label=t['aqua'])]
    ax.legend(handles=h, loc='upper left', fontsize=5.8, bbox_to_anchor=(0, -.01), ncol=2)
    ax.set_title(t['f1'], fontsize=7.8, loc='left', weight='bold')
    fig.text(.5, -.04, t['note'], ha='center', fontsize=6, color=INK2, style='italic')
    save(fig, lang, 'Figure_1_France_sites_and_marine_systems')


def fig2(lang):
    """Temperature–heat-duty diagram (Brest, annual-average MW)."""
    t = T[lang]; th = m.Inputs().th; c = R['sites']['BRE']['cascade']; md = R['thermal']['med_design']
    MW = lambda gwh: gwh * 1000 / 8760
    fig, axs = plt.subplots(1, 2, figsize=(7.3, 3.4), gridspec_kw=dict(width_ratios=[1.15, 1]))
    ax = axs[0]; x = 0
    def seg(x0, w, T0, T1, col, lab, hatch=None, alpha=.85):
        ax.add_patch(Rectangle((x0, min(T0, T1)), w, max(3, abs(T1 - T0)), fc=col, ec='white', lw=.8, alpha=alpha, hatch=hatch, zorder=3))
        return x0 + w
    d = MW(c['htl_direct_GWh']); tr = MW(c['htl_trim_GWh']); q = MW(c['med_motive_GWh']); cd = MW(c['main_condenser_GWh'])
    x = seg(0, d, 250, 285, C[1], t['htl']); ax.text(x + tr + 1.2, 262, t['htl'], ha='left', fontsize=5.8)
    x2 = seg(x, tr, 285, 330, '#f8d6c4', t['trim'], hatch='///'); ax.text(x2 + 1.2, 312, t['trim'], ha='left', fontsize=5.8)
    x3 = seg(x2 + .6, q, 68, 72, C[0], t['ext']); ax.text(x2 + .6 + q / 2, 84, t['ext'], ha='center', fontsize=5.8)
    n = md['effects']; step = (th.TBT_C - th.T_last_C) / n
    xs = np.linspace(x2 + .6, x3, n + 1)
    for i in range(n): ax.plot([xs[i], xs[i + 1]], [th.TBT_C - i * step] * 2, color=C[2], lw=1.6, zorder=4)
    for i in range(1, n): ax.plot([xs[i]] * 2, [th.TBT_C - (i - 1) * step, th.TBT_C - i * step], color=C[2], lw=1.0, zorder=4)
    ax.text(x2 + .6 + q / 2, 12, t['effects'] + f"\n({n} × {fmt(step, lang)} K, GOR {fmt(md['gor'], lang)})", ha='center', fontsize=5.6, color=INK)
    seg(x3 + .6, cd, 33, 37, '#bdbab2', t['cond']); ax.text(x3 + .6 + cd / 2, 48, t['cond'], ha='center', fontsize=5.8)
    ax.set_xlim(0, x3 + cd + 2); ax.set_ylim(0, 360); ax.set_xlabel(t['duty']); ax.set_ylabel(t['temp'])
    ax.set_title(t['f2a'], fontsize=7.4, loc='left', weight='bold')
    # panel b
    ax = axs[1]
    Qend = MW(c['med_motive_GWh']) * th.end_condenser_fraction
    ax.plot([0, Qend], [th.T_last_C] * 2, color=C[2], lw=2.2, label=t['vap'])
    ax.plot([0, Qend], [th.loop_return_C, th.loop_supply_C], color=C[0], lw=2.2, label=t['loop'])
    ax.annotate('', (Qend * .98, th.loop_supply_C), (Qend * .98, th.T_last_C), arrowprops=dict(arrowstyle='<->', lw=.7, color=INK2))
    ax.text(Qend * .9, (th.loop_supply_C + th.T_last_C) / 2, f"{t['dT']} = {fmt(th.T_last_C - th.loop_supply_C, lang, 0)} K", ha='right', va='center', fontsize=6)
    users = c['per_user']; Ts = {'prawn_RAS': th.T_prawn_C, 'hatchery': th.T_hatch_C, 'greenhouse_base': th.T_gh_base_C, 'greenhouse_peak': th.T_gh_peak_C,
                                'alginate_drying': th.T_dry_C, 'smokehouse': th.T_dry_C, 'kelp_drying': th.T_dry_C}
    x0 = Qend + 1.0
    lab_y = {'hatchery': (-5.5, 'center'), 'prawn_RAS': (-5.5, 'center'), 'greenhouse_base': (2.0, 'center'), 'greenhouse_peak': (2.0, 'center'),
             'alginate_drying': (2.0, 'right'), 'kelp_drying': (6.5, 'center'), 'smokehouse': (2.0, 'left')}
    for i, k in enumerate(['hatchery', 'prawn_RAS', 'greenhouse_base', 'greenhouse_peak', 'alginate_drying', 'kelp_drying', 'smokehouse']):
        u = users[k]; w = MW((u['med_direct'] + u['med_hp'] + u['cond_hp']) / 1000)
        direct = k in ('hatchery', 'prawn_RAS', 'greenhouse_base')
        col = C[2] if direct else C[3]
        ax.add_patch(Rectangle((x0, Ts[k] - 1), max(w, .25), 2, fc=col, ec='white', zorder=3))
        if not direct:
            ax.annotate('', (x0 + w / 2, Ts[k] - 1), (x0 + w / 2, 30), arrowprops=dict(arrowstyle='->', lw=.8, color=C[3]))
        dy, ha = lab_y[k]
        xt = x0 + w / 2 if ha == 'center' else (x0 + w if ha == 'right' else x0)
        ax.text(xt, Ts[k] + dy, f"{t['users'][k]}", ha=ha, fontsize=5.1, va='bottom')
        x0 += w + .3
    ax.set_xlim(0, x0 + .5); ax.set_ylim(10, 80); ax.set_xlabel(t['duty']); ax.set_ylabel(t['temp'])
    h = [Line2D([], [], color=C[2], lw=2.2, label=t['vap']), Line2D([], [], color=C[0], lw=2.2, label=t['loop']),
         Patch(fc=C[2], label=t['direct']), Patch(fc=C[3], label=t['hpl'])]
    ax.legend(handles=h, fontsize=5.6, loc='upper left')
    ax.set_title(t['f2b'], fontsize=7.4, loc='left', weight='bold')
    fig.tight_layout(); save(fig, lang, 'Figure_2_temperature_heat_duty_diagram')


def box(ax, x, y, w, h, txt, fc, val=None, lang='en', tc=INK, fs=6.4):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.004,rounding_size=0.012', fc=fc, ec='white', lw=1.2, zorder=3))
    s = txt if val is None else f'{txt}\n{fmt(val, lang)}'
    ax.text(x + w / 2, y + h / 2, s, ha='center', va='center', fontsize=fs, color=tc, zorder=4, linespacing=1.15)


def arrow(ax, x0, y0, x1, y1, w, col):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>', mutation_scale=7, lw=max(.6, w), color=col, alpha=.75, zorder=2))


def fig3(lang):
    t = T[lang]; h = R['sites']['BRE']['cascade']; u = h['per_user']
    colon = ' : ' if lang == 'fr' else ': '
    fig, ax = plt.subplots(figsize=(7.2, 4.6)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    sc = lambda gwh: .4 + gwh / 40
    E, Hd, Q, Rm = h['gross_elec_GWh'], h['htl_direct_GWh'], h['med_motive_GWh'], h['main_condenser_GWh']
    box(ax, .00, .36, .13, .26, t['reactor'], C[1], h['thermal_GWh'], lang, 'white', 7)
    box(ax, .22, .80, .15, .13, t['elec'], C[0], E, lang, 'white')
    box(ax, .22, .60, .15, .13, t['htlb'], '#f3b28f', Hd, lang)
    box(ax, .22, .38, .15, .14, t['medb'], '#9cc5ec', Q, lang)
    box(ax, .22, .08, .15, .14, t['condb'], '#d9d7d0', Rm, lang)
    for (y, v, col) in ((.865, E, C[0]), (.665, Hd, C[1]), (.45, Q, C[0]), (.15, Rm, MUTED)): arrow(ax, .13, .49, .22, y, sc(v), col)
    box(ax, .44, .80, .17, .10, t['trimb'], '#f8d6c4', h['htl_trim_GWh'], lang); arrow(ax, .37, .86, .44, .85, sc(h['htl_trim_GWh']), C[0])
    box(ax, .44, .58, .17, .12, t['water'] + f"\n{fmt(2.0, lang)} {t['Mm3']}", '#cfe3f6', None, lang); arrow(ax, .37, .47, .44, .63, 1.0, C[0])
    box(ax, .44, .33, .17, .16, t['lowt'], '#b8e3d0', h['med_available_delivered_GWh'], lang); arrow(ax, .37, .44, .44, .41, sc(h['med_available_delivered_GWh']), C[2])
    box(ax, .44, .15, .17, .11, t['hpb'], '#e6e4df', h['lowT_from_condenser_hp_GWh'], lang); arrow(ax, .37, .15, .44, .20, .8, MUTED)
    box(ax, .44, .01, .17, .10, t['bkb'], '#f6c9c9', h['lowT_from_outage_backup_GWh'], lang)
    order = [('prawn_RAS', True), ('hatchery', True), ('greenhouse_base', True), ('greenhouse_peak', False), ('kelp_drying', False), ('alginate_drying', False), ('smokehouse', False)]
    for i, (k, direct) in enumerate(order):
        v = (u[k]['med_direct'] + u[k]['med_hp'] + u[k]['cond_hp'] + sum(u[k]['out_heat']) + sum(u[k]['trip_heat'])) / 1000; y = .86 - i * .105
        box(ax, .70, y, .27, .075, f"{T[lang]['users'][k]}{colon}{fmt(v, lang)}", '#d8f0e5' if direct else '#fde6c2', None, lang, fs=6.2)
        arrow(ax, .61, .41, .70, y + .037, sc((u[k]['med_direct'] + u[k]['med_hp']) / 1000) * .6 + .3, C[2] if direct else C[3])
    box(ax, .70, .02, .27, .075, f"{t['unusedb']}{colon}{fmt(h['med_unused_GWh'], lang)}", '#e6e4df', None, lang, fs=6.2); arrow(ax, .61, .37, .70, .06, .6, MUTED)
    ax.text(.36, .985, t['f3title'], ha='center', fontsize=8, weight='bold', color=INK)
    ax.text(.30, .315, f"−{fmt(h['turbine_penalty_GWh'], lang)} {t['penalty']}", fontsize=5.8, color=INK2, ha='center')
    ax.legend(handles=[Patch(fc='#d8f0e5', label=t['leg_direct']), Patch(fc='#fde6c2', label=t['leg_hp'])], loc='lower left', fontsize=6, bbox_to_anchor=(0, -.02))
    save(fig, lang, 'Figure_3_Brest_heat_cascade')


def fig4(lang):
    t = T[lang]; rows = list(csv.DictReader(open(D / 'v12_monthly_BRE.csv'))); keys = list(t['users'].keys())
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw=dict(width_ratios=[1.45, 1]))
    ax = axs[0]; b = np.zeros(12); x = np.arange(12)
    for i, k in enumerate(keys):
        v = np.array([float(r[k + '_MWh']) for r in rows]) / 1000
        ax.bar(x, v, bottom=b, color=C[i], width=.72, label=t['users'][k], edgecolor=SURF, linewidth=.6); b += v
    av = np.array([float(r['med_available_MWh']) for r in rows]) / 1000
    ax.step(np.r_[x - .5, 11.5], np.r_[av, av[-1]], where='post', color=INK, lw=1.2, ls='--'); ax.text(11.4, av.max() + .25, t['avail'], ha='right', fontsize=6)
    ax.set_xticks(x, list('JFMAMJJASOND')); ax.set_ylabel(t['gwh']); ax.set_title(t['f4a'], fontsize=7.6, loc='left', weight='bold')
    ax.legend(fontsize=5.6, ncol=2, loc='upper center', bbox_to_anchor=(.5, -.12))
    ax = axs[1]; W = R['sites']['BRE']['cascade']['water']; vals = dict(W['uses']); vals['demin_sold'] = W['demin_sold']; vals['bulk_sold'] = W['bulk_sold']
    vals['outage_mains'] = W['outage_mains_m3']
    ks = ['greenhouse_irrigation', 'prawn_RAS_makeup', 'hatchery_and_processing', 'electrolyser_feed', 'alginate_extraction', 'demin_sold', 'bulk_sold', 'outage_mains']
    v = [vals[k] / 1000 for k in ks]
    ax.barh(range(len(ks)), v, color=[C[0]] * 5 + [C[6]] * 2 + [C[7]], height=.62); ax.invert_yaxis()
    ax.set_yticks(range(len(ks)), [t['wuses'][k] for k in ks], fontsize=6.1); ax.set_xlabel(t['m3'])
    for i, vv in enumerate(v): ax.text(vv + 12, i, fmt(vv, lang, 0), va='center', fontsize=6, color=INK2)
    ax.set_xlim(0, max(v) * 1.25); ax.set_title(t['f4b'], fontsize=7.6, loc='left', weight='bold'); ax.grid(axis='y', visible=False)
    fig.tight_layout(); save(fig, lang, 'Figure_4_Brest_monthly_dispatch_and_water')


def fig5(lang):
    t = T[lang]; led = list(csv.DictReader(open(D / 'v12_enterprise_ledger_cascade.csv')))
    fig, axs = plt.subplots(1, 3, figsize=(7.3, 3.1), gridspec_kw=dict(width_ratios=[1.4, 1.35, .8]))
    ax = axs[0]; ents = list(t['ent'].keys()); x = np.arange(len(SITES))
    e0 = {k: R['sites'][k]['energy_only']['enterprises'] for k in SN}
    pos = np.zeros(len(SITES)); neg = np.zeros(len(SITES))
    for j, en in enumerate(ents):
        vals = []
        for s in SITES:
            v = next((float(r['net_eur']) for r in led if r['site'] == s.name and r['enterprise'] == en), 0.0)
            v -= e0[s.key].get(en, {}).get('net_eur', 0.0)
            vals.append(v / 1e6)
        vals = np.array(vals)
        col = C[j % 8] if j < 8 else MUTED
        ax.bar(x, np.where(vals > 0, vals, 0), bottom=pos, color=col, width=.68, label=t['ent'][en], edgecolor=SURF, linewidth=.5); pos += np.where(vals > 0, vals, 0)
        ax.bar(x, np.where(vals < 0, vals, 0), bottom=neg, color=col, width=.68, edgecolor=SURF, linewidth=.5); neg += np.where(vals < 0, vals, 0)
    tot = [R['sites'][s.key]['coproduct_value'] / 1e6 for s in SITES]
    ax.plot(x, tot, 'D', color=INK, ms=4, label=t['total'], zorder=5)
    for i, v in enumerate(tot): ax.text(i, pos[i] + .5, fmt(v, lang), ha='center', fontsize=5.8)
    ax.axhline(0, color=MUTED, lw=.6); ax.set_xticks(x, [s.name.replace('-sur-Mer', '') for s in SITES], fontsize=5.8, rotation=30)
    ax.set_ylim(top=max(pos) + 1.6); ax.set_ylabel(t['meur']); ax.set_title(t['f5a'], fontsize=7.2, loc='left', weight='bold')
    ax.legend(fontsize=4.9, loc='upper center', bbox_to_anchor=(.5, -.25), ncol=3)
    ax = axs[1]; rs = {r['key']: r for r in R['med_rightsizing']}; st = {r['key']: r for r in R['site_table']}
    ser = [(t['c20'], [st[s_.key]['cascade_increment_MEUR'] for s_ in SITES], C[1]), (t['crs'], [rs[s_.key]['cascade_increment_MEUR'] for s_ in SITES], C[2]),
           (t['swro'], [st[s_.key]['swro_increment_MEUR'] for s_ in SITES], C[6])]
    for j_, (lab, vals, col) in enumerate(ser):
        ax.bar(x + (j_ - 1) * .26, vals, width=.25, color=col, label=lab, edgecolor=SURF, linewidth=.4)
    ax.axhline(0, color=INK2, lw=.7); ax.set_xticks(x, [s_.name.replace('-sur-Mer', '') for s_ in SITES], fontsize=5.8, rotation=30)
    ax.set_ylabel(t['meur']); ax.set_title(t['f5b'], fontsize=7.2, loc='left', weight='bold')
    ax.legend(fontsize=5.4, loc='upper center', bbox_to_anchor=(.5, -.25), ncol=1)
    ax = axs[2]; y = np.arange(len(SITES))
    fc = [R['sites'][s.key]['cascade']['first_law'] * 100 for s in SITES]; fh = [R['sites'][s.key]['hp_only']['first_law'] * 100 for s in SITES]
    ax.barh(y - .18, fh, height=.34, color=MUTED, label=t['hponly']); ax.barh(y + .18, fc, height=.34, color=C[0], label=t['casc'])
    ax.set_yticks(y, [s.name.replace('-sur-Mer', '') for s in SITES], fontsize=5.8); ax.invert_yaxis(); ax.set_xlim(35, 62); ax.set_xlabel('%')
    ax.legend(fontsize=5.6, loc='upper center', bbox_to_anchor=(.5, -.3), ncol=1); ax.set_title(t['f5c'], fontsize=7.2, loc='left', weight='bold'); ax.grid(axis='y', visible=False)
    fig.tight_layout(); save(fig, lang, 'Figure_5_consolidated_value_and_cascade_vs_heat_pumps')


def fig6(lang):
    t = T[lang]; fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8), gridspec_kw=dict(width_ratios=[1.3, 1]))
    ax = axs[0]; x = np.arange(len(SITES))
    dis = [R['sites'][s.key]['cascade']['imta']['dissolved_N_t'] for s in SITES]; cap = [R['sites'][s.key]['cascade']['imta']['captured_N_t'] for s in SITES]
    ax.bar(x, dis, color='#cfe3f6', width=.65, label=t['dis']); ax.bar(x, cap, color=C[2], width=.65, label=t['capd'])
    for i in range(len(SITES)):
        ax.text(i, dis[i] + 2, f"{fmt(100 * cap[i] / dis[i], lang, 0)}{' %' if lang == 'fr' else '%'}", ha='center', fontsize=6)
    ax.set_xticks(x, [f"{s.name.replace('-sur-Mer', '')}\n{s.fish.split(' / ')[0]}" for s in SITES], fontsize=5.2)
    ax.set_ylabel(t['tN']); ax.legend(fontsize=6); ax.set_title(t['f6a'], fontsize=7.4, loc='left', weight='bold')
    ax = axs[1]; f = m.Food(); hv = np.arange(100, 1001, 25)
    for key, col in (('BRE', C[1]), ('LEH', C[0])):
        s = next(z for z in SITES if z.key == key)
        sm = [m.honey_salmon(s, m.Food(hives=h))[1]['smoked_t'] for h in hv]
        ax.plot(hv, sm, color=col, lw=2, label=s.name)
        ax.plot(f.hives, R['sites'][key]['cascade']['smoked']['smoked_t'], 'o', ms=5, mfc=col, mec='white')
    ax.axhline(f.smoked_target_t, color=MUTED, ls='--', lw=1); ax.text(110, f.smoked_target_t + 10, t['target'], fontsize=6)
    ax.set_xlabel(t['hives']); ax.set_ylabel(t['smoked_t']); ax.set_ylim(0, 520); ax.legend(fontsize=6, loc='lower right')
    ax.set_title(t['f6b'], fontsize=7.4, loc='left', weight='bold')
    fig.tight_layout(); save(fig, lang, 'Figure_6_IMTA_nitrogen_and_honey')


def fig7(lang):
    t = T[lang]; sw = list(csv.DictReader(open(D / 'v12_alginate_price_sweep_brest.csv')))
    fig, axs = plt.subplots(1, 3, figsize=(7.3, 2.8), gridspec_kw=dict(width_ratios=[1.3, 1, 1]))
    ax = axs[0]
    for i, repl in enumerate(('1.4', '2.0', '2.8')):
        rr = [r for r in sw if abs(float(r['replacement_fuel_eur_l']) - float(repl)) < 1e-9]
        ax.plot([float(r['price_eur_kg']) for r in rr], [float(r['margin_MEUR']) for r in rr], color=C[i], lw=2, label=f"{t['repl']} {fmt(float(repl), lang)} €/L")
        ax.plot(float(rr[0]['breakeven_eur_kg']), 0, 'o', ms=5, mfc=C[i], mec='white')
    ax.axhline(0, color=MUTED, lw=.7); ax.axvspan(3, 7, color='#eeece6', zorder=0)
    ax.set_xlabel(t['price']); ax.set_ylabel(t['meur']); ax.legend(fontsize=5.6, loc='upper left'); ax.set_title(t['f7a'], fontsize=7, loc='left', weight='bold')
    ax = axs[1]; st = [r for r in R['site_table'] if r['alginate_t'] > 0]; y = np.arange(len(st))
    ax.barh(y - .18, [r['alginate_pack_breakeven_eur_kg'] for r in st], height=.34, color=C[1], label=t['pack'])
    ax.barh(y + .18, [r['alginate_food_plus_pack_breakeven_eur_kg'] for r in st], height=.34, color=C[0], label=t['comb'])
    for i, r in enumerate(st): ax.text(r['alginate_pack_breakeven_eur_kg'] + .05, i - .18, fmt(r['alginate_pack_breakeven_eur_kg'], lang, 2), va='center', fontsize=5.6)
    ax.axvline(4.5, color=INK2, ls=':', lw=.8)
    ax.set_yticks(y, [r['site'].replace('-sur-Mer', '') for r in st], fontsize=6); ax.invert_yaxis(); ax.set_xlabel(t['bekg']); ax.set_xlim(0, 5.6)
    ax.legend(fontsize=5.6, loc='upper center', bbox_to_anchor=(.5, -.3), ncol=1); ax.set_title(t['f7b'], fontsize=7, loc='left', weight='bold'); ax.grid(axis='y', visible=False)
    ax = axs[2]; a = m.Alginate(); site = SITES[2]
    plastic = a.plastic_avoided_kgCO2_kg; proc = -a.alg_per_kg_plastic * a.process_kgCO2_kg
    fuel = -a.alg_per_kg_plastic / site.alginate_yield * site.fuel_yield_t_t / .8 * a.diesel_kgCO2_l
    for i, (lab, parts) in enumerate([(t['lowc'], [plastic, proc, 0]), (t['foss'], [plastic, proc, fuel])]):
        pos = neg = 0
        for v, col, nm in zip(parts, (C[2], C[3], C[7]), (t['plastic'], t['algproc'], t['fuelgap'])):
            if v >= 0: ax.bar(i, v, bottom=pos, color=col, width=.5, label=nm if i == 1 else None); pos += v
            else: ax.bar(i, v, bottom=neg, color=col, width=.5, label=nm if i == 1 else None); neg += v
        net = sum(parts); ax.plot([i - .3, i + .3], [net] * 2, color=INK, lw=2); ax.text(i + .32, net, f"{t['net']} {fmt(net, lang, 2)}", va='center', fontsize=5.8)
    ax.axhline(0, color=MUTED, lw=.7); ax.set_xticks([0, 1], [t['lowc'], t['foss']], fontsize=5.6); ax.set_xlim(-.6, 1.95); ax.set_ylim(-4.6, 4.2)
    ax.set_ylabel(t['kgco2']); ax.legend(fontsize=5.4, loc='lower left'); ax.set_title(t['f7c'], fontsize=7, loc='left', weight='bold')
    fig.tight_layout(); save(fig, lang, 'Figure_7_alginate_breakeven_and_climate')


def figS1(lang):
    t = T[lang]; mc = list(csv.DictReader(open(D / 'v12_monte_carlo.csv')))
    keys = ['coproduct_value_MEUR', 'rightsized_increment_MEUR', 'cascade_increment_MEUR', 'brest_pack_breakeven_eur_kg']
    fig, axs = plt.subplots(1, 4, figsize=(7.3, 2.1))
    for i, (ax, k) in enumerate(zip(axs, keys)):
        v = np.array([float(r[k]) for r in mc]); ax.hist(v, bins=40, color=C[0], edgecolor=SURF, linewidth=.3)
        med = np.median(v)
        for p in np.percentile(v, [5, 95]): ax.axvline(p, color=MUTED, lw=.7, ls=':')
        ax.axvline(med, color=INK, lw=1)
        if k in ('rightsized_increment_MEUR', 'cascade_increment_MEUR'): ax.axvline(0, color=C[7], lw=1)
        ax.set_title(t['s1p'][i], fontsize=6.4, loc='left'); ax.set_yticks([])
    fig.suptitle(t['s1'].format(n=len(R['monte_carlo']['inputs'])), fontsize=7.6, weight='bold', x=.01, ha='left'); fig.tight_layout(); save(fig, lang, 'Supplementary_Figure_S1_Monte_Carlo')


def figS2(lang):
    t = T[lang]; sw = list(csv.DictReader(open(D / 'v12_med_size_sweep_brest.csv'))); x = np.array([float(r['med_Mm3']) for r in sw])
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    ax = axs[0]
    a = np.array([float(r['lowT_from_med_GWh']) for r in sw]); b = np.array([float(r['from_cond_hp_GWh']) for r in sw])
    ax.stackplot(x, a, b, colors=[C[2], C[3]], labels=[t['frommed'], t['fromhp']], alpha=.9)
    ax.plot(x, [float(r['unused_GWh']) for r in sw], '-', color=INK2, lw=1.4, label=t['unused'])
    ax2 = ax.twinx(); ax2.plot(x, [float(r['hp_capacity_MW']) for r in sw], '--', color=C[6], lw=1.4, label=t['hpcap']); ax2.set_ylabel(t['mw']); ax2.set_ylim(0, 50); ax2.grid(False)
    ax2.spines['right'].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=5.4, loc='upper center', bbox_to_anchor=(.5, -.3), ncol=2)
    ax.set_xlabel(t['medsize']); ax.set_ylabel(t['gwhy']); ax.set_title(t['s2a'], fontsize=7.4, loc='left', weight='bold')
    ax = axs[1]
    ax.plot(x, [float(r['cascade_increment_MEUR']) for r in sw], '-', color=C[1], lw=2, label=t['inc'])
    ax.plot(x, [float(r['cascade_increment_redundant_hp_MEUR']) for r in sw], '--', color=C[7], lw=1.6, label=t['red'])
    ax.plot(x, [float(r['cascade_vs_swro_MEUR']) for r in sw], ':', color=C[6], lw=1.8, label=t['vsro'])
    ax.axhline(0, color=INK2, lw=.7); ax.set_xlabel(t['medsize']); ax.set_ylabel(t['meur'])
    ax.legend(fontsize=5.4, loc='upper center', bbox_to_anchor=(.5, -.3), ncol=1)
    ax.set_title(t['s2b'], fontsize=7.4, loc='left', weight='bold')
    fig.tight_layout(); save(fig, lang, 'Supplementary_Figure_S2_MED_sizing')


def figS5(lang):
    t = T[lang]; br = next(r for r in csv.DictReader(open(D / 'v12_cascade_vs_hp_only_bridge.csv')) if r['site'] == 'Brest')
    fig, ax = plt.subplots(figsize=(5.2, 3.0)); ks = list(t['bridge'].keys()); cum = 0
    for i, k in enumerate(ks):
        v = float(br[k]) / 1e6
        if k == 'cascade_increment_eur':
            ax.bar(i, v, color=INK2, width=.65); ax.text(i, v - .08 if v < 0 else v + .05, fmt(v, lang, 2), ha='center', va='top' if v < 0 else 'bottom', fontsize=6.4)
        else:
            ax.bar(i, v, bottom=cum, color=C[2] if v >= 0 else C[7], width=.65); ax.text(i, cum + v + (.05 if v >= 0 else -.05), fmt(v, lang, 2), ha='center', va='bottom' if v >= 0 else 'top', fontsize=6)
            cum += v
    ax.axhline(0, color=MUTED, lw=.6); ax.set_xticks(range(len(ks)), [t['bridge'][k] for k in ks], fontsize=5.8, rotation=90); ax.set_ylim(-1.0, 4.4)
    ax.set_ylabel(t['meur']); ax.set_title(t['s5'], fontsize=7.6, loc='left', weight='bold')
    fig.tight_layout(); save(fig, lang, 'Supplementary_Figure_S5_Brest_bridge')


def figS6(lang):
    t = T[lang]; g2 = list(csv.DictReader(open(D / 'v12_sensitivity_gh_share_x_electricity.csv')))
    gs = sorted({float(r['gh_direct_share']) for r in g2}); pe = sorted({float(r['electricity_eur_MWh']) for r in g2})
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('div', [C[7], '#f6f4ef', C[0]])
    vals_all = [float(r[k]) for r in g2 for k in ('rightsized_firm_MEUR', 'full_size_MEUR')]
    lim = max(abs(min(vals_all)), abs(max(vals_all))); norm = TwoSlopeNorm(0, -lim, lim)
    for ax, key, title in ((axs[0], 'rightsized_firm_MEUR', t['s6a']), (axs[1], 'full_size_MEUR', t['s6b'])):
        Z = np.array([[float(next(r for r in g2 if float(r['gh_direct_share']) == a and float(r['electricity_eur_MWh']) == b)[key]) for b in pe] for a in gs])
        ax.imshow(Z, cmap=cmap, norm=norm, aspect='auto', origin='lower')
        for i in range(len(gs)):
            for j in range(len(pe)):
                ax.text(j, i, fmt(Z[i, j], lang, 2), ha='center', va='center', fontsize=5.0, color=INK)
        ax.set_xticks(range(len(pe)), [f'{int(v)}' for v in pe], fontsize=6); ax.set_yticks(range(len(gs)), [f'{int(round(v * 100))}' for v in gs], fontsize=6)
        ax.set_xlabel(t['pel']); ax.set_ylabel(t['ghs']); ax.grid(False); ax.set_title(title, fontsize=7.2, loc='left', weight='bold')
        j0 = pe.index(105.0); i0 = gs.index(0.55); ax.add_patch(Rectangle((j0 - .5, i0 - .5), 1, 1, fill=False, ec=INK, lw=1.2))
    fig.suptitle(t['s6'], fontsize=7.6, weight='bold', x=.01, ha='left'); fig.tight_layout(); save(fig, lang, 'Supplementary_Figure_S6_sensitivity_gh_share_x_electricity')


CORRIDORS = None


def figS3(lang):
    import importlib.util
    spec = importlib.util.spec_from_file_location('corr', ROOT / 'model' / 'ers_corridors.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    t = T[lang]; fig, ax = plt.subplots(figsize=(5.8, 5.4)); base_map(ax); france_on_top(ax)
    for tier, cs in mod.CORRIDORS.items():
        for name, pts in cs.items():
            xs, ys = zip(*pts); ax.plot(xs, ys, color=C[0] if tier == 1 else C[4], lw=2.2 if tier == 1 else 1.6, solid_capstyle='round', zorder=6)
    for n, (x, y) in g.CITIES.items():
        ax.plot(x, y, 'o', ms=3, mfc='white', mec=INK2, mew=.7, zorder=7); ax.text(x + .17, y + .1, n, fontsize=5.8, color=INK2, zorder=8)
    for name, x, y in g.ERS_PILOTS: ax.plot(x, y, '*', ms=9, mfc=C[3], mec=INK, mew=.5, zorder=9)
    for s in SITES: ax.plot(s.lon, s.lat, 'h', ms=6, mfc=C[1], mec='white', mew=.8, zorder=8)
    h = [Line2D([], [], color=C[0], lw=2.2, label=t['tier1']), Line2D([], [], color=C[4], lw=1.6, label=t['tier2']),
         Line2D([], [], marker='*', ls='', ms=8, mfc=C[3], mec=INK, mew=.5, label=t['pilot']), Line2D([], [], marker='h', ls='', ms=6, mfc=C[1], mec='white', label=T[lang]['hub'])]
    ax.legend(handles=h, loc='upper left', fontsize=5.8, bbox_to_anchor=(0, -.01), ncol=2)
    ax.set_title(t['s3'], fontsize=7.6, loc='left', weight='bold')
    fig.text(.5, .0, t['note'], ha='center', fontsize=6, color=INK2, style='italic')
    save(fig, lang, 'Supplementary_Figure_S3_ERS_corridor_map')


def figS4(lang):
    t = T[lang]; cv = list(csv.DictReader(open(D / 'v12_ers_network_curve.csv'))); tr = list(csv.DictReader(open(D / 'v12_ers_transition.csv')))
    fig, axs = plt.subplots(1, 3, figsize=(7.3, 2.8))
    ax = axs[0]; km = [float(r['network_km']) for r in cv]
    ax.plot(km, [100 * float(r['capture_share']) for r in cv], color=C[0], lw=2)
    for k in (4900, 8850):
        cs = m.ers_capture(m.ERS(), k); ax.plot(k, 100 * cs, 'o', ms=5, mfc=C[0], mec='white')
        ax.text(k + 250, 100 * cs - 7, f"{fmt(k, lang, 0)} km", fontsize=5.8, color=INK2)
    ax.set_xlabel(t['netkm']); ax.set_ylabel(t['share']); ax.set_ylim(0, 60); ax.set_title(t['s4a'], fontsize=7.2, loc='left', weight='bold')
    ax = axs[1]; cases = ['longrun_low', 'longrun_central', 'longrun_high', 'spot_nov2026']; x = np.arange(len(cases))
    for j, (k, col, lab) in enumerate((('cost_diesel_eur_vkm', MUTED, t['diesel']), ('cost_ers_eur_vkm', C[0], t['ers']), ('cost_bev_mcs_eur_vkm', C[2], t['bev']))):
        ax.bar(x + (j - 1) * .26, [R['ers'][c][k] for c in cases], width=.24, color=col, label=lab)
    ax.set_xticks(x, [t['sc'][c] for c in cases], fontsize=5.6); ax.set_ylabel(t['ekm']); ax.legend(fontsize=5.4, loc='upper center', ncol=3, columnspacing=.6, handlelength=1); ax.set_ylim(0, .78)
    ax.set_title(t['s4b'], fontsize=7.2, loc='left', weight='bold')
    ax = axs[2]; yrs = [int(r['year']) for r in tr]; v = [float(r['hgv_co2_Mt']) for r in tr]
    ax.plot(yrs, v, color=C[1], lw=2, label=t['hgv']); ax.axhline(27.9, color=MUTED, ls='--', lw=1, label=t['base23'])
    ax.fill_between(yrs, v, 27.9, color=C[2], alpha=.25); ax.set_ylim(0, 32); ax.set_xlabel(t['year']); ax.set_ylabel(t['mt']); ax.legend(fontsize=5.8, loc='lower left')
    ax.set_title(t['s4c'], fontsize=7.2, loc='left', weight='bold')
    fig.tight_layout(); save(fig, lang, 'Supplementary_Figure_S4_ERS_economics')


if __name__ == '__main__':
    for lang in ('en', 'fr'):
        for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, figS1, figS2, figS3, figS4, figS5, figS6):
            f(lang)
    print('figures written')
