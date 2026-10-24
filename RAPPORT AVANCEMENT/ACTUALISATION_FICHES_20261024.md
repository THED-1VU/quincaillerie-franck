# Publication des fiches historiques — 24/10/2026

Le propriétaire demande explicitement de publier la branche `codex/revue-103-decisions-c1-c3`, commit documentaire initial **b853793**, après `git merge --no-ff origin/main`.

Le 24/10, le fetch a révélé que main avait avancé au-delà du socle annoncé 7bebded : **546fa957571b7d1c105440889376efacd442752b**. Le merge local **e1bf3f61347763f827879ccc5aad96bfbef5c326** intègre ce HEAD, avec #104/#105/#106. Aucun merge GitHub effectué. Le message historique du merge mentionne le socle annoncé 7bebded ; le SHA effectivement intégré est celui indiqué ici.

## Statut des huit fiches

Les fiches sont conservées comme propositions antérieures aux décisions. Leur état historique « ouvert » ne fait plus autorité pour D1 et C2-01 :

- **D1 VALIDÉE le 24/10/2026** : caissier autorisé aux prix de vente TTC et montants ; prix d'achat, coûts et marges interdits, y compris API/export/indirect. Les droits du comptable restent réservés au propriétaire. Réalisation et preuves suivies dans #107 ; la décision seule ne clôture pas le critère technique.
- **C2-01 VALIDÉE le 24/10/2026** : cinq échecs consécutifs entraînent un verrou temporaire de **15 minutes** ; cela remplace l'ancien comportement de verrou permanent. Les fiches proposant de confirmer le verrou existant décrivent donc une option qui n'a pas été retenue. Réalisation et preuves suivies dans #107.
- **Q1–Q6 restent réservées au comptable**, sans valeur fiscale inventée. La saisie TTC reste acquise ; Q3 porte sur la confirmation fiscale et documentaire.
- **D-N1 et D-N5**, également validées le 24/10, sont suivies avec D1/C2-01 dans le contrat de #107. Aucun score modifié par cette publication documentaire.

## Revue indépendante à venir

Le rapport `REVUE_103_C1_C2_CODEX.md` est une revue historique au SHA #103 **54ffea5**. #103 a ensuite été fusionnée ; ce rapport n'est pas un verdict sur les correctifs à venir.

À l'ouverture de la PR **qoder/correctifs-post-103** : reproduire indépendamment avant/après les trois défauts (code retour EXE, port administratif pytest, révocation après restauration), puis commenter la PR avec SHA et preuves. Au dernier relevé GitHub de cette publication, cette PR n'était pas ouverte. Aucun verdict anticipé.

PR #108 (`cycle-78-decisions-proprietaire`) : audit distinct, ne pas la confondre avec la PR de correctifs demandée. Ne modifier aucune branche Qoder ou Claude Code. Conserver `verif-integration` ; sa suppression exige toujours l'accord propriétaire.
