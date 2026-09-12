"""Correspondance entre le rôle métier (utilisateurs.role) et le rôle
PostgreSQL applicatif (chantier C3) — whitelist fermée, jamais construite à
partir d'une entrée arbitraire.
"""

from __future__ import annotations

from fastapi import HTTPException, status

_CORRESPONDANCE = {
    "responsable": "qf_responsable",
    "agent_stock": "qf_agent_stock",
    "agent_comptabilite": "qf_agent_comptabilite",
}


def role_pg(role_metier: str) -> str:
    try:
        return _CORRESPONDANCE[role_metier]
    except KeyError as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"Rôle inconnu : {role_metier!r}"
        ) from exc
