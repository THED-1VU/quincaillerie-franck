# CYCLE 73 — Relecture intégrale du registre des écarts + tableau des décisions D1–D13

**Date :** 2026-10-23 (cycle 73, branche `cycle-73-analyse-registre`)
**Périmètre :** `REGISTRE_ECARTS_100.md` relu intégralement (40 écarts, 9 déjà
CLOS, 31 ouverts) après l'intégration des 12 PR #78 → #89 dans `main`
(fusions exécutées ce cycle sous autorisation explicite du propriétaire —
mission 1 —, y compris la PR #90 de réintégration ; seul `main` à `d0fa264`
fait foi). **Aucune réponse métier n'est inventée** : les recommandations
reprennent les constats techniques prouvés ; chaque décision reste au
propriétaire.

**Rappel des scores réconciliés (référence post-cycle 72, avant ce cycle) :**
C0 86, C1 92, C2 82, C3 77, C4 78, C5 81, C6 85, C7 67, C8 86, C9 60,
C10 58, C11 85, C12 95, C13 77, C14 66 — moyenne ≈ 78,3 %.

---

## 1. Ce que le cycle 73 change d'abord : les fusions sont faites

Les écarts qui avaient pour seule condition des fusions Git sont désormais
**acquittables** (la preuve d'acquittement = le contenu vérifié sur `main` +
la CI verte, pas seulement la PR ouverte) :

| Écart | Condition qui bloque | État après cycle 73 | Statut proposé |
|-------|---------------------|---------------------|----------------|
| **C0-01** (fusions #78→#82) | fusion propriétaire | 12 fusions exécutées dans l'ordre (#78→#89 + #90), CI verte à chaque étape, aucun conflit masqué, aucun force-push ; `main` = `d0fa264` | **CLOS** (preuve : registre des fusions §journal cycle 73) |
| **C13-01** (job Playwright CI) | fusion de #79 | `.github/workflows/ci.yml` sur `main` porte désormais les jobs **pytest + playwright** ; les deux jobs ont tourné vert à chaque fusion (ex. run 39894259707 : playwright 8 min 39 s, pytest 8 min 57 s) | **CLOS** |
| **C13-02** (régression complète automatisée) | fusion de #79 **et** #88 | les deux fusionnées ; la preuve finale est la **régression locale fraîche rejouée sur le nouveau `main` ce cycle** (détail et chiffres au §journal cycle 73 — la 1ʳᵉ exécution a révélé un artefact d'invocation, corrigé et rejoué) | **CLOS à la production de la preuve fraîche** |
| **C14-01** (versions candidates non fusionnées) | fusion de #80/#81 | `main` contient l'exécutable reconstruit (cycle 63) **et** le dossier `INSTALLATION/` complet (guide testeur, checklist, preuve de simulation, README) | **CLOS** |
| **C14-03** (note de transfert) | — (déjà CLOS au cycle 72) | le contenu de la PR #89 n'est arrivé sur `main` **que ce cycle** via la PR #90 (`NOTE_DE_TRANSFERT.md`, 8 674 octets, vérifié sur `main`) | CLOS confirmé **sur `main`** |

Après acquittement, il reste **27 écarts ouverts** (au lieu de 31), tous
bloqués sur une décision ou une validation humaine — aucun n'est actionnable
par le développement sans décision préalable, sauf mention contraire ci-dessous.

---

## 2. Analyse des 31 écarts ouverts, un par un

Légende : **Satisfait ce cycle** = la condition est levée, l'écart passe en
acquittement ; **Reste** = ce qui manque concrètement ; **Décision** = qui
doit faire quoi ; **Preuve attendue** = ce qui clôturera l'écart ; **Effet**
= mouvement de score justifiable (amplitude à confirmer par re-audit).

### P1 (17 écarts — vérifiés un par un, voir §3)

| # | Écart | Satisfait ce cycle ? | Reste | Décision | Preuve attendue | Chantier | Effet |
|---|-------|----------------------|-------|----------|-----------------|----------|-------|
| 1 | **C0-01** fusions PR | **OUI** — 12 fusions + #90, ordre respecté, CI verte chaque fois | rien (mis à part la prise de connaissance du propriétaire) | propriétaire : constater l'exécution | registre des fusions dans le journal du cycle 73 + `main` = `d0fa264` | C0 | C0 86 → **≈ 90** |
| 2 | **C0-02** service PG + sauvegarde planifiée au poste cible | non | exécuter `enregistrer_service_pg.ps1` + `planifier_sauvegarde.ps1` sur le poste cible | propriétaire (+ opérateur), lors de l'installation réelle | service présent après redémarrage du poste ; sauvegarde chiffrée à l'heure dite ; `restaurer.ps1` rejoué | C0 | s'ajoute à C0 |
| 3 | **C0-03** installation réelle sur 2ᵉ poste | non | scénario `GUIDE_TESTEUR_INSTALLATION.txt` sur machine vierge | propriétaire / test humain | parcours complet + PV signé | C0/C12 | conditionne C12-01 |
| 4 | **C1-01** paiements mixtes | non | table `ventes_paiements` (migration 051+) après décision | **D2** (propriétaire) puis développement | vente à deux modes enregistrée, tracée, exportée, total contrôlé par la base | C1 | s'ajoute à C1 |
| 5 | **C1-03** reprise sur vraies données | non | protocole d'import réel (`importer_stock_initial.py`) avec reprise d'essai sur copie | propriétaire (+ fichier réel) | base de production chargée, comptages réconciliés, PV | C1/C14 | conditionne le GO |
| 6 | **C3-01** visibilité prix caissier | partiellement — technique **déjà vérifié** (aucun `prix_achat` n'atteint écrans ni réponses réseau ; inspection + matrice cycle 65) | confirmation formelle de l'option 1 | **D1** (propriétaire) | décision écrite ; si variante « total seul » : écran + tests | C3 | C3 77 → ≈ 80 à la confirmation |
| 7 | **C4-03** campagne UX stock | non | campagne guidée (réception, transfert, casse, comptage) | test humain | PV sans anomalie bloquante | C4 | s'ajoute à C4/C9 |
| 8 | **C5-02** seuil remises | non | pourcentage + comportement (blocage/alerte) | **D4** (propriétaire) puis développement (mécanisme déjà livré au cycle 42, inactif) | paramètre en config + tests dédiés + Playwright remise > seuil | C5 | s'ajoute à C5 |
| 9 | **C5-03** impression ticket | non | impression réelle (bouton navigateur suffisant en v1) | test humain (imprimante) | ticket papier lisible, mentions incluses, PV | C5 | s'ajoute à C5 |
| 10 | **C6-01** fond de caisse + seuil écart | non | modèle (fond) + écran après décision | **D3** (propriétaire) puis développement | clôture calculant écart vs fond+ventes, régularisation tracée | C6 | s'ajoute à C6 |
| 11 | **C7-04** 2ᵉ campagne comptage réel | non | campagne de recette croisée | test humain | deux campagnes concordantes + PV | C7 | s'ajoute à C7 |
| 12 | **C9-01** campagne UX complète n°2 | **débloqué ce cycle** — sa seule dépendance (« fusions PR pour tester la version fusionnée ») est levée ; la version candidate existe sur `main` | exécuter le guide testeur poste par poste | test humain | fiches de retour sans anomalie bloquante ; correctifs éventuels en cycles dédiés | C9 | débloque C10-01 |
| 13 | **C10-01** rapport de tests manuels + PV signé | non (dépend C9-01) | consolider les fiches de campagne en PV | développement (consolidation) + propriétaire (signature) | PV signé au dossier C14 | C10/C14 | débloque C14-02 |
| 14 | **C11-01** faux positif Kaspersky | non — **reproduit ce cycle** : `db/outils/sauvegarder.ps1` a de nouveau été supprimé du disque par l'antivirus pendant le cycle (constat au `git status`, fichier restaurable depuis Git mais requarantainé) | exclusion ciblée côté poste | propriétaire (**D11**, droits administrateur) | sauvegarde exécutée sans quarantaine, copie chiffrée présente | C11/C12 | GO (sauvegarde à l'arrêt sur ce poste) |
| 15 | **C12-01** restauration sur 2ᵉ poste | non (dépend C0-03/C0-02) | `restaurer.ps1` sur second poste + connexion + contrôles | test humain | base restaurée fonctionnelle + PV | C12 | dernière marche de C12 (95 %) |
| 16 | **C14-01** versions candidates fusionnées | **OUI** — `main` contient exe + dossier d'installation | rien | propriétaire : constater | arborescence `main` + CI verte | C14 | C14 66 → **≈ 76** |
| 17 | **C14-02** PV recette + dossier GO/NO-GO | non | consolidation (version figée, guides, protocoles, PV, retour arrière, checklists J-1/Jour J, risques résiduels) — les supports de préparation sont livrés ce cycle (fiches de recette, voir `CYCLE_73_FICHES_RECETTE.md`) | développement (consolidation) + propriétaire (signature GO) | dossier complet + PV signé + GO consigné | C14 | clôture l'objectif 100 % |

### P2 (12 écarts)

| # | Écart | Satisfait ce cycle ? | Reste | Décision | Preuve attendue | Chantier | Effet |
|---|-------|----------------------|-------|----------|-----------------|----------|-------|
| 18 | **C1-02** ventilation HT/TTC documents | non | colonne HT par ligne si requis | **D5** (propriétaire — à confirmer par le comptable avant tout import réel) | facture conforme à la décision + pytest reçu | C1 | s'ajoute à C1 |
| 19 | **C2-01** confirmations paramètres | non | trancher les 5 lignes `a_decider=TRUE` (`boutique_numero_contribuable`, `boutique_telephone`, `seuil_alerte_plancher`, `seuil_ecart_caisse_tolere`, `tentatives_max_connexion`) + confirmation `duree_session=480` et `plafond_vraisemblance` | propriétaire | bascule `a_decider=FALSE` avec référence datée + seed mis à jour | C2 | s'ajoute à C2 |
| 20 | **C2-02** 2FA | non | décision puis TOTP si retenu | **D10** (propriétaire) | connexion à 2ᵉ facteur + procédure de récupération documentée | C2 | Qualité (menace faible : poste dédié local) |
| 21 | **C5-01** `utilisateur_caisse_id` | constat chiffré fait (cycle 66) : attribution **systématique** au compte responsable même quand un agent saisit (`ventes.py:210-227`) | trancher puis correctif court (le compte authentifié est déjà porté par le jeton) | **D9** (propriétaire) | vente saisie par `agent_comptabilite` portant son id + tests | C5 | s'ajoute à C5 (traçabilité « qui a encaissé ») |
| 22 | **C6-02** vente tardive / Mobile Money hors-ligne / blocage post-clôture | non | 3 règles à écrire puis ajustements ciblés | propriétaire puis développement | règles + pytest (vente 23 h 59 / 00 h 01) | C6 | s'ajoute à C6 |
| 23 | **C7-01** plafond vraisemblance | non | confirmation écrite de la valeur 10 000 (déjà en config, `a_decider=FALSE`) | propriétaire | confirmation datée au registre des décisions | C7 | mineur |
| 24 | **C10-02** test multi-postes simultané | non | deux postes (ou deux navigateurs) saisissant en parallèle | test humain (dépend C0-03) | ventes simultanées sans conflit, journaux corrects | C10 | s'ajoute à C10 |
| 25 | **C11-02** poste cible : lockfile, venv, empreinte exe | **condition levée** (PR #80/#81 fusionnées, le contenu à vérifier est sur `main`) | exécuter la checklist d'installation sur place | développement lors de l'installation accompagnée | empreinte SHA de l'exe conforme, venv issu du lockfile | C11 | au jour J |
| 26 | **C12-02** alerte échec de sauvegarde | non | mécanisme minimal (fichier d'alerte + carte tableau de bord) **ou** acceptation écrite renouvelée | propriétaire | décision écrite ; si mécanisme : alerte testée en échec simulé | C12 | s'ajoute à C12 |
| 27 | **C12-03** résilience service PostgreSQL | non (dépend C0-02) | investigation journal Windows + PostgreSQL sur le poste cible ; service enregistré + surveillance | développement lors de l'installation | service démarré, test de coupure simulé documenté | C12 | s'ajoute à C12 |
| 28 | **C13-01** job Playwright CI | **OUI** | rien | — | workflow pytest+playwright vert sur `main` (prouvé sur les fusions du cycle) | C13 | C13 → ≈ 100 (avec C13-02) |
| 29 | **C13-02** régression complète automatisée | **OUI** (orchestrateur `verifier_tout.sh` 13 suites fusionné via #88 ; partie CI via #79) | rejouer la preuve **fraîche sur le nouveau `main`** (fait ce cycle, §journal) | — | 13/13 suites, EXIT=0 sur `main` = `d0fa264` | C13 | avec C13-01 : C13 77 → **≈ 100** |

### P3 (2 écarts ouverts)

| # | Écart | Reste | Décision | Preuve attendue | Chantier |
|---|-------|-------|----------|-----------------|----------|
| 30 | **C3-02** responsable ne compte pas | confirmation formelle de l'option 1 (écran réservé agent stock, responsable supervise) — déjà cohérent API/UI vérifié | **D8** | décision écrite ; adaptateur Playwright seulement si délégation | C3 |
| 31 | **C3-03** cumul de rôles à l'écran | confirmation formelle (livré et testé au cycle 43) | **D7** | décision écrite | C3 |

*(C14-03 : CLOS — son contenu est désormais réellement sur `main` via #90,
voir §1.)*

---

## 3. Vérification des 17 écarts P1 (contrôle demandé par le propriétaire)

1. **C0-01** — vérifié : `gh pr list --state open` ne retourne plus aucune PR
   du lot #78→#89 ; shas de fusion 12/12 en journal ; `main` = `d0fa264`
   (parents c4e0e9b + 805d479). ✔ levé.
2. **C0-02** — vérifié : toujours `BLOQUE_PROPRIETAIRE` ; aucune exécution des
   deux scripts sur un poste cible (aucune autorisation d'installation reçue).
   ✔ reste bloqué (normal).
3. **C0-03** — vérifié : aucune installation sur 2ᵉ poste ce cycle. ✔ reste
   bloqué (normal).
4. **C1-01** — vérifié : aucune migration `ventes_paiements` (dernier numéro :
   050, changement de mot de passe requis) ; `ventes.mode_paiement` toujours
   mono-valeur. ✔ reste bloqué sur D2.
5. **C1-03** — vérifié : aucun import de données réelles (ordre permanent). ✔
   reste bloqué (normal).
6. **C3-01** — vérifié : l'état technique décrit au registre est inchangé
   (`vente.html` ne consomme que `prix_vente`, vue 048 sans `prix_achat`,
   `security_invoker`) ; aucune décision D1 consignée. ✔ reste bloqué sur
   confirmation.
7. **C4-03** — vérifié : aucune campagne stock humaine menée. ✔ reste bloqué
   (normal).
8. **C5-02** — vérifié : `seuil_remise_validation_pct` présent dans le seed
   depuis le cycle 68 mais **inactif** (pas de valeur décidée). ✔ reste bloqué
   sur D4.
9. **C5-03** — vérifié : aucune impression réelle testée. ✔ reste bloqué
   (normal).
10. **C6-01** — vérifié : `seuil_ecart_caisse_tolere` toujours `a_decider=TRUE`
    ; aucune table de fond de caisse (dernière migration : 050). ✔ reste
    bloqué sur D3.
11. **C7-04** — vérifié : une seule campagne de comptage au dossier. ✔ reste
    bloqué (normal).
12. **C9-01** — vérifié : campagne n°2 non menée ; **dépendance levée ce
    cycle** (version fusionnée disponible). ✔ débloqué, prêt à exécuter (fiche
    livrée ce cycle).
13. **C10-01** — vérifié : aucun PV signé au dossier. ✔ reste bloqué (attend
    C9-01).
14. **C11-01** — vérifié : incident **reproduit ce cycle** (suppression du
    script sur disque constatée au `git status` après le pull). ✔ reste
    bloqué sur action propriétaire.
15. **C12-01** — vérifié : aucune restauration sur second poste. ✔ reste
    bloqué (normal).
16. **C14-01** — vérifié : `INSTALLATION/` + exe présents sur `main`. ✔ levé.
17. **C14-02** — vérifié : dossier GO/NO-GO non consolidé ; préparation
    avancée ce cycle (fiches de recette). ✔ reste bloqué sur les campagnes +
    signature.

**Bilan P1 : 3 écarts levés par le cycle 73 (C0-01, C14-01, et C9-01
débloqué), 14 restent bloqués sur décision/action humaine — aucun nouveau
bloquage technique constaté.**

---

## 4. Tableau des décisions D1–D13 (options, recommandation argumentée, conséquences)

Les recommandations reprennent les constats techniques prouvés du dépôt ;
**l'arbitrage métier appartient au propriétaire** — les colonnes
« conséquence métier » décrivent des conséquences, pas des décisions.

| Décision | Écart(s) | Options | Recommandation argumentée (technique) | Conséquences techniques | Conséquences métier | Impact |
|----------|----------|---------|----------------------------------------|-------------------------|---------------------|--------|
| **D1** prix caissier | C3-01 | 1. statu quo (prix vente visibles, achat jamais) 2. masquer davantage 3. rôle caissier distinct | **Option 1** — déjà en place et vérifiée en inspection + matrice (aucun code à écrire) | aucune si option 1 ; sinon écran variante + tests Playwright par rôle + contrôle réseau | option 1 = vendeur/caissier voit le prix de vente, jamais la marge ; options 2-3 = périmètre commercial à définir | GO + Score C3 |
| **D2** paiements mixtes | C1-01 | 1. mono-mode (statu quo) 2. multi-modes (`ventes_paiements`) | si cas rare : option 1 en v1 (acompte partiel déjà couvert par les règlements de créance) | option 2 = migration 051+, impact caisse/rapports/annulation/clôture — chantier à part entière | option 1 oblige à scinder une vente réelle « espèces + Mobile Money » en deux enregistrements ; option 2 la trace fidèlement | GO |
| **D3** fond de caisse + seuil écart | C6-01 | 1. fond paramétrable par site, seuil fixe 2. fond saisi à chaque clôture, seuil paramétrable | option 1 (fond stable en pratique) | option 1 = paramètre + calcul écart vs fond+ventes + écran + tests | chiffre l'écart de caisse : sans lui, chaque clôture en écart demande une investigation manuelle | Score C6 |
| **D4** seuil remises | C5-02 | 1. plafond % + alerte 2. validation responsable au-delà du seuil 3. libre | option 1 avec paramètre par défaut neutre jusqu'à choix du pourcentage (mécanisme déjà livré cycle 42, inactif) | activer le paramètre + tests dédiés + Playwright > seuil | une remise de 99 % reste possible sans alerte tant que non tranché (maîtrise des marges) | GO |
| **D5** HT ou TTC | C1-02 | 1. confirmer TTC (hypothèse en place depuis le cycle 6) 2. basculer HT | faire confirmer TTC par le comptable **avant tout import réel** ; si confirmation : ajouter la ventilation HT ligne à ligne sur les documents si exigée | inversion après coup = migration de données ; ventilation = colonnes sur reçu/rapports | présentation fiscale des factures ; à trancher avant le jour J | GO |
| **D6** durée session | C2-01 | 1. 8 h fixes (valeur décidée 2026-09-22, à confirmer formellement) 2. paramètre de base modifiable | option 1 en v1 (une valeur modifiable a des effets de sécurité à documenter) | option 2 = brancher `parametres.duree_session_minutes` sur l'émission des jetons | option 1 = déconnexion au bout de 8 h de session | Score C2 |
| **D7** cumul rôles UI | C3-03 | 1. un seul périmètre visuel (rôle principal) 2. menu par union + bascule | option 1 tant que le cumul reste rare (aucun trou de sécurité : l'API reste le garde) | option 2 = refonte navigation + tests | confort d'usage des comptes cumulés | Qualité |
| **D8** responsable compte ? | C3-02 | 1. comptage = agent stock, responsable supervise 2. ouvrir l'écran au responsable | option 1 (cohérente avec le comptage à l'aveugle et l'addendum) | option 2 = ouvrir la gate + adaptateur Playwright | praticité au jour J si l'agent stock est absent | Qualité |
| **D9** `utilisateur_caisse_id` | C5-01 | 1. journal actuel conservé (toujours responsable) 2. attribuer au compte authentifié | audit déjà fait (constat chiffré cycle 66) ; le correctif de l'option 2 est court (jeton déjà porteur) — à trancher en connaissance de cause | option 2 = correctif `ventes.py` + tests pytest/SQL | option 1 = le journal d'audit prête l'encaissement au responsable même quand un agent saisit (traçabilité faussée en cas de litige caisse) | Score C5 |
| **D10** 2FA | C2-02 | 1. statu quo 2. code par e-mail 3. TOTP hors ligne | reporter après la v1 ; si retenu : TOTP (option 3, indépendant de la connectivité) | option 3 = intégration TOTP + procédure de récupération + tests | mitigation si mot de passe fuité ; menace réelle faible (poste dédié, réseau local) | Qualité |
| **D11** Kaspersky | C11-01 | 1. exclusion ciblée dossier/script 2. réécrire en binaire | **option 1** — l'option 2 ne supprime pas la détection heuristique ; reproduit encore ce cycle | aucune (action machine) | la sauvegarde chiffrée est à l'arrêt sur ce poste tant que l'exclusion n'est pas posée — risque de perte de données réel | GO |
| **D12** tests physiques / GO | C9-01, C10-01, C12-01, C14-02 | ordre des étapes (décisions D1–D6 → import test → campagne UX → installation poste caisse → bascule) | ordre proposé repris tel quel ; les fiches de recette livrées ce cycle rendent chaque étape immédiatement exécutable | chaque étape = preuve + PV | bascule en production — chaque étape exige l'autorisation explicite du propriétaire | GO + Score C9/C10/C12/C14 |
| **D13** fusions PR | C0-01, C13-01, C14-01 | — | **soldé** : 12 fusions exécutées ce cycle sous autorisation mission 1 (ordre, CI verte, aucun conflit masqué, aucun force-push) ; seule la **PR #60** (doc-only, cycle 56) reste ouverte — « fusionner ou fermer », décision propriétaire | aucune | `main` est désormais la version candidate de référence pour la recette | **RÉSOLU** (reste : sort de #60) |

**État D13 détaillé — PR #60 (seule encore ouverte) :**
- Contenu : documentation seule (32 insertions, 1 ligne modifiée dans
  `ADDENDUM_CAHIER_DES_CHARGES.md`) — marque le chantier C point a
  (« une fiche, un stock par site », décidé 2026-09-19) comme **livré** aux
  cycles 34-35 (migrations 025-031), ce que l'addendum ne disait pas.
- Fraîcheur : le contenu reste **exact** en 2026-10-23 (C4-01 du registre,
  CLOS, re-vérifie le même modèle : `articles` sans `site_id`, `stocks_sites`
  en clé composite). Aucun des 35 commits fusionnés ce cycle ne touche
  l'ADDENDUM : **pas de doublon, pas de conflit** (diff trois-points propre).
- Recommandation : **fusionner** (documentation exacte, zéro code, zéro
  risque), ou fermer si le propriétaire préfère requalifier. **Décision
  réservée au propriétaire** (règle permanente + mission 1 : « Ne pas prendre
  cette décision sans ma validation »).

---

## 5. Chemin vers 99–100 % après ce cycle

1. **Fait (cycle 73)** : intégration complète → C0-01, C13-01, C13-02
   (preuve fraîche), C14-01 acquittés ; C9-01 débloqué.
2. **Décisions propriétaire** (D1–D6, D8–D10 + confirmations C2-01/C7-01/
   C12-02 + sort de #60) : 13 points — aucune ligne de code ne peut les
   remplacer.
3. **Campagnes humaines** (D12) : campagne UX n°2 (tous parcours, fiche
   prête), campagne stock, 2ᵉ comptage, impression, 2ᵉ poste + restauration,
   multi-postes — fiches GO/NO-GO livrées ce cycle.
4. **Au jour J** (sous autorisation) : installation réelle (C0-02, C0-03,
   C11-02, C12-03), import réel (C1-03), consolidation + signature du PV
   (C10-01, C14-02) et GO.

Gains de score justifiables ce cycle (amplitudes à confirmer par re-audit) :
**C0 86 → ≈ 90**, **C13 77 → ≈ 100**, **C14 66 → ≈ 76** — moyenne ≈ 78,3 % →
**≈ 80–81 %** sans aucune campagne humaine supplémentaire ; les chantiers
restants ne bougeront plus que sur décisions (D1–D10) ou validations
humaines (D12).

---

*Règle respectée : aucun écart n'est déclaré clos sans preuve d'exécution
réelle ; aucune réponse métier n'a été inventée ; toutes les décisions
restent au propriétaire.*
