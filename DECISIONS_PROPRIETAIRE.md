# Décisions à prendre par le propriétaire — registre vivant (cycle 65+)

Chaque point : contexte, options, impact, recommandation de la session de
développement. **Rien n'est décidé à la place du propriétaire** : ces points
bloquent soit la montée en production, soit la fermeture d'un chantier à 99-100 %.
Mis à jour au fil des cycles ; les décisions obtenues sont déplacées dans
`RAPPORT AVANCEMENT/loop-state.md` (section « Décisions du propriétaire »).

Légende impact : **GO** = bloque la mise en production ; **Score** = bloque
la qualification 99-100 % d'un chantier ; **Qualité** = amélioration sans blocage.

---

## D1 — Prix affichés à l'écran de vente pour le caissier (visibilité prix)

- **Contexte** : le rôle caissier est fusionné avec l'agent comptabilité
  (addendum h, décidé). Côté base, ce rôle lit `articles.prix_vente` mais PAS
  `prix_achat` (matrice SQL, cycle 65). Côté écran `vente.html`, le vendeur
  saisit et encaisse. La question jamais tranchée : quels prix le caissier
  doit-il voir pendant la vente (prix de vente uniquement ? remises visibles ?)
  et l'écran actuel affiche-t-il exactement ce périmètre ?
- **Options** :
  1. Statu quo : prix de vente visibles, prix d'achat jamais (cohérent avec
     les privilèges SQL actuels) — **vérifié en inspection ce cycle**, aucun
     code à écrire.
  2. Masquer davantage (ex. prix catalogue dans certains écrans) — aucun
     besoin identifié à ce jour.
  3. Rôle caissier distinct à droits affinés (refuse la fusion h).
- **Vérification faite au cycle 65 (aucun code modifié)** :
  - `vente.html` ne consomme que `prix_vente` du catalogue — le `prix_achat`
    (présent dans le payload du responsable seulement) est ignoré explicitement
    (`vente.html:344-349`) ; cohérent avec les GRANT SQL (008).
  - `/rapports/ecarts-prix-vendeurs` : la vue `ecarts_prix_vendeurs` (048,
    `SECURITY INVOKER`) n'expose que `prix_catalogue` (copie du prix de vente
    à la vente) et le prix payé — **aucun `prix_achat`** ; la RLS par site
    s'applique au rôle lecteur.
  - `/rapports/ventes` : colonnes chiffrées sans prix d'achat
    (`rapports.py:189-192`).
- **Impact** : **GO** (confidentialité commerciale) + **Score C3**.
- **Recommandation** : l'option 1 est déjà en place et vérifiée en inspection
  ce cycle — il ne reste qu'à la **confirmer** comme décision (aucun code à
  écrire). Toute évolution (rôle caissier distinct, marges visibles) repartirait
  de ce constat.
- **Statut** : OUVERT — confirmation formelle requise.

## D2 — Paiements mixtes (point b, question 3)

- **Contexte** : une vente peut-elle être réglée en plusieurs modes
  (espèces + mobile money + crédit client sur la même facture) ? Le modèle
  `ventes.mode_paiement` est mono-valeur aujourd'hui.
- **Options** :
  1. Mono-mode (statu quo) : interdit les mixtes, le vendeur saisit deux
     ventes ou un acompte. Simple, comptabilité inchangée.
  2. Multi-modes : nouvelle table `ventes_paiements`, impact caisse,
     rapports, annulation, clôture — chantier à part entière.
- **Impact** : **GO** (fréquence réelle du cas en boutique inconnue — le
  propriétaire seul peut le dire).
- **Recommandation** : si les mixtes sont rares, option 1 en v1 (acompte
  partiel déjà couvert par les règlements de créance).
- **Décision (2026-10-23)** : **option 2 — paiements mixtes retenus** :
  une vente peut être réglée en plusieurs modes sur la même facture
  (espèces + Mobile Money), avec traçabilité par mode.
- **Chaîne** : VALIDÉE PAR LE PROPRIÉTAIRE (2026-10-23) → **IMPLÉMENTÉE**
  (cycle 75-C, PR #95 : table `ventes_paiements`, décomposition tracée par
  mode, caisse et rapports adaptés) → **TESTÉE** (pytest + Playwright,
  régression complète du cycle 75) → **CLÔTURÉE côté développement**
  (écart C1-01 CLOS — la fusion de la PR #95 reste au propriétaire).
- **Statut** : VALIDÉE — IMPLÉMENTÉE — TESTÉE (fusion PR #95 : propriétaire).

## D3 — Fond de caisse initial et seuil d'écart (point g)

- **Contexte** : la clôture de caisse compare espèces comptées et recettes
  attendues. Fond de caisse initial (constante de la journée ? par session ?)
  et seuil d'écart toléré avant alerte non chiffrés.
- **Options** :
  1. Fond paramétrable par site, seuil fixe (ex. 1 000 FCFA).
  2. Fond saisi à chaque clôture, seuil paramétrable.
- **Impact** : **Score C6** (le reste du point g est livré).
- **Recommandation** : option 1 — un fond par site est stable en pratique.
- **Statut** : OUVERT.

## D4 — Seuil de remise et qui peut remiser (point f)

- **Contexte** : les remises sont saisies en vente (cycle 59) sans plafond ni
  règle d'habilitation particulière.
- **Options** :
  1. Plafond en pourcentage par paramètre + alerte au dépassement.
  2. Validation responsable au-delà d'un seuil.
  3. Libre (statu quo).
- **Impact** : **GO** (maîtrise des marges).
- **Recommandation** : option 1, paramètre `seuil_remise_pct` par défaut 100 %
  (statu quo effectif) jusqu'à décision.
- **Décision (2026-10-23)** : remises **autorisées jusqu'à 10 %** pour tout
  vendeur ; **au-delà de 10 %, la validation du responsable est obligatoire**
  (jamais un simple avertissement).
- **Chaîne** : VALIDÉE PAR LE PROPRIÉTAIRE (2026-10-23) → **IMPLÉMENTÉE**
  (cycle 75-B, PR #94 : migration 051 `seuil_remise_validation_pct=10`,
  blocage 403 côté serveur pour un agent au-delà du seuil — par ligne et
  remise globale, condition strictement `>`) → **TESTÉE** (pytest dédiés +
  Playwright, régression complète du cycle 75) → **CLÔTURÉE côté
  développement** (écart C5-02 CLOS — la fusion de la PR #94 reste au
  propriétaire).
- **Statut** : VALIDÉE — IMPLÉMENTÉE — TESTÉE (fusion PR #94 : propriétaire).

## D5 — Prix saisis HT ou TTC (point d, question 3)

- **Contexte** : hypothèse de travail TTC (`prix_saisis_ttc = oui` depuis le
  cycle 6) jamais confirmée par le comptable. Inverser après coup coûte une
  migration des données.
- **Impact** : **GO**.
- **Recommandation** : à faire confirmer par le comptable avant tout import
  réel du stock.
- **Audit livré (cycle 75-G, 2026-10-23)** — décision validée : la saisie
  TTC est CONSERVÉE et le traitement fiscal est audité, sans rien inventer
  (note complète : `RAPPORT AVANCEMENT/D5_AUDIT_TTC.md`) :
  - prix saisis TTC partout, TVA extraite sur le TOTAL de la vente (jamais
    ligne à ligne) — `ventes.py:335-337, 378-384` ;
  - aucun taux inventé : `taux_tva` = paramètre en base (défaut migrations
    0 = aucune TVA appliquée ; base de test 19,25 %, décidé cycle 6 — la
    valeur exacte reste la question Q2), valeur
    `a_definir` refusée par `parametre_numerique()` (migration 006) ;
    sur une base issue des migrations seules, `regime_fiscal`,
    `prix_saisis_ttc`, `boutique_numero_contribuable`, `arrondi_montants`
    restent à l'état sentinelle (la base de test porte les valeurs du
    cycle 6 — vérifié en SQL le 2026-10-23) ;
  - reçu PDF et exports n'affichent que des valeurs déduites et stockées
    (`ventes.py:432-440, 543-552`, `rapports.py:280`) ;
  - **6 questions comptables** (Q1-Q6) listées pour confirmation AVANT tout
    import réel : régime fiscal, taux exact, confirmation TTC, ventilation
    ligne à ligne (écart C1-02), mentions obligatoires, arrondi.
- **Chaîne** : VALIDÉE PAR LE PROPRIÉTAIRE (2026-10-23 — TTC conservé,
  traitement fiscal à confirmer avec le comptable avant tout import réel) →
  **IMPLÉMENTÉE** (cycle 75-G, PR #99 : audit documenté
  `RAPPORT AVANCEMENT/D5_AUDIT_TTC.md`, états réels vérifiés en SQL —
  migrations vs seed — aucun taux inventé) → **TESTÉE** (vérifications SQL
  exécutées, régression complète du cycle 75) → **reste une sous-condition
  au propriétaire** : les réponses du comptable Q1-Q6, et aucune bascule de
  paramètre avant elles (écart C1-02).
- **Statut** : VALIDÉE — IMPLÉMENTÉE (audit) — TESTÉE ; réponses comptable
  Q1-Q6 attendues avant tout import réel (C1-02 reste BLOQUE_PROPRIETAIRE ;
  fusion PR #99 : propriétaire).

## D6 — Durée de session inactive (C2)

- **Contexte** : `duree_session_minutes = 480` (8 h) en config, mais
  `parametres.duree_session_minutes` vaut encore `a_definir` — le paramètre
  de base n'est pas branché sur l'émission des jetons.
- **Options** :
  1. Garder 8 h fixes (journée de travail), fermer le paramètre de base.
  2. Brancher le paramètre de base et le laisser modifiable par le
     responsable.
- **Impact** : **Score C2**.
- **Recommandation** : option 1 pour la v1 (une valeur modifiable a des
  effets de sécurité à documenter).
- **Décision (2026-10-23)** : session limitée à **480 minutes maximum**, avec
  expiration et révocation **vérifiables**.
- **Chaîne** : VALIDÉE PAR LE PROPRIÉTAIRE (2026-10-23) → **IMPLÉMENTÉE**
  (cycle 75-E, PR #97 : plafond porté par les jetons signés — migration 033 ;
  révocation une à une — migration 018 ; aucune route de renouvellement) →
  **TESTÉE** (`test_session_d6.py` : expiration et révocation prouvées par
  exécution, régression complète du cycle 75) → **CLÔTURÉE côté
  développement** (la moitié « session » de l'écart C2-01 est résorbée ;
  la fusion de la PR #97 reste au propriétaire).
- **Statut** : VALIDÉE — IMPLÉMENTÉE — TESTÉE (fusion PR #97 : propriétaire).

## D7 — Cumul de rôles à l'écran (divergence D2 du cycle 65)

- **Contexte** : l'API honore tous les rôles d'un compte ; l'UI ne regarde
  que le rôle principal. Un compte stock+comptabilité ne voit que ses écrans
  de stock à l'écran alors que l'API l'accepterait en vente.
- **Options** :
  1. Statu quo : un compte cumulé = un seul périmètre visuel (rôle principal),
     les autres rôles ne servent qu'en API.
  2. Menu par union des rôles : l'écran affiche les entrées des rôles
     secondaires avec une bascule.
- **Impact** : **Qualité** (aucun trou de sécurité — l'API reste le garde).
- **Recommandation** : option 1 tant que le cumul reste rare ; réexaminer si
  des comptes réels cumulent au quotidien.
- **Décision (2026-10-23)** : **option 2 — union des rôles à l'écran** : un
  utilisateur cumulant plusieurs rôles voit TOUTES les fonctions autorisées
  par ses rôles (le bandeau de chaque page liste tous ses écrans).
- **Chaîne** : VALIDÉE PAR LE PROPRIÉTAIRE (2026-10-23) → **IMPLÉMENTÉE**
  (cycle 75-D, PR #96 : carte centralisée `ROLES_PAR_PAGE` dans `api.js`,
  `ajusterNavigation()` retire les liens interdits ET ajoute les manquants ;
  régressions connexes corrigées au cycle 75-H, PR #100) → **TESTÉE**
  (Playwright par profil, régression complète du cycle 75) → **CLÔTURÉE
  côté développement** (écart C3-03 CLOS — les fusions des PR #96 et #100
  restent au propriétaire).
- **Statut** : VALIDÉE — IMPLÉMENTÉE — TESTÉE (fusions PR #96 puis #100 :
  propriétaire).

## D8 — Inventaire : le responsable peut-il compter ? (divergence D1 du cycle 65)

- **Contexte** : l'API autorise le responsable à lancer/compter un inventaire,
  l'écran `inventaire.html` ne l'accepte pas (gate `["agent_stock"]`).
- **Options** :
  1. Statu quo : le comptage est une tâche d'agent, le responsable supervise
     (écarts, validations) — cohérent avec l'addendum (comptage physique par
     le personnel).
  2. Ouvrir l'écran au responsable (gate `["responsable", "agent_stock"]`).
- **Impact** : **Qualité**.
- **Recommandation** : option 1 (cohérente avec l'esprit comptage aveugle).
- **Décision (2026-10-23)** : **option 1 confirmée** — l'agent stock effectue
  le comptage, le responsable supervise et valide.
- **Chaîne** : VALIDÉE PAR LE PROPRIÉTAIRE (2026-10-23) → **constat :
  comportement déjà conforme** (`inventaire.html` réservé à l'agent stock ;
  le responsable consulte les écarts et valide les déclarations) →
  **TESTÉE** (preuve par exécution au cycle 75-D, PR #96 : suites inventaire
  et stock, régression complète du cycle 75) → **CLÔTURÉE** (écart C3-02
  CLOS ; la fusion de la PR #96 reste au propriétaire).
- **Statut** : VALIDÉE — TESTÉE (conforme, aucun code requis ; fusion
  PR #96 : propriétaire).

## D9 — Attribution `utilisateur_caisse_id` (anomalie relevée au cycle 65)

- **Contexte** : `server/app/routes/ventes.py` — l'attribution du caissier sur
  une vente suivait une logique à auditer (compte qui enregistre ? vendeur ?
  site ?). Qualifiée au cycle 66 (écart C5-01 : `utilisateur_caisse_id`
  attribué au responsable quel que soit l'encaisseur réel), corrigée au
  cycle 75-A.
- **Impact** : **Score C5/C13** (traçabilité de qui a encaissé).
- **Recommandation** : audit d'abord, décision ensuite — ne pas trancher sans
  le constat chiffré.
- **Décision (2026-10-23)** : chaque encaissement est attribué à
  **l'utilisateur authentifié réel** qui l'enregistre (jamais substitué au
  responsable).
- **Chaîne** : VALIDÉE PAR LE PROPRIÉTAIRE (2026-10-23) → **IMPLÉMENTÉE**
  (cycle 75-A, PR #93 : `utilisateur_caisse_id` tire du jeton authentifié,
  plus jamais du corps de requête ni du rôle) → **TESTÉE** (pytest dédiés :
  vente encaissée par un agent porte son identifiant, tentative de
  substitution refusée ; régression complète du cycle 75) → **CLÔTURÉE côté
  développement** (écart C5-01 CLOS — la fusion de la PR #93 reste au
  propriétaire).
- **Statut** : VALIDÉE — IMPLÉMENTÉE — TESTÉE (fusion PR #93 : propriétaire).

## D10 — Authentification forte (2FA) pour le responsable (C11)

- **Contexte** : mot de passe seul. Le 2026-10-20, Kaspersky signale
  `sauvegarder.ps1` (faux positif documenté). Aucune 2FA n'existe.
- **Options** :
  1. Statu quo (poste dédié, réseau local).
  2. Code à usage unique envoyé/e-mail — dépend d'une connectivité que la
     boutique n'a pas forcément.
  3. TOTP sur application mobile du responsable (hors ligne possible).
- **Impact** : **Qualité** (menace réelle faible sur un poste dédié local).
- **Recommandation** : reporter après la v1 ; si retenu, TOTP (option 3).
- **Mesures compensatoires en place (V1)** — consignées au cycle 75-E
  (D10 validée le 2026-10-23 : 2FA reportée après V1, TOTP si retenu) ;
  chacune est prouvée par exécution, pas déclarée :
  1. Mots de passe bcrypt coût 12, préfixe $2a$ compatible pgcrypto
     (migration 009, `test_hachage_genere_par_le_serveur_est_verifiable_par_pgcrypto`) ;
  2. mot de passe provisoire OBLIGATOIRE à la première connexion et après
     réinitialisation (migration 050, contrôle 403 à chaque requête —
     `test_changement_mdp_force.py`) ;
  3. limitation de débit sur /auth/connexion (038, fenêtre partagée en
     base — `test_limitation_de_debit_sur_la_connexion`) et verrouillage
     du compte après échecs répétés, levé par le responsable seul
     (migration 009 — `test_verrouillage_apres_echecs_repetes`,
     `test_deverrouillage_refuse_a_un_agent`) ;
  4. sessions signées bornées à 480 minutes (D6, migration 033),
     révocables une à une (migration 018), AUCUNE route de
     renouvellement — `test_session_d6.py` ;
  5. coupure immédiate d'un jeton encore valide : désactivation du compte
     (024) et réinitialisation par le responsable
     (`test_reinitialisation_responsable_coupe_jeton_encore_valide`) ;
  6. cloisonnement PostgreSQL : rôles PG par métier + RLS par site
     (migration 029) — un mot de passe volé ne sort pas du périmètre du
     compte (`test_privileges_sql_roles.py`, matrice des rôles) ;
  7. journal d'audit non destructible (004/005) : toute connexion et toute
     action administrative restent tracées.
  L'ajout ultérieur du TOTP (option 3) viendra EN PLUS de ces mesures, qui
  ne dépendent d'aucune connectivité.
- **Chaîne** : VALIDÉE PAR LE PROPRIÉTAIRE (2026-10-23 — 2FA reportée après
  V1, TOTP si retenu) → **mesures compensatoires IMPLÉMENTÉES** (liste
  ci-dessus, cycles 3 à 44) et **TESTÉES une par une** (cycle 75-E, PR #97 :
  chaque test cité rejoué vert dans la régression complète du cycle 75) →
  **CLÔTURÉE pour la V1** (écart C2-02 CLOS — le TOTP éventuel est un
  chantier post-V1 ; la fusion de la PR #97 reste au propriétaire).
- **Statut** : VALIDÉE (reportée après V1) — mesures compensatoires
  IMPLÉMENTÉES — TESTÉES (fusion PR #97 : propriétaire).

## D11 — Kaspersky : faux positif sur `sauvegarder.ps1`

- **Contexte** : à chaque exécution, Kaspersky met en quarantaine le script
  de sauvegarde (détection `PDM:Trojan.Win32.Generic`, heuristique connue sur
  les scripts ps1 qui lancent pg_dump). La sauvegarde planifiée C12 est donc
  neutralisée sur ce poste tant que l'exclusion n'est pas posée.
- **Options** :
  1. Exclusion ciblée du dossier `_pgdev/sauvegardes/` (ou du script) dans
     Kaspersky — action manuelle sur le poste, propriétaire uniquement.
  2. Remplacer le script planifié par un binaire compilé — ne supprime pas
     la détection heuristique, travail sans fin.
- **Impact** : **GO** (la sauvegarde réelle est à l'arrêt sur le poste du
  propriétaire tant que pointé).
- **Recommandation** : option 1, action du propriétaire sur son poste.
- **Statut** : OUVERT — action propriétaire.

## D12 — Tests physiques et mise en service (C0/C12/C14)

- **Contexte** : restauration de sauvegarde sur un second poste physique
  (C12 bloqué à 95 % sans cette preuve), deuxième campagne UX humaine (C9/C10),
  installation réelle, import du stock initial, mise en production.
- **Impact** : **GO** + **Score C9/C10/C12/C14**.
- **Recommandation** : ordre proposé — décisions D1-D6 → import test sur base
  jetable → campagne UX → installation sur le poste de caisse → bascule.
- **Statut** : OUVERT — chaque étape exige l'autorisation explicite du
  propriétaire (« aucune installation réelle, aucun import de données réelles,
  aucune mise en production sans mon autorisation »).

## D13 — Branches et PR en attente de fusion

- **Contexte** : les PR #78→#89 (+ #90) du cycle 73 sont **fusionnées**
  (mission 1, `main` = d0fa264 puis PR #91 du cycle 74). Restent en attente :
  - **PR #60** (doc chantier C, septembre) — sort à décider (recommandation
    précédente : fusionner, doc seule) ;
  - **PR #92** (cycle 74 : arbitrage, calendrier des campagnes, pilotage
    99-100 %) — documentation seule ;
  - **pile du cycle 75, à fusionner DANS L'ORDRE** (chacune empilée sur la
    précédente, CI à vérifier après chaque fusion) :
    **#93** (D9 encaissement) → **#94** (D4 remises) → **#95** (D2 mixtes) →
    **#96** (D7+D8) → **#97** (D6+D10) → **#98** (C12-02 alerte sauvegarde) →
    **#99** (D5 audit TTC) → **#100** (correctifs de régression D7/D4).
- **Impact** : **Score global** (`main` n'intègre pas encore le cycle 75).
- **Recommandation** : fusion par le propriétaire dans l'ordre ; chaque fusion
  relance la CI (pytest + Playwright) avant la suivante — ne pas fusionner une
  PR dont les contrôles obligatoires échouent.
- **Statut** : OUVERT — fusion propriétaire uniquement.
