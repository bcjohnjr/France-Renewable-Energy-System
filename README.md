# France V20.2 — SMR cogeneration hubs, offshore wind, kelp fuel and France's transport system (code and data)

Code and data for *Small modular reactors as the firm heat and power source of French coastal fuel-and-food hubs*
(submitted to Research & Design of Nuclear Engineering). **Everything is in this one flat directory** — no subfolders are
needed; every script reads its inputs from, and writes its outputs to, the directory it sits in.

## Requirements
Python ≥ 3.11 with `numpy`, `scipy`, `matplotlib`, `Pillow` (see `requirements.txt`). No network.
Optional, only to rebuild the manuscript: Node.js with the `docx` package, and LibreOffice.

## Reproduce (about 3 minutes; run from this directory)
```
python -B -I france_v12.py && python -B -I test_v12.py && python -B -I build_figures_v12.py               # hub model, 387 checks
python -B -I system_v14.py && python -B -I test_system_v14.py && python -B -I build_figures_system_v14.py # wind, kelp, drones, freight, 185 checks
python -B -I sweetspot_v19.py && python -B -I test_sweetspot_v19.py && python -B -I build_figures_sweetspot_v19.py  # national model, 131 checks
python -B -I build_figure_grid_harvester.py                                                         # Fig. 9 Grid Harvester
python -B -I grid_harvester_engineering.py && python -B -I test_grid_harvester.py                      # Note S10, Table S17, 17 checks
python -B -I build_docs_v20.py                                                                      # optional: manuscript and SI (Node + LibreOffice)
```
Numerical outputs (`v12_*`, `v14_*`, `v17_*`, `v19_*`, `v20_*`) are regenerated in place and match the files shipped here
(byte-identical on our platform; floating-point-level differences elsewhere). Figures are written to `figures/en` and
`figures/fr` and documents to `docs/`; these folders are created at run time and are not part of the repository.

## Files
| Group | Files |
|---|---|
| Hub model | `france_v12.py`, `test_v12.py`, `build_figures_v12.py`, `ers_corridors.py`, `geo_france.py`, `france_model.py` (archived earlier model, used by the hub model for shared inputs) |
| System extension | `system_v14.py`, `test_system_v14.py`, `build_figures_system_v14.py`, `weather_v17.py` |
| National model | `sweetspot_v19.py`, `test_sweetspot_v19.py`, `build_figures_sweetspot_v19.py` |
| Grid Harvester | `build_figure_grid_harvester.py`, `grid_harvester_engineering.py`, `test_grid_harvester.py`; artwork `grid_harvester_side.jpg`, `grid_harvester_top.jpg`, `grid_harvester_turn_geometry_es.png` (P. Valdés Bacallao) |
| Weather inputs | `hourly_{BRE,DKQ,FOS,LEH,LRO,STN}_v16.csv.gz`, `weather_summary_v16.json`, `cf_*_v16.csv`; `fetch_weather_v16.py` re-downloads them (optional; internet) |
| Outputs | `v12_*` hub model, `v14_*` system extension, `v17_wind_contracts_by_site.csv`, `v19_*` national model, `v20_grid_harvester_engineering.json` |
| Test logs | `test_log.txt`, `test_system_log.txt`, `test_sweetspot_v19_log.txt`, `test_grid_harvester_log.txt` (720/720 checks) |
| Manuscript build | `content_v20.py`, `build_docs_v20.py`, `make_docx.js` |

Weather inputs: ERA5 hourly reanalysis (Copernicus Climate Change Service / ECMWF; Hersbach et al. 2020) served by the
Open-Meteo Historical Weather API, CC BY 4.0, downloaded 12 November 2026 with `fetch_weather_v16.py`.

Licences: code MIT (`LICENSE`); data, figures and artwork CC BY 4.0. Citation: `CITATION.cff`.
