# Q1 — Régime fiscal réel

**Décideur : comptable, réponse transmise par le propriétaire.** Source : D5_AUDIT_TTC.md Q1 ; C1-02.

**Options à faire qualifier :** impôt libératoire, simplifié, réel/assujetti TVA, ou autre qualification applicable explicitée par le comptable. Ces libellés reproduisent la question existante et ne constituent pas une qualification fiscale par Codex.

**Recommandation de méthode :** obtenir une confirmation écrite du régime et de sa date d'effet ; ne pas déduire le régime des valeurs du seed. Le taux de test 19,25 % et `regime_fiscal=reel` ne sont pas des preuves de la situation réelle.

**Impact technique :** renseigner le paramètre régime avec sa référence et vérifier les règles/mentions demandées avec Q2–Q6. Préserver les ventes historiques. **Effort indicatif :** 0,5–1 jour si paramétrage seul ; chiffrage complémentaire si de nouveaux traitements sont exigés.

**Question exacte :** « Quel est le régime fiscal applicable à la quincaillerie, avec assujettissement ou non à la TVA, et à compter de quelle date ? »

**Clôture :** réponse comptable écrite, traduction technique relue et tests synthétiques. Aucun choix, import réel ni changement de paramètre effectué.
