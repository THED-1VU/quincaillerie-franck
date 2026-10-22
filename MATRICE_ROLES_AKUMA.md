# Matrice complète des rôles — Akuma (cycle 65, chantier C8/C2/C3)

État vérifié **par exécution réelle** le 2026-10-21 sur la base de test
`quincaillerie_c65` (schéma + migrations 000→050 + jeu d'essai). Trois
niveaux de preuve, aucun ne se substituant aux autres :

1. **API** — `server/tests/test_matrice_roles.py` : 56 routes × 3 rôles,
   ≈ 390 requêtes réelles. Convention : rôle autorisé ⇒ jamais 401/403 ;
   rôle interdit ⇒ exactement 403 ; anonyme ⇒ 401.
2. **SQL** — `server/tests/test_privileges_sql_roles.py` : 10 sondes sous
   chaque rôle PostgreSQL (`SET LOCAL ROLE`, la même bascule que
   `database.connexion_pour()` en production). C'est le contrôle qui compte :
   un bug applicatif ne peut au pire répondre 403 à tort — jamais fuiter une
   donnée interdite, car PostgreSQL est le vrai garde.
3. **UI** — `maquette/verification/verifier-roles.mjs` : 30 contrôles
   Playwright, 22 captures dans `maquette/captures/roles/`. Chaque écran
   protégé appelle `exigerSession(roles)` (`maquette/api.js:166`), qui
   vérifie RÉELLEMENT le profil auprès du serveur (GET `/moi`) puis redirige
   : rôle non autorisé → écran d'accueil de ce rôle (jamais une erreur nue).

## 1. Rôles et comptes

| Rôle PostgreSQL | Libellé UI | Compte de test | Mot de passe de test |
|---|---|---|---|
| `qf_responsable` | Responsable | `resp` | `ResponsableTest123` |
| `qf_agent_comptabilite` | Agent comptabilité (caissier fusionné, addendum h) | `magasin.compta` | `AgentComptaTest123` |
| `qf_agent_stock` | Agent stock | `magasin.stock` | `AgentStockTest123` |

Le rôle **caissier** n'existe pas en tant que tel : fusionné avec agent
comptabilité (décision propriétaire, addendum point h — encaisse ET saisit).
Question ouverte associée : la **visibilité des prix** de ce rôle sur
l'écran de vente — voir `DECISIONS_PROPRIETAIRE.md`, jamais tranchée ici.

## 2. Matrice UI — écran × rôle

Source : appels `exigerSession(...)` au chargement de chaque écran.

| Écran | Responsable | Comptabilité | Stock |
|---|:-:|:-:|:-:|
| `connexion.html` | public | public | public |
| `changer-mot-de-passe.html` | tout rôle authentifié (session requise, garde spéciale) | idem | idem |
| `vente.html` | ✅ | ✅ | ❌ |
| `tableau-bord.html` | ✅ | ❌ | ❌ |
| `inventaire.html` | ❌ | ❌ | ✅ |
| `stock.html` | ✅ | ❌ | ✅ |
| `clients.html` | ✅ | ✅ | ❌ |
| `rapports.html` | ✅ | ✅ | ✅ |
| `comptes.html` | ✅ | ❌ | ❌ |
| `rh.html` | ✅ | ❌ | ❌ |
| `declarations.html` | ✅ | ❌ | ❌ |
| `cloture-caisse.html` | ✅ | ❌ | ❌ |

Accueil après connexion (`PAGE_ACCUEIL_PAR_ROLE`, `maquette/api.js:44`) :
responsable → tableau de bord, comptabilité → vente, stock → inventaire.

> **Divergence documentée D1** : l'API autorise le responsable sur
> `GET /inventaire/articles-a-compter` et `POST /inventaire/comptages`
> (règle « comptage supervisable par le responsable »), mais `inventaire.html`
> ne gate que sur `["agent_stock"]` — choix d'ergonomie revendiqué par
> l'écran lui-même (comptage à l'aveugle = tâche d'agent). Non corrigé :
> décision d'ergonomie, pas défaut d'habilitation. Le périmètre API reste
> strictement identique au besoin (le responsable lit les écarts sur
> `tableau-bord.html` et `declarations.html`, il ne compte pas).

## 3. Matrice API — route × rôle (58 routes, exhaustif)

Sources : décorateurs `exiger_role(...)` de `server/app/routes/`, revus
ligne à ligne au cycle 65. `TOUS` = toute session valide (sans `exiger_role`).
Les routes sans jeton renvoient 401 ; les routes publiques sont listées.

**Public (3)** — `POST /auth/connexion`, `GET /sante`,
`GET /configuration/logo`.

**Tous rôles authentifiés (6)** — `POST /auth/deconnexion`,
`POST /auth/changer-mot-de-passe` (aussi accessible au compte au mot de
passe provisoire, seule route métier qui le soit),
`GET /articles`, `GET /moi`.

**Responsable seul (33)** — administration des comptes
(`GET/POST /admin/comptes`, `PATCH /admin/comptes/{id}/actif`,
`PATCH /admin/comptes/{id}/mot-de-passe`, `POST /admin/comptes/{id}/deverrouiller`),
`POST /ventes/{id}/annuler`, inventaire en lecture et régularisation
(`GET /inventaire/ecarts`, `GET /inventaire/historique-comptages`,
`GET /inventaire/ecarts-ventes`, `POST /inventaire/ecarts-ventes/{id}/regulariser`,
`POST /inventaire/ecarts/{id}/regulariser`), validation des déclarations
stock (casse, retours client, articles offerts — 3 routes),
tableau de bord (`GET /tableau-bord/alertes-stock`,
`GET /tableau-bord/articles-offerts-en-attente`,
`GET /tableau-bord/credit-client`), caisse
(`GET /caisse/attendu`, `POST /caisse`, `GET /caisse`), exploitation
(`GET /exploitation/derniere-sauvegarde`), logo
(`POST/DELETE /configuration/logo`), RH complète
(`POST /rh/employes`, `GET/POST /rh/absences-conges`,
`GET/POST /rh/avances-salaire`, `POST /rh/avances-salaire/{id}/rembourser`),
export du stock valorisé (`GET /rapports/stock`, cycle 67 — écart C4-02,
porte `prix_achat` donc réservé au rôle qui en a le privilège) et export
des écarts de comptage (`GET /rapports/ecarts-comptage`, cycle 68 — écart
C7-03, joint les régularisations et valorise à prix d'achat, mêmes
privilèges colonnes 008/012).
clients en écriture (`POST /clients`, `PUT /clients/{id}`,
`PATCH /clients/{id}/actif`).

**Responsable + comptabilité (13)** — vente (`GET /ventes/synthese-jour`,
`GET /ventes/parametres`, `GET /ventes/vendeurs`, `POST /ventes`,
`GET /ventes/{id}/recu`), rapports de vente
(`GET /rapports/ventes`, `GET /rapports/ecarts-prix-vendeurs`),
déclarations d'articles offerts (`POST/GET /stock/articles-offerts/declarations`),
transactions (`POST/GET /transactions`), clients en lecture et règlements
(`GET /clients`, `POST /clients/{id}/reglements`),
`GET /rh/employes`.

**Responsable + stock (11)** — articles (`POST /articles`,
`PUT /articles/{id}`), comptage (`GET /inventaire/articles-a-compter`,
`POST /inventaire/comptages`), mouvements de stock
(`POST /stock/entrees`, `POST /stock/transferts`,
`POST /stock/retours-fournisseur`), déclarations casse et retours client
(`POST/GET /stock/casse/declarations`,
`POST/GET /stock/retours-client/declarations`).

**Les trois rôles (1)** — `GET /rapports/articles`.

Résultat d'exécution : **zéro divergence** sur l'ensemble de la matrice
(une requête par case, échecs collectés puis affichés d'un coup — le rapport
se lit comme un tableau, pas un premier échec qui masque les suivants).

## 4. Matrice SQL — privilèges par rôle PostgreSQL

Attendus = `GRANT` par colonne (migration 008 et suivantes). Sondes réelles
sous chaque rôle (pas via l'API) :

| Donnée | Responsable | Comptabilité | Stock |
|---|:-:|:-:|:-:|
| `articles.prix_achat` | ✅ | ❌ | ❌ |
| `articles.prix_vente` | ✅ | ✅ | ❌ |
| `stocks_sites.quantite_stock` | ✅ | ❌ | ✅ |
| `comptages_stock.quantite` | ✅ | ❌ | ✅ |
| `comptages_stock.quantite_attendue` (comptage aveugle, 012/029) | ✅ | ❌ | ❌ |
| `clotures_caisse` (toutes colonnes) | ✅ | ❌ | ❌ |
| `utilisateurs.mot_de_passe_hash` | ❌ | ❌ | ❌ |
| `INSERT mouvements_stock` direct (type vente) | n/a (fonctions SECURITY DEFINER) | n/a | ❌ |

Le comptage **aveugle** est prouvé au niveau SQL : la colonne
`quantite_attendue` — celle qui trahirait le stock théorique pendant un
inventaire — n'est lisible par aucun des trois rôles applicatifs ; le moteur
d'écart la calcule en `SECURITY DEFINER`.

## 5. Exports Excel/PDF

Cinq routes d'export, toutes derrière `exiger_role` et servies
par `telechargerFichier()` (jeton en en-tête, jamais en URL) :

| Route | Rôles | Formats |
|---|---|---|
| `GET /rapports/articles?format=` | R, S, C | xlsx, pdf |
| `GET /rapports/stock?format=` | **R seul** (cycle 67, écart C4-02) | xlsx (feuille « totaux par site »), pdf |
| `GET /rapports/ecarts-comptage?format=&date_debut=&date_fin=` | **R seul** (cycle 68, écart C7-03) | xlsx (feuille « totaux »), pdf |
| `GET /rapports/ventes?...&format=` | R, C | xlsx, pdf |
| `GET /rapports/ecarts-prix-vendeurs` | R, C | tableau (JSON) |

L'export stock porte `prix_achat` : c'est précisément pourquoi il est
réservé au responsable (privilège colonne 008) — l'agent stock conserve
son export catalogue sans prix d'achat, l'agent comptabilité n'a même
pas les quantités. L'habilitation des exports est couverte par la matrice
API (les mêmes routes répondent 403 hors rôle, avec ou sans `?format=`).

## 6. Cloisonnement par site

Non répété ici au détail : couvert par `server/tests/test_cloisonnement_site.py`
(preuve RLS en SQL direct hors de toute ligne applicative — sous
`qf_agent_stock` avec `qf.site_id='1'`, une requête demandant
explicitement `site_id=2` ne renvoie rien ; contre-épreuve responsable :
les deux sites visibles). Aucune route n'accepte de `site_id` client.

## 7. Sessions et authentification

- Connexion : bcrypt (`$2a$`, 12 tours) via pgcrypto, limite de débit
  10/min par identifiant (cycle 44), verrouillage de compte par tentatives
  échouées (base), réinitialisation et déverrouillage par le responsable.
- Jeton signé + `jti` révocable (cycle 21-22) : `POST /auth/deconnexion`
  révoque réellement — la matrice le prouve (re-connexion nécessaire après
  la case).
- **Changement du mot de passe provisoire (correctif cycle 65)** : la
  colonne `doit_changer_mot_de_passe` existait depuis le cycle 38 (remise à
  zéro par le responsable) mais n'était **contrôlée nulle part** — un compte
  provisoire accédait à toute l'application. Désormais :
  - migration 050 `changement_mdp_requis()` (SECURITY DEFINER, seul `qf_app`
    en a le droit — cf. la contrainte des privilèges de `qf_app`) ;
  - `deps.py` l'évalue à chaque requête authentifiée : drapeau vrai ⇒ 403
    « Vous devez changer votre mot de passe provisoire avant de continuer. »
    sauf sur `/auth/changer-mot-de-passe` et `/auth/deconnexion` ;
  - `connexion.html` et `api.js:180` renvoient vers
    `changer-mot-de-passe.html` (garde anti-boucle sur l'écran lui-même) ;
  - preuves : `server/tests/test_changement_mdp_force.py` (3 tests : blocage
    403 de toutes les routes, refus 401 du mauvais actuel puis libération
    réelle, imposition du drapeau par le responsable sur un jeton encore
    valide) + 6 contrôles Playwright (captures `force-01` à `force-04`).

## 8. Cumul de rôles (addendum h, cycle 43)

Un compte peut porter plusieurs rôles (`utilisateurs_roles`). L'API évalue
**tous** les rôles du compte (test_cumul_roles.py, cycle 43) ; l'UI
(`exigerSession`) ne regarde que le **rôle principal** (`/moi.role`) et
redirige hors des écrans du rôle secondaire.

> **Divergence documentée D2** : un compte stock+comptabilité atteint
> `GET /ventes/parametres` en API (200 mesuré), mais `vente.html` le
> renvoie vers `inventaire.html` (capture
> `cumul-01-ui-refuse-perimetre-secondaire.png`). Divergence
> volontairement documentée, non corrigée : décider si l'UI doit adopter
> les rôles secondaires (options dans `DECISIONS_PROPRIETAIRE.md`).

## 9. Divergences et anomalies relevées au cycle 65

| # | Gravité | Description | Décision |
|---|---|---|---|
| D1 | P3 | `inventaire.html` refuse le responsable alors que l'API l'autorise à compter | ergonomie revendiquée — à confirmer |
| D2 | P3 | UI cumul de rôles = rôle principal seul, API = tous les rôles | décision ergonomique à prendre |
| D3 | P2 | Attribution `utilisateur_caisse_id` incohérente (`server/app/routes/ventes.py:210-227`) — relevée en exploration, à auditer au cycle 66 | propriétaire |
| D4 | P2 | Visibilité des prix du caissier sur l'écran de vente — jamais tranchée | propriétaire (obligatoire avant GO) |

Aucun de ces points n'est un trou d'habilitation : les accès réels (API et
SQL) sont exactement ceux du tableau, et chaque divergence est soit prouvée
sans effet de sécurité, soit une décision métier explicitement laissée ouverte.
