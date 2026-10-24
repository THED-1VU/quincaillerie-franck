# C2-01 — Seuil de verrouillage

> Fiche historique. **C2-01 a été validée le 24/10/2026 : 5 échecs consécutifs, verrou temporaire de 15 minutes.** Voir `../ACTUALISATION_FICHES_20261024.md`. Le maintien du verrou exclusivement manuel proposé ci-dessous n'a pas été retenu.

**État : décision propriétaire ouverte.** Source : registre C2-01. Valeur actuelle : 5 tentatives, `a_decider=TRUE`. La session maximale de 480 minutes est déjà décidée et ne fait pas l'objet de cette fiche.

| Option | Conséquence | Effort indicatif après décision |
|---|---|---|
| A. Confirmer 5 | Conserver le mécanisme existant ; tracer la décision et lever le drapeau d'attente | 0,5–1 jour avec tests |
| B. Choisir un seuil inférieur | Verrouillage plus précoce, davantage d'interventions du responsable | 0,5–1 jour si seul le seuil change |
| C. Choisir un seuil supérieur | Davantage d'erreurs tolérées, davantage d'essais possibles par compte | 0,5–1 jour si seul le seuil change |

**Recommandation soumise : A**, pour confirmer un comportement déjà implémenté et testé. La limitation du débit par IP reste distincte du compteur par compte ; le déverrouillage actuel par responsable et le report de la 2FA ne sont pas modifiés. Toute demande de déverrouillage automatique serait un changement supplémentaire à cadrer.

**Question exacte :** « Confirmez-vous le verrouillage d'un compte après 5 échecs de connexion, avec déverrouillage par le responsable selon le parcours actuel ? Sinon, quel seuil entier retenez-vous ? »

**Clôture après réponse :** référence de décision, paramètre/seed cohérents, `a_decider=FALSE`, tests seuil−1/seuil, concurrence et déverrouillage. Aucune valeur administrative décidée par Codex. Estimation hors attente et évolution de mécanisme.
