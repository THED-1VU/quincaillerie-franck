# Réponse aux trois questions avant fusion de la PR #29 — 2026-09-18

Aucune fusion, aucun cycle démarré. Ce document répond aux trois questions
posées, avec sources précises pour chaque affirmation.

---

## 1. Questions non tranchées ayant réduit le périmètre de C5 (rapport d'écarts de prix)

Le chantier C5 du cycle 27 s'est limité au socle déjà décidé le 2026-09-13
(numéro de facturier + vendeur obligatoires, préfixe par site). Le rapport
« écarts de prix par vendeur » prévu par `ADDENDUM_CAHIER_DES_CHARGES.md`
(section c) n'a pas été construit parce que **deux** des cinq questions
d'origine posées au propriétaire restent sans réponse, et ce sont
précisément les deux qui déterminent la forme du rapport :

> **Question 3.** *« Les vendeurs sont-ils toujours des personnes ayant un
> compte dans l'application, ou faut-il une liste de vendeurs à part ? »*
>
> Tant que la réponse n'est pas connue, le rapport ne peut pas être complet
> par construction : `vendeur_id` référence aujourd'hui uniquement un
> compte utilisateur existant (choix fait pour livrer le socle sans
> attendre). Si dans les faits un extra ou un apprenti sans compte négocie
> parfois un prix, ses ventes resteraient absentes de tout rapport agrégé
> par vendeur — un rapport construit maintenant donnerait une fausse
> impression d'exhaustivité.

> **Question 5.** *« L'écart prix catalogue / prix négocié doit-il
> déclencher une validation du responsable au-delà d'un certain seuil
> (ex. remise > 15 %) ? »*
>
> C'est la question qui définit ce que le rapport doit signaler comme
> anormal. Sans seuil, le rapport ne peut que lister des écarts bruts, sans
> pouvoir dire lesquels méritent l'attention du responsable — ce qui video
> l'objectif anti-vol énoncé dans le contexte du point c (« un écart entre
> prix catalogue et prix facturé ne peut être rattaché à personne » devient
> « … ne peut être signalé comme suspect »).

Les trois autres questions de l'addendum (format exact du numéro au-delà
du préfixe — question 2 ; blocage vs alerte à la saisie — question 4 ;
et la question 1, déjà tranchée) ne bloquaient pas le socle livré et n'ont
pas motivé la réduction de périmètre.

**Pour débloquer le rapport**, il faut une réponse à ces deux questions,
formulée comme suit :

1. *Un vendeur qui négocie un prix a-t-il, dans les faits, toujours un
   compte de connexion dans l'application (responsable, agent stock ou
   agent comptabilité) ? Ou bien une personne sans compte (apprenti,
   extra, aide familiale) négocie-t-elle parfois un prix elle-même ?*
2. *À partir de quel écart entre le prix catalogue et le prix réellement
   facturé (montant, ou pourcentage de remise) une vente doit-elle être
   signalée comme méritant l'attention du responsable dans le rapport ?
   Existe-t-il déjà, dans les faits, une tolérance informelle appliquée
   par la boutique ?*

---

## 2. Tableau complet C0–C14

Deux colonnes de score : **« fusionné »** = ce qui est sur `main`
aujourd'hui (avant toute décision sur la PR #29) ; **« PR #29 »** = ce que
cette pull request, encore ouverte, ferait passer ces trois lignes à si
elle est fusionnée. Les 12 autres lignes ne sont pas touchées par la
PR #29.

| Code | Chantier | Score fusionné | PR #29 (en attente) | Preuve (résumé) |
|---|---|:-:|:-:|---|
| C0 | Infrastructure et dépôt | **55 %** | — | `.exe` PyInstaller autonome, testé depuis un dossier isolé du dépôt (cycle 4). Reste : CI, création du 1er compte responsable, mode kiosque. |
| C1 | Base de données et intégrité | **80 %** | — | 9 migrations + inverses, 100 contrôles SQL, 0 échec (`db/tests/DERNIER_RESULTAT.md`, cycle 2). |
| C2 | Authentification et comptes | **65 %** | — | Connexion via fonction `SECURITY DEFINER`, verrouillage, 36/36 tests (cycle 3). |
| C3 | Habilitations et cloisonnement | **60 %** | **68 %** | Fusionné : cloisonnement SQL/RLS prouvé (`test_cloisonnement_site.py`, cycle 3). PR #29 : diagnostic révèle que le rôle caissier (point h) existe déjà via `agent_comptabilite` — aucun code, correction d'une inexactitude du tableau (RH déjà testé par une route). |
| C4 | Articles et stock | **72 %** | — | 6 opérations `SECURITY DEFINER`, 104/104 tests, aucun prix ne fuit à l'agent stock (cycles 9/11/13). |
| C5 | Ventes et facturation | **62 %** | **72 %** | Fusionné : TVA/anti-survente/annulation/reçu PDF, 24/24 tests dédiés (cycles 6/17/19). PR #29 : numéro de facturier + vendeur obligatoires (point c, socle réduit — voir §1 ci-dessus), 33/33 tests dédiés à C5. |
| C6 | Comptabilité et RH | **85 %** | — | Clôture de caisse immuable par site (migration 019), 163/163 pytest, 24/24 Playwright dédiés (cycle 25, fusionné). |
| C7 | Inventaire et écarts | **50 %** | — | Comptage à l'aveugle, quantité attendue jamais exposée, 11/11 tests + 17/17 Playwright (cycle 7). |
| C8 | Tableaux de bord et rapports | **70 %** | — | Exports Excel/PDF cloisonnés par rôle et par site, bascule vue consolidée/site (cycles 10/12/14/23). |
| C9 | Ergonomie et UI | **58 %** | — | 7 des 11 constats UX corrigés/confirmés non défectueux (cycle 24, fusionné). **2ᵉ campagne humaine toujours nécessaire** pour l'objectif chronométré principal. |
| C10 | Mobile et API web | **55 %** | — | 3 des 5 constats mobiles corrigés (débordement, police, coupure réseau — cycle 24, fusionné). UX-5 toujours ouvert. |
| C11 | Sécurité applicative | **68 %** | — | Révocation de session, en-têtes de sécurité, 144/144 tests (cycle 22). |
| C12 | Sauvegarde et exploitation | **80 %** | — | Planification réelle déclenchée, fichier d'état + journal Windows, restauration depuis la copie hors-site (cycle 26, fusionné). |
| C13 | Tests automatisés et qualité | **55 %** | **60 %** | Fusionné : 3 couches de tests (pytest/SQL/Playwright) unifiées par `verifier_tout.sh` (cycle 20). PR #29 : `psql` cherché sur le `PATH` avant le chemin Windows en dur — un des deux points bloquant une CI Linux est corrigé. |
| C14 | Documentation et livrables | **40 %** | — | CDC, guides testeur, dossier de recette. Manque le code source et les scripts de fabrication dans les livrables (CDC §7). |

**Moyenne indicative** : **≈ 64 %** en l'état fusionné actuel de `main` ;
**≈ 65 %** si la PR #29 est fusionnée telle quelle.

---

## 3. État des constats consignés mais non traités

### a) Les 11 constats UX (`UX_BASELINE.md` §4 bis)

| Constat | État | Détail |
|---|---|---|
| UX-0 (méthodologie) | **OUVERT** | Désaccord entre « pire des 3 essais » (protocole) et « 3ᵉ essai pratiqué » (lecture du testeur) — décision du propriétaire requise, aucun code n'y répond. |
| UX-1 (panier ≤ 2 actions) | **RÉGLÉ** (cycle 24, fusionné) | Un nombre en tête de la recherche fixe la quantité dès l'ajout. |
| UX-2 (vente clavier seul) | **RÉGLÉ** (cycle 24, fusionné) | Raccourci `F3` pour négocier le prix sans souris. |
| UX-3 (débordement tableau de bord) | **RÉGLÉ** (cycle 24, fusionné) | Cause CSS identifiée et corrigée (`minmax(0, ...)`) — cause la plus plausible, honnêtement signalée comme non formellement exclusive (téléphone d'origine jamais identifié précisément). |
| UX-4 (chiffres illisibles) | **RÉGLÉ** (cycle 24, fusionné) | Taille de police minimale garantie, mesurée ≥ 16px. |
| UX-5 (recette lente au téléphone) | **OUVERT** | Hors du plan validé pour la piste UX, non traité. |
| UX-6 (clavier numérique) | **Non défectueux** | Déjà correct à l'inspection (`type="number"` + `inputmode="numeric"` déjà posés) — pas un vrai défaut. |
| UX-7 (coupure réseau silencieuse, sévère) | **RÉGLÉ** (cycle 24, fusionné) | `AbortController` 20 s, message français, formulaire réutilisable sans recharger. |
| UX-8 (annuler une ligne introuvable) | **OUVERT** | Hors du plan validé pour la piste UX, non traité. |
| UX-9 (prix gris mal compris) | **RÉGLÉ** (cycle 24, fusionné) | Message explicite « indicatif », « PAS le prix qui sera facturé ». |
| UX-10 (comptage définitif non signalé) | **RÉGLÉ** (cycle 24, fusionné) | Avertissement toujours visible, sans dialogue bloquant. |

**Bilan** : 7 corrigés et vérifiés par exécution + 1 confirmé non défectueux
= 8 clos ; **3 toujours ouverts (UX-0, UX-5, UX-8)**, dont un (UX-0) est une
pure décision, sans code associé.

### b) Erreur PostgreSQL « error code 487 » (shared memory)

**Toujours OUVERTE — jamais corrigée à la racine, seulement récupérée à
chaque occurrence.**

Correction de chiffre : le compte de « 504 occurrences » cité provient
d'un état antérieur de la session, que je ne peux plus retracer avec
certitude. **Vérifié à l'instant** dans `_pgdev/server.log` (log continu
du 2026-09-12 au 2026-09-18, 10 179 lignes) : **15 occurrences** de
`could not reserve shared memory region ... error code 487`, la plus
récente ce matin à 04:36:52. C'est une fragilité connue de PostgreSQL sous
Windows (collision d'espace d'adressage sous pression mémoire), pas un bug
de ce projet. Chaque occurrence a été suivie d'une reprise automatique par
rejeu du WAL au redémarrage (`pg_ctl start` via `db/outils/demarrer_pg.ps1`),
sans perte de données constatée à chaque vérification. Aucun code de ce
dépôt ne traite la cause elle-même : c'est un risque opérationnel permanent
du poste de développement Windows actuel, pas une chose que ce projet peut
« réparer » — seulement surveiller et récupérer proprement, ce qui a été
fait à chaque fois qu'observé.

### c) Tâche planifiée de sauvegarde exigeant une session Windows ouverte

**Toujours OUVERTE.** Documenté explicitement dans
`db/outils/GUIDE_SAUVEGARDE_RESTAURATION.md`, section 5 : la tâche
planifiée (`planifier_sauvegarde.ps1`) est enregistrée avec
`-LogonType Interactive` (aucun mot de passe requis, aucun droit
administrateur nécessaire) — elle ne se déclenche que si une session
Windows de l'utilisateur concerné est ouverte. Pour un fonctionnement 24/7
réel sur le poste serveur, il faudrait soit laisser une session ouverte en
permanence, soit qu'un administrateur crée un compte de service dédié et
ré-enregistre la tâche en `-LogonType Password`/`ServiceAccount` (mot de
passe réel, jamais dans ce dépôt). Non traité par la PR #29 (hors de son
périmètre, qui ne touchait pas C12 lui-même).

### d) Copie hors-site non chiffrée

**Toujours OUVERTE.** Documenté au même endroit (section 5) : l'addendum
propose le chiffrement de la copie hors-site, mais aucune décision
(algorithme, gestion de la clé) n'a été prise par le propriétaire — un
dossier réseau ou une clé USB non chiffrés restent lisibles par quiconque
y a un accès physique. Non traité par la PR #29.

### Pour mémoire — un point de cette liste a été traité entre-temps

Le **voyant de tableau de bord non câblé visuellement** (aussi listé dans
le même « Ce que ce cycle NE couvre PAS » du guide de sauvegarde) **est
traité par la PR #29**, actuellement en attente : lien vers
`cloture-caisse.html` et carte « Dernière sauvegarde » avec ses trois états
réels. Ce point sera donc réglé si, et seulement si, la PR #29 est
fusionnée.
