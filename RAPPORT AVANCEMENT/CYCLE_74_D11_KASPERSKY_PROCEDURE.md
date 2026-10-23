# CYCLE 74 — D11 : procédure de résolution du faux positif Kaspersky sur `sauvegarder.ps1`

**Destinataire :** propriétaire (seule personne habilitée à agir sur son
antivirus et son poste). **Ce document ne décrit que des actions à exécuter
par vous, sur votre machine, avec vos droits administrateur. Le développement
n'a créé aucune exclusion antivirus, généralisée ou non, et n'a désactivé
aucune protection.**

---

## 1. Constat factuel (vérifié par le développement au cycle 74)

| Élément | Constat |
|---------|---------|
| Fichier concerné | `db/outils/sauvegarder.ps1` (script de sauvegarde chiffrée, livré cycle 40) |
| Détection Kaspersky | `PDM:Trojan.Win32.Generic` — détection **heuristique** (PDM = Pattern Detection Mechanism), sans signature précise, typique des faux positifs sur les scripts PowerShell combinant chiffrement AES + HMAC-SHA256 + phrase secrète |
| Fichier sur disque | **ABSENT** — supprimé/mis en quarantaine par Kaspersky (constaté au cycle 74) |
| État Git | suppression visible `D db/outils/sauvegarder.ps1` (jamais commitée, à ne jamais committer) |
| Empreinte attendue (version Git, main = 37b7b79) | SHA-256 `3684aae048cdd66afeeda1a9bfe11855023add940bf385b22a3fe5f4759607a2` — 25 965 octets |
| Dernière modification en Git | commit `9b0c07b` du **2026-09-18** — le script est figé et auditable depuis plus d'un mois ; toute détection récente porte donc sur un fichier inchangé |
| `restaurer.ps1` | **non touché** par l'antivirus |
| Historique | détection reproduite à **chaque exécution** du script (incident documenté au registre, écart C11-01, gravité P1) |

**Pourquoi c'est vraisemblablement un faux positif :** le fichier est
versionné, lisible et inchangé depuis le 2026-09-18 ; sa fonction est
documentée (sauvegarde `pg_dump` + chiffrement AES + authentification
HMAC-SHA256) ; la détection est générique et heuristique (aucun nom de
menace précis). Le jugement final reste celui de la soumission à
l'éditeur (étape 3) — le développement ne « déclare » pas le fichier sain,
il fournit les moyens de le vérifier par empreinte.

## 2. Procédure de résolution soumise (à exécuter dans cet ordre)

### Étape 0 — Rien à faire côté Git
La suppression visible sur le disque est volontairement laissée en l'état ;
elle disparaîtra d'elle-même quand le fichier reviendra identique à HEAD.

### Étape 1 — Restaurer le fichier (au choix, une seule voie suffit)
- **Voie A (recommandée — garanti à l'octet près) :** restauration Git :
  ```powershell
  cd "C:\Users\USER\Documents\MES DOCUMENTS\PROFESSEIONNELS\THED CONNECT\QuincaillerieFranck_Test"
  git checkout -- db/outils/sauvegarder.ps1
  ```
- **Voie B :** restauration depuis la quarantaine Kaspersky : ouvrir
  Kaspersky → **Menaces détectées / Quarantaine** → sélectionner
  `sauvegarder.ps1` → **Restaurer**.

### Étape 2 — Vérifier l'empreinte AVANT toute exécution
```powershell
Get-FileHash "db\outils\sauvegarder.ps1" -Algorithm SHA256
```
- Résultat attendu : **`3684aae048cdd66afeeda1a9bfe11855023add940bf385b22a3fe5f4759607a2`**
- Si l'empreinte **diverge** : STOP — n'exécutez pas le script, ne créez
  aucune exclusion, et signalez-le. Un fichier dont l'empreinte diffère de
  la version Git ne doit jamais être exécuté.

### Étape 3 — Signaler le faux positif à Kaspersky
- Portail : **https://opentip.kaspersky.com/** → catégorie « False
  positive » ; joindre le fichier et préciser l'empreinte SHA-256 ci-dessus.
- Le délai de liste blanche par l'éditeur est variable (quelques jours à
  quelques semaines). Cette démarche ne bloque pas l'étape 4 si vous
  l'estimez nécessaire d'ici là.

### Étape 4 — Si (et seulement si) l'antivirus re-quarantaine à l'exécution : exclusion **ciblée par fichier uniquement**
- Kaspersky → Paramètres → **Menaces et exclusions → Exclusions** → ajouter
  le chemin **complet du fichier seul** :
  `C:\Users\USER\Documents\MES DOCUMENTS\PROFESSEIONNELS\THED CONNECT\QuincaillerieFranck_Test\db\outils\sauvegarder.ps1`
- **Interdits** (conformément à votre ordre et aux bonnes pratiques) :
  exclusion de dossier, exclusion par type de menace, exclusion des scripts
  PowerShell en général, désactivation de la protection résidente ou
  quelconque baisse de protection.
- Sur le poste de production (exécutable Akuma), appliquer la même règle
  fichier par fichier si le même faux positif y surgit.

### Étape 5 — Exécution de contrôle (critère d'acceptation du registre)
1. Lancer une sauvegarde de contrôle réelle (commande habituelle du script,
   vers l'emplacement prévu des sauvegardes chiffrées).
2. Vérifier : **aucune nouvelle quarantaine** + **copie chiffrée présente**
   au répertoire de destination + script terminé proprement.
3. C'est exactement le critère d'acceptation de l'écart C11-01 :
   « sauvegarde exécutée sans quarantaine, copie chiffrée présente ».

### Étape 6 — Retour au développement
Répondre avec : voie choisie (A/B), empreinte constatée, résultat de
l'exécution de contrôle, exclusion posée (oui/non). Le développement
mettra alors à jour le registre (C11-01 → CLOS sur preuve), le journal du
cycle, et débloquera la fiche R4 (pré-requis de l'installation réelle).

## 3. Ce que ce déblocage ouvre

| Dépend de D11 | Nature |
|---------------|--------|
| C11-01 (P1) | déblocage direct — la sauvegarde chiffrée redevient exécutable |
| C12 (chantier sauvegarde/restauration) | la chaîne complète redevient testable |
| Campagne **F** (restauration 2ᵉ PC, RTO 2 h) | nécessite des sauvegardes fraîches et régulières |
| Fiche **R4** (installation 2ᵉ poste) | le même script est utilisé pour les sauvegardes du poste cible |
| Jour J (import stock réel) | une sauvegarde pré-import est un garde-fou indispensable |

**Risque si D11 reste sans réponse :** la sauvegarde chiffrée demeure à
l'arrêt sur ce poste ; en production, le même faux positif pourrait surgir
au pire moment (pendant une sauvegarde, la veille d'un import).
