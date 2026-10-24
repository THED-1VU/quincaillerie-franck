# C12 — Sauvegarde et reprise : audit, preuves par doubles, procédure de
# sécurité et fiche second PC (Lot B, 2026-10-23)

Commande du propriétaire (opération 100 % / Lot B) : « Audite la chaîne
complète de sauvegarde […]. La mise en quarantaine de sauvegarder.ps1 par
Kaspersky est un blocage de sécurité. Ne restaure pas le fichier, ne
l'exécute pas, ne crée aucune exclusion et ne désactive aucune protection
sans mon autorisation explicite. Tu peux utiliser des doubles de test sûrs
et une base isolée pour vérifier les mécanismes indépendants du script.
Prépare une procédure de contrôle de sécurité et une fiche de recette sur
second PC. Ne déclare pas C12 à 100 % global tant que les tests physiques
et la résolution sécurisée du blocage ne sont pas prouvés. »

## 1. Conformité aux contraintes (traçabilité)

* `sauvegarder.ps1` n'a été **ni restauré, ni exécuté, ni commité, ni
  soustrait à la quarantaine**. Toute sa lecture s'est faite par
  `git show HEAD:db/outils/sauvegarder.ps1` (le blob du dépôt, jamais le
  fichier disque).
* Aucune exclusion antivirus n'a été créée, aucune protection désactivée.
* Tous les tests ci-dessous utilisent des **doubles sûrs** et des bases
  isolées (`quincaillerie_probe`, `quincaillerie_c12`), jamais une base de
  production ni celle de Codex (`quincaillerie_test`).

## 2. Chaîne auditée et preuves d'exécution (2026-10-23)

### 2.1 Mécanismes cryptographiques — double indépendant

`db/tests/c12/double_chiffrement.ps1` (nouveau, Lot B) ré-implemente le
**format contractuel** documenté dans les en-têtes de `sauvegarder.ps1`
(`Chiffrer-Fichier`) et `restaurer.ps1` (`Dechiffrer-Fichier`) :

```
[16 sel][16 IV][AES-256-CBC][32 HMAC-SHA256]
PBKDF2-SHA256 100 000 itérations, 64 octets dérivés
(32 AES + 32 HMAC, clés DISTINCTES), HMAC avant déchiffrement,
comparaison à temps constant manuelle (.NET 4.x).
```

L'intérêt du double : il prouve le contrat entre DEUX codes indépendants,
pas seulement qu'un script relit ce qu'il vient d'écrire.

**Autotest : 11/11 contrôles passés** (exécution réelle, PowerShell 5.1) :

| # | Contrôle | Verdict |
|---|---|---|
| T1 | chiffrement produit le `.enc`, **supprime le clair** | OK |
| T2 | format exact (16+16+multiple de 16+32, sel/IV non nuls) | OK |
| T3 | aller-retour octet à octet (SHA-256 identique) | OK |
| T4 | phrase fausse → refus **par l'HMAC**, pas le padding AES | OK |
| T5 | texte chiffré corrompu (octet 40) → refus | OK |
| T6 | empreinte corrompue (dernier octet) → refus | OK |
| T7 | troncature (50 octets) → refus « trop court » | OK |
| T8 | fichier vide → 80 octets chiffrés, relu vide | OK |
| T9 | clés AES/HMAC **distinctes** dans la dérivation | OK |
| T10 | fichier sans `.enc` (héritage clair d'avant cycle 28) → rendu tel quel | OK |
| T11 | `.enc` sans phrase → refus (aucune récupération sans phrase) | OK |

Constat de sécurité utile : Kaspersky **n'a pas signalé** ce double
(mêmes primitives .NET, même suppression de fichier) — conforte
l'hypothèse heuristique du faux positif (donnée pour la procédure, §3).

### 2.2 Restauration réelle — le VRAI restaurer.ps1 sur base isolée

Chaîne exécutée intégralement (aucun script de production touché) :
`pg_dump -Fc` de `quincaillerie_probe` → chiffrement par le double →
restauration par le **vrai** `db/outils/restaurer.ps1` vers la base
neuve `quincaillerie_c12` :

* refus sans phrase sur un `.enc` (exit 1) — ✓ conforme ;
* **compatibilité croisée prouvée** : le vrai `restaurer.ps1` déchiffre
  sans erreur un fichier produit par le double (mêmes format/dérivation) ;
* refus de restaurer sur une base existante sans `-Forcer` (exit 1) — ✓ ;
* restauration complète : **38 tables**, rejeu des rôles (erreurs
  « already exists » attendues), exit 0 ;
* comparaison source ↔ restaurée : **tables 38 = 38, privilèges colonnes
  qf_responsable 556 = 556, politiques RLS 13 = 13, articles 5 = 5,
  stocks 5 = 5, utilisateurs 5 = 5, paramètres 19 = 19, migrations 52** ;
* données vivantes : Ciment 6 500 FCFA, 5 comptes bcrypt `$2a$`,
  extensions (pgcrypto, pg_trgm) intactes ;
* **l'application démarre sur la base restaurée** (uvicorn port 8030) :
  `/sante` OK, connexion `resp` OK, lecture articles OK, et le
  **cloisonnement des prix est intact** — `resp` voit `prix_vente`, l'agent
  stock ne voit AUCUN prix (privilèges colonne restitués) ;
* aucun fichier clair résiduel après le chemin de succès.

### 2.3 Défaut trouvé par exécution et corrigé : clairs laissés sur un
chemin de refus

En rejouant le refus « base cible existe déjà sans `-Forcer` », le dump
**déchiffré restait sur le disque** : le `throw` de refus court-circuitait
`Nettoyer-FichiersClairs`, contredisant l'invariant « jamais de clair
au-delà de cette restauration » (journaux, en-têtes du script).

**Correctif livré** (branche `operation-100-lot-b`, `db/outils/restaurer.ps1`) :
`Nettoyer-FichiersClairs` défini AVANT tout déchiffrement, appelé avant
chaque `throw` de refus (base existante, rôles introuvables) et dans un
`catch` autour des déchiffrements. **Re-prouvé par exécution** : les deux
chemins de refus ne laissent plus AUCUN clair ; le chemin de succès reste
vert (38 tables, exit 0). Gravité P3 (contexte : opérateur local qui se
trompe de base cible), mais l'invariant est désormais total.

## 3. Procédure de contrôle de sécurité — faux positif Kaspersky
(PDM:Trojan.Win32.Generic sur `db\outils\sauvegarder.ps1`)

**À exécuter par le propriétaire seul** (droits admin, poste cible). Le
cycle 74 a arbitré cette action « GO » ; cette procédure en est le mode
opératoire détaillé. Aucune étape n'aveugle l'antivirus au-delà du fichier
concerné.

Empreintes de référence (SHA-256, consignées 2026-10-23) :

| Fichier | SHA-256 |
|---|---|
| `sauvegarder.ps1` — source officielle (blob git `main`) | `3684aae048cdd66afeeda1a9bfe11855023add940bf385b22a3fe5f4759607a2` |
| `restaurer.ps1` — version corrigée Lot B (branche) | `45dd314e51808b89ad4671cd2241f61d7c69cb473e742275d7e651e99a45bfa7` |
| `double_chiffrement.ps1` — nouveau double de test | `ddffa5a738824aaef4f5ece8a9642a2146fdf312a2dc4ab05c3b009a444e7dd5` |

| Étape | Action | Critère de contrôle |
|---|---|---|
| S1 | Vérifier le fond : pourquoi ce fichier déclenche l'heuristique | Le script combine chiffrement .NET + suppression de fichier clair + écriture Event Log — motifs PDM génériques ; AUCUNE charge malveillante ; source = dépôt git privé du projet, relu ligne à ligne au cycle 28 et par le Lot B |
| S2 | Restaurer le fichier DEPUIS LE DÉPÔT (`git checkout main -- db/outils/sauvegarder.ps1` ou extraction de l'archive de livraison) — jamais depuis un média inconnu | `Get-FileHash db\outils\sauvegarder.ps1` = empreinte ci-dessus (nuance : si l'outil convertit les fins de ligne, comparer au contenu du blob ; la référence est le dépôt) |
| S3 | Soumettre le fichier au contrôle Kaspersky AVANT toute exclusion : menu « Résoudre » → « Détails » → envoyer pour analyse (« Envoyer à Kaspersky ») avec motif « outil de sauvegarde interne, faux positif présumé » | Le rapport d'analyse est archivé avec ce document ; si Kaspersky confirme une menace réelle : STOP, alerte immédiate, aucune exclusion |
| S4 | Décision SIGNÉE du propriétaire : exclusion ciblée du SEUL fichier `db\outils\sauvegarder.ps1` (jamais le dossier, jamais `*.ps1`, jamais désactivation de la protection temps réel) | Capture d'écran de l'exclusion (portée exacte visible) + date + signature sur PV |
| S5 | Contrôle post-restauration : exécuter une sauvegarde d'essai sur la base de test (jamais la production avant validation) | `dernier_etat_sauvegarde.json` à jour, fichier `.enc` daté, AUCUNE nouvelle quarantaine ; l'alerte d'échec C12-02 (cycle 75-F) reste visible sur le tableau de bord en cas d'échec |
| S6 | Surveillance continue : à chaque mise à jour du script (future PR), recalculer l'empreinte, re-vérifier S2–S5 | Toute divergence d'empreinte = fichier altéré → refuser, ré-extraire depuis le dépôt |

**Interdits permanents** (valables pour tout intervenant) : aucune
restauration du fichier depuis un média autre que le dépôt officiel ;
aucune exclusion de portée supérieure au fichier ; aucune désactivation,
même temporaire, de la protection ; jamais d'exécution tant que l'empreinte
n'est pas vérifiée.

## 4. Fiche de recette — restauration sur second PC (C12-01, RTO 2 h)

Dérivée de la fiche R3 du cycle 73 (`CYCLE_73_FICHES_RECETTE.md`),
enrichie des preuves du Lot B. **La version corrigée de `restaurer.ps1`
(empreinte §3) est celle à utiliser** : elle seule garantit l'invariant
« aucun clair résiduel » sur tous les chemins.

**Pré-requis sur B :** PostgreSQL portable livré (`_pgdev\pgsql\`), fichier
`restaurer.ps1` (empreinte vérifiée S2), sauvegarde `.enc` produite sur A
par le vrai `sauvegarder.ps1` **après** la procédure §3, phrase secrète,
exclusions antivirus posées selon §3 (S4).

| # | Étape | Critère de réussite | Fait | Date/visas |
|---|---|---|---|---|
| P1 | Copier la sauvegarde `.enc` de A vers B (clé USB) | taille identique octet à octet (`Get-FileHash` sur A et B) | ☐ | |
| P2 | Lancer sur B : `restaurer.ps1 -FichierBase <fichier>.enc -FichierRoles <fichier>_roles.sql.enc -PhraseChiffrement <phrase> -NomBaseCible <base_neuve>` | « Restauration terminée : N table(s) », aucune table manquante vs A, **aucun fichier clair resté sur le disque** (nouveau contrôle Lot B) | ☐ | |
| P3 | Tentative de restauration sur une base EXISTANTE sans `-Forcer` | refus (exit 1) et **aucun clair résiduel** (correctif Lot B prouvé, §2.3) | ☐ | |
| P4 | Démarrer l'application sur B (Akuma.exe ou uvicorn) pointant la base restaurée | `/sante` OK, connexion responsable OK | ☐ | |
| P5 | Contrôle métier sur B : lire les articles, les prix, ouvrir l'historique | prix visibles au responsable, **AUCUN prix pour l'agent stock** (cloisonnement colonnes restitué — prouvé Lot B §2.2) | ☐ | |
| P6 | Contrôle de comptages A ↔ B (leLot B fournit la requête : tables, privilèges, RLS, articles, stocks, utilisateurs, paramètres) | comptages identiques (référence : §2.2) | ☐ | |
| P7 | Saisir UNE vente d'essai sur B, annuler, re-vérifier le stock | parcours complet fonctionnel sur base restaurée | ☐ | |
| P8 | Mesurer le temps total (arrêt A → B opérationnel) | **RTO ≤ 2 h** exigé par C12 | ☐ | |
| P9 | PV signé : captures, empreintes vérifiées, horodatage | archivé avec ce document | ☐ | |

## 5. Ce qui reste ouvert après le Lot B (aucun 100 % déclaré)

| Écart | État après Lot B | Responsable |
|---|---|---|
| C12-01 restauration second PC | mécanisme ENTIER prouvé par exécution (§2.2) ; l'épreuve physique P1–P9 reste à dater/signer | TEST HUMAIN |
| Kaspersky / sauvegarder.ps1 | le script lui-même n'a toujours JAMAIS été exécuté depuis la quarantaine ; la procédure §3 est prête, la décision d'exclusion appartient au propriétaire | PROPRIÉTAIRE |
| C12-03 résilience service PostgreSQL | hors périmètre Lot B (installation, C0-02) ; investigation sur poste cible | développement à l'installation |
| sauvegarde RÉELLE par le vrai script | bloquée par la quarantaine — aucune preuve d'exécution du vrai `sauvegarder.ps1` ne sera claimée avant S5 | propriétaire après §3 |

**Conclusion honnête** : la chaîne mécanique (chiffrement, intégrité,
restauration, reprise applicative, cloisonnement) est prouvée par
exécution à 100 % ; les maillons physiques (imprimante de sauvegarde =
vrai script, second PC, service) restent la propriété du propriétaire
conformément à l'ordre : **C12 ne sera pas déclaré 100 % global tant que
P1–P9 et S1–S6 ne sont pas signés.**
