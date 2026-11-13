# SMRs and offshore wind for seaweed fuel, food and electric freight in France — model and data

Code and data for: J.K. Bily, C. Pahl, P. Valdés Bacallao, *Small modular reactors and offshore wind for seaweed fuel, food and electric freight in France: six coastal hubs, the electrification–liquid-fuel sweet spot and a transition to 2041* (submitted to Research & Design of Nuclear Engineering).

Three models. `france_v12.py` is the monthly hub model: reactor heat cascade through seawater distillation to greenhouses, prawns, fish co-located with seaweed, honey-smoked salmon and alginate, compared with heat pumps and reverse osmosis on consolidated accounts with firm heat (387 checks). `system_v14.py` reuses it to cost kelp drop-in fuel under SMR, offshore-wind and combined supply with turbine-anchored farms, a renewable-powered Grid Harvester and utility drones, and the national electric motorways and transport CO₂ (185 checks, including the hourly ERA5 wind contract of `weather_v17.py`). `sweetspot_v19.py` finds the national cost-minimising split between electrification and liquid fuel (electric-motorway length and the batteries of regional and long-haul hybrid trucks), with a linear programme that allocates waste-lipid HEFA, kelp HTL fuel, certified low-carbon (nuclear/grid) e-fuel and hourly-matched RFNBO e-fuel to jet, marine, road and export under jet-fraction limits, the ReFuelEU SAF and synthetic minima (Annex I annual minima and period averages) and the FuelEU intensity target; it ranks the levers on liquid-fuel price and builds a 2027–2041 transition with a cost-optimised kelp-hub build and the electricity and electrolyser capacity it implies (131 checks).

## Layout
```
model/   france_v12.py, test_v12.py, build_figures_v12.py, system_v14.py, test_system_v14.py, build_figures_system_v14.py,
         weather_v17.py, sweetspot_v19.py, test_sweetspot_v19.py, build_figures_sweetspot_v19.py,
         fetch_weather_v16.py (optional: re-downloads the ERA5 data in data/weather/; needs internet),
         france_model.py (underlying reactor and fuel-chain energy model), geo_france.py, ers_corridors.py
build/   content_v20.py, build_docs_v20.py, make_docx.js (manuscript and SI generation; needs Node docx and LibreOffice)
data/    all outputs (v12_* hub model, v14_* system extension, v19_* national model; v17_wind_contracts = hourly wind contracts); data/weather/ = ERA5 hourly inputs
qa/      test logs
```

## Reproduce (Python ≥ 3.11 with numpy, scipy, matplotlib, Pillow; no network; about 3 minutes; run from the repository root)
```
python -I model/france_v12.py && python -I model/test_v12.py && python -I model/build_figures_v12.py
python -I model/system_v14.py && python -I model/test_system_v14.py && python -I model/build_figures_system_v14.py
python -I model/sweetspot_v19.py && python -I model/test_sweetspot_v19.py && python -I model/build_figures_sweetspot_v19.py
python -I model/build_figure_grid_harvester.py   # Fig. 9 Grid Harvester (artwork in data/artwork/)
python -I model/grid_harvester_engineering.py    # Note S10, Table S17
python -I model/test_grid_harvester.py           # 17 checks
```
Outputs are byte-identical to the files in `data/`.

## Notes
Weather inputs: ERA5 hourly reanalysis (Copernicus Climate Change Service / ECMWF; Hersbach et al. 2020) served by the Open-Meteo Historical Weather API, CC BY 4.0, downloaded 12 November 2026 with model/fetch_weather_v16.py.
Seaweed farm-gate cost, the waste-lipid and biogenic-CO₂ caps, the off-wire leg-length model, the transition ramp rates, the share of moorings turbine foundations replace, site wind contract prices, harvester and drone performance, sea temperatures and the outage schedule are screening assumptions, not measurements.

## Licence and citation
Code: MIT. Data, figures and text: CC BY 4.0 (see LICENSE). An archived release with a Zenodo DOI will be created on acceptance; until then cite the article and this repository (CITATION.cff).
