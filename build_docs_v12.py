"""Build V12 EN and FR manuscripts, SI, cover letters and responses (.docx via docx-js, .pdf via LibreOffice)."""
import json, subprocess, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import content_v12 as C

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build' / 'docs'; OUT.mkdir(parents=True, exist_ok=True)
SPEC = ROOT / 'build' / 'specs'; SPEC.mkdir(exist_ok=True)


def fig_block(lang, stem, caption, embed, new_page=False):
    b = dict(kind='figure', caption=caption, newPage=new_page)
    if embed:
        p = ROOT / 'figures' / lang / f'{stem}.png'; w, h = Image.open(p).size
        b.update(path=str(p), w=w / 300 * 96, h=h / 300 * 96)
    return b


def render(spec, name):
    sp = SPEC / f'{name}.json'; sp.write_text(json.dumps(spec, ensure_ascii=False), encoding='utf8')
    docx = OUT / f'{name}.docx'
    subprocess.run(['node', str(ROOT / 'build' / 'make_docx.js'), str(sp), str(docx)], check=True, capture_output=True)
    subprocess.run(['zip', '-d', str(docx), '*/'], capture_output=True)
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(OUT), str(docx)], check=True, capture_output=True)


NAMES = {'en': dict(ms='Manuscript_RDNE_France_SMR_Cascaded_Heat_EN', msfig='Manuscript_RDNE_France_SMR_Cascaded_Heat_EN_reading_copy_with_figures',
                    si='Supplementary_Information_EN', cl='Cover_Letter_RDNE_EN', rr='Response_to_Referee_EN', figcap='Figure captions'),
         'fr': dict(ms='Manuscrit_RDNE_France_PRM_Chaleur_Cascade_FR', msfig='Manuscrit_RDNE_France_PRM_Chaleur_Cascade_FR_copie_de_lecture_avec_figures',
                    si='Informations_supplementaires_FR', cl='Lettre_de_presentation_RDNE_FR', rr='Reponse_au_relecteur_FR', figcap='Légendes des figures')}


def build(lang):
    nm = NAMES[lang]; B, tables, figs, cite = C.manuscript(lang)
    for embed in (False, True):
        blocks = list(B)
        for t in tables: blocks.append(dict(kind='table', newPage=True, **t))
        blocks += [dict(kind='pagebreak'), dict(kind='h1', text=nm['figcap'])]
        for j, (stem, cap) in enumerate(figs): blocks.append(fig_block(lang, stem, cap, embed, new_page=embed and j > 0))
        render(dict(blocks=blocks, double=not embed, line=300, lineNumbers=not embed, figWidthCm=16, tableSize=18, title=B[1]['text']), nm['msfig'] if embed else nm['ms'])
    si = [fig_block(lang, b['file'], b['caption'], True) if b['kind'] == 'figure' else b for b in C.si(lang)]
    render(dict(blocks=si, line=276, size=22, tableSize=17, figWidthCm=16, title='Supplementary Information'), nm['si'])
    render(dict(blocks=[dict(kind=k, text=t) for k, t in C.cover(lang)], font='Arial', size=21, line=276, title='Cover letter'), nm['cl'])
    render(dict(blocks=C.response(lang), font='Arial', size=21, line=276, title='Response to referee'), nm['rr'])
    print(lang, 'done; references', len(cite.order))


if __name__ == '__main__':
    for lang in ('en', 'fr'): build(lang)
