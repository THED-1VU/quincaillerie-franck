# Correspondance suites de vérification ↔ chantiers (cycle 71, écart C13-02)

Chaque suite de ce dossier est listée avec son mode d'exécution, le ou les
chantiers dont elle porte la preuve, et l'orchestrateur qui la rejoue.
Sources : en-tête de chaque fichier `.mjs` (chantier et cycle cités par leur
auteur), `db/outils/verifier_tout.sh`, PR #79 (`executer_suites_reelles.sh` +
job `playwright` de `.github/workflows/ci.yml`).

## Suites réelles — serveur + PostgreSQL réels (13)

| Suite (`npm run …`) | Mode | Chantier(s) prouvé(s) | Ce qu'elle prouve | Orchestration |
|---|---|---|---|---|
| `routes` — `verifier-routes-appelees.mjs` | statique (aucun serveur requis) | transverse C0–C14 (câblage front/back) | aucun écran n'appelle une route morte (régression « chantier A » détectée en cycle 46) | `verifier_tout.sh` étape 4 |
| `cablage` — `verifier-cablage.mjs` | réel (cycle 3) | C9/C10 (en-tête) + C3 (cloisonnement) | connexion réelle des 3 rôles, contenu réseau cloisonné par rôle (agent stock sans prix, comptable sans quantité), jamais la quantité attendue côté client, erreurs en français, 5 largeurs | `verifier_tout.sh` + CI (#79) |
| `vente` — `verifier-vente-reelle.mjs` | réel (cycle 6) | C5 | parcours vente complet, vente à crédit avec PDF réel (en-tête %PDF), remises (cycle 59) | `verifier_tout.sh` + CI (#79) |
| `stock` — `verifier-stock-reel.mjs` | réel (cycle 11, réécrit cycle 52) | C4 | casse/retour/offert avec effets stock réels, case décimale (cycle 60) | `verifier_tout.sh` + CI (#79) |
| `rapports` — `verifier-rapports-reel.mjs` | réel (cycle 12, étendu 67/68) | C8 | exports stock valorisé (cycle 67) et écarts de comptage (cycle 68), téléchargements réels (octets vérifiés) | `verifier_tout.sh` + CI (#79) |
| `inventaire` — `verifier-inventaire-reel.mjs` | réel (cycle 7) | C7 | comptage à l'aveugle, régularisations, historique | `verifier_tout.sh` + CI (#79) |
| `ux` — `verifier-ux-corrections.mjs` | réel (campagne UX-1) | C9 | les 8 constats de `UX_BASELINE.md` §4 bis corrigés et stables | `verifier_tout.sh` + CI (#79) |
| `comptes` — `verifier-comptes-reel.mjs` | réel (cycle 32) | C2 | écran Comptes câblé au serveur, gestion des comptes par le responsable | `verifier_tout.sh` + CI (#79) |
| `caisse` — `verifier-caisse-reel.mjs` | réel (cycle 25/26) | C6 | clôture de caisse réservée au responsable, attendu serveur, écart commenté, historique | `verifier_tout.sh` + CI (#79) |
| `rh` — `verifier-rh-reel.mjs` | réel (cycle 18) | C6 | écran RH câblé, accès réservé | `verifier_tout.sh` + CI (#79) |
| `exploitation` — `verifier-exploitation-reel.mjs` | réel (cycle 51/52) | C12 (sauvegarde, logo) + C8 (cartes du tableau de bord) | voyant sauvegarde par la vraie route, cartes Ventes du jour / Articles offerts, logo téléversé/affiché/supprimé, 403 agent stock | `verifier_tout.sh` + CI (#79) |
| `echappement` — `verifier-echappement-html.mjs` | réel (cycle post-7) | C11 (XSS) sur écrans C5/C8 | une charge HTML/JS dans un nom d'article ne s'exécute jamais (vente, écarts du tableau de bord) | `verifier_tout.sh` + CI (#79) |
| `roles` — `verifier-roles.mjs` | réel (cycle 65) | C3 (matrice des habilitations — l'en-tête dit « chantier C8 », le pilotage du cycle 65 disait « C8/C2 » ; le contenu est la matrice des habilitations + le mot de passe provisoire, soit C3 + C2) | captures par rôle, refus UI redirigé, changement de mot de passe provisoire forcé, cumul de rôles (divergence D2 documentée) | `verifier_tout.sh` UNIQUEMENT — **absente de l'orchestrateur CI de la PR #79** (voir écart ci-dessous) |

## Suites héritées — exclues de toute orchestration (2)

| Suite (`npm run …`) | Mode | Statut |
|---|---|---|
| `affichage` — `verifier-affichage.mjs` | statique (serveur statique `:8080`, cycle 1) | **inutilisable sur écrans connectés** — backend requis ; limite documentée depuis le cycle 59, constatée à nouveau au cycle 61 |
| `flux` — `verifier-flux.mjs` | statique (même périmètre) | idem |

## Écarts d'orchestration connus

1. **`roles` absente de la CI** — `executer_suites_reelles.sh` (PR #79, cycle 62)
   enchaîne 12 suites ; `verifier-roles.mjs` (cycle 65) est postérieure à ce
   script. Ajout recommandé après fusion de la PR #79 : une entrée
   `"roles:verifier-roles.mjs"` dans le tableau `SUITES` du script (le job CI
   exporte déjà `PGDATABASE_PISTE`, la suite s'y intègre sans autre change).
2. **Deux orchestrateurs complémentaires, pas concurrents** —
   `verifier_tout.sh` (poste de développement) enchaîne les 3 couches
   SQL → pytest → 13 suites ; `executer_suites_reelles.sh` (CI) rejoue les
   12 suites Playwright seules, en parallèle du job pytest. Le critère du
   registre « une commande unique rejoue l'ensemble, résultat consolidé »
   est satisfait localement par `verifier_tout.sh` (bilan en fin de sortie,
   code 1 dès qu'une étape échoue) et dans la CI par la combinaison
   `ci.yml` (#79) dès que celle-ci est fusionnée.

## Comment rejouer

```bash
# Poste de développement (PostgreSQL démarré, 3 couches, une seule commande) :
bash db/outils/verifier_tout.sh

# Suite individuelle (serveur réel déjà démarré sur 8010) :
cd maquette/verification && npm run <nom>

# Rejeu de la matrice des rôles isolée (base de piste surchargée par défaut) :
cd maquette/verification && PGDATABASE_PISTE=quincaillerie_test npm run roles
```
