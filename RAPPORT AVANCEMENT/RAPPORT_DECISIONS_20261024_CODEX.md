# Décisions du 24/10/2026 — rapport Codex et preuves

## Socle, coordination et livraison

- Main synchronisé et vérifié : **546fa957571b7d1c105440889376efacd442752b**. Il intègre #103 puis #104/#105/#106. Le socle annoncé au début était 7bebded ; cette évolution a été signalée.
- Code et preuves : commit contenant cette fiche (SHA final dans #110), branche `codex/decisions-integration-20261024`, PR **#110**. Créée depuis le nouveau main, avec report de nos seuls commits ; aucune branche Qoder/Claude modifiée, aucun force-push.
- #107 était le brouillon sur l'ancien socle : fermé comme remplacé par #110, **branche conservée**. Ce n'est pas une fusion.
- Le contrat et la réservation de **055** ont été publiés avant tout fichier de migration (46616ae / #107, puis repris dans #110). Coordination préalable dans #103/#105/#108.
- Les quatre décisions sont inscrites dans DECISIONS_PROPRIETAIRE.md, REGISTRE_ECARTS_100.md et loop-state.md, datées du 24/10, avec propriétaire métier, Codex technique, périmètre et état. La livraison reste en PR, sans clôture globale anticipée.
- Publication documentaire demandée : **#109**, commit initial b853793, merge local de origin/main e1bf3f6 et actualisation 2ad33fd. CI pytest/Playwright verte. Les huit fiches restent historiques ; D1 et C2-01 sont explicitement signalées comme désormais validées, Q1–Q6 restent au comptable, TTC acquis.

## Tableau de livraison

| Décision | Code concerné et correction | Tests | Preuves | PR | Statut de clôture |
|---|---|---|---|---|---|
| D-N1 | ventes.py : cumul des remises de ligne et globale, rapporté au catalogue pondéré par les quantités. Au-delà de 10 %, responsable authentifié obligatoire ; les champs d'approbation fournis par le client n'accordent aucun droit. 055 : approbations_remises et fonction SQL qui relit auteur et montants, trace atomique et immuable. Une majoration ne compense pas une remise pour contourner le plafond | 10 % exact, un centime au-dessus, entrées %, montant et prix négocié, pondération, fausse approbation, catalogue zéro, paiement incohérent sans trace orpheline ; responsable en rôle secondaire ; scénario navigateur de cumul refusé | pytest décisions ; SQL 055 ; vrai POST /ventes 201 pour rôle responsable secondaire, approbateur=utilisateur authentifié=4 ; Playwright vente | #110 | Correction technique vérifiée dans la PR ; intégration réservée au propriétaire |
| D-N5 | exploitation.py : preuve qualifiée seulement si complete=true ET verifiee=true, date avec fuseau non future ; échec explicite rejeté même si indicateurs contradictoires. Alerte à âge ≥3600 s. Une tentative échouée/incomplète/non vérifiée ne rajeunit pas la dernière preuve. Tableau de bord : bandeau, minuterie et actualisation continue | 3599/3600/3601 s, métadonnées manquantes ou fausses, dates invalides/futures/sans fuseau, preuve précédente, contradiction ECHEC+indicateurs vrais ; franchissement réel des 60 minutes sans rechargement | pytest décisions et exploitation ; preuve avant/après de la contradiction : faux succès âge 0 → périmé âge 7200 ; Playwright exploitation 18 contrôles, dont 4 ajoutés | #110 | Consommateur et alerte vérifiés ; **clôture opérationnelle non acquise**, producteur en quarantaine non qualifié |
| D1 | Contrôles des projections existantes API/SQL ; rapports.py corrige l'export d'un compte caissier+stock pour conserver l'union des prix de vente autorisés, sans prix d'achat/coût/marge. Deux projections exécutées chacune sous son rôle SQL permis, pas de GRANT de prix d'achat ajouté | Caissier simple/cumul stock, API directe et paramètres de rôle injectés, XLSX, refus des exports valorisés et fonctions réservées, SQL direct sur achat et historique des prix ; non-régression rôles/rapports | Tests décisions, SQL 02/055, Playwright rapports et rôles ; aucun achat exposé dans les parcours contrôlés | #110 | Périmètre caissier vérifié ; **droits comptable toujours réservés**, aucune extension décidée |
| C2-01 | 055 : verrouille_jusqua, verrou de ligne avant calcul, horloge après attente, 5 échecs consécutifs → 15 min ; essais pendant verrou sans incrément ni prolongation ; expiration puis succès/échec correctement recompté. Seed aligné sur a_decider=false ; limiteur HTTP et déverrouillage administratif autorisé conservés | Concurrence ×10, rupture de série par succès, expiration puis échec=1, autre compte indépendant, 429, refus de déverrouillage par agent ; charge complémentaire 20 refus concurrents et une authentification valide distincte | pytest décisions ; SQL 055 ; compteur=5 et échéance inchangés sous charge ; 20 refus, compte distinct accepté en 0,241 s sur cette machine (mesure locale, pas un engagement de performance) | #110 | Correction et protections ciblées vérifiées ; pas de prétention à une immunité totale au DoS |

## Exécutions et résultats

### CI complète sur le dernier SHA

Au moment de cette consignation, le dernier SHA publié 6d0ebe4 a pytest complet et 13 suites Playwright verts. Le commit contenant les ultimes protections réseau/cache doit repasser ces contrôles : résultats définitifs rattachés à son SHA dans le commentaire de #110, sans succès anticipé ici.

Commandes de ci.yml : `python -m pytest server/tests -q`, puis, dans le job indépendant Playwright avec serveur/PostgreSQL réels, `bash maquette/verification/executer_suites_reelles.sh` (13 suites).

La CI sur a734b1f avait donné **437 passed, 83 warnings, 528,23 s** ; son job Playwright avait échoué sur une attente hidden incorrecte du nouveau test. e266b58 corrige cette attente. Puis **6d0ebe4 donne 438 passed, 83 warnings, 490,25 s et 13/13 Playwright**, après ajout du refus de preuve contradictoire. La présente livraison ajoute les protections réseau/cache ci-dessous ; sa CI est à distinguer de ces résultats antérieurs.

### Contrôles locaux isolés

PostgreSQL 17 privé : 5560 pour tests/navigation, 5562 pour migration/charge, 5566 pour revue post-#103. Aucun rôle ni mot de passe modifié sur le serveur partagé. Ports HTTP sélectionnés libres ; un premier lancement sur 8030 occupé a été abandonné sans tuer son occupant.

- Avant correctifs, 23 échecs / 2 succès sur le nouveau fichier. Deux échecs étaient une URL inexistante du harnais D1, corrigée avant interprétation ; ne pas les compter comme fuites produit. Le défaut réel d'export cumulé a été reproduit ensuite.
- Passage ciblé intermédiaire : 25 réussis ; après ajout des cas supplémentaires et du reçu corrigé : **39 passed, 3 warnings, 68,30 s** sur a734b1f.
- Premier pytest complet local sur 3715366 : **425 passed / 1 failed** (ancien reçu enregistré par un caissier avec 700/6500 de remise). Ce scénario a été corrigé pour le faire approuver par le responsable ; son contrôle PDF n'a pas été supprimé.
- Nouveau cas de preuve contradictoire : **1 passed, 30 deselected**, 0,27 s ; il porte le fichier des décisions à 31 cas paramétrés. La reproduction avant/après utilise le helper exact de e266b58, puis le helper corrigé, sans modifier les fichiers pendant la mesure.
- SQL, préparation rechargée avant chaque suite : **01 protections 202/202**, **02 habilitations 55/55**, **03 concurrence 6/6**, **055 contrôles spécifiques OK**. Commandes `psql -v ON_ERROR_STOP=1 -f db/tests/<fichier>.sql` et `bash db/tests/03_concurrence.sh`. Sous Windows, un adaptateur local retire uniquement CR des sorties psql pour les comparaisons Bash, sans changer le code retour ni les requêtes.
- Playwright local : 12 suites vertes au passage groupé ; seule exploitation échouait sur le harnais `waitForSelector('[hidden]')` qui attendait par défaut une visibilité impossible. Attente explicite state=hidden corrigée, puis exploitation **18/18** au rejeu. Le passage groupé complet vert de CI constitue la preuve des 13 suites sur un seul SHA.
- Empreintes des sources sauvegardées avant/après les campagnes locales : aucune modification pendant chaque exécution. Les captures générées restent locales et ne figurent pas dans la PR.

### Migration 055

Exécution depuis une base 000–054 synthétique, puis 055 : succès. Un compte déjà bloqué reçoit une échéance bornée de 15 minutes. Inverse sans approbation : succès ; empreinte MD5 de pg_get_functiondef(verifier_connexion) identique à la version 053/054 antérieure. Réapplication et seconde invocation du migrateur : succès sans doublon. Contrôle de présence unique de 055 exécuté en SQL.

En présence d'une approbation synthétique, l'inverse est **refusée**, code psql 3 attendu. Contrôle suivant : approbation et ligne schema_migrations 055 toujours présentes. Une marche arrière ne détruit donc pas silencieusement le journal.

La mesure de charge complète ce contrôle : 20 connexions SQL simultanées visant un compte déjà verrouillé sont refusées, compteur et échéance inchangés ; une authentification correcte d'un autre compte est acceptée. Maximum observé pour le compte verrouillé : 0,120 s ; compte valide distinct : 0,241 s. Cela ne constitue pas une qualification de volumétrie de production.

## Derniers contrôles réseau, cache et atomicité

- Snapshot complet avant le commit de livraison : **41 passed, 3 warnings, 69,99 s**, puis **13/13 Playwright en une passe**, port HTTP privé 65216, PostgreSQL privé 5560. Contrôles SQL 01/02/03/055 également verts. Empreintes des sources inchangées pendant l'exécution (`decisions_navigation_20261024T080105Z`).
- Scénario adversarial ajouté au parcours d'exploitation : lecture de l'état maintenue en attente au franchissement des 60 minutes. Avant correction, la relecture annulait le délai et le bandeau n'apparaissait pas à temps ; reproduction en échec dans `decisions_exploitation_20261024T075901Z`. Après correction, l'échéance reste active pendant la lecture, le bandeau apparaît sans réponse réseau et sans rechargement. Ce contrôle fait partie des 18 contrôles d'exploitation du passage final.
- Les réponses interprétées portent `Cache-Control: no-store` et le navigateur demande une lecture sans cache. Le statut est non confirmé et visible avant la première réponse ; au retour de visibilité, l'échéance connue est contrôlée immédiatement. Test HTTP ajouté au fichier des décisions (désormais 32 cas paramétrés).
- Paiement incohérent créé **après** la trace d'approbation : trace observée dans la transaction, puis CheckViolation au COMMIT ; contrôle par une nouvelle connexion : zéro vente et zéro approbation correspondantes. Preuve `migration055_20261024T080939Z/atomicite_approbation.json`. Les tests de migration, charge et responsable secondaire ont aussi repassé dans cette exécution.

Le contrat de preuve D-N5 exige un horodatage avec fuseau daté de la sauvegarde elle-même et les deux booléens explicites de complétude et vérification. Une attestation précédente peut être fournie sous `derniere_sauvegarde_verifiee`, en conservant sa propre date ; un résultat ECHEC explicite la disqualifie. Le consommateur ne réalise pas ni ne présume la vérification du producteur.

## Revue post-#103 demandée : AVANT exécuté, APRÈS à venir

La PR qoder/correctifs-post-103 n'était pas ouverte au dernier relevé. Aucun verdict après correction n'est inventé. #108 est un audit distinct.

Sur les scripts exacts de main **546fa95**, sans les modifier :

1. Campagne EXE originale, outils/réseau/13 suites simulés dans un bac à sable : CREATE DATABASE échoue avec marqueur confirmé, mais code final **0**.
2. verifier_tout.sh original avec doubles : PGPORT demandé **5566**, environnement de son invocation pytest donnant le port administratif effectif **5433**.
3. Vrai jeton HTTP, cluster privé synthétique, dump direct pg_dump puis restauration par restaurer.ps1 original : déconnexion **204**, ancien jeton refusé sur source **401**, de nouveau accepté après restauration **200**, même clé de test.

Ces preuves AVANT sont publiées dans [le commentaire de #109](https://github.com/THED-1VU/quincaillerie-franck/pull/109#issuecomment-6381537697). À l'ouverture de la PR attendue : inspection de son diff, rejeu indépendant APRÈS sur son SHA et commentaire de verdict. Ne pas assimiler la revue de #103 à celle d'une future correction.

## Limites et clôture

- **Aucune fusion GitHub**, aucun push sur main, aucune suppression de branche/worktree. verif-integration conservé. Les fusions restent au propriétaire via Claude in Chrome.
- sauvegarder.ps1 est exclu des nouveaux worktrees ; ni exécuté ni restauré. Les dumps des seuls tests synthétiques proviennent directement de pg_dump, pas du script en quarantaine.
- Le consommateur D-N5 n'invente aucune vérification : le format historique du producteur, sans attestation complète/vérifiée, laisse une alerte. La preuve doit dater la sauvegarde elle-même, pas une consultation ni un nouvel essai échoué. L'intégration opérationnelle du producteur reste à qualifier hors quarantaine ; pas de GO sauvegarde réel.
- La règle 5/15 borne chaque verrou et résiste aux prolongations par essais durant le verrou. Un attaquant persistant peut encore provoquer de nouvelles séries après expiration ; la politique choisie ne supprime pas tout déni de service. Limiteur et journalisation restent nécessaires.
- D1 est vérifiée pour le caissier existant et son cumul stock ; aucun nouveau rôle comptable ni droit comptable n'est attribué. Le rôle responsable conserve ses droits autorisés.
- **Scores inchangés : C1 96 %, C2 90 %, C3 88 %.** Pas de 100 % global, pas de décision fiscale inventée : Q1–Q6 restent au comptable, la saisie TTC est acquise. Les anciens tableaux divergents ne sont pas réécrits silencieusement.
- Aucun import réel, aucune installation réelle, aucune production. Aucun cluster, dump, binaire ou capture ajouté à la PR.

Journaux et harnais conservés localement sous `_preuves_simulation_integration/` : `decisions_baseline_20261024T054735Z`, `decisions_complete_20261024T063257Z`, `decisions_navigation_20261024T072413Z`, `decisions_exploitation_20261024T073320Z`, `migration055_20261024T074008Z`, `post103_20261024T073503Z` et `etat_contradictoire_avant_apres.json`. Deux essais de harnais de migration ont été interrompus par l'encodage d'accents dans les arguments -c de psql.exe ; corrigés dans le harnais, sans modification de la migration. Les succès ultérieurs sont identifiés séparément.
