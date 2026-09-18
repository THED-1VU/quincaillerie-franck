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

---

## a) Transfert de stock entre le magasin et le comptoir

> **Décidé (cycle 9, 2026-09-13), questions 2 et 3.** Opération **unique et
> atomique** produisant une sortie du site d'origine et une entrée au site
> de destination, même horodatage, même auteur, motif obligatoire —
> **jamais** d'état intermédiaire « en transit ». Ne recalcule **pas** le
> seuil d'alerte (ce n'est pas une réception fournisseur). Déclenché par le
> responsable, ou par l'agent stock **du site d'origine seulement**.
> Appliqué dans `db/migrations/014_articles_stock_transferts_retours.sql`
> (`transferer_stock`). Question 4 **non retranchée** : un transfert vise
> deux articles déjà existants, un par site — aucune fiche miroir n'est
> créée automatiquement côté destination ; si elle n'existe pas encore, le
> transfert est refusé plutôt que d'inventer sa création. Questions 1 et 5
> (réapprovisionnement exclusivement interne ? fréquence/volume) restent
> sans réponse, sans effet sur ce qui est construit.

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

> **Statu quo maintenu explicitement (cycle 6, 2026-09-12).** Le propriétaire
> n'a pas encore répondu aux 6 questions ci-dessous. Plutôt que d'attendre
> pour livrer le reste du chantier C5, `mode_paiement = 'credit_client'` est
> **désactivé côté serveur** (`server/app/routes/ventes.py` le refuse avec un
> message explicite) — aucune table Client, aucune créance créée. Ce n'est
> pas une décision sur le FOND du point b, seulement la confirmation que rien
> n'est inventé à sa place : dès que le propriétaire répond, ce statu quo est
> le premier à lever.

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
> **Question 3 toujours ouverte, réponse attendue du propriétaire :** un
> vendeur qui négocie un prix a-t-il, dans les faits, toujours un compte
> de connexion dans l'application (responsable, agent stock ou agent
> comptabilité) ? Ou une personne sans compte (apprenti, extra, aide
> familiale) négocie-t-elle parfois un prix elle-même ? Aucun code n'en
> dépend tant que la réponse n'est pas connue.

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
3. Les vendeurs sont-ils **toujours** des personnes ayant un compte dans l'application, ou
   faut-il une liste de vendeurs à part ?
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
1. Combien d'**articles** environ par site ? Combien de **ventes par jour** en moyenne et un
   jour de pointe ? Combien d'**employés**, de **fournisseurs** ?
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
| c | **Numéro facturier + vendeur obligatoires** | **Décidé 2026-09-13** : un facturier par site (préfixe MAG-/CPT-) — questions 2-5 (format exact, vendeurs sans compte, blocage vs. alerte, seuil de validation) ouvertes, sans effet bloquant sur le principe |
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
