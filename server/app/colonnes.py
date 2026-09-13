"""Listes de colonnes autorisées par rôle, pour les requêtes SQL qui gèrent
elles-mêmes leur cloisonnement (lecture directe et exports — chantiers C3
et C8).

Un seul point de définition : la même liste sert à ``GET /articles``
(``routes/demonstration.py``, cycle 3) et aux exports de
``routes/rapports.py`` (cycle 10), pour que le gating du prix de vente par
rôle (CDC §3.7) reste identique dans les deux cas — jamais deux listes qui
pourraient diverger avec le temps.

Whitelist fermée, jamais construite à partir d'une entrée de la requête
HTTP : c'est ce qui rend une injection SQL sur le nom de colonne impossible
ici, pas une validation a posteriori.
"""

from __future__ import annotations

COLONNES_ARTICLES = {
    "agent_stock": "id, nom, unite, quantite_stock, seuil_alerte, site_id",
    "agent_comptabilite": "id, nom, unite, prix_vente, site_id",
    "responsable": "id, nom, unite, prix_achat, prix_vente, quantite_stock, seuil_alerte, site_id",
}
