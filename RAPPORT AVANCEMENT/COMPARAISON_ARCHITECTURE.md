# Comparaison d'architecture cible — Quincaillerie Franck

Décision **non tranchée**. Ce document compare les deux options au regard des trois
priorités du propriétaire, et traite explicitement l'impression du ticket de caisse.
Il se termine par une recommandation, qui reste une proposition soumise au propriétaire.

Priorités, dans l'ordre :

1. **Rendu / ergonomie / responsivité / expérience utilisateur.**
2. **Usage téléphone** : les responsables doivent **suivre** *et* **saisir** depuis un
   mobile, où qu'ils soient. Ce n'est pas une option secondaire.
3. **Fiabilité métier** : droits par rôle, intégrité du stock, traçabilité anti-vol.

---

## Les deux options

### Option A — Application de bureau (PyQt6) + interface web séparée pour le mobile

On conserve (et on refond) l'application de bureau Windows existante pour la boutique,
et on **ajoute** une API web (FastAPI) + un front web responsive **distinct** pour le
téléphone. Deux bases de code d'interface : Qt et web.

```
Postes boutique  ─(PyQt6)──────────────┐
                                       ├──► PostgreSQL (poste serveur, LAN)
Téléphone ─(navigateur)─► API FastAPI ─┘
```

### Option B — Application web unique, servie en local

Une seule application web (serveur FastAPI/Django + PostgreSQL sur le poste serveur du
LAN). **Le même** logiciel est utilisé par le PC de caisse (navigateur en plein écran /
mode kiosque, ou enveloppe type Tauri/Electron) **et** par le téléphone (même URL, mise
en page responsive). Aucune dépendance Internet pour l'usage quotidien : le serveur est
sur le réseau local.

```
PC de caisse ─(navigateur kiosque)─┐
Postes boutique ─(navigateur)──────┼──► Serveur web (LAN) ──► PostgreSQL (LAN)
Téléphone ─(navigateur, via VPN)───┘
```

---

## Évaluation par priorité

### Priorité 1 — Rendu, ergonomie, responsivité

| | Option A (bureau + web) | Option B (web unique local) |
|---|---|---|
| Ergonomie du poste de caisse | **Très forte** : Qt natif, focus clavier maîtrisé, raccourcis, zéro latence, aucune surprise de rendu navigateur. | **Bonne si travaillée** : raccourcis clavier, mode kiosque plein écran, pas de « web mou ». Latence LAN négligeable. |
| Responsivité multi-écrans (360 px → 1920 px) | **Faible côté Qt** : Qt s'adapte mal aux très petites largeurs ; il faut de toute façon **refaire** une UI web pour le mobile. | **Native** : une seule feuille de style responsive couvre PC et mobile. |
| Cohérence visuelle PC / mobile | **À maintenir deux fois** : deux technologies, deux rendus, risque de dérive. | **Une seule UI** : cohérence par construction. |
| Coût de mise au point ergonomique | **Double** (Qt + web). | **Simple** (une UI), mais exigence de rigueur sur le parcours de caisse. |
| Risque | Dette d'UI permanente. | Parcours de caisse « au niveau natif » à prouver (mesures du point k de l'addendum). |

**Avantage : Option B**, sauf si le test montre que le parcours de caisse web ne tient pas
les cibles chiffrées (vente < 60 s, navigation clavier intégrale) sur le matériel réel.

### Priorité 2 — Usage téléphone (suivi ET saisie)

| | Option A | Option B |
|---|---|---|
| Suivi mobile | Nécessite de **construire** l'API + un front web dédié. | **Inclus** : le téléphone ouvre la même application. |
| Saisie mobile (recettes, dépenses, inventaire, voire ventes) | Nouvelle surface à développer et à sécuriser **en plus** de l'app Qt. | **Inclus** : mêmes écrans, mêmes règles, même code serveur. |
| Règles métier | **Dédoublées** : implémentées côté Qt *et* côté API — risque de divergence (une règle corrigée d'un côté, pas de l'autre). | **Uniques** : toutes au serveur, appelées par tous les clients. |
| Accès hors du LAN | VPN/tunnel vers l'API (comme le préconise le dossier de recette). | VPN/tunnel WireGuard vers le serveur web. Identique. |
| Effort pour atteindre la priorité 2 | Élevé (c'est un second produit). | Faible (c'est le même produit). |

**Avantage : Option B, nettement.** La priorité 2 étant explicitement « pas secondaire »,
l'option qui la satisfait sans créer un second produit est la plus alignée.

### Priorité 3 — Fiabilité métier (droits, stock, anti-vol)

| | Option A | Option B |
|---|---|---|
| Où vivent les règles (décrément atomique, gating des prix, audit) | Côté **client Qt** (comme aujourd'hui : `user = postgres` en direct) → **contournables** ; l'API doit les **réimplémenter**. Pour bien faire, il faudrait que Qt passe *aussi* par l'API — auquel cas autant tout centraliser (= Option B). | Côté **serveur uniquement** : un seul point d'application, testable une fois. |
| Exposition de PostgreSQL | Le poste Qt s'y connecte directement (surface d'attaque LAN + risque de requête directe). | Seul le serveur web parle à PostgreSQL ; les clients ne voient jamais la base. |
| Cloisonnement par rôle « aussi dans les requêtes » (exigence CDC §4.2) | Difficile : chaque client fait ses requêtes. RLS possible mais complexe avec un client lourd. | Naturel : autorisation vérifiée par endpoint, RLS PostgreSQL activable, rôle applicatif à privilèges minimaux. |
| Traçabilité (journal d'audit, connexions, annulations) | À écrire deux fois (Qt + API). | Écrite une fois, au serveur. |
| Intégrité concurrente (survente) | Verrou géré par chaque client → fragile. | Verrou géré au serveur, transaction unique. |

**Avantage : Option B**, qui correspond à la recommandation du dossier de recette
(« masquer l'interface ne suffit pas », validation serveur de tous les prix/quantités).

---

## Le point dur : impression du ticket de caisse

Le CDC exige une **impression directe** d'un reçu format ticket **avec code-barres**,
**sans étape intermédiaire** (au plus **1 confirmation**, cf. point k de l'addendum).

### Option A — natif Qt

- Qt sur le poste de caisse pilote l'imprimante ticket directement : génération du PDF
  (reportlab) puis envoi au spouleur Windows, ou flux **ESC/POS** vers une imprimante
  thermique USB/série. Impression **silencieuse**, immédiate, fiable.
- **C'est l'argument le plus solide en faveur de l'Option A.** Rien à inventer.

### Option B — web

Un navigateur **n'imprime pas silencieusement** par défaut (`window.print()` ouvre un
dialogue → viole « sans étape intermédiaire »). Solutions, du moins au plus intrusif :

1. **Chrome/Edge en `--kiosk-printing`** sur le **poste de caisse uniquement** :
   l'impression part **sans dialogue** vers l'imprimante par défaut. Imprimante ticket
   définie par défaut, marges à zéro, format ticket (80 mm). **Zéro développement.**
   Convient à la majorité des imprimantes thermiques qui exposent un pilote Windows.
2. **Petit agent d'impression local** (service Windows, ~150–250 lignes) : le serveur
   envoie le ticket (HTML rendu, PDF, ou commandes ESC/POS) à `http://localhost:<port>`
   sur le poste de caisse ; l'agent le pousse à l'imprimante en **ESC/POS**. Découplé,
   très fiable, gère « imprimante hors ligne / plus de papier », permet la réimpression.
   C'est la solution de repli si l'imprimante ne se laisse pas piloter proprement via
   le pilote Windows, ou si l'on veut un rendu ticket au pixel près.
3. **QZ Tray / WebUSB / WebSerial** : possible mais dépendances lourdes, permissions
   navigateur, fragilité entre versions — **non recommandé**.

**Conclusion impression :** l'Option B **peut** satisfaire l'exigence, via
`--kiosk-printing` (effort nul) avec repli sur un agent d'impression local ESC/POS
(effort faible, ~1 jour). Ce n'est **pas** un facteur bloquant, mais c'est le point à
**prototyper en premier** avec l'imprimante réelle de la boutique avant de figer le choix.
L'Option A élimine ce risque d'entrée de jeu.

---

## Autres facteurs

| Facteur | Option A | Option B |
|---|---|---|
| Réutilisation de l'existant | **Forte** : repart du `.exe` actuel (une fois le source reconstruit). | Faible : nouvelle application (mais le **schéma** et les **règles** sont réutilisés). |
| Fonctionnement sans Internet | Oui (LAN). | Oui (serveur sur le LAN). Le téléphone hors LAN passe par VPN — déjà prévu au dossier de recette. |
| Panne du poste serveur | Tous les postes tombent (déjà le cas aujourd'hui avec Postgres central). | Idem : serveur web + DB sur le même poste → onduleur + poste de secours (addendum i) d'autant plus critiques. |
| Déploiement / mise à jour | Redéployer un `.exe` sur chaque poste (PyInstaller). | Mettre à jour **un seul** serveur ; les clients rechargent la page. **Plus simple.** |
| Compétences pour la maintenance | Python + Qt (plus rare). | Python web + HTML/CSS/JS (plus courant, plus facile à reprendre). |
| Licence | PyQt6 = GPL ou licence commerciale à surveiller. | Stack web classique, pas de contrainte équivalente. |
| Postes clients | Windows uniquement. | Tout appareil avec navigateur récent (utile si un poste change). |

---

## Recommandation (proposition, non décision)

**Option B — application web unique servie en local — est recommandée**, pour ces raisons :

1. Elle sert le mieux la **priorité 2** (suivi *et* saisie mobile), explicitement non
   secondaire, **sans créer un second produit** ni dédoubler les règles métier.
2. Elle sert le mieux la **priorité 3** : règles et audit centralisés au serveur, base
   jamais exposée aux clients, cloisonnement applicable « aussi dans les requêtes »,
   verrou de concurrence unique. C'est aussi ce que recommande le dossier de recette.
3. Sur la **priorité 1**, elle donne une UI unique et réellement responsive de 360 px à
   1920 px ; le seul point de vigilance est le parcours de caisse, qui doit être mesuré
   (cibles du point k) sur le matériel réel.
4. Le **déploiement** (un serveur à mettre à jour) et la **maintenabilité** (stack
   courante) sont meilleurs.

**Conditions pour retenir l'Option B :**

- **Prototyper l'impression du ticket** avec l'imprimante réelle de la boutique
  (`--kiosk-printing` d'abord, agent ESC/POS local en repli) **avant** de figer le choix.
- **Mesurer le parcours de caisse** en web (vente < 60 s, navigation 100 % clavier) sur
  un poste équivalent à celui de la boutique.
- Traiter l'**onduleur + poste de secours** (addendum i) comme prérequis, le serveur web
  et la base étant sur la même machine.

**Retenir l'Option A** seulement si l'un de ces tests échoue de façon irrémédiable
(impression thermique impossible à rendre silencieuse et fidèle ; ergonomie de caisse
web sous les cibles malgré les efforts), ou si le propriétaire veut capitaliser au
maximum sur l'exécutable existant à très court terme.

**Option écartée d'office : rien.** Les deux restent recevables tant que les tests
ci-dessus n'ont pas été faits — d'où le maintien de cette décision parmi les trois à
trancher en priorité.
