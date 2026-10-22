# Checklist d'installation — Akuma / Quincaillerie Franck

Recette vierge à imprimer et remplir **sur le poste serveur**, le jour de
l'installation réelle. Chaque ligne a un résultat attendu vérifiable ; la
checklist signée fait partie de la preuve d'installation. Référence complète
des étapes : `INSTALLATION/README.md`.

Poste : _______________________  Date : ____________  Opérateur : ______________

## A. Fichiers

- [ ] A1. `C:\QuincaillerieFranck\Akuma.exe` présent (depuis `server\fabrication\dist\`)
- [ ] A2. `config.example.ini` présent à côté de l'exe
- [ ] A3. `db\migrations\` : 100 fichiers `.sql` (commande : `dir db\migrations\*.sql | measure`)
- [ ] A4. `db\outils\` : scripts `.ps1` présents (sauvegarder, restaurer, planifier, enregistrer_service_pg, migrer, creer_compte_responsable)
- [ ] A5. `QuincaillerieFranck_Test\creation_base_donnees.sql` présent
- [ ] A6. `_pgdev\pgsql\bin\psql.exe` présent (~1 Go copiés)

## B. PostgreSQL

- [ ] B1. `demarrer_pg.ps1 -Port 5432` exécuté → `accepting connections`
- [ ] B2. (admin) `enregistrer_service_pg.ps1 -PgPort 5432` → « enregistre, demarre et repond »
- [ ] B3. `Get-Service QuincaillerieFranck_PostgreSQL` → `Running`, `StartType: Automatic`
- [ ] B4. Base créée : `psql -d postgres -c "CREATE DATABASE quincaillerie;"`
- [ ] B5. Schéma d'origine appliqué sans erreur (`creation_base_donnees.sql`)
- [ ] B6. `migrer.ps1 appliquer` → « Termine » + **49 lignes** listées
- [ ] B7. `migrer.ps1 etat` → versions 000 à 049, toutes datées

## C. Configuration applicative

- [ ] C1. `config.ini` créé depuis l'exemple, `[database]` renseigné (host 127.0.0.1, port 5432, dbname quincaillerie, user qf_app)
- [ ] C2. `secret_key` générée (64 caractères hex, jamais la valeur d'exemple)
- [ ] C3. Mot de passe `qf_app` posé (`definir_mot_de_passe_app.sql`) et identique dans `config.ini`
- [ ] C4. Premier compte responsable créé (`creer_compte_responsable.ps1`), identifiant noté : ______________

## D. Lancement

- [ ] D1. Double-clic `Akuma.exe` → console ouverte, navigateur plein écran sur la connexion
- [ ] D2. `http://127.0.0.1:8000/sante` → `{"etat":"ok","base":"joignable"}`
- [ ] D3. Connexion réussie avec le compte responsable (changement de mot de passe imposé)
- [ ] D4. Pare-feu : port 8000 autorisé en privé ; téléphone test sur `http://<IP>:8000/app/connexion.html` → écran de connexion affiché
- [ ] D5. Tableau de bord : carte « Dernière sauvegarde » visible (même « aucune »)

## E. Sauvegarde (administrateur)

- [ ] E1. Exclusions antivirus posées (`postgres.exe`, `_pgdev\`, `db\outils\sauvegarder.ps1`)
- [ ] E2. `phrase_chiffrement.txt` créé, protégé `icacls`, copie papier hors boutique
- [ ] E3. Sauvegarde de test manuelle → 3 fichiers `.enc` produits, `.dump.enc` > 0 o
- [ ] E4. Restauration de test vers base `quincaillerie_verification` → réussie (puis base de vérification supprimée)
- [ ] E5. `planifier_sauvegarde.ps1 -CompteSysteme` → tâche enregistrée
- [ ] E6. `Start-ScheduledTask` → `dernier_etat_sauvegarde.json` daté, `"resultat":"SUCCES"`
- [ ] E7. Carte « Dernière sauvegarde » du tableau de bord à jour après l'essai

## F. Fin

- [ ] F1. Mot de passe `postgres` changé (noté hors ligne)
- [ ] F2. Historique de la console PowerShell fermé/supprimé (mots de passe)
- [ ] F3. Cette checklist signée : ______________  — copie remise au responsable
- [ ] F4. Import du stock et des créances : **non réalisé** (protocole distinct, autorisation dédiée requise)

> **Rappel.** Toute opération sur des données réelles — import du stock,
> créances, mise en service — exige l'autorisation explicite du propriétaire
> et suit un protocole écrit à part. Cette checklist couvre l'installation
> technique uniquement.
