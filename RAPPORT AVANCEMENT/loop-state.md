# État du cycle de finalisation — Quincaillerie Franck

Référentiel fixe `C0`–`C14` — **ne jamais renuméroter**.
Cycle décrit dans `.agents/skills/finalisation-loop/SKILL.md`.

- Date d'initialisation : **2026-09-10**
- Dernier cycle fusionné : **Cycle 1 — maquette du parcours (C9)**, 2026-09-11
- Décision d'architecture : **application web unique servie sur le réseau local**
  (PC de caisse au navigateur plein écran + téléphones). Pas de bureau PyQt6.
- Règle : un score ne monte que sur **preuve d'exécution réelle**.

---

## Scores de départ

| Code | Chantier | Score | Base d'évaluation |
|------|----------|:-----:|-------------------|
| C0 | Infrastructure et dépôt | **10 %** | Dépôt Git + GitHub privé créés dans ce cycle de cadrage ; `.gitignore` en place. Pas encore de CI, pas de scripts de build, pas d'environnement reproductible, pas de migrations. |
| C1 | Base de données et intégrité | **35 %** | Évalué sur pièces (`creation_base_donnees.sql`). Structure et types corrects (NUMERIC partout, FK présentes, 2 tables d'audit, index de filtre). Mais quasi aucune règle d'intégrité défendue par la base : pas de CHECK de domaine, pas de trigger, `ecart` non calculé, pas de verrou anti-survente, cascades destructrices sur l'audit, connexion en superutilisateur, pas de RLS, pas de table de paramètres. Voir `MODELE_DONNEES.md` §4. |
| C2 | Authentification et comptes | **0 %** | Non vérifié par exécution. Le schéma prévoit hash, `tentatives_echouees`, `doit_changer_mot_de_passe` ; aucun journal de connexion, aucune session/jeton, aucun audit de compte. |
| C3 | Habilitations et cloisonnement des rôles | **0 %** | Non vérifié. CHECK sur `role`, `site_id` présent, mais pas de contrainte rôle↔site, pas de RLS, cloisonnement supposé uniquement applicatif (« masquer l'UI ne suffit pas »). Rôle « caissier » non tranché (addendum h). |
| C4 | Articles et stock | **0 %** | Non vérifié. Règle des 20 %, seuil non modifiable, mouvements tracés : présents au CDC, absents de la base (défaut `seuil_alerte = 5`, aucun trigger). Pas de transfert inter-sites (addendum a), pas de retours/casse (addendum f). |
| C5 | Ventes et facturation | **0 %** | Non vérifié. Workflow `en_attente/payee/annulee` modélisé. Manquent : n° facturier + vendeur (addendum c), créance client (addendum b), audit d'annulation, cohérence des montants, génération du n° de facture, arbitrage saisie a posteriori vs blocage (addendum e). |
| C6 | Comptabilité et RH | **0 %** | Non vérifié. `transactions`, `employes`, `absences_conges`, `avances_salaire` présents. Manquent : clôture de caisse (addendum g), contre-passation d'annulation, `transactions.vente_id` non unique, audit des corrections. |
| C7 | Inventaire et écarts | **0 %** | Non vérifié. `comptages_stock` + comptage à l'aveugle modélisés. `ecart` stocké et non contraint (faille anti-vol) ; pas d'unicité par créneau ; pas de rattachement des écarts de survente au comptage (addendum e). |
| C8 | Tableaux de bord et rapports | **0 %** | Non vérifié. Exigés au CDC (consolidé/par site, alertes, exports Excel/PDF avec gating du prix par rôle) ; aucune preuve d'exécution. |
| C9 | Ergonomie et UI *(priorité 1)* | **25 %** | Cycle 1. Maquette non câblée des 4 écrans clés (`maquette/`), thème unique, données simulées isolées. Vérifié par exécution : 20/20 captures aux 5 largeurs sans débordement, 0 erreur console, cibles ≥ 44 px, ajout au panier en 2 actions, comptage à l'aveugle sans quantité attendue dans la page (`maquette/verification/`, 14/14). **Plafonné à 60 %** tant que le tableau de mesures humaines de `UX_BASELINE.md` §4 n'est pas rempli (vitesse, compréhension des erreurs, clavier réel). Reste : implémentation réelle des écrans, câblage, mesures chronométrées. |
| C10 | Mobile et API web *(priorité 1)* | **0 %** | Diagnostic : « Web API or mobile interface : Not found ». Aucune interface mobile dans le livré. Priorité n°2 du propriétaire non couverte. |
| C11 | Sécurité applicative | **0 %** | Non vérifié (le « Sécurité : 100 % » du diagnostic est un artefact : mots-clés trouvés dans le script de diagnostic lui-même). Connexion superutilisateur, `secret_key` d'exemple, pas de RLS, cloisonnement non prouvé côté requêtes. |
| C12 | Sauvegarde et exploitation | **0 %** | Diagnostic : « Backup and restore procedure : Not found ». Aucun script, aucune procédure. Onduleur, RPO/RTO, mise à jour des postes : à définir (addendum i). |
| C13 | Tests automatisés et qualité | **0 %** | Aucun test automatisé détecté (« Tests identifiable : Found » = simple présence du mot « test » dans les guides). Aucune suite exécutable. |
| C14 | Documentation et livrables | **40 %** | Évalué sur pièces. Documentation d'usage/recette solide : CDC détaillé, 2 guides testeur, dossier de recette, guide d'installation. `MODELE_DONNEES.md`, `PERIMETRE_LIVRE.md`, `ADDENDUM_CAHIER_DES_CHARGES.md` produits dans ce cycle. Manquent (CDC §7) : code source, scripts de fabrication des exécutables, scripts + guide de sauvegarde/restauration. |

**Moyenne indicative après cycle 1 : ≈ 7,9 %** (C0 10, C1 35, C9 25, C14 40, autres 0).
Cette moyenne n'est pas un objectif : chaque chantier est mené à 100 % séparément.

---

## Journal des cycles

### Cycle 0 — Cadrage (2026-09-10)

- **Phase 1 — Constat** : code source inaccessible (audit antérieur, négatif).
  Matière disponible : `creation_base_donnees.sql`, `config.example.ini`, deux
  guides testeur, dossier de recette, cahier des charges, deux exécutables de
  référence. Diagnostic automatisé confirme : pas de sauvegarde, pas de script de
  build, pas d'interface mobile dans le livré.
- **Phase 2 — Objectif** : produire les 5 livrables de cadrage (rétro-spec du
  modèle de données, rétro-spec fonctionnelle, dépôt Git + GitHub privé,
  addendum au cahier des charges, cycle de finalisation + état initial).
  Critère de sortie : les 5 livrables existent, la branche `main` est poussée
  sur le dépôt privé `THED-1VU/quincaillerie-franck`, aucun secret ni exécutable
  versionné.
- **Phase 3 — Branche** : `main` (cycle de cadrage, pas de code applicatif).
- **Phase 4 — Vérification** : `git log` sur `main`, `git ls-files` ne contient
  ni `*.exe` ni `config.ini`, dépôt visible en privé sur GitHub.
- **Phase 5 — Score** : C0 0 % → 10 %, C1 0 % → 35 % (sur pièces),
  C14 0 % → 40 % (sur pièces). Aucun autre chantier touché.
- **Reste à faire** : obtenir du propriétaire les décisions des points **d**
  (fiscalité), **e** (saisie a posteriori vs blocage) et le choix
  d'**architecture cible** avant d'ouvrir les cycles C4 / C5 / C9 / C10.

### Cycle 1 — Maquette du parcours (C9) — 2026-09-11

- **Phase 1 — Diagnostic** : C9 à 0 %, aucune interface évaluable (audit statique
  « Ergonomie PC : 0 % » = non mesurable). Architecture désormais actée :
  application web unique servie sur le LAN.
- **Phase 2 — Objectif** : maquette **fonctionnelle mais non câblée** de 4 écrans
  (connexion, vente PC de caisse, tableau de bord responsable mobile, comptage
  d'inventaire à l'aveugle) en HTML/CSS/JS sans chaîne de build, thème unique,
  données simulées isolées. Critère de sortie : serveur qui démarre, 4 écrans
  affichés, captures aux 5 largeurs sans débordement, ajout au panier ≤ 2 actions,
  quantité attendue absente de l'écran **et** du code sur le comptage, +
  `UX_BASELINE.md` avec protocole de mesure humaine et plafond C9 à 60 % tant
  qu'il n'est pas rempli.
- **Phase 3 — Action** : branche `cycle-1-maquette-ux`. Créé `maquette/`
  (`theme.css`, `styles.css`, `donnees-simulees.js`, `index.html` + 4 écrans,
  `favicon.svg`, `README.md`) et `maquette/verification/` (2 scripts Playwright).
  Aucun code applicatif, aucune connexion base.
- **Phase 4 — Vérification par exécution** :
  - `py -m http.server 8080` → les 5 ressources et 4 écrans répondent `200`.
  - `maquette/verification/verifier-affichage.mjs` : **20/20** cas
    (4 écrans × 360/390/768/1366/1920 px), `débordement=false` partout,
    **0 erreur console**, cible tactile minimale **44 px**. 20 captures écrites
    dans `maquette/captures/`.
  - `maquette/verification/verifier-flux.mjs` : **14/14** contrôles — connexion
    (erreurs près du champ, couple valide → écran de vente), vente (« robi » +
    `Entrée` = +1 ligne en **2 actions** ; article déjà présent → quantité +1
    sans doublon ; focus qui revient sur la recherche ; `F4` change le paiement ;
    `F9` = **une** confirmation puis succès ; **0** fenêtre superposée),
    inventaire (tableau de données réduit à id/nom/unité ; champ vide au départ ;
    `Entrée` → article suivant, progression `2 / 5`).
  - Un débordement de 17 px détecté à la 1re passe (badge « facturier papier »
    sur l'écran de vente à 360 px) → corrigé (retour à la ligne du bandeau
    sous 720 px) → re-vérifié : 0 échec.
- **Phase 5 — Mémoire** : C9 **0 % → 25 %** (plafonné à 60 % via `UX_BASELINE.md`).
  Commit sur `cycle-1-maquette-ux`, PR vers `main`, fusion après vérification.
- **Reste à faire (C9)** : implémenter les écrans réels et les câbler ; faire
  remplir le tableau de mesures humaines de `UX_BASELINE.md` §4.

---

## Prochain cycle — sélection

1. **Contrôle de boucle** (sans code) : vérifier que le cycle 1 a bien parcouru
   les 5 phases, que le score C9 est adossé à des preuves, et l'état de Git.
2. **Cycle 2 — C1** : migration corrective du schéma (CHECK de domaine, `ecart`
   calculé, `CHECK (quantite_stock >= 0)`, cascades d'audit en `RESTRICT`, table
   `parametres`, rôle applicatif non superutilisateur, tables d'audit
   manquantes). Prérequis : PostgreSQL disponible sur la machine.
3. **Cycle 3 — C2 / C3 / C11** : noyau serveur (FastAPI en couches),
   authentification, habilitations appliquées au niveau des requêtes SQL,
   cloisonnement par site, journalisation.
4. **C0** — environnement reproductible (dépendances figées, CI minimale) :
   à intégrer tôt, débloque la vérification automatisée des cycles suivants.
