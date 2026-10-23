"""Matrice exhaustive route × rôle (chantier C8, cycle 65).

Contrairement aux tests d'habilitation existants (écrits route par route au
fil des cycles), cette matrice parcourt TOUTE la surface API avec les MÊMES
attentes pour chacun des trois rôles — une régression d'habilitation sur une
route ancienne ne peut plus passer inaperçue.

Convention de la matrice :
- rôle AUTORISÉ  -> la réponse n'est JAMAIS 401 ni 403 (le corps vide ou
  l'identifiant inexistant donne 400/404/409/422 selon la route — ce qui est
  prouvé ici, c'est l'habilitation, pas la charge utile) ;
- rôle INTERDIT  -> exactement 403 (``Rôle non autorisé pour cette route.``) ;
- anonyme        -> 401 sur toute route protégée.

Sources des attentes : décorateurs ``exiger_role(...)`` des fichiers de
``server/app/routes/`` (revue ligne à ligne au cycle 65). Les échecs sont
collectés puis affichés d'un coup : la matrice se lit comme un rapport, pas
un premier échec qui masque les suivants.
"""

from __future__ import annotations

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    entete_autorisation,
    se_connecter,
)

R = "responsable"
S = "agent_stock"
C = "agent_comptabilite"
PUBLIC = "PUBLIC"
TOUS = "TOUS"  # tout rôle authentifié (obtenir_session, sans exiger_role)

# (méthode, chemin, rôles attendus) — chemin tel que servi, {id} = identifiant 1.
MATRICE: list[tuple[str, str, object]] = [
    # --- Public (aucun jeton) ---
    ("POST", "/auth/connexion", PUBLIC),
    ("GET", "/sante", PUBLIC),
    ("GET", "/configuration/logo", PUBLIC),
    # --- Tout rôle authentifié ---
    ("POST", "/auth/deconnexion", TOUS),
    ("POST", "/auth/changer-mot-de-passe", TOUS),
    ("GET", "/articles", TOUS),
    ("GET", "/moi", TOUS),
    # --- Responsable seul ---
    ("GET", "/admin/comptes", {R}),
    ("POST", "/admin/comptes", {R}),
    ("PATCH", "/admin/comptes/{id}/actif", {R}),
    ("PATCH", "/admin/comptes/{id}/mot-de-passe", {R}),
    ("POST", "/admin/comptes/{id}/deverrouiller", {R}),
    ("POST", "/ventes/{id}/annuler", {R}),
    ("GET", "/inventaire/ecarts", {R}),
    ("GET", "/inventaire/historique-comptages", {R}),
    ("GET", "/inventaire/ecarts-ventes", {R}),
    ("POST", "/inventaire/ecarts-ventes/{id}/regulariser", {R}),
    ("POST", "/inventaire/ecarts/{id}/regulariser", {R}),
    # Exports responsable seul (cycle 67 /rapports/stock — ajouté à la matrice
    # au cycle 68, omis au cycle 67 ; cycle 68 /rapports/ecarts-comptage,
    # écart C7-03) : portent prix_achat (008) et quantite_attendue/ecart (012).
    ("GET", "/rapports/stock", {R}),
    ("GET", "/rapports/ecarts-comptage", {R}),
    ("POST", "/stock/casse/declarations/{id}/valider", {R}),
    ("POST", "/stock/retours-client/declarations/{id}/valider", {R}),
    ("POST", "/stock/articles-offerts/declarations/{id}/valider", {R}),
    ("GET", "/tableau-bord/alertes-stock", {R}),
    ("GET", "/tableau-bord/articles-offerts-en-attente", {R}),
    ("GET", "/tableau-bord/credit-client", {R}),
    ("GET", "/caisse/attendu", {R}),
    ("POST", "/caisse", {R}),
    ("GET", "/caisse", {R}),
    ("GET", "/exploitation/derniere-sauvegarde", {R}),
    ("GET", "/exploitation/etat-sauvegarde", {R}),
    ("POST", "/configuration/logo", {R}),
    ("DELETE", "/configuration/logo", {R}),
    ("POST", "/rh/employes", {R}),
    ("GET", "/rh/absences-conges", {R}),
    ("POST", "/rh/absences-conges", {R}),
    ("GET", "/rh/avances-salaire", {R}),
    ("POST", "/rh/avances-salaire", {R}),
    ("POST", "/rh/avances-salaire/{id}/rembourser", {R}),
    ("POST", "/clients", {R}),
    ("PUT", "/clients/{id}", {R}),
    ("PATCH", "/clients/{id}/actif", {R}),
    # --- Responsable + agent comptabilité (caissier fusionné, addendum h) ---
    ("GET", "/ventes/synthese-jour", {R, C}),
    ("GET", "/ventes/parametres", {R, C}),
    ("GET", "/ventes/vendeurs", {R, C}),
    ("POST", "/ventes", {R, C}),
    ("GET", "/ventes/{id}/recu", {R, C}),
    ("GET", "/rapports/ventes", {R, C}),
    ("GET", "/rapports/ecarts-prix-vendeurs", {R, C}),
    ("POST", "/stock/articles-offerts/declarations", {R, C}),
    ("GET", "/stock/articles-offerts/declarations", {R, C}),
    ("POST", "/transactions", {R, C}),
    ("GET", "/transactions", {R, C}),
    ("GET", "/clients", {R, C}),
    ("POST", "/clients/{id}/reglements", {R, C}),
    ("GET", "/rh/employes", {R, C}),
    # --- Responsable + agent stock ---
    ("POST", "/articles", {R, S}),
    ("PUT", "/articles/{id}", {R, S}),
    ("GET", "/inventaire/articles-a-compter", {R, S}),
    ("POST", "/inventaire/comptages", {R, S}),
    ("POST", "/stock/entrees", {R, S}),
    ("POST", "/stock/transferts", {R, S}),
    ("POST", "/stock/casse/declarations", {R, S}),
    ("GET", "/stock/casse/declarations", {R, S}),
    ("POST", "/stock/retours-client/declarations", {R, S}),
    ("GET", "/stock/retours-client/declarations", {R, S}),
    ("POST", "/stock/retours-fournisseur", {R, S}),
    # --- Les trois rôles ---
    ("GET", "/rapports/articles", {R, S, C}),
]

# Réponses admises pour un rôle autorisé : l'habilitation est prouvée par
# l'absence de 401/403 ; la charge utile volontairement vide ou l'identifiant
# 1 parfois inexistant donne une validation ou un « introuvable » normaux.
_CODES_AUTORISE = {200, 201, 204, 400, 404, 409, 422}

_COMPTE_PAR_ROLE = {
    R: ("resp", MOT_DE_PASSE_RESPONSABLE),
    S: ("magasin.stock", MOT_DE_PASSE_AGENT_STOCK),
    C: ("magasin.compta", MOT_DE_PASSE_AGENT_COMPTA),
}


def _executer(client, methode: str, chemin: str, entetes: dict | None):
    fonction = getattr(client, methode.lower())
    if methode in ("POST", "PUT", "PATCH"):
        return fonction(chemin, headers=entetes or {}, json={})
    return fonction(chemin, headers=entetes or {})


def test_matrice_complete_route_par_role(client):
    jetons = {
        role: se_connecter(client, identifiant, mot_de_passe)["jeton"]
        for role, (identifiant, mot_de_passe) in _COMPTE_PAR_ROLE.items()
    }
    echecs: list[str] = []

    for methode, chemin_brut, attendu in MATRICE:
        chemin = chemin_brut.replace("{id}", "1")

        if attendu == PUBLIC:
            reponse = _executer(client, methode, chemin, None)
            if reponse.status_code in (401, 403):
                echecs.append(f"{methode} {chemin} PUBLIC -> {reponse.status_code} (attendu : accessible)")
            continue

        # Anonyme : 401 sauf pour les routes publiques (traitées au-dessus).
        reponse = _executer(client, methode, chemin, None)
        if reponse.status_code != 401:
            echecs.append(f"{methode} {chemin} anonyme -> {reponse.status_code} (attendu : 401)")

        roles_attendus = set(attendu) if attendu != TOUS else {R, S, C}
        for role in (R, S, C):
            entetes = entete_autorisation(jetons[role])
            reponse = _executer(client, methode, chemin, entetes)
            if role in roles_attendus:
                if reponse.status_code in (401, 403):
                    echecs.append(
                        f"{methode} {chemin} {role} -> {reponse.status_code} "
                        f"(attendu : autorisé, {_CODES_AUTORISE})"
                    )
                elif reponse.status_code not in _CODES_AUTORISE:
                    echecs.append(
                        f"{methode} {chemin} {role} -> {reponse.status_code} inattendu "
                        f"(hors {_CODES_AUTORISE})"
                    )
            elif reponse.status_code != 403:
                echecs.append(
                    f"{methode} {chemin} {role} -> {reponse.status_code} (attendu : 403)"
                )
            # /auth/deconnexion révoque VRAIMENT le jeton (cycle 21) : on se
            # reconnecte pour ne pas invalider la suite de la matrice.
            if chemin == "/auth/deconnexion" and reponse.status_code == 204:
                identifiant, mot_de_passe = _COMPTE_PAR_ROLE[role]
                jetons[role] = se_connecter(client, identifiant, mot_de_passe)["jeton"]

    assert not echecs, "Divergences matrice route × rôle :\n" + "\n".join(
        f"  - {e}" for e in echecs
    )
