# Q2 — Taux de TVA

**Décideur : comptable.** Dépend de Q1. Source : D5_AUDIT_TTC.md Q2 ; C1-02.

**Options à faire qualifier :** non-assujettissement/exonération précisée ; taux unique confirmé ; plusieurs taux ou exceptions explicités. Aucun taux n'est proposé comme vérité fiscale. Le défaut migration 0 et le seed synthétique 19,25 % ne valent pas validation.

**Recommandation de méthode :** obtenir le ou les taux exacts, le champ d'application et les dates d'effet, puis vérifier si le paramètre global actuel suffit.

**Impact technique :** le serveur extrait actuellement la TVA du total TTC avec le taux en base. Un taux unique relève du paramétrage ; plusieurs taux exigeraient un modèle et des calculs à cadrer. Préserver les valeurs fiscales mémorisées des ventes historiques. **Effort indicatif :** 0,5–1 jour pour taux unique et tests ; 3–7 jours ou davantage pour un modèle multi-taux, après spécification et revue des migrations.

**Question exacte :** « Selon le régime confirmé, quelle TVA exacte appliquer, à quels articles/opérations et depuis quelle date ; existe-t-il des exonérations ou plusieurs taux ? »

**Clôture :** réponse écrite et cas chiffrés approuvés, tests synthétiques des calculs et documents. Aucun taux réel modifié.
