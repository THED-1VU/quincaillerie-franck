# Contrat partagé — décisions du 24/10/2026

Socle : origin/main `7bebdeddc67d00d11b750238cca42b6d7154a21d` (#103 fusionnée).
Branche Codex : `codex/decisions-proprietaire-20261024`.

Le propriétaire autorise explicitement les quatre corrections, leurs tests et des PR coordonnées. Ce document est publié avant toute modification des fichiers transversaux de Qoder.

| Décision | Portée / responsable de réalisation | Interface et invariant attendus | Statut initial |
|---|---|---|---|
| D-N1 | Codex, coordination Qoder pour ventes.py / vente.html | POST /ventes : remise effective totale rapportée au total catalogue pondéré par quantités, toutes remises incluses ; ≤10 % sans approbation, >10 % uniquement sous identité responsable authentifiée ; preuve d'approbation liée à la vente, atomique | VALIDÉE propriétaire 24/10 ; conformité à reproduire/tester |
| D-N5 | Codex, coordination Qoder pour exploitation.py et tableau-bord.html | GET /exploitation/etat-sauvegarde : succès frais uniquement sur preuve complète ET vérifiée ; alerte à âge ≥3600 s ; échec/incomplet/non vérifié ne rajeunit pas la dernière preuve ; actualisation du bandeau sans rechargement | VALIDÉE propriétaire 24/10 ; conformité à reproduire/tester |
| D1 | Codex ; droits comptable réservés au propriétaire | Caissier = compte agent_comptabilite existant : vente TTC autorisée, achats/coûts/marges exclus des API/exports/SQL et accès indirects contrôlés ; aucun nouveau droit comptable | VALIDÉE propriétaire 24/10 ; audit et tests nécessaires |
| C2-01 | Codex / schéma et auth | 5 échecs consécutifs, verrou SQL atomique de 15 min à partir du cinquième ; essais pendant verrou sans prolongation ; succès remet le compteur à zéro ; limites HTTP conservées | VALIDÉE propriétaire 24/10 ; conformité à reproduire/tester |

## Réservation et coordination

- **055 réservée à Codex**, avant création, dans RAPPORT AVANCEMENT/loop-state.md : verrouillage temporaire, audit des approbations, protections associées strictement nécessaires. Aucun autre agent ne doit utiliser ce numéro.
- Tables prévues : utilisateurs (date de fin de verrou), journal d'approbation des remises lié à ventes ; fonctions d'authentification conservant leur signature. Migration réversible et historique 000–054 non réécrit.
- Approbation de remise : le responsable enregistre la vente lui-même, sous son jeton existant. Aucun champ client « approuvé » ni mot de passe de responsable envoyé dans un panier. Traçabilité SQL du responsable, du montant catalogue, du montant final et de la décision.
- Sauvegardes : le producteur en quarantaine est exclu. Le consommateur refuse tout ancien SUCCES sans preuve explicite de complétude et vérification. Une interface de preuve documentée sera testée avec des fichiers synthétiques ; aucune affirmation de fonctionnement du producteur réel.
- Possibles chevauchements : PR #105 sur ventes.py ; ne pas remplacer son correctif de concurrence ni le fusionner sans autorisation. Revalidation de compatibilité requise avant fusion.
- Tests uniquement sur **cluster privé** PostgreSQL, bases/ports et captures séparés ; aucun changement de mot de passe sur le cluster partagé.
- Pas de score relevé par cette décision, pas d'import réel, de production, de fusion, ni d'exécution/restauration de sauvegarder.ps1. `verif-integration` conservé.
