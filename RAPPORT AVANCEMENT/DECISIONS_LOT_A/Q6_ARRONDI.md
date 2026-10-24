# Q6 — Arrondis au franc CFA

**Décideur : comptable.** Source : D5_AUDIT_TTC.md Q6 ; C1-02.

**État technique actuel :** TVA extraite du total TTC, arrondie au franc avec ROUND_HALF_UP ; HT obtenu par différence. Ne pas confondre ce calcul fiscal avec une obligation non décidée d'arrondir chaque prix ou remise de vente au franc entier.

**Options à confirmer :** méthode actuelle sur le total ; méthode différente spécifiée ; arrondis par ligne avec règle d'allocation des écarts. La validité fiscale de ces options n'est pas décidée par Codex.

**Recommandation de méthode :** soumettre au comptable les cas demi-franc, remise fractionnaire, plusieurs lignes, remboursement et somme des composantes d'un paiement mixte ; exiger une règle complète et des exemples chiffrés attendus.

**Impact technique :** centraliser la règle retenue, assurer HT+TVA=TTC, somme des composantes=TTC et cohérence reçu/annulation/remboursement. Les contraintes 054 restent à respecter. Aucun recalcul rétroactif implicite. **Effort indicatif :** 0,5–1 jour pour confirmer et tester l'actuel ; 2–4 jours pour une autre méthode ou une allocation par ligne, à affiner avec Q4.

**Question exacte :** « Confirmez-vous ROUND_HALF_UP au franc sur la TVA extraite du total TTC ; sinon, quelle méthode exacte, à quelle étape, et comment répartir les écarts entre lignes, paiements et remboursements ? Merci de valider des exemples chiffrés. »

**Clôture :** règle écrite et exemples approuvés, tests synthétiques des bornes et réconciliations. Aucun choix fiscal ni modification de calcul effectué.
