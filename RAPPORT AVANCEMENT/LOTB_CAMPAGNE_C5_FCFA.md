# Campagne métier C5 — Ventes et facturation en FCFA (Lot B, 2026-10-23)

Commande du propriétaire (opération 100 % / Lot B) : « Prépare une campagne
de tests métier avec des montants en FCFA, comprenant les cas normaux,
limites et erreurs. »

## 1. Périmètre et environnement

* **Chantier :** C5 — Ventes et facturation (88 % au registre avant le lot).
* **Base d'exécution :** `quincaillerie_lotb` (base isolée du Lot B, port
  5433 — jamais `quincaillerie_test`, réservée à Codex, cf.
  `COORDINATION_LOT_B_CODEX.md`).
* **Jeu de prix du seed (`db/tests/00_jeu_essai.sql`, site 1) :**

| Article | Prix catalogue | Stock initial |
|---|---|---|
| Ciment CIM II 50 kg (id 1) | 6 500 FCFA | 30 |
| Fer à béton 8 mm (id 2) | 3 500 FCFA | 35 |
| Clou 5 cm (id 3) | 800 FCFA | — |
| Article rare (id 4) | 2 000 FCFA | 1 |

* **Rôles impliqués :** `resp` (responsable), `magasin.compta` (caissier
  du comptoir — décision de fusion du rôle caissier, 2026-09-13),
  `magasin.stock` (contrôle négatif : jamais vendeur).
* **Partie automatisée :** `server/tests/test_campagne_fcfa_c5.py`
  (2 tests, rejoués par `verifier_tout.sh` comme toute la suite pytest).
* **Partie humaine :** section 4 — ne peut PAS être automatisée, à dater
  et signer sur PV par le propriétaire.

## 2. Scénarios normaux — « une journée de boutique »

Enchaînés dans `test_journee_boutique_fcfa` : les ventes se suivent sur la
même base et la cohérence d'ensemble (attendu de caisse vs ventes réelles
de la journée) n'est vérifiée qu'à la fin — c'est le propre d'une journée
réelle, que les tests unitaires isolés ne prouvent pas.

| # | Scénario métier | Montants FCFA | Vérifications |
|---|---|---|---|
| N1 | Le responsable crée la fiche client « Awa Diallo » (plafond 500 000) | — | 201, plafond enregistré |
| N2 | 08h15 — un client achète 2 sacs de ciment, paie espèces | 13 000 | 201, total exact, recette unique 13 000, **encaisseur = le caissier authentifié** (D9) |
| N3 | 09h00 — un maçon paie 1 fer à béton par Orange Money | 3 500 | 201, mode enregistré |
| N4 | 10h30 — vente **mixte** : 1 sac de ciment, 3 000 espèces + 3 500 Orange Money (D2) | 6 500 | mode `mixte`, composantes séparées en base, **une seule** recette du total, reçu PDF nommant « Espèces » et « Orange Money » |
| N5 | 11h45 — remise **exactement 10 %** sur 1 sac (D4) | remise 650, payé 5 850 | acceptée à un agent (la limite est le seuil) |
| N6 | 14h00 — Awa achète 1 sac **à crédit** | créance 6 500 | aucune recette, encours client 6 500 |
| N7 | 15h20 — le **responsable** annule la vente Orange Money (client revenu) | dépense 3 500 | contre-passation exacte, stock restitué, sortie de l'attendu, motif tracé |
| N8 | 18h00 — attendu de caisse du jour | espèces **21 850**, Orange Money **3 500** | jamais le total des recettes (5 850 + 13 000 + 6 500 + 3 500) : l'attendu suit les **composantes**, le journal les ventes — c'est le contrat D2 |
| N9 | 18h05 — clôture : le tiroir contient exactement 21 850 | écart 0 | clôture sans commentaire (écart nul) |
| N10 | Lendemain — Awa règle en deux fois : acompte 3 250 puis solde 3 250 | encours 3 250 → 0 | FIFO, refus d'un franc de trop (422) |
| N11 | Après règlement, la vente à crédit ne peut plus être annulée | — | 422 « règlement » — la boutique a l'argent |

## 3. Scénarios limites et erreurs

Dans `test_cas_limites_et_erreurs_fcfa` — chaque borne du métier, avec le
verdict serveur attendu :

| # | Cas | Verdict attendu |
|---|---|---|
| L1 | Remise ligne 10,01 % par un **agent** | **403** exige un responsable (décision D4 : « jusqu'à 10 % ») |
| L2 | Remise ligne 10,01 % par le **responsable** | 201, remise exacte 650,65 (arrondi arithmétique) |
| L3 | Remise **globale** 15 % par un agent (contournement ligne → vente) | **403** — même seuil sur les deux mécanismes |
| L4 | Remise négative (−100) | **422** — jamais une majoration déguisée |
| L5 | Mixte incohérent : 3 000 + 3 400 ≠ 6 500 | **422** citant le total attendu |
| L6 | Mode de paiement inconnu (« bitcoin ») | **422** — modes fermés : espèces, Orange Money, MTN MoMo, autre, crédit |
| L7 | Vente à crédit **sans client** | **422** message clair, pas d'erreur SQL brute |
| L8 | Crédit au-delà du plafond (13 000 > plafond 6 500) | **422**, aucune créance créée, encours intact |
| L9 | **Usurpation d'encaisseur** : champ `utilisateur_caisse_id` injecté dans le JSON | 201 mais **ignoré** — l'encaisseur reste le compte authentifié (D9, identifiant du jeton signé) |
| L10 | **Survente** : 99 sacs demandés, 30 en stock | **201** — comportement migration 011 : le client a payé, la vente passe, le stock tombe à 0 (jamais négatif), l'écart est tracé pour l'inventaire (lien C7) |
| L11 | Vente par un **agent stock** | **403** — aucune habilitation `ventes` (migration 008) |

## 4. Cas exigant une recette humaine (non automatisables)

| # | Cas | Pourquoi humain | Critère de réussite |
|---|---|---|---|
| H1 | **Impression du ticket** sur imprimante réelle (C5-03, P1) | le papier, la largeur du ruban thermique, la lisibilité réelle ne se simulent pas | ticket imprimé lisible : boutique, date, article, quantité, total, mode de paiement ; PV signé |
| H2 | **Reçu d'une vente mixte** relu sur papier | la mise en page PDF peut être correcte en octets et illisible à 58 mm de large | les deux modes et leurs montants lisibles sur le ticket |
| H3 | **Litige client** : un client conteste un prix affiché vs facturé | interaction humaine réelle | le vendeur retrouve le prix catalogue dans l'historique du reçu ; gestion signée |
| H4 | **Remise au-delà du seuil au comptoir** : un client négocie 15 % en caisse | la négociation est humaine ; l'automate prouve le refus serveur (L1/L3), pas la scène réelle | le caissier doit faire venir le responsable ; refus sinon, constaté sur l'écran réel |

## 5. Résultats d'exécution

Exécutée le **2026-10-23** sur `quincaillerie_lotb` (base dédiée Lot B),
venv du checkout principal, configuration éphémère `QF_CONFIG` (jamais
le vrai `config.ini`), après la baseline verte du run 4 — jamais en
parallèle d'une autre campagne sur la même base.

```
QF_TEST_DBNAME=quincaillerie_lotb QF_CONFIG=<ephemere> \
  python -m pytest -q tests/test_campagne_fcfa_c5.py
=> 2 passed, 0 failed (8,36 s)
```

| Exécution | Commande | Résultat |
|---|---|---|
| 2026-10-23 (1ʳᵉ passe, intégrée au run complet) | `pytest` complet incluant la campagne | 369 passed + 2 failed — la campagne seule en échec : préfixe de facturier « MAG- » exigé pour le site 1 (contrainte métier migration 020), mes numéros « JRN-… »/« LIM-… » refusés en 422 |
| 2026-10-23 (correctifs de la campagne : préfixes MAG-, mode mixte lu en base — absent de `ReponseVente` par conception, restitution stock = avant vente + 1 unité, « franc de trop » = 3 251 sur 3 250 restants) | `pytest -q tests/test_campagne_fcfa_c5.py` | **2 passed, 0 failed** |

Tous les N1–N11 et L1–L11 prouvés par exécution : espèces 13 000,
Orange Money 3 500, mixte 3 000+3 500 (UNE recette de 6 500, reçu PDF
nommant « mixte », « Espèces », « Orange Money »), remise exacte 10 %
→ 5 850 pour l'agent, 10,01 % → 403 agent / 5 849,35 pour le
responsable (650,65 de remise), remise globale 15 % → 403, crédit
6 500 (aucune recette, encours 6 500, plafond 500 000), annulation
responsable (dépense 3 500 contre-passée, stock restitué), attendu de
caisse **espèces 21 850 / Orange Money 3 500 / MTN 0 / autre 0**,
clôture exacte écart nul sans commentaire, règlements 3 250 + 3 250
en FIFO, refus de 3 251 sur 3 250 restants (422), vente à crédit
réglée non annulable (422), injection `utilisateur_caisse_id=999`
ignorée (l'encaisseur est le compte authentifié, D9), survente 99 sacs
→ 201, stock à 0, 1 écart tracé, agent stock 403 sur tout le parcours.

Aucun défaut applicatif découvert : les 4 échecs intermédiaires étaient
des défauts de MA campagne (non-conformité aux règles métier réelles,
elles-mêmes correctes et déjà testées) — chaque correctif a été
apporté au test, jamais au code applicatif.

## 6. Ce que cette campagne ne re-teste pas (déjà couvert ailleurs)

Évitée la duplication avec les suites dédiées, toutes vertes au cycle 75
et rejouées par `verifier_tout.sh` : unicité du numéro de facturier
(migration 020 + `01_protections.sql`), retour client / avoir /
remboursement et partage dette-espèces (8 tests `test_stock.py` + suite
Playwright `stock`), TVA et questions comptable (audit D5, cycle 75-F),
injections XSS sur le reçu (suite `echappement`), limitations de débit et
sessions (`test_authentification.py`, D6).
