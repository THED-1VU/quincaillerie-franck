# Dernier résultat de vérification — maquette (chantiers C9/C10)

Ce fichier est une **trace**. Les preuves restent rejouables depuis
`maquette/verification/` (`npm run affichage`, `npm run flux`, ou directement
`node verifier-cablage.mjs`).

## État actuel (2026-09-13, cycle 20 — chantier C13)

**Ce fichier n'avait plus été mis à jour depuis le cycle 5** (2026-09-12) —
un vrai trou dans la documentation, alors que 6 nouvelles suites ont été
écrites depuis (cycles 6 à 18) et sont rejouées à chaque cycle touchant
l'écran ou la route qu'elles couvrent. Section corrigée ici, pas pour
ajouter du nouveau code mais pour que ce fichier reflète enfin l'état réel
du projet — voir aussi `db/outils/verifier_tout.sh` (nouveau, cycle 20),
qui enchaîne les 7 suites ci-dessous en une seule commande.

| Suite (`npm run …`) | Depuis | Dernier résultat connu |
|---|---|---|
| `cablage` | cycle 5, étendue à chaque écran câblé depuis | **77/77** (cycle 16) |
| `vente` | cycle 6 | **12/12** (cycle 19 — reçu PDF ajouté) |
| `inventaire` | cycle 7 | **17/17** (cycle 7) |
| `stock` | cycle 11 | **26/26** (cycle 13) |
| `rapports` | cycle 12 | **29/29** (cycle 14) |
| `echappement` | cycle 7 (contrôle de boucle) | **11/11** (cycle 7) |
| `rh` | cycle 18 | **21/21** (cycle 18) |
| `affichage`, `flux` | cycle 1 | inchangées depuis (voir plus bas) — nécessitent un **second serveur statique séparé** (`py -m http.server 8080`, jamais automatisé), donc **non incluses** dans `verifier_tout.sh` |

Rejoué en bloc le 2026-09-13 (`bash db/outils/verifier_tout.sh`, sans le
couple `affichage`/`flux`) : **193 contrôles Playwright, 0 échec**, en plus
de la suite SQL (44/44 + 52/52 + 6/6 + réversibilité) et de la suite
pytest (**140/140**) — voir `db/tests/DERNIER_RESULTAT.md` et
`server/tests/DERNIER_RESULTAT.md` pour le détail de ces deux couches.

**Piège trouvé en écrivant `verifier_tout.sh`** : enchaîner plusieurs
suites contre le même serveur en quelques minutes dépasse la limite de
connexion de `config.ini` (10/minute, anti-force-brute) — les suites
suivantes échouaient silencieusement (session jamais créée). Le script
utilise une copie temporaire de `config.ini` avec cette limite relevée,
jamais le vrai fichier. Un second piège, plus sournois : la suite SQL
(étape 7, réversibilité) supprime puis recrée les rôles applicatifs
**globaux au serveur** — `qf_app` retrouve un mot de passe vide, différent
de celui de `config.ini`, et pytest ET Playwright échouent en cascade
juste après pour une raison invisible dans leurs propres messages
d'erreur. Corrigé dans le script (mot de passe reposé après
reconstruction de la base).

---

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
