# Cascaded heat from small modular reactors for desalination, aquaculture and food production in France — model and data

Code and data for: J.K. Bily, C. Pahl, P. Valdés Bacallao, *Cascaded heat utilisation from small modular reactors for desalination, aquaculture and food production: a techno-economic assessment for France* (submitted to Research & Design of Nuclear Engineering).

A monthly screening model of six French coastal hubs. It compares a multi-effect-distillation (MED) heat cascade with heat pumps on the reactor's main condenser, with purchased water and with seawater reverse osmosis. All scenarios are on consolidated accounts without heat credits, with heat kept firm and water bought in during reactor and distillation outages. It includes 387 consistency tests and a 2,000-draw Monte Carlo analysis.

## Layout
```
model/   france_v12.py (model), test_v12.py (387 checks), build_figures_v12.py (EN/FR figures),
         france_model.py (underlying reactor and fuel-chain energy model), geo_france.py, ers_corridors.py
build/   content_v12.py, build_docs_v12.py, make_docx.js (manuscript and SI generation; needs Node docx and LibreOffice)
data/    all outputs: v12_results.json, site summary, ledgers, bridge, monthly dispatch, MED sweeps, right-sizing,
         2-D sensitivity, ERS cases, Monte Carlo draws
qa/      test log
```

## Reproduce (Python ≥ 3.11 with numpy, matplotlib, Pillow; no network; about 3 minutes)
```
python -I model/france_v12.py      # regenerates data/
python -I model/test_v12.py        # 387/387 checks
python -I model/build_figures_v12.py
```
Run the commands from the repository root. Outputs are byte-identical to the files in `data/`.

## Notes
Sea temperatures, greenhouse climate factors and the outage schedule are illustrative screening inputs, not site measurements. The maps are hand-digitised and schematic.

## Licence and citation
Code: MIT. Data, figures and text: CC BY 4.0 (see LICENSE). An archived release with a Zenodo DOI will be created on acceptance; until then please cite the article and this repository (see CITATION.cff).
