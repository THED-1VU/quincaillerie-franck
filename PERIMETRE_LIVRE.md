# Rétro-spécification fonctionnelle — Périmètre livré (reconstitué)

Le code source de l'application livrée (exécutables Windows du 7 septembre 2026) est
**inaccessible**. Ce document reconstitue ce que l'application **est censée offrir**, à
partir de quatre sources :

- `QuincaillerieFranck_Test/CAHIER DES CHARGES.docx` — spécification de référence (CDC) ;
- `QuincaillerieFranck_Test/GUIDE_TESTEUR_INSTALLATION.txt` — procédure de déploiement (GI) ;
- `QuincaillerieFranck_Test/GUIDE_TESTEUR_POSTES_ET_SCENARIO.docx` — scénario de test (GS) ;
- `dossier_diagnostic_quincaillerie_franck.docx` — dossier de recette rédigé par un tiers (DR) ;
- appoint : chemins de fichiers cités dans les commentaires de `creation_base_donnees.sql`.

**Niveau de confiance** de chaque élément :

- **Confirmé** : décrit par un scénario de test exécutable (GS ou DR).
- **Spécifié** : présent au CDC, non rejoué par un scénario.
- **Indice** : seulement suggéré par un commentaire SQL ou une mention de passage.

---

## 1. Modules cités dans le code (commentaires SQL)

Les commentaires de `creation_base_donnees.sql` nomment des fichiers, ce qui atteste
l'existence des composants correspondants :

| Chemin cité | Composant déduit |
|---|---|
| `ui/login_window.py` | Fenêtre de connexion |
| `ui/dialogue_parametres.py` | Dialogue « Paramètres » (identifiant / mot de passe de l'utilisateur courant) |
| `ui/formulaire_article.py` | Formulaire de création / modification d'article (gating du prix par rôle) |
| `modules/articles.py` (`modifier_article`) | Logique métier articles + écriture des historiques |
| `modules/paiement.py` | Sélection du mode de paiement / encaissement |
| `modules/rh.py` | Module RH (employés, absences, avances) |
| `modules/inventaire.py` | Module comptage d'inventaire + calcul d'écart |
| `api/` | API web mobile (FastAPI, signée avec `[api] secret_key`) |

**Architecture technique déclarée au CDC §5** : Python 3, PyQt6 (bureau Windows natif),
PostgreSQL local, psycopg v3, bcrypt, reportlab (reçus PDF + code-barres), openpyxl
(export Excel), FastAPI (supervision mobile optionnelle), PyInstaller (exécutables
autonomes), réseau local sans Internet.

**Deux exécutables livrés** :

- `QuincaillerieFranck.exe` — application principale, affichage adapté au rôle connecté ;
- `CreerCompteResponsable.exe` — outil console, crée le tout premier compte responsable
  (GI §4 : pose 3 questions — nom, identifiant, mot de passe).

---

## 2. Rôles et cloisonnement (CDC §2, GS §1, DR §3–5)

| Rôle | Portée | Ne doit **jamais** voir | Confiance |
|---|---|---|---|
| **Responsable** | Les deux sites, consolidé | — (accès total) | Confirmé |
| **Agent stock** | Un seul site | Aucun prix, aucun montant en FCFA nulle part | Confirmé |
| **Agent comptabilité** | Un seul site | Aucune quantité de stock disponible | Confirmé |

Jusqu'à 5 comptes actifs : 1 responsable + 2 agents stock (1/site) + 2 agents comptabilité
(1/site). Le cloisonnement doit s'appliquer **à l'écran ET dans les requêtes** (CDC §4.2) —
le DR §7.4 insiste : « masquer l'interface ne suffit pas ».

---

## 3. Écrans et fonctions reconstitués

### 3.1 Connexion (`ui/login_window.py`)

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Connexion identifiant + mot de passe | Hash bcrypt, jamais en clair | CDC §3.1, §4.2 | Spécifié |
| Verrouillage après N tentatives échouées | Réactivable par le responsable ; message compréhensible | CDC §3.1 ; DR Resp. A2 | Confirmé |
| Invitation à changer identifiant + mot de passe à la 1re connexion | Proposée **une seule fois** par compte (`doit_changer_mot_de_passe`) | CDC §3.1 ; GS §1 | Spécifié |
| Aucune donnée sensible après fermeture/réouverture | Pas de session persistée en clair | DR Resp. A4 | Confirmé (test) |
| Connexion < 30 s | Objectif ergonomique | DR §2, checklist UI | Spécifié (à mesurer) |

### 3.2 Paramètres utilisateur (`ui/dialogue_parametres.py`)

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Modifier son propre identifiant / mot de passe à tout moment | Tout rôle, confirmation + reconnexion OK | CDC §3.1 ; DR Resp. A3 | Confirmé |

### 3.3 Tableau de bord — Responsable

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Vue consolidée **ou** par site | Bascule deux sites / un site | CDC §3.7 ; GS §7 | Spécifié |
| Recettes du jour | Total du jour = somme des ventes payées | GS §7 ; DR Resp. E3 | Confirmé |
| Alertes de stock faible | Articles sous le seuil d'alerte | CDC §3.7 ; GS §7 | Confirmé (test) — cycle 10, `GET /tableau-bord/alertes-stock`, câblée sur l'écran |
| Accès rapide aux autres modules | Navigation | CDC §3.7 | Spécifié |
| Historique des comptages d'inventaire | Tous sites, filtre par période | CDC §3.6–3.7 ; GS §7 | Confirmé (test) — cycle 10, `GET /inventaire/historique-comptages`, pas encore d'écran dédié |

### 3.4 Tableau de bord — Agent stock

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Limité à son site et à son périmètre stock | Aucun montant FCFA | CDC §3.7 ; DR Stock A/B | Confirmé |
| Indicateur d'inventaire vert / rouge | Vert si tout correspond ; rouge + détail des écarts sinon | CDC §3.6 ; GS §6 ; DR Stock D3 | Confirmé (test) |

### 3.5 Tableau de bord — Agent comptabilité

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Limité à son site | Recettes / dépenses du jour de son site | CDC §3.7 ; DR Compta A1 | Confirmé |
| Quantités de stock jamais affichées | Y compris à la recherche d'article | DR Compta A2, B1 | Confirmé (test) |

### 3.6 Administration — comptes utilisateurs (responsable uniquement)

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Créer un compte | Rôle + site **obligatoires** ; identifiant unique | GS §3 ; DR Resp. B1–B2 | Confirmé |
| Désactiver / réactiver un compte | Désactivé ⇒ connexion refusée ; réactivé ⇒ connexion OK | CDC §3.8 ; DR Resp. B3 | Confirmé (test) |
| Onglet « Utilisateurs » | 4 comptes créés au scénario (magasin.stock, comptoir.stock, magasin.compta, comptoir.compta) | GS §3 | Confirmé |

### 3.7 Fournisseurs (responsable uniquement)

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Créer / gérer un fournisseur | Nom, contact, téléphone ; champs obligatoires signalés | CDC §3.8 ; DR Resp. B4 | Confirmé |

### 3.8 Articles et stock

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Fiche article | nom, catégorie, unité, prix achat, prix vente, quantité, fournisseur, site | CDC §3.2 ; DR Resp. C1 | Confirmé |
| Prix (achat + vente) et fournisseur **réservés au responsable** | Agent stock : formulaire **sans champ prix** ; modification prix impossible pour lui | CDC §3.2 ; GS §4 ; DR Stock C1, C3 | Confirmé (test) |
| Création / modification d'article par l'agent stock | nom, catégorie, unité — **jamais la quantité**, décision de ce cycle : le CDC l'évoque, mais l'accepter en modification de fiche contournerait l'audit des mouvements de stock (cycle 9) ; toute quantité passe par une réception, un transfert, une casse ou un retour | CDC §2 ; GS §4 ; DR Stock C1–C2 | Confirmé (test) — cycle 11, `PUT /articles/{id}`, écran `stock.html` |
| Seuil d'alerte **calculé automatiquement** | 20 % de la quantité reçue ; recalculé **uniquement** à une entrée de stock ; jamais à une sortie ni à une modification de fiche ; non saisissable | CDC §3.2, §4.2 ; DR Resp. C3–C4 | Confirmé (test) |
| Fixer le prix catalogue (responsable) | Onglet Articles → modifier ; scénario : 6 prix fixés | GS §4 | Confirmé |
| Mouvements de stock — entrée / sortie | **Motif obligatoire**, utilisateur + horodatage tracés | CDC §3.2 ; DR Resp. C3–C4, Stock C4 | Confirmé (test) |
| Sortie supérieure au stock refusée | Le stock ne devient jamais négatif | DR Stock C5 | Confirmé (test) |
| Historique prix + historique modifications **sur la fiche article** | Ancien / nouveau, auteur, date | CDC §3.2 ; DR Resp. C2 | Confirmé (test) — cycle 11 : ces deux tables existaient depuis le cycle 1 sans jamais avoir reçu une ligne, faute de route |

### 3.9 Enregistrer une vente (agent comptabilité + responsable)

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Recherche d'article | Rapide, sans afficher le stock à la compta | CDC §3.3 ; DR Compta B1 | Confirmé |
| Ajout au panier : quantité + **prix négocié** sur le **même écran** | Le prix catalogue n'est qu'indicatif | CDC §3.3 ; GS §5 ; DR Compta B2 | Confirmé (test) |
| Plusieurs articles par vente | Sous-totaux corrects et modifiables avant validation | GS §5 (clients 5, 9) ; DR Compta B3 | Confirmé |
| Calcul automatique sous-total / TVA / total | Règles de TVA et d'arrondi « cohérentes avec la configuration » | CDC §3.3 ; DR Compta B4 | Spécifié (config TVA non fournie) |
| Mode de paiement | espèces, Orange Money, MTN Mobile Money, crédit client, autre | CDC §3.3 ; GS §5 ; DR Compta B5 | Confirmé |
| Type de document | ticket simple **ou** facture détaillée à numéro attribué automatiquement | CDC §3.3 ; GS §5 | Confirmé |
| Validation ⇒ décrément de stock **atomique** + création **immédiate** de la recette | Protégé contre la survente concurrente | CDC §3.3 ; DR Compta B3, §6 | Confirmé (test) — *voir contradiction §5* |
| Impression directe du reçu ticket de caisse **avec code-barres**, sans étape intermédiaire | reportlab | CDC §3.3 ; GS §5 ; diag. §9 | Spécifié (imprimante à tester) |
| Anti double-clic sur « Valider » | Une seule vente créée | DR Compta D1 | Confirmé (test) |
| Fermeture pendant saisie non validée ⇒ aucune transaction partielle | Atomicité | DR Compta D2 | Confirmé (test) |
| Vente < 60 s après identification de l'article | Objectif ergonomique | GS ; DR Compta D3, §9 P0 | Spécifié (à mesurer) |
| **Refus de vente si stock insuffisant** | Scénario client n°8 : demande 50 fer à béton, 30 en stock ⇒ message clair, vente refusée | GS §5 note ; DR §6 | Confirmé (test) — *voir contradiction §5* |

### 3.10 Historique des ventes / annulation

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Liste des ventes, filtrable | Montant + mode de paiement visibles | GS §7 ; DR Resp. E | Confirmé |
| Annulation d'une vente — **responsable uniquement** | Restitue le stock + retire la recette associée | CDC §3.3 ; DR Resp. D4 | Confirmé (test) |
| Un agent ne peut pas annuler | Action refusée | DR §6 « Annulation contrôlée » | Confirmé (test) |
| Double annulation refusée | Pas de double restitution | CDC §3.3 ; DR Resp. D5, §6 | Confirmé (test) |

### 3.11 Comptabilité

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Saisie recette / dépense | Description libre, montant, site, date, auteur | CDC §3.4 ; DR Compta C1–C2 | Confirmé |
| Dépense de type salaire rattachée à un employé | Employé sélectionnable ; traçabilité de la paie | CDC §3.4 ; DR Compta C3 | Confirmé |
| Historique des transactions filtrable par site + période | | CDC §3.4 ; DR Compta C4 | Confirmé |

### 3.12 Ressources humaines (`modules/rh.py`, responsable uniquement)

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Fiche employé | nom, poste, téléphone, type de contrat (permanent / temporaire), salaire mensuel, site | CDC §3.5 ; DR Resp. B4 | Confirmé (test) |
| Suivi des absences et congés | | CDC §3.5 | Confirmé (test) |
| Suivi des avances sur salaire | Statut remboursé / non remboursé, bouton de remboursement | CDC §3.5 | Confirmé (test) |
| Module inaccessible aux agents | Menus absents ou accès refusé | DR Stock A3, Compta A3 | Confirmé (test) |

### 3.13 Comptage d'inventaire (`modules/inventaire.py`, agent stock)

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Comptage par article, matin **et** soir | Réalisé par l'agent stock du site | CDC §3.6 ; GS §6 | Confirmé |
| Comptage **à l'aveugle** | Quantité attendue jamais affichée pendant la saisie | CDC §3.6 ; DR Stock D1 | Confirmé (test) |
| Écart calculé **après** validation | compté − attendu | CDC §3.6 ; DR Stock D2 | Confirmé (test) |
| Indicateur tableau de bord agent : vert / rouge + détail | Rouge tant que l'écart n'est pas résorbé ; redevient vert au comptage suivant correct | CDC §3.6 ; GS §6 | Confirmé (test) |
| Historique des comptages réservé au responsable | L'agent n'y accède pas s'il est réservé | DR Stock D4 | Confirmé (test) |

### 3.14 Rapports et exports

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Export Excel (openpyxl) et PDF (reportlab) | Filtre de période | CDC §3.7 ; DR Resp. E2 | Confirmé (test) — cycle 10, `GET /rapports/ventes` (filtre de période) et `GET /rapports/articles` (instantané, sans période — un catalogue n'a pas d'historique) |
| **Gating du prix de vente selon le rôle de l'exportateur** | L'export d'un agent stock ne contient ni prix ni recette | CDC §3.7 ; DR Stock B3 | Confirmé (test) — cycle 10, absence physique des colonnes de prix relue dans le fichier produit (Excel et PDF), pas seulement filtrée à l'écriture |
| Rapport : total du jour = somme des ventes | Vérification croisée avec le tableau de bord | GS §7 | Confirmé (test) |

### 3.15 Impression (reportlab)

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Reçu PDF, disponible dès la validation de la vente | `GET /ventes/{id}/recu`, bouton « Imprimer le reçu » sur l'écran de vente, sans étape intermédiaire | CDC §3.3 ; GS §5 | Confirmé (test) — cycle 19. Document A4 (`reportlab`), pas un ticket de caisse thermique ; **aucun code-barres** (non demandé explicitement, non ajouté) |
| Facture détaillée numérotée | `numero_facture` attribué automatiquement | CDC §3.3 ; GS §5 (clients 2, 4, 10) | Spécifié — le point c (numérotation du facturier) reste non tranché ; le reçu identifie la vente par son numéro interne en attendant |
| Contenu du reçu | Nom + coordonnées de la boutique (si décidées — `boutique_telephone`/`numero_contribuable` restent `a_definir`, omis plutôt qu'inventés), n° de vente, date/heure, articles, quantités, prix, total TTC + détail TVA, mode de paiement ; réimprimable à tout moment (route en lecture, aucun effet de bord) ; une vente annulée porte une mention explicite (jamais un reçu d'apparence valide pour une vente qui ne l'est plus) | diag. §9 | Confirmé (test) — cycle 19, contenu relu dans le fichier PDF réellement produit, pas seulement le code HTTP |
| Impression physique sur une imprimante réelle | Le navigateur ouvre/télécharge le PDF ; l'envoi à une imprimante thermique dédiée n'est pas implémenté | DR §6 | Non vérifiable par l'agent (imprimante physique requise) |
| Comportement si imprimante indisponible | Vente reste traçable, erreur claire, réimpression autorisée | DR §6 | Non vérifiable (test à faire) — mais la réimpression elle-même (relire le PDF à tout moment) est déjà confirmée |

### 3.16 API web mobile (`api/`, FastAPI) — optionnelle au CDC

| Fonction | Détail | Source | Confiance |
|---|---|---|---|
| Supervision à distance par le responsable depuis un navigateur | Signée avec `[api] secret_key` ; sessions responsable | CDC §5, §4.1 ; `config.example.ini` | Indice |
| Endpoints métiers (proposés par le DR, non livrés) | `GET /dashboard`, `GET /stock/alerts`, `GET /sales/summary`, `POST /sales`, `POST /inventory/counts`, `GET /audit` | DR §7.3 | Proposition (non livré) |

> Le diagnostic automatisé conclut : **« Web API or mobile interface : Not found »**. Aucune
> interface mobile n'est présente dans le paquet livré / analysé. La priorité n°2 du
> propriétaire (suivi **et** saisie depuis un téléphone) n'est donc **pas couverte** par la
> version actuelle — voir addendum et comparaison d'architecture.

---

## 4. Tests transversaux attendus (DR §6)

| Test | Critère d'acceptation | Statut attendu |
|---|---|---|
| Survente concurrente (stock = 1, deux postes) | Une seule vente acceptée ; stock jamais négatif | Confirmé (à rejouer) |
| Annulation contrôlée | Agent refusé ; responsable autorisé ; 2e annulation refusée | Confirmé |
| Coupure réseau pendant validation | Message clair ; aucune double vente ; état final cohérent | À tester |
| Imprimante indisponible | Vente traçable ; erreur claire ; réimpression possible | À tester |
| Sauvegarde / restauration sur base séparée | Données + droits restaurés ; preuve conservée | Confirmé (test) — cycle 21, `db/outils/sauvegarder.ps1`/`restaurer.ps1` : comptes de lignes et droits par colonne identiques avant/après, sur une base séparée. Fréquence, conservation et RPO/RTO restent à trancher (point i). |
| Session inactive | Déconnexion / verrouillage conforme à la règle | À tester (règle à définir) |

---

## 5. Contradictions et zones grises du périmètre livré

1. **Décrément atomique anti-survente vs. saisie a posteriori.** Le CDC §3.3, le GS
   (client n°8) et le DR §6 imposent tous que l'application **refuse** une vente si le stock
   est insuffisant. Or le circuit réel (CDC §1.1, GS §2) fait saisir la vente **après**
   l'encaissement, à partir du facturier papier. Un logiciel ne peut pas refuser une vente
   déjà payée. → **Addendum, point e.**
2. **Rôle « caissier ».** Le CDC fait encaisser le **responsable en personne** au comptoir.
   Le DR mentionne un « caissier » sur PC (checklist UI : « utilisation clavier par le
   caissier »). Le schéma a `utilisateur_caisse_id` mais aucun rôle `caissier`. **Décidé
   2026-09-13** : rôle créé, fusionné avec le périmètre agent comptabilité (encaisse et
   saisit) — reste à implémenter. → **Addendum, point h.**
3. **Vente à crédit.** `mode_paiement = 'credit_client'` existe et le CDC crée une recette
   immédiate — pour de l'argent non encaissé. Aucune créance, aucun solde, aucun règlement
   ultérieur. → **Addendum, point b.**
4. **Transfert de stock entre sites.** Modèle à deux sites (magasin ⇄ comptoir), mais aucune
   opération de transfert prévue (CDC ni schéma). → **Addendum, point a.**
5. **TVA.** Le CDC calcule « la TVA » mais ne donne ni taux, ni régime, ni règle d'arrondi,
   ni cas d'exonération. `taux_tva` par défaut = `0`. → **Addendum, point d.**
6. **Numéro du facturier papier + vendeur.** Absents du schéma et des écrans. Sans eux, la
   saisie a posteriori par le comptable ne peut être reliée à un vendeur ni à une pièce
   papier. **Décidé 2026-09-13** : un facturier par site (préfixe MAG-/CPT-) — reste à
   implémenter. → **Addendum, point c.**
7. **Sauvegarde / restauration.** Exigée au CDC §4.3 et testée au DR §6. Le **mécanisme**
   existe désormais (`db/outils/sauvegarder.ps1`/`restaurer.ps1`, cycle 21, vérifié par
   exécution sur une base séparée). **Décidé 2026-09-13** : RPO 1 heure — reste à automatiser
   (planification). → **Addendum, point i.**
8. **Livrables manquants** (CDC §7) : code source (dépôt Git, livré), scripts de fabrication
   des exécutables (livrés, chantier C0), scripts de sauvegarde / restauration (livrés,
   chantier C12, cycle 21) — reste un **guide** utilisateur pour ces deux derniers (quand et
   comment les lancer sur un poste réel), pas seulement les scripts. → **Addendum, point l ;
   chantier C14.**

---

## 6. Synthèse pour le chantier C14

Périmètre **fonctionnel** bien couvert par la documentation : le CDC est détaillé et
cohérent, les deux guides testeur donnent un scénario rejouable de bout en bout (10 clients,
comptage matin/soir, vérifications responsable), le dossier de recette fournit des checklists
par rôle et des tests transversaux. C'est une base de reconstruction fonctionnelle **fiable**.

En revanche, les **livrables techniques** exigés par le CDC §7 sont largement absents :
pas de code source, pas de scripts de build, pas de scripts ni de guide de
sauvegarde/restauration. Les rétro-spécifications `MODELE_DONNEES.md` et `PERIMETRE_LIVRE.md`
n'existaient pas avant ce cycle.

**Score de départ C14 : 40 %** — documentation d'usage et de recette ≈ 80 % ; livrables de
livraison (source, build, sauvegarde) ≈ 15 %.
