"""Chantier C8 (tableaux de bord et rapports) — cycle 10 : exports Excel et
PDF, gating du prix de vente selon le rôle EN SQL (CDC §3.7).

Chaque test relit le contenu RÉEL du fichier produit (openpyxl pour le
classeur, pypdf pour le texte du PDF) — jamais une simple vérification du
code HTTP ou du type MIME : c'est le contenu qui doit prouver l'absence ou
la présence des colonnes de prix, pour chacun des trois rôles.
"""

from __future__ import annotations

from io import BytesIO

import psycopg
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


def test_export_articles_agent_stock_limite_a_son_site(client):
    """Modèle multi-site (cycle 35) : le catalogue exporté est commun aux
    deux sites, mais la QUANTITÉ est celle du site de l'agent — une fiche
    dont le stock vit sur l'autre site apparaît avec quantité 0."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/rapports/articles", params={"format": "xlsx"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur.active
    entetes = [c.value for c in next(feuille.iter_rows(min_row=1, max_row=1))]
    idx_nom = entetes.index("nom")
    idx_qte = entetes.index("quantite_stock")
    lignes = {row[idx_nom].value: row[idx_qte].value for row in feuille.iter_rows(min_row=2)}
    assert "Clou 5 cm" in lignes  # catalogue commun, la fiche est visible
    assert lignes["Clou 5 cm"] == 0  # mais son stock (100) est au Comptoir
    assert lignes["Ciment CIM II 50 kg"] == 30  # site 1 (Magasin), bien présent


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
            "numero_facturier": "MAG-TEST0001",
            "vendeur_id": 1,
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


def test_export_ventes_agent_comptabilite_limite_a_son_site(client):
    """Constat du contrôle de boucle après le cycle 10 : une vente du
    Comptoir (site 2) ne doit jamais apparaître dans l'export d'un agent
    comptabilité du Magasin (site 1)."""
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_resp["jeton"]),
        json={
            "site_id": 2,
            "mode_paiement": "especes",
            "numero_facturier": "CPT-TEST0002",
            "vendeur_id": 2,  # « Employée Comptoir » — l'employé 1 est du Magasin, site 1
            "lignes": [{"article_id": 3, "quantite": 1, "prix_unitaire": 800}],
        },
    )
    assert reponse_vente.status_code == 201, reponse_vente.text

    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get(
        "/rapports/ventes",
        params={"format": "xlsx", "date_debut": "2000-01-01", "date_fin": "2999-12-31"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 200, reponse.text
    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur.active
    assert feuille.max_row == 1  # aucune vente du Comptoir visible pour un agent du Magasin


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


# ---------------------------------------------------------------------------
# /rapports/stock (cycle 67, écart C4-02 du REGISTRE_ECARTS_100.md) : stock
# valorisé par site, RESPONSABLE SEULEMENT — prix_achat n'est un privilège
# que du responsable (migration 008), les deux rôles agents sont refusés par
# exiger_role avant même la base. Valeurs attendues : jeu d'essai figé —
# Ciment 30 × 5 000 / 6 500 au Magasin (site 1), Clou 100 × 600 / 800 au
# Comptoir (site 2), « Article rare » 1 ≤ seuil 1 → SOUS_SEUIL.
# ---------------------------------------------------------------------------

def _lignes_export_stock(reponse) -> dict:
    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur["stock"]
    entetes = [c.value for c in next(feuille.iter_rows(min_row=1, max_row=1))]
    lignes = {}
    for row in feuille.iter_rows(min_row=2):
        ligne = {entetes[i]: row[i].value for i in range(len(entetes))}
        lignes[(ligne["nom"], ligne["site_id"])] = ligne
    return classeur, lignes


def test_export_stock_responsable_xlsx_valorisation_et_alertes(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/rapports/stock", params={"format": "xlsx"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    classeur, lignes = _lignes_export_stock(reponse)

    ciment = lignes[("Ciment CIM II 50 kg", 1)]
    assert ciment["quantite_stock"] == 30
    assert ciment["prix_achat"] == 5000 and ciment["prix_vente"] == 6500
    assert ciment["valorisation_achat"] == 150000
    assert ciment["valorisation_vente"] == 195000
    assert ciment["alerte"] == "OK"

    clou = lignes[("Clou 5 cm", 2)]
    assert clou["quantite_stock"] == 100
    assert clou["valorisation_achat"] == 60000
    assert clou["valorisation_vente"] == 80000

    rare = lignes[("Article rare", 1)]
    assert rare["quantite_stock"] == 1
    assert rare["alerte"] == "SOUS_SEUIL"  # 1 ≤ seuil 1

    # Feuille de synthèse : totaux par site, cohérents avec les lignes.
    feuille_totaux = classeur["totaux par site"]
    entetes = [c.value for c in next(feuille_totaux.iter_rows(min_row=1, max_row=1))]
    totaux = {
        row[entetes.index("site_id")].value: {
            "total_achat": row[entetes.index("total_achat")].value,
            "total_vente": row[entetes.index("total_vente")].value,
            "nb_ruptures": row[entetes.index("nb_ruptures")].value,
            "nb_sous_seuil": row[entetes.index("nb_sous_seuil")].value,
        }
        for row in feuille_totaux.iter_rows(min_row=2)
    }
    assert totaux[1]["total_achat"] == 263000   # 150 000 + 112 000 + 1 000
    assert totaux[1]["total_vente"] == 337000   # 195 000 + 140 000 + 2 000
    assert totaux[1]["nb_ruptures"] == 0
    assert totaux[1]["nb_sous_seuil"] == 1       # « Article rare »
    assert totaux[2]["total_achat"] == 60000
    assert totaux[2]["total_vente"] == 80000
    assert totaux[2]["nb_sous_seuil"] == 0


def test_export_stock_responsable_pdf_avec_valorisation(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/rapports/stock", params={"format": "pdf"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 200, reponse.text
    texte = _texte_pdf(reponse.content)
    assert "valorisation_achat" in texte and "valorisation_vente" in texte
    assert "150000" in texte  # valorisation d'achat du Ciment, jeu d'essai


def test_export_stock_agent_stock_refuse(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/rapports/stock", params={"format": "xlsx"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 403, reponse.text


def test_export_stock_agent_comptabilite_refuse(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get(
        "/rapports/stock", params={"format": "xlsx"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 403, reponse.text


def test_export_stock_format_invalide_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/rapports/stock", params={"format": "csv"}, headers=entete_autorisation(session["jeton"])
    )
    assert reponse.status_code == 422, reponse.text


# ---------------------------------------------------------------------------
# /rapports/ecarts-comptage (cycle 68, écart C7-03 du REGISTRE_ECARTS_100.md) :
# écarts de comptage valorisés au prix d'achat sur une période, régularisations
# comprises, RESPONSABLE SEULEMENT — quantite_attendue/ecart (012) et prix_achat
# (008) ne sont lisibles par aucun autre rôle. Données : comptages réels via
# l'API (magasin.stock, site 1) — Ciment 30 attendus, 25 comptés (écart -5,
# valorisation -25 000 au prix d'achat 5 000) puis régularisé ; Fer 40 attendus,
# 42 comptés (écart +2, valorisation +5 600 au prix d'achat 2 800), non
# régularisé.
# ---------------------------------------------------------------------------

def _semencer_deux_ecarts_de_comptage(client) -> None:
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    ciment = client.post(
        "/inventaire/comptages",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "moment": "matin", "quantite_comptee": 25},
    )
    assert ciment.status_code == 201, ciment.text
    fer = client.post(
        "/inventaire/comptages",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 2, "moment": "matin", "quantite_comptee": 42},
    )
    assert fer.status_code == 201, fer.text
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    regularisation = client.post(
        f"/inventaire/ecarts/{ciment.json()['comptage_id']}/regulariser",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"type_resolution": "erreur_de_comptage"},
    )
    assert regularisation.status_code == 201, regularisation.text


def _lignes_export_ecarts_comptage(reponse) -> dict:
    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur["écarts de comptage"]
    entetes = [c.value for c in next(feuille.iter_rows(min_row=1, max_row=1))]
    lignes = {}
    for row in feuille.iter_rows(min_row=2):
        ligne = {entetes[i]: row[i].value for i in range(len(entetes))}
        lignes[(ligne["nom"], ligne["site_id"])] = ligne
    return classeur, lignes


_PERIODE_TOUTE = {"date_debut": "2000-01-01", "date_fin": "2999-12-31"}


def test_export_ecarts_comptage_responsable_xlsx_valorisation_et_regularisation(client):
    _semencer_deux_ecarts_de_comptage(client)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    params = {**_PERIODE_TOUTE, "format": "xlsx"}
    reponse = client.get("/rapports/ecarts-comptage", params=params,
                         headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    classeur, lignes = _lignes_export_ecarts_comptage(reponse)

    ciment = lignes[("Ciment CIM II 50 kg", 1)]
    assert ciment["quantite_comptee"] == 25 and ciment["quantite_attendue"] == 30
    assert ciment["ecart"] == -5
    assert ciment["prix_achat"] == 5000
    assert ciment["valorisation_ecart"] == -25000
    assert ciment["type_resolution"] == "erreur_de_comptage"

    fer = lignes[("Fer à béton 8 mm", 1)]
    assert fer["ecart"] == 2
    assert fer["valorisation_ecart"] == 5600
    assert not fer["type_resolution"]  # non régularisé -> cellule vide

    # Feuille de synthèse : totaux cohérents avec les lignes.
    feuille_totaux = classeur["totaux"]
    entetes = [c.value for c in next(feuille_totaux.iter_rows(min_row=1, max_row=1))]
    total = {entetes[i]: row[i].value for row in feuille_totaux.iter_rows(min_row=2, max_row=2)
             for i in range(len(entetes))}
    assert total["nb_ecarts"] == 2
    assert total["ecart_cumule"] == -3
    assert total["valorisation_cumulee"] == -19400
    assert total["nb_sans_regularisation"] == 1


def test_export_ecarts_comptage_responsable_pdf_avec_valorisation(client):
    _semencer_deux_ecarts_de_comptage(client)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    params = {**_PERIODE_TOUTE, "format": "pdf"}
    reponse = client.get("/rapports/ecarts-comptage", params=params,
                         headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    texte = _texte_pdf(reponse.content)
    assert "valorisation_ecart" in texte
    assert "25000" in texte
    assert "erreur_de_comptage" in texte


def test_export_ecarts_comptage_hors_periode_vide(client):
    _semencer_deux_ecarts_de_comptage(client)
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    params = {"date_debut": "2000-01-01", "date_fin": "2000-01-02", "format": "xlsx"}
    reponse = client.get("/rapports/ecarts-comptage", params=params,
                         headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur["écarts de comptage"]
    assert feuille.max_row == 1  # en-têtes seuls
    feuille_totaux = classeur["totaux"]
    entetes = [c.value for c in next(feuille_totaux.iter_rows(min_row=1, max_row=1))]
    total = {entetes[i]: row[i].value for row in feuille_totaux.iter_rows(min_row=2, max_row=2)
             for i in range(len(entetes))}
    assert total["nb_ecarts"] == 0


def test_export_ecarts_comptage_agent_stock_refuse(client):
    _semencer_deux_ecarts_de_comptage(client)
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    params = {**_PERIODE_TOUTE, "format": "xlsx"}
    reponse = client.get("/rapports/ecarts-comptage", params=params,
                         headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 403, reponse.text


def test_export_ecarts_comptage_agent_comptabilite_refuse(client):
    _semencer_deux_ecarts_de_comptage(client)
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    params = {**_PERIODE_TOUTE, "format": "xlsx"}
    reponse = client.get("/rapports/ecarts-comptage", params=params,
                         headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 403, reponse.text


def test_export_ecarts_comptage_format_invalide_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    params = {**_PERIODE_TOUTE, "format": "csv"}
    reponse = client.get("/rapports/ecarts-comptage", params=params,
                         headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 422, reponse.text


def test_export_ecarts_comptage_dates_invalides_refusees(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    params = {"date_debut": "pas-une-date", "date_fin": "2026-10-21", "format": "xlsx"}
    reponse = client.get("/rapports/ecarts-comptage", params=params,
                         headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 422, reponse.text
    params = {"date_debut": "2026-10-22", "date_fin": "2026-10-21", "format": "xlsx"}
    reponse = client.get("/rapports/ecarts-comptage", params=params,
                         headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 422, reponse.text



# ---------------------------------------------------------------------------
# /rapports/ecarts-prix-vendeurs (cycle 58, point c Q5, décidé 2026-09-18) :
# 10 % sous le prix catalogue, en configuration, signale SANS jamais bloquer.
# ---------------------------------------------------------------------------

def _vendre(client, session, *, prix_unitaire, vendeur_id=1, site_id=1,
            numero="MAG-ECART01", article_id=1):
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "site_id": site_id,
            "mode_paiement": "especes",
            "numero_facturier": numero,
            "vendeur_id": vendeur_id,
            "lignes": [{"article_id": article_id, "quantite": 1,
                        "prix_unitaire": prix_unitaire}],
        },
    )
    assert reponse.status_code == 201, reponse.text


def test_ecarts_prix_signale_au_dela_du_seuil_pas_en_deca(client):
    """Ciment catalogue 6 500 : 5 720 payé = 12 % sous le catalogue →
    SIGNALÉ ; 5 980 payé = 8 % → écart visible mais NON signalé (10 %)."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _vendre(client, session, prix_unitaire=5720, numero="MAG-ECART01")
    _vendre(client, session, prix_unitaire=5980, numero="MAG-ECART02")

    reponse = client.get(
        "/rapports/ecarts-prix-vendeurs",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["seuil_pct"] == 10
    assert len(corps["vendeurs"]) == 1
    groupe = corps["vendeurs"][0]
    assert groupe["nb_signalees"] == 1
    assert groupe["nb_lignes"] == 2
    par_prix = {l["prix_unitaire"]: l for l in groupe["lignes"]}
    assert par_prix[5720]["signale"] is True
    assert par_prix[5720]["ecart_pct"] == 12
    assert par_prix[5980]["signale"] is False
    assert par_prix[5980]["ecart_pct"] == 8


def test_ecarts_prix_seuil_reellement_configurable(client):
    """Le seuil est une VALEUR DE CONFIGURATION (décision 2026-09-18) : le
    faire passer à 5 % fait basculer l'écart de 8 % au signalement, sans
    aucun changement de code."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _vendre(client, session, prix_unitaire=5980, numero="MAG-ECART03")  # 8 %

    reponse = client.get(
        "/rapports/ecarts-prix-vendeurs",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.json()["vendeurs"][0]["lignes"][0]["signale"] is False

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE parametres SET valeur = '5' WHERE cle = 'seuil_ecart_prix_vendeur'"
            )
        conn.commit()

    reponse = client.get(
        "/rapports/ecarts-prix-vendeurs",
        headers=entete_autorisation(session["jeton"]),
    )
    corps = reponse.json()
    assert corps["seuil_pct"] == 5
    assert corps["vendeurs"][0]["lignes"][0]["signale"] is True


def test_ecarts_prix_prix_au_dessus_du_catalogue_visible_jamais_signale(client):
    """Upsell toléré (037, point d) : 7 020 payé contre 6 500 de catalogue
    = écart NÉGATIF restitué tel quel, jamais signalé — la décision ne vise
    que les prix négociés SOUS le catalogue."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _vendre(client, session, prix_unitaire=7020, numero="MAG-ECART04")

    reponse = client.get(
        "/rapports/ecarts-prix-vendeurs",
        headers=entete_autorisation(session["jeton"]),
    )
    groupe = reponse.json()["vendeurs"][0]
    ligne = groupe["lignes"][0]
    assert ligne["ecart_unitaire"] == -520
    assert ligne["signale"] is False
    assert groupe["nb_signalees"] == 0


def test_ecarts_prix_agent_stock_refuse(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/rapports/ecarts-prix-vendeurs",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 403, reponse.text


def test_ecarts_prix_agent_comptabilite_autorise_et_limite_a_son_site(client):
    """RLS PAR LA VUE (migration 048, SECURITY INVOKER) : un agent
    comptabilité du Magasin voit les écarts de SON site et JAMAIS ceux du
    Comptoir — une vue classique (security definer) contournerait la RLS
    et montrerait les deux sites."""
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _vendre(client, session_resp, prix_unitaire=5720, vendeur_id=1, site_id=1,
            numero="MAG-ECART05")
    _vendre(client, session_resp, prix_unitaire=700, vendeur_id=2, site_id=2,
            numero="CPT-ECART06", article_id=3)  # Clou 5 cm, catalogue 800 = 12,5 %

    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get(
        "/rapports/ecarts-prix-vendeurs",
        headers=entete_autorisation(session["jeton"]),
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    numeros = {
        l["numero_facturier"] for g in corps["vendeurs"] for l in g["lignes"]
    }
    assert "MAG-ECART05" in numeros
    assert "CPT-ECART06" not in numeros


def test_ecarts_prix_periode_et_dates_invalides(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    _vendre(client, session, prix_unitaire=5720, numero="MAG-ECART07")

    hors_periode = client.get(
        "/rapports/ecarts-prix-vendeurs",
        params={"date_debut": "2000-01-01", "date_fin": "2000-01-02"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert hors_periode.status_code == 200, hors_periode.text
    assert hors_periode.json()["vendeurs"] == []

    bonne_periode = client.get(
        "/rapports/ecarts-prix-vendeurs",
        params={"date_debut": "2000-01-01", "date_fin": "2999-12-31"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert len(bonne_periode.json()["vendeurs"]) == 1

    invalide = client.get(
        "/rapports/ecarts-prix-vendeurs",
        params={"date_debut": "n'importe quoi"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert invalide.status_code == 422, invalide.text

    inversee = client.get(
        "/rapports/ecarts-prix-vendeurs",
        params={"date_debut": "2999-12-31", "date_fin": "2000-01-01"},
        headers=entete_autorisation(session["jeton"]),
    )
    assert inversee.status_code == 422, inversee.text
