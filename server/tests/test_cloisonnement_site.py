"""Un agent ne peut pas atteindre les données de l'autre site en modifiant
les paramètres de sa requête (chantier C3, exigence explicite du cycle 3).

Deux niveaux de preuve :
  1. Au niveau de l'API : aucune route n'accepte de site_id venant du
     client ; on le vérifie en en envoyant un quand même.
  2. Au niveau de la base, EN CONTOURNANT complètement l'API : même en
     forgeant une requête SQL qui demande explicitement le site 2, sous le
     rôle PostgreSQL d'un agent du site 1, la RLS ne laisse rien passer.
     C'est la preuve la plus forte : elle ne dépend d'aucune ligne de code
     applicatif, seulement des politiques posées au cycle 2.
"""

from __future__ import annotations

import psycopg

from conftest import MOT_DE_PASSE_AGENT_STOCK, PG_ADMIN_DSN, entete_autorisation, se_connecter


def test_agent_ignore_le_site_fourni_en_parametre_de_requete(client):
    """L'agent stock du Magasin (site 1) tente d'obtenir le Comptoir (site 2)
    en l'ajoutant à l'URL. La route ne lit ce paramètre nulle part : le
    résultat reste limité au site 1, quoi que le client envoie."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(session["jeton"])

    reponse_normale = client.get("/articles", headers=entetes)
    reponse_avec_site_force = client.get("/articles?site_id=2", headers=entetes)

    assert reponse_normale.status_code == reponse_avec_site_force.status_code == 200
    sites_normale = {a["site_id"] for a in reponse_normale.json()["articles"]}
    sites_forcee = {a["site_id"] for a in reponse_avec_site_force.json()["articles"]}
    assert sites_normale == sites_forcee == {1}


def test_rls_bloque_meme_en_sql_direct_hors_de_lapi(base_reinitialisee):
    """Preuve la plus forte : on contourne entièrement l'API et le code
    Python. Sous le rôle qf_agent_stock avec qf.site_id='1', une requête SQL
    qui demande EXPLICITEMENT site_id = 2 sur stocks_sites ne renvoie rien —
    et sans aucun filtre, seul le site 1 apparaît. La protection est dans
    PostgreSQL, pas dans une ligne de code applicatif qui pourrait avoir un
    bug. (Depuis le cycle 35, c'est la QUANTITÉ qui est cloisonnée : le
    catalogue, lui, est commun — la RLS de stocks_sites fait foi.)"""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_agent_stock")
                cur.execute("SELECT set_config('qf.site_id', '1', true)")

                cur.execute("SELECT article_id, site_id FROM stocks_sites WHERE site_id = 2")
                lignes_site_force = cur.fetchall()
                assert lignes_site_force == [], (
                    "la RLS aurait dû bloquer toute ligne du site 2, "
                    f"a renvoyé : {lignes_site_force}"
                )

                cur.execute("SELECT DISTINCT site_id FROM stocks_sites")
                sites_visibles = {ligne[0] for ligne in cur.fetchall()}
                assert sites_visibles == {1}, (
                    f"sans filtre, seul le site 1 devrait être visible, vu : {sites_visibles}"
                )


def test_rls_laisse_le_responsable_voir_les_deux_sites_en_sql_direct(base_reinitialisee):
    """Contre-épreuve : la même politique RLS ne bride PAS le responsable —
    ce n'est donc pas une restriction générale sur la table, mais bien un
    cloisonnement PAR RÔLE."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_responsable")
                cur.execute("SELECT DISTINCT site_id FROM stocks_sites ORDER BY site_id")
                sites_visibles = {ligne[0] for ligne in cur.fetchall()}
                assert sites_visibles == {1, 2}


def test_agent_comptoir_ne_voit_pas_les_ventes_du_magasin(base_reinitialisee):
    """Même vérification sur la table ventes, avec un agent DIFFÉRENT
    (comptoir.stock n'a pas de droit sur ventes — on utilise donc
    qf_agent_comptabilite, en insérant une vente de test sur chaque site
    directement, hors API, pour isoler la vérification RLS)."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ventes (site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc)
                    VALUES (1, 4, 'en_attente', 1000, 0, 0, 1000)
                    """
                )
                cur.execute(
                    """
                    INSERT INTO ventes (site_id, utilisateur_id, statut, sous_total_ht, taux_tva, montant_tva, total_ttc)
                    VALUES (2, 4, 'en_attente', 2000, 0, 0, 2000)
                    """
                )
        conn.commit()

        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE qf_agent_comptabilite")
                cur.execute("SELECT set_config('qf.site_id', '1', true)")
                cur.execute("SELECT site_id, total_ttc FROM ventes WHERE site_id = 2")
                assert cur.fetchall() == []
                cur.execute("SELECT DISTINCT site_id FROM ventes")
                assert {r[0] for r in cur.fetchall()} == {1}
