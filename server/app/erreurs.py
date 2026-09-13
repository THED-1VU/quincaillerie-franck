"""Traduction d'un refus métier de la base en réponse HTTP claire.

Partagé entre ``routes/stock.py`` (cycle 9) et ``routes/articles.py``
(cycle 11, correctif du constat trouvé au contrôle de boucle après le
cycle 9 : ``POST /articles`` ne traduisait aucune erreur, un ``site_id`` ou
``fournisseur_id`` invalide remontait en 500 générique).
"""

from __future__ import annotations

import psycopg
from fastapi import HTTPException, status


def erreur_metier(exc: psycopg.Error) -> HTTPException:
    """Traduit un refus métier de la base (CHECK ou clé étrangère) en 422
    avec le message même de la base — toujours en français, jamais un
    message brut, puisque c'est le projet qui l'a écrit (``RAISE
    EXCEPTION``) ou, pour une clé étrangère standard, un message générique
    sans nom de table ni de colonne.

    ``InsufficientPrivilege`` n'est PAS traitée ici : le gestionnaire
    global (``main.py``) répond déjà "Accès refusé." pour cette classe
    d'erreur.
    """
    if isinstance(exc, psycopg.errors.ForeignKeyViolation):
        message = "Référence invalide (site, fournisseur ou article introuvable)."
    else:
        message = (exc.diag.message_primary or "Opération refusée.").strip()
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, message)
