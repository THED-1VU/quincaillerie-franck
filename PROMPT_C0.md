# PROMPT C0 (révisé) — Cadrage de reconstruction, Quincaillerie Franck

À coller tel quel dans une session Claude Code neuve. Ce prompt est autonome : il ne suppose
aucun accès à une conversation antérieure.

---

```
CONTEXTE ÉTABLI (ne pas remettre en question, c'est le résultat d'un audit déjà mené)

Une application de gestion a été développée pour les Ets Quincaillerie Franck, quincaillerie
située à Batouri (région de l'Est, Cameroun). Elle a été livrée UNIQUEMENT sous forme
d'exécutables Windows. Le code source n'existe nulle part sur cette machine : recherche
exhaustive menée sur H:\, C:\, E:\, le profil utilisateur, les corbeilles de tous les
disques, et les artefacts de compilation. Résultat : aucun fichier .py, aucun .spec, aucun
dossier build. Le Python 3.14.6 installé localement ne contient aucune des bibliothèques du
projet (ni PyQt6, ni psycopg, ni bcrypt, ni PyInstaller), ce qui confirme que la compilation
a eu lieu dans un environnement extérieur. Les exécutables datent du 7 septembre 2026.
N'entreprends AUCUNE nouvelle recherche du code source : c'est fait, et c'est négatif.

CE QUI EXISTE RÉELLEMENT, à lire intégralement avant toute chose :
  H:\2026\PROFESSIONNEL\THED CONNECT\QuincaillerieFranck_Test\QuincaillerieFranck_Test\
    - creation_base_donnees.sql          <- le modèle de données réel, pièce maîtresse
    - config.example.ini                 <- structure de configuration attendue
    - GUIDE_TESTEUR_INSTALLATION.txt     <- procédure de déploiement réelle
    - GUIDE_TESTEUR_POSTES_ET_SCENARIO.docx <- scénarios de test, donc périmètre fonctionnel
    - CAHIER DES CHARGES.docx            <- spécification de référence
    - QuincaillerieFranck.exe            <- application fonctionnelle (référence vivante)
    - CreerCompteResponsable.exe         <- outil de création du premier compte
  H:\2026\PROFESSIONNEL\THED CONNECT\QuincaillerieFranck_Test\
    - dossier_diagnostic_quincaillerie_franck.docx <- dossier de recette rédigé par un tiers
    - diagnostic estimatif1.txt

CONTEXTE MÉTIER (issu du cahier des charges)
Deux sites physiques : un magasin de stock et un comptoir de vente. Trois rôles :
- Responsable : les deux sites, fixe les prix, gère fournisseurs/RH/comptes, encaisse au
  comptoir, seul habilité à annuler une vente.
- Agent stock : un seul site, crée et modifie les articles (nom, quantité, unité), ne voit
  jamais un prix ni un montant en FCFA, réalise le comptage matin et soir.
- Agent comptabilité : un seul site, enregistre a posteriori les ventes déjà payées d'après
  un facturier papier en saisissant le prix réellement négocié, saisit recettes et dépenses,
  ne voit jamais les quantités en stock.
Le seuil d'alerte est calculé automatiquement (20 % de la quantité reçue) et recalculé
uniquement lors d'une entrée de stock. Le comptage d'inventaire est « à l'aveugle » : la
quantité attendue est masquée pendant la saisie. Fonctionnement en réseau local, PostgreSQL
sur un poste serveur, jusqu'à 5 postes.

PRIORITÉS DU PROPRIÉTAIRE, DANS CET ORDRE
1. Le rendu : ergonomie, responsivité, expérience utilisateur.
2. L'usage téléphone : les responsables doivent SUIVRE et aussi SAISIR des données depuis un
   mobile, où qu'ils soient. Ce n'est pas une option secondaire.
3. La fiabilité métier : droits par rôle, intégrité du stock, traçabilité anti-vol.

TA MISSION — 5 livrables, dans cet ordre, sans écrire une ligne de code applicatif

1. RETRO-SPÉCIFICATION DU MODÈLE DE DONNÉES
   Lis creation_base_donnees.sql en entier et produis `MODELE_DONNEES.md` : liste des tables,
   colonnes, types, clés primaires et étrangères, contraintes CHECK et UNIQUE, index,
   séquences, déclencheurs, tables d'audit. Puis une évaluation critique : ce qui est
   correctement modélisé, ce qui manque, ce qui est risqué (montants en FLOAT plutôt qu'en
   NUMERIC, absence de contrainte de quantité positive, absence de verrou anti-survente,
   audit incomplet). Ce schéma est le point de départ de la reconstruction : on le corrige,
   on ne le jette pas.

2. RETRO-SPÉCIFICATION FONCTIONNELLE
   Lis les deux guides testeur et le dossier de recette. Produis `PERIMETRE_LIVRE.md` : la
   liste des écrans et fonctions que l'application livrée est censée offrir, déduite des
   scénarios de test. C'est la meilleure approximation disponible de ce qui existe, puisque
   le code est inaccessible.

3. DÉPÔT GIT
   Crée le dépôt à H:\2026\PROFESSIONNEL\THED CONNECT\QuincaillerieFranck_Test (git init si
   absent), avec un .gitignore excluant config.ini, *.exe, build/, dist/, __pycache__/,
   *.log, et toute sauvegarde .sql contenant des données. Crée un dépôt GitHub PRIVÉ
   `quincaillerie-franck` sous le compte THED-1VU et pousse la branche main. Ne committe
   jamais un mot de passe ni un fichier de configuration réel. Les deux .exe restent sur le
   disque mais hors du dépôt : ils servent de référence, pas de livrable versionné.

4. ADDENDUM AU CAHIER DES CHARGES
   Écris `ADDENDUM_CAHIER_DES_CHARGES.md`. Pour chaque point : la règle proposée, les cas
   limites, et la question exacte à poser au propriétaire quand une décision métier est
   nécessaire. Les points à traiter :
   a) Transfert de stock entre le magasin et le comptoir : opération quotidienne absente du
      cahier des charges alors que le modèle à deux sites l'exige.
   b) Vente à crédit : le cahier des charges fait créer une recette immédiate alors qu'aucun
      argent n'est entré. Il faut une créance client, un solde et un règlement ultérieur.
   c) Numéro du facturier papier, saisi et unique sur chaque vente, plus identification du
      vendeur ayant négocié le prix. Sans ces deux champs, l'objectif anti-vol est
      inatteignable puisque la saisie est faite après coup par le comptable.
   d) Régime fiscal : question à poser au propriétaire — la boutique est-elle assujettie à la
      TVA au régime du réel, ou relève-t-elle de l'impôt libératoire ou du régime simplifié ?
      Le taux doit être une valeur de configuration et l'application doit pouvoir n'appliquer
      aucune TVA.
   e) Contradiction à arbitrer : le cahier des charges impose un décrément atomique
      anti-survente, alors que les ventes sont saisies APRÈS l'encaissement réel. Un logiciel
      ne peut pas refuser une vente déjà encaissée. Propose une règle explicite — autoriser la
      saisie avec alerte d'écart et régularisation d'inventaire plutôt que blocage — et dis ce
      que devient alors le test de concurrence.
   f) Retours, casse, avaries, remises ; conversion d'unités (sac/kg, barre/mètre, vrac).
   g) Clôture de caisse quotidienne et rapprochement entre espèces comptées et recettes
      saisies.
   h) Rôle « caissier » : le cahier des charges ne le prévoit pas et fait encaisser le
      responsable en personne, alors que l'usage décrit un caissier dédié sur PC. À clarifier.
   i) Exploitation : onduleur obligatoire sur le poste serveur (coupures de courant fréquentes,
      risque de corruption PostgreSQL), perte de données maximale acceptable, délai de reprise,
      procédure de mise à jour des 5 postes.
   j) Reprise de l'existant : chargement du stock initial depuis le cahier papier, volumétrie
      attendue (nombre d'articles, de ventes par jour), et plan de formation des utilisateurs.
   k) Critères ergonomiques mesurables : vente complète en moins de 60 secondes, connexion en
      moins de 30 secondes, aucun débordement en 1366x768, messages d'erreur en français
      placés près du champ concerné, lisibilité mobile à 360, 390 et 768 px.
   l) Propriété du code source et obligation de livraison du dépôt, à intégrer explicitement
      au cahier des charges pour que la situation actuelle ne se reproduise pas.

5. CYCLE DE FINALISATION
   Crée `.agents/skills/finalisation-loop/SKILL.md` décrivant le cycle en 5 phases utilisé sur
   ce projet, puis initialise `RAPPORT AVANCEMENT/loop-state.md` avec le score de départ de
   chacun des 15 chantiers du référentiel fixe.

   Phase 1 Diagnostic/test : mesurer l'état réel par exécution, jamais par lecture seule.
   Phase 2 Objectif : choisir UN seul chantier, écrire un critère de sortie vérifiable.
   Phase 3 Action : implémenter sur une branche dédiée `cycle-N-<chantier>`.
   Phase 4 Vérification : prouver par exécution réelle. Une correction non exécutée est
           réputée non faite.
   Phase 5 Mémoire : mettre à jour loop-state.md, committer, ouvrir la PR, fusionner après
           vérification.

   RÉFÉRENTIEL FIXE — NE JAMAIS RENUMÉROTER :
   C0 Infrastructure et dépôt | C1 Base de données et intégrité | C2 Authentification et
   comptes | C3 Habilitations et cloisonnement des rôles | C4 Articles et stock | C5 Ventes
   et facturation | C6 Comptabilité et RH | C7 Inventaire et écarts | C8 Tableaux de bord et
   rapports | C9 Ergonomie et UI (priorité 1) | C10 Mobile et API web (priorité 1) |
   C11 Sécurité applicative | C12 Sauvegarde et exploitation | C13 Tests automatisés et
   qualité | C14 Documentation et livrables

   Tous les chantiers partent de 0 % sauf C1 et C14, que tu évalues sur pièces à partir du
   SQL et des guides existants.

RÈGLES PERMANENTES
- N'écris aucun code applicatif dans ce cycle : c'est un cycle de cadrage.
- Ne devine jamais une règle métier manquante : pose la question dans l'addendum.
- L'architecture technique cible (application de bureau plus interface web, ou application
  web unique servie en local et utilisée à la fois sur le PC de caisse et sur téléphone)
  n'est PAS encore tranchée. Ne la présuppose pas. Termine ton rapport par une comparaison
  argumentée des deux options, au regard des trois priorités ci-dessus, en traitant
  explicitement la question de l'impression du ticket de caisse.
- Tout en français.

Termine par un résumé court : qualité du modèle de données existant, périmètre fonctionnel
reconstitué, et les trois décisions que le propriétaire doit trancher en priorité.
```
