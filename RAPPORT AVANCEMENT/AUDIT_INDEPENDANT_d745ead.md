# AUDIT INDÉPENDANT — `main` = d745ead (2026-10-23)

**Auditeur :** Claude Code, troisième agent, sans avoir produit le code audité
(Qoder : C5/C8/C12, Codex : C1/C2/C3). **Mode :** phase 1 en lecture et tests
seulement ; phase 2 = PR vers `main`, aucune fusion, aucun push sur `main`,
aucune branche de Qoder ou de Codex modifiée, aucun fichier de #103 touché.
**Interdits tenus :** pas de décision métier, pas d'import réel, pas de GO,
`sauvegarder.ps1` jamais exécuté, aucune migration créée (donc aucun numéro à
réserver dans `loop-state.md` — le prochain numéro libre reste **055**).

**Preuves jointes :** `preuves/audit_independant_d745ead/controles_independants.py`
(contrôles écrits par l'auditeur, HTTP réel + SQL), sa sortie sur `d745ead`
(`sortie_sur_main_d745ead.txt`) et sur le code de la PR #105
(`sortie_sur_pr105.txt`).

## 1. Environnement et limites de l'audit

| Élément | Audit | CI du dépôt | Effet |
|---|---|---|---|
| PostgreSQL | **16** (conteneur, port 5433) | 17 | non testé sur 17 ; aucune fonction propre à 17 constatée |
| Python / Node | 3.13 / 22 | 3.13 / 24 | — |
| Chrome des suites | Chromium de Playwright, `chrome` émulé par lien (voir D-N7) | Chrome de l'image `ubuntu-latest` | — |
| Base | reconstruite de zéro (schéma d'origine + 000→054 + jeu d'essai), bases jetables | idem | — |

Je n'ai pas exécuté `db/outils/verifier_tout.sh` tel quel : pytest et les 13
suites ont été lancés séparément, sur les mêmes commandes que la CI.

## 2. Phase 1 — Contre-audit de `d745ead`

Classement : **REPRODUIT** (l'annonce est confirmée par mon exécution) ·
**SEULEMENT DOCUMENTÉ** (rien à exécuter, ou non exécutable ici) ·
**NON REPRODUCTIBLE** · **DÉFAUT NOUVEAU**.

| # | Contrôle | Résultat observé | Classement |
|---|---|---|---|
| a1 | Base vierge, migrations 000→054 | `migrer.sh appliquer` sort 0 ; 54 versions enregistrées (55 fichiers : deux fichiers portent le numéro 040, historique documenté dans `migrer.sh`) | REPRODUIT |
| a2 | Allers-retours des inverses 054→051 puis 051→054, deux fois | tous les fichiers sortent 0 ; schéma `pg_dump -s` identique avant/après (seuls diffèrent les jetons aléatoires `\restrict`/`\unrestrict` de pg_dump) | REPRODUIT |
| b1 | pytest | **394 passés**, 0 échec (591 s) | REPRODUIT |
| b2 | 13 suites Playwright | routes 65 · cablage 101 · vente 63 · stock 49 · rapports 52 · inventaire 17 · ux 27 · comptes 26 · caisse 24 · rh 21 · exploitation 14 · echappement 11 · roles 35 = **505 contrôles, 0 échec** — mais `roles` échoue (code 1) sur un poste sans Google Chrome, voir D-N7 | REPRODUIT (13/13, 505) avec réserve D-N7 |
| c-D2 | Paiements mixtes | mixte 4 000 + 2 500 → 201, `mode_paiement = 'mixte'`, composantes tracées, **une seule** recette de 6 500 ; somme ≠ total, `mode_paiement` + `paiements` simultanés, composante crédit, montant négatif → 422 ; même mode deux fois → 422 (pas de 500) ; insertion SQL directe incohérente rejetée par la base (« composantes, somme ou modes incohérents ») ; `/caisse/attendu` ventile espèces / Mobile Money | REPRODUIT |
| c-D4 | Remise > 10 % | agent : −10 % accepté, −10,01 % ligne / `remise_montant` 651 sur 6 500 / `prix_unitaire` 5 800 (contournement par le prix) / globale 10,5 % / globale 700 sur 6 500 → 403 ; responsable −50 % accepté | REPRODUIT |
| c-D4bis | Remises **cumulées** | agent : ligne −10 % **et** globale −10 % → 201, vente à **5 265 FCFA sur 6 500 (−19 %)**, sans responsable | **DÉFAUT NOUVEAU** (D-N1) |
| c-D9 | Encaisseur réel | agent compta → `utilisateur_caisse_id` = lui ; `utilisateur_caisse_id: 1` injecté dans le corps ignoré ; responsable → lui-même ; agent du comptoir → id 5 | REPRODUIT |
| c-D6 | Session 480 min | jeton réel exp−iat = 28 800 s ; jeton correctement signé à 600 min, expiré, non enregistré en base, ou mal signé → 401 ; session échue côté serveur → 401 ; déconnexion révoque ; désactivation ou changement de mot de passe coupent toutes les sessions du compte ; configuration 9 999 min plafonnée à 480 | REPRODUIT |
| c-D7 | Union des rôles | `/moi` renvoie l'union ; compte stock+compta peut vendre (API) ; `/admin/comptes` reste 403 ; rôle retiré en base → effet immédiat sur la session ouverte ; **écran** (Playwright, mon propre script) : bandeau du compte cumulé = clients, inventaire, rapports, stock, vente ; comptes / RH / clôture / tableau de bord redirigent | REPRODUIT |
| c-C12-02 | Alerte de sauvegarde | quatre états conformes (succès daté / échec + motif / absent / illisible) ; succès sans horodatage → `inconnu` ; agent 403, sans jeton 401 | REPRODUIT |
| c-C12bis | Alerte de sauvegarde, cas limites | JSON valide mais pas un objet (`[]`, `"x"`) → **500** ; dernier succès vieux de 2 ans → toujours `succes` | **DÉFAUT NOUVEAU** (D-N4, D-N5) |
| d | Concurrence (hors liste demandée) | 20 ventes du même article, 4 clients → 2×201 + 18×503 | **DÉFAUT NOUVEAU** (D-N2) |
| d | Entrées aberrantes (hors liste) | vente 2,5 sur article entier, quantité 0,0001, prix 10^15, entrée de stock 10^12, comptage 2,5 → 500 | **DÉFAUT NOUVEAU** (D-N2bis, D-N3) |

Aucun résultat classé NON REPRODUCTIBLE. SEULEMENT DOCUMENTÉ : le
fonctionnement de `sauvegarder.ps1` / `restaurer.ps1` (non exécutables ici, et
interdits), la tenue sur PostgreSQL 17, les recettes humaines R1–R5.

## 3. Défauts nouveaux

| # | Gravité proposée | Défaut | Preuve | Traitement |
|---|---|---|---|---|
| D-N1 | P2 (décision) | **Remises cumulées** : le seuil de 10 % est testé séparément sur chaque remise de ligne et sur la remise globale (sur le total déjà remisé). Ligne −10 % + globale −10 % ≈ −19 % sans responsable. | script, section D4 : vente à 5 265 FCFA | **Non corrigé** : dire si les 10 % s'appliquent au cumul est une décision du propriétaire (D4). Proposition de registre : **C5-04**, BLOQUE_PROPRIETAIRE. Ligne ajoutée à la fiche R1 (ligne 16). |
| D-N2 | **P1** | **Interblocage PostgreSQL entre ventes simultanées d'un même article** (verrou partagé de la clé étrangère composite, puis verrou exclusif de `decrementer_stock_vente`). Mesuré sur 20 ventes : 2 clients → 1 échec (une série), 3 clients → 12, 4 clients → 18, 5 clients → 17. Présenté au vendeur comme « système injoignable ». | journal PostgreSQL ; `test_concurrence_http.py` rouge sur `d745ead` | **PR #105** (sans migration). Proposition de registre : **C10-03**. |
| D-N2bis | P3 | Saisies aberrantes → 500 « Erreur interne » : quantité décimale sur article entier à la vente, quantité arrondie à zéro, prix ou quantité au-delà de NUMERIC | script, section « entrées aberrantes » | **PR #105** |
| D-N3 | P2 | **C7** : comptage d'une quantité décimale sur un article entier → 500 (la base refuse bien, la route ne traduit pas `CheckViolation`) | script ; test rouge sur `d745ead` | **PR #104**. Proposition de registre : **C7-05**. |
| D-N4 | P3 | **C12-02** : fichier d'état JSON valide mais pas un objet → `GET /exploitation/etat-sauvegarde` répond 500 (`{"configure": True, **etat}` sur une liste ou une chaîne) ; l'écran n'affiche alors pas le bandeau d'alerte mais une erreur serveur | script | **Non corrigé** (hors C7/C9/C10 ; correctif trivial : traiter tout JSON non-objet comme `inconnu`). Proposition : **C12-04**. |
| D-N5 | P2 (décision) | **C12-02** : l'alerte voit l'échec, pas le **silence** ; un dernier `SUCCES` ancien (planificateur arrêté, script jamais relancé) reste « réussie le … ». Le cahier des charges demande une sauvegarde toutes les heures en heures d'ouverture, RPO proposé 1 h (`ADDENDUM_CAHIER_DES_CHARGES.md`, section Sauvegardes). | script, `etat.json` daté de 2024 → `succes` | **Non corrigé** : l'âge au-delà duquel on alerte est une décision du propriétaire (l'addendum donne l'ancre 1 h, il ne tranche pas l'alerte). Proposition : **C12-05**, BLOQUE_PROPRIETAIRE. |
| D-N6 | P3 | **C7-03** : l'export `/rapports/ecarts-comptage` nomme « id » la colonne qui porte l'identifiant de l'**article** (`a.id`), pas du comptage ; `ecart_cumule` / `valorisation_cumulee` sont des sommes algébriques (un manquant et un surplus se compensent). | lecture de `rapports.py` + xlsx exporté | **Non corrigé** : changer les en-têtes d'un export destiné à la déclaration fiscale, ou choisir net/absolu, relève du propriétaire. À signaler seulement. |
| D-N7 | P3 | **C13/C10** : `maquette/verification/verifier-roles.mjs` fixe `channel: "chrome"` et ignore `PLAYWRIGHT_CHANNEL`, contrairement aux 11 autres suites ; la CI exporte `PLAYWRIGHT_CHANNEL=chromium` mais n'installe que Chromium : la 13ᵉ suite ne passe que parce que l'image `ubuntu-latest` embarque Google Chrome. | exécution : échec « Chromium distribution 'chrome' is not found » ; succès (35/35) avec le correctif | **PR de documentation et de recette** (une ligne). Proposition : **C13-03**. |
| D-N8 | P3 | Hygiène : les suites Playwright réécrivent des captures versionnées (`maquette/captures/*.png`) : un run local sale l'arbre | `git status` après passe | À signaler ; aucune action. |
| D-N9 | P3 | Cosmétique : le bandeau de `stock.html` pour un agent stock contient deux liens vers `inventaire.html` (« Retour » et « Inventaire ») | DOM | À signaler ; aucune action. |

## 4. Phase 2 — Lot C (C7 / C9 / C10)

**Nommage utilisé :** celui de `REGISTRE_ECARTS_100.md` (C7 Inventaire et
comptage 67 %, C9 Tests et recette 60 %, C10 Qualité et non-régression 58 %).
Les scores 67 / 60 / 58 sont identiques dans tous les documents ; les
**noms** ne le sont pas, voir § 5.

Le registre n'attribue **aucun poids par écart** : je n'invente donc pas de
points. « Gain justifiable » = ce que la preuve d'exécution permet de
revendiquer aujourd'hui (aucun score ne change) et ce qui le permettrait.

### Vérification de la conclusion « 0 dev-actionnable »

Verdict global : **exacte pour les écarts listés du registre**, **inexacte
pour le chantier** — l'audit a trouvé trois défauts faisables par le code que
le registre ne listait pas (D-N2 → C10-03, D-N3 → C7-05, fiches obsolètes →
C9-02), et la divergence de nommage cache des restes de C9/C10 qui ne sont
tracés nulle part (§ 5).

| Écart | Statut registre | Ma vérification | « 0 dev-actionnable » ? | Décision / recette attendue et preuve de clôture | PR |
|---|---|---|---|---|---|
| **C7-01** plafond de vraisemblance à confirmer | BLOQUE_PROPRIETAIRE | Base : `plafond_vraisemblance_comptage = 10000`, `a_decider = FALSE`, référence « Défaut équipe de développement (2026-09-25), à confirmer » ; 10 000 accepté, 10 001 refusé (HTTP) | **Confirmé** | Décision : confirmer ou changer 10 000 (une ligne datée dans `DECISIONS_PROPRIETAIRE.md`). Clôture : cette ligne + mise à jour de `parametres.reference_decision` (migration **055**, à réserver à ce moment-là). | — |
| **C7-02** historique des comptages | CLOS (cycle 68) | Historique : tous les comptages + type/motif/date de régularisation ; interdit aux agents ; la régularisation ne touche pas au stock ; seconde régularisation refusée | Confirmé (rien à faire) | — | — |
| **C7-03** export écarts de comptage | CLOS (cycle 68) | xlsx : `nb_ecarts` et `ecart_cumule` = somme des lignes ; réservé au responsable ; réserve D-N6 (en-tête « id », cumul algébrique) | Confirmé, avec D-N6 à trancher | Décision (facultative) : nom de colonne et net/absolu | — |
| **C7-04** 2ᵉ campagne de comptage physique | BLOQUE_TEST_HUMAIN | Non exécutable par un agent | **Confirmé** | Recette : fiche **R1 §6 élargie** (CYCLE_74_ARBITRAGE, ligne D). Clôture : deux campagnes concordantes + PV (critère du registre), captures. | — |
| **C7-05** (proposé) comptage décimal → 500 | — (nouveau) | Reproduit, corrigé | **Infirme la conclusion** | Clôture : PR #104 fusionnée + test vert | **#104** |
| **C9-01** campagne UX n°2 | BLOQUE_TEST_HUMAIN | Fiche R1 obsolète (ne couvrait ni D2, D4, D6, D7, D9, C12-02, ni la concurrence ; R2 ligne 9 prescrivait **l'ancien** comportement D7 option 1) | Confirmé pour la campagne elle-même | Recette : **R1 corrigée** (lignes 13-21) ; clôture : tableau signé + captures + 5 réponses « VOS RETOURS » + version testée (`d745ead` ou plus récente), sans anomalie bloquante | **C9-02 (proposé)** : PR de documentation |
| **C10-01** rapport de tests manuels signé | BLOQUE_PROPRIETAIRE | Trame de PV déjà dans la fiche R5 ; ses prérequis étaient périmés (D2/D4/D5 présentés comme non décidées, « 5 lignes `a_decider` » au lieu de 6, risque « paiements mixtes reportés ») — corrigés | Confirmé (signature = propriétaire) | Clôture : PV signé déposé dans `RAPPORT AVANCEMENT/cycles/` + registre mis à jour | même PR de documentation |
| **C10-02** test multi-postes / simultané | BLOQUE_TEST_HUMAIN | **Critère « ventes simultanées sans conflit » non tenu sur `d745ead`** (D-N2) ; corrigé et prouvé automatiquement | **Infirme la conclusion pour le volet applicatif** ; le volet « deux postes physiques » reste humain | Recette : 2ᵉ poste (C0-03, fiche R4) + fiche R1 ligne 20 ; clôture : ventes simultanées sur deux postes sans conflit, journaux relus | **#105** (volet logiciel) |
| **C10-03** (proposé) interblocage ventes | — (nouveau) | Reproduit, corrigé | — | PR #105 fusionnée + `test_concurrence_http.py` vert en CI | **#105** |

Gain justifiable **aujourd'hui** : **0 point** sur C7, C9, C10 — aucun écart
du registre ne passe CLOS sur preuve d'exécution humaine, et le registre exige
ce type de preuve. Ce que les PR changent : elles lèvent deux défauts réels
(500 sur comptage, blocage entre postes) et rendent la future campagne R1
conforme aux décisions du 2026-10-23.

## 5. Désaccords de nommage C0–C14 (signalés, non corrigés)

Source « registre » = `REGISTRE_ECARTS_100.md` ; source « loop-state » =
tableau d'ouverture de `RAPPORT AVANCEMENT/loop-state.md` ; « C75 » =
`CYCLE_75_RAPPORT_CONSOLIDE.md`.

| Chantier | Registre | loop-state | C75 |
|---|---|---|---|
| C3 | Habilitations et cloisonnement | …**des rôles** | = registre |
| C6 | **Clôture de caisse et paiements** | **Comptabilité et RH** | = loop-state |
| C7 | Inventaire et **comptage** | Inventaire et **écarts** | = loop-state |
| C8 | **Interfaces et parcours** | **Tableaux de bord et rapports** | = registre |
| **C9** | **Tests et recette** | **Ergonomie et UI** *(priorité 1)* | = loop-state |
| **C10** | **Qualité et non-régression** | **Mobile et API web** *(priorité 1)* | = loop-state |
| C11 | Sécurité | Sécurité applicative | = loop-state |
| C12 | Sauvegarde et **reprise** | Sauvegarde et **exploitation** | = registre |
| C13 | **Intégration continue** | **Tests automatisés et qualité** | = loop-state |
| C14 | Dossier de recette et mise en production | Documentation et livrables | **Dossier de recette** |

Les pourcentages concordent partout, sauf les retards de mise à jour de
`loop-state.md` sur C1 (92 → 96), C2 (82 → 90), C3 (77 → 88), C5 (81 → 88),
C12 (95 → 97), déjà reportés au registre et à C75.

**Conséquence qui dépasse la forme.** Pour C9 et C10, le registre et
`loop-state.md` ne décrivent pas le même chantier. Les restes que
`loop-state.md` attribue à C10 « Mobile et API web » — mesure UX-5 (< 45 s au
téléphone), campagne sur téléphone réel, « API dédiée si un jour distincte de
l'appli web, usage hors ligne, notifications » — et à C9 « Ergonomie et UI » —
UX-0 (méthode de mesure à trancher par le propriétaire), objectif chronométré
< 60 s jamais remesuré avec un vrai testeur — **n'ont aucun écart dans le
registre** (qui ne tient pour C9 que C9-01 et pour C10 que C10-01/02).
Proposition à arbitrer par le propriétaire, sans que je la tranche : soit
reporter ces restes comme écarts du registre (nouvelles lignes C9-03, C10-04),
soit déclarer explicitement qu'ils sont hors V1. Les écarts ainsi ajoutés
seraient tous BLOQUE_TEST_HUMAIN ou BLOQUE_PROPRIETAIRE.

Autres incohérences de comptage relevées : `loop-state.md` et le cycle 73
parlent de « 9 campagnes humaines R1–R9 » alors que `CYCLE_73_FICHES_RECETTE.md`
n'a que les fiches **R1–R5** (le tableau A–I de `CYCLE_74_ARBITRAGE.md` compte
bien neuf campagnes, rattachées aux cinq fiches) ; et le registre dit « 6
lignes `a_decider` » là où la fiche R5 en disait 5 (corrigée ici : 6, vérifié
en base).

## 6. Pull requests ouvertes par l'audit

| PR | Branche | Contenu | Preuve |
|---|---|---|---|
| **#104** | `claude/c7-comptage-decimal-422` | C7 : comptage décimal sur article entier → 422 | test rouge → vert ; 19/19 sur les fichiers touchés |
| **#105** | `claude/cool-heisenberg-gqxu24` | C10-02 : interblocage des ventes simultanées, saisies aberrantes → 4xx, interblocage → 409 | 403 pytest sur base isolée (394 + 9) ; 13/13 suites Playwright sur ce code ; contrôles indépendants |
| **#106** (cette PR) | `claude/c9-c10-recette-et-audit` | rapport d'audit, contrôles indépendants et leur sortie, fiches de recette R1/R2/R5 mises à jour, `verifier-roles.mjs` respecte `PLAYWRIGHT_CHANNEL` | roles 35/35 sans Google Chrome installé |

Aucune des trois ne touche un fichier de #103 (rapports `LOTB_*`,
`restaurer.ps1`, `verifier_tout.sh`, `double_chiffrement.ps1`,
`test_campagne_fcfa_c5.py`, captures, `loop-state.md`) ; aucune ne contient de
migration. Les trois partent de `origin/main` = `d745ead`.

## 7. Ce que je n'ai pas fait

- Pas de modification de `REGISTRE_ECARTS_100.md` ni de `loop-state.md` (fichiers
  que d'autres PR modifient, et que le propriétaire arbitre) : les lignes
  proposées (C5-04, C7-05, C9-02, C10-03, C12-04, C12-05, C13-03) sont dans ce
  rapport, à reporter par le propriétaire ou par un cycle dédié.
- Pas de correctif pour D-N1 et D-N5 (décisions métier), ni pour D-N4, D-N6,
  D-N8, D-N9 (hors Lot C ou arbitrage du propriétaire).
- Aucune exécution de `sauvegarder.ps1`, aucune restauration, aucun import réel.
- PostgreSQL 17 non testé.
