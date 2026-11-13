# France V20.2 — SMRs and offshore wind for seaweed fuel, food and electric freight (EN + FR package)
**Target journal:** Research & Design of Nuclear Engineering (RDNE), EDP Sciences, Les Ulis — no publication charges in the launch period (get written confirmation for a 2027 acceptance).
**Title:** Small modular reactors and offshore wind for seaweed fuel, food and electric freight in France: six coastal hubs, the electrification–liquid-fuel sweet spot and a transition to 2041
**Authors:** Jonathan Karl Bily (corresponding), Christoph Pahl, Patricia Valdés Bacallao

V20.2 makes the repository **flat**: all 76 code, data, weather, artwork and log files sit in one directory (`Repository/`, no subfolders) and every script reads and writes there, so it can be uploaded to GitHub as is. Results, figures and manuscript are unchanged (720/720 checks from a flat copy; outputs byte-identical); only Table S6 and the SI file references changed.

V20.1 answered the referee report on V20: new **Supplementary Note S10 and Table S17** derive the Grid Harvester's throughput (416.7 t/h from head width × speed × crop per pass), hose hydraulics, pump power, drag and energy ratio (2.6 central; 0.3–3.9 across assumptions) from first principles (`model/grid_harvester_engineering.py`, 17 checks), and show that the 16% fleet-fuel saving rests on electrified support craft and moves fuel cost by under €0.01/L. The introduction makes the reactor the common thread; keywords cut to six; cover letter dated 13 November.

V20 made the corresponding author's revisions: the **Grid Harvester** is restored as new **Fig. 9** (side and top views by P. Valdés Bacallao, and the turn-loss geometry of the Spanish study, recomputed in `model/build_figure_grid_harvester.py`), with its description in Section 2.6; former Figs 9–12 are now Figs 10–13. All paragraphs, captions and references are justified, and the title, article type and author information are centred. The AI tool is named Artificial Inventor/Synthetic Scientist V63. The code and data are on GitHub. Results are unchanged.

V19.1 (text only) had answered the referee report on V19, which found the science ready to submit: the data-availability statement and Table S6 now cite release v19.0 (create that tag when you upload `Repository/`), Table S6 lists scipy, and the cover letter centres the scope on SMR cogeneration. Results are unchanged.

V19 answers the informal referee report on V18:
- **Synthetic aviation fuel.** Certified low-carbon e-fuel from reactor power (≥70% life-cycle savings) now counts toward both the SAF and the synthetic minima in the central case, as ReFuelEU allows; RFNBO-only procurement is an alternative scenario (+€0.57 bn a year in 2041; synthetic premium €1.51/L).
- **2030–2034 schedule.** ReFuelEU Annex I annual minima and period averages are implemented exactly (least-cost path back-loads within each period).
- **Kelp hubs.** Early hubs pay wind-only costs until the SMR arrives in 2035; every build from 0 to 36 hubs is scanned under two commissioning schedules. The cost surface is nearly flat: six pilots are cheapest but not decisively, so the paper presents them as the low-commitment choice.

V18 had answered the informal referee report on V17:
- **RFNBO eligibility.** E-fuel is split into RFNBO (offshore wind contracted per coast, hourly matching under Delegated Regulation 2023/1184, ERA5 profiles; €2.31–3.11/L before CO₂) and low-carbon e-fuel from reactor/grid baseload (€2.10/L), which counts for the SAF share but not, centrally, the synthetic sub-mandate. The synthetic quota adds €1.51/L (€0 if low-carbon e-fuel counts).
- **Kelp hubs.** Build size is now chosen on total 2027–2041 cost with fixed costs paid by built hubs: 6 pilot hubs at central costs; 36 only if all cost levers are met. The 28-hub motorway figure is labelled a kelp-only upper bound.
- **Electricity boundary.** 149 TWh in 2041 (53 light vehicles, 28 trucks, 40 low-carbon, 28 RFNBO), 8.2 GW offshore wind for RFNBO and 12.8 GW electrolysers (Table S15); stated as a screening scenario, not an investment plan.
- **Framing.** Abstract and cover letter lead with the reactor as the hub's firm heat and power; anchor sharing and wind contracts stated as assumptions.

V17 had answered the informal referee report on V16:
- **Weather now drives the wind economics.** Ten years of hourly ERA5 data (2015–2024, downloaded by the authors) feed an hourly wind contract for each hub (contracted capacity, wind used, surplus sold, shortfall bought from the reactor or the grid). This replaces the flat €20/MWh firming charge. ERA5 capacity factors range from 38% to 51%. The SMR + wind fuel costs €2.44/L and wind-only €2.83/L. At wind-only hubs, output stays below half the load for up to 17 days at a time.
- **Heavy trucks now form two classes** (regional depot-charged, long-haul catenary), with a 6 × 3 off-wire distance grid (Table S14, Fig. 10d) and both distances in the Monte Carlo.
- **Fuel-specific balances.** A linear programme now handles jet, marine, road and export, with jet-fraction limits (HTL kelp not jet-eligible), the ReFuelEU synthetic sub-mandate and FuelEU as an intensity constraint. ReFuelEU and FuelEU are now step functions. The pooled method is kept as a comparison.

V16 had answered the referee report on V14: the combined SMR + wind option is decomposed (of its €0.16/L edge over SMR + drones, €0.03 is cheaper wind power and €0.13 is the hypothetical anchor sharing) and wind is stated as a third-party private-wire purchase with delivery-charge tests; CO₂ results are labelled screened operational reductions; the system Monte Carlo now samples 19 inputs incl. catenary capital and freight capture (motorway saving positive in 82% of draws, previously 98%); a joint capital × capture grid (new Table S12) shows the fixed 8,850 km network turning negative at +40% capital and −20% capture (€-0.29 bn/yr) while the re-optimised sweet spot still saves €2.7 bn/yr. An optional script, `Repository/model/fetch_weather_v16.py`, downloads the ERA5 hourly wind and solar data now used in V17.

V15 had added, at the authors' request, a national model of the sweet spot between electrification and liquid fuels (domestic transport plus international aviation and shipping), a ranked analysis of what lowers the price of liquid fuel, and a year-by-year 2027–2041 transition (Sections 2.8–2.9, 3.7–3.9, Tables 5–6, Figs 10–12, Note S9). V14 had extended the paper: kelp-to-fuel costs, offshore wind co-located with the kelp farms (turbine foundations as anchors) compared with and combined with SMRs, the renewable-powered Grid Harvester and utility drones, offshore fish farms, and electric motorways with the transport CO₂ they avoid are now in the abstract and main text. The hub model and all heat-cascade results are unchanged from V12/V13.

| Result (central inputs) | Value |
|---|---|
| **Sweet spot 2041 (fuel-specific balances)** | 6,500 km catenary; batteries 360 kWh long-haul / 540 kWh regional; 13.5% of truck-km on renewable range extenders; saves €3.27 bn/yr vs diesel |
| Ranges | Monte Carlo 5–95%: 4,750–8,250 km; off-wire grid: 5,250–7,000 km, saving €1.3–4.2 bn |
| Marginal prices 2041 | SAF €3.38/L (pooled model: €2.85); road €2.05/L; RFNBO-only procurement would add €1.51/L synthetic premium (+€0.57 bn/yr); kelp fuel goes to shipping |
| Kelp hubs to build | 6 pilots cheapest at central cost, but 6–24 hubs within €0.10 bn over 2027–2041; 35 with all cost levers |
| Electricity 2041 (transition) | 149 TWh; 11.3 GW electrolysers; 8.2 GW offshore wind only if RFNBO-only (not financed in model) |
| Transition 2027–2041 | operational CO₂ 146.8 → 69.7 Mt (−53%); €22.1 bn motorway capex |
| Kelp drop-in fuel, mean of six hubs: SMR only / offshore wind only / SMR + wind (weather-based) | €2.62 / €2.83 / €2.44 per litre (long-run diesel €1.45) |
| Farm-gate seaweed share of fuel cost; fuel at €1,200/t seaweed | 50%; €4.86 per litre |
| Utility drones / Grid Harvester | 43–100 drones per hub, net €0.03–0.23 M/yr; harvester fuel saving does not repay its kit |
| Electric motorways, 8,850 km, with kelp-fuelled hybrids | saves €1.28 bn/yr at long-run diesel (€0.04–3.01 bn at €1.20–1.80/L); positive in 82% of draws; €-0.29 bn at +40% capital / −20% capture |
| Transport CO₂ avoided (screened, operational) | 12.8 Mt/yr = 46% of heavy-truck and 10% of domestic transport emissions; fuel of ~28 hubs (2,770 km² kelp; kelp-only upper bound) |
| Reactor-steam distillation vs heat pumps, firm heat | best-sized plants €−1.07 M/yr nationally |
| Co-products, six sites | €26.2 M/yr (central case) |

"Share of draws" = fraction of model draws from stated triangular distributions — not a probability of commercial success.

## Layout
```
EN_Submission/   Manuscript (.docx upload; .pdf), reading copy with figures, cover letter, Supplementary Information, Figures/ (PDF, TIFF 300 dpi, PNG)
FR_Dossier/      French manuscript, SI, cover letter and figures (RDNE accepts English only)
Repository/      Flat folder (no subfolders) to upload as is to https://github.com/bcjohnjr/France-Renewable-Energy-System
QA/              run logs, test logs (387/387 hub model; 185/185 system + weather; 131/131 national model; 17/17 Grid Harvester engineering)
Archive/         NOT FOR SUBMISSION: revision note with point-by-point response (EN/FR) and change logs V13→…→V20.2
```

## Reproduce (Python ≥ 3.11; numpy, scipy, matplotlib, Pillow; no network; about 3 minutes)
```
cd Repository
python -B -I france_v12.py && python -B -I test_v12.py && python -B -I build_figures_v12.py
python -B -I system_v14.py && python -B -I test_system_v14.py && python -B -I build_figures_system_v14.py
python -B -I sweetspot_v19.py && python -B -I test_sweetspot_v19.py && python -B -I build_figures_sweetspot_v19.py
python -B -I build_figure_grid_harvester.py && python -B -I grid_harvester_engineering.py && python -B -I test_grid_harvester.py
```
Licence: code MIT; data, text and figures CC BY 4.0. Seaweed cost, anchor sharing, the waste-lipid and biogenic-CO₂ caps, the off-wire leg model, transition ramp rates, site wind prices, drone and harvester performance, sea temperatures and the outage schedule are screening assumptions.
