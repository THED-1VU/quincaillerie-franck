"""Préparation de la base avant chaque module de test.

Chaque test part d'un état connu : les migrations doivent déjà être
appliquées (voir db/outils/migrer.sh appliquer) sur la base pointée par
server/config.ini. Ce fichier recharge le jeu d'essai (db/tests/00_jeu_essai.sql)
et fixe des mots de passe bcrypt RÉELS (préfixe $2a$) pour les comptes de
test, connectés directement en tant que "postgres" — un raccourci
d'administration de test, jamais un chemin emprunté par l'application.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

RACINE_DEPOT = Path(__file__).resolve().parent.parent.parent
RACINE_SERVEUR = RACINE_DEPOT / "server"
PGDEV = RACINE_DEPOT / "_pgdev"
PSQL_EXE = PGDEV / "pgsql" / "bin" / "psql.exe"

# Au niveau du MODULE (pas d'une fixture) : certains tests importent `app.*`
# directement sans dépendre de la fixture `app` (ex. tests de config.py qui
# doivent justement pouvoir s'exécuter sans application déjà construite).
if str(RACINE_SERVEUR) not in sys.path:
    sys.path.insert(0, str(RACINE_SERVEUR))

# Connexion ADMINISTRATIVE de test (postgres, jamais utilisée par
# l'application elle-même — voir server/app/config.py qui refuse ce compte).
PG_HOST = "127.0.0.1"
PG_PORT = 5433
PG_ADMIN_DSN = f"host={PG_HOST} port={PG_PORT} dbname=quincaillerie_test user=postgres password=qf_dev_local"

# Mots de passe de test, en clair, UNIQUEMENT valables sur la base de test
# locale (_pgdev, jamais versionnée, jamais partagée).
MOT_DE_PASSE_RESPONSABLE = "ResponsableTest123"
MOT_DE_PASSE_AGENT_STOCK = "AgentStockTest123"
MOT_DE_PASSE_AGENT_STOCK_COMPTOIR = "AgentStockCptTest123"
MOT_DE_PASSE_AGENT_COMPTA = "AgentComptaTest123"
MOT_DE_PASSE_AGENT_COMPTA_COMPTOIR = "AgentComptaCptTest123"


def _executer_sql_admin(sql: str) -> None:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute(sql)
        conn.commit()


@pytest.fixture(scope="function")
def base_reinitialisee():
    """Recharge le jeu d'essai + fixe des mots de passe bcrypt réels.

    scope="function" : chaque test repart d'un état identique — important
    puisque plusieurs tests modifient tentatives_echouees, mot_de_passe_hash,
    ou l'état actif d'un compte.
    """
    # IMPORTANT (piège Windows) : `env=` REMPLACE tout l'environnement du
    # sous-processus au lieu de le compléter. psql.exe a besoin des variables
    # système habituelles (SystemRoot, PATH...) pour que la résolution réseau
    # fonctionne — sans elles, il échoue silencieusement (code 2). On part
    # donc TOUJOURS d'une copie de os.environ, jamais d'un dict neuf.
    environnement = {**os.environ, "PGPASSWORD": "qf_dev_local"}
    resultat = subprocess.run(
        [str(PSQL_EXE), "-h", PG_HOST, "-p", str(PG_PORT), "-U", "postgres",
         "-d", "quincaillerie_test", "-v", "ON_ERROR_STOP=1", "-q",
         "-f", str(RACINE_DEPOT / "db" / "tests" / "00_jeu_essai.sql")],
        env=environnement,
        capture_output=True, text=True,
    )
    assert resultat.returncode == 0, (
        f"Échec du rechargement du jeu d'essai :\n{resultat.stdout}\n{resultat.stderr}"
    )

    # Hachages bcrypt RÉELS, générés par pgcrypto lui-même (gen_salt('bf', 12)
    # produit systématiquement un préfixe $2a$, compatible pgcrypto par
    # construction — pas de risque de piège 2a/2b ici).
    _executer_sql_admin(
        f"""
        UPDATE utilisateurs SET tentatives_echouees = 0,
               mot_de_passe_hash = crypt('{MOT_DE_PASSE_RESPONSABLE}', gen_salt('bf', 12))
         WHERE identifiant = 'resp';
        UPDATE utilisateurs SET tentatives_echouees = 0,
               mot_de_passe_hash = crypt('{MOT_DE_PASSE_AGENT_STOCK}', gen_salt('bf', 12))
         WHERE identifiant = 'magasin.stock';
        UPDATE utilisateurs SET tentatives_echouees = 0,
               mot_de_passe_hash = crypt('{MOT_DE_PASSE_AGENT_STOCK_COMPTOIR}', gen_salt('bf', 12))
         WHERE identifiant = 'comptoir.stock';
        UPDATE utilisateurs SET tentatives_echouees = 0,
               mot_de_passe_hash = crypt('{MOT_DE_PASSE_AGENT_COMPTA}', gen_salt('bf', 12))
         WHERE identifiant = 'magasin.compta';
        UPDATE utilisateurs SET tentatives_echouees = 0,
               mot_de_passe_hash = crypt('{MOT_DE_PASSE_AGENT_COMPTA_COMPTOIR}', gen_salt('bf', 12))
         WHERE identifiant = 'comptoir.compta';
        """
    )
    yield


@pytest.fixture(scope="function")
def app(base_reinitialisee):
    """Application FastAPI configurée pour la base de test, avec un limiteur
    de débit large (les tests d'authentification déclenchent volontairement
    plusieurs échecs ; seul test_limitation_de_debit resserre la limite lui-même)."""
    from app.config import Config, ConfigApi, ConfigBase
    from app.main import creer_application

    config = Config(
        base=ConfigBase(
            host=PG_HOST, port=PG_PORT, dbname="quincaillerie_test",
            user="qf_app", password="qf_app_dev_local",
        ),
        api=ConfigApi(
            secret_key="0" * 64,  # jeton de test, jamais utilisé en dehors de ce process
            duree_session_minutes=480,
            tentatives_max_par_minute=1000,  # neutralisé par défaut pour les autres tests
        ),
    )
    return creer_application(config)


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app)


def se_connecter(client: TestClient, identifiant: str, mot_de_passe: str) -> dict:
    reponse = client.post(
        "/auth/connexion", json={"identifiant": identifiant, "mot_de_passe": mot_de_passe}
    )
    assert reponse.status_code == 200, f"Connexion échouée : {reponse.status_code} {reponse.text}"
    return reponse.json()


def entete_autorisation(jeton: str) -> dict:
    return {"Authorization": f"Bearer {jeton}"}
