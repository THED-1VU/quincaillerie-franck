# Cycle 75 — Rapport consolidé : exécution des décisions du propriétaire (2026-10-23)

Ordre du propriétaire : implémenter les 9 décisions validées (D2, D4, D5, D6,
D7, D8, D9, D10, C12-02) par sous-cycles LOOP (ANALYSE → IMPLÉMENTATION →
TESTS CIBLÉS → CORRECTIONS → RÉGRESSION → PREUVES → JOURNAL → PR), sans
attendre une nouvelle autorisation entre sous-cycles techniques, sans jamais
fusionner une PR dont les contrôles obligatoires échouent. **9/9 décisions
implémentées et testées, 8 PR ouvertes empilées (#93→#100), aucune fusionnée**
(fusion = propriétaire uniquement).

## 1. Les 9 décisions — chaîne VALIDÉE → IMPLÉMENTÉE → TESTÉE

| Décision | Sous-cycle | PR / commit | Livraison | Preuves d'exécution |
|---|---|---|---|---|
| **D9** encaissement attribué au compte authentifié | C75-A | #93 · 84152ad | `ventes.py` tire `utilisateur_caisse_id` du jeton signé ; l'ancienne requête « premier responsable trouvé » est supprimée | `test_encaissement_d9.py` 3/3 (agent → agent ; responsable → responsable ; injection navigateur ignorée — `DemandeVente` n'expose aucun champ) ; non-régression ventes 45/45, caisse+crédit 35/35 |
| **D4** remises ≤ 10 %, au-delà validation responsable | C75-B | #94 · 15937f4 | Migration 051 `seuil_remise_validation_pct=10` (+ inverse) ; blocage **403 serveur** pour un agent, par ligne ET remise globale, strictement `>` | `test_seuil_remise_d4.py` (150 lignes) ; jeu d'essai synchronisé + verrou `test_jeu_essai.py` ; suite vente Playwright étendue |
| **D2** paiements mixtes espèces + Mobile Money | C75-C | #95 · 69b55c0 | Migration 052 `ventes_paiements` (une composante par mode, backfill, **invariant somme = encaissé porté par la base**, RLS par site) ; API `paiements[]` (somme inexacte → 422, recette de journal toujours UNIQUE du total) ; case « paiement mixte » dans `vente.html`, reçu PDF décomposé, attendu de caisse rejoint sur les composantes | 10 tests pytest D2 (composantes, invariants en SQL direct, attendu caisse, annulation) ; vente Playwright 63/63 (+12) ; pytest complet **354/354** |
| **D7** union des rôles à l'écran + **D8** comptage agent / validation responsable | C75-D | #96 · 5dcd967 | Carte centralisée `ROLES_PAR_PAGE` (api.js) + `ajusterNavigation()` : retire les liens interdits ET ajoute les manquants — un compte cumulé voit TOUTES ses fonctions | D8 prouvée par exécution : l'agent stock compte, le responsable valide sur `declarations.html` avec effet stock réel (stock 49/49) ; captures régénérées |
| **D6** session ≤ 480 min vérifiable + **D10** 2FA reportée après V1 | C75-E | #97 · 50a8e3a | Plafond porté par les jetons signés (migration 033), révocation une à une (018), aucune route de renouvellement ; **7 mesures compensatoires** consignées (D10) | `test_session_d6.py` : expiration et révocation prouvées ; chaque mesure compensatoire adossée à son test rejoué vert (liste dans `DECISIONS_PROPRIETAIRE.md` D10) |
| **C12-02** alerte visible d'échec/absence de sauvegarde | C75-F | #98 · 3fd51a9 | Endpoint interprété `GET /exploitation/etat-sauvegarde` (succès daté / échec motivé / absent / inconnu — **jamais de succès sans preuve**) ; bandeau persistant `role=alert` au tableau de bord nommant le motif ; pastille d'alerte | `test_exploitation_etat.py` 8/8 via faux fichiers (`sauvegarder.ps1` jamais exécuté, limite §7) ; exploitation 14/14, câblage 101/101 (bandeau : 4 états), routes 65/65, matrice des rôles (403 agents) |
| **D5** prix TTC conservés, traitement fiscal à confirmer | C75-G | #99 · 1535236 + a4fcce2 | Audit `RAPPORT AVANCEMENT/D5_AUDIT_TTC.md` : TVA extraite sur le total, **aucun taux inventé** ; états réels vérifiés en SQL (migrations = sentinelles ; base de test = valeurs cycle 6, `taux_tva` 19,25) ; **6 questions Q1-Q6** pour le comptable ; 6 lignes `a_decider=TRUE` relevées | Vérifications SQL exécutées sur base reconstruite ; aucune bascule de paramètre avant les réponses (C1-02 reste bloqué sur elles) |

## 2. Audit d'impact préalable (exigé avant tout code)

`RAPPORT AVANCEMENT/CYCLE_75_AUDIT_IMPACT.md` — cartographie schéma / API /
écrans / RLS / tests de chaque décision avant l'implémentation : migrations
prévues (051, 052), routes touchées, écrans concernés, suites de test à
étendre. Aucun code écrit avant cet audit.

## 3. Régressions découvertes par la régression complète et la CI — corrigées (C75-H, PR #100)

Trois régressions introduites par le cycle 75 lui-même, trouvées parce que la
régression complète ET la CI ont été rejouées (aucune n'aurait été vue par
les seuls tests ciblés des sous-cycles) :

1. **Crash de la suite stock** (C75-D) : `ajusterNavigation` retire
   `#lien-declarations` du bandeau de l'agent stock avant l'init de la page ;
   `stock.html` écrivait `.hidden` dessus → TypeError → `#f-nom` jamais créé.
   Correctif : garde-null.
2. **Débordements du bandeau à 768/1366 px** (comptes, rapports, caisse, rh —
   C75-D) : l'union D7 remplit le bandeau au-delà d'une ligne ; `flex-wrap`
   n'était autorisé que sous 720 px. Correctif : `flex-wrap: wrap` dans la
   règle de base `.bandeau`.
3. **Crash de la suite UX-2** (C75-B) : le scénario négociait 2900 sur le Fer
   à béton 3500 = 17,1 % de remise, désormais refusée 403 à l'agent (D4).
   Correctif : prix négocié 3300 (5,7 %) — le contrôle porte sur le clavier
   seul, pas sur la remise.

Suites ciblées rejouées en local après correctifs : stock **49/49**, ux
**27/27**, rapports **52/52**, comptes OK (exit 0), caisse **24/24**, rh
**21/21**, câblage **101/101**. 43 captures régénérées (bandeau à deux
lignes = comportement voulu).

## 4. Vérifications de clôture (preuves réelles)

- **pytest** : complet **354/354** en local (branche C75-H) ; job pytest de
  la CI **PASS** sur la PR #100 (7 min 26 s).
- **CI GitHub — PR #100 (sommet de la pile, contient TOUT le cycle 75)** :
  job playwright **13/13 suites réussies** (run 39942692463) — routes 65,
  câblage 101, vente 63, stock 49, rapports 52, inventaire 17, ux 27,
  comptes 26, caisse 24, rh 21, exploitation 14, échappement 11, roles.
- **Régression complète locale** (`bash db/outils/verifier_tout.sh`, branche
  C75-H, exécutée le 2026-10-23) : SQL complet + reconstruction + pytest +
  13 suites Playwright + jeu d'essai final rechargé — **BILAN « Toutes les
  étapes sont passées », ETAPES_KO=0**. Fin de run visible dans la sortie :
  échappement **11/11**, roles **35/35** (dont les 10 contrôles d'union D7
  « cumul » et les 5 de changement de mot de passe forcé), jeu d'essai final
  OK (journaux : `db/tests/DERNIER_RESULTAT.md`,
  `server/tests/DERNIER_RESULTAT.md`, `maquette/verification/DERNIER_RESULTAT.md`).
- **CI par PR** (pile empilée, chacun re-testé par GitHub) :

| PR | Contenu | pytest | playwright |
|---|---|---|---|
| #93 (D9) | pass | **pass** |
| #94 (D4) | **fail** (test retour crédit : remise 84,6 % désormais interdite — corrigé dans la branche suivante) | fail (les 3 régressions, corrigées en #100) |
| #95 (D2) | pass | fail (idem) |
| #96 (D7+D8) | pass | fail (idem) |
| #97 (D6+D10) | pass | fail (idem) |
| #98 (C12-02) | pass | fail (idem) |
| #99 (D5) | pass | fail (idem) |
| **#100 (correctifs + tout le cycle)** | **pass** | **pass — 13/13 suites** |

Lecture : les échecs des PR intermédiaires sont exactement les 3 régressions
du §3 (et l'alignement pytest de #94), toutes corrigées dans #100. **#100 est
le seul état complètement vert et contient l'intégralité du cycle 75** —
deux chemins s'offrent au propriétaire (§7).

## 5. Tableau C0-C14 (taux individuels après cycle 75)

| Chantier | Taux | Ce qui a bougé au cycle 75 | Ce qui manque pour 99-100 % |
|---|:---:|---|---|
| C0 Infrastructure et dépôt | **90 %** | — | installation réelle 2ᵉ poste (C0-03, test humain), service PostgreSQL + tâche planifiée (C0-02, admin) |
| C1 Base de données et intégrité | **96 %** ↑ (92) | D2 : `ventes_paiements`, invariant porté par la base (C1-01 CLOS) | C1-02 (réponses comptable Q1-Q6), C1-03 (reprise avec vraies données — jour J) |
| C2 Authentification et comptes | **90 %** ↑ (82) | D6 prouvée (C2-01 moitié session résorbée), D10 : C2-02 CLOS avec 7 mesures compensatoires testées | confirmation `tentatives_max_connexion` (C2-01) |
| C3 Habilitations et cloisonnement | **88 %** ↑ (77) | D7 implémentée (union des écrans), D8 confirmée (C3-02, C3-03 CLOS) | D1 : confirmation du statu quo prix caissier (C3-01) |
| C4 Articles et stock | **78 %** | — | campagne UX du parcours stock (C4-03, test humain) |
| C5 Ventes et facturation | **88 %** ↑ (81) | D9 (C5-01 CLOS), D4 (C5-02 CLOS), paiements mixtes décomposés sur le reçu | impression physique du ticket (C5-03, test humain) |
| C6 Comptabilité et RH | **85 %** | attendu de caisse rejoint sur les composantes de paiement (D2) | D3 (fond de caisse, seuil d'écart), C6-02 (vente tardive, Mobile Money déconnecté, blocage post-clôture) |
| C7 Inventaire et écarts | **67 %** | — | C7-01 (confirmation `plafond_vraisemblance_comptage`), 2ᵉ campagne de comptage (C7-04) |
| C8 Interfaces et parcours | **86 %** | bandeau union D7 (+ correctif flex-wrap), bandeau sauvegarde | campagne UX n°2 (C9-01 recouvre le parcours) |
| C9 Ergonomie et UI | **60 %** | UX-2 revérifié sous D4 (vente clavier seul 3300) | campagne UX humaine n°2 (C9-01) |
| C10 Mobile et API web | **58 %** | débordements bandeau corrigés aux 5 largeurs | campagne sur téléphone réel, test multi-postes (C10-02) |
| C11 Sécurité applicative | **85 %** | D10 : mesures compensatoires prouvées une par une | D11 (exclusion Kaspersky — action propriétaire), C11-02 (jour J) |
| C12 Sauvegarde et reprise | **97 %** ↑ (95) | C12-02 livré : bandeau d'alerte testé en échec simulé | C12-01 (restauration 2ᵉ poste, test humain), C12-03 (jour J) |
| C13 Tests automatisés et qualité | **100 %** | 13 suites Playwright vertes en CI sur le sommet de la pile ; régression complète locale verte | — |
| C14 Dossier de recette | **76 %** | registre et décisions consolidés (chaîne VALIDÉE → IMPLÉMENTÉE → TESTÉE) | C14-02 : PV de recette + GO/NO-GO (signature propriétaire) |

**Moyenne indicative : ≈ 80,8 % (cycle 73) → ≈ 83 % (cycle 75).** Aucune
hausse sans preuve d'exécution réelle ; les chantiers à décision restante ne
sont pas montés artificiellement.

## 6. Registre des écarts : 20 CLOS / 20 ouverts / 0 P3

Clôturés au cycle 75 sur les décisions du propriétaire : **C5-01** (D9),
**C5-02** (D4), **C1-01** (D2), **C2-02** (D10), **C3-02** (D8), **C3-03**
(D7), **C12-02** (alerte sauvegarde). Restent 20 écarts ouverts :
11 BLOQUE_PROPRIETAIRE · 7 BLOQUE_TEST_HUMAIN · 2 jour J (C11-02, C12-03).
**Aucun P0, aucun P3.** Détail et preuves : `REGISTRE_ECARTS_100.md`.

## 7. Ce qui reste à la main du propriétaire

1. **Fusions** — deux chemins, à son choix (les deux intègrent tout le
   cycle 75 ; aucun conflit masqué, aucun force-push) :
   - **(a) fusionner #93 puis #100** : #100 contient les commits de
     #94→#99, GitHub marquera ces PR intégrées ; seules deux fusions à
     valider, chacune sur CI verte ;
   - **(b) fusionner #93→#100 une par une** pour la piste de revue : les CI
     des PR #94→#99 sont rouges exactement des 3 régressions du §3 (corrigées
     dans #100) — la règle « ne pas fusionner une PR dont les contrôles
     échouent » s'apprécie alors à la lumière du présent rapport.
2. **Sort des PR #60 et #92** (documentation) — décision propriétaire.
3. **D1** : confirmer le statu quo (prix de vente seuls au caissier — déjà
   en place et vérifié, aucune ligne de code à écrire).
4. **D3** : fond de caisse initial + seuil d'écart toléré (C6-01, 2 lignes
   `a_decider`).
5. **C6-02, C7-01** : arbitrages commerciaux restants (vente tardive /
   Mobile Money déconnecté / blocage post-clôture ; confirmation du plafond
   de vraisemblance 10 000).
6. **D11** : sur son poste — restauration de `sauvegarder.ps1` depuis la
   quarantaine Kaspersky + exclusion ciblée (procédure et empreintes SHA-256
   au cycle 74). La suppression du fichier du disque local n'est **jamais
   commitée** (arbitrage D11 en cours).
7. **Réponses du comptable Q1-Q6** (D5) — avant tout import réel du stock ;
   aucune bascule de paramètre avant elles.
8. **Campagnes humaines** (fiches prêtes `CYCLE_73_FICHES_RECETTE.md`) et
   **D12** (tests physiques, PV, GO/NO-GO).

## 8. Limites impératives respectées (§7 de l'ordre)

Aucun GO production · aucune installation réelle en boutique · aucun import
de données réelles · aucune exclusion antivirus posée par le développement ·
`sauvegarder.ps1` jamais exécuté ni restauré sans validation de sécurité ·
aucune fusion de PR par le développement · décisions D1, D3, C6-02, C7-01 et
les autres arbitrages non couverts restent OUVERTS.
