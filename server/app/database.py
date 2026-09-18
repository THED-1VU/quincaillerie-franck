"""Accès à PostgreSQL — SEULE couche du serveur qui parle à la base.

Toutes les requêtes sont paramétrées (jamais de f-string ni de concaténation
dans du SQL — chantier C11). Le rôle PostgreSQL de la session est fixé par
``SET LOCAL ROLE``, à l'intérieur d'une transaction : il revient
automatiquement au rôle de connexion (qf_app) au COMMIT/ROLLBACK, même si la
connexion est réutilisée par la suite.

C'est ICI, et nulle part ailleurs, que se fait la bascule vers le rôle de
l'utilisateur authentifié (chantier C3) : aucune route ne doit vérifier un
droit elle-même, c'est PostgreSQL qui le fait, via les privilèges par colonne
et les politiques RLS posées au cycle 2.

Trouvé par exécution lors du contrôle de boucle après le cycle 7 : la base
de développement tournait en ``Europe/Paris`` alors que la boutique est à
Batouri, Cameroun (``Africa/Douala``, UTC+1, jamais d'heure d'été) — un
décalage silencieux sur tout ce qui dépend du « jour » (CURRENT_DATE,
NOW()) : unicité d'un comptage par jour (migration 003), écrans « du jour »
(chantiers C5 et C7). Fixé au niveau de la base par la migration 013
(``ALTER DATABASE ... SET timezone``), et RENFORCÉ ICI à chaque connexion,
pour ne dépendre ni d'un réglage de base qu'un déploiement pourrait oublier
d'appliquer, ni du fuseau du système d'exploitation du poste serveur.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .config import ROLES_VALIDES, Config

# La boutique est à Batouri (Cameroun) : jamais hérité du système
# d'exploitation du poste serveur, ni d'une variable d'environnement. Voir
# aussi db/migrations/013_fuseau_horaire_boutique.sql (même valeur, au
# niveau de la base).
FUSEAU_HORAIRE_BOUTIQUE = "Africa/Douala"


class BaseDeDonnees:
    def __init__(self, config: Config) -> None:
        self._config = config

    def _parametres_connexion(self) -> dict:
        b = self._config.base
        return dict(
            host=b.host, port=b.port, dbname=b.dbname, user=b.user, password=b.password,
            # Cycle 28 : trouvé par exécution (PostgreSQL arrêté délibérément,
            # avec autorisation) — SANS ceci, une tentative de connexion
            # pouvait rester bloquée 2 min 10 s avant d'échouer (dépend du
            # comportement TCP de l'OS, pas d'un réglage applicatif). Chaque
            # tentative bloquée immobilisait aussi un thread du serveur —
            # quelques clients qui réessaient pendant une panne suffiraient à
            # épuiser les threads disponibles et à geler des requêtes SANS
            # RAPPORT avec la base. 5 s : largement suffisant sur le réseau
            # local de la boutique, assez court pour rester perçu comme "une
            # vraie panne" par le vendeur (voir CONNEXION_ECHOUEE ci-dessous).
            connect_timeout=5,
        )

    @contextmanager
    def connexion_anonyme(self) -> Iterator[psycopg.Connection]:
        """Connexion sous qf_app, SANS bascule de rôle.

        Réservée aux opérations qui doivent avoir lieu AVANT que l'on sache
        qui se connecte : vérifier des identifiants. qf_app est NOINHERIT et
        ne porte par lui-même aucun droit sur les tables métier — seules les
        fonctions explicitement accordées à qf_app (verifier_connexion) sont
        utilisables ici.
        """
        with psycopg.connect(**self._parametres_connexion(), row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('TimeZone', %s, false)", (FUSEAU_HORAIRE_BOUTIQUE,))
            yield conn

    @contextmanager
    def connexion_pour(
        self,
        role: str,
        *,
        site_id: Optional[int] = None,
        utilisateur_id: Optional[int] = None,
    ) -> Iterator[psycopg.Connection]:
        """Connexion basculée, POUR LA DURÉE DE LA TRANSACTION, vers le rôle
        PostgreSQL de l'utilisateur authentifié.

        - ``role`` doit être l'un de ROLES_VALIDES (whitelist fermée : jamais
          construit à partir d'une donnée arbitraire de la requête HTTP).
        - ``site_id`` alimente qf_site_courant() : les politiques RLS
          d'articles/ventes/transactions/mouvements/comptages s'appuient
          dessus pour cloisonner par site.
        - ``utilisateur_id`` alimente qf_utilisateur_courant() : sert au
          libre-service (changer son propre mot de passe).

        ``SET LOCAL`` et ``set_config(..., true)`` ne durent que la
        transaction en cours : au COMMIT ou au ROLLBACK, la connexion revient
        au rôle qf_app, prête à être réutilisée sans fuite de contexte.
        """
        if role not in ROLES_VALIDES:
            raise ValueError(f"Rôle inconnu : {role!r}")

        with psycopg.connect(**self._parametres_connexion(), row_factory=dict_row) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    # Un nom de rôle ne se paramètre pas comme une valeur
                    # ordinaire (SET n'accepte pas les paramètres liés) ; on
                    # compose un identifiant SQL sûr — la valeur vient d'une
                    # whitelist fermée vérifiée juste au-dessus, jamais
                    # directement d'une entrée utilisateur.
                    cur.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                    cur.execute("SELECT set_config('TimeZone', %s, true)", (FUSEAU_HORAIRE_BOUTIQUE,))
                    if site_id is not None:
                        cur.execute("SELECT set_config('qf.site_id', %s, true)", (str(site_id),))
                    if utilisateur_id is not None:
                        cur.execute(
                            "SELECT set_config('qf.utilisateur_id', %s, true)",
                            (str(utilisateur_id),),
                        )
                yield conn
