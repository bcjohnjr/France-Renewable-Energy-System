# France V12 — Cascaded heat utilisation from SMRs (EN + FR package)
**Target journal:** Research & Design of Nuclear Engineering (RDNE), EDP Sciences, Les Ulis, France — no publication charges in the launch period (get written confirmation for a 2027 acceptance).
**Title:** Cascaded heat utilisation from small modular reactors for desalination, aquaculture and food production: a techno-economic assessment for France
**Authors:** Jonathan Karl Bily (corresponding), Christoph Pahl, Patricia Valdés Bacallao

V12 is a minor revision answering the fifth informal review (of V11, 11 November 2026): day-weighted monthly allocation, an explicit twelve-month water balance and presentation fixes. No conclusion changes. The response and change log are in `Archive/` and are **not** part of the journal submission.

**Conclusion (unchanged in direction).** With heat kept firm and water bought in through reactor and distillation outages, no MED size beats heat pumps nationally. The best plants (0.90–1.15 Mm³/yr) range from −€0.29 to +€0.01 M per site; only Dunkerque is marginally positive. The non-firm economic comparison has been withdrawn (it used heat pumps that were not installed); the model reports only the heat a design without backup would leave unserved. Reactor-steam MED is a water-supply option, not heat recovery.

| Result (central inputs, firm heat) | V12 value |
|---|---|
| First-law utilisation, heat-pump-only → cascade | 44.1–49.2% → 54.4–57.0% |
| 2.0 Mm³ cascade − heat-pump-only | €−1.42 to −0.90 M/yr per site (national €−6.98 M; ahead in 2.0% of model draws) |
| Right-sized cascade (0.90–1.15 Mm³) − heat-pump-only | €−0.29 to +0.01 M/yr per site (national €−1.07 M; 5–95%: −5.34 to +3.21; ahead in 32.3% of draws) |
| Heat unserved without backup (not valued) | 2.4–3.6 GWh/yr per site (3.3–3.9% of low-temperature demand) |
| Right-sized, with grid connection at €150/kW / interruptible-water discount 15% / full SWRO polishing on MED | national €−1.90 M / €−1.73 M / €−1.29 M |
| Mains water bought during outages, Brest | 132,000 m³/yr (75,000 m³ in the August refuelling month) |
| HP + SWRO (2.0 Mm³) − heat-pump-only | €−0.40 to −0.23 M/yr per site (national €−1.83 M) |
| Co-product value, six sites (central case) | €26.2 M/yr (5–95%: −34.4 to 67.9; negative in 27.8% of draws) |
| Packaging-alginate break-even | €4.83–5.26/kg; Fos (Ulva) has no alginate |

"Share of draws" = fraction of 2,000 draws from the stated triangular distributions (40 inputs), conditional on the model's cost boundary — not a probability of commercial success.

## Layout
```
EN_Submission/   Manuscript (.docx upload: double-spaced, line-numbered; .pdf), reading copy with figures,
                 cover letter (RDNE six parts), Supplementary Information, Figures/ (PDF, TIFF 300 dpi, PNG)
FR_Dossier/      French translation of manuscript, SI and cover letter, French figures (RDNE accepts English only)
Code/            model/ (france_v12.py, test_v12.py, build_figures_v12.py, geo_france.py, ers_corridors.py,
                 france_model.py = underlying reactor and fuel-chain energy model), build/ (content_v12.py, build_docs_v12.py, make_docx.js), data/
Source_Data/     All outputs (MED size sweep, right-sizing incl. unmet heat, 2-D sensitivity, ledgers, monthly dispatch, Monte Carlo)
QA/              run log, test log (387/387), rendered page checks
Archive/         NOT FOR SUBMISSION: response to the fifth informal review (EN/FR) and CHANGELOG_V11_to_V12.md
.zenodo.json     Draft Zenodo metadata (record CC BY 4.0; code files MIT)
```

## Reproduce (Python ≥ 3.11; numpy, matplotlib, Pillow; no network; ~3 min)
```
cd Code
python -I model/france_v12.py && python -I model/test_v12.py && python -I model/build_figures_v12.py
```
Licence: code MIT; data, text and figures CC BY 4.0. Sea temperatures, greenhouse climate factors and the outage schedule are illustrative screening inputs (SI Table S4). Claude (Anthropic) assisted with code, figures, drafting and translation (disclosed in the manuscript and cover letter).
