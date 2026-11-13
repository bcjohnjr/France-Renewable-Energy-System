"""Fig. 9 (EN and FR): the Grid Harvester (side and top views; artwork P. Valdés Bacallao) and the turn-loss geometry of
the companion Spanish study (conventional vessel vs Grid Harvester head). Turn losses are recomputed here and written to
data/v19_grid_harvester_turns.json; the panel text of the French figure is redrawn in French."""
import sys, json
from math import pi
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt
from PIL import Image
import build_figures_v12 as F

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / 'data' / 'artwork'
CYCLE_M2 = 14_400.0


def turns(w_cv=10.0, n_cv=10, head_m=6.0, span_m=100.0):
    """Area missed in turns (Spanish study geometry): conventional 10-m vessel, 60 m x 240 m field, 10 x 90-degree turns;
    Grid Harvester 6-m head, 100-m span, 24 laps and 23 x 180-degree turns per 1.44-ha cycle."""
    conv = n_cv * (1 - pi / 4) * w_cv ** 2
    r = head_m / 2; laps = round(CYCLE_M2 / span_m / head_m); nt = laps - 1
    out = dict(cycle_m2=CYCLE_M2, conventional=dict(width_m=w_cv, turns=n_cv, missed_m2=conv, missed_pct=100 * conv / CYCLE_M2),
               grid=dict(head_m=head_m, span_m=span_m, laps=laps, turns=nt))
    for mode, miss, twice in (('forward', 2 * (4 - pi), 8 - 2 * (4 - pi)), ('in_place', 2 - pi / 2, 2.0)):
        out['grid'][mode] = dict(missed_m2=nt * miss * r * r, missed_pct=100 * nt * miss * r * r / CYCLE_M2, lmm_twice_pct=100 * nt * twice * r * r / CYCLE_M2)
    return out


T = turns()
(ROOT / 'data' / 'v19_grid_harvester_turns.json').write_text(json.dumps(T, indent=1))

LAB = dict(en=dict(a='a  Grid Harvester, side view', b='b  Grid Harvester, top view with the path of the harvesting head'),
           fr=dict(a='a  Grid Harvester, vue de côté', b='b  Grid Harvester, vue de dessus et trajet de la tête de récolte',
                   c='c  Navire classique', d='d  Navire classique, virage à 90°', e='e  Grid Harvester, tête virant en avançant',
                   f='f  Grid Harvester, tête virant sur place'))


def fr_geometry():
    """French version of the turn-geometry panel: English titles and notes masked and redrawn in French."""
    im = Image.open(ART / 'grid_harvester_turn_geometry_es.png').convert('RGB'); W, H = im.size
    fig = plt.figure(figsize=(W / 300, H / 300), dpi=300); ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(im); ax.set_axis_off()
    wipe = lambda x0, y0, x1, y1: ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc='white', ec='none'))
    for box in ((60, 0, 520, 72), (790, 0, 1420, 72), (560, 335, 1560, 405), (570, 690, 1300, 760), (1350, 100, W, 260), (1350, 430, W, 600), (1350, 790, W, 960)):
        wipe(*box)
    c, g = T['conventional'], T['grid']; fw, ip = g['forward'], g['in_place']
    f_ = lambda x, d=1: f'{x:,.{d}f}'.replace(',', ' ').replace('.', ',')
    kw = dict(fontsize=8.6, weight='bold', va='center', ha='left')
    ax.text(88, 42, LAB['fr']['c'], **kw); ax.text(818, 42, LAB['fr']['d'], **kw); ax.text(574, 372, LAB['fr']['e'], **kw); ax.text(584, 727, LAB['fr']['f'], **kw)
    kn = dict(fontsize=6.4, va='center', ha='left', color='#444444', linespacing=1.5)
    ax.text(1380, 180, f"Manque par virage à 90° : (1 − π/4)R², R = largeur du navire\n{c['turns']} virages, navire de {f_(c['width_m'], 0)} m, 1,44 ha\nManque : {f_(c['missed_m2'], 0)} m² ({f_(c['missed_pct'])} %)", **kn)
    ax.text(1380, 515, f"Manque par virage à 180° : 2(4 − π)R²\n{g['turns']} virages, tête de {f_(g['head_m'], 0)} m, 1,44 ha\nManque : {f_(fw['missed_m2'], 0)} m² ({f_(fw['missed_pct'])} %)\nAvec LMM : {f_(fw['lmm_twice_pct'])} % récolté deux fois", **kn)
    ax.text(1380, 875, f"Manque par virage à 180° : (2 − π/2)R²\n{g['turns']} virages, tête de {f_(g['head_m'], 0)} m, 1,44 ha\nManque : {f_(ip['missed_m2'], 0)} m² ({f_(ip['missed_pct'])} %)\nAvec LMM : {f_(ip['lmm_twice_pct'])} % récolté deux fois", **kn)
    ax.set_xlim(0, W); ax.set_ylim(H, 0)
    fig.canvas.draw(); arr = Image.frombuffer('RGBA', fig.canvas.get_width_height(), fig.canvas.buffer_rgba()).convert('RGB'); plt.close(fig)
    return arr


def build(lang):
    side = Image.open(ART / 'grid_harvester_side.jpg').convert('RGB'); top = Image.open(ART / 'grid_harvester_top.jpg').convert('RGB')
    geo = Image.open(ART / 'grid_harvester_turn_geometry_es.png').convert('RGB') if lang == 'en' else fr_geometry()
    W = 7.09; hr = W / 2 / (side.size[0] / side.size[1]); hb = W / (geo.size[0] / geo.size[1])
    fig = plt.figure(figsize=(W, hr + hb + .45))
    gs = fig.add_gridspec(2, 2, height_ratios=[hr, hb], hspace=.10, wspace=.03)
    for k, (img, spec) in enumerate(((side, gs[0, 0]), (top, gs[0, 1]))):
        ax = fig.add_subplot(spec); ax.imshow(img, interpolation='lanczos'); ax.set_axis_off()
        ax.set_title(LAB[lang]['ab'[k]], fontsize=7.2, weight='bold', loc='left')
    ax = fig.add_subplot(gs[1, :]); ax.imshow(geo, interpolation='lanczos'); ax.set_axis_off()
    F.save(fig, lang, 'Figure_9_Grid_Harvester')


if __name__ == '__main__':
    for lang in ('en', 'fr'): build(lang)
    print('Fig. 9 Grid Harvester written;', json.dumps({k: round(v['missed_pct'], 2) for k, v in [('conventional', T['conventional']), ('forward', T['grid']['forward']), ('in_place', T['grid']['in_place'])]}))
