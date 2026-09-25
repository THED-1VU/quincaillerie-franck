# Addendum au cahier des charges — Ets Quincaillerie Franck

Ce document complète le `CAHIER DES CHARGES.docx` sur les points que la spécification
d'origine laisse ouverts ou contradictoires. Pour chaque point :

1. **Règle proposée** — ce que l'on retient par défaut, à valider.
2. **Cas limites** — situations à couvrir explicitement.
3. **Question(s) au propriétaire** — décision métier qui ne peut pas être devinée.

> Convention : aucune règle métier n'est tranchée par l'équipe technique. Tant qu'une
> question ci-dessous est sans réponse, le comportement correspondant reste **à l'arrêt**
> (fonction désactivée ou valeur neutre), jamais deviné.

Rappel des priorités du propriétaire, dans l'ordre : **1. rendu / ergonomie / responsivité —
2. usage téléphone (suivi ET saisie) — 3. fiabilité métier (droits, stock, anti-vol).**

## Gestion des comptes utilisateurs (CDC §3.8)

> **Décidé (2026-09-20).** La création des comptes se fait **par le
> responsable, depuis l'intérieur de l'application**, conformément au CDC
> (GS §3, DR Resp. B1-B2) : créer un agent stock ou un agent comptabilité
> avec **site obligatoire**, identifiant unique, désactiver / réactiver
> un compte. **Pas d'auto-inscription publique** — elle n'apparaît nulle
> part dans le CDC et présenterait un risque de sécurité inutile pour
> cette application métier.
>
> Deux chantiers distincts en découlent, à ne pas mélanger :
> - **C0-C** (périmètre C0) : outil de création du **premier** compte
>   responsable — résout l'œuf et la poule, car aucun compte ne peut être
>   créé aujourd'hui dans l'application web reconstruite (diagnostic du
>   2026-09-20 : aucune route, aucun écran ; seul l'ancien
>   `CreerCompteResponsable.exe` de l'application d'origine existait,
>   non reconstruit). **Non démarré.**
> - **C2** (Authentification et comptes) : écran + route de gestion des
>   comptes depuis l'application, pour l'usage courant du responsable une
>   fois connecté (créer, désactiver, réactiver — CDC §3.8). **Non
>   démarré** ; diagnostic à faire dans un cycle séparé. Le socle SQL
>   existe déjà : `qf_responsable` a reçu `GRANT INSERT`/`UPDATE` sur
>   `utilisateurs` (migration 008) — il ne manque que la route et
>   l'écran.

---

## a) Transfert de stock entre le magasin et le comptoir

> **Décidé (cycle 9, 2026-09-13), questions 2 et 3.** Opération **unique et
> atomique** produisant une sortie du site d'origine et une entrée au site
> de destination, même horodatage, même auteur, motif obligatoire —
> **jamais** d'état intermédiaire « en transit ». Ne recalcule **pas** le
> seuil d'alerte (ce n'est pas une réception fournisseur). Déclenché par le
> responsable, ou par l'agent stock **du site d'origine seulement**.
> Appliqué dans `db/migrations/014_articles_stock_transferts_retours.sql`
> (`transferer_stock`). Questions 1 et 5 (réapprovisionnement exclusivement
> interne ? fréquence/volume) restent sans réponse, sans effet sur ce qui
> est construit.
>
> **Décidé (2026-09-19), question 4 — DÉCISION STRUCTURELLE, rupture avec
> le modèle actuel.** Un article physique porte **une seule fiche** au
> niveau de la quincaillerie (nom, catégorie, unité, prix) ; c'est le
> **stock** qui est réparti par site. Exemple du propriétaire : 100 sacs de
> ciment, 70 au magasin et 30 au comptoir, restent **une seule référence**
> « Ciment X » totalisant 100 — jamais deux fiches. Un transfert déplace de
> la quantité d'un site vers l'autre **sans dupliquer la fiche** ; si le
> site de destination n'a pas encore de stock pour cet article, **le
> transfert crée cet emplacement automatiquement** (ceci **inverse**
> l'implémentation actuelle de `transferer_stock()`, qui refuse ce cas —
> voir l'impact technique ci-dessous). Cette décision **confirme** la
> **règle proposée** à l'origine de ce document (ci-dessous, « un article
> logique... création automatique de l'instance cible ») : c'est le code
> effectivement livré au cycle 9 qui s'en était écarté, pas l'inverse.
>
> **Transferts, précision complémentaire (2026-09-19).** Un transfert est
> décidé par le **responsable**, ou par une **personne qu'il désigne** —
> cohérent avec la règle déjà en vigueur (agent stock du site d'origine) ;
> ne change pas qui peut techniquement déclencher un transfert, précise
> seulement que la désignation est à la discrétion du responsable, pas
> figée à un rôle système. Chaque mouvement enregistre explicitement la
> **quantité partie** du site d'origine et la **quantité arrivée** au site
> de destination — déjà le cas (`transferer_stock()` écrit une ligne
> `sortie` et une ligne `entree` liées) : rien à changer sur ce point
> précis.
>
> **Ce que cette décision règle enfin explicitement, dans
> `VISION_PRODUIT.md`** : le principe « une fiche, un stock par site »
> vaut pour toute la gamme Akuma, pas seulement pour ce client — voir la
> section « Décisions d'éditeur » de ce document.

### Impact technique et plan de migration (évalué le 2026-09-19, aucun code écrit)

**Constat de départ, par lecture du code actuel.** Le modèle aujourd'hui en
vigueur est documenté noir sur blanc dans le schéma lui-même
(`QuincaillerieFranck_Test/creation_base_donnees.sql`, commentaire au-dessus
de `CREATE TABLE articles`) : *« Un article appartient toujours à un seul
site. Le ciment/fer du magasin n'apparaît jamais au catalogue du
comptoir. »* — exactement l'inverse de la décision ci-dessus.
`articles.site_id` est `NOT NULL` ; `quantite_stock` et `seuil_alerte` sont
des colonnes de la fiche elle-même, pas d'un stock séparé.

**C1 — schéma (impact le plus lourd).**
- Nouvelle table de stock par site (ex. `stocks_sites` : `article_id`,
  `site_id`, `quantite_stock`, `seuil_alerte`, clé primaire composite) —
  `articles` perd `site_id`, `quantite_stock`, `seuil_alerte`.
- `mouvements_stock` et `comptages_stock` ne référencent aujourd'hui que
  `article_id` ; le site est déduit **implicitement** via `articles.site_id`
  (utilisé par les policies RLS ET par le déclencheur
  `figer_quantite_attendue()`, migration 003, qui lit
  `articles.quantite_stock` directement). Les deux tables doivent gagner un
  `site_id` **explicite**, et ce déclencheur doit lire la nouvelle table de
  stock par (article_id, site_id).
- La contrainte d'unicité « un comptage par article/moment/jour » doit
  devenir « par article **et site**/moment/jour » : le même article peut
  légitimement être compté le même jour, une fois par site.
- **Migration des données existantes — la partie la plus délicate** :
  aujourd'hui, « Ciment CIM II 50 kg » au Magasin et un éventuel « Ciment
  CIM II 50 kg » au Comptoir sont deux lignes `articles` indépendantes, sans
  aucune clé qui les relie. Les fusionner en une seule fiche + deux lignes
  de stock exige une **règle de rapprochement** (nom strictement identique ?
  confirmation humaine ligne par ligne ?) — un rapprochement automatique sur
  le seul nom risquerait de fusionner à tort deux articles distincts qui
  portent le même libellé par coïncidence. **Question ouverte, à trancher
  avant d'écrire cette migration** : sur quel critère rapprocher deux fiches
  existantes, et qui valide chaque fusion ?
- Deux attributs de la fiche actuelle ne sont pas couverts par la décision
  du propriétaire et restent **à confirmer** plutôt que devinés : le
  **fournisseur** (`fournisseur_id`) et le **prix** (`prix_achat`,
  `prix_vente`) sont-ils communs à la fiche (un seul prix, quel que soit le
  site de vente), ou peuvent-ils différer selon le site de stockage ?
  L'exemple du propriétaire (100 sacs, une seule référence) porte sur la
  **quantité**, pas explicitement sur le prix.

**C3 — cloisonnement par site.**
- La politique RLS `p_articles_site` (migration 008) filtre aujourd'hui
  directement sur `articles.site_id` — cette colonne disparaissant, la
  politique doit être repensée. Conséquence directe du principe « une seule
  fiche » : le **catalogue** (nom, catégorie, unité) devient visible aux
  deux sites pour tout agent de terrain ; c'est la **nouvelle table de
  stock** qui porte désormais le cloisonnement (chaque agent ne voit que la
  ligne de stock de son propre site). C'est une déduction directe de la
  décision ci-dessus, pas une règle inventée — mais elle mérite votre
  confirmation explicite avant le cycle, car elle change ce qu'un agent
  stock du Comptoir peut voir du Magasin (le nom des articles, pas leur
  quantité).
- Les politiques dérivées `p_mouvements_site` et `p_comptages_site`
  (aujourd'hui une sous-requête vers `articles` pour retrouver le site) se
  simplifient : elles filtreront directement sur leur propre colonne
  `site_id`.
- Les `GRANT` par colonne (prix invisibles à l'agent stock, quantité
  invisible au comptable, migration 008) se répartiront différemment : le
  prix reste sur `articles` (visible responsable/comptabilité, pas agent
  stock), la quantité migre vers la nouvelle table de stock (visible
  responsable/agent stock, pas comptabilité) — une séparation par **table**
  remplace une partie de l'actuelle séparation par colonne, plutôt sain.

**C4 — articles et stock.**
- `POST`/`PUT /articles` ne crée plus jamais une paire (nom, site) mais la
  fiche seule ; l'ouverture d'un stock à un site donné (première réception,
  ou transfert entrant) devient une opération distincte.
- `transferer_stock()` change de forme : un seul `article_id` en entrée
  (plus deux), avec `site_origine`/`site_destination` explicites ; la ligne
  de stock de destination est **créée automatiquement** si absente
  (inversion du refus actuel, conformément à la décision).
- `enregistrer_entree_stock`, `enregistrer_casse`,
  `enregistrer_retour_client`/`fournisseur` : toutes agissent aujourd'hui
  sur « la » quantité d'un article — qui n'existe plus au singulier ;
  chacune doit désormais cibler explicitement un (article, site).
- L'écran de vente/stock doit continuer à n'afficher que la quantité **du
  site courant** de l'agent — jamais un total global qui révélerait le
  stock de l'autre site (recoupe directement C3).

**C7 — comptages.**
- Un comptage cible désormais un couple (article, site), pas un article
  seul — la liste « à compter » d'un agent reste filtrée à son site (sans
  changement de principe), mais la clé de désignation change.
- Le même article peut être compté le même jour une fois par site, sans
  conflit — la contrainte d'unicité doit le permettre (voir C1).
- Le principe « la quantité attendue n'atteint jamais le navigateur »
  (garanti par grants de colonne + réponse API tronquée) reste intégralement
  valable, simplement sur une clé composite.

**C8 — tableaux de bord.**
- Les écrans « vue consolidée / par site » (cycle 23) restent valides dans
  leur principe (filtrer par site) ; la source de la quantité et du seuil
  d'alerte change de table.
- Un total « consolidé » de stock devient enfin un vrai total métier (100
  sacs, comme dans l'exemple du propriétaire) — **à vérifier** si un tel
  total de stock consolidé existe déjà quelque part dans les rapports
  actuels (les totaux consolidés connus à ce jour concernent les ventes,
  pas le stock ; à confirmer précisément au diagnostic du cycle qui
  ouvrira ce chantier, pas ici).
- Les alertes de stock faible doivent se déclencher par (article, site), pas
  par fiche : un article en rupture au Comptoir mais bien fourni au Magasin
  doit alerter, sans être masqué par un total global.

**Plan de migration proposé (ordre, sans code)** :
1. Créer la nouvelle table de stock par site (structure ci-dessus).
2. Trancher la règle de rapprochement des fiches existantes homonymes et
   fusionner les données (étape la plus sensible, nécessite une validation
   humaine article par article, pas une fusion automatique aveugle).
3. Ajouter `site_id` à `mouvements_stock` et `comptages_stock`, réamorcé
   depuis le `site_id` de l'article d'origine avant sa suppression.
4. Réécrire les fonctions `SECURITY DEFINER` du stock (entrée, sortie,
   casse, retours, transfert, comptage) pour cibler la nouvelle table.
5. Réécrire les politiques RLS et les `GRANT` par colonne/table concernés.
6. Adapter les écrans et routes qui lisent aujourd'hui
   `articles.quantite_stock`/`seuil_alerte` directement.
7. Rejouer l'intégralité de la suite (SQL + pytest + Playwright) — C1, C3,
   C4, C7 et C8 sont tous touchés **simultanément**, aucune non-régression
   partielle n'est concluante ici.

**Confirmé par le propriétaire (2026-09-19) : ce chantier est un cycle à
part entière, à mener AVANT l'import du stock initial (point j)** —
importer 800 à 1 200 références dans l'ancien modèle (une fiche par site)
puis les fusionner après coup serait un travail double et risqué.

**Contexte.** Le modèle a deux sites (magasin de stock, comptoir de vente) et un article
appartient à un seul site (`articles.site_id`). Le réapprovisionnement du comptoir depuis le
magasin est une opération quotidienne, absente du cahier des charges et du schéma
(`mouvements_stock.type` = `entree` / `sortie` seulement, commentaire : « pas de transfert
entre sites »).

**Règle proposée.**
- Nouvelle opération **« Transfert »** : sortie du site source + entrée du site cible, en une
  seule transaction atomique, tracée comme un couple lié (même référence de transfert).
- Un **article « logique »** (même nom, même unité) peut exister sur les deux sites ; le
  transfert déplace une quantité de l'instance source vers l'instance cible (création
  automatique de l'instance cible si elle n'existe pas, avec le même prix catalogue).
- Réservé au **responsable** et à l'**agent stock** (à confirmer : lequel initie, lequel
  reçoit / confirme).
- Le transfert **ne recalcule pas** le seuil d'alerte (ce n'est pas une réception
  fournisseur) — cohérent avec la règle « seuil recalculé uniquement à une entrée ».
- Un transfert en attente de réception apparaît comme **stock en transit** (ni au source, ni
  disponible au cible) jusqu'à confirmation.

**Cas limites.**
- Transfert supérieur au stock du site source → refus, message près du champ.
- Transfert reçu partiellement (5 sacs envoyés, 4 arrivés) → écart de transfert à consigner
  comme un comptage / une casse (voir point f).
- Article inexistant au site cible → création guidée ou refus.
- Annulation d'un transfert déjà confirmé → contre-transfert tracé, pas de suppression.
- Transfert « à l'aveugle » pendant qu'un comptage d'inventaire est en cours sur l'un des
  deux sites.
- Prix catalogue différent entre les deux instances du même article.

**Questions au propriétaire.**
1. Le comptoir est-il réapprovisionné **uniquement** depuis le magasin, ou reçoit-il aussi
   des livraisons fournisseur en direct ?
2. Qui **déclenche** le transfert (responsable ? agent stock du magasin ?) et qui le
   **confirme à la réception** (agent stock du comptoir ?) ?
3. Veut-on un état intermédiaire « en transit », ou le transfert est-il instantané
   (départ = arrivée, même personne, même moment) ?
4. Le même article physique doit-il porter le **même identifiant catalogue** sur les deux
   sites (prix commun) ou rester deux fiches indépendantes ?
5. Fréquence et volume typiques d'un transfert (nombre de lignes, par jour) ?

---

## b) Vente à crédit — créance client, solde, règlement

> **Statu quo tenu du cycle 6 (2026-09-12) au 2026-09-19.** Pendant cette
> période, `mode_paiement = 'credit_client'` est resté **désactivé côté
> serveur** (`server/app/routes/ventes.py` le refuse avec un message
> explicite) — aucune table Client, aucune créance créée. Ce statu quo est
> **levé par la décision ci-dessous** ; le code, lui, n'a pas encore changé
> (aucun code écrit à la date de cette note).
>
> **Décidé (2026-09-19).** Le crédit **existe et sera repris** (réponses aux
> questions 1 à 6 ci-dessous) :
> 1. Un **fichier clients nominatif** existe : chaque client identifié par
>    son **nom** et son **téléphone** (pas de liste courte informelle).
> 2. Chaque client a un **plafond de crédit fixé par le responsable**, avec
>    une **valeur par défaut configurable par boutique** — **100 000 FCFA**
>    pour Ets Quincaillerie Franck — dépassable **au cas par cas** pour les
>    clients réguliers et les professionnels (le responsable peut fixer un
>    plafond différent du défaut, par client).
> 3. Paiements mixtes : **non traités par cette décision**, question 3
>    laissée sans réponse explicite — à ne pas construire tant qu'elle n'est
>    pas confirmée séparément.
> 4. Créance non recouvrée : **non traité** — aucune relance automatique, pas
>    de règle d'abandon de créance en version 1 (voir ci-dessous, « aucun
>    intérêt, aucune relance automatique »). Reste ouvert si le besoin se
>    présente réellement.
> 5. Enregistrement d'un règlement : **règlements partiels autorisés**, sans
>    préciser explicitement qui peut les enregistrer (comptabilité,
>    responsable, ou les deux) — à confirmer si cela devient un point de
>    friction réel.
> 6. Le tableau de bord du responsable montre l'**encours total** et les
>    **créances de plus de 30, 60 et 90 jours** (échéancier par ancienneté,
>    pas seulement un total).
>
> **Règles complémentaires, non demandées par les 6 questions d'origine mais
> précisées par le propriétaire :** une vente à crédit crée une **créance**,
> **jamais** une recette encaissée (cohérent avec la « Règle proposée »
> ci-dessous, déjà correcte) ; **aucune relance automatique, aucun intérêt**
> en version 1 ; la fonction crédit est **activable ou désactivable par
> boutique** dans la gamme Akuma (consigné dans `VISION_PRODUIT.md` — une
> boutique de la gamme peut fonctionner sans crédit client du tout).
>
> **Reprise nécessaire, à ne pas oublier au chargement du stock initial
> (point j) :** 15 à 25 clients ont une dette en cours, tenue dans un
> **cahier de crédit** physique — leur chargement initial (nom, téléphone,
> solde de départ, plafond éventuel déjà connu) doit être prévu au même
> titre que le stock, pas traité comme un cas annexe.
>
> **Livré (2026-09-25, migration 045).** Client (nom, téléphone, plafond
> 100 000 FCFA par défaut, dépassable par le responsable) ; une vente à
> crédit crée une créance, jamais une recette (question 1-2 tenues) ;
> règlements partiels, **alloués en FIFO contre les créances les plus
> anciennes** — jamais liés à une créance précise, comme le cahier papier
> ne l'a jamais demandé (répond à la question 5 en ouvrant l'écriture du
> règlement au responsable ET à l'agent comptabilité) ; encours et
> vieillissement 30/60/90 jours sur le tableau de bord du responsable
> (question 6) ; activable/désactivable par boutique (question implicite
> de la gamme, `VISION_PRODUIT.md`) ; chargement initial des créances,
> `db/outils/importer_creances_initiales.py`, même discipline que le point j.
> **Non traité, comme explicitement laissé ouvert ci-dessus** : paiements
> mixtes (question 3), créance non recouvrée/relance/abandon (question 4).
> **Trouvé et corrigé en construisant ce chantier** : `annuler_vente()`
> (migration 017) contre-passait inconditionnellement une recette par une
> dépense — pour une vente à crédit, qui n'en a jamais créé, cela aurait
> produit une dépense fantôme. Corrigé : la créance est annulée à sa place ;
> une créance déjà entamée par un règlement refuse l'annulation (le premier
> des « cas limites » ci-dessous reste donc réellement ouvert, le second
> — annulation après règlement partiel — refuse plutôt que d'inventer un
> avoir).

**Contexte.** `mode_paiement = 'credit_client'` est autorisé. Le cahier des charges (§3.3)
crée une **recette immédiate** à la validation de la vente. Or, en crédit, **aucun argent
n'est entré**. Il n'existe ni table `clients`, ni créance, ni solde, ni règlement ultérieur.
Comptabiliser une recette pour une vente à crédit fausse les recettes du jour et le
rapprochement de caisse.

**Règle proposée.**
- Créer une entité **Client** (nom, téléphone, plafond de crédit optionnel).
- Une vente `credit_client` :
  - décrémente le stock comme une vente normale ;
  - **ne crée pas** de recette ; elle crée une **créance** d'un montant égal au total TTC,
    rattachée au client, statut `ouverte` ;
  - le chiffre d'affaires du jour distingue **CA facturé** (inclut le crédit) et
    **encaissements du jour** (exclut le crédit).
- Un **règlement** (espèces, Orange Money, MTN MoMo, autre) réduit le solde de la créance et
  crée la **recette** à la date du règlement. Règlements partiels autorisés.
- Solde client = Σ créances ouvertes − Σ règlements. Consultable par responsable et
  comptabilité.
- Une créance soldée passe en statut `reglee` ; jamais supprimée.

**Cas limites.**
- Règlement partiel, puis second règlement.
- Vente à crédit **annulée** avant tout règlement → créance annulée (tracée), stock restitué.
- Vente à crédit annulée **après** un règlement partiel → avoir / remboursement à définir.
- Client qui dépasse son plafond de crédit → blocage ou alerte responsable ?
- Créance ancienne jamais réglée → relance, passage en « douteuse », abandon de créance
  (écriture comptable dédiée) ?
- Règlement d'un montant supérieur au solde (avance client) → refus ou avoir ?
- Paiement mixte : une partie espèces, le reste à crédit sur la même vente.

**Questions au propriétaire.**
1. Faut-il un **fichier clients** nominatif, ou le crédit est-il réservé à quelques clients
   connus (liste courte gérée par le responsable) ?
2. Un **plafond de crédit** par client est-il souhaité ? Avec blocage automatique ou simple
   alerte ?
3. Les **paiements mixtes** (partie comptant, partie crédit) existent-ils dans la pratique ?
4. Que devient une créance **non recouvrée** après X mois (relance, abandon, provision) ?
5. Qui peut enregistrer un **règlement de créance** : comptabilité, responsable, les deux ?
6. Le tableau de bord doit-il afficher l'**encours crédit total** et la liste des clients
   débiteurs ?

---

## c) Numéro du facturier papier + identification du vendeur

> **Décidé (2026-09-13).** Un facturier **par site**, avec préfixe
> (`MAG-####` au Magasin, `CPT-####` au Comptoir) : `numero_facturier`
> et `vendeur_id` deviennent obligatoires sur chaque vente. **Livré au
> cycle 27** (socle réduit, voir `db/migrations/020_facturier_vendeur.sql`) —
> les questions 2 et 4 (format au-delà du préfixe, blocage) sont
> couvertes par ce socle (préfixe vérifié en base ; « obligatoire »
> revient à un blocage).
>
> **Décidé (2026-09-18), question 5.** Seuil de signalement d'un prix
> négocié : **10 % sous le prix catalogue**, valeur de **configuration**
> (pas une constante figée dans le code — modifiable sans redéploiement,
> même principe que `taux_tva`/`seuil_ecart_caisse_tolere`). Un écart au-delà
> de ce seuil **signale** la vente dans le futur rapport « écarts de prix
> par vendeur » — il ne bloque **jamais** la vente elle-même, cohérent avec
> le principe du projet qu'un encaissement déjà fait n'est jamais remis en
> cause. Chantier de construction du rapport lui-même **pas encore
> démarré** : reste bloqué sur la question 3 ci-dessous (voir note),
> toujours ouverte — coder le rapport sans y répondre exclurait
> silencieusement les ventes d'un vendeur sans compte, si le cas existe
> réellement.
>
> **Décidé (2026-09-19), question 3 — portée gamme Akuma, pas seulement ce
> client.** L'employé et le compte utilisateur sont deux notions
> **distinctes**. Le champ « vendeur » d'une vente pointe vers une **fiche
> employé du module RH** (`employes`, chantier C6), jamais vers un compte de
> connexion (`utilisateurs`, chantier C2). Un employé peut exister **sans
> compte** — il vend, il est traçable par sa fiche employé, il ne se
> connecte simplement jamais à l'application. Un compte, à l'inverse,
> **appartient toujours** à un employé (pas de compte flottant sans fiche).
> La liste proposée à la saisie de `vendeur_id` devient celle des **employés
> actifs du site**, pas celle des comptes utilisables comme aujourd'hui
> (`GET /ventes/vendeurs`, cycle 27). Le rapport « écarts de prix par
> vendeur » (ci-dessus) devient un **rapport par employé**.
>
> **Conséquence sur le modèle de données actuel, non appliquée par cette
> note** (aucun code écrit ici) : `ventes.vendeur_id` référence aujourd'hui
> `utilisateurs(id)` (migration 020) — il devra référencer `employes(id)`
> à la place. Implique une migration de schéma (nouvelle contrainte de clé
> étrangère, reprise des lignes déjà saisies depuis le cycle 27 vers la
> fiche employé correspondante) et la réécriture de `GET /ventes/vendeurs`
> pour interroger `employes` plutôt que `utilisateurs`. Chantier à part
> entière, non démarré, candidat pour un prochain cycle C5/C6.
>
> **Confirmé (2026-09-19), avec le contexte réel de la boutique.** 4 à 6
> personnes négocient effectivement des prix, dont des **aides occasionnels
> sans contrat** — exactement le cas « employé sans compte » anticipé
> ci-dessus, pas une hypothèse théorique. Le responsable veut savoir
> **chaque soir qui a vendu quoi et à quel prix** : c'est le rapport par
> employé mentionné ci-dessus qui répond à ce besoin, une fois le chantier
> mené.
>
> **Livré (chantier B, 2026-09-25, migration 040).** `ventes.vendeur_id`
> référence désormais `employes(id)`, plus `utilisateurs(id)` ;
> `GET /ventes/vendeurs` interroge `employes` (actifs, du site — ou
> `site_id` NULL, couvre les deux, même convention que
> `declarations_article_offert.employe_id`, migration 039).
> Confirmé le même jour : le projet est encore avant son premier
> lancement réel (point j non traité), aucune vente réelle à reprendre —
> la « reprise des lignes déjà saisies » anticipée ci-dessus ne s'est pas
> posée. **Le lien structurel « un compte appartient toujours à un
> employé » reste NON construit**, volontairement laissé hors du
> périmètre de ce chantier (la présélection automatique du vendeur, qui
> l'aurait exploité, est abandonnée — choix manuel désormais systématique) ;
> le rapport « écarts de prix par vendeur »/« par employé » reste
> également non construit (question 5 du seuil, ci-dessus, non ré-ouverte).

**Contexte.** La saisie des ventes est faite **a posteriori** par le comptable, d'après le
**facturier papier** tenu par le responsable après négociation. Le schéma ne stocke ni la
**référence de la pièce papier**, ni **qui a réellement vendu / négocié le prix**
(`ventes.utilisateur_id` = le comptable qui saisit ; `utilisateur_caisse_id` = qui encaisse).
Sans ces deux informations, l'objectif anti-vol est inatteignable : un écart entre prix
catalogue et prix facturé ne peut être rattaché à personne.

**Règle proposée.**
- Ajouter à chaque vente :
  - `numero_facturier` — **obligatoire** et **unique**, saisi par le comptable, tel qu'inscrit
    sur le carnet papier (référence de rapprochement).
  - `vendeur_id` (ou `vendeur_nom` si le vendeur n'a pas de compte) — **obligatoire** :
    la personne qui a négocié le prix et rempli la ligne du facturier.
- Contrôle de cohérence à la saisie : `numero_facturier` non déjà utilisé ; format libre
  mais non vide ; alerte si numéro non consécutif au précédent (trou dans le carnet).
- Rapport « **écarts de prix par vendeur** » : pour chaque vente où
  `prix_unitaire ≠ prix catalogue`, montant et % d'écart, agrégés par vendeur et par période.
- Le `numero_facturier` figure sur le reçu imprimé et dans tous les exports autorisés.

**Cas limites.**
- Page du carnet papier annulée / raturée → saisir le numéro avec statut `annulee` côté
  papier, sans mouvement de stock.
- Un même numéro de facturier couvrant plusieurs clients (erreur de tenue du carnet).
- Vendeur = responsable lui-même (cas courant) → toujours renseigné explicitement.
- Vendeur sans compte utilisateur (extra, apprenti) → liste de « vendeurs » distincte des
  comptes de connexion ?
- Carnet papier perdu / illisible pour une journée.
- Deux carnets papier en parallèle (un par site) → numéros qui se chevauchent → préfixe par
  site.

**Questions au propriétaire.**
1. Y a-t-il **un seul** facturier papier, ou **un par site** ? Faut-il un préfixe
   (ex. `MAG-0842`, `CPT-0842`) ?
2. Le numéro de facturier est-il **purement numérique et séquentiel**, ou comporte-t-il déjà
   un format (année, série) ?
3. ~~Les vendeurs sont-ils **toujours** des personnes ayant un compte dans l'application, ou
   faut-il une liste de vendeurs à part ?~~ **Tranché le 2026-09-19** : liste
   à part — les employés actifs du site (voir le callout en tête de section).
4. Veut-on **bloquer** la saisie d'une vente sans numéro de facturier, ou seulement
   **alerter** ?
5. ~~L'écart prix catalogue / prix négocié doit-il déclencher une **validation du responsable**
   au-delà d'un certain seuil (ex. remise > 15 %) ?~~ **Tranché le 2026-09-18** :
   seuil de 10 %, en configuration, signale sans jamais bloquer (voir le
   callout en tête de section).

---

## d) Régime fiscal et TVA

> **Décidé (cycle 6, 2026-09-12).** Régime du **réel**, taux de TVA
> **19,25 %** (global, sans séparer TVA/CAC sur les documents — aucun ticket
> imprimé n'existe encore pour que la question se pose). Les prix négociés
> avec le client sont compris **TTC**. Arrondi **arithmétique standard**
> (0,5 arrondit vers le haut), calculé sur le **total** de TVA de la vente,
> jamais ligne à ligne. Appliqué dans `db/migrations/011_ventes_fiscalite_
> anti_survente.sql` (table `parametres`) et `server/app/routes/ventes.py`.
> Restent ouvertes, non bloquantes pour C5 : le numéro de contribuable et les
> mentions légales (question 4 — aucun document imprimé n'existe encore) et
> les ventes exonérées (question 5 — aucun cas rencontré à ce jour).
>
> **Décidé (2026-09-19), question 1.** Le régime fiscal réel de la boutique
> est déterminé par le seuil légal : chiffre d'affaires annuel
> **supérieur à 50 millions de FCFA** ⇒ **régime du réel**, TVA applicable au
> taux de **19,25 %** — confirme et documente la valeur déjà appliquée
> depuis le cycle 6, cette fois avec sa justification. Le taux **reste une
> valeur de configuration** (`parametres.taux_tva`), jamais codée en dur, et
> doit pouvoir être **nul** pour une autre boutique de la gamme Akuma dont le
> chiffre d'affaires resterait sous ce seuil (mécanique déjà en place,
> confirmée comme exigence permanente — voir `VISION_PRODUIT.md`).
>
> **Question 3 toujours ouverte, à confirmer par le comptable avant tout
> code qui la figerait.** Les prix négociés au comptoir sont-ils saisis
> **TTC** ou **HT** ? Hypothèse de travail du propriétaire, **non validée** :
> au comptoir, le client négocie un **montant total à payer** — le prix
> négocié serait donc **TTC**, le HT se recalculant pour les rapports
> (cohérent avec le fonctionnement actuel de `server/app/routes/ventes.py`,
> qui extrait la TVA d'un total TTC). **Aucun code n'est à écrire tant que
> le comptable n'a pas confirmé** — l'hypothèse, si elle se révèle exacte,
> ne fera que documenter un comportement déjà en place ; si elle se révèle
> fausse, elle changerait un calcul déjà en production.

**Contexte.** Le cahier des charges calcule « la TVA » mais ne précise ni le **régime
fiscal**, ni le **taux**, ni les **règles d'arrondi**, ni les cas d'**exonération**.
`ventes.taux_tva` a pour défaut `0`. Au Cameroun, selon le chiffre d'affaires et le régime,
une petite quincaillerie peut relever de l'**impôt libératoire**, du **régime simplifié**, ou
du **régime du réel** (assujettie à la TVA, taux courant **19,25 %** = 17,5 % + 10 % de CAC).

**Règle proposée.**
- Le **taux de TVA est une valeur de configuration** (table `parametres`), pas une constante
  de code. Une seule valeur active à la fois, historisée (date d'effet).
- L'application doit pouvoir fonctionner **sans aucune TVA** : taux = 0 ⇒ pas de ligne TVA
  sur les documents, `sous_total_ht = total_ttc`, mention « TVA non applicable » si le régime
  l'exige.
- Chaque vente **fige** le taux appliqué (`ventes.taux_tva`) — un changement de taux futur
  ne réécrit pas l'historique.
- Arrondi : **au franc CFA entier** (pas de centimes de franc), méthode d'arrondi à préciser
  (arithmétique / commercial). Arrondi calculé sur le **total de la TVA de la vente**, pas
  ligne à ligne, pour éviter les écarts d'un franc.
- Prix catalogue et prix négociés saisis **TTC** ou **HT** : à trancher (voir questions).
- Les documents (ticket, facture) affichent les mentions légales correspondant au régime
  (n° de contribuable, régime, « TVA non applicable — art. … » le cas échéant).

**Cas limites.**
- Passage d'un régime à l'autre en cours d'exercice (changement de taux à une date d'effet).
- Article ou client exonéré (revente à un organisme, export) alors que la boutique est
  assujettie.
- Prix « rond » négocié avec le client (ex. 11 500 FCFA) : est-ce un montant **TTC** dont il
  faut extraire la TVA, ou un **HT** auquel on ajoute la TVA ?
- Facture d'avoir (retour) : TVA reprise au même taux que la vente d'origine.
- Ventes antérieures au paramétrage de la TVA.

**Questions au propriétaire.**
1. **Quel est le régime fiscal réel de la boutique** aujourd'hui : impôt libératoire, régime
   simplifié, ou régime du réel (assujettie TVA) ?
2. Si assujettie : le taux est-il **19,25 %** ? Faut-il faire apparaître séparément TVA et
   CAC, ou un taux global ?
3. Les prix affichés et négociés avec le client sont-ils compris comme **TTC** (le client
   paie ce montant, la TVA est « dedans ») ou **HT** (TVA ajoutée au moment de la vente) ?
4. Faut-il un **numéro de contribuable** et des mentions légales sur les tickets et factures ?
   Lesquelles ?
5. Y a-t-il des **ventes exonérées** (clients ou produits particuliers) ?
6. Arrondi : au **franc entier** systématiquement ? Arrondi commercial (0,5 vers le haut) ?

---

## e) Contradiction : décrément atomique anti-survente vs. saisie a posteriori

> **Décidé (cycle 6, 2026-09-12), question 1 confirmée.** La règle proposée
> ci-dessous est retenue telle quelle : une vente déjà encaissée **n'est
> jamais bloquée**, le stock est ramené à 0 (jamais négatif), l'écart est
> consigné dans `ecarts_stock_ventes` et réservé au responsable (jamais visible
> de l'agent stock — comptage à l'aveugle, chantier C7). Appliqué dans
> `db/migrations/011_ventes_fiscalite_anti_survente.sql`
> (`decrementer_stock_vente`) et prouvé par `db/tests/03_concurrence.sh`
> (6/6). Questions 2 à 5 restent ouvertes et **non traitées** ce cycle :
> aucun seuil d'alerte immédiate au-delà du simple enregistrement, aucune
> route de régularisation d'un écart, aucun plafond de vraisemblance par
> ligne, et la sortie de stock manuelle / le transfert (hors périmètre C5)
> restent à trancher séparément.

**Contexte.** Le cahier des charges (§3.3), le scénario de test (client n°8) et le dossier de
recette (§6) exigent tous que l'application **refuse** une vente quand le stock est
insuffisant, et que **deux ventes concurrentes** sur `stock = 1` n'en laissent passer
**qu'une**. Mais le circuit réel fait **saisir la vente après l'encaissement** : le client a
déjà payé et emporté la marchandise. **Un logiciel ne peut pas refuser une vente déjà
encaissée.** Les deux règles ne peuvent pas coexister telles quelles.

**Règle proposée — autoriser la saisie avec alerte d'écart, plutôt que blocage.**
- La saisie d'une vente **n'est jamais bloquée** pour cause de stock insuffisant. Elle est
  **toujours enregistrée** (la marchandise est déjà partie).
- Si `quantité vendue > quantité en stock`, la vente est enregistrée **avec un marqueur
  « écart de stock »**, le stock est porté à **0** (jamais négatif), et l'écart
  (`quantité manquante`) est :
  - inscrit dans un **journal d'écarts de stock** (article, quantité, vente, date, saisisseur) ;
  - **poussé vers le prochain comptage d'inventaire** comme différence à expliquer ;
  - **remonté au responsable** (alerte tableau de bord + rapport « écarts »).
- Le stock négatif reste **interdit par la base** (`CHECK (quantite_stock >= 0)`), mais côté
  application cela se traduit par « stock ramené à 0 + écart consigné », pas par un refus.
- Une **régularisation d'inventaire** (entrée/sortie de correction, motivée, par le
  responsable ou l'agent stock) solde l'écart après enquête.
- Le **refus dur** ne subsiste que pour les opérations faites **avant** que la marchandise
  parte : une **sortie de stock manuelle** de l'agent stock, ou un **transfert** (point a),
  au-delà du disponible → refusés. La *saisie comptable d'une vente* n'entre pas dans ce cas.

**Ce que devient le test de concurrence.** Le test « stock = 1, deux ventes simultanées sur
deux postes » ne teste plus un **refus** mais l'**absence de corruption** :
- les deux ventes sont enregistrées (les deux clients ont payé) ;
- le stock final est **exactement 0**, **jamais négatif**, quel que soit l'entrelacement ;
- **un** écart de stock de **1 unité** est consigné (et un seul), rattaché à la seconde
  vente dans l'ordre de validation ;
- aucune ligne de vente perdue, aucun double décrément, `quantite_stock` cohérent avec la
  somme des mouvements.
Le décrément reste donc **atomique et sérialisé** (verrou de ligne sur l'article, ou
`UPDATE … SET quantite_stock = GREATEST(0, quantite_stock - :q)` en une instruction), mais
son rôle est d'empêcher la **corruption concurrente**, pas de rejeter une vente.

**Cas limites.**
- Vente saisie en retard alors qu'une entrée de stock est passée entre-temps (le stock a été
  reconstitué) → pas d'écart, comportement normal.
- Deux comptables saisissant deux ventes du même article quasi simultanément.
- Écart consigné puis **vente annulée** par le responsable → l'écart doit être **repris**
  (annulé lui aussi), stock restitué.
- Article dont le stock est déjà à 0 par erreur de saisie antérieure → toute vente crée un
  écart ; il faut pouvoir distinguer « vrai manquant » de « stock jamais initialisé ».
- Faut-il **empêcher** de saisir une quantité manifestement absurde (ex. 10 000 sacs) même
  si on n'empêche pas l'écart ?

**Questions au propriétaire.**
1. Confirmez-vous la règle : **on n'empêche jamais** la saisie d'une vente déjà encaissée,
   même à découvert de stock, et on **consigne un écart** que l'inventaire devra expliquer ?
2. Au-delà de quel **écart** (en quantité ou en valeur) veut-on une **alerte immédiate** au
   responsable, plutôt qu'un simple report au comptage ?
3. Qui a le droit de **régulariser** un écart de stock : responsable seul, ou aussi agent
   stock avec motif ?
4. Veut-on un **plafond de vraisemblance** (quantité maximale par ligne) qui, lui, bloque la
   saisie pour éviter les fautes de frappe ?
5. La **sortie de stock manuelle** de l'agent stock et le **transfert** doivent-ils, eux,
   rester **bloqués** au-delà du disponible ? (proposition : oui)

---

## f) Retours, casse, avaries, remises ; conversion d'unités

> **Décidé (cycle 9, 2026-09-13), volet « retours et casse » seulement.**
> Trois opérations distinctes, jamais confondues avec une correction de
> quantité : **casse ou avarie** (sortie à motif obligatoire, validée par
> le responsable seul — un agent stock ne peut pas l'enregistrer) ;
> **retour client** (entrée rattachée à la vente d'origine, refusée si la
> vente n'existe pas ou n'est pas du même site) ; **retour fournisseur**
> (sortie rattachée à la réception d'origine, refusée si le mouvement
> visé n'est pas une réception fournisseur). Chacune tracée, horodatée,
> attribuée. Appliqué dans
> `db/migrations/014_articles_stock_transferts_retours.sql`
> (`enregistrer_casse`, `enregistrer_retour_client`,
> `enregistrer_retour_fournisseur`). Les **remises** et la **conversion
> d'unités** ne sont pas traitées par cette décision et restent
> entièrement ouvertes.
>
> **Décidé (2026-09-22), réponses aux 5 questions ci-dessous — complète la
> décision du cycle 9, ne la remplace pas.** Principe directeur, formulé
> par le propriétaire lui-même et transversal à tout ce point : **aucune
> différence entre stock théorique et stock réel ne doit pouvoir
> apparaître sans une opération explicite qui l'explique** — chaque
> mouvement ci-dessous est une opération tracée et identifiable, jamais
> une modification manuelle silencieuse.
>
> 1. **Retours clients** : validation du responsable **obligatoire** avant
>    tout retour (aucune réintégration automatique) — l'état de l'article
>    est vérifié avant réintégration au stock (une marchandise invendable
>    reprise ne revient **pas** en stock, cf. « Cas limites » ci-dessous,
>    déjà anticipé). **Trois issues possibles**, jamais une seule : échange,
>    avoir client, remboursement espèces — ce dernier exige une
>    **autorisation explicite du responsable**. Chaque retour est tracé
>    **à la fois** dans l'historique du stock **et** dans celui de la
>    vente d'origine (pas l'un ou l'autre).
> 2. **Casse / avaries** : la **déclaration** (constat) est ouverte à
>    **n'importe quel utilisateur** (magasinier, vendeur, responsable) qui
>    la constate, mais la **validation de la sortie de stock** reste
>    réservée au responsable **seul** — un simple utilisateur ne retire
>    jamais un article du stock unilatéralement (distinction
>    déclaration/validation qui **durcit** ce qu'`enregistrer_casse`
>    posait au cycle 9 — voir « conséquence technique » plus bas). Le
>    mouvement retient systématiquement : article, quantité, motif, site,
>    utilisateur déclarant, date/heure, validation du responsable,
>    observation libre optionnelle.
> 3. **Unités de vente — le point le plus structurant.** Chaque article
>    porte sa **propre** unité de vente (sac, pièce, barre, mètre, litre,
>    kilogramme, …), définie sur sa fiche — **pas** de référentiel
>    global imposé uniformément. Chaque article est en outre configuré
>    **individuellement** pour n'accepter **que** des quantités entières
>    (ex. sac de ciment) ou pour accepter des **quantités décimales**
>    (ex. 12,50 m de câble, 2,5 L de peinture) : ce paramétrage se fait
>    **par article**, jamais globalement. Exemples cités : fil électrique
>    au mètre, peinture/liquides en quantité inférieure au contenant,
>    matériaux coupés à la longueur demandée quand techniquement
>    possible, clous/vis vendus en quantité plutôt qu'au conditionnement
>    complet. **Conséquence technique directe** : les colonnes de
>    quantité concernées (`stocks_sites.quantite_stock`,
>    `mouvements_stock`, `comptages_stock`, lignes de vente/retour/casse)
>    doivent devenir **`NUMERIC`** au lieu d'`INTEGER`, avec un indicateur
>    par article (`articles.quantite_decimale_autorisee` ou équivalent)
>    qui **contraint la saisie/la vente** à un entier quand il est faux —
>    validation applicative **et** contrainte base (`CHECK`), pas l'une
>    sans l'autre.
> 4. **Remises** : **toujours visibles explicitement** sur le ticket (prix
>    normal, montant de la remise, total réellement payé) — **jamais**
>    une modification silencieuse du prix affiché. Applicable **au choix**
>    au niveau d'**une ligne** d'article **ou** de la **vente entière**
>    (deux mécanismes, pas un seul). Exprimée en **montant ou en
>    pourcentage**, au choix du vendeur. Les trois valeurs — prix initial,
>    montant de la remise, montant réellement payé — sont **conservées
>    séparément**, jamais fusionnées en une seule colonne de prix
>    modifié. **Autorisation du responsable exigée au-delà d'un seuil** —
>    **valeur du seuil non donnée par le propriétaire, reste `a_definir`**
>    (même sentinelle que `duree_session_minutes`, `seuil_ecart_caisse_tolere`,
>    `plafond_vraisemblance_comptage` : aucun blocage tant qu'un chiffre
>    n'est pas fixé). Le cumul des remises accordées doit rester
>    exploitable dans un rapport ultérieur (chantier C8, pas ce point).
> 5. **Articles offerts** : **distinct** d'une remise à 100 % — c'est une
>    **« sortie commerciale gratuite »** identifiée comme telle en base,
>    **jamais** une vente à prix nul. L'article est bien **déduit du
>    stock**, même si le montant facturé est zéro. Conservés
>    systématiquement : article, quantité, **valeur normale** (pour ne
>    **pas** fausser la marge dans les rapports C8 — la valeur théorique
>    perdue doit rester visible même si la recette encaissée est nulle),
>    client si identifié, motif, utilisateur, validation du responsable
>    si nécessaire.
>
> **Reste ouvert, non tranché par cette décision** : le chiffre exact du
> seuil de remise nécessitant validation responsable (point 4 —
> `a_definir`, mécanique prête mais aucun blocage tant qu'il n'est pas
> fixé, même principe que les autres sentinelles du projet).

**Contexte.** Aucun de ces éléments n'est modélisé. `mouvements_stock.type` ne connaît que
`entree` / `sortie`. Les remises sont noyées dans `ventes_lignes.prix_unitaire`. `unite` est
un texte libre sans référentiel ni règle de conversion.

**Règle proposée.**
- **Retour client** : opération dédiée générant un **avoir** (facture d'avoir numérotée),
  qui **remet la marchandise en stock** (mouvement `retour`), **retire la recette**
  correspondante (ou crée un remboursement selon le mode), et reste **tracée** (motif,
  autorisée par le responsable). Un retour référence toujours la **vente d'origine**.
- **Casse / avarie / perte** : mouvement de stock de type `casse` (ou `perte`), **motif
  obligatoire**, **sans recette**, réservé au responsable (ou agent stock avec validation
  responsable). Apparaît dans un rapport « pertes » distinct des ventes.
- **Remise** : la remise reste exprimée par le `prix_unitaire` négocié (déjà le cas), mais
  on ajoute, en option, un champ `remise_pct` ou `remise_montant` **par ligne** pour la
  rendre explicite sur le document et dans les rapports (et pour le contrôle du point c).
- **Unités** : référentiel d'unités fermé (`sac`, `barre`, `kg`, `m`, `L`, `pièce`, `m³`, …).
  Conversions gérées comme des **articles distincts liés** (« Ciment 50 kg » vs « Ciment
  vrac kg » avec un facteur), **pas** de conversion implicite à la volée dans une vente.
  Le vrac (quantité décimale) impose de revoir `quantite INTEGER` → `NUMERIC` sur les
  articles concernés.

**Cas limites.**
- Retour partiel d'une vente multi-lignes.
- Retour d'une vente à crédit non encore réglée (point b).
- Marchandise reprise **invendable** (cassée au retour) → retour **sans** remise en stock,
  vers « pertes ».
- Casse constatée **pendant** un comptage d'inventaire (écart = casse identifiée).
- Article vendu à l'unité mais acheté au sac (1 sac = 50 kg) : quantité en stock décimale.
- Remise à 100 % (article offert) : stock décrémenté, recette nulle — à distinguer d'une
  casse.

**Questions au propriétaire.**
1. Les **retours clients** existent-ils dans la pratique ? À quelle fréquence ? Avec
   remboursement en espèces ou avoir sur un prochain achat ?
2. Comment sont traitées aujourd'hui la **casse** et les **avaries** (qui les constate, qui
   les valide) ?
3. Vend-on des articles **au détail dans une unité différente de l'achat** (sac → kg,
   barre → mètre, vrac) ? Lesquels ? Faut-il gérer des **quantités décimales** ?
4. Les **remises** doivent-elles apparaître explicitement (ligne « remise ») sur le ticket,
   ou rester intégrées au prix ?
5. Un article **offert** (remise 100 %) : cas réel ? Comment le distinguer d'un cadeau
   commercial dans les comptes ?

---

## g) Clôture de caisse quotidienne et rapprochement

> **Décidé (2026-09-13).** Une clôture **par site** (Magasin et Comptoir
> clôturent séparément), selon l'écran proposé ci-dessous : total attendu
> par mode de paiement, comptage réel saisi par le responsable, écart
> calculé et figé. Les questions 2 à 6 (fond de caisse initial, qui
> clôture et à quelle heure, rapprochement Mobile Money, seuil d'écart
> toléré, blocage ou simple marquage de la journée) restent à trancher au
> moment de l'implémentation (chantier dédié, diagnostic puis plan avant
> tout code).

**Contexte.** Aucune clôture de caisse n'est prévue (ni CDC, ni schéma). Le responsable
encaisse au comptoir mais rien ne rapproche, en fin de journée, les **espèces réellement en
caisse** des **recettes enregistrées**.

**Règle proposée.**
- Écran **« Clôture de caisse »** (responsable, une par jour et par site où il y a
  encaissement) :
  - le système affiche le **total attendu** par mode de paiement (espèces, Orange Money,
    MTN MoMo, autre) pour la journée, à partir des ventes `payee` et des règlements de
    créance ;
  - le responsable saisit les **espèces comptées** (et, si possible, les relevés Mobile
    Money) ;
  - le système calcule l'**écart de caisse** (compté − attendu) par mode ;
  - un **commentaire** est obligatoire si l'écart dépasse un seuil ;
  - la clôture est **figée** (date, auteur, montants, écart) et non modifiable ; une
    correction se fait par une clôture rectificative tracée.
- Une journée non clôturée est signalée sur le tableau de bord du responsable.
- Les ventes saisies **après** la clôture d'une journée sont rattachées à la journée en
  cours, ou nécessitent une réouverture tracée (voir questions).

**Cas limites.**
- Saisie comptable tardive (vente d'hier saisie aujourd'hui) après clôture d'hier.
- Fond de caisse initial (monnaie de départ) à déduire du comptage.
- Écart de caisse récurrent → rapport de suivi des écarts par période / par personne.
- Journée sans aucune vente (dimanche) → clôture à zéro ou pas de clôture ?
- Encaissements Mobile Money non rapprochables faute de relevé.
- Deux sites : une clôture par site, ou une seule pour la boutique ?

**Questions au propriétaire.**
1. Y a-t-il **une caisse physique** unique (comptoir), ou de l'encaissement des deux côtés ?
2. Existe-t-il un **fond de caisse** de départ chaque matin ? Quel montant ?
3. Qui fait la clôture, à quelle heure, et que fait-on des **ventes saisies en retard** après
   clôture ?
4. Rapproche-t-on aussi **Orange Money / MTN MoMo** (relevés disponibles ?) ou seulement les
   **espèces** ?
5. Quel **écart de caisse** est toléré sans justification (ex. ± 500 FCFA) ?
6. La clôture doit-elle **empêcher** toute nouvelle saisie sur la journée clôturée, ou juste
   la marquer ?

---

## h) Rôle « caissier »

> **Décidé (2026-09-13).** Un rôle `caissier` est créé, **fusionné avec
> le périmètre de l'agent comptabilité** : il encaisse une vente **et**
> peut la saisir (contrairement à la « règle proposée » initiale, qui
> séparait les deux). Reste à trancher au moment de l'implémentation :
> le périmètre exact de lecture (détail des prix ou total seul — question
> 3), le cumul avec d'autres rôles (question 4), et la cohérence avec les
> rôles `agent_comptabilite` déjà existants (fusion des deux rôles, ou
> `caissier` comme rôle distinct avec les mêmes droits — diagnostic puis
> plan avant tout code).
>
> **Diagnostic du chantier C3 (2026-09-18) : architecture déjà conforme,
> aucun nouveau rôle nécessaire.** `qf_agent_comptabilite` **fait déjà les
> deux** aujourd'hui — vérifié par exécution réelle, pas supposé :
> `POST /ventes` l'autorise déjà (`exiger_role("responsable",
> "agent_comptabilite")`), et `vente.html` est même son écran d'accueil
> par défaut après connexion. La fusion décidée ci-dessus correspond donc
> exactement au rôle existant, sans changement de code. Cloisonnement
> confirmé par de vraies requêtes HTTP (pas seulement en SQL direct) :
> `GET /rh/employes` avec un jeton `agent_comptabilite` → `403` (déjà
> couvert par `server/tests/test_rh.py::test_agent_comptabilite_ne_peut_pas_creer_employe`
> et `test_lister_employes_reserve_au_responsable` — la mention « non
> testé par une route » de `loop-state.md` était devenue inexacte depuis
> l'ajout de ces tests) ; `qf_agent_comptabilite` est également exclu de
> `clotures_caisse` (chantier C6, cycle 25 — seul le responsable clôture).
> **Fournisseurs : pas un vrai manque.** La table `fournisseurs` n'a pas
> de colonne `site_id` (partagée entre les deux boutiques par construction)
> et aucune route `/fournisseurs` n'existe dans le dépôt (`GET
> /fournisseurs` → `404`) — rien à cloisonner par site sur une donnée qui
> n'a jamais été exposée. Le seul point réellement ouvert reste la
> question 3 ci-dessous (périmètre exact de lecture des prix).
>
> **Décidé (2026-09-22), question 4 — cumul de rôles : OUI.** Un compte
> peut porter plusieurs rôles (petit effectif). Livré au cycle 41 (C3) :
> migration 035 `utilisateurs_roles` + `roles_utilisateur()`, jeton portant
> la liste des rôles, `exiger_role` choisissant le rôle effectif par route
> (SET ROLE PostgreSQL), création de compte avec rôles cumulés
> (case « Cumuler aussi l'autre rôle agent » dans `comptes.html`).
> **Question 3 (détail des prix ou total seul pour le caissier) : EN
> ATTENTE, consignée le 2026-09-22** — sa mise en œuvre touche le terrain
> vente, réservé au point f en cours ; elle sera tranchée et implémentée
> quand ce terrain sera libre.

**Contexte.** Le cahier des charges ne prévoit **pas** de rôle caissier : c'est le
**responsable en personne** qui encaisse au comptoir. Le dossier de recette et la checklist
UI parlent pourtant d'un **« caissier »** sur PC (« utilisation clavier par le caissier »,
« PC de caisse »). Le schéma a un `utilisateur_caisse_id` mais aucun rôle `caissier` dans le
`CHECK` de `utilisateurs.role`.

**Règle proposée (à valider).**
- Introduire un **quatrième rôle `caissier`**, rattaché au **comptoir**, dont le périmètre
  est :
  - encaisser une vente `en_attente` (passage à `payee`, saisie du mode de paiement) ;
  - imprimer / réimprimer le reçu ;
  - **ne peut pas** : fixer les prix, annuler une vente, voir les marges, accéder au stock
    détaillé, à la RH, à l'administration.
- Le responsable **conserve** le droit d'encaisser (il reste caissier « par héritage »).
- `utilisateur_caisse_id` pointe vers le caissier **ou** le responsable selon qui a encaissé.
- Si le propriétaire ne veut **pas** de caissier dédié : le rôle n'est pas créé, et
  l'encaissement reste réservé au responsable (statu quo du CDC). Aucune autre modification.

**Cas limites.**
- Caissier absent → le responsable encaisse.
- Un caissier peut-il aussi **saisir** la vente (rôle comptabilité) sur un petit effectif ?
- Cumul de rôles sur une même personne (caissier + agent stock) — autorisé ?
- Le caissier voit-il le **total à encaisser** uniquement, ou aussi le détail des lignes /
  prix ?

**Questions au propriétaire.**
1. Y a-t-il, dans les faits, une **personne dédiée à la caisse** différente du responsable ?
2. Si oui, doit-elle **seulement encaisser**, ou aussi **saisir les ventes** (fusion avec le
   rôle comptabilité du comptoir) ?
3. Le caissier a-t-il le droit de voir le **détail des prix** d'une vente, ou juste le
   **montant total** à encaisser ?
4. Faut-il pouvoir **cumuler** plusieurs rôles sur un même compte (petit effectif) ?

---

## i) Exploitation : onduleur, RPO / RTO, mise à jour des postes

> **Décidé (2026-09-13), question 1.** RPO cible : **1 heure** — sauvegarde
> automatique horaire pendant les heures d'ouverture, plus une en fin de
> journée, comme proposé ci-dessous. Le **mécanisme** de sauvegarde/
> restauration existe déjà (`db/outils/sauvegarder.ps1`/`restaurer.ps1`,
> cycle 21, vérifié par exécution sur une base séparée) ; reste à
> l'automatiser (planification horaire — Tâches planifiées Windows,
> chantier dédié). Questions 2 à 6 (RTO cible, budget onduleur/poste de
> secours, connexion Internet pour une copie distante, qui sait restaurer
> sur place, fréquence acceptable des mises à jour) restent ouvertes.
>
> **Décidé (2026-09-18), chantier C12.** Trois manques bloquant une mise en
> service réelle, réglés :
> - **Chiffrement des sauvegardes** (déjà proposé ci-dessus) : porte sur le
>   fichier produit par `sauvegarder.ps1` lui-même (AES-256 + HMAC-SHA256,
>   PowerShell/.NET natif — aucune dépendance externe, aucune installation
>   sur le poste boutique ; BitLocker To Go écarté, il exige Windows Pro/
>   Enterprise). La **phrase de passe** est saisie par le responsable à la
>   configuration, jamais écrite dans un fichier du dépôt, stockée comme les
>   autres secrets de l'application — voir `db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`
>   §6, à lire avant toute installation.
> - **Sauvegarde sans session Windows ouverte** : `planifier_sauvegarde.ps1
>   -CompteSysteme` enregistre la tâche planifiée sous `NT AUTHORITY\SYSTEM`
>   au lieu d'un compte interactif — s'exécute même si personne n'est
>   connecté au poste.
> - **PostgreSQL non enregistré comme service Windows** — trouvé plus grave
>   que les plantages eux-mêmes : rien ne le relançait après un arrêt brutal,
>   la boutique restait bloquée jusqu'à une intervention technique.
>   `enregistrer_service_pg.ps1` l'enregistre comme service (démarrage
>   automatique + redémarrage automatique après échec).
> - **Écran figé quand la base devient injoignable** — le pire scénario
>   identifié pour ce chantier : un vendeur devant un écran mort, un client
>   qui attend. L'application affiche désormais, dans ce cas précis, un
>   message clair en français (base injoignable, ce n'est pas la faute du
>   vendeur, la saisie en cours n'est pas perdue, qui prévenir) au lieu de
>   se figer ou d'afficher une erreur technique — voir
>   `server/app/main.py` (gestionnaire `psycopg.OperationalError`) ; le
>   détail technique va au journal serveur, jamais à l'écran du comptoir.

**Contexte.** Coupures de courant fréquentes à Batouri, PostgreSQL sur un poste serveur non
protégé = risque de corruption. Le CDC exige une sauvegarde quotidienne (rétention 30 jours,
copie hors serveur) et une procédure de restauration, mais **aucun script ni procédure n'est
détectable** dans le livré. Rien n'est dit sur la **perte de données acceptable**, le **délai
de reprise**, ni la **mise à jour des 5 postes**.

**Règle proposée.**
- **Onduleur (ASI) obligatoire** sur le poste serveur, dimensionné pour tenir au moins le
  temps d'un **arrêt propre de PostgreSQL** (≈ 10–15 min) ; arrêt automatique déclenché par
  l'onduleur (USB + logiciel) quand la batterie est basse. Onduleur recommandé aussi sur le
  poste de caisse (ne pas perdre une vente en cours).
- **Sauvegardes** :
  - `pg_dump` complet **toutes les heures** pendant les heures d'ouverture + un dump **de
    fin de journée** ;
  - rétention **30 jours** glissants sur le serveur ;
  - **copie automatique** après chaque dump vers un support **hors serveur** (clé USB
    dédiée, second poste, ou stockage distant chiffré si Internet disponible) ;
  - **chiffrement** des sauvegardes qui quittent le serveur ;
  - **notification** (message WhatsApp / e-mail au responsable) en cas d'échec de sauvegarde.
- **RPO proposé : 1 heure** (au pire, on reperd la dernière heure de saisie, rattrapable via
  le facturier papier). **RTO proposé : 2 heures** (temps de remonter une base sur un poste
  de secours).
- **Restauration** : toujours d'abord sur une **base séparée** (`quincaillerie_restore`),
  vérification (10 dernières ventes, soldes, comptes) **avant** toute bascule réelle.
  Procédure écrite, testée **une fois par trimestre**, preuve conservée.
- **Mise à jour des postes** : nouvel exécutable déposé sur un **partage réseau** ; script de
  mise à jour qui vérifie la version, sauvegarde l'ancienne, remplace, journalise ; **schéma
  de base versionné** (migrations numérotées, appliquées par le serveur, jamais à la main) ;
  procédure de **retour arrière** (exécutable précédent + migration inverse ou restauration).
- **Poste serveur** : IP locale fixe, pare-feu ouvert seulement sur le port PostgreSQL et
  seulement pour le sous-réseau de la boutique, démarrage automatique de PostgreSQL au boot,
  reste allumé pendant les heures d'ouverture.

**Cas limites.**
- Coupure pendant un `pg_dump` → le dump partiel doit être écarté, pas écraser le bon.
- Coupure pendant une validation de vente → transaction non committée perdue, stock cohérent
  (atomicité), reprise sans double vente.
- Support de copie (clé USB) plein ou absent.
- Poste serveur physiquement hors service → délai pour redémarrer sur un autre poste.
- Migration de schéma échouée en cours de déploiement.
- Sauvegarde jamais restaurée = sauvegarde non fiable (à tester réellement).

**Questions au propriétaire.**
1. Quelle **perte de données maximale** est acceptable en cas de sinistre : 1 heure de
   saisie ? une demi-journée ? une journée ?
2. Quel **délai de reprise** est acceptable : reprise le jour même ? sous 2 heures ? le
   lendemain ?
3. Y a-t-il **un budget onduleur** et **un poste de secours** identifié pouvant devenir
   serveur ?
4. Une **connexion Internet** est-elle disponible sur le poste serveur pour une copie de
   sauvegarde distante (même lente, une fois par jour) ?
5. Qui, sur place, est capable de **lancer une restauration** en cas d'absence du prestataire ?
   Faut-il une procédure « pas à pas » pour non-technicien ?
6. À quelle **fréquence** accepte-t-on d'interrompre l'activité pour **mettre à jour** les
   postes (soir ? dimanche ?) ?

---

## j) Reprise de l'existant : stock initial, volumétrie, formation

> **Décidé (2026-09-19), question 1 et modalités de chargement.**
> **Volumétrie** : 800 à 1 200 références au total ; 40 à 60 ventes par jour
> ordinaire, 80 à 120 les jours de forte affluence ; 3 à 6 articles par
> vente, davantage sur les ventes de matériaux. **Comptage** : fait par le
> **responsable et les vendeurs**, sur **3 à 5 jours**, boutique **ouverte**
> (pas fermée comme envisagé dans la « Règle proposée » d'origine
> ci-dessous — à corriger en conséquence), **par zones puis par catégories
> successives**.
>
> **Conséquence directe pour l'outil d'import, qui change de nature** : un
> **import unique et global ne convient pas**. L'outil doit accepter
> **plusieurs chargements successifs et partiels** (une zone ou une
> catégorie à la fois, sur plusieurs jours), **sans jamais dupliquer** ce
> qui a déjà été chargé, et **indiquer clairement ce qui reste à traiter**
> (par zone/catégorie, pas seulement un total). Les articles trouvés en
> magasin mais **absents du cahier** sont **créés après validation du
> responsable**, avec désignation, unité, quantité et prix — jamais créés
> automatiquement sans son regard.
>
> **Reprise du crédit client, à charger avec le stock** (voir point b) : 15
> à 25 clients ont une dette en cours dans un cahier de crédit séparé — leur
> chargement (nom, téléphone, solde, plafond éventuel) suit le même
> principe de chargement progressif et validé, pas un import à part isolé.
>
> **Dépendance d'ordre, confirmée par le propriétaire** : ce chargement ne
> peut démarrer **qu'après** le cycle de migration du modèle article/stock
> (point a, « une fiche, un stock par site ») — importer dans l'ancien
> modèle (une fiche par site) puis fusionner après coup doublerait le
> travail et le risque d'erreur.
>
> **Livré (2026-09-25, migration 041) — le STOCK seul.** Dépendance d'ordre
> satisfaite (point a livré aux cycles 34-35, voir plus haut). Mouvement
> `inventaire_initial` dédié, seuil à 20 % (convention retenue), plusieurs
> chargements successifs et partiels sans duplication (`db/outils/importer_stock_initial.py`,
> simulation obligatoire avant tout chargement réel, création d'article
> seulement après confirmation explicite du responsable — voir `db/README.md`,
> « Chargement du stock initial réel »). **Le crédit client N'A PAS été
> chargé avec le stock**, contrairement à ce que demande le callout
> ci-dessus : le point b (reprise du crédit client) n'est pas construit (pas
> de table `clients`) — c'est un chantier séparé, à mener avant de pouvoir
> tenir cette dépendance littéralement.

**Contexte.** La gestion était manuelle (cahier, facturier papier). Il faut **charger le
stock de départ**, connaître les **volumes réels**, et **former** des utilisateurs sans
culture informatique.

**Règle proposée.**
- **Chargement du stock initial** :
  - inventaire physique complet, contradictoire (agent stock + responsable), un site après
    l'autre, boutique fermée ou hors affluence ;
  - saisie via un **import** (fichier Excel : nom, catégorie, unité, quantité, site,
    fournisseur, prix achat, prix vente) fourni par le prestataire, contrôlé puis injecté ;
    à défaut, double saisie manuelle vérifiée ;
  - le chargement initial est un **mouvement `inventaire_initial`** daté, tracé, non
    confondu avec des entrées fournisseur (n'active pas la règle des 20 % — le seuil initial
    est saisi une fois, ou fixé à 20 % de la quantité initiale par convention à valider) ;
  - **gel** des opérations pendant le chargement, puis **rapprochement** avec le dernier état
    du cahier papier.
- **Volumétrie à établir** (par le propriétaire) : nombre d'articles par site, nombre de
  ventes par jour (moyenne / pointe), nombre de lignes par vente, nombre de fournisseurs,
  d'employés. Sert à dimensionner l'ergonomie (recherche, pagination) et le matériel.
- **Formation** :
  - support court **par rôle** (1 à 2 pages, captures, en français simple) ;
  - session pratique **par rôle** sur la base de test, avec le scénario des 10 clients ;
  - période de **double tenue** (papier **et** application) sur 1 à 2 semaines, puis bascule ;
  - un **référent** par site pour les questions du quotidien ;
  - critère de fin de formation : chaque utilisateur réalise seul son parcours type (vente,
    comptage, saisie compta) dans les temps cibles du point k.

**Cas limites.**
- Écart entre stock physique et cahier papier au moment de la reprise (à figer comme point
  de départ, pas à « corriger » a posteriori).
- Articles sans prix connu au moment de la reprise.
- Fournisseurs mal identifiés dans le cahier papier.
- Utilisateur en difficulté persistante avec l'outil après formation.
- Bascule un site à la fois vs. les deux en même temps.

**Questions au propriétaire.**
1. ~~Combien d'**articles** environ par site ? Combien de **ventes par jour** en moyenne et un
   jour de pointe ?~~ **Tranché le 2026-09-19** : voir le callout en tête de
   section (800-1 200 références, 40-120 ventes/jour selon affluence).
   Nombre exact d'employés et de fournisseurs non chiffré par ce même
   callout — 4 à 6 vendeurs confirmés par ailleurs (point c), fournisseurs
   non précisés.
2. Le stock initial peut-il être fourni sous forme de **fichier Excel** exploitable, ou
   faudra-t-il tout **ressaisir** depuis le cahier ?
3. Accepte-t-on une période de **double tenue** (papier + application) avant de basculer ?
   Combien de temps ?
4. Bascule **des deux sites en même temps** ou **l'un après l'autre** ?
5. Qui sont les **référents** pressentis sur chaque site ?
6. Quel est le **niveau de confort informatique** réel de chaque futur utilisateur (pour
   calibrer la formation) ?

---

## k) Critères ergonomiques mesurables

**Contexte.** Le CDC demande une interface « simple », « rapide », « en français », mais sans
**seuils vérifiables**. Le dossier de recette et le propriétaire placent l'ergonomie en
**priorité n°1**.

**Règle proposée — critères de recette, mesurés chronomètre en main et à des résolutions
imposées :**

| # | Critère | Cible | Méthode de mesure |
|---|---------|-------|-------------------|
| k1 | Connexion (saisie identifiant/mot de passe → tableau de bord affiché) | **< 30 s** | Chronomètre, utilisateur non entraîné, 3 essais, on garde le pire |
| k2 | Vente standard (1 article déjà identifié → reçu imprimé) | **< 60 s** | Chronomètre, à partir de l'écran de vente |
| k3 | Ajout d'un article au panier | **1 à 2 actions** (recherche + Entrée) | Comptage des clics/touches |
| k4 | Modifier quantité ou prix d'une ligne | **sans changer d'écran** | Observation |
| k5 | Impression du ticket | **≤ 1 confirmation** | Observation |
| k6 | Message d'erreur | **en français, à côté du champ concerné, dit quoi corriger** | Provoquer 5 erreurs types |
| k7 | Bouton retour / annulation | **toujours visible et identifiable** sur chaque écran | Revue écran par écran |
| k8 | Confirmation avant opération irréversible (annulation de vente, clôture, désactivation de compte) | **systématique et explicite** | Revue |
| k9 | Affichage sans débordement (aucun texte, bouton ou tableau essentiel coupé) | **1366 × 768** (PC) | Redimensionnement + capture |
| k10 | Lisibilité mobile (suivi + saisie) sans zoom, zones tactiles utilisables | **360, 390 et 768 px** de large | Émulateur + appareil réel |
| k11 | Recherche d'un article dans le catalogue complet | **< 3 s** pour afficher le résultat | Chronomètre, catalogue à volumétrie réelle |
| k12 | Navigation entièrement au **clavier** pour la vente (caissier) | **possible de bout en bout** | Test sans souris |
| k13 | Aucune fenêtre modale inutile dans le parcours de vente | **0** | Comptage |

Un critère non mesuré = non acquis. Les mesures sont refaites à chaque cycle de finalisation
touchant C9 ou C10.

**Cas limites.**
- Poste lent / réseau chargé : les cibles s'entendent sur le matériel réel de la boutique,
  pas sur une machine de développement.
- Catalogue qui grossit : k11 doit tenir à 2× la volumétrie annoncée.
- Écran de caisse tactile éventuel (sans clavier) : k12 devient « au clavier **ou** au
  tactile ».

**Questions au propriétaire.**
1. Ces **cibles chiffrées** sont-elles acceptées comme **critères de recette** (une version
   qui ne les atteint pas est refusée) ?
2. Quel est le **matériel réel** des postes (processeur, RAM, taille et résolution d'écran)
   sur lequel mesurer ?
3. Le poste de caisse a-t-il un **clavier**, un **écran tactile**, ou les deux ?
4. Quels **modèles de téléphone** les responsables utilisent (pour fixer les largeurs de
   test) ?
5. Y a-t-il des **contraintes visuelles** (grands caractères, fort contraste) pour certains
   utilisateurs ?

---

## l) Propriété du code source et obligation de livraison du dépôt

> **Décidé (2026-09-13), question 1.** La situation problématique décrite
> ci-dessous (« livré uniquement en exécutables, aucun code source ») est
> déjà résolue en pratique : le dépôt existe sous un compte dont le
> propriétaire détient l'accès administrateur permanent, et chaque cycle
> y est livré en continu. Formalisé dans `OWNERSHIP.md` (nouveau), qui
> documente aussi un audit de l'historique Git complet confirmant
> qu'aucun secret réel n'y a jamais été committé. Questions 2 à 4
> (clause contractuelle de paiement, dépôt fiduciaire, répartition des
> accès) relèvent d'un accord contractuel, hors du périmètre technique.

**Contexte.** L'application a été livrée **uniquement en exécutables**. Aucun code source,
aucun script de fabrication (`.spec` PyInstaller), aucun script de sauvegarde n'existe sur la
machine du propriétaire. Le CDC §7 liste pourtant le code source (dépôt Git) et les scripts
de build parmi les livrables. La situation actuelle rend le propriétaire **captif** du
prestataire et **incapable de reconstruire, corriger ou reprendre** l'outil.

**Règle proposée — à intégrer explicitement au cahier des charges :**
- Le **code source complet** de l'application, de l'API, du schéma de base et des scripts
  (build, sauvegarde, restauration, migrations, tests) est la **propriété des Ets
  Quincaillerie Franck**.
- Le code est livré **en continu** dans un **dépôt Git** dont le propriétaire est
  **titulaire du compte** (organisation / compte GitHub appartenant à la quincaillerie), le
  prestataire étant simple contributeur. Le propriétaire a un **accès administrateur permanent**.
- **Aucune livraison de version** (exécutable) n'est acceptée sans que le **commit
  correspondant** soit présent sur la branche `main` du dépôt, **étiqueté** (tag de version),
  avec les **scripts de fabrication** permettant de régénérer l'exécutable à l'identique.
- Le dépôt contient : code, schéma + migrations, scripts de build PyInstaller, scripts et
  guide de sauvegarde/restauration, jeux de tests, documentation d'installation et
  d'exploitation, `MODELE_DONNEES.md`, `PERIMETRE_LIVRE.md`, le présent addendum.
- Le dépôt **ne contient jamais** : `config.ini` réel, mots de passe, clés secrètes,
  sauvegardes de données réelles, exécutables compilés.
- **Réversibilité** : à la fin de la relation contractuelle, le prestataire remet tout accès
  et toute clé ; le propriétaire doit pouvoir **reconstruire et déployer sans lui**. Une
  clause de **dépôt fiduciaire (escrow)** des secrets de signature/déploiement peut être
  ajoutée.
- Le non-respect de la livraison du dépôt est un **manquement contractuel** conditionnant le
  paiement du solde.

**Cas limites.**
- Bibliothèques tierces sous licence : vérifier la compatibilité (PyQt6 en GPL/commercial),
  documenter les licences.
- Secrets nécessaires au build (certificat de signature Windows) : gérés en escrow, hors dépôt.
- Prestataire qui livre un exécutable « en urgence » sans commit : non conforme, à régulariser
  immédiatement.
- Historique Git réécrit / forcé : interdit sur `main`.

**Questions au propriétaire.**
1. Le dépôt doit-il être hébergé sous un **compte / une organisation appartenant à la
   quincaillerie** (recommandé), plutôt que sous le compte du prestataire ?
2. Souhaitez-vous une **clause explicite** liant le **paiement du solde** à la livraison
   conforme du dépôt et des scripts de build ?
3. Faut-il un **dépôt fiduciaire (escrow)** pour le certificat de signature et les secrets de
   déploiement ?
4. Qui, côté quincaillerie, détient les **accès administrateur** du dépôt et des comptes
   d'hébergement ?
5. Acceptez-vous que ce document (l'addendum) soit **annexé au cahier des charges** et
   **signé** au même titre ?

---

## Récapitulatif des décisions attendues

| Point | Décision structurante | État |
|---|---|---|
| a | **Modèle de transfert inter-sites** | **Décidé cycle 9** (questions 2-3) : opération atomique sortie+entrée, sans recalcul de seuil — questions 1, 4, 5 restent ouvertes, sans effet bloquant |
| b | Créance client / vente à crédit | Statu quo confirmé cycle 6 : **désactivé**, C5/C6 attendent toujours les 6 questions |
| c | **Numéro facturier + vendeur obligatoires** | **Décidé 2026-09-13** : un facturier par site (préfixe MAG-/CPT-). **Question 3 décidée 2026-09-19, livrée 2026-09-25 (chantier B, migration 040)** : le vendeur est une fiche employé, pas un compte — questions 2, 4, 5 (format exact, blocage vs. alerte, seuil de validation) ouvertes, sans effet bloquant sur le principe |
| d | **Régime fiscal / taux de TVA** | **Décidé cycle 6** : réel, 19,25 %, TTC, arrondi arithmétique sur le total |
| e | **Saisie a posteriori vs blocage anti-survente** | **Décidé cycle 6** (question 1) : jamais de blocage, écart consigné — questions 2-5 ouvertes |
| f | **Retours / casse** / remises / unités | **Décidé cycle 9**, volet retours et casse seulement : trois opérations distinctes, tracées — remises et conversion d'unités restent entièrement ouvertes |
| g | **Clôture de caisse** | **Décidé 2026-09-13** : une clôture par site — questions 2-6 (fond de caisse, horaire, Mobile Money, seuil d'écart, blocage) ouvertes, sans effet bloquant sur le principe |
| h | **Rôle caissier** | **Décidé 2026-09-13** : créé, fusionné avec le périmètre agent comptabilité (encaisse et saisit) — questions 3-4 (lecture des prix, cumul de rôles) et la cohérence avec `agent_comptabilite` restent à trancher à l'implémentation |
| i | **RPO / RTO / onduleur / mises à jour** | **Décidé 2026-09-13**, question 1 : RPO 1 heure — mécanisme déjà livré (cycle 21), reste à automatiser (planification) ; questions 2-6 (RTO, onduleur, Internet, qui restaure, fréquence de mise à jour) ouvertes |
| j | Volumétrie + reprise du stock + formation | Bloque C4, dimensionnement — non tranché |
| k | Cibles ergonomiques comme critères de recette | Bloque C9/C10, définition de « fini » — non tranché |
| l | **Propriété du code + livraison du dépôt** | **Décidé 2026-09-13**, question 1 : déjà résolu en pratique (dépôt sous compte propriétaire, accès admin détenu, livraison continue) — formalisé dans `OWNERSHIP.md`, audit de l'historique confirmé sans secret réel. Questions 2-4 (clause contractuelle, escrow, répartition des accès) relèvent d'un accord contractuel |

Restent à trancher : le reste du point **b** (vente à crédit) si le
crédit client doit un jour être réellement proposé aux clients, le point
**j** (volumétrie/reprise du stock, bloque le dimensionnement de C4), et
le point **k** (cibles ergonomiques comme critères de recette formels,
distinct des mesures déjà décrites dans `UX_BASELINE.md`). Les points
**a** et **f** sont tranchés dans leur volet qui bloquait C4 (cycle 9,
2026-09-13) ; leurs sous-questions restantes (réappro, identifiant
catalogue partagé, fréquence, remises, unités) n'ont plus d'effet
bloquant identifié à ce jour. Les points **c**, **g**, **h**, **i** et
**l** sont tranchés dans leur décision structurante (2026-09-13) : les
chantiers correspondants (C5 numéro facturier, C6 clôture de caisse, C3
rôle caissier, C12 automatisation des sauvegardes) peuvent démarrer —
chacun avec son propre diagnostic et son propre plan avant tout code,
comme le veut le processus.
