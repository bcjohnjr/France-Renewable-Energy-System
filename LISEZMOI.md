# France V12 — Valorisation en cascade de la chaleur des PRM (dossier EN + FR)
**Revue visée :** Research & Design of Nuclear Engineering (RDNE), EDP Sciences, Les Ulis — sans frais de publication pendant la période de lancement (obtenir une confirmation écrite pour une acceptation en 2027).
**Auteurs :** Jonathan Karl Bily (correspondant), Christoph Pahl, Patricia Valdés Bacallao

La V12 est une révision mineure répondant à la cinquième relecture informelle (de la V11, 11 novembre 2026) : répartition mensuelle pondérée par les jours, bilan d’eau explicite sur douze mois et corrections de présentation. Aucune conclusion ne change. La réponse et le journal des modifications sont dans `Archive/` et **ne font pas** partie de la soumission.

**Conclusion (inchangée dans son sens).** Avec une chaleur garantie et de l’eau achetée pendant les arrêts du réacteur et de la distillation, aucune taille de MED ne bat les pompes à chaleur au niveau national. Les meilleures unités (0,90–1,15 Mm³/an) vont de −0,29 à +0,01 M€ par site ; seul Dunkerque est à peine positif. La comparaison économique sans garantie a été retirée (elle utilisait des pompes à chaleur non installées) ; le modèle n’indique que la chaleur qu’une conception sans secours laisserait non servie.

| Résultat (paramètres centraux, chaleur garantie) | Valeur V12 |
|---|---|
| Cascade 2,0 Mm³ − PAC seules | −1,42 à −0,90 M€/an par site (national −6,98 M€ ; 2,0 % des tirages) |
| Cascade bien dimensionnée (0,90–1,15 Mm³) − PAC seules | −0,29 à +0,01 M€/an par site (national −1,07 M€ ; 32,3 % des tirages) |
| Chaleur non servie sans secours (non valorisée) | 2,4–3,6 GWh/an par site (3,3–3,9 % de la demande) |
| Eau du réseau achetée pendant les arrêts, Brest | 132 000 m³/an (75 000 m³ au mois de rechargement d’août) |
| PAC + OIEM (2,0 Mm³) − PAC seules | national −1,83 M€ |
| Valeur des coproduits, six sites (cas central) | 26,2 M€/an (négative dans 27,8 % des tirages) |

Organisation : voir README.md. Reproduction : `cd Code && python -I model/france_v12.py && python -I model/test_v12.py && python -I model/build_figures_v12.py` (387/387 tests).
