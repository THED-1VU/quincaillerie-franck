"""Configuration du serveur, lue depuis config.ini (jamais commité).

Voir config.example.ini pour la structure attendue. Aucun secret n'est écrit
en dur dans le code : tout vient de ce fichier, ou d'un chemin indiqué par la
variable d'environnement QF_CONFIG (utile pour les tests).
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

RACINE_SERVEUR = Path(__file__).resolve().parent.parent
CONFIG_PAR_DEFAUT = RACINE_SERVEUR / "config.ini"

# Rôles PostgreSQL applicatifs valides — voir db/migrations/008_roles_applicatifs.sql.
ROLES_VALIDES = ("qf_responsable", "qf_agent_stock", "qf_agent_comptabilite")


class ErreurConfiguration(RuntimeError):
    """Configuration absente, incomplète ou dangereuse (ex. compte superutilisateur)."""


@dataclass(frozen=True)
class ConfigBase:
    host: str
    port: int
    dbname: str
    user: str
    password: str


@dataclass(frozen=True)
class ConfigApi:
    secret_key: str
    duree_session_minutes: int
    tentatives_max_par_minute: int


@dataclass(frozen=True)
class Config:
    base: ConfigBase
    api: ConfigApi


def charger_config(chemin: Optional[Path] = None) -> Config:
    chemin = chemin or Path(os.environ.get("QF_CONFIG", str(CONFIG_PAR_DEFAUT)))
    if not chemin.exists():
        raise ErreurConfiguration(
            f"Fichier de configuration introuvable : {chemin}. "
            "Copiez config.example.ini vers config.ini et renseignez les valeurs."
        )

    cp = configparser.ConfigParser()
    cp.read(chemin, encoding="utf-8")

    base = ConfigBase(
        host=cp.get("database", "host", fallback="127.0.0.1"),
        port=cp.getint("database", "port", fallback=5432),
        dbname=cp.get("database", "dbname"),
        user=cp.get("database", "user"),
        password=cp.get("database", "password"),
    )

    # SÉCURITÉ (chantier C11) : le serveur ne doit JAMAIS se connecter en
    # superutilisateur. C'est exactement la faille corrigée au cycle 2 —
    # inutile de la rouvrir ici par une configuration hâtive.
    if base.user == "postgres":
        raise ErreurConfiguration(
            "Configuration refusée : l'application ne doit jamais se "
            "connecter avec le compte superutilisateur 'postgres'. "
            "Utilisez le rôle applicatif qf_app "
            "(voir db/outils/definir_mot_de_passe_app.sql)."
        )

    secret_key = cp.get("api", "secret_key", fallback="")
    if not secret_key or secret_key.startswith("A_GENERER"):
        raise ErreurConfiguration(
            "Configuration refusée : api.secret_key n'a pas été renseignée "
            "(valeur d'exemple encore présente). Générez-en une avec : "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )
    if len(secret_key) < 32:
        raise ErreurConfiguration(
            "Configuration refusée : api.secret_key est trop courte "
            "(32 caractères hexadécimaux minimum attendus)."
        )

    api = ConfigApi(
        secret_key=secret_key,
        duree_session_minutes=cp.getint("api", "duree_session_minutes", fallback=480),
        tentatives_max_par_minute=cp.getint("api", "tentatives_max_par_minute", fallback=10),
    )

    return Config(base=base, api=api)
