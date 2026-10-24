"""Preuves C-1 a C-4 : une restauration coupe les sessions anterieures,
verrouille la base pendant le montage et ne peut jamais annoncer un succes
si l'invalidation echoue.

Tout est synthetique : aucune donnee reelle, aucun appel a sauvegarder.ps1
(le dump est produit directement par pg_dump). Les scripts reellement
executes sont db/outils/restaurer.ps1 et les outils PostgreSQL locaux.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psycopg
import pytest

from conftest import (MOT_DE_PASSE_AGENT_STOCK, MOT_DE_PASSE_AGENT_STOCK_COMPTOIR,
                      MOT_DE_PASSE_RESPONSABLE, PGDEV, PG_ADMIN_DSN, PG_HOST,
                      PG_PORT, PG_TEST_DBNAME, entete_autorisation, se_connecter)
from app.securite import GestionnaireSessions

RACINE = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("powershell")
PG_DUMP = shutil.which("pg_dump") or str(PGDEV / "pgsql" / "bin" / "pg_dump.exe")
PG_RESTORE = shutil.which("pg_restore") or str(PGDEV / "pgsql" / "bin" / "pg_restore.exe")
SCRIPT_RESTAURATION = RACINE / "db" / "outils" / "restaurer.ps1"

ROUTES_SESSION = ("/moi", "/admin/comptes", "/ventes/parametres")

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or not POWERSHELL
    or not Path(PG_DUMP).exists() or not Path(PG_RESTORE).exists(),
    reason="restauration de bout en bout : Windows + PowerShell + outils PostgreSQL requis",
)


def _dsn_admin(base: str) -> str:
    return f"host={PG_HOST} port={PG_PORT} dbname={base} user=postgres password=qf_dev_local"


def _dsn_app(base: str) -> str:
    return f"host={PG_HOST} port={PG_PORT} dbname={base} user=qf_app password=qf_app_dev_local"


def _environnement_outils() -> dict:
    return {
        **os.environ,
        "PGPASSWORD": "qf_dev_local",
        "PATH": str(Path(PG_DUMP).parent) + os.pathsep + os.environ.get("PATH", ""),
    }


def _supprimer_base(nom: str) -> None:
    with psycopg.connect(_dsn_admin("postgres"), autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=%s AND pid<>pg_backend_pid()", (nom,))
        conn.execute(f'DROP DATABASE IF EXISTS "{nom}"')


def _valeur_admin(base: str, requete: str, parametres: tuple = ()):
    with psycopg.connect(_dsn_admin(base)) as conn:
        ligne = conn.execute(requete, parametres).fetchone()
        return ligne[0] if ligne is not None else None


def _executer_admin(base: str, sql: str) -> None:
    with psycopg.connect(_dsn_admin(base), autocommit=True) as conn:
        conn.execute(sql)


def _compter_sessions(base: str) -> int:
    return int(_valeur_admin(base, "SELECT count(*) FROM sessions_serveur"))


def _limite_connexions(base: str) -> int | None:
    ligne = _valeur_admin(
        "postgres", "SELECT datconnlimit FROM pg_database WHERE datname=%s", (base,))
    return int(ligne) if ligne is not None else None


def _creer_dump(destination: Path) -> None:
    resultat = subprocess.run(
        [PG_DUMP, "-h", PG_HOST, "-p", str(PG_PORT), "-U", "postgres",
         "-Fc", "-f", str(destination), PG_TEST_DBNAME],
        env=_environnement_outils(), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=180,
    )
    assert resultat.returncode == 0, resultat.stderr


def _commande_restauration(dump: Path, nom_cible: str) -> list[str]:
    return [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(SCRIPT_RESTAURATION),
            "-FichierBase", str(dump), "-NomBaseCible", nom_cible,
            "-PgHost", PG_HOST, "-PgPort", str(PG_PORT)]


def _restaurer(dump: Path, nom_cible: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        _commande_restauration(dump, nom_cible),
        env=_environnement_outils(), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )


def _application(base: str):
    from app.config import Config, ConfigApi, ConfigBase
    from app.main import creer_application
    from fastapi.testclient import TestClient

    config = Config(
        base=ConfigBase(host=PG_HOST, port=PG_PORT, dbname=base,
                        user="qf_app", password="qf_app_dev_local"),
        api=ConfigApi(secret_key="0" * 64, duree_session_minutes=480,
                      tentatives_max_par_minute=1000),
    )
    return TestClient(creer_application(config))


def _jti(jeton: str) -> str:
    return GestionnaireSessions("0" * 64, 480).verifier(jeton).jti


def _refuser_partout(client, jeton: str) -> None:
    for route in ROUTES_SESSION:
        reponse = client.get(route, headers=entete_autorisation(jeton))
        assert reponse.status_code == 401, (route, reponse.status_code, reponse.text)


def _nom_cible() -> str:
    return f"quincaillerie_restauree_{uuid.uuid4().hex[:8]}"


def test_c1_plusieurs_sessions_avant_dump_toutes_refusees_apres_restauration(client, tmp_path):
    """C-1 : trois comptes connectes avant le dump, tous refuses apres."""
    sessions = [
        se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE),
        se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK),
        se_connecter(client, "comptoir.stock", MOT_DE_PASSE_AGENT_STOCK_COMPTOIR),
    ]
    for session in sessions:
        assert client.get("/moi", headers=entete_autorisation(session["jeton"])).status_code == 200
    assert _compter_sessions(PG_TEST_DBNAME) >= 3

    dump = tmp_path / "synthetique_c1.dump"
    _creer_dump(dump)

    # Le scenario de la revue #103 : revocation APRES le dump. Les deux
    # autres sessions ne sont jamais revoquees, ce qui rend la preuve plus
    # forte que le seul cas du jeton deconnecte.
    assert client.post("/auth/deconnexion",
                       headers=entete_autorisation(sessions[0]["jeton"])).status_code == 204

    nom_cible = _nom_cible()
    try:
        restauration = _restaurer(dump, nom_cible)
        sortie = restauration.stdout + restauration.stderr
        assert restauration.returncode == 0, sortie
        invalidees = re.search(r"[Ss]essions de la sauvegarde invalidees \((\d+)\)", sortie)
        assert invalidees and int(invalidees.group(1)) >= 3, sortie
        assert _compter_sessions(nom_cible) == 0

        restauree = _application(nom_cible)
        for session in sessions:
            _refuser_partout(restauree, session["jeton"])

        nouvelle = se_connecter(restauree, "resp", MOT_DE_PASSE_RESPONSABLE)
        assert restauree.get("/moi", headers=entete_autorisation(nouvelle["jeton"])).status_code == 200
    finally:
        _supprimer_base(nom_cible)


def test_c2_echec_invalidation_code_non_nul_et_base_fermee(client, tmp_path):
    """C-2 : si TRUNCATE echoue, aucune restauration reussie, base laissee fermee.

    Une table de la sauvegarde porte une cle etrangere vers sessions_serveur
    (creee dans la base source avant le dump) : PostgreSQL refuse alors le
    TRUNCATE sans CASCADE. C'est une panne reelle du nettoyage, pas un
    double de test.
    """
    se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _executer_admin(PG_TEST_DBNAME, """
        CREATE TABLE public.verrou_c2 (
            session_jti VARCHAR(32) REFERENCES sessions_serveur(jti));
        INSERT INTO public.verrou_c2 SELECT jti FROM sessions_serveur LIMIT 1;
    """)
    dump = tmp_path / "synthetique_c2.dump"
    nom_cible = _nom_cible()
    try:
        _creer_dump(dump)
    finally:
        _executer_admin(PG_TEST_DBNAME, "DROP TABLE IF EXISTS public.verrou_c2;")

    try:
        restauration = _restaurer(dump, nom_cible)
        sortie = restauration.stdout + restauration.stderr
        assert restauration.returncode != 0, sortie
        assert "impossible d'invalider les sessions" in sortie
        assert "Restauration terminee" not in sortie
        assert _compter_sessions(nom_cible) == 1
        assert _limite_connexions(nom_cible) == 0
    finally:
        _supprimer_base(nom_cible)


def test_c3_aucune_connexion_applicative_pendant_la_restauration(client, tmp_path):
    """C-3 : la base cible est fermee aux comptes applicatifs pendant le montage.

    Un evenement DDL de la sauvegarde ralentit la creation de
    sessions_serveur : la fenetre de restauration devient observable, et une
    connexion qf_app est refusee par la limite de connexions. Les marqueurs
    de sortie prouvent l'ordre verrouillage -> restauration -> invalidation
    -> reautorisation.
    """
    se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _executer_admin(PG_TEST_DBNAME, """
        CREATE OR REPLACE FUNCTION public.ralentir_restauration_c3() RETURNS event_trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF current_query() ILIKE '%CREATE TABLE%'
               AND current_query() ILIKE '%sessions_serveur%' THEN
                PERFORM pg_sleep(5);
            END IF;
        END $$;
        CREATE EVENT TRIGGER trg_ralentir_restauration_c3 ON ddl_command_start
        WHEN TAG IN ('CREATE TABLE') EXECUTE FUNCTION public.ralentir_restauration_c3();
    """)
    dump = tmp_path / "synthetique_c3.dump"
    nom_cible = _nom_cible()
    try:
        _creer_dump(dump)
    finally:
        _executer_admin(PG_TEST_DBNAME,
                        "DROP EVENT TRIGGER IF EXISTS trg_ralentir_restauration_c3; "
                        "DROP FUNCTION IF EXISTS public.ralentir_restauration_c3();")

    processus = subprocess.Popen(
        _commande_restauration(dump, nom_cible),
        env=_environnement_outils(), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        errors="replace", bufsize=1,
    )
    try:
        limite = None
        fin = time.monotonic() + 60
        while time.monotonic() < fin and processus.poll() is None:
            try:
                if _limite_connexions(nom_cible) == 0:
                    limite = 0
                    break
            except psycopg.Error:
                pass
            time.sleep(0.05)
        assert limite == 0, "la base cible n'a jamais ete verrouillee"
        assert processus.poll() is None, "restauration terminee avant la tentative de connexion"

        with pytest.raises(psycopg.OperationalError) as echec:
            psycopg.connect(_dsn_app(nom_cible), connect_timeout=3)
        message = str(echec.value).lower()
        assert "connection" in message and ("limit" in message or "too many" in message), message

        sortie, _ = processus.communicate(timeout=180)
        assert processus.returncode == 0, sortie
        marqueurs = [
            "Verrouillage des connexions applicatives",
            "Restauration du contenu depuis",
            "Sessions de la sauvegarde invalidees",
            "Reautorisation des connexions",
        ]
        positions = [sortie.find(marqueur) for marqueur in marqueurs]
        assert all(position >= 0 for position in positions), sortie
        assert positions == sorted(positions), sortie

        with psycopg.connect(_dsn_app(nom_cible), connect_timeout=3) as conn:
            assert conn.execute("SELECT 1").fetchone()[0] == 1
    finally:
        if processus.poll() is None:
            processus.kill()
            processus.wait(timeout=10)
        _supprimer_base(nom_cible)


def test_c4_verrouillage_restaure_reste_actif_puis_deverrouillage(client, tmp_path):
    """C-4 : l'etat de blocage C2-01 est restaure avec le dump.

    Risque residuel documente : une sauvegarde prise pendant un verrouillage
    le ramene. La parade utilisee ici est celle qui existe deja (route
    responsable /admin/comptes/{id}/deverrouiller) ; aucune modification de
    auth.py ni de migration n'est necessaire.
    """
    resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    utilisateur_stock = int(_valeur_admin(
        PG_TEST_DBNAME,
        "SELECT id FROM utilisateurs WHERE identifiant='magasin.stock'"))
    seuil = int(_valeur_admin(
        PG_TEST_DBNAME,
        "SELECT valeur FROM parametres WHERE cle='tentatives_max_connexion'"))

    derniere = None
    for _ in range(seuil):
        derniere = client.post("/auth/connexion", json={
            "identifiant": "magasin.stock", "mot_de_passe": "MauvaisSecret123"})
        assert derniere.status_code == 401, derniere.text
    assert "verrouill" in derniere.json()["detail"].lower()
    refus = client.post("/auth/connexion", json={
        "identifiant": "magasin.stock", "mot_de_passe": MOT_DE_PASSE_AGENT_STOCK})
    assert refus.status_code == 401 and "verrouill" in refus.json()["detail"].lower()

    dump = tmp_path / "synthetique_c4.dump"
    _creer_dump(dump)

    nom_cible = _nom_cible()
    try:
        restauration = _restaurer(dump, nom_cible)
        sortie = restauration.stdout + restauration.stderr
        assert restauration.returncode == 0, sortie
        assert _compter_sessions(nom_cible) == 0

        restauree = _application(nom_cible)
        _refuser_partout(restauree, resp["jeton"])

        verrouille = restauree.post("/auth/connexion", json={
            "identifiant": "magasin.stock", "mot_de_passe": MOT_DE_PASSE_AGENT_STOCK})
        assert verrouille.status_code == 401, verrouille.text
        assert "verrouill" in verrouille.json()["detail"].lower()

        responsable = se_connecter(restauree, "resp", MOT_DE_PASSE_RESPONSABLE)
        deverrouillage = restauree.post(
            f"/admin/comptes/{utilisateur_stock}/deverrouiller",
            headers=entete_autorisation(responsable["jeton"]))
        assert deverrouillage.status_code == 200, deverrouillage.text
        assert se_connecter(restauree, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    finally:
        _supprimer_base(nom_cible)
