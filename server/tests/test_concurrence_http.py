"""Écritures concurrentes À TRAVERS L'API (écart C10-02, volet automatisable).

`db/tests/03_concurrence.sh` prouve la sérialisation du stock avec deux
sessions SQL brutes ; il ne passe pas par la route `POST /ventes`. Or deux
postes de caisse, c'est deux clients HTTP qui vendent le même article au même
instant : la route insère d'abord la ligne de vente (la clé étrangère composite
vers `stocks_sites` prend un verrou partagé sur la ligne de stock) puis appelle
`decrementer_stock_vente()` (verrou exclusif sur la MÊME ligne) — deux ventes
simultanées du même article se bloquaient mutuellement (interblocage
PostgreSQL 40P01, remonté au vendeur comme « système d'enregistrement
injoignable »). Constat de l'audit indépendant du 2026-10-23, reproduit à
partir de 2 clients simultanés.

Ces tests ne remplacent PAS l'épreuve à deux postes physiques du registre
(C10-02 reste BLOQUE_TEST_HUMAIN pour sa clôture) : ils fournissent la preuve
automatisée, rejouée par la CI, que la couche applicative ne perd ni ne
double aucune écriture sous concurrence.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)

ARTICLE_CIMENT = 1  # 6 500 FCFA, stock Magasin
ARTICLE_FER = 2     # 3 500 FCFA, stock Magasin


def _sql(requete: str, params: tuple = ()):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(requete, params or None)
            lignes = cur.fetchall() if cur.description else None
        conn.commit()
    return lignes


def _fixer_stock(article_id: int, quantite: int) -> None:
    _sql(
        "UPDATE stocks_sites SET quantite_stock = %s WHERE article_id = %s AND site_id = 1",
        (quantite, article_id),
    )


def _stock(article_id: int) -> float:
    return float(
        _sql(
            "SELECT quantite_stock FROM stocks_sites WHERE article_id = %s AND site_id = 1",
            (article_id,),
        )[0][0]
    )


def _en_parallele(travaux, travailleurs: int):
    """Lance tous les travaux d'un même élan (barrière) : sans elle, le
    démarrage échelonné des threads laisserait les requêtes s'exécuter l'une
    après l'autre et le test ne prouverait rien."""
    barriere = Barrier(len(travaux))

    def lancer(travail):
        barriere.wait(timeout=30)
        return travail()

    with ThreadPoolExecutor(max_workers=travailleurs) as executor:
        futurs = [executor.submit(lancer, t) for t in travaux]
        return [f.result(timeout=120) for f in futurs]


def _corps_vente(numero: str, lignes: list[dict]) -> dict:
    return {
        "numero_facturier": numero,
        "vendeur_id": 1,
        "site_id": 1,
        "mode_paiement": "especes",
        "lignes": lignes,
    }


def _ligne(article_id: int, prix: int) -> dict:
    return {"article_id": article_id, "quantite": 1, "prix_unitaire": prix}


def test_ventes_simultanees_du_meme_article_aboutissent_toutes(client):
    """12 ventes du même article, 12 requêtes lancées ensemble par les deux
    postes (responsable + comptabilité du Magasin) : toutes acceptées, stock
    décrémenté d'exactement 12, une recette et un mouvement par vente."""
    _fixer_stock(ARTICLE_CIMENT, 1000)
    jetons = [
        se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)["jeton"],
        se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)["jeton"],
    ]
    nb = 12

    def vente(i: int):
        return lambda: client.post(
            "/ventes",
            headers=entete_autorisation(jetons[i % 2]),
            json=_corps_vente(f"MAG-CC{i:04d}", [_ligne(ARTICLE_CIMENT, 6500)]),
        )

    reponses = _en_parallele([vente(i) for i in range(nb)], travailleurs=nb)

    codes = sorted(r.status_code for r in reponses)
    assert codes == [201] * nb, f"codes obtenus : {codes} ; corps : {[r.text for r in reponses if r.status_code != 201][:2]}"
    assert _stock(ARTICLE_CIMENT) == 1000 - nb
    assert _sql("SELECT count(*) FROM ventes WHERE numero_facturier LIKE 'MAG-CC%'")[0][0] == nb
    assert _sql(
        "SELECT count(*) FROM mouvements_stock WHERE categorie = 'vente' AND type = 'sortie' "
        "AND vente_id IN (SELECT id FROM ventes WHERE numero_facturier LIKE 'MAG-CC%')"
    )[0][0] == nb
    assert float(_sql(
        "SELECT sum(montant) FROM transactions WHERE type = 'recette' "
        "AND vente_id IN (SELECT id FROM ventes WHERE numero_facturier LIKE 'MAG-CC%')"
    )[0][0]) == 6500 * nb


def test_ventes_multi_lignes_en_ordre_oppose_ne_se_bloquent_pas(client):
    """Deux articles vendus dans des ordres opposés (ciment+fer / fer+ciment)
    en même temps : l'ordre de verrouillage est imposé par la route (article
    croissant), jamais par l'ordre de saisie du vendeur."""
    _fixer_stock(ARTICLE_CIMENT, 1000)
    _fixer_stock(ARTICLE_FER, 1000)
    jeton = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)["jeton"]
    nb = 10

    def vente(i: int):
        lignes = [_ligne(ARTICLE_CIMENT, 6500), _ligne(ARTICLE_FER, 3500)]
        if i % 2:
            lignes.reverse()
        return lambda: client.post(
            "/ventes",
            headers=entete_autorisation(jeton),
            json={k: v for k, v in _corps_vente(f"MAG-ML{i:04d}", lignes).items() if k != "site_id"},
        )

    reponses = _en_parallele([vente(i) for i in range(nb)], travailleurs=nb)

    assert sorted(r.status_code for r in reponses) == [201] * nb, [r.text for r in reponses][:2]
    assert _stock(ARTICLE_CIMENT) == 1000 - nb
    assert _stock(ARTICLE_FER) == 1000 - nb


def test_meme_numero_de_facturier_simultane_une_seule_vente(client):
    """Deux postes saisissent le même numéro de carnet au même instant :
    exactement une vente, l'autre est refusée proprement (409, jamais 5xx)."""
    _fixer_stock(ARTICLE_CIMENT, 1000)
    jetons = [
        se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)["jeton"],
        se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)["jeton"],
    ]

    def vente(i: int):
        return lambda: client.post(
            "/ventes",
            headers=entete_autorisation(jetons[i % 2]),
            json=_corps_vente("MAG-DOUBLON", [_ligne(ARTICLE_CIMENT, 6500)]),
        )

    reponses = _en_parallele([vente(i) for i in range(6)], travailleurs=6)

    codes = sorted(r.status_code for r in reponses)
    assert codes == [201] + [409] * 5, codes
    assert _sql("SELECT count(*) FROM ventes WHERE numero_facturier = 'MAG-DOUBLON'")[0][0] == 1
    assert _stock(ARTICLE_CIMENT) == 999


def test_double_annulation_simultanee_restitue_le_stock_une_seule_fois(client):
    """Deux clics simultanés sur « annuler » : le stock n'est restitué
    qu'une fois."""
    _fixer_stock(ARTICLE_CIMENT, 1000)
    responsable = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)["jeton"]
    cree = client.post(
        "/ventes",
        headers=entete_autorisation(responsable),
        json=_corps_vente("MAG-ANNUL", [_ligne(ARTICLE_CIMENT, 6500)]),
    )
    assert cree.status_code == 201, cree.text
    vente_id = cree.json()["vente_id"]
    assert _stock(ARTICLE_CIMENT) == 999

    def annuler():
        return client.post(
            f"/ventes/{vente_id}/annuler",
            headers=entete_autorisation(responsable),
            json={"motif": "double clic"},
        )

    reponses = _en_parallele([annuler for _ in range(4)], travailleurs=4)

    codes = sorted(r.status_code for r in reponses)
    assert codes.count(200) == 1, codes
    assert all(c < 500 for c in codes), codes
    assert _stock(ARTICLE_CIMENT) == 1000
