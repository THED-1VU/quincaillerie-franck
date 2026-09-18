"""Configuration de l'affichage (cycle 28) : le logo DU CLIENT — distinct du
logo Akuma (marque de l'éditeur, fichier statique livré avec la maquette,
jamais remplaçable par l'utilisateur, voir ``maquette/assets/``).

Réservé au responsable pour le téléversement (``POST``) — cloisonné au
niveau de la REQUÊTE (``exiger_role``), pas seulement en cachant un bouton
à l'écran ; voir ``server/tests/test_configuration.py``, un jeton
``agent_*`` doit recevoir 403 avant même de toucher un fichier.

La lecture (``GET``) reste PUBLIQUE, sans session : un logo de boutique
n'est pas une donnée sensible (même principe que ``favicon.svg``, déjà servi
sans authentification), et l'écran de connexion — avant toute session — doit
pouvoir l'afficher à côté du nom de la boutique.

Le fichier lui-même vit HORS BASE, dans un dossier dédié (voir
``DOSSIER_LOGO`` ci-dessous) : la base (migration 021) ne garde que
l'extension du fichier présent, jamais son contenu. Inclus dans la
sauvegarde/restauration (``db/outils/sauvegarder.ps1``/``restaurer.ps1``) —
un logo perdu à la restauration serait une régression.
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from ..deps import exiger_role, obtenir_bd
from ..roles import role_pg
from ..securite import Session

routeur = APIRouter(prefix="/configuration", tags=["configuration"])

# Même limite déjà documentée pour MAQUETTE_DIR (server/app/main.py,
# chantier C0, « reste à faire ») : ce chemin, résolu depuis __file__,
# fonctionne en développement (uvicorn lancé depuis le dépôt) mais PAS
# encore dans l'exécutable autonome empaqueté (PyInstaller --onefile extrait
# dans un dossier temporaire éphémère, effacé à la fermeture) — signalé ici
# plutôt que silencieusement hérité sans qu'on en reparle.
RACINE_DEPOT = Path(__file__).resolve().parent.parent.parent.parent
DOSSIER_LOGO = RACINE_DEPOT / "server" / "donnees" / "logo_boutique"

# Choix TECHNIQUE (pas une décision métier du propriétaire, donc pas de
# sentinelle « a_definir ») : 2 Mo est largement suffisant pour un logo —
# une image de cette taille couvre déjà un PNG non compressé à haute
# résolution — tout en restant petit pour la sauvegarde et le chargement de
# l'écran de connexion.
TAILLE_MAX_OCTETS = 2 * 1024 * 1024

# Signature RÉELLE du contenu (octets de début de fichier), jamais
# l'extension du nom ni le Content-Type déclaré par le navigateur — les deux
# sont manipulables sans rapport avec le contenu réel du fichier envoyé.
_SIGNATURES: dict[bytes, str] = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
}


def _extension_reelle(contenu: bytes) -> str | None:
    for signature, extension in _SIGNATURES.items():
        if contenu.startswith(signature):
            return extension
    return None


@routeur.post("/logo", status_code=status.HTTP_204_NO_CONTENT)
async def televerser_logo(
    request: Request,
    fichier: UploadFile = File(...),
    session: Session = Depends(exiger_role("responsable")),
) -> None:
    """Remplace le logo actuel de la boutique (ou en crée un premier). Un
    seul fichier à la fois : l'ancien est supprimé, quel qu'ait été son
    format d'origine."""
    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Fichier trop volumineux ({len(contenu) // 1024} Ko) — "
            f"maximum {TAILLE_MAX_OCTETS // 1024} Ko.",
        )

    extension = _extension_reelle(contenu)
    if extension is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Format non reconnu : seuls PNG et JPEG sont acceptés (vérifié "
            "sur le contenu réel du fichier, jamais sur son nom).",
        )

    # Décodage RÉEL, pas seulement la signature : un fichier peut porter le
    # bon en-tête sans être une image valide (tronqué, corrompu). Réencodage
    # SYSTÉMATIQUE ensuite — jamais les octets bruts envoyés par le client
    # écrits tels quels — pour ne jamais stocker un fichier qui serait AUSSI
    # valide comme autre chose qu'une image (fichier « polyglotte »).
    try:
        image_verif = Image.open(io.BytesIO(contenu))
        image_verif.verify()  # laisse l'objet inutilisable pour la suite
        image = Image.open(io.BytesIO(contenu))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Fichier illisible comme image — vérifiez qu'il n'est pas corrompu.",
        ) from exc

    DOSSIER_LOGO.mkdir(parents=True, exist_ok=True)
    for ancien in DOSSIER_LOGO.glob("logo.*"):
        ancien.unlink()

    chemin_cible = DOSSIER_LOGO / f"logo.{extension}"
    if extension == "png":
        image.convert("RGBA").save(chemin_cible, format="PNG")
    else:
        image.convert("RGB").save(chemin_cible, format="JPEG", quality=90)

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE parametres SET valeur = %s, utilisateur_id = %s "
                "WHERE cle = 'logo_boutique_extension'",
                (extension, session.utilisateur_id),
            )


@routeur.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_logo(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
) -> None:
    """Retire le logo téléversé — l'application retombe alors sur le seul
    nom de la boutique (jamais une image cassée, jamais un espace vide)."""
    for ancien in DOSSIER_LOGO.glob("logo.*"):
        ancien.unlink()

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE parametres SET valeur = '', utilisateur_id = %s "
                "WHERE cle = 'logo_boutique_extension'",
                (session.utilisateur_id,),
            )


@routeur.get("/logo")
def obtenir_logo():
    """PUBLIQUE (voir docstring du module) : les octets du logo s'ils
    existent, 404 sinon — c'est au NAVIGATEUR de masquer proprement l'image
    absente (``onerror``), pas à cette route d'inventer un visuel de repli."""
    for extension, media_type in (("png", "image/png"), ("jpg", "image/jpeg")):
        chemin = DOSSIER_LOGO / f"logo.{extension}"
        if chemin.is_file():
            return FileResponse(chemin, media_type=media_type)
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun logo téléversé.")
