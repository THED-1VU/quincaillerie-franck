"""Sondes d'exécution des scripts d'outillage (revue #103, réserves A et B).

Aucune connexion PostgreSQL réelle ni EXE réel : psql, npm, curl, netstat,
tasklist, taskkill, timeout et Python sont doublés dans un bac à sable. Les
scripts testés sont les fichiers RÉELS du dépôt, copiés tels quels.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")
if BASH is None and Path(r"C:\Program Files\Git\bin\bash.exe").exists():
    BASH = r"C:\Program Files\Git\bin\bash.exe"

besoin_bash = pytest.mark.skipif(BASH is None, reason="bash requis pour sonder les scripts")


def _ecrire_executable(chemin: Path, contenu: str) -> None:
    chemin.write_text(contenu, encoding="utf-8", newline="\n")
    chemin.chmod(chemin.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _lancer(script: Path, *arguments: str, env: dict | None = None,
            cwd: Path | None = None) -> subprocess.CompletedProcess:
    environnement = dict(os.environ)
    if env:
        environnement.update(env)
    return subprocess.run(
        [BASH, str(script), *arguments],
        env=environnement,
        cwd=str(cwd or RACINE),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


# ---------------------------------------------------------------------------
# A — campagne EXE : tout échec de préparation doit donner un code non nul
# ---------------------------------------------------------------------------
def _psql_simule(motif_echec: str | None) -> str:
    echec = ""
    if motif_echec:
        echec = f'  *"{motif_echec}"*) echo "ECHEC_PREPARATION_SIMULE" >&2; exit 1 ;;\n'
    return (
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "$QF_JOURNAL_PSQL"\n'
        'if [ -n "${QF_ECHEC_DROP_SECOND:-}" ] && [[ "$*" == *"DROP DATABASE"* ]]; then\n'
        '  n=$(cat "$QF_COMPTEUR_DROP" 2>/dev/null || echo 0)\n'
        '  n=$((n + 1)); echo "$n" > "$QF_COMPTEUR_DROP"\n'
        '  if [ "$n" -ge 2 ]; then echo "ECHEC_NETTOYAGE_SIMULE" >> "$QF_JOURNAL_PSQL"; exit 1; fi\n'
        "fi\n"
        'case "$*" in\n'
        + echec
        + "esac\n"
        "exit 0\n"
    )


def _bac_campagne(tmp_path: Path, motif_echec: str | None) -> tuple[Path, Path, Path]:
    box = tmp_path / "bac_campagne"
    for dossier in ("db/outils", "_pgdev/pgsql/bin", "server/fabrication/dist",
                    "maquette/verification", "QuincaillerieFranck_Test", "db/tests"):
        (box / dossier).mkdir(parents=True)
    shutil.copy2(RACINE / "db/outils/campagne_exe_lotb.sh",
                 box / "db/outils/campagne_exe_lotb.sh")
    (box / "db/outils/migrer.sh").write_text("exit 0\n", encoding="utf-8", newline="\n")
    (box / "db/outils/definir_mot_de_passe_app.sql").write_text(
        "-- simulé\n", encoding="utf-8", newline="\n")
    (box / "db/tests/00_jeu_essai.sql").write_text("-- simulé\n", encoding="utf-8")
    (box / "QuincaillerieFranck_Test/creation_base_donnees.sql").write_text(
        "-- simulé\n", encoding="utf-8")
    _ecrire_executable(box / "server/fabrication/dist/Akuma.exe",
                       "#!/usr/bin/env bash\nexit 0\n")
    _ecrire_executable(box / "_pgdev/pgsql/bin/psql.exe", _psql_simule(motif_echec))

    hooks = tmp_path / "doubles.sh"
    hooks.write_text(
        "netstat(){ :; }\n"
        "tasklist(){ :; }\n"
        "taskkill(){ :; }\n"
        "sleep(){ :; }\n"
        "curl() {\n"
        '  if [ -n "${QF_CURL_ECHEC:-}" ]; then return 1; fi\n'
        "  return 0\n"
        "}\n"
        'timeout(){ shift; "$@"; }\n'
        "npm() {\n"
        '  if [ -n "${QF_NPM_ECHEC:-}" ] && [[ "$*" == *"$QF_NPM_ECHEC"* ]]; then\n'
        "    return 1\n"
        "  fi\n"
        "  return 0\n"
        "}\n",
        encoding="utf-8", newline="\n",
    )
    journal = tmp_path / "journal_psql.log"
    return box, hooks, journal


def _env_campagne(box: Path, hooks: Path, journal: Path, **extra: str) -> dict:
    # PSQL explicite : sans lui, la campagne hérite du PSQL réel exporté par
    # verifier_tout.sh et le bac à sable interroge la vraie instance.
    return {"BASH_ENV": str(hooks), "QF_JOURNAL_PSQL": str(journal),
            "PSQL": str(box / "_pgdev/pgsql/bin/psql.exe"), **extra}


@besoin_bash
def test_campagne_exe_preparation_en_echec_code_non_nul(tmp_path):
    """R1 : CREATE DATABASE échoue, les 13 suites simulées passent — code 0 avant."""
    box, hooks, journal = _bac_campagne(tmp_path, "CREATE DATABASE")
    resultat = _lancer(box / "db/outils/campagne_exe_lotb.sh",
                       env=_env_campagne(box, hooks, journal),
                       cwd=box)
    assert resultat.returncode != 0, resultat.stdout
    assert "ECHEC_PREPARATION_SIMULE" in resultat.stdout
    assert "Campagne interrompue" in resultat.stdout
    lignes = journal.read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 2, lignes  # DROP + CREATE, puis arrêt : aucune suite
    assert any("CREATE DATABASE" in ligne for ligne in lignes)


@besoin_bash
def test_campagne_exe_echec_apres_creation_supprime_la_base(tmp_path):
    """R1 : le nettoyage doit couvrir les sorties anticipées, pas seulement la fin."""
    box, hooks, journal = _bac_campagne(tmp_path, "creation_base_donnees.sql")
    resultat = _lancer(box / "db/outils/campagne_exe_lotb.sh",
                       env=_env_campagne(box, hooks, journal),
                       cwd=box)
    assert resultat.returncode != 0, resultat.stdout
    lignes = journal.read_text(encoding="utf-8").splitlines()
    assert sum("DROP DATABASE" in ligne for ligne in lignes) == 2, lignes
    assert any("CREATE DATABASE" in ligne for ligne in lignes)


@besoin_bash
def test_campagne_exe_lancement_muet_code_non_nul(tmp_path):
    """R1 : un EXE qui ne repond jamais doit interrompre la campagne et nettoyer."""
    box, hooks, journal = _bac_campagne(tmp_path, None)
    resultat = _lancer(box / "db/outils/campagne_exe_lotb.sh",
                       env=_env_campagne(box, hooks, journal, QF_CURL_ECHEC="1"),
                       cwd=box)
    assert resultat.returncode != 0, resultat.stdout
    assert "n'a jamais répondu" in resultat.stdout
    assert "BILAN" not in resultat.stdout
    lignes = journal.read_text(encoding="utf-8").splitlines()
    assert sum("DROP DATABASE" in ligne for ligne in lignes) == 2, lignes
    assert any("CREATE DATABASE" in ligne for ligne in lignes)


@besoin_bash
def test_campagne_exe_echec_nettoyage_code_non_nul(tmp_path):
    """Un nettoyage impossible doit faire échouer la campagne, pas seulement s'afficher."""
    box, hooks, journal = _bac_campagne(tmp_path, None)
    resultat = _lancer(box / "db/outils/campagne_exe_lotb.sh",
                       env=_env_campagne(box, hooks, journal,
                                         QF_ECHEC_DROP_SECOND="1",
                                         QF_COMPTEUR_DROP=str(tmp_path / "compteur_drop")),
                       cwd=box)
    assert resultat.returncode != 0, resultat.stdout
    assert "nettoyage : ÉCHEC" in resultat.stdout
    assert "BILAN" in resultat.stdout
    assert "Toutes les étapes sont passées" not in resultat.stdout
    journal_texte = journal.read_text(encoding="utf-8")
    assert "ECHEC_NETTOYAGE_SIMULE" in journal_texte
    assert (tmp_path / "compteur_drop").read_text(encoding="utf-8").strip() != "1"


@besoin_bash
def test_campagne_exe_dependance_manquante_arret_avant_action(tmp_path):
    """Une dépendance absente arrête la campagne avant tout DROP/CREATE."""
    box, hooks, journal = _bac_campagne(tmp_path, None)
    resultat = _lancer(box / "db/outils/campagne_exe_lotb.sh",
                       env=_env_campagne(box, hooks, journal,
                                         PSQL=str(tmp_path / "psql_absent.exe")),
                       cwd=box)
    assert resultat.returncode != 0, resultat.stdout
    assert "dépendance manquante" in resultat.stdout
    assert not journal.exists() or journal.read_text(encoding="utf-8").strip() == ""


@besoin_bash
def test_campagne_exe_suite_en_echec_code_non_nul(tmp_path):
    """Le code final doit aussi refléter un échec de suite, pas seulement la préparation."""
    box, hooks, journal = _bac_campagne(tmp_path, None)
    resultat = _lancer(box / "db/outils/campagne_exe_lotb.sh",
                       env=_env_campagne(box, hooks, journal, QF_NPM_ECHEC="vente"),
                       cwd=box)
    assert resultat.returncode != 0, resultat.stdout
    assert "suite vente" in resultat.stdout
    assert "BILAN" in resultat.stdout


# ---------------------------------------------------------------------------
# B — verifier_tout.sh : port/hôte transmis à pytest, cible de test vérifiée
# ---------------------------------------------------------------------------
def _bac_verifier_tout(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    box = tmp_path / "bac_verifier_tout"
    for dossier in ("db/outils", "db/tests", "server", "maquette/verification",
                    "QuincaillerieFranck_Test"):
        (box / dossier).mkdir(parents=True)
    shutil.copy2(RACINE / "db/outils/verifier_tout.sh",
                 box / "db/outils/verifier_tout.sh")
    (box / "db/tests/executer_tests.sh").write_text(
        'printf \'%s\\n\' "${BASE_TEST:-ABSENT}" >> "${QF_JOURNAL_SQL:-/dev/null}"\n'
        "exit 0\n", encoding="utf-8", newline="\n")
    (box / "db/tests/00_jeu_essai.sql").write_text("-- simulé\n", encoding="utf-8")
    (box / "db/outils/migrer.sh").write_text("exit 0\n", encoding="utf-8", newline="\n")
    (box / "QuincaillerieFranck_Test/creation_base_donnees.sql").write_text(
        "-- simulé\n", encoding="utf-8")

    psql = box / "psql_simule.exe"
    _ecrire_executable(psql,
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "${QF_JOURNAL_PSQL:-/dev/null}"\n'
        'if [[ "$*" == *"current_database()"* ]]; then\n'
        '  if [[ "$*" == *"-d postgres"* ]]; then\n'
        '    printf \'%s|127.0.0.1|%s\\n\' "postgres" "${QF_STUB_SERVER_PORT:-$QF_STUB_PORT}"\n'
        "  else\n"
        '    printf \'%s|127.0.0.1|%s\\n\' "$QF_STUB_DB" "$QF_STUB_PORT"\n'
        "  fi\n"
        "fi\n"
        "exit 0\n")
    pg_dump = box / "pg_dump_simule.exe"
    _ecrire_executable(pg_dump, "#!/usr/bin/env bash\nexit 0\n")

    python = box / "python_simule.exe"
    _ecrire_executable(python,
        "#!/usr/bin/env bash\n"
        'if [ "${1:-}" = "-m" ] && [ "${2:-}" = "pytest" ]; then\n'
        "  {\n"
        '    echo "QF_TEST_PGHOST=${QF_TEST_PGHOST:-ABSENT}"\n'
        '    echo "QF_TEST_PGPORT=${QF_TEST_PGPORT:-ABSENT}"\n'
        '    echo "QF_TEST_DBNAME=${QF_TEST_DBNAME:-ABSENT}"\n'
        "  } >> \"$QF_JOURNAL_PYTEST\"\n"
        "fi\n"
        "exit 0\n")

    hooks = tmp_path / "doubles_verifier.sh"
    hooks.write_text(
        "curl(){ :; }\n"
        'timeout(){ shift; "$@"; }\n'
        "npm(){ return 0; }\n",
        encoding="utf-8", newline="\n")
    journal_pytest = tmp_path / "journal_pytest.log"
    return box, hooks, journal_pytest, psql


@besoin_bash
def test_verifier_tout_transmet_hote_port_et_base_a_pytest(tmp_path):
    """R2 : PGPORT=5558 doit devenir QF_TEST_PGPORT=5558 pour conftest."""
    box, hooks, journal_pytest, psql = _bac_verifier_tout(tmp_path)
    journal_psql = tmp_path / "journal_psql.log"
    journal_sql = tmp_path / "journal_sql.log"
    resultat = _lancer(
        box / "db/outils/verifier_tout.sh",
        env={
            "BASH_ENV": str(hooks),
            "PSQL": str(psql),
            "PG_DUMP": str(box / "pg_dump_simule.exe"),
            "PYTHON": str(box / "python_simule.exe"),
            "PGHOST": "127.0.0.1", "PGPORT": "5558", "PGUSER": "postgres",
            "PGPASSWORD": "qf_dev_local", "BASE_TEST": "quincaillerie_q103_bac",
            "PORT_SERVEUR": "18010", "TEMP": str(tmp_path),
            "QF_STUB_DB": "quincaillerie_q103_bac", "QF_STUB_PORT": "5558",
            "QF_JOURNAL_PSQL": str(journal_psql),
            "QF_JOURNAL_PYTEST": str(journal_pytest),
            "QF_JOURNAL_SQL": str(journal_sql),
        },
        cwd=box)
    assert resultat.returncode == 0, resultat.stdout
    contenu = journal_pytest.read_text(encoding="utf-8")
    assert "QF_TEST_PGPORT=5558" in contenu, contenu
    assert "QF_TEST_PGHOST=127.0.0.1" in contenu, contenu
    assert "QF_TEST_DBNAME=quincaillerie_q103_bac" in contenu, contenu
    assert journal_sql.read_text(encoding="utf-8").strip() == "quincaillerie_q103_bac"


@besoin_bash
def test_verifier_tout_refuse_un_port_effectif_different(tmp_path):
    box, hooks, journal_pytest, psql = _bac_verifier_tout(tmp_path)
    resultat = _lancer(
        box / "db/outils/verifier_tout.sh", "--verifier-cible",
        env={
            "BASH_ENV": str(hooks), "PSQL": str(psql),
            "PGHOST": "127.0.0.1", "PGPORT": "5558", "PGUSER": "postgres",
            "PGPASSWORD": "qf_dev_local", "BASE_TEST": "quincaillerie_q103_bac",
            "QF_STUB_DB": "quincaillerie_q103_bac", "QF_STUB_PORT": "5599",
            "QF_STUB_SERVER_PORT": "5558",
            "QF_JOURNAL_PYTEST": str(journal_pytest),
        },
        cwd=box)
    assert resultat.returncode != 0, resultat.stdout
    assert "incohérente" in resultat.stdout


@besoin_bash
def test_verifier_tout_instancie_incoherente_arrete_avant_destructif(tmp_path):
    """Une instance ambiguë (port effectif différent) doit arrêter AVANT l'étape 1."""
    box, hooks, journal_pytest, psql = _bac_verifier_tout(tmp_path)
    journal_psql = tmp_path / "journal_psql.log"
    journal_sql = tmp_path / "journal_sql.log"
    resultat = _lancer(
        box / "db/outils/verifier_tout.sh",
        env={
            "BASH_ENV": str(hooks), "PSQL": str(psql),
            "PG_DUMP": str(box / "pg_dump_simule.exe"),
            "PYTHON": str(box / "python_simule.exe"),
            "PGHOST": "127.0.0.1", "PGPORT": "5558", "PGUSER": "postgres",
            "PGPASSWORD": "qf_dev_local", "BASE_TEST": "quincaillerie_q103_bac",
            "QF_STUB_DB": "quincaillerie_q103_bac", "QF_STUB_PORT": "5558",
            "QF_STUB_SERVER_PORT": "5599",
            "QF_JOURNAL_PSQL": str(journal_psql),
            "QF_JOURNAL_PYTEST": str(journal_pytest),
            "QF_JOURNAL_SQL": str(journal_sql),
        },
        cwd=box)
    assert resultat.returncode != 0, resultat.stdout
    assert "identité de l'instance incohérente" in resultat.stdout
    assert not journal_sql.exists(), "la suite SQL destructive a été lancée"
    contenu = journal_psql.read_text(encoding="utf-8")
    assert "DROP DATABASE" not in contenu
    assert "TRUNCATE" not in contenu
    assert "CREATE DATABASE" not in contenu


@besoin_bash
def test_verifier_tout_refuse_la_base_de_production():
    resultat = _lancer(RACINE / "db/outils/verifier_tout.sh", "--verifier-cible",
                       env={"BASE_TEST": "quincaillerie"})
    assert resultat.returncode != 0, resultat.stdout
    assert "production" in resultat.stdout


@besoin_bash
def test_verifier_tout_refuse_un_hote_non_local():
    resultat = _lancer(RACINE / "db/outils/verifier_tout.sh", "--verifier-cible",
                       env={"BASE_TEST": "quincaillerie_test", "PGHOST": "192.0.2.1"})
    assert resultat.returncode != 0, resultat.stdout
    assert "loopback" in resultat.stdout


# ---------------------------------------------------------------------------
# B — conftest.py refuse lui aussi une cible non-test (pytest lancé à la main)
# ---------------------------------------------------------------------------
def _charger_conftest(env_sup: dict) -> subprocess.CompletedProcess:
    code = (
        "import importlib.util\n"
        "spec = importlib.util.spec_from_file_location('conftest_sonde', 'tests/conftest.py')\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "print('PORT=' + str(module.PG_PORT))\n"
        "print('HOST=' + module.PG_HOST)\n"
        "print('BASE=' + module.PG_TEST_DBNAME)\n"
    )
    env = dict(os.environ)
    env.update(env_sup)
    return subprocess.run([sys.executable, "-c", code],
                          cwd=str(RACINE / "server"), env=env,
                          capture_output=True, text=True, timeout=60)


def test_conftest_utilise_le_port_et_l_hote_transmis():
    resultat = _charger_conftest({
        "QF_TEST_PGHOST": "127.0.0.1", "QF_TEST_PGPORT": "5558",
        "QF_TEST_DBNAME": "quincaillerie_q103",
    })
    assert resultat.returncode == 0, resultat.stderr
    assert "PORT=5558" in resultat.stdout
    assert "HOST=127.0.0.1" in resultat.stdout
    assert "BASE=quincaillerie_q103" in resultat.stdout


@pytest.mark.parametrize("environnement,motif", [
    ({"QF_TEST_DBNAME": "quincaillerie"}, "base de test"),
    ({"QF_TEST_PGHOST": "192.0.2.1"}, "locale"),
    ({"QF_TEST_PGPORT": "abc"}, "entier"),
])
def test_conftest_refuse_une_cible_non_test(environnement, motif):
    resultat = _charger_conftest(environnement)
    assert resultat.returncode != 0
    assert motif in resultat.stderr
