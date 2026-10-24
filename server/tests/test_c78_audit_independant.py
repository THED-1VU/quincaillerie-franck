"""Audit indépendant des décisions propriétaire du 24/10/2026 (cycle 78).

Ce fichier n'appartient PAS à la suite ordinaire : il exprime le comportement
EXIGÉ par les quatre décisions, et sert deux fois —
  1. reproduction des écarts sur ``main`` (7bebded) ;
  2. vérification indépendante de la branche de correction, sans modifier
     le travail de l'agent qui la porte.

Lancement (base isolée, jamais la base de développement partagée) :

    QF_AUDIT_C78=1 QF_TEST_DBNAME=quincaillerie_c78 \
      python -m pytest -q server/tests/test_c78_audit_independant.py

Aucun score n'est tiré de ce fichier : seuls des résultats d'exécution
réels, datés et rejouables comptent.

Décisions couvertes :
  - D-N1 : plafond de 10 % de remise EFFECTIVE TOTALE (lignes + globale),
    pondérée par les quantités, approbation responsable au-delà, tracée ;
  - D-N5 : alerte obligatoire dès 60 minutes d'ancienneté de la dernière
    sauvegarde COMPLÈTE ET VÉRIFIÉE ; un échec ou une tentative non vérifiée
    ne réinitialise pas le délai ;
  - D1 : le caissier (agent_comptabilite) voit les prix de vente et montants,
    jamais prix d'achat / coût de revient / marge, y compris par API, export
    ou SQL direct ;
  - C2-01 : 5 échecs consécutifs → verrou temporaire de 15 minutes, non
    prolongeable par de nouvelles tentatives, levé à l'expiration.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
from threading import Barrier
from decimal import Decimal

import psycopg
import pytest
from openpyxl import load_workbook
from pypdf import PdfReader

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("QF_AUDIT_C78") != "1",
    reason="Audit cycle 78 : lancer avec QF_AUDIT_C78=1 (base isolée).",
)

_PRIX_CATALOGUE_ARTICLE_1 = 6500
_INTERDITS = {
    "prix_achat",
    "cout_revient",
    "cout_unitaire",
    "marge",
    "valorisation_achat",
    "ancien_prix_achat",
    "nouveau_prix_achat",
    "prix_achat_unitaire",
}


# ---------------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------------
def _vente(
    numero: str,
    lignes: list[dict],
    *,
    remise_globale_montant: float | None = None,
    remise_globale_pct: float | None = None,
    site_id: int = 1,
    **champs_libres,
) -> dict:
    corps = {
        "mode_paiement": "especes",
        "numero_facturier": numero,
        "vendeur_id": 1,
        "site_id": site_id,
        "lignes": lignes,
    }
    if remise_globale_montant is not None:
        corps["remise_globale_montant"] = remise_globale_montant
    if remise_globale_pct is not None:
        corps["remise_globale_pct"] = remise_globale_pct
    # Champs libres : utilisés pour prouver qu'une « fausse approbation »
    # envoyée par le client est ignorée (le schéma Pydantic n'a aucun champ
    # d'approbation : la décision est serveur).
    corps.update(champs_libres)
    return corps


def _compter_ventes(numero: str) -> int:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT count(*) FROM ventes WHERE numero_facturier = %s", (numero,)
        ).fetchone()[0]


def _toutes_les_cles(objet: object):
    if isinstance(objet, dict):
        for cle, valeur in objet.items():
            yield str(cle)
            yield from _toutes_les_cles(valeur)
    elif isinstance(objet, list):
        for element in objet:
            yield from _toutes_les_cles(element)


def _entetes_xlsx(contenu: bytes) -> list[str]:
    classeur = load_workbook(BytesIO(contenu), read_only=True)
    premiere = next(classeur.active.iter_rows(min_row=1, max_row=1, values_only=True))
    return [str(v) for v in premiere if v is not None]


# ===========================================================================
# D-N1 — remises cumulées : 10 % effectifs de la vente, toutes remises
# ===========================================================================
def test_dn1_cumul_ligne_et_globale_refuse_a_un_agent(client):
    """9 % sur la ligne + 9 % en remise globale = 18 % effectifs : refus.

    C'est le contournement central que la décision ferme : chaque mécanisme
    pris séparément reste sous 10 %, leur CUMUL ne l'est plus.
    """
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-AN10001",
            [{"article_id": 1, "quantite": 1, "remise_pct": 9}],
            remise_globale_pct=9,
        ),
    )
    assert reponse.status_code == 403, reponse.text
    assert _compter_ventes("MAG-AN10001") == 0


def test_dn1_borne_exacte_dix_pct_acceptee(client):
    """5 % ligne (325 FCFA) + 325 FCFA global = 650 = 10 % EXACT : passe.

    La limite est inclusive, conformément à « plafond de remise sans
    approbation est de 10 % » ; seule une remise STRICTEMENT supérieure
    exige l'approbation.
    """
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-AN10002",
            [{"article_id": 1, "quantite": 1, "remise_pct": 5}],
            remise_globale_montant=325,
        ),
    )
    assert reponse.status_code == 201, reponse.text
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT remise_globale_montant FROM ventes WHERE numero_facturier = 'MAG-AN10002'"
        ).fetchone()[0] == Decimal("325.00")


def test_dn1_borne_exacte_depassee_dun_centime_refusee(client):
    """650,01 FCFA de remise totale sur 6500 = 10,00015 % : refus."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-AN10003",
            [{"article_id": 1, "quantite": 1, "remise_pct": 5}],
            remise_globale_montant=325.01,
        ),
    )
    assert reponse.status_code == 403, reponse.text
    assert _compter_ventes("MAG-AN10003") == 0


def test_dn1_pondere_par_les_quantites_pas_par_ligne(client):
    """20 % sur une ligne de 6500 (1300 FCFA) + 0 % sur 10 × 3500 (35000)
    = 3,13 % de la vente : AUTORISÉ.

    L'ancien contrôle par ligne bloquait cette vente alors que la remise
    effective totale reste très en dessous du plafond. La décision raisonne
    sur la vente entière, pondérée par les quantités.
    """
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-AN10004",
            [
                {"article_id": 1, "quantite": 1, "remise_pct": 20},
                {"article_id": 2, "quantite": 10, "remise_pct": 0},
            ],
        ),
    )
    assert reponse.status_code == 201, reponse.text


def test_dn1_fausse_approbation_envoyee_par_le_client_ignoree(client):
    """Un agent qui prétend avoir une approbation dans le corps JSON est
    toujours refusé : l'approbation est constatée côté serveur, jamais
    déclarée par le client."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-AN10005",
            [{"article_id": 1, "quantite": 1, "remise_pct": 10}],
            remise_globale_pct=10,
            approbation_responsable=True,
            approbateur_id=1,
            approbation={"responsable_id": 1, "accordee": True},
        ),
    )
    assert reponse.status_code == 403, reponse.text
    assert _compter_ventes("MAG-AN10005") == 0


def test_dn1_approbation_responsable_tracee_et_immuable(client):
    """Le responsable peut dépasser 10 % ; la trace porte l'auteur
    AUTHENTIFIÉ et les montants relus en base, pas ceux du client."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-AN10006",
            [{"article_id": 1, "quantite": 1, "remise_pct": 10}],
            remise_globale_pct=10,
            approbateur_id=999,  # doit être ignoré au profit du jeton
        ),
    )
    assert reponse.status_code == 201, reponse.text
    vente_id = reponse.json()["vente_id"]

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        ligne = conn.execute(
            """
            SELECT responsable_id, total_catalogue, remise_totale, total_ttc
              FROM approbations_remises WHERE vente_id = %s
            """,
            (vente_id,),
        ).fetchone()
    # 650 (10 % ligne) + 585 (10 % de 5850 restants) = 1235 ; TTC = 5265.
    assert ligne == (
        session["utilisateur_id"],
        Decimal("6500.00"),
        Decimal("1235.00"),
        Decimal("5265.00"),
    )

    with pytest.raises(psycopg.errors.RestrictViolation):
        with psycopg.connect(PG_ADMIN_DSN) as conn:
            conn.execute(
                "DELETE FROM approbations_remises WHERE vente_id = %s", (vente_id,)
            )


def test_dn1_pas_dapprobation_a_dix_pct_exact(client):
    """À 10 % exactement, aucune approbation n'est requise ni tracée."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-AN10007", [{"article_id": 1, "quantite": 1, "remise_pct": 10}]
        ),
    )
    assert reponse.status_code == 201, reponse.text
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM approbations_remises WHERE vente_id = %s",
            (reponse.json()["vente_id"],),
        ).fetchone()[0] == 0


def test_dn1_cumul_responsable_secondaire_peut_approuver(client):
    """C3 (cumul de rôles) : un compte dont le rôle PRINCIPAL est agent
    comptabilité mais qui détient AUSSI le rôle responsable est autorisé par
    ``exiger_role`` comme responsable — l'approbation D-N1 doit suivre la
    même union, sinon la vente échoue dans la même transaction alors qu'elle
    est présentée à un compte habilité responsable."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute(
            """
            INSERT INTO utilisateurs_roles (utilisateur_id, role)
            SELECT id, 'responsable' FROM utilisateurs
             WHERE identifiant = 'magasin.compta'
            ON CONFLICT DO NOTHING
            """
        )
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json=_vente(
            "MAG-AN10008",
            [{"article_id": 1, "quantite": 1, "remise_pct": 10}],
            remise_globale_pct=10,
        ),
    )
    assert reponse.status_code == 201, reponse.text
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        ligne = conn.execute(
            "SELECT responsable_id FROM approbations_remises WHERE vente_id = %s",
            (reponse.json()["vente_id"],),
        ).fetchone()
    assert ligne == (session["utilisateur_id"],)


# ===========================================================================
# D-N5 — fraîcheur : alerte à 60 minutes sur la dernière preuve complète
#        ET vérifiée ; un échec / une tentative non vérifiée ne rajeunit pas
# ===========================================================================
def _ecrire_etat(tmp_path, monkeypatch, contenu: dict) -> None:
    chemin = tmp_path / "dernier_etat_sauvegarde.json"
    chemin.write_text(json.dumps(contenu), encoding="utf-8")
    monkeypatch.setenv("QF_FICHIER_ETAT_SAUVEGARDE", str(chemin))


def _etat_sauvegarde(client) -> dict:
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/exploitation/etat-sauvegarde",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


def _preuve(horodatage: datetime, **extra) -> dict:
    return {"horodatage": horodatage.isoformat(), "complete": True, "verifiee": True, **extra}


def test_dn5_sauvegarde_fraiche_verifiee_sans_alerte(client, tmp_path, monkeypatch):
    maintenant = datetime.now(timezone.utc)
    _ecrire_etat(
        tmp_path,
        monkeypatch,
        {"resultat": "SUCCES", **_preuve(maintenant - timedelta(seconds=60))},
    )
    etat = _etat_sauvegarde(client)
    assert etat["etat"] == "succes"
    assert etat["alerte"] is False
    assert etat["seuil_secondes"] == 3600
    assert 55 <= etat["age_secondes"] <= 70
    assert 3530 <= etat["delai_alerte_secondes"] <= 3545


@pytest.mark.parametrize(
    "age,etat_attendu,alerte_attendue",
    [(3599, "succes", False), (3600, "perime", True), (3601, "perime", True)],
)
def test_dn5_borne_exacte_soixante_minutes(
    client, tmp_path, monkeypatch, age, etat_attendu, alerte_attendue
):
    """« dès que ... atteint 60 minutes » : l'alerte s'allume À 3600 s,
    pas une seconde plus tard."""
    maintenant = datetime.now(timezone.utc)
    _ecrire_etat(
        tmp_path,
        monkeypatch,
        {"resultat": "SUCCES", **_preuve(maintenant - timedelta(seconds=age))},
    )
    etat = _etat_sauvegarde(client)
    assert etat["etat"] == etat_attendu
    assert etat["alerte"] is alerte_attendue
    assert abs(etat["age_secondes"] - age) <= 3


@pytest.mark.parametrize(
    "qualification",
    [
        {},
        {"complete": True},
        {"complete": True, "verifiee": "true"},
        {"complete": False, "verifiee": True},
        {"complete": True, "verifiee": False},
    ],
)
def test_dn5_sauvegarde_non_qualifiee_ne_produit_jamais_un_succes(
    client, tmp_path, monkeypatch, qualification
):
    """Une sauvegarde incomplète, non vérifiée, ou dont la vérification est
    une chaîne « true », ne prouve rien : jamais de succès, toujours alerte."""
    maintenant = datetime.now(timezone.utc)
    _ecrire_etat(
        tmp_path,
        monkeypatch,
        {
            "resultat": "SUCCES",
            "horodatage": (maintenant - timedelta(seconds=30)).isoformat(),
            **qualification,
        },
    )
    etat = _etat_sauvegarde(client)
    assert etat["etat"] != "succes"
    assert etat["alerte"] is True


def test_dn5_echec_ne_rajeunit_pas_la_derniere_preuve_verifiee(
    client, tmp_path, monkeypatch
):
    """Une sauvegarde ÉCHOUÉE, même horodatée à l'instant, ne réinitialise
    pas le délai : c'est la dernière preuve complète et vérifiée (2 h) qui
    compte, et l'alerte reste allumée."""
    maintenant = datetime.now(timezone.utc)
    _ecrire_etat(
        tmp_path,
        monkeypatch,
        {
            "resultat": "ECHEC",
            "horodatage": maintenant.isoformat(),
            "complete": False,
            "verifiee": False,
            "messages": ["pg_dump a échoué"],
            "derniere_sauvegarde_verifiee": _preuve(maintenant - timedelta(hours=2)),
        },
    )
    etat = _etat_sauvegarde(client)
    assert etat["etat"] == "echec"
    assert etat["alerte"] is True
    assert 7195 <= etat["age_secondes"] <= 7215


def test_dn5_succes_non_verifie_ne_rajeunit_pas_la_preuve(
    client, tmp_path, monkeypatch
):
    """Même en « SUCCES », une tentative non vérifiée ne rajeunit pas la
    preuve : l'âge affiché reste celui de la dernière sauvegarde qualifiée."""
    maintenant = datetime.now(timezone.utc)
    _ecrire_etat(
        tmp_path,
        monkeypatch,
        {
            "resultat": "SUCCES",
            "horodatage": maintenant.isoformat(),
            "complete": False,
            "verifiee": False,
            "derniere_sauvegarde_verifiee": _preuve(maintenant - timedelta(hours=2)),
        },
    )
    etat = _etat_sauvegarde(client)
    assert etat["etat"] != "succes"
    assert etat["alerte"] is True
    assert 7195 <= etat["age_secondes"] <= 7215


def test_dn5_format_actuel_du_producteur_non_qualifie(
    client, tmp_path, monkeypatch
):
    """Constat de chaîne : ``sauvegarder.ps1`` écrit aujourd'hui un état
    SUCCES daté SANS marqueur de complétude/vérification. Une telle preuve
    ne doit pas éteindre l'alerte — le producteur doit donc être enrichi
    (vérification réelle du dump), sinon l'écran alertera à chaque cycle.

    Ce test décrit volontairement le format réel du producteur au 24/10 :
    il restera vrai tant que le producteur n'écrira pas ces marqueurs.
    """
    maintenant = datetime.now(timezone.utc)
    _ecrire_etat(
        tmp_path,
        monkeypatch,
        {
            "horodatage": (maintenant - timedelta(seconds=60)).isoformat(),
            "resultat": "SUCCES",
            "base": "quincaillerie_c78",
            "pg_host": "127.0.0.1",
            "pg_port": 5433,
            "fichier_base": "quincaillerie_c78_20261024_120000.dump",
            "fichier_roles": "quincaillerie_c78_20261024_120000_roles.sql",
            "dossier_distant": None,
            "retention_jours": 30,
            "messages": [],
        },
    )
    etat = _etat_sauvegarde(client)
    assert etat["etat"] != "succes"
    assert etat["alerte"] is True


def test_dn5_absent_ou_illisible_toujours_en_alerte(client, tmp_path, monkeypatch):
    monkeypatch.setenv(
        "QF_FICHIER_ETAT_SAUVEGARDE", str(tmp_path / "aucun_etat.json")
    )
    etat = _etat_sauvegarde(client)
    assert etat["etat"] == "absent"
    assert etat["alerte"] is True

    chemin = tmp_path / "corrompu.json"
    chemin.write_text("{ceci n'est pas du json", encoding="utf-8")
    monkeypatch.setenv("QF_FICHIER_ETAT_SAUVEGARDE", str(chemin))
    etat = _etat_sauvegarde(client)
    assert etat["etat"] == "inconnu"
    assert etat["alerte"] is True


@pytest.mark.parametrize(
    "horodatage",
    [
        "date invalide",
        "2099-01-01T00:00:00+00:00",  # future : ne prouve rien
        "2026-10-24T12:00:00",  # sans fuseau : ambigu, refusé
    ],
)
def test_dn5_horodatage_invalide_futur_ou_sans_fuseau_refuse(
    client, tmp_path, monkeypatch, horodatage
):
    _ecrire_etat(
        tmp_path,
        monkeypatch,
        {
            "resultat": "SUCCES",
            "horodatage": horodatage,
            "complete": True,
            "verifiee": True,
        },
    )
    etat = _etat_sauvegarde(client)
    assert etat["etat"] != "succes"
    assert etat["alerte"] is True


def test_dn5_route_reservee_au_responsable(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get(
        "/exploitation/etat-sauvegarde",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 403


# ===========================================================================
# D1 — prix de vente visibles au caissier, prix d'achat / coûts / marges non
# ===========================================================================
def test_d1_api_articles_sans_prix_achat_ni_marge_meme_avec_parametres(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get(
        "/articles?role=responsable&prix_achat=true&inclure_couts=1&marge=1",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert any(a.get("prix_vente") == _PRIX_CATALOGUE_ARTICLE_1 for a in corps["articles"])
    assert not (_INTERDITS & set(_toutes_les_cles(corps)))


def test_d1_exports_comptables_sans_colonnes_interdites(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    catalogue = client.get(
        "/rapports/articles?format=xlsx&role=responsable", headers=entetes
    )
    assert catalogue.status_code == 200, catalogue.text
    colonnes = _entetes_xlsx(catalogue.content)
    assert "prix_vente" in colonnes
    assert not (_INTERDITS & set(colonnes))

    catalogue_pdf = client.get("/rapports/articles?format=pdf", headers=entetes)
    assert catalogue_pdf.status_code == 200, catalogue_pdf.text
    texte = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(BytesIO(catalogue_pdf.content)).pages
    )
    assert "prix_vente" in texte
    assert not any(interdit in texte for interdit in _INTERDITS)

    ventes = client.get(
        "/rapports/ventes?date_debut=2026-01-01&date_fin=2026-12-31&format=xlsx",
        headers=entetes,
    )
    assert ventes.status_code == 200, ventes.text
    colonnes = _entetes_xlsx(ventes.content)
    assert "total_ttc" in colonnes
    assert not (_INTERDITS & set(colonnes))

    ecarts = client.get("/rapports/ecarts-prix-vendeurs", headers=entetes)
    assert ecarts.status_code == 200, ecarts.text
    assert not (_INTERDITS & set(_toutes_les_cles(ecarts.json())))


def test_d1_routes_de_valorisation_refusees_au_caissier(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])
    for url in (
        "/rapports/stock?format=xlsx",
        "/rapports/ecarts-comptage?date_debut=2026-01-01&date_fin=2026-12-31&format=xlsx",
        "/tableau-bord/credit-client",
        "/inventaire/ecarts",
        "/exploitation/etat-sauvegarde",
    ):
        assert client.get(url, headers=entetes).status_code == 403, url


def test_d1_sql_direct_sans_prix_achat_ni_historique(client):
    """Défense en profondeur : même en contournant l'API, le rôle PostgreSQL
    du caissier ne peut lire ni prix_achat, ni la table d'historique des prix."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute("SET LOCAL ROLE qf_agent_comptabilite")
        prix_vente = conn.execute(
            "SELECT prix_vente FROM articles WHERE id = 1"
        ).fetchone()[0]
    assert prix_vente == Decimal("6500.00")

    for requete in (
        "SELECT prix_achat FROM articles",
        "SELECT * FROM articles",
        "SELECT * FROM historique_prix_articles",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(PG_ADMIN_DSN) as conn:
                conn.execute("SET LOCAL ROLE qf_agent_comptabilite")
                conn.execute(requete)


def test_d1_cumul_de_roles_ne_donne_pas_acces_aux_couts(client):
    """Un compte caissier auquel on ajoute le rôle agent_stock conserve
    l'interdiction : le cumul n'élève jamais les privilèges de colonne."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute(
            """
            INSERT INTO utilisateurs_roles (utilisateur_id, role)
            SELECT id, 'agent_stock' FROM utilisateurs
             WHERE identifiant = 'magasin.compta'
            ON CONFLICT DO NOTHING
            """
        )

    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get(
        "/articles", headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    assert not (_INTERDITS & set(_toutes_les_cles(reponse.json())))

    for role in ("qf_agent_comptabilite", "qf_agent_stock"):
        for requete in ("SELECT prix_achat FROM articles", "SELECT * FROM articles"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(PG_ADMIN_DSN) as conn:
                    conn.execute(f"SET LOCAL ROLE {role}")
                    conn.execute(requete)


# ===========================================================================
# C2-01 — cinq échecs consécutifs, verrou 15 minutes, non prolongeable
# ===========================================================================
def _tenter(client, identifiant: str, mot_de_passe: str = "faux"):
    return client.post(
        "/auth/connexion",
        json={"identifiant": identifiant, "mot_de_passe": mot_de_passe},
    )


def _etat_compte(identifiant: str):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute(
            """
            SELECT tentatives_echouees, verrouille_jusqua, clock_timestamp()
              FROM utilisateurs WHERE identifiant = %s
            """,
            (identifiant,),
        ).fetchone()


def test_c201_cinq_echecs_verrouillent_quinze_minutes(client):
    for _ in range(4):
        reponse = _tenter(client, "magasin.stock")
        assert reponse.status_code == 401
        assert "verrouill" not in reponse.json()["detail"].lower()

    cinquieme = _tenter(client, "magasin.stock")
    assert cinquieme.status_code == 401
    assert "verrouill" in cinquieme.json()["detail"].lower()

    tentatives, fin, maintenant = _etat_compte("magasin.stock")
    assert tentatives == 5
    assert fin is not None
    assert 890 <= (fin - maintenant).total_seconds() <= 900


def test_c201_verrou_non_prolonge_par_les_tentatives_suivantes(client):
    """Pendant le verrou, ni un bon ni un mauvais mot de passe ne prolonge
    ni ne raccourcit l'échéance : le déni de service est borné à 15 minutes."""
    for _ in range(5):
        assert _tenter(client, "magasin.stock").status_code == 401
    _, fin_initiale, _ = _etat_compte("magasin.stock")

    for mot_de_passe in ("faux", MOT_DE_PASSE_AGENT_STOCK, "faux", "faux"):
        reponse = _tenter(client, "magasin.stock", mot_de_passe)
        assert reponse.status_code == 401
        assert "verrouill" in reponse.json()["detail"].lower()

    tentatives, fin_finale, _ = _etat_compte("magasin.stock")
    assert tentatives == 5
    assert fin_finale == fin_initiale


def test_c201_expiration_libere_le_compte(client):
    """À l'expiration (simulée en base : attendre 15 minutes réelles n'est
    pas un test acceptable), le bon mot de passe repasse et le compteur
    repart de zéro."""
    for _ in range(5):
        assert _tenter(client, "magasin.stock").status_code == 401

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute(
            """
            UPDATE utilisateurs
               SET verrouille_jusqua = clock_timestamp() - interval '1 second'
             WHERE identifiant = 'magasin.stock'
            """
        )

    reponse = _tenter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    assert reponse.status_code == 200, reponse.text

    tentatives, fin, _ = _etat_compte("magasin.stock")
    assert tentatives == 0
    assert fin is None


def test_c201_serie_rompue_par_un_succes(client):
    """« Échecs CONSÉCUTIFS » : quatre échecs, un succès, quatre échecs ne
    verrouillent pas. Un autre compte n'est jamais affecté."""
    for _ in range(4):
        assert _tenter(client, "magasin.stock").status_code == 401
    assert _tenter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK).status_code == 200
    for _ in range(4):
        assert _tenter(client, "magasin.stock").status_code == 401

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        tentatives = conn.execute(
            "SELECT tentatives_echouees FROM utilisateurs WHERE identifiant = 'magasin.stock'"
        ).fetchone()[0]
    assert tentatives == 4
    se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)


def test_c201_seuil_decide_en_base(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        assert conn.execute(
            """
            SELECT valeur::int, a_decider
              FROM parametres WHERE cle = 'tentatives_max_connexion'
            """
        ).fetchone() == (5, False)


def test_c201_identifiant_inconnu_ne_verrouille_aucun_compte(client):
    """Le compteur de limitation protège la route, mais un identifiant
    inexistant ne peut verrouiller aucun compte réel (pas de déni de
    service par identifiants inventés)."""
    for _ in range(6):
        assert _tenter(client, "inconnu.audit").status_code == 401

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM utilisateurs WHERE tentatives_echouees > 0"
        ).fetchone()[0] == 0
        assert conn.execute(
            """
            SELECT count(*) FROM journal_connexions
             WHERE identifiant_saisi = 'inconnu.audit'
               AND motif_echec = 'identifiant_inconnu'
            """
        ).fetchone()[0] == 6


def test_c201_concurrence_compteur_sans_perte(base_reinitialisee):
    """Dix échecs simultanés : le compteur ne perd aucun incrément (5, pas
    moins) et les dix tentatives sont journalisées."""
    barriere = Barrier(10)

    def essai(_):
        with psycopg.connect(PG_ADMIN_DSN) as conn:
            conn.execute("SET LOCAL ROLE qf_app")
            barriere.wait(timeout=30)
            return conn.execute(
                """
                SELECT ok FROM verifier_connexion(
                    'magasin.stock', 'faux', NULL, 'audit_c78_concurrence'
                )
                """
            ).fetchone()[0]

    with ThreadPoolExecutor(max_workers=10) as pool:
        assert list(pool.map(essai, range(10))) == [False] * 10

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT tentatives_echouees FROM utilisateurs WHERE identifiant = 'magasin.stock'"
        ).fetchone()[0] == 5
        assert conn.execute(
            """
            SELECT count(*) FROM journal_connexions
             WHERE poste = 'audit_c78_concurrence'
            """
        ).fetchone()[0] == 10


def test_c201_concurrence_verrou_borne(base_reinitialisee):
    """Sous concurrence, le verrou posé reste borné à 15 minutes et n'est
    pas repoussé par les requêtes qui attendaient le verrou de ligne."""
    barriere = Barrier(10)

    def essai(_):
        with psycopg.connect(PG_ADMIN_DSN) as conn:
            conn.execute("SET LOCAL ROLE qf_app")
            barriere.wait(timeout=30)
            return conn.execute(
                """
                SELECT ok FROM verifier_connexion(
                    'magasin.stock', 'faux', NULL, 'audit_c78_concurrence_verrou'
                )
                """
            ).fetchone()[0]

    with ThreadPoolExecutor(max_workers=10) as pool:
        assert list(pool.map(essai, range(10))) == [False] * 10

    tentatives, fin, maintenant = _etat_compte("magasin.stock")
    assert tentatives == 5
    assert fin is not None
    assert 890 <= (fin - maintenant).total_seconds() <= 900
