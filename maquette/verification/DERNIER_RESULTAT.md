# Dernier résultat de vérification — maquette (cycle 1, chantier C9)

Exécuté le **2026-09-11** sur `http://127.0.0.1:8080/` (serveur `py -m http.server 8080`),
Google Chrome via Playwright (`channel: "chrome"`).

Ce fichier est une **trace**. La preuve reste rejouable : `npm run affichage` et
`npm run flux` depuis `maquette/verification/`.

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
