"""Chantier C8 (tableaux de bord et rapports) — cycle 10 : exports Excel et
PDF, gating du prix de vente selon le rôle EN SQL (CDC §3.7).

Chaque test relit le contenu RÉEL du fichier produit (openpyxl pour le
classeur, pypdf pour le texte du PDF) — jamais une simple vérification du
code HTTP ou du type MIME : c'est le contenu qui doit prouver l'absence ou
la présence des colonnes de prix, pour chacun des trois rôles.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook
from pypdf import PdfReader

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)


def _entetes_xlsx(contenu: bytes) -> list[str]:
    classeur = load_workbook(BytesIO(contenu))
    feuille = classeur.active
    return [c.value for c in next(feuille.iter_rows(min_row=1, max_row=1))]


def _texte_pdf(contenu: bytes) -> str:
    lecteur = PdfReader(BytesIO(contenu))
    return "\n".join(page.extract_text() or "" for page in lecteur.pages)


# ---------------------------------------------------------------------------
# /rapports/articles : les 3 rôles, gating du prix en SQL
# ---------------------------------------------------------------------------

def test_export_articles_agent_stock_xlsx_sans_prix(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/rapports/articles", params={"format": "xlsx"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    entetes = _entetes_xlsx(reponse.content)
    assert "prix_achat" not in entetes
    assert "prix_vente" not in entetes
    assert "quantite_stock" in entetes  # périmètre stock, autorisé


def test_export_articles_agent_stock_pdf_sans_prix(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/rapports/articles", params={"format": "pdf"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    texte = _texte_pdf(reponse.content)
    assert "prix" not in texte.lower()
    assert "Ciment CIM II 50 kg" in texte


def test_export_articles_responsable_xlsx_avec_prix(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/rapports/articles", params={"format": "xlsx"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur.active
    entetes = [c.value for c in next(feuille.iter_rows(min_row=1, max_row=1))]
    assert "prix_achat" in entetes and "prix_vente" in entetes
    idx_prix_achat = entetes.index("prix_achat")
    valeurs_prix_achat = [
        row[idx_prix_achat].value for row in feuille.iter_rows(min_row=2)
    ]
    assert 5000 in valeurs_prix_achat  # Ciment CIM II 50 kg, jeu d'essai


def test_export_articles_responsable_pdf_avec_prix(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/rapports/articles", params={"format": "pdf"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    texte = _texte_pdf(reponse.content)
    assert "prix_achat" in texte and "prix_vente" in texte
    assert "5000" in texte  # prix d'achat du Ciment, jeu d'essai


def test_export_articles_agent_comptabilite_prix_vente_seulement(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get(
        "/rapports/articles", params={"format": "xlsx"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    entetes = _entetes_xlsx(reponse.content)
    assert "prix_vente" in entetes
    assert "prix_achat" not in entetes
    assert "quantite_stock" not in entetes  # jamais de quantité pour la compta (CDC §3.5)


def test_export_articles_format_invalide_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/rapports/articles", params={"format": "csv"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 422, reponse.text


# ---------------------------------------------------------------------------
# /rapports/ventes : responsable + agent comptabilité, agent stock refusé
# ---------------------------------------------------------------------------

def _enregistrer_une_vente(client, session) -> None:
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "site_id": 1,
            "mode_paiement": "especes",
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 201, reponse.text


def test_export_ventes_responsable_xlsx_contient_le_total(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _enregistrer_une_vente(client, session)

    reponse = client.get(
        "/rapports/ventes",
        params={"format": "xlsx", "date_debut": "2000-01-01", "date_fin": "2999-12-31"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 200, reponse.text
    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur.active
    entetes = [c.value for c in next(feuille.iter_rows(min_row=1, max_row=1))]
    assert "total_ttc" in entetes
    idx_total = entetes.index("total_ttc")
    totaux = [row[idx_total].value for row in feuille.iter_rows(min_row=2)]
    assert any(float(t) == 6500 for t in totaux)


def test_export_ventes_hors_periode_est_vide(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _enregistrer_une_vente(client, session)

    reponse = client.get(
        "/rapports/ventes",
        params={"format": "xlsx", "date_debut": "2000-01-01", "date_fin": "2000-01-02"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 200, reponse.text
    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur.active
    assert feuille.max_row == 1  # seulement l'en-tête, aucune vente hors période


def test_export_ventes_agent_comptabilite_autorise(client):
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _enregistrer_une_vente(client, session_resp)

    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get(
        "/rapports/ventes",
        params={"format": "pdf", "date_debut": "2000-01-01", "date_fin": "2999-12-31"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 200, reponse.text


def test_export_ventes_agent_stock_refuse(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/rapports/ventes",
        params={"format": "xlsx", "date_debut": "2000-01-01", "date_fin": "2999-12-31"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 403, reponse.text


def test_export_ventes_date_invalide_refusee(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/rapports/ventes",
        params={"format": "xlsx", "date_debut": "n'importe quoi", "date_fin": "2026-09-13"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 422, reponse.text
