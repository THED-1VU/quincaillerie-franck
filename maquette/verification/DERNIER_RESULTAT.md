# Dernier résultat de vérification — maquette (chantiers C9/C10)

Ce fichier est une **trace**. Les preuves restent rejouables depuis
`maquette/verification/` (`npm run affichage`, `npm run flux`, ou directement
`node verifier-cablage.mjs`).

## Cycle 5 — câblage sur le noyau serveur (2026-09-12)

Exécuté le **2026-09-12** sur `http://127.0.0.1:8010/app/` (serveur réel
`uvicorn app.main:app`, écrans servis par `StaticFiles` sous `/app`), Google
Chrome via Playwright (`channel: "chrome"`), base PostgreSQL de développement
réinitialisée par le script lui-même (`db/tests/00_jeu_essai.sql` + mots de
passe bcrypt réels des 3 comptes de test).

### `verifier-cablage.mjs` — **73 / 73**

- Connexion réelle (`POST /auth/connexion`) pour les 3 rôles, redirection vers
  le bon écran d'accueil.
- Accès direct à l'écran d'un autre rôle → reredirigé ; sans session → renvoyé
  à la connexion (3 écrans testés).
- Agent stock : `/articles` ne contient **aucun** champ de prix/montant.
  Agent comptabilité : `/articles` ne contient **aucun** champ de
  quantité/seuil, mais contient bien `prix_vente`. Les deux : filtré au bon
  site (RLS du cycle 2/3 exploitée jusqu'à l'écran).
- **Point le plus sensible** : après rechargement de la page d'inventaire,
  aucune occurrence de « quantité attendue » (ni variante) dans le HTML rendu,
  dans le code source de la page, ni dans les réponses réseau observées.
- Messages d'erreur serveur toujours en français, près du champ : champ vide,
  mot de passe erroné (message exact du serveur), panne réseau simulée
  (jamais de message brut).
- Recherche réelle dans le catalogue : un article de l'autre site ne
  ressort pas ; validation de vente clairement annoncée « SIMULATION »
  (aucune route d'écriture inventée).
- Tableau de bord responsable : ventes du jour réelles et consolidées
  (`GET /ventes/synthese-jour`, 2 sites, total correct) ; les 2 cartes non
  câblées portent explicitement « donnée simulée ».
- Aucun débordement horizontal ni cible tactile < 44 px sur mobile, aux
  5 largeurs, sur les 4 écrans.
- **Trouvé par ce script puis corrigé pendant le cycle** : les nouveaux
  boutons de déconnexion (`min-height:auto` en ligne) faisaient descendre la
  cible tactile la plus petite à 32 px sur 3 écrans à 3 largeurs — supprimé,
  le thème impose déjà 44 px par défaut sur `.btn`. Et : la bannière
  d'avertissement de l'écran d'inventaire contenait elle-même, en toutes
  lettres, la phrase interdite « quantité attendue » — reformulée sans perdre
  le sens, pendant que la note d'aide voisine (guillemets français, pas de
  fuite) ne déclenchait à juste titre aucune alerte.
- Non-régression : suite pytest du serveur rejouée après ce cycle —
  **toujours 36/36**.

20 captures régénérées dans `../captures/` (5 largeurs × 4 écrans, sur les
écrans réellement câblés).

---

## Cycle 1 — maquette non câblée (2026-09-11)

Exécuté le **2026-09-11** sur `http://127.0.0.1:8080/` (serveur `py -m http.server 8080`),
Google Chrome via Playwright (`channel: "chrome"`).

## `verifier-affichage.mjs` — 20 / 20

4 écrans × largeurs 360 / 390 / 768 / 1366 / 1920 px.

| Écran | 360 | 390 | 768 | 1366 | 1920 |
|---|:-:|:-:|:-:|:-:|:-:|
| connexion | ✅ | ✅ | ✅ | ✅ | ✅ |
| vente | ✅ | ✅ | ✅ | ✅ | ✅ |
| tableau-bord | ✅ | ✅ | ✅ | ✅ | ✅ |
| inventaire | ✅ | ✅ | ✅ | ✅ | ✅ |

- `débordement horizontal = false` sur les 20 cas.
- `0` erreur console / exception JS sur les 20 cas.
- Cible tactile interactive minimale mesurée : **44 px** (bouton « retirer » du
  panier) ; **48 px** ailleurs.
- 20 captures écrites dans `../captures/`.

> À la 1re passe : débordement de **17 px** sur `vente` à 360 px
> (`span.bandeau__role` — badge « facturier papier »). Corrigé (retour à la ligne
> du bandeau sous 720 px). 2e passe : 20/20, `débordement=false` partout.

## `verifier-flux.mjs` — 14 / 14

**Connexion**
- ✅ erreur affichée près du champ si la saisie est vide
- ✅ message « identifiant ou mot de passe incorrect » + mention du blocage
- ✅ couple valide `awa` / `franck` → écran de vente

**Vente**
- ✅ « robi » + `Entrée` ajoute 1 ligne au panier (2 → 3) — **2 actions**
- ✅ article déjà présent → quantité +1, pas de doublon (8 → 9)
- ✅ le focus revient sur la recherche après ajout (enchaînement rapide)
- ✅ `F4` change le mode de paiement (especes → orange_money)
- ✅ 1er `F9` demande **une** confirmation
- ✅ 2e `F9` valide (message de succès)
- ✅ **aucune** fenêtre superposée (0 `dialog` / `modal`)

**Inventaire à l'aveugle**
- ✅ le tableau de données ne porte que `id` / `nom` / `unité` (aucune quantité attendue)
- ✅ le champ de saisie est vide au départ (rien n'est pré-rempli)
- ✅ saisie + `Entrée` → article suivant (Ciment CIM II 50 kg → Fer à béton 8 mm)
- ✅ progression mise à jour (`2 / 5`)
