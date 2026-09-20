# Vision produit — Akuma

## Ce que ce document fixe noir sur blanc

**Akuma est une gamme logicielle destinée à toute quincaillerie, où qu'elle se
trouve.** Les Ets Quincaillerie Franck (Batouri, Cameroun) sont le **premier
client et le terrain de validation**, pas la cible unique.

Conséquence directe pour toute décision de conception à venir : le nom de la
boutique, son logo, ses sites, ses utilisateurs et ses règles fiscales sont
des **données de configuration**, jamais des **constantes du code**. Un
deuxième client, dans un autre pays, avec une autre fiscalité, une autre
devise et un autre nombre de sites, doit pouvoir être servi par le même code
sans le modifier — seulement en changeant sa configuration.

Ce document ne redéfinit rien du cahier des charges des Ets Quincaillerie
Franck (`CAHIER DES CHARGES.docx`, `ADDENDUM_CAHIER_DES_CHARGES.md`), qui
reste le contrat du premier client et qui n'est pas affecté par ce qui suit.
Il recense ce qui, dans le code existant, suppose implicitement qu'il n'y
aura jamais qu'un seul client, à Batouri, et ne survivrait pas tel quel à
l'arrivée d'un deuxième.

**Aucune correction n'est faite dans ce document ni par lui.** C'est un état
des lieux ; chaque ligne peut devenir un chantier de généricité à part
entière, choisi et validé comme n'importe quel autre chantier du
`.agents/skills/finalisation-loop/SKILL.md`, séparément du référentiel
`C0`–`C14` (qui, lui, reste organisé autour du premier client).

---

## Décisions d'éditeur, valables pour toute la gamme Akuma

Les décisions qui suivent ont été prises par le propriétaire le 2026-09-19,
explicitement **pour la gamme Akuma**, pas seulement pour le premier client.
Les deux premières remplacent et complètent le protocole encore imprécis de
`UX_BASELINE.md` — sans le modifier ici : la mise à jour de ce fichier de
travail, propre au premier client, reste à faire au moment d'organiser la
prochaine campagne humaine réelle. Les décisions supplémentaires, ajoutées le
même jour dans une seconde série de réponses, sont marquées séparément
ci-dessous.

### UX-0 — convention de mesure humaine (prise en main / usage courant)

**Décidé.** Une campagne de recette ergonomique mesure **deux critères
distincts**, jamais un seul :

- **Prise en main** — le **1ᵉʳ essai** d'un testeur qui **n'a jamais vu
  l'écran** avant.
- **Usage courant** — le **3ᵉ essai du même testeur**, une fois l'écran
  découvert.

Les deux temps sont **relevés et rapportés séparément** — jamais fondus en
une seule mesure, jamais l'un présenté comme représentatif de l'autre.

**Composition de la campagne.** Trois testeurs **différents** sont requis,
dont **au moins un** n'ayant jamais participé au projet. Un seul testeur qui
recommence l'essai trois fois de suite ne constitue **pas** une campagne
valide : il ne mesurerait qu'un seul chemin d'apprentissage, pas une
diversité d'utilisateurs réels.

### Point k — cibles d'acceptation ergonomique

**Décidé.** Chaque cible ci-dessous se lit selon les deux temps d'UX-0
ci-dessus — une valeur pour l'usage courant, une pour la prise en main —
sauf les critères qualitatifs, qui ne dépendent pas du nombre d'essais.

| Parcours | Usage courant | Prise en main |
|---|:-:|:-:|
| Connexion | < 30 s | < 60 s |
| Vente de 3 articles, prix négociés | < 60 s | < 3 min |
| Ajout d'un article au panier | ≤ 2 actions | ≤ 4 min *(cible haute, tolère l'exploration)* |
| Comptage de 10 articles | < 2 min | < 90 s *(voir note)* |
| Saisie d'une recette au téléphone | < 45 s | *(non chiffré séparément)* |

> Note de cohérence, consignée sans rien modifier ni interpréter : deux
> valeurs méritent une re-confirmation avant la prochaine campagne, la prise
> en main étant censée rester plus lente que l'usage courant, jamais l'inverse.
> « Ajout d'un article » compare une unité (2 actions) à une durée (4 min) —
> pas la même dimension. « Comptage de 10 articles » donne une prise en main
> (90 s) plus rapide que l'usage courant (2 min) — à l'envers du principe
> général. Valeurs reçues et reportées telles quelles ; à trancher
> explicitement avant usage en recette.

**Critères qualitatifs** (s'appliquent aux deux temps, sans distinction) :
- Aucun débordement horizontal à 360, 390, 768, 1366 et 1920 px, **sur un
  vrai téléphone** (pas seulement un émulateur).
- Aucun message technique visible par l'utilisateur.
- Confirmation exigée avant toute opération irréversible.
- Retour en arrière compréhensible sans aide extérieure.

**Règle de blocage.** Un dépassement en **usage courant bloque la
livraison** du parcours concerné. Un dépassement en **prise en main** est un
**indicateur d'amélioration**, jamais un motif de blocage.

### Modèle article/stock multi-site — une fiche, un stock par site

**Décidé.** Dans toute la gamme Akuma, un article physique porte **une seule
fiche produit** au niveau de la boutique (nom, catégorie, unité, prix) —
**jamais** une fiche par site. C'est le **stock** qui est réparti par site
(ou tout autre emplacement de stockage). Un transfert déplace de la quantité
d'un site vers un autre **sans dupliquer la fiche** ; si le site de
destination n'a pas encore de ligne de stock pour cet article, le transfert
**la crée automatiquement**.

Cette décision **corrige un défaut de conception**, pas seulement un
paramètre à externaliser : le modèle actuellement codé (`articles.site_id`
obligatoire, une ligne = un article **et** un site, transfert qui refuse de
créer la ligne de destination) empêcherait **toute** quincaillerie
multi-site de la gamme de gérer un même article sur plusieurs points de
vente sans le dupliquer artificiellement. L'évaluation technique précise de
ce changement (impact sur le schéma, le cloisonnement par site, les écrans
de stock, les comptages et les tableaux de bord) est consignée dans
`ADDENDUM_CAHIER_DES_CHARGES.md`, point a — propre à l'implémentation
actuelle du premier client, mais le **principe** ci-dessus vaut pour la
gamme entière et doit guider toute nouvelle installation dès sa conception,
pas seulement la migration du premier client.

Ce principe **remplace** l'hypothèse encore ouverte de l'audit ci-dessous
(section « Modèle à deux sites nommés ») sur le fond du modèle de données :
le nombre de sites reste variable d'un client à l'autre (déjà noté), mais on
sait désormais aussi qu'un même article ne doit **jamais** être dupliqué
entre sites. Les points restants de cet audit (noms de sites codés en dur
côté écran, contrainte de préfixe de facturier liée à un `site_id` litéral)
restent d'actualité et non résolus par cette décision.

### Crédit client — fonction togglable par boutique

**Décidé.** Le crédit client est une fonction de la gamme Akuma, **activable
ou désactivable par boutique** — une installation peut fonctionner sans
crédit client du tout, une autre peut l'activer avec ses propres réglages.
Le **plafond par défaut** appliqué à un nouveau client est une valeur de
**configuration par boutique**, jamais une constante (100 000 FCFA n'est une
valeur que pour Ets Quincaillerie Franck — voir
`ADDENDUM_CAHIER_DES_CHARGES.md`, point b). Aucune relance automatique,
aucun intérêt en version 1 — un principe de simplicité qui vaut, sauf avis
contraire, pour toute la gamme.

### Fiscalité — confirmation de la règle déjà posée par l'audit

**Confirmé.** Le taux de TVA reste une valeur de configuration
(`parametres.taux_tva`), jamais codée en dur, et doit pouvoir être **nul**
pour une boutique de la gamme Akuma dont le régime fiscal ne le justifie pas
(seuil de chiffre d'affaires différent, autre pays). Ne change rien à
l'audit déjà consigné plus bas (section « Régime fiscal et calcul de la
TVA ») : cette confirmation porte sur la valeur du taux, pas sur le
**modèle** de calcul (TVA unique extraite d'un TTC global), qui reste, lui,
un point de généricité non résolu.

### Outil d'import — chargements partiels et successifs

**Décidé.** L'outil d'import de données initiales (stock, clients à crédit,
ou toute autre reprise de données à l'ouverture d'une nouvelle boutique de
la gamme) doit accepter **plusieurs chargements successifs et partiels**,
**sans jamais dupliquer** ce qui a déjà été chargé, et **indiquer clairement
ce qui reste à traiter**. Un import unique et global, pensé comme un
événement ponctuel, ne convient à aucune ouverture réaliste : un inventaire
physique complet prend plusieurs jours, zone par zone. Les éléments trouvés
sur place mais absents du support de reprise (cahier, fichier) sont créés
**après validation humaine**, jamais automatiquement. Le détail propre au
premier client (volumétrie, durée du comptage, découpage par zones) est
consigné dans `ADDENDUM_CAHIER_DES_CHARGES.md`, point j.

---

## Méthode de cet audit

Recherche systématique dans le code (`server/`, `maquette/`, `db/`) des
valeurs qui supposent Batouri, le Cameroun, ou les Ets Quincaillerie Franck —
par exécution de recherches textuelles ciblées, puis lecture du contexte de
chaque occurrence trouvée. Cet audit n'est pas nécessairement exhaustif : il
couvre ce qu'une recherche par mots-clés peut trouver, pas une relecture
ligne à ligne de tout le dépôt.

---

## Déjà généricisé (à prendre en exemple)

Avant de lister ce qui reste codé en dur, deux points montrent que le
mécanisme de configuration existe déjà et fonctionne :

- **Identité de la boutique** : `boutique_nom`, `boutique_ville`,
  `boutique_telephone`, `boutique_numero_contribuable` sont des lignes de la
  table `parametres` (`db/migrations/006_parametres_applicatifs.sql`), lues
  au moment de générer le reçu de vente (`server/app/routes/ventes.py`).
  Rien n'est écrit en dur.
- **Logo de la boutique** : téléversable par le responsable depuis le cycle
  28 (`POST/DELETE/GET /configuration/logo`), stocké hors base, absent par
  défaut sans rien casser à l'affichage.

Ces deux exemples sont la référence à suivre : une donnée qui change d'un
client à l'autre vit dans `parametres` ou un stockage équivalent, jamais
dans une constante Python, un `<option>` HTML ou une contrainte SQL.

---

## Recensé comme codé en dur

### 1. Fuseau horaire — `Africa/Douala`

- **Où c'est codé** :
  - `server/app/database.py` (constante `FUSEAU_HORAIRE_BOUTIQUE =
    "Africa/Douala"`, appliquée à chaque connexion via `SET TIME ZONE`) ;
  - `db/migrations/013_fuseau_horaire_boutique.sql` (`ALTER DATABASE ... SET
    timezone TO 'Africa/Douala'`, avec un contrôle qui **lève une erreur**
    si la session n'est pas exactement sur ce fuseau).
  - Doublé intentionnellement aux deux niveaux (base + application) depuis
    l'incident du cycle 7 (dérive silencieuse détectée en `Europe/Paris`) —
    voir le commentaire en tête de `database.py`.
- **Ce qu'il faudrait pour le rendre paramétrable** : une clé
  `fuseau_horaire` dans `parametres`, lue au démarrage du serveur et
  appliquée par `SET TIME ZONE` (déjà le mécanisme utilisé côté
  application) ; réécrire la migration 013 pour ne plus figer la valeur au
  niveau de la base, ou accepter qu'elle reste un réglage d'installation
  (un fichier de config par client, pas une valeur partagée). Revérifier
  ensuite toute la logique qui dépend du changement de jour (unicité d'un
  comptage par jour, écrans « du jour » de C5/C7) avec un autre fuseau.
- **Difficulté estimée** : **moyenne**. La valeur est isolée dans un seul
  nom de constante et une seule migration, mais le changement touche un
  réglage de base de données (pas qu'une variable applicative) et exige de
  revérifier tout ce qui dépend de la notion de « jour ».

### 2. Devise — `FCFA`

- **Où c'est codé** : littéralement, dans `server/app/routes/ventes.py`
  (fonction `_fcfa()`, qui **ajoute** la chaîne `" FCFA"` à tout montant
  formaté) et dans les libellés HTML (`maquette/vente.html`,
  `maquette/cloture-caisse.html`, `maquette/rh.html`,
  `maquette/tableau-bord.html`).
- **Point notable** : la table `parametres` a **déjà** une clé `devise`
  (valeur `'FCFA'`, `db/migrations/006_parametres_applicatifs.sql`) — un
  test SQL vérifie même explicitement qu'elle peut être changée en `'EUR'`
  (`db/tests/01_protections.sql`). **Le stockage existe, mais aucun code
  applicatif ne le lit** : le formatage ignore complètement ce paramètre.
- **Ce qu'il faudrait** : faire lire `devise` par `_fcfa()` et par
  l'équivalent côté client (les pages HTML devraient recevoir la devise du
  serveur, comme elles reçoivent déjà `boutique_nom`, plutôt que d'écrire
  « FCFA » dans le gabarit) ; trancher une règle de décimales (le FCFA n'a
  pas de centimes, ce qui est aujourd'hui une hypothèse implicite du
  formatage — `round(float(montant))` sans décimale — qui ne conviendrait
  pas à une devise à centimes).
- **Difficulté estimée** : **faible à moyenne**. Le stockage et le
  mécanisme de configuration existent déjà ; il s'agit de câblage plus que
  de conception, sauf la question des décimales qui est une vraie décision.

### 3. Régime fiscal et calcul de la TVA

- **Où c'est codé** : `parametres.regime_fiscal` et `parametres.taux_tva`
  existent déjà comme valeurs configurables (`db/migrations/
  006_parametres_applicatifs.sql`), mais le **modèle** de calcul, lui, est
  fixé dans le code (`server/app/routes/ventes.py`) : un **seul taux** de
  TVA, extrait d'un total **TTC** déjà négocié (prix qui incluent la taxe),
  appliqué à la vente entière — jamais par ligne, jamais plusieurs taux
  simultanés, jamais de prix affichés hors taxe.
- **Ce qu'il faudrait** : une vraie décision métier avant tout code — un
  régime avec plusieurs taux, une taxe ajoutée plutôt qu'extraite (fiscalité
  à l'américaine par exemple), ou une taxation par article plutôt que par
  vente ne rentrent pas dans le modèle actuel. Ce n'est pas un paramètre à
  ajouter, c'est une abstraction à concevoir (« stratégie fiscale »
  interchangeable).
- **Difficulté estimée** : **élevée**. C'est un changement de modèle de
  calcul, pas une valeur à externaliser.

### 4. Modes de paiement — Orange Money / MTN Mobile Money

- **Où c'est codé**, à trois niveaux distincts :
  - **Schéma de base** : `db/migrations/019_cloture_caisse.sql` — la table
    `clotures_caisse` a des colonnes **nommées** `attendu_orange_money`,
    `attendu_mtn_momo`, `compte_orange_money`, `compte_mtn_momo`,
    `ecart_orange_money`, `ecart_mtn_momo` (et leur fonction de calcul
    `calculer_attendu_caisse()`) ;
  - **Validation serveur** : `_MODES_PAIEMENT_ACTIFS = {"especes",
    "orange_money", "mtn_momo", "autre"}` (`server/app/routes/ventes.py`) ;
  - **Écran** : la liste des moyens de paiement proposés à la vente vient de
    `maquette/donnees-simulees.js` (`especes` / `orange_money` /
    `mtn_momo`), pas d'une route qui interrogerait une configuration.
- **Ce qu'il faudrait** : un modèle de « canaux de paiement » configurable
  (nom, éventuellement un type — espèces/mobile/autre — pour les écrans qui
  distinguent les espèces du reste), au lieu de colonnes nommées en dur ;
  `calculer_attendu_caisse()` et l'écran de clôture devraient itérer sur une
  liste de canaux plutôt que sur quatre colonnes fixes.
- **Difficulté estimée** : **élevée**. Ce n'est pas qu'une liste d'options
  à rendre configurable : le schéma de `clotures_caisse` et sa fonction de
  calcul sont construits colonne par colonne autour de ces deux moyens de
  paiement précis.

### 5. Modèle à deux sites nommés

> Voir aussi la décision « Modèle article/stock multi-site » plus haut
> (2026-09-19) : au-delà des noms de sites codés en dur ci-dessous, le
> modèle actuel a un défaut plus profond — un article n'a aujourd'hui une
> fiche que sur UN site, jamais partagée. Les deux problèmes sont liés mais
> distincts ; celui décrit ici (noms/id de sites en dur) reste entier même
> une fois le premier corrigé.

- **Où c'est codé** : la table `sites` elle-même est générique (un nombre
  quelconque de lignes est déjà possible), mais deux sites précis,
  identifiés par leur `id` (1 et 2) et leurs noms (« Magasin de stock »,
  « Comptoir »), sont codés en dur à plusieurs endroits :
  - une **contrainte de base** (`db/migrations/020_facturier_vendeur.sql`) :
    `CHECK (site_id = 1 AND numero_facturier LIKE 'MAG-%') OR (site_id = 2
    AND numero_facturier LIKE 'CPT-%')` — le préfixe du facturier papier est
    littéralement lié à l'identifiant numérique du site ;
  - le **front-end**, en au moins sept endroits : options `<option
    value="1">Magasin de stock</option>` / `<option
    value="2">Comptoir</option>` écrites en dur dans `maquette/vente.html`,
    `maquette/cloture-caisse.html`, `maquette/rh.html`,
    `maquette/stock.html`, `maquette/tableau-bord.html` (deux fois), et la
    constante `LIBELLE_SITE = { 1: "Magasin de stock", 2: "Comptoir" }`
    dans `maquette/api.js`. **Aucune route `GET /sites` n'existe** pour
    peupler ces listes dynamiquement.
- **Ce qu'il faudrait** : une route `GET /sites` (nom + éventuellement un
  préfixe de facturier propre à chaque site, en colonne plutôt qu'en
  contrainte `CHECK`), et faire peupler chaque écran depuis cette route au
  lieu d'options écrites en dur.
- **Difficulté estimée** : **moyenne à élevée**. Beaucoup de points de code
  à toucher, mais de façon mécanique et répétitive — sauf la contrainte de
  préfixe de facturier, qui redevient une question métier dès qu'il y a
  plus de deux sites ou un client sans carnet papier du tout (point 6).

### 6. Numéro de facturier (carnet papier)

- **Où c'est codé** : `ventes.numero_facturier`, avec la contrainte de
  préfixe ci-dessus, obligatoire sur toute nouvelle vente
  (`db/migrations/020_facturier_vendeur.sql`). Le concept lui-même — un
  carnet **papier** que le comptable transcrit après coup — est une
  pratique commerciale propre au premier client, pas universelle : un
  client déjà informatisé sans carnet papier n'a rien à transcrire.
- **Ce qu'il faudrait** : rendre l'exigence elle-même paramétrable par
  installation (carnet papier obligatoire, ou non) plutôt que supposée
  partout.
- **Difficulté estimée** : **moyenne**. Suppose une décision métier
  (comment une installation sans carnet papier gère alors la traçabilité
  que le facturier apportait) avant tout code.

### 7. Langue — français uniquement

- **Où c'est codé** : partout — aucune couche d'internationalisation
  n'existe. Tous les libellés HTML, tous les messages d'erreur renvoyés par
  l'API (`server/app/routes/*.py`), tous les textes des reçus PDF et
  exports sont des chaînes françaises écrites en dur, mélangées au code.
- **Ce qu'il faudrait** : une couche de traduction (clés de message plutôt
  que texte en dur) sur l'ensemble du code applicatif et des écrans — un
  travail transverse à tout le dépôt, pas un point isolé.
- **Difficulté estimée** : **élevée**. Pas un paramètre : une réécriture
  progressive de la quasi-totalité des chaînes visibles par l'utilisateur.

### 8. Format de numéro de téléphone

- **Où c'est codé** : le champ est stocké en texte libre
  (`telephone: Optional[str] = Field(default=None, max_length=30)`,
  `server/app/schemas.py`) — **aucun format camerounais (+237) n'est
  imposé**. C'est en réalité déjà tolérant.
- **À noter pour mémoire** : l'absence de validation signifie aussi
  l'absence de tout contrôle de cohérence, quel que soit le pays — pas un
  vrai défaut de généricité, mais un point à garder en tête si une
  validation de format devait un jour être ajoutée (elle devrait rester
  paramétrable par pays dès sa conception, pas verrouillée sur le Cameroun).
- **Difficulté estimée** : **faible** (rien à changer aujourd'hui, juste à
  ne pas régresser plus tard).

### 9. Format de date sur le reçu imprimé

- **Où c'est codé** : `f"Date : {vente['date_encaissement']:%d/%m/%Y
  %H:%M}"` (`server/app/routes/ventes.py`) — format jour/mois/année écrit en
  dur sur le reçu PDF. Les exports de `server/app/routes/rapports.py`
  n'ont pas été audités en détail (formats de date éventuels dans les
  fichiers Excel/PDF de rapports à vérifier séparément).
- **Ce qu'il faudrait** : au minimum documenter que ce format est un choix
  (largement partagé, mais pas universel — il ne conviendrait pas tel quel
  à un affichage américain) ; le rendre configurable seulement si un client
  réel en a besoin.
- **Difficulté estimée** : **faible**, pour le seul point trouvé ici.

### 10. Noms internes `qf_*` (rôles PostgreSQL, préfixes)

- **Où c'est codé** : les rôles de base de données (`qf_app`,
  `qf_responsable`, `qf_agent_stock`, `qf_agent_comptabilite`) portent un
  préfixe `qf` (Quincaillerie Franck), visible uniquement en base et dans
  le code serveur — jamais exposé à un utilisateur final.
- **Ce qu'il faudrait** : rien d'urgent — un renommage serait cosmétique,
  sans bénéfice fonctionnel, et coûterait une migration sur un objet
  sensible (les rôles portent tous les privilèges de cloisonnement C1/C3).
- **Difficulté estimée** : **faible priorité** — à ne traiter, si jamais,
  qu'à l'occasion d'un autre chantier touchant déjà ces migrations, jamais
  pour lui-même.

---

## Ce que cet audit ne couvre pas

- Les exports Excel/PDF de `server/app/routes/rapports.py` n'ont pas été
  relus en détail pour d'éventuels formats de date, de nombre ou de devise
  supplémentaires.
- Aucune recherche n'a porté sur des hypothèses non textuelles (ex. :
  arrondis, unités de mesure implicites, jours fériés/ouvrés) — un audit
  complémentaire pourrait les révéler.
- Ce document est un état des lieux à la date ci-dessous ; il doit être
  relu (pas supposé à jour) avant de servir de base à un chantier de
  généricité, si du code a changé entre-temps.

---

*Rédigé le 2026-09-19, sur la base du code à l'état du cycle 28 (commit
`2b60974`). Aucune correction appliquée par ce document — audit seul.*
