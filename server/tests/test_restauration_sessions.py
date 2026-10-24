"""R3 (revue #103) : une restauration coupe les sessions anterieures.

Scenario reproduit avec des donnees synthetiques : connexion, dump, puis
revocation APRES le dump, puis restauration par le VRAI script
db/outils/restaurer.ps1. Sans l'invalidation des sessions restaurees,
l'ancien jeton redevient valide ; avec, il doit repondre 401 et une
reconnexion doit fonctionner. Aucune donnee reelle, aucune execution de
sauvegarder.ps1 (le dump est produit directement par pg_dump).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
import pytest

from conftest import (MOT_DE_PASSE_RESPONSABLE, PGDEV, PG_ADMIN_DSN, PG_HOST,
                      PG_PORT, PG_TEST_DBNAME, entete_autorisation,
                      se_connecter)
from app.securite import GestionnaireSessions

RACINE = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("powershell")
PG_DUMP = shutil.which("pg_dump") or str(PGDEV / "pgsql" / "bin" / "pg_dump.exe")
PG_RESTORE = shutil.which("pg_restore") or str(PGDEV / "pgsql" / "bin" / "pg_restore.exe")

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or not POWERSHELL
    or not Path(PG_DUMP).exists() or not Path(PG_RESTORE).exists(),
    reason="restauration de bout en bout : Windows + PowerShell + outils PostgreSQL requis",
)


def _dsn_admin(base: str) -> str:
    return f"host={PG_HOST} port={PG_PORT} dbname={base} user=postgres password=qf_dev_local"


def _supprimer_base(nom: str) -> None:
    with psycopg.connect(_dsn_admin("postgres"), autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=%s AND pid<>pg_backend_pid()", (nom,))
        conn.execute(f'DROP DATABASE IF EXISTS "{nom}"')


def test_restauration_invalide_les_sessions_anterieures(client, tmp_path):
    nom_cible = f"quincaillerie_restauree_{uuid.uuid4().hex[:8]}"
    dump = tmp_path / "synthetique.dump"
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    jeton = session["jeton"]
    jti = GestionnaireSessions("0" * 64, 480).verifier(jeton).jti
    entetes = entete_autorisation(jeton)

    try:
        environnement = {
            **os.environ,
            "PGPASSWORD": "qf_dev_local",
            "PATH": str(Path(PG_DUMP).parent) + os.pathsep + os.environ.get("PATH", ""),
        }
        dump_resultat = subprocess.run(
            [PG_DUMP, "-h", PG_HOST, "-p", str(PG_PORT), "-U", "postgres",
             "-Fc", "-f", str(dump), PG_TEST_DBNAME],
            env=environnement, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180,
        )
        assert dump_resultat.returncode == 0, dump_resultat.stderr

        # Revocation APRES le dump : l'etat vulnerabilisant de la revue #103.
        assert client.post("/auth/deconnexion", headers=entetes).status_code == 204
        assert client.get("/moi", headers=entetes).status_code == 401
        with psycopg.connect(PG_ADMIN_DSN) as conn:
            assert conn.execute(
                "SELECT count(*) FROM jetons_revoques WHERE jti=%s", (jti,)
            ).fetchone()[0] == 1

        restauration = subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(RACINE / "db" / "outils" / "restaurer.ps1"),
             "-FichierBase", str(dump), "-NomBaseCible", nom_cible,
             "-PgHost", PG_HOST, "-PgPort", str(PG_PORT)],
            env=environnement, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300,
        )
        sortie = restauration.stdout + restauration.stderr
        assert restauration.returncode == 0, sortie
        invalidees = re.search(r"[Ss]essions de la sauvegarde invalidees \((\d+)\)", sortie)
        assert invalidees and int(invalidees.group(1)) >= 1, sortie

        with psycopg.connect(_dsn_admin(nom_cible)) as conn:
            assert conn.execute("SELECT count(*) FROM sessions_serveur").fetchone()[0] == 0

        from app.config import Config, ConfigApi, ConfigBase
        from app.main import creer_application
        from fastapi.testclient import TestClient

        config = Config(
            base=ConfigBase(host=PG_HOST, port=PG_PORT, dbname=nom_cible,
                            user="qf_app", password="qf_app_dev_local"),
            api=ConfigApi(secret_key="0" * 64, duree_session_minutes=480,
                          tentatives_max_par_minute=1000),
        )
        client_restaure = TestClient(creer_application(config))
        assert client_restaure.get("/moi", headers=entetes).status_code == 401

        nouvelle = se_connecter(client_restaure, "resp", MOT_DE_PASSE_RESPONSABLE)
        assert client_restaure.get(
            "/moi", headers=entete_autorisation(nouvelle["jeton"])
        ).status_code == 200
    finally:
        _supprimer_base(nom_cible)
