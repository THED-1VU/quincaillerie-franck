# CYCLE 75 — Audit d'impact des décisions validées (avant tout code)

**Date :** 2026-10-23 (cycle 75). **Décisions validées par le propriétaire :**
D2, D4, D5, D6, D7, D8, D9, D10, C12-02. **Restent ouvertes :** D3, C6-02,
C2-01, C7-01, PR #60, D1 (non reprise dans cet ordre), D11 (procédure
soumise, action propriétaire).

Méthode : chaque ligne cite les fichiers exacts lus pendant l'audit —
aucune modification n'est entreprise avant cette cartographie ; aucune
fonctionnalité existante n'est dupliquée.

---

## C75-A — D9 : l'encaissement attribué au compte authentifié réel

| Élément | Constat d'audit |
|---|---|
| Cause | `server/app/routes/ventes.py:210-227` : `SELECT id FROM utilisateurs WHERE role='responsable' LIMIT 1` — l'encaissement est prêté au **premier responsable trouvé**, pas à l'auteur réel (constat chiffré du cycle 66, écart C5-01) |
| Écriture | `ventes.py:399-414` : INSERT dans `ventes (… utilisateur_caisse_id …)` — `session.utilisateur_id` est DÉJÀ disponible (jeton signé, `deps.py`) |
| Schéma | `QuincaillerieFranck_Test/creation_base_donnees.sql:148` : `utilisateur_caisse_id INTEGER REFERENCES utilisateurs(id)` — aucune contrainte de rôle, correctif sans migration |
| Cohérence base | `db/migrations/001_contraintes_domaine.sql:118` (vente payée ⇒ encaisseur NOT NULL), `db/outils/prevol.sql:36` (vente payée sans encaisseur = anomalie pré-vol), index `007:43` |
| Tests existants | AUCUN test pytest ne fige l'ancien comportement — correctif libre ; `server/tests/test_ventes.py` couvre ventes/crédit, à étendre |
| Résistance usurpation | `DemandeVente` (`schemas.py`) n'expose AUCUN champ `utilisateur_caisse_id` — l'API ne peut pas recevoir ce champ du navigateur ; à PROUVER par un test qui tente de l'injecter dans le JSON |
| Périmètres testés exigés | vente normale, vente à crédit (creances.utilisateur_id — déjà l'authentifié, `ventes.py:488-492`), annulation (`annuler_vente` migration 017/031, passe `session.utilisateur_id` — déjà correct), clôture (`caisse.py` lit `calculer_attendu_caisse` — ne dépend pas de l'encaisseur) |
| **Modifications** | 1. `ventes.py` : supprimer la requête « premier responsable », `utilisateur_caisse_id = session.utilisateur_id`, commentaire réécrit (décision D9 2026-10-23). 2. Tests pytest dédiés (agent saisit → encaisseur = agent ; tentative d'injection du champ ignorée). 3. Registre C5-01 → CLOS sur preuve. **Aucune migration.** |

## C75-B — D4 : remise > 10 % ⇒ validation responsable côté serveur

| Élément | Constat d'audit |
|---|---|
| Mécanisme EXISTANT | `ventes.py:254-267` : lecture `parametres.seuil_remise_validation_pct` (valeur `'a_definir'` ⇒ seuil désactivé) ; blocage `ventes.py:315-326` (par ligne) et `ventes.py:366-375` (remise globale) : **403 si l'auteur n'est pas responsable** — vérifié côté serveur, lié à la vente, journalisé par `ventes.utilisateur_id` |
| Paramètre | inséré par `db/migrations/037_remises.sql` à `'a_definir'` ; rejoint le jeu d'essai (`db/tests/00_jeu_essai.sql`, écart C1-04) |
| Décision à implanter | seuil = **10** : migration 051 (premier numéro libre) qui fixe la valeur definitive + garde `a_decider` cohérent ; jeu d'essai aligné |
| Journalisation | la vente au-delà du seuil porte son auteur responsable (`ventes.utilisateur_id` — PK du compte authentifié, jeton signé) ; contrôle journal distinct à évaluer contre `005_journaux_audit` (décision au sous-cycle, sans redondance avec ce qui existe) |
| Écran | `maquette/vente.html` affiche déjà l'erreur serveur ; remise 0 % / = 10 % passent, 10,01 % refusée pour un agent, acceptée pour un responsable |
| Tests exigés par l'ordre | 0 %, 10 % (limite, passe), 10,01 % (refuse un agent, accepte un responsable), remise négative (refusée par GREATEST/schéma — à prouver), contournement : prix_unitaire négocié (ligne 286-291 : la remise est RECALCULÉE depuis le prix catalogue côté serveur, jamais crus sur parole) |
| **Modifications** | migration 051 (valeur 10), jeu d'essai, tests pytest dédiés (5 cas), contrôle Playwright vente > seuil |

## C75-C — D2 : paiements mixtes sur une même vente

| Élément | Constat d'audit |
|---|---|
| État actuel | `ventes.mode_paiement` UNIQUE (`creation_base_donnees.sql:149-151` : especes/orange_money/mtn_momo/credit_client/autre) ; recette UNIQUE par vente (`ventes.py:493-500`, table `transactions`, index unique partiel migration 002) |
| Comptabilité par mode | `calculer_attendu_caisse` (migration 019, appelée par `caisse.py:56`) calcule l'attendu **par mode** ; clôture comptabilise 4 compteurs (especes, orange_money, mtn_momo, autre) — `caisse.py:164-166` |
| Crédit | chemin DÉDIÉ et séparé (045/047 : `creances`, règlements partiels, retour client) — les paiements mixtes ne concernent QUE les ventes payées, jamais `credit_client` dans la décomposition |
| Annulation | `annuler_vente` (017/031) : contre-passe par UNE dépense du montant total — préservée ; la décomposition par mode reste lisible dans la nouvelle table (statut annulé, jamais supprimé) |
| **Modifications prévues** | **Migration 052** : table `ventes_paiements (vente_id, mode, montant)` + CHECK modes (sans credit_client) + CHECK montant > 0 + invariant **somme(paiements) = total_ttc de la vente** (trigger/01_protections) + **backfill** des ventes payées existantes (une composante chacune) ; API : `DemandeVente.paiements[]` optionnel (somme vérifiée côté serveur = total), reçu PDF affiche la décomposition ; `calculer_attendu_caisse` agrège `ventes_paiements` ; rapports par mode idem. Tests : transactionnels (rollback), concurrence, non-régression comptable (invariant 01_protections), clôture sans double comptage |
| Numérotation | 051 = D4 ; 052 = D2 (aucune migration publiée n'est modifiée rétroactivement) |

## C75-D — D7 (menus = toutes les permissions accordées) + D8 (comptage)

| Élément | Constat d'audit |
|---|---|
| Backend déjà conforme | connexion renvoie DÉJÀ la liste `roles` complète (`auth.py:82-103`, `roles_utilisateur()` migration 035) ; `exiger_role` (`deps.py:94-110`) accepte les rôles effectifs — l'API est déjà « union » |
| Défaut UI (C3-03) | `/moi` (`demonstration.py:119-139`) n'expose QUE le rôle principal ; `maquette/api.js:185` : `rolesAutorises.includes(profil.role)` — gate d'écran sur rôle principal SEUL |
| D8 | comportement déjà conforme à la décision : l'écran inventaire refuse le responsable (comptage agent stock, à l'aveugle), le responsable supervise : voit les écarts et régularise (migration 032) ; l'ordre dit « supervise et valide » = flux existant — à VALIDER par tests, pas à réécrire |
| **Modifications** | 1. `/moi` renvoie aussi `roles` (fonction `roles_utilisateur()` déjà GRANTée à qf_app). 2. `api.js` : gate d'écran = union (`profil.roles` avec repli session stockée puis rôle principal) ; accueil initial reste `PAGE_ACCUEIL_PAR_ROLE` (ergonomie, pas une permission). 3. Mise à jour tests : `test_cumul_roles.py`, `test_matrice_roles.py`, suites Playwright `roles` + `cablage` (redirections d'écrans pour comptes cumulés), documents `MATRICE_ROLES_AKUMA.md` + fiche R2 §9 (comportement D7 option union, décision 2026-10-23). 4. D8 : tests existants conservés + registre C3-02 CLOS sur preuve |
| Sécurité | AUCUN contournement : la gate UI reste un confort ; le garde réel reste le serveur (RLS + exiger_role) — vérifié par la matrice |

## C75-E — D6 (sessions ≤ 480 min) + D10 (2FA reportée, mesures compensatoires)

| Élément | Constat d'audit |
|---|---|
| Durée | `auth.py:82-91` : `duree_session_minutes` = config.ini, sinon `duree_session_minutes_decidee()` (paramètre base) ; expiration vérifiée à chaque requête (`securite.py:148` « Jeton expiré, reconnectez-vous ») |
| Révocation | migration 018 (`revoquer_jeton`), déconnexion = révocation du jeton COURANT (`auth.py`, 3 tests pytest existants `test_deconnexion_*`) |
| Prolongation | AUCUNE route de renouvellement de jeton dans le code — à PRUVER par test (jeton à 480 min + 1 s refusé) |
| D6 à implanter | vérification par tests (480 max, expiration, révocation, déconnexion, rejet expiré/révoqué, pas de refresh) + consigner la valeur 480 (décision D6) — la bascule du paramètre reste liée à C2-01 (ouvert) |
| D10 mesures compensatoires V1 (déjà en place) | bcrypt cost 12 ; mot de passe provisoire forcé (050) ; limiteur de débit partagé (038) sur /auth/connexion ; révocation des jetons (018) ; session ≤ 480 min ; RLS par rôle/site (029) ; audit non destructible (004/005) → à DOCUMENTER (sans code nouveau) |
| **Modifications** | tests pytest dédiés (expiration 480, rejet refresh inexistant, révocation) + note D10 documentée ; rien d'autre |

## C75-F — C12-02 : alerte visible d'échec/absence de sauvegarde

| Élément | Constat d'audit |
|---|---|
| Socle EXISTANT | `sauvegarder.ps1` écrit `_pgdev\sauvegardes\dernier_etat_sauvegarde.json` (resultat SUCCES/ECHEC, horodatage, chemin — voir `git show HEAD:db/outils/sauvegarder.ps1`, version Git lisible sans exécution) ; route `GET /exploitation/derniere-sauvegarde` (`exploitation.py:56`, `FICHIER_ETAT_PAR_DEFAUT`, surcharge test via `QF_FICHIER_ETAT_SAUVEGARDE` — prouvé au cycle 64) |
| Exigences de l'ordre | 4 états : dernière réussie / dernier échec / absence de récente / inconnu ; JAMAIS de succès sans preuve (= le fichier JSON écrit par le script, seul ; aucune déduction) ; tests simulés sûrs — **sauvegarder.ps1 n'est JAMAIS exécuté** (quarantaine Kaspersky, limite §7) |
| **Modifications** | 1. `exploitation.py` : endpoint interprété (états normalisés : `succes(date)`, `echec(date, motif)`, `absent_depuis_recente`, `inconnu` — fichier absent ou illisible). 2. Alerte visible sur `tableau-bord.html` (responsable seul) : bandeau persistant selon état. 3. Tests : pytest avec faux fichiers d'état (4 cas + JSON corrompu), Playwright affichage des 4 états avec `QF_FICHIER_ETAT_SAUVEGARDE` pointé vers des fichiers de test |

## C75-G — D5 : politique TTC auditée

| Élément | Constat d'audit |
|---|---|
| Constat | prix saisis TTC partout : `ventes.py:334-386` (TTC par ligne, TVA EXTRAITE sur le total — jamais ligne à ligne), `taux_tva` = paramètre base (`parametres`), reçu PDF (`ventes.py:558+`) et rapports/exports affichent sous_total_ht/taux_tva/montant_tva/total_ttc déduits, jamais saisis |
| **Modifications** | AUCUN code prévu — audit documenté ; questions comptable listées (taux_tva applicable et sa valeur réelle, exigence de ventilation HT ligne à ligne sur les documents, mention fiscale du numéro de facture) — **aucun taux ni règle fiscale inventé** ; livrable = note jointe au registre (C1-02 partiellement soldée : TTC confirmé, ventilation = question comptable ouverte avant import réel) |

---

## Dépendances d'exécution (ordre de l'ordre §3)

A → B → C → D → E → F → G, régression ciblée à chaque sous-cycle, régression
COMPLÈTE (pytest + SQL + 13 suites) en fin de cycle. Branches empilées,
une PR par sous-cycle, fusion propriétaire ; CI verte obligatoire avant toute
demande de fusion.

## Règles rappelées par l'ordre (§7) — respectées

Aucun GO production · aucune installation réelle · aucun import réel ·
aucune exclusion antivirus · `sauvegarder.ps1` jamais exécuté · D3, C6-02,
C2-01, C7-01, PR #60 restent ouverts · migrations jamais modifiées
rétroactivement (051 = D4, 052 = D2).
