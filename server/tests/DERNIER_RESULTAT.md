# Dernier résultat d'exécution — suite pytest du serveur

Trace rejouable :

```powershell
.\db\outils\demarrer_pg.ps1
server\.venv\Scripts\python.exe -m pytest server\tests\ -v
```

---

## Cycle 19 — reçu de vente imprimable (chantier C5), 2026-09-13

`GET /ventes/{id}/recu` (`reportlab`, PDF A4) — CDC §3.3/§7.1
« imprimer / réimprimer le reçu ». Mêmes rôles que `POST /ventes`.
Aucune migration.

```
test_recu_vente_pdf_contient_les_lignes_et_totaux PASSED
test_recu_vente_annulee_porte_la_mention PASSED
test_recu_vente_inexistante_refusee PASSED
test_agent_stock_ne_peut_pas_obtenir_de_recu PASSED
test_recu_vente_agent_comptabilite_limite_a_son_site PASSED

======================= 140 passed, 31 warnings in 236.96s =======================
```

Contenu du PDF relu par `pypdf` (jamais une simple vérification du code
HTTP) : nom de la boutique, nom d'article, total TTC présents pour une
vente normale ; mention « VENTE ANNULÉE » + motif présents pour une vente
annulée, absents sinon. Cloisonnement par site vérifié avec un nouveau
compte de test (`comptoir.compta`, ajouté à `conftest.py` — jusqu'ici
inutilisé dans la suite).

### Écran (`maquette/vente.html`) — bouton « Imprimer le reçu »

`verifier-vente-reelle.mjs` étendu : un VRAI téléchargement de navigateur
est intercepté après le clic (en-tête `%PDF`), pas seulement la présence
du bouton.

```
[ok] vente réelle : bouton « Imprimer le reçu » visible après la vente
[ok] reçu réel : PDF réellement téléchargé (en-tête « %PDF» )

Total : 12 contrôles, 0 échec(s).
```

`verifier-cablage.mjs` (77/77) et `verifier-echappement-html.mjs` (11/11)
rejoués sans régression.

---

## Cycle 18 — écran dédié pour la RH (chantier C6), 2026-09-13

Aucune route ni migration nouvelle : `maquette/rh.html` câble les routes
`employes`/`absences-conges`/`avances-salaire` du cycle 16, jamais
exposées à un écran jusqu'ici. Aucun test pytest ajouté (rien de nouveau
côté serveur) — vérifié uniquement par une nouvelle suite Playwright,
`verifier-rh-reel.mjs`.

```
RÉUSSIS (21) :
  magasin.stock : accès direct à rh.html -> reredirigé
  magasin.compta : accès direct à rh.html -> reredirigé
  rh@360/390/768/1366/1920 : aucun débordement, cibles ≥ 44px
  responsable : accès à rh.html
  employé réel : POST /rh/employes -> 201, réapparaît dans la liste
  absence/congé réelle : POST /rh/absences-conges -> 201, rattachée au bon employé
  avance réelle : POST /rh/avances-salaire -> 201, réapparaît non remboursée
  remboursement réel : POST /rh/avances-salaire/{id}/rembourser -> 204,
    bouton « Rembourser » disparaît ensuite

Total : 21 contrôles, 0 échec.
```

**Piège rencontré et corrigé** : le 3e lien de navigation ajouté au
bandeau de `tableau-bord.html` (« Ressources humaines ») faisait déborder
l'écran entre 720px et ~820px — la règle générique de `styles.css` ne
repasse en colonne qu'en dessous de 719px. Corrigé par un `<style>` scopé
à `tableau-bord.html` (voir `server/README.md`, section C6/cycle 18).
`verifier-cablage.mjs` (77/77) et `verifier-echappement-html.mjs` (11/11)
rejoués après correction : 0 régression.

Suite pytest complète inchangée : **135/135** (aucun code serveur touché
ce cycle).

---

## Cycle 17 — annulation de vente, régularisation d'écart (chantier C5), 2026-09-13

Migration 017 (`annulation_vente_regularisation_ecart`) : `annuler_vente()`
et `regulariser_ecart_vente()` — CDC §3.3 (« Annulation d'une vente —
responsable uniquement : restitue le stock et retire la recette
associée »), et `ecarts_stock_ventes.regularise` (cycle 6, jamais posé par
aucune fonction jusqu'ici). Aucune règle nouvelle inventée : les deux
mécanismes complètent une trace déjà décidée par le propriétaire.

### `test_ventes.py` (7) et `test_inventaire.py` (6) — nouveaux, 13/13

```
test_annuler_vente_restitue_le_stock_et_contre_passe_la_recette PASSED
test_annuler_vente_a_decouvert_ne_restitue_que_le_stock_reellement_decremente PASSED
test_annuler_vente_deja_annulee_refusee PASSED
test_annuler_vente_inexistante_refusee PASSED
test_annuler_vente_motif_blanc_refuse PASSED
test_agent_stock_et_agent_comptabilite_ne_peuvent_pas_annuler_une_vente PASSED
test_regulariser_ecart_vente_marque_traite PASSED
test_regulariser_ecart_vente_deja_regularise_refuse PASSED
test_regulariser_ecart_vente_inexistant_refuse PASSED
test_regulariser_ecart_vente_reserve_au_responsable PASSED
test_annulation_vente_regularise_automatiquement_lecart PASSED

======================= 135 passed, 31 warnings in 200.72s =======================
```

Faille trouvée par exécution en écrivant ce cycle, **avant tout code
Python** (détail complet dans `db/tests/DERNIER_RESULTAT.md` et
`db/README.md`) : `decrementer_stock_vente()` (cycle 6) ne renseignait
jamais `mouvements_stock.vente_id` — corrigé dans la migration 017 même,
sans quoi `annuler_vente()` n'aurait rien trouvé à restituer pour aucune
vente réelle.

### Écran (`maquette/tableau-bord.html`) — bouton « Régulariser »

La carte « Écarts de stock (ventes) », réelle depuis le cycle 8, expose
désormais un bouton « Régulariser » par ligne non régularisée
(`POST /inventaire/ecarts-ventes/{id}/regulariser`) — vérifié par
exécution via `verifier-inventaire-reel.mjs` (le texte du bouton apparaît
bien dans la ligne rendue) et `verifier-echappement-html.mjs` (un nom
d'article malveillant reste échappé y compris avec le bouton ajouté).

### Suite complète

```powershell
server\.venv\Scripts\python.exe -m pytest server\tests\ -v
```

**135 passed** (124 hérités + 11 nouveaux), 0 régression. Les 6 suites
Playwright rejouées : `cablage` 77/77, `inventaire` 17/17, `vente` 10/10,
`stock` 26/26, `rapports` 29/29, `echappement` 11/11 — 0 régression.
(`affichage` et `flux` nécessitent un serveur statique séparé sur le port
8080, non lancé cette fois — sans lien avec ce chantier.)

---

## Cycle 16 — comptabilité et RH (chantier C6), 2026-09-13

Aucune nouvelle migration : `transactions`, `employes`, `absences_conges`,
`avances_salaire` existent avec leurs `GRANT` depuis les cycles 1/2, sans
route jusqu'ici. Troisième et dernier chantier du lot validé après le
cycle 13. Clôture de caisse (addendum, point g) volontairement non
traitée.

### `test_transactions.py` (8) et `test_rh.py` (10) — nouveaux, 18/18

```
test_responsable_enregistre_une_recette PASSED
test_responsable_enregistre_une_depense_rattachee_a_un_employe PASSED
test_agent_comptabilite_enregistre_sur_son_site PASSED
test_agent_stock_ne_peut_pas_enregistrer_de_transaction PASSED
test_transaction_employe_invalide_refusee_proprement PASSED
test_responsable_doit_preciser_un_site_pour_une_transaction PASSED
test_lister_transactions_filtre_par_periode PASSED
test_lister_transactions_date_invalide_refusee PASSED
test_responsable_cree_un_employe PASSED
test_agent_comptabilite_ne_peut_pas_creer_employe PASSED
test_lister_employes_reserve_au_responsable PASSED
test_responsable_cree_une_absence_conge PASSED
test_absence_conge_employe_invalide_refusee PASSED
test_absence_periode_incoherente_refusee PASSED
test_responsable_cree_une_avance_salaire PASSED
test_rembourser_avance_salaire PASSED
test_rembourser_avance_deja_remboursee_refusee PASSED
test_rembourser_avance_inexistante_refusee PASSED

======================= 18 passed, 6 warnings in 26.80s =======================
```

### Écran (`maquette/tableau-bord.html`) — `verifier-cablage.mjs`, 77/77

La carte « Saisie rapide », simulée depuis le cycle 5, câble désormais un
vrai formulaire vers `POST /transactions` — vérifié par exécution (une
recette de 4 500 FCFA réellement retrouvée en base après validation), et
non plus seulement par lecture du code. +1 contrôle par rapport au cycle
15 (76 → 77).

### Suite complète

```powershell
server\.venv\Scripts\python.exe -m pytest server\tests\ -v
```

**124 passed** (106 hérités + 18 nouveaux), 0 régression. Les 6 suites
Playwright : 77/77, 10/10, 17/17, 11/11, 26/26, 29/29 — 0 régression.

---

## Cycle 13 — correction des constats n°2 et n°3 (chantier C4), 2026-09-13

Migration 016 (`retours_coherence_document_origine.sql`) : corrige
`enregistrer_retour_client()` et `enregistrer_retour_fournisseur()`
(migration 014) pour qu'un retour ne dépasse jamais, en article et en
quantité, ce que le document d'origine référencé porte réellement — le
constat n°2 du contrôle de boucle après le cycle 9. `PUT /articles/{id}`
corrigé pour ne tracer un changement de prix que s'il a réellement eu
lieu — le constat n°3 du contrôle de boucle après le cycle 11.

### `test_stock.py` (+3) et `test_articles.py` (+1) — nouveaux, 4/4

```
test_retour_client_article_non_vendu_dans_la_vente_refuse PASSED
test_retour_client_quantite_cumulee_depassee_refuse PASSED
test_retour_fournisseur_quantite_cumulee_depassee_refuse PASSED
test_modification_prix_identique_ne_trace_rien PASSED
```

Vérifié en SQL direct avant tout code Python (comme pour la migration 014) :
retour exactement égal au reste disponible (accepté), un de plus (refusé),
deuxième retour cumulé qui dépasse après un premier retour valide
(refusé), article non vendu dans la vente indiquée (refusé) — pour le
retour client comme pour le retour fournisseur. Les vérifications
préexistantes (site, existence du mouvement/de la vente, nature du
mouvement, stock suffisant) revérifiées intactes après le changement
d'ordre des contrôles dans `enregistrer_retour_fournisseur()`.

### Suite complète

```powershell
server\.venv\Scripts\python.exe -m pytest server\tests\ -v
```

**104 passed** (100 hérités des cycles précédents + 4 nouveaux), 0
régression. Les 6 suites Playwright (`cablage`, `vente`, `inventaire`,
`echappement`, `stock`, `rapports`) : 76/76, 10/10, 17/17, 11/11, 26/26,
29/29 — 0 régression (aucun écran touché ce cycle).

---

## Cycle 11 — écran de stock (chantier C4), 2026-09-13

Aucune nouvelle table : migration 015 (une seule fonction,
`articles_autre_site()`). Correctif du constat n°1 du contrôle de boucle
après le cycle 9 (`POST /articles` ne traduisait aucune erreur de la
base) et nouvelle route `PUT /articles/{id}` (modification, tracée dans
`historique_modifications_articles`/`historique_prix_articles`).

### `test_articles.py` — 10 nouveaux tests (5 → 15)

```
test_responsable_cree_un_article_avec_prix PASSED
test_agent_stock_cree_un_article_sans_prix PASSED
test_agent_stock_ne_peut_pas_choisir_un_autre_site PASSED
test_responsable_doit_preciser_un_site PASSED
test_agent_comptabilite_ne_peut_pas_creer_darticle PASSED
test_site_invalide_refuse_proprement PASSED
test_responsable_modifie_le_nom_et_le_prix PASSED
test_agent_stock_modifie_le_nom_mais_pas_le_prix PASSED
test_agent_stock_ne_modifie_pas_un_article_de_lautre_site PASSED
test_modification_article_inexistant_refusee PASSED
test_modification_sans_aucun_champ_refusee PASSED
test_modification_fournisseur_invalide_refusee_proprement PASSED
test_agent_stock_voit_les_articles_de_lautre_site_sans_prix PASSED
test_agent_stock_ne_voit_pas_son_propre_site_dans_lautre_site PASSED
test_responsable_ne_peut_pas_appeler_articles_autre_site PASSED

======================= 15 passed, 5 warnings in 22.54s =======================
```

### Écran (`maquette/stock.html`) — `verifier-stock-reel.mjs`, 26/26

Les 6 opérations exécutées réellement par un agent stock (création,
réception, transfert vers le Comptoir avec le nouveau sélecteur
inter-site, retour client contre une vraie vente, retour fournisseur
contre la réception faite plus haut dans le même script — chaque montant
de stock revérifié en base après chaque étape) et par un responsable
(modification de prix tracée, casse) ; aucun bouton « Casse » pour
l'agent stock ; **aucune occurrence de « FCFA » dans la page de l'agent
stock, avant et après les opérations** ; aucun champ de prix dans les
réponses réseau de `/articles` et `/articles/autre-site` vues par la
page ; layout aux 5 largeurs, cibles ≥ 44 px.

### Suite complète

```powershell
server\.venv\Scripts\python.exe -m pytest server\tests\ -v
```

**100 passed** (90 hérités + 10 nouveaux), 0 régression. Les 5 suites
Playwright (`cablage`, `vente`, `inventaire`, `echappement`, **`stock`
nouveau**) : 76/76, 10/10, 17/17, 11/11, 26/26 — 0 régression.

---

## Cycle 10 — chantier C8 (tableaux de bord et rapports), 2026-09-13

Aucune nouvelle migration : les trois briques de ce cycle s'appuient sur
des colonnes déjà en base depuis les cycles 2 et 4.

### `test_tableau_bord.py` (6) + `test_rapports.py` (11) — nouveaux, 17/17

```
test_alertes_stock_liste_larticle_sous_seuil PASSED
test_alertes_stock_narticle_au_dessus_du_seuil_absent PASSED
test_alertes_stock_reservee_au_responsable PASSED
test_historique_comptages_filtre_par_periode PASSED
test_historique_comptages_date_invalide_refusee PASSED
test_historique_comptages_reserve_au_responsable PASSED
test_export_articles_agent_stock_xlsx_sans_prix PASSED
test_export_articles_agent_stock_pdf_sans_prix PASSED
test_export_articles_responsable_xlsx_avec_prix PASSED
test_export_articles_responsable_pdf_avec_prix PASSED
test_export_articles_agent_comptabilite_prix_vente_seulement PASSED
test_export_articles_format_invalide_refuse PASSED
test_export_ventes_responsable_xlsx_contient_le_total PASSED
test_export_ventes_hors_periode_est_vide PASSED
test_export_ventes_agent_comptabilite_autorise PASSED
test_export_ventes_agent_stock_refuse PASSED
test_export_ventes_date_invalide_refusee PASSED

======================= 17 passed, 4 warnings in 25.31s =======================
```

Les tests d'export relisent le contenu **réel** du fichier produit
(`openpyxl.load_workbook`, `pypdf.PdfReader`) plutôt que le seul code HTTP :
`test_export_articles_agent_stock_xlsx_sans_prix` et son équivalent PDF
vérifient l'absence physique de `prix_achat`/`prix_vente` dans les en-têtes
et dans le texte extrait ; les tests « responsable » vérifient au contraire
la présence d'une valeur de prix réelle du jeu d'essai (`5000`) dans le
fichier.

### Suite complète

```powershell
server\.venv\Scripts\python.exe -m pytest server\tests\ -v
```

**90 passed** (73 hérités des cycles précédents + 17 nouveaux), 0 régression.

---

## Cycle 9 — chantier C4 (articles et stock), 2026-09-13

Décisions du propriétaire (addendum, points a et f) appliquées : migration
000 à **014** (`014_articles_stock_transferts_retours.sql`).

### `test_articles.py` (5) + `test_stock.py` (13) — nouveaux, 18/18

```
test_responsable_cree_un_article_avec_prix PASSED
test_agent_stock_cree_un_article_sans_prix PASSED
test_agent_stock_ne_peut_pas_choisir_un_autre_site PASSED
test_responsable_doit_preciser_un_site PASSED
test_agent_comptabilite_ne_peut_pas_creer_darticle PASSED
test_reception_recalcule_le_seuil PASSED
test_reception_refusee_pour_un_article_de_lautre_site PASSED
test_transfert_normal_ne_recalcule_pas_le_seuil PASSED
test_transfert_motif_blanc_refuse_par_la_base PASSED
test_transfert_stock_insuffisant_refuse PASSED
test_transfert_vers_le_meme_site_refuse PASSED
test_agent_stock_ne_transfere_que_depuis_son_site PASSED
test_casse_reservee_au_responsable PASSED
test_retour_client_rattache_a_la_vente PASSED
test_retour_client_vente_inexistante_refuse PASSED
test_agent_stock_ne_traite_un_retour_client_que_pour_son_site PASSED
test_retour_fournisseur_sur_une_vraie_reception PASSED
test_retour_fournisseur_sur_un_mouvement_qui_nest_pas_une_reception PASSED
```

**Trois failles trouvées par exécution**, jamais exploitables avant ce
cycle (aucune route n'appelait ces fonctions) : `enregistrer_entree_stock()`
(cycle 2), `enregistrer_retour_client()` et `enregistrer_retour_fournisseur()`
(ce cycle) ne vérifiaient aucun site — un agent stock du Magasin pouvait
agir sur le stock du Comptoir. Confirmé par exécution AVANT correction :

```sql
SET ROLE qf_agent_stock; SELECT set_config('qf.site_id', '1', true);
SELECT enregistrer_entree_stock(3, 10, 2, 'test cross-site');  -- article du Comptoir
 enregistrer_entree_stock
--------------------------
                      109        <- ACCEPTÉ, aurait dû être refusé
```

Cause : `current_user` à l'intérieur d'une fonction `SECURITY DEFINER` vaut
le propriétaire de la fonction, pas l'appelant — voir `db/README.md`. Après
correction (`qf_site_courant()` à la place de `current_user`), même essai :
`ERROR: Un agent stock ne peut réceptionner que pour son propre site.`

### Suite complète — 73/73, 0 régression

```
73 passed in ~107s
```

### Non-régression SQL du cycle 2, rejouée à jour (`db/tests/executer_tests.sh`)

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 014) : OK
>>> jeu d'essai chargé : OK
>>> protections   : OK   (44/44)
>>> habilitations : OK   (52/52)
>>> concurrence   : OK   (6/6)
>>> aller / retour des migrations : OK   (aucune différence nouvelle après
                                          réversion — colonnes et fonctions
                                          entièrement retirées)
```

Bug trouvé en écrivant la migration (pas en la concevant) :
`01_protections.sql` insère directement dans `mouvements_stock` sans
`categorie`, désormais `NOT NULL` — corrigé (deux lignes).

### Non-régression des écrans réels (Playwright)

Aucun écran n'a été construit pour C4 ce cycle (hors périmètre du plan
validé) ; les quatre scripts existants ont été rejoués pour confirmer
qu'un changement de schéma sur `mouvements_stock` ne casse ni C5 ni C7 :

```
verifier-cablage.mjs (C9/C10)          : 74/74 — 0 régression
verifier-vente-reelle.mjs (C5)         : 10/10 — 0 régression
verifier-inventaire-reel.mjs (C7)      : 17/17 — 0 régression
verifier-echappement-html.mjs          : 11/11 — 0 régression
```

---

## Cycle de correction après le cycle 7, 2026-09-12

Fait avant de démarrer un nouveau chantier, sur validation explicite du
propriétaire, après qu'un contrôle de boucle a rejoué le cycle 7 comme un
relecteur extérieur et trouvé 5 constats absents du rapport initial (voir
`RAPPORT AVANCEMENT/loop-state.md`). Migrations 000 à **013** appliquées
(nouvelle : `013_fuseau_horaire_boutique.sql`).

### `test_inventaire.py` — 11/11 (9 + 2 nouveaux)

```
test_liste_a_compter_ne_contient_aucune_quantite PASSED
test_liste_a_compter_du_responsable_distingue_les_deux_sites PASSED   (nouveau)
test_comptage_ne_renvoie_jamais_quantite_attendue_ni_ecart PASSED
test_champs_interdits_injectes_par_le_client_sont_sans_effet PASSED   (nouveau)
test_agent_stock_ne_peut_pas_lire_ecart_en_sql_direct[ecart] PASSED
test_agent_stock_ne_peut_pas_lire_ecart_en_sql_direct[quantite_attendue] PASSED
test_article_deja_compte_disparait_de_la_liste_et_refuse_un_second_envoi PASSED
test_agent_stock_ne_peut_pas_compter_un_article_de_lautre_site PASSED
test_agent_comptabilite_interdit_sur_linventaire PASSED
test_ecarts_du_jour_reserves_au_responsable PASSED
test_ecarts_ventes_du_jour_relie_c5_et_c7 PASSED
```

### Suite complète — 55/55, 0 régression

```
55 passed in ~91s
```

### Fuseau horaire — vérifié à deux niveaux indépendants

```
SHOW TimeZone;  ->  Africa/Douala   (fraîche connexion, après migration 013)
```

Défense en profondeur confirmée par exécution : la base a été réglée
délibérément sur `UTC` (`ALTER DATABASE ... SET timezone TO 'UTC'`), puis
`connexion_anonyme()` et `connexion_pour()` (`server/app/database.py`) ont
quand même renvoyé `Africa/Douala` — le réglage applicatif ne dépend pas de
celui de la base. Remis à `Africa/Douala` ensuite.

### Non-régression SQL du cycle 2, rejouée à jour (`db/tests/executer_tests.sh`)

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 013) : OK
>>> jeu d'essai chargé : OK
>>> protections   : OK   (44/44)
>>> habilitations : OK   (52/52)
>>> concurrence   : OK   (6/6)
>>> aller / retour des migrations : OK
```

### Vérification bout-en-bout sur les écrans réels (Playwright)

```
verifier-cablage.mjs (C9/C10)         : 74/74 — 0 régression
verifier-vente-reelle.mjs (C5)        : 10/10 — 0 régression (rejoué après le
                                          correctif de fuseau horaire, qui
                                          touche aussi /ventes/synthese-jour)
verifier-inventaire-reel.mjs (C7)     : 17/17 (12 + 5 nouveaux : double
                                          soumission/409 à deux onglets)
verifier-echappement-html.mjs (nouveau) : 11/11 — un nom d'article portant
                                          une charge HTML/JS ne s'exécute nulle
                                          part (vente.html et tableau-bord.html),
                                          s'affiche partout comme texte brut
```

Bug trouvé par l'exécution en écrivant la vérification (pas en la
concevant) : le script `verifier-inventaire-reel.mjs` supposait le moment
par défaut ("matin" avant 13h) figé — le correctif de fuseau horaire a
changé l'heure locale réellement utilisée par la page, faisant basculer ce
défaut à "soir" au moment du contrôle. Corrigé en forçant explicitement le
moment (bouton "Matin") plutôt que de dépendre de l'heure du jour au
moment du test.

---

## Cycle 7 — chantier C7 (inventaire et écarts), 2026-09-12

Migrations 000 à **012** appliquées (nouvelle :
`012_comptage_aveugle_colonnes.sql`).

### `test_inventaire.py` — nouveau, 9/9

```
test_liste_a_compter_ne_contient_aucune_quantite PASSED
test_comptage_ne_renvoie_jamais_quantite_attendue_ni_ecart PASSED
test_agent_stock_ne_peut_pas_lire_ecart_en_sql_direct[ecart] PASSED
test_agent_stock_ne_peut_pas_lire_ecart_en_sql_direct[quantite_attendue] PASSED
test_article_deja_compte_disparait_de_la_liste_et_refuse_un_second_envoi PASSED
test_agent_stock_ne_peut_pas_compter_un_article_de_lautre_site PASSED
test_agent_comptabilite_interdit_sur_linventaire PASSED
test_ecarts_du_jour_reserves_au_responsable PASSED
test_ecarts_ventes_du_jour_relie_c5_et_c7 PASSED
```

Point le plus important, prouvé par exécution : **avant** la migration 012,
`SET ROLE qf_agent_stock; SELECT ecart, quantite_attendue FROM
comptages_stock;` était accepté par PostgreSQL — jamais exploité par aucune
route, mais une faille de confidentialité réelle. Après la migration :
`ERROR: permission denied for table comptages_stock`.

### Suite complète — 53/53, 0 régression

```
53 passed in ~71s
```

### Non-régression SQL du cycle 2, rejouée à jour (`db/tests/executer_tests.sh`)

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 012) : OK
>>> jeu d'essai chargé : OK
>>> protections   : OK   (44/44)
>>> habilitations : OK   (52/52)
>>> concurrence   : OK   (6/6)
>>> aller / retour des migrations : OK
```

### Vérification bout-en-bout sur les écrans réels (Playwright, `verifier-inventaire-reel.mjs`)

```
12/12 — liste à compter réelle sans quantité, comptage produisant un écart
réel (-8) sans qu'il n'apparaisse dans la page, le code source ou les
réponses réseau observées après rechargement, article compté absent de la
liste au rechargement, tableau de bord affichant l'écart de comptage exact
(-8) et l'écart de vente à découvert exact (manque 2).
```

Non-régression des cycles 5 et 6 (`verifier-cablage.mjs`,
`verifier-vente-reelle.mjs`, tous deux mis à jour pour refléter les écarts
désormais réels au tableau de bord) : **74/74** et **10/10**.

---

## Cycle 6 — chantier C5 (ventes), 2026-09-12

Exécuté avec **Python 3.13.3**, contre **PostgreSQL 17.11** (`_pgdev/`), base
`quincaillerie_test`, migrations 000 à **011** appliquées (nouvelle :
`011_ventes_fiscalite_anti_survente.sql`).

### `test_ventes.py` — nouveau, 8/8

```
test_parametres_vente_expose_le_taux_tva_en_vigueur PASSED
test_vente_normale_decremente_le_stock_et_calcule_la_tva PASSED
test_vente_a_decouvert_nest_jamais_refusee_et_consigne_lecart PASSED
test_credit_client_reste_desactive PASSED
test_agent_stock_ne_peut_pas_enregistrer_de_vente PASSED
test_agent_comptabilite_ne_peut_pas_vendre_pour_lautre_site PASSED
test_responsable_doit_preciser_le_site PASSED
test_responsable_peut_vendre_pour_un_site_precise PASSED
```

Point le plus important, prouvé par exécution : une vente de 5 unités
d'« Article rare » (stock réel : 1) est **acceptée** (201), le stock tombe à
0 (jamais négatif), et un écart de 4 unités est consigné dans
`ecarts_stock_ventes`, réservé au responsable — jamais un refus.

### Suite complète — 44/44, 0 régression

```
44 passed in ~58s
```

### Non-régression SQL du cycle 2, rejouée à jour (`db/tests/executer_tests.sh`)

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées (000 à 011) : OK
>>> jeu d'essai chargé : OK
>>> protections   : OK   (44/44)
>>> habilitations : OK   (52/52)
>>> concurrence   : OK   (6/6 — comportement anti-survente, voir 03_concurrence.sh)
>>> aller / retour des migrations : OK
```

### Vérification bout-en-bout sur l'écran réel (Playwright, `verifier-vente-reelle.mjs`)

```
10/10 — vente normale (numéro de vente serveur, plus aucune mention
SIMULATION, aperçu affiché AVANT validation identique au montant confirmé
par le serveur), vente à découvert acceptée avec écart affiché à l'écran,
crédit client absent des options de paiement, responsable bloqué tant qu'il
n'a pas choisi de site.
```

Bug trouvé en écrivant ce contrôle : l'aperçu du total (`majTotaux()` dans
`vente.html`) ajoutait encore la TVA par-dessus le sous-total au lieu de
l'extraire d'un prix déjà TTC (décision d) — corrigé pour utiliser
exactement la même formule que la route.

Non-régression du cycle 5 (`verifier-cablage.mjs`, mis à jour car la
validation de vente n'est plus une confirmation simulée) : **74/74**.

---

## Cycle 3 — chantiers C2, C3, C11

Exécuté le **2026-09-12** avec **Python 3.13.3**, contre **PostgreSQL 17.11**
(`_pgdev/`, cycle 2 stabilisé), base `quincaillerie_test`, migrations 000 à
010 appliquées.

---

## Phase 1 — Diagnostic par exécution, avant d'écrire une route

Deux pièges trouvés et corrigés **avant** d'écrire le code serveur, en
testant chaque brique en SQL direct d'abord :

1. **pgcrypto ne valide pas un hachage `$2b$`** (défaut de la bibliothèque
   Python `bcrypt`). Testé dans les deux sens :
   ```
   crypt('MotDePasseTest123', '$2b$12$...')  -> f  (FAUX même pour le bon mot de passe)
   crypt('MotDePasseTest123', '$2a$12$...')  -> t  (bon mot de passe)
   crypt('MauvaisMotDePasse', '$2a$12$...')  -> f  (mauvais mot de passe)
   ```
   → `securite.hacher_mot_de_passe()` génère toujours avec `prefix=b"2a"`.

2. **`qf_app` ne pouvait exécuter aucune fonction** :
   ```
   ERROR: function verifier_connexion(...) does not exist   -- sous qf_app
   -- la même requête, identique, réussit sous postgres
   ```
   Cause : `USAGE ON SCHEMA public` jamais accordé à `qf_app` (migration 008).
   → migration **010** (corrective, 008 non modifiée rétroactivement).

## Phase 4 — Vérification par exécution

### Fonctions d'authentification, testées directement en SQL avant tout code Python

```
--- bon mot de passe ---
ok | utilisateur_id | nom_complet | role        | doit_changer_mot_de_passe
t  | 1              | Awa Franck  | responsable | t

--- verrouillage après 5 échecs ---
essai 1 (mauvais mdp) : f | identifiant_ou_mot_de_passe_incorrect
essai 2 (mauvais mdp) : f | identifiant_ou_mot_de_passe_incorrect
essai 3 (mauvais mdp) : f | identifiant_ou_mot_de_passe_incorrect
essai 4 (mauvais mdp) : f | identifiant_ou_mot_de_passe_incorrect
essai 5 (mauvais mdp) : f | compte_verrouille
6e essai (BON mdp)    : f | compte_verrouille   <- refusé même avec le bon mot de passe
après déverrouillage  : t |  (bon mot de passe accepté de nouveau)

--- libre-service, limité à sa propre ligne ---
changer_mon_mot_de_passe('AgentTest123', '$2a$...')      -> t (bon mdp actuel)
rejoué avec l'ANCIEN mdp                                  -> f (plus valide)
avec un mauvais mdp actuel dès le départ (autre compte)   -> f
```

### Suite pytest — 36 / 36

```
tests/test_authentification.py::test_connexion_reussie PASSED
tests/test_authentification.py::test_connexion_mot_de_passe_incorrect PASSED
tests/test_authentification.py::test_connexion_identifiant_inconnu PASSED
tests/test_authentification.py::test_verrouillage_apres_echecs_repetes PASSED
tests/test_authentification.py::test_compte_desactive_ne_peut_pas_se_connecter PASSED
tests/test_authentification.py::test_deverrouillage_par_le_responsable PASSED
tests/test_authentification.py::test_deverrouillage_refuse_a_un_agent PASSED
tests/test_authentification.py::test_limitation_de_debit_sur_la_connexion PASSED
tests/test_authentification.py::test_changement_mot_de_passe_a_la_premiere_connexion PASSED
tests/test_authentification.py::test_changement_mot_de_passe_refuse_si_actuel_incorrect PASSED
tests/test_authentification.py::test_un_agent_ne_peut_changer_que_son_propre_mot_de_passe PASSED
tests/test_cloisonnement_site.py::test_agent_ignore_le_site_fourni_en_parametre_de_requete PASSED
tests/test_cloisonnement_site.py::test_rls_bloque_meme_en_sql_direct_hors_de_lapi PASSED
tests/test_cloisonnement_site.py::test_rls_laisse_le_responsable_voir_les_deux_sites_en_sql_direct PASSED
tests/test_cloisonnement_site.py::test_agent_comptoir_ne_voit_pas_les_ventes_du_magasin PASSED
tests/test_habilitations.py::test_agent_stock_ne_voit_aucun_prix PASSED
tests/test_habilitations.py::test_agent_comptabilite_ne_voit_aucune_quantite PASSED
tests/test_habilitations.py::test_responsable_voit_tout PASSED
tests/test_habilitations.py::test_responsable_voit_les_deux_sites PASSED
tests/test_habilitations.py::test_agent_stock_ne_voit_que_son_site PASSED
tests/test_habilitations.py::test_agent_comptabilite_ne_voit_que_son_site PASSED
tests/test_habilitations.py::test_agent_stock_interdit_sur_synthese_ventes PASSED
tests/test_habilitations.py::test_comptabilite_et_responsable_autorises_sur_synthese_ventes PASSED
tests/test_habilitations.py::test_profil_ne_renvoie_jamais_de_hachage PASSED
tests/test_habilitations.py::test_aucune_route_accessible_sans_jeton PASSED
tests/test_habilitations.py::test_jeton_invalide_refuse PASSED
tests/test_habilitations.py::test_jeton_falsifie_refuse PASSED
tests/test_securite.py::test_reponse_de_connexion_ne_contient_jamais_de_hachage PASSED
tests/test_securite.py::test_reponses_articles_et_profil_ne_contiennent_jamais_de_hachage PASSED
tests/test_securite.py::test_config_refuse_le_compte_superutilisateur PASSED
tests/test_securite.py::test_config_refuse_la_cle_secrete_exemple PASSED
tests/test_securite.py::test_mot_de_passe_en_clair_jamais_ecrit_dans_le_code_serveur PASSED
tests/test_securite.py::test_hachage_genere_par_le_serveur_est_verifiable_par_pgcrypto PASSED
tests/test_securite.py::test_jeton_expire_est_refuse PASSED
tests/test_securite.py::test_jeton_signe_avec_une_autre_cle_est_refuse PASSED
tests/test_securite.py::test_injection_sql_dans_lidentifiant_ne_casse_rien PASSED

36 passed in 47.49s
```

### Preuve la plus forte du chantier C3 — RLS en SQL direct, hors API

```sql
BEGIN;
SET LOCAL ROLE qf_agent_stock;
SELECT set_config('qf.site_id', '1', true);
SELECT id, nom, site_id FROM articles WHERE site_id = 2;   -- demande EXPLICITEMENT l'autre site
```
```
 id | nom | site_id
----+-----+---------
(0 ligne)
```
```sql
SELECT id, nom, site_id FROM articles;                      -- sans aucun filtre
```
```
 id |         nom         | site_id
----+---------------------+---------
  1 | Ciment CIM II 50 kg |       1
  2 | Fer à béton 8 mm    |       1
  4 | Article rare        |       1
```

Même en demandant explicitement `WHERE site_id = 2`, PostgreSQL renvoie
**zéro ligne** — la RLS filtre avant même que le `WHERE` du client ne
s'applique. Aucun code applicatif n'est impliqué dans ce test.

### Parcours HTTP bout-en-bout (démarrage réel d'uvicorn, requêtes `curl`)

```
POST /auth/connexion {"identifiant":"resp","mot_de_passe":"ResponsableTest123"}
-> 200 {"jeton":"...","role":"responsable","site_id":null,...}

GET /articles (agent stock, Magasin)
-> 200 {"articles":[{"id":1,"nom":"Ciment CIM II 50 kg","unite":"sac","quantite_stock":30,"seuil_alerte":6,"site_id":1}, ...]}
   (aucun champ prix_achat / prix_vente ; site_id toujours 1)

GET /articles (agent comptabilité, Magasin)
-> 200 {"articles":[{"id":1,"nom":"Ciment CIM II 50 kg","unite":"sac","prix_vente":6500.0,"site_id":1}, ...]}
   (aucun champ quantite_stock / seuil_alerte)

GET /ventes/synthese-jour (agent stock)
-> 403 {"detail":"Rôle non autorisé pour cette route."}

GET /moi (sans jeton)
-> 401 {"detail":"Jeton manquant."}

POST /auth/connexion {"identifiant":"x' OR '1'='1","mot_de_passe":"peu importe"}
-> 401 {"detail":"Identifiant ou mot de passe incorrect."}   (aucune erreur serveur, injection neutralisée)
```

---

## Non-régression du cycle 2

Les migrations 009 et 010 ajoutées ce cycle n'ont rien cassé : la suite
complète du cycle 2 a été rejouée après leur ajout.

```
>>> création de quincaillerie_test : OK
>>> migrations appliquées          : OK
>>> jeu d'essai chargé             : OK
>>> protections   : OK   (44/44)
>>> habilitations : OK   (52/52)
>>> concurrence   : OK   (4/4)
>>> aller / retour des migrations  : OK
Toutes les étapes sont passées.
```

Différences après aller-retour des migrations (000 à 010) : les 2 déjà
documentées (`db/README.md`) + l'extension `pgcrypto` conservée (comme
`pg_trgm`), sans effet de bord.

---

## Bilan

**136 contrôles au total pour ce cycle** (44 + 52 + 4 hérités du cycle 2,
rejoués sans régression, + 36 nouveaux pour C2/C3/C11), **0 échec**.
