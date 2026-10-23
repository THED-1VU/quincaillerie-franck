"""Audit autonome sur une base jetable, sans sauvegarde ni script en quarantaine.

Depuis le worktree : python "RAPPORT AVANCEMENT/cycles/verifier_lot_a.py".
Prérequis : environnement de développement et PostgreSQL local de test.
Les mots de passe ci-dessous sont exclusivement les valeurs publiques de test.
"""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import uuid
import time
import urllib.request

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT if (ROOT / "_pgdev/pgsql/bin/initdb.exe").exists() else ROOT.parent.parent
BIN = MAIN / "_pgdev/pgsql/bin"
DB = "quincaillerie_codex_a_" + uuid.uuid4().hex[:10]
NAVIGATEUR = "--navigateur" in sys.argv
PORT = int(os.environ.get("QF_AUDIT_PGPORT", "5548" if NAVIGATEUR else "5547"))
OUT = ROOT / ("_preuves_lot_a_browser" if NAVIGATEUR else
              "_preuves_lot_a_migrations" if "--migration-seule" in sys.argv else
              "_preuves_lot_a_temporaires" if "--temporaires" in sys.argv else
              "_preuves_lot_a_cible" if "--cible" in sys.argv else "_preuves_lot_a")
OUT.mkdir(exist_ok=True)
CONFIG = OUT / "config_test.ini"
ENV = dict(os.environ, PGHOST="127.0.0.1", PGPORT=str(PORT), PGUSER="postgres",
           PGPASSWORD="qf_dev_local", PGDATABASE=DB, QF_TEST_DBNAME=DB,
           QF_TEST_PGPORT=str(PORT),
           QF_CONFIG=str(CONFIG), PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
ADMIN = dict(host="127.0.0.1", port=PORT, dbname="postgres", user="postgres",
             password="qf_dev_local", connect_timeout=3)
RESULTS = {}


def run(label, command, *, required=True):
    with (OUT / (label + ".log")).open("w", encoding="utf-8") as log:
        try:
            result = subprocess.run([str(x) for x in command], cwd=ROOT, env=ENV,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=1200)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
    RESULTS[label] = code
    print(f"{label}: {code}", flush=True)
    if required and code:
        raise RuntimeError(f"Échec : {label}, voir le journal")


def psql(label, path, *, required=True, single=True):
    run(label, [BIN / "psql.exe", "-v", "ON_ERROR_STOP=1", *(["--single-transaction"] if single else []),
                "-q", "-f", path], required=required)


def sonder_paiements(database):
    result = {}
    for name, mode, component, parent_change in (
        ("sans_composante", "especes", False, False),
        ("mixte_un_seul_mode", "mixte", True, False),
        ("credit_avec_composante", "credit_client", True, False),
        ("total_parent_seul", "especes", True, True),
    ):
        with psycopg.connect(**{**ADMIN, "dbname": database}) as connection:
            try:
                ident = connection.execute(
                    "INSERT INTO ventes(site_id,utilisateur_id,statut,mode_paiement,utilisateur_caisse_id,"
                    "sous_total_ht,taux_tva,montant_tva,total_ttc,date_encaissement,numero_facturier,vendeur_id) "
                    "VALUES(1,1,'payee',%s,1,100,0,0,100,NOW(),'MAG-SONDE001',1) RETURNING id", (mode,)
                ).fetchone()[0]
                if component:
                    connection.execute("INSERT INTO ventes_paiements(vente_id,mode_paiement,montant) "
                                       "VALUES(%s,'especes',100)", (ident,))
                connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
                if parent_change:
                    connection.execute("UPDATE ventes SET total_ttc=101,sous_total_ht=101 WHERE id=%s", (ident,))
                result[name] = "ACCEPTE"
            except psycopg.errors.CheckViolation:
                result[name] = "REFUSE"
            finally:
                connection.rollback()
    return result


def verifier_upgrade_051():
    legacy = DB + "_legacy051"
    previous_database = ENV["PGDATABASE"]
    with psycopg.connect(**ADMIN, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(legacy)))
    ENV["PGDATABASE"] = legacy
    try:
        psql("legacy051_schema", ROOT / "QuincaillerieFranck_Test/creation_base_donnees.sql")
        for migration in migrations:
            if int(migration.name[:3]) <= 51:
                psql("legacy051_" + migration.stem, migration)
        psql("legacy051_seed", ROOT / "db/tests/00_jeu_essai.sql")
        with psycopg.connect(**{**ADMIN, "dbname": legacy}) as connection:
            ident = connection.execute("INSERT INTO ventes(site_id,utilisateur_id,statut,mode_paiement,sous_total_ht,taux_tva,montant_tva,total_ttc) "
                                       "VALUES(1,4,'en_attente','especes',0,0,0,0) RETURNING id").fetchone()[0]
            ident_pending = connection.execute("INSERT INTO ventes(site_id,utilisateur_id,statut,mode_paiement,sous_total_ht,taux_tva,montant_tva,total_ttc) "
                                              "VALUES(1,4,'en_attente','especes',100,0,0,100) RETURNING id").fetchone()[0]
        original = subprocess.check_output(["git", "show", "2dae406:db/migrations/052_paiements_mixtes.sql"], cwd=ROOT)
        initial_file = OUT / "052_initiale.sql"
        initial_file.write_bytes(original)
        psql("052_initiale_refuse_brouillon_zero", initial_file, required=False)
        assert RESULTS["052_initiale_refuse_brouillon_zero"] != 0
        RESULTS["052_initiale_refuse_brouillon_zero"] = 0  # défaut ancien reproduit
        psql("052_corrigee_depuis_051", ROOT / "db/migrations/052_paiements_mixtes.sql")
        with psycopg.connect(**{**ADMIN, "dbname": legacy}) as connection:
            assert connection.execute("SELECT count(*) FROM ventes WHERE id=%s", (ident,)).fetchone()[0] == 1
            assert connection.execute("SELECT count(*) FROM ventes_paiements WHERE vente_id=%s", (ident,)).fetchone()[0] == 0
            assert connection.execute("SELECT count(*) FROM ventes_paiements WHERE vente_id=%s", (ident_pending,)).fetchone()[0] == 0
        psql("052_inverse_sans_mixte", ROOT / "db/migrations/052_paiements_mixtes_inverse.sql")
        with psycopg.connect(**{**ADMIN, "dbname": legacy}) as connection:
            # Compatibilité avec une base déjà passée par l'ancien inverse.
            connection.execute("ALTER TABLE ventes RENAME CONSTRAINT ventes_mode_paiement_check TO ventes_mode_paiement")
        psql("052_reapplication_apres_inverse", ROOT / "db/migrations/052_paiements_mixtes.sql")
        with psycopg.connect(**{**ADMIN, "dbname": legacy}) as connection:
            ident = connection.execute("INSERT INTO ventes(site_id,utilisateur_id,statut,mode_paiement,utilisateur_caisse_id,"
                "sous_total_ht,taux_tva,montant_tva,total_ttc,date_encaissement,numero_facturier,vendeur_id) "
                "VALUES(1,1,'payee','mixte',1,100,0,0,100,NOW(),'MAG-AR052',1) RETURNING id").fetchone()[0]
            connection.execute("INSERT INTO ventes_paiements(vente_id,mode_paiement,montant) "
                               "VALUES(%s,'especes',50),(%s,'orange_money',50)", (ident, ident))
        psql("052_inverse_mixte_refuse_atomiquement", ROOT / "db/migrations/052_paiements_mixtes_inverse.sql", required=False)
        assert RESULTS["052_inverse_mixte_refuse_atomiquement"] != 0
        RESULTS["052_inverse_mixte_refuse_atomiquement"] = 0
        with psycopg.connect(**{**ADMIN, "dbname": legacy}) as connection:
            assert connection.execute("SELECT count(*) FROM ventes_paiements WHERE vente_id=%s", (ident,)).fetchone()[0] == 2
    finally:
        ENV["PGDATABASE"] = previous_database
        with psycopg.connect(**ADMIN, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(legacy)))


def sonder_masquage_table(database, ancien=False):
    with psycopg.connect(**{**ADMIN, "dbname": database}) as connection:
        try:
            if ancien:
                source = subprocess.check_output(["git", "show", "83a4172:db/migrations/054_integrite_paiements.sql"], cwd=ROOT).decode("utf-8")
                functions = re.findall(r"CREATE FUNCTION .*?\$\$;", source, flags=re.S)
                assert len(functions) == 3
                for function in functions:
                    connection.execute(function.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1))
                for signature in ("verrouiller_vente_paiement()", "verifier_integrite_paiements(INTEGER)", "controler_paiements_complets()"):
                    connection.execute("ALTER FUNCTION public." + signature + " RESET ALL")
            connection.execute("SET LOCAL ROLE qf_agent_comptabilite")
            connection.execute("SELECT set_config('qf.site_id','1',TRUE)")
            ident = connection.execute("INSERT INTO public.ventes(site_id,utilisateur_id,statut,mode_paiement,utilisateur_caisse_id,"
                "sous_total_ht,taux_tva,montant_tva,total_ttc,date_encaissement,numero_facturier,vendeur_id) "
                "VALUES(1,4,'payee','mixte',4,100,0,0,100,NOW(),'MAG-TEMP002',1) RETURNING id").fetchone()[0]
            connection.execute("CREATE TEMP TABLE ventes (LIKE public.ventes)")
            connection.execute("INSERT INTO pg_temp.ventes SELECT * FROM public.ventes WHERE id=%s", (ident,))
            connection.execute("UPDATE pg_temp.ventes SET statut='en_attente'")
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            return "ACCEPTE"
        except psycopg.errors.CheckViolation:
            return "REFUSE"
        finally:
            connection.rollback()


CONFIG.write_text("[database]\nhost=127.0.0.1\nport=" + str(PORT) + "\ndbname=" + DB +
                  "\nuser=qf_app\npassword=qf_app_dev_local\n[api]\nsecret_key=" +
                  "0" * 64 + "\nduree_session_minutes=480\n", encoding="utf-8")
CLUSTER = OUT / ("pgdata_" + uuid.uuid4().hex[:8])
run("initdb", [BIN / "initdb.exe", "-D", CLUSTER, "-U", "postgres", "-A", "trust", "-E", "UTF8", "--no-locale"])
run("pg_start", [BIN / "pg_ctl.exe", "-D", CLUSTER, "-l", OUT / "postgres.log", "-o",
                 f"-p {PORT} -h 127.0.0.1", "-w", "start"])
with psycopg.connect(**ADMIN, autocommit=True) as connection:
    connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(DB)))
print("Base isolée : " + DB, flush=True)
try:
    psql("schema_origine", ROOT / "QuincaillerieFranck_Test/creation_base_donnees.sql")
    migrations = sorted(p for p in (ROOT / "db/migrations").glob("[0-9][0-9][0-9]_*.sql")
                        if not p.name.endswith("_inverse.sql"))
    (OUT / "inventaire_migrations.json").write_text(
        json.dumps([p.name for p in migrations], ensure_ascii=False, indent=2), encoding="utf-8")
    for migration in migrations:
        psql(migration.stem, migration)
    with psycopg.connect(**{**ADMIN, "dbname": DB}, autocommit=True) as connection:
        connection.execute("ALTER ROLE qf_app PASSWORD 'qf_app_dev_local'")
    for test in (() if NAVIGATEUR else ("01_protections", "02_habilitations")):
        psql("seed_" + test, ROOT / "db/tests/00_jeu_essai.sql")
        psql(test, ROOT / ("db/tests/" + test + ".sql"), required=False, single=False)
    if NAVIGATEUR:
        psql("seed_browser", ROOT / "db/tests/00_jeu_essai.sql")
        ENV["PGDATABASE_PISTE"] = DB
        ENV["SERVEUR_URL"] = "http://127.0.0.1:8027"
        with (OUT / "serveur.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen([sys.executable, "-B", "-m", "uvicorn", "app.main:app",
                                       "--app-dir", "server", "--host", "127.0.0.1", "--port", "8027"],
                                      cwd=ROOT, env=ENV, stdout=log, stderr=log,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                for attempt in range(50):
                    try:
                        urllib.request.urlopen(ENV["SERVEUR_URL"] + "/sante", timeout=1).close()
                        break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError("Le serveur de test s'est arrêté")
                        time.sleep(0.2)
                else:
                    raise RuntimeError("Le serveur de test ne répond pas")
                for suite, filename in (("comptes", "comptes-reel"), ("roles", "roles"),
                                        ("cablage", "cablage"), ("vente", "vente-reelle")):
                    source = ROOT / "maquette/verification" / ("verifier-" + filename + ".mjs")
                    temporary = source.with_name("_codex_" + source.name)
                    content = source.read_text(encoding="utf-8").replace('"5433"', '"' + str(PORT) + '"')
                    content = content.replace('resolve(ICI, "..", "captures"',
                                              'resolve(ICI, "..", "..", "_preuves_lot_a_browser", "captures"')
                    temporary.write_text(content, encoding="utf-8")
                    try:
                        run("playwright_" + suite, ["node", temporary], required=False)
                    finally:
                        temporary.unlink(missing_ok=True)
            finally:
                server.terminate()
                server.wait(timeout=15)
    else:
        psql("seed_concurrence", ROOT / "db/tests/00_jeu_essai.sql")
        bash = "C:/Program Files/Git/bin/bash.exe"
        ENV["PSQL"] = str(BIN / "psql.exe").replace("\\", "/")
        run("03_concurrence", [bash, "db/tests/03_concurrence.sh"], required=False)
        cibles = (["server/tests/test_integrite_paiements_sql.py", "server/tests/test_paiements_mixtes_d2.py",
                   "server/tests/test_sessions_serveur.py", "server/tests/test_session_d6.py",
                   "server/tests/test_changement_mdp_force.py", "server/tests/test_cumul_roles.py"]
                  if "--cible" in sys.argv else ["server/tests"])
        if "--temporaires" in sys.argv:
            cibles = ["server/tests/test_exploitation_etat.py",
                      "server/tests/test_securite.py::test_config_refuse_le_compte_superutilisateur",
                      "server/tests/test_securite.py::test_config_refuse_la_cle_secrete_exemple"]
        if "--migration-seule" not in sys.argv:
            run("pytest_complet", [sys.executable, "-B", "-m", "pytest", *cibles, "-q",
                            "--tb=short", "-p", "no:cacheprovider", "--basetemp",
                            OUT / ("pytest_" + uuid.uuid4().hex[:8])], required=False)
        # Restauration logique directe : aucun outil de sauvegarde en quarantaine.
        run("dump_test", [BIN / "pg_dump.exe", "-Fc", "-f", OUT / "donnees_synthetiques.dump"])
        restored = DB + "_restauree"
        with psycopg.connect(**ADMIN, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(restored)))
        run("restore_test", [BIN / "pg_restore.exe", "-d", restored, "--exit-on-error", OUT / "donnees_synthetiques.dump"])
        hashes = {}
        for database in (DB, restored):
            with psycopg.connect(**{**ADMIN, "dbname": database}) as connection:
                hashes[database] = {}
                for table in ("utilisateurs", "utilisateurs_roles", "stocks_sites", "ventes", "ventes_paiements", "transactions"):
                    hashes[database][table] = connection.execute(sql.SQL(
                        "SELECT count(*),md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'')) FROM {} t"
                    ).format(sql.Identifier(table))).fetchone()
        assert hashes[DB] == hashes[restored], "La restauration diffère de sa source"
        (OUT / "reprise_empreintes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
        ENV["PGDATABASE"] = restored
        for version in ("054_integrite_paiements", "053_sessions_serveur"):
            psql("retour_" + version, ROOT / "db/migrations" / (version + "_inverse.sql"))
        avant = sonder_paiements(restored)
        with psycopg.connect(**{**ADMIN, "dbname": restored}) as connection:
            connection.execute("DELETE FROM schema_migrations WHERE version='051'")
        for label, command in (
            ("refus_historique_incomplet_ps", ["powershell.exe", "-NoProfile", "-File", "db/outils/migrer.ps1", "appliquer"]),
            ("refus_historique_incomplet_bash", ["C:/Program Files/Git/bin/bash.exe", "db/outils/migrer.sh", "appliquer"]),
        ):
            run(label, command, required=False)
            assert RESULTS[label] != 0, "Un historique incomplet ne doit pas être accepté"
            RESULTS[label] = 0  # refus attendu et vérifié ; journal brut conservé
        with psycopg.connect(**{**ADMIN, "dbname": restored}) as connection:
            connection.execute("INSERT INTO schema_migrations(version,nom) VALUES('051','seuil_remise_valide')")
        run("upgrade_depuis_052_powershell", ["powershell.exe", "-NoProfile", "-File", "db/outils/migrer.ps1", "appliquer"])
        run("reapplication_bash", ["C:/Program Files/Git/bin/bash.exe", "db/outils/migrer.sh", "appliquer"])
        apres = sonder_paiements(restored)
        (OUT / "paiements_avant_apres.json").write_text(json.dumps({"052": avant, "054": apres}, indent=2), encoding="utf-8")
        assert set(avant.values()) == {"ACCEPTE"} and set(apres.values()) == {"REFUSE"}
        masquage = {"83a4172": sonder_masquage_table(restored, ancien=True),
                    "corrige": sonder_masquage_table(restored)}
        (OUT / "masquage_table_avant_apres.json").write_text(json.dumps(masquage, indent=2), encoding="utf-8")
        assert masquage == {"83a4172": "ACCEPTE", "corrige": "REFUSE"}
        with psycopg.connect(**{**ADMIN, "dbname": restored}) as connection:
            assert connection.execute("SELECT count(*) FROM schema_migrations WHERE version IN ('053','054')").fetchone()[0] == 2
        RESULTS["reprise_et_upgrade"] = 0
        verifier_upgrade_051()
        with psycopg.connect(**ADMIN, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(restored)))
finally:
    (OUT / "resultats.json").write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    with psycopg.connect(**ADMIN, autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(DB)))
    CONFIG.unlink(missing_ok=True)
    run("pg_stop", [BIN / "pg_ctl.exe", "-D", CLUSTER, "-m", "fast", "-w", "stop"])
    print("Base jetable et configuration supprimées ; journaux conservés.", flush=True)
sys.exit(1 if any(RESULTS.values()) else 0)
