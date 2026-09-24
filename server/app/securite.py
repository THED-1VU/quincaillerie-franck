"""Sécurité applicative (chantier C11) : hachage des mots de passe, jetons de
session signés, limitation de débit sur la connexion.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Optional

import bcrypt

# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------
# PRÉFIXE $2a$ OBLIGATOIRE. pgcrypto (utilisé par verifier_connexion, côté
# base) ne valide PAS un hachage bcrypt au format $2b$, celui que produit
# bcrypt.gensalt() par défaut — vérifié par exécution, dans les deux sens
# (bon mot de passe -> vrai, mauvais -> faux), avant d'écrire cette fonction.
# Voir db/migrations/009_authentification.sql pour le détail du piège.
_TOURS_BCRYPT = 12


def hacher_mot_de_passe(mot_de_passe_clair: str) -> str:
    sel = bcrypt.gensalt(rounds=_TOURS_BCRYPT, prefix=b"2a")
    return bcrypt.hashpw(mot_de_passe_clair.encode("utf-8"), sel).decode("ascii")


# ---------------------------------------------------------------------------
# Jetons de session — signés (HMAC-SHA256), sans état côté serveur
# ---------------------------------------------------------------------------
# Choix technique délibéré depuis le cycle 3 : un jeton signé et borné dans
# le temps, ne nécessitant ni table ni magasin partagé pour sa VALIDITÉ.
# Limite corrigée au cycle 21 (chantier C11) : chaque jeton porte désormais
# un identifiant aléatoire (jti) que la route de déconnexion peut révoquer
# dans PostgreSQL (db/migrations/018_revocation_jetons.sql) — un magasin
# déjà partagé entre plusieurs processus applicatifs, donc résout les deux
# limites documentées ici à la fois (révocation ET partage multi-processus)
# sans dépendance nouvelle. La vérification de signature/expiration reste
# ICI, sans accès à la base — seule deps.py, qui a déjà une connexion,
# vérifie la révocation après coup.


class JetonInvalide(Exception):
    """Jeton absent, mal formé, signature invalide ou expiré."""


@dataclass(frozen=True)
class Session:
    utilisateur_id: int
    role: str
    site_id: Optional[int]
    nom_complet: str
    doit_changer_mot_de_passe: bool
    emis_a: int
    expire_a: int
    jti: str
    roles: tuple = ()

    def avec_role(self, role_effectif: str) -> "Session":
        """Session identique, mais avec ``role`` remplacé par le rôle retenu
        pour CETTE requête (chantier C3, cumul de rôles) : le rôle effectif
        sert au ``SET ROLE`` PostgreSQL, tandis que ``roles`` conserve la
        liste complète pour les contrôles d'habilitation."""
        from dataclasses import replace

        return replace(self, role=role_effectif)


def _b64_encoder(donnees: bytes) -> bytes:
    return base64.urlsafe_b64encode(donnees).rstrip(b"=")


def _b64_decoder(donnees: bytes) -> bytes:
    return base64.urlsafe_b64decode(donnees + b"=" * (-len(donnees) % 4))


class GestionnaireSessions:
    def __init__(self, secret_key: str, duree_minutes: int) -> None:
        self._cle = secret_key.encode("utf-8")
        self._duree_secondes = duree_minutes * 60

    def emettre(
        self,
        *,
        utilisateur_id: int,
        role: str,
        site_id: Optional[int],
        nom_complet: str,
        doit_changer_mot_de_passe: bool,
        duree_minutes: int | None = None,
        roles: list | None = None,
    ) -> str:
        maintenant = int(time.time())
        duree_secondes = (
            duree_minutes * 60 if duree_minutes is not None else self._duree_secondes
        )
        charge = {
            "uid": utilisateur_id,
            "role": role,
            # Cumul de rôles (chantier C3, cycle 41) : liste complète des
            # rôles effectifs. Absente des jetons antérieurs -> (role,).
            "roles": roles if roles is not None else [role],
            "site": site_id,
            "nom": nom_complet,
            "chg": doit_changer_mot_de_passe,
            "iat": maintenant,
            "exp": maintenant + duree_secondes,
            # Identifiant du jeton (cycle 21) : 16 octets aléatoires en
            # hexadécimal (32 caractères, tient dans jetons_revoques.jti
            # VARCHAR(32)) — permet de révoquer CE jeton précis, jamais
            # deviné à l'avance puisqu'il ne dépend d'aucune donnée connue
            # de l'utilisateur.
            "jti": secrets.token_hex(16),
        }
        corps = _b64_encoder(json.dumps(charge, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(self._cle, corps, hashlib.sha256).digest()
        return (corps + b"." + _b64_encoder(signature)).decode("ascii")

    def verifier(self, jeton: str) -> Session:
        try:
            corps_b64, sig_b64 = jeton.encode("ascii").split(b".", 1)
        except (ValueError, UnicodeEncodeError) as exc:
            raise JetonInvalide("Format de jeton invalide.") from exc

        signature_attendue = hmac.new(self._cle, corps_b64, hashlib.sha256).digest()
        try:
            signature_recue = _b64_decoder(sig_b64)
        except Exception as exc:  # noqa: BLE001 - toute erreur de décodage = jeton invalide
            raise JetonInvalide("Signature illisible.") from exc

        # Comparaison à temps constant : ne pas laisser un attaquant déduire
        # la signature attendue octet par octet via le temps de réponse.
        if not hmac.compare_digest(signature_attendue, signature_recue):
            raise JetonInvalide("Signature invalide.")

        try:
            charge = json.loads(_b64_decoder(corps_b64))
        except Exception as exc:  # noqa: BLE001
            raise JetonInvalide("Contenu de jeton illisible.") from exc

        if int(time.time()) >= charge.get("exp", 0):
            raise JetonInvalide("Jeton expiré, reconnectez-vous.")

        return Session(
            utilisateur_id=charge["uid"],
            role=charge["role"],
            site_id=charge["site"],
            nom_complet=charge["nom"],
            doit_changer_mot_de_passe=charge["chg"],
            emis_a=charge["iat"],
            expire_a=charge["exp"],
            # .get() : un jeton émis avant le cycle 21 (déjà en circulation
            # au moment du déploiement) n'a pas de "jti" — reste vérifiable
            # jusqu'à sa propre expiration naturelle, simplement jamais
            # révocable a posteriori (aucune régression : il ne l'était pas
            # non plus avant ce cycle).
            jti=charge.get("jti", ""),
            # Cumul de rôles (chantier C3, cycle 41) : un jeton antérieur n'a
            # pas de "roles" — il retombe sur son rôle principal seul.
            roles=tuple(charge.get("roles") or [charge["role"]]),
        )


# ---------------------------------------------------------------------------
# Limitation de débit — fenêtre glissante, en mémoire
# ---------------------------------------------------------------------------
# Limite PAR PROCESSUS. Protection technique contre le bourrage de mots de
# passe (« credential stuffing »), distincte du verrouillage de compte qui,
# lui, est une règle métier posée en base (parametres.tentatives_max_connexion,
# appliquée par verifier_connexion). Documentée comme limite d'implémentation :
# un déploiement à plusieurs travailleurs voudrait un compteur partagé.


class LimiteurDebit:
    def __init__(self, max_essais: int, fenetre_secondes: int = 60) -> None:
        self.max_essais = max_essais
        self.fenetre_secondes = fenetre_secondes
        self._historique: dict[str, list[float]] = {}

    def autorise(self, cle: str) -> bool:
        maintenant = time.monotonic()
        essais = self._historique.setdefault(cle, [])
        essais[:] = [t for t in essais if maintenant - t < self.fenetre_secondes]
        if len(essais) >= self.max_essais:
            return False
        essais.append(maintenant)
        return True

    def reinitialiser(self, cle: str) -> None:
        self._historique.pop(cle, None)
