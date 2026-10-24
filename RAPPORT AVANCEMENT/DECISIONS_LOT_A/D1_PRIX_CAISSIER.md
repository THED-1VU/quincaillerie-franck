# D1 — Prix visibles par le caissier

> Fiche historique. **D1 a été validée le 24/10/2026** ; voir `../ACTUALISATION_FICHES_20261024.md`. Le statut ci-dessous décrit la préparation antérieure, pas une décision encore attendue.

**État : décision propriétaire ouverte.** Source : DECISIONS_PROPRIETAIRE.md D1 ; REGISTRE_ECARTS_100.md C3-01. Le caissier est déjà fusionné avec agent_comptabilite ; cette fusion n'est pas remise en question.

| Option | Conséquence | Effort indicatif après décision |
|---|---|---|
| A. Confirmer l'actuel : prix de vente et remises visibles, prix d'achat exclus | Valider précisément les champs et écrans ; conserver les protections API/SQL | 0,5–1 jour de vérification et traçabilité |
| B. Total seul, ou masquer certains détails | Définir les champs autorisés ; modifier projections API et interface, puis tester les accès directs et les cumuls | 2–5 jours selon écrans |
| C. Rôle caissier distinct | Réouvrir explicitement la fusion décidée ; nouvelle matrice et migrations éventuelles | À cadrer, au moins plusieurs jours |

**Recommandation soumise : A**, cohérente avec la fusion existante et la confidentialité des achats. L'API et SQL doivent rester autorités ; masquer du HTML ne suffit pas. Les comptes cumulant des rôles conservent l'union des droits explicitement autorisés, à vérifier pour les champs sensibles.

**Question exacte :** « Confirmez-vous que le compte caissier/agent comptabilité voit les prix de vente unitaires, le détail et les remises, sans jamais voir les prix d'achat ; sinon, quels champs précis doivent être masqués et sur quels écrans/documents ? »

**Clôture après réponse :** décision datée + matrice de champs + tests négatifs API/SQL et contrôles UI/cumuls. Aucun changement effectué. Efforts en jours de développement, estimatifs, hors attente propriétaire.
