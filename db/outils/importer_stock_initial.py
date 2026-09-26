#!/usr/bin/env python3
"""Chargement du stock initial réel depuis un fichier Excel (point j).

Décision du propriétaire (2026-09-19, ADDENDUM_CAHIER_DES_CHARGES.md, point
j ; convention du seuil validée le 2026-09-25) : le chargement initial est un
mouvement ``inventaire_initial`` daté, tracé, jamais confondu avec une
réception fournisseur (migration 041, ``enregistrer_inventaire_initial()``).
Périmètre de ce cycle : le STOCK seul (le crédit client, point b, n'est pas
construit et sera un chantier séparé).

Colonnes attendues dans la feuille active du fichier Excel (première ligne =
en-têtes, insensible à la casse) :
    nom, categorie, zone, unite, site, fournisseur, prix_achat, prix_vente,
    quantite

- ``site`` doit correspondre exactement (insensible à la casse) au ``nom``
  d'une ligne de la table ``sites`` ("Magasin de stock", "Comptoir").
- ``zone`` est un texte libre (ex. "Rayon A", "Réserve") : il n'existe pas de
  colonne dédiée sur ``articles`` — l'addendum n'en demande pas — la zone est
  simplement portée dans le motif du mouvement, pour traçabilité.
- ``fournisseur`` peut être vide (fournisseur_id NULL). S'il est renseigné et
  ne correspond à aucun fournisseur existant, la fiche n'est PAS créée
  automatiquement : il faut relancer avec --confirmer-fournisseurs pour
  autoriser la création (jamais silencieuse).

Modèle "une fiche, N stocks de site" (migrations 026-031, cycle 35) : si le
``nom`` correspond déjà à un article existant (comparaison stricte après
btrim, insensible à la casse), la fiche EXISTANTE est réutilisée et seule une
nouvelle ligne ``stocks_sites`` est ajoutée pour le site de cette ligne — ce
n'est PAS un homonyme à rapprocher (il n'y a plus qu'une seule fiche par nom
dans ce schéma), c'est le fonctionnement normal du multi-site. Le script
signale seulement, sans bloquer, les cas où la fiche existante a une unité ou
des prix différents de ceux de la ligne importée, pour vérification humaine.

Idempotence ("sans jamais dupliquer", addendum point j) : avant de charger
une ligne, le script vérifie si un mouvement ``inventaire_initial`` portant
EXACTEMENT le même motif (nom du fichier + numéro de ligne, voir
_motif_ligne ci-dessous) existe déjà pour cet (article, site) — si oui, la
ligne est signalée « déjà chargée » et ignorée. Rejouer deux fois le même
fichier ne charge donc jamais deux fois la même ligne. Un même article/site
peut néanmoins recevoir plusieurs chargements RÉELLEMENT distincts (deux
zones différentes, ou deux fichiers différents) : c'est voulu (addendum,
chargement partiel/successif), enregistrer_inventaire_initial() additionne.

SÉCURITÉ (pas d'annulation possible après coup — l'historique n'est jamais
effacé, comme partout ailleurs dans ce projet) : par défaut ce script est en
SIMULATION SEULE (aucune écriture, tout est fait puis annulé par ROLLBACK).
Il faut l'option --executer, explicite, pour committer réellement. Toujours
lancer une fois SANS --executer d'abord et relire le rapport.

Usage :
    python db/outils/importer_stock_initial.py --fichier stock.xlsx \
        --utilisateur-id 1
        [--executer] [--confirmer-fournisseurs] [--config server/config.ini]
"""

from __future__ import annotations

import argparse
import configparser
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import openpyxl
import psycopg
from psycopg import sql

RACINE = Path(__file__).resolve().parents[2]

COLONNES_ATTENDUES = [
    "nom", "categorie", "zone", "unite", "site", "fournisseur",
    "prix_achat", "prix_vente", "quantite",
]


@dataclass
class LigneImport:
    numero: int
    nom: str
    categorie: str
    zone: str
    unite: str
    site: str
    fournisseur: str
    prix_achat: float
    prix_vente: float
    quantite: float


@dataclass
class Rapport:
    articles_crees: list = field(default_factory=list)
    fiches_reutilisees: list = field(default_factory=list)
    charges: list = field(default_factory=list)
    deja_charges: list = field(default_factory=list)
    fournisseurs_crees: list = field(default_factory=list)
    fournisseurs_en_attente: list = field(default_factory=list)
    avertissements: list = field(default_factory=list)
    erreurs: list = field(default_factory=list)
    a_trancher: list = field(default_factory=list)

    def fusionner(self, autre: "Rapport") -> None:
        self.articles_crees += autre.articles_crees
        self.fiches_reutilisees += autre.fiches_reutilisees
        self.charges += autre.charges
        self.deja_charges += autre.deja_charges
        self.fournisseurs_crees += autre.fournisseurs_crees
        self.fournisseurs_en_attente += autre.fournisseurs_en_attente
        self.avertissements += autre.avertissements
        self.a_trancher += autre.a_trancher

    def imprimer(self, simulation: bool) -> None:
        titre = "SIMULATION (aucune écriture)" if simulation else "CHARGEMENT RÉEL"
        print(f"\n===== {titre} : résultat par zone/catégorie =====")
        for etiquette, liste in (
            ("Articles créés", self.articles_crees),
            ("Fiches existantes réutilisées (nouveau site)", self.fiches_reutilisees),
            ("Lignes chargées", self.charges),
            ("Déjà chargées (ignorées, idempotence)", self.deja_charges),
            ("Fournisseurs créés", self.fournisseurs_crees),
        ):
            print(f"\n-- {etiquette} : {len(liste)}")
            for texte in liste:
                print(f"   {texte}")
        if self.fournisseurs_en_attente:
            distincts = sorted(set(self.fournisseurs_en_attente))
            print(f"\n-- Fournisseurs manquants, en attente de confirmation ({len(distincts)}) :")
            for texte in distincts:
                print(f"   {texte}")
            print("   Relancer avec --confirmer-fournisseurs pour les créer.")
        if self.avertissements:
            print(f"\n-- Avertissements ({len(self.avertissements)}, non bloquants) :")
            for texte in self.avertissements:
                print(f"   {texte}")
        if self.a_trancher:
            distinctes = sorted(set(self.a_trancher))
            print(f"\n-- À TRANCHER par le responsable ({len(distinctes)}) :")
            for texte in distinctes:
                print(f"   {texte}")
            print("   Plusieurs fiches existantes portent un nom équivalent après")
            print("   normalisation (accents/casse/espaces/tirets) : l'outil ne")
            print("   choisit jamais d'office. Rapprocher manuellement (outil")
            print("   db/outils/rapprocher_articles.ps1), puis relancer l'import.")
        if self.erreurs:
            print(f"\n-- ERREURS ({len(self.erreurs)}, lignes ignorées) :")
            for texte in self.erreurs:
                print(f"   {texte}")
        print(
            f"\nBilan : {len(self.charges)} ligne(s) chargée(s), "
            f"{len(self.deja_charges)} déjà présente(s), "
            f"{len(self.erreurs)} en erreur, "
            f"{len(set(self.fournisseurs_en_attente))} fournisseur(s) en attente, "
            f"{len(set(self.a_trancher))} ambiguïté(s) de nom à trancher."
        )


def lire_config(chemin: Path) -> dict:
    cp = configparser.ConfigParser()
    lus = cp.read(chemin, encoding="utf-8")
    if not lus:
        raise SystemExit(f"config introuvable : {chemin}")
    s = cp["database"]
    return dict(
        host=s.get("host", "127.0.0.1"),
        port=s.getint("port", fallback=5432),
        dbname=s["dbname"],
        user=s.get("user", "qf_app"),
        password=s["password"],
    )


def lire_excel(chemin: Path) -> list[LigneImport]:
    classeur = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
    feuille = classeur.active
    lignes_brutes = feuille.iter_rows(min_row=1)
    try:
        entete = next(lignes_brutes)
    except StopIteration:
        raise SystemExit("fichier vide : aucune ligne d'en-tête.")
    entetes = [str(c.value).strip().lower() if c.value is not None else "" for c in entete]
    manquantes = [c for c in COLONNES_ATTENDUES if c not in entetes]
    if manquantes:
        raise SystemExit(f"colonnes manquantes dans le fichier : {', '.join(manquantes)}")
    index = {nom: entetes.index(nom) for nom in COLONNES_ATTENDUES}

    def valeur(rangee, colonne):
        return rangee[index[colonne]].value

    resultat: list[LigneImport] = []
    for n, rangee in enumerate(lignes_brutes, start=2):
        if all(cellule.value is None for cellule in rangee):
            continue
        try:
            resultat.append(LigneImport(
                numero=n,
                nom=str(valeur(rangee, "nom") or "").strip(),
                categorie=str(valeur(rangee, "categorie") or "").strip(),
                zone=str(valeur(rangee, "zone") or "").strip(),
                unite=str(valeur(rangee, "unite") or "").strip(),
                site=str(valeur(rangee, "site") or "").strip(),
                fournisseur=str(valeur(rangee, "fournisseur") or "").strip(),
                prix_achat=float(valeur(rangee, "prix_achat") or 0),
                prix_vente=float(valeur(rangee, "prix_vente") or 0),
                quantite=float(valeur(rangee, "quantite") or 0),
            ))
        except (TypeError, ValueError) as exc:
            resultat.append(LigneImport(
                numero=n, nom="", categorie="", zone="", unite="", site="",
                fournisseur="", prix_achat=0, prix_vente=0, quantite=0,
            ))
            resultat[-1].nom = f"__ERREUR_LECTURE__:{exc}"
    return resultat


def _motif_ligne(nom_fichier: str, ligne: LigneImport) -> str:
    """Identifiant d'idempotence : mêmes fichier + numéro de ligne ->
    toujours le même motif -> une ré-exécution ne recharge jamais deux fois
    la même ligne. La zone reste lisible dans le motif pour l'humain."""
    base = f"Import stock initial - {nom_fichier} L{ligne.numero}"
    if ligne.zone:
        base += f" - zone {ligne.zone}"
    return base[:255]


def _deja_charge(cur, article_id: int, site_id: int, motif: str) -> bool:
    cur.execute(
        "SELECT 1 FROM mouvements_stock "
        "WHERE article_id = %s AND site_id = %s AND categorie = 'inventaire_initial' AND motif = %s",
        (article_id, site_id, motif),
    )
    return cur.fetchone() is not None


def _trouver_site(cur, nom_site: str) -> Optional[int]:
    cur.execute("SELECT id FROM sites WHERE lower(btrim(nom)) = lower(btrim(%s))", (nom_site,))
    ligne = cur.fetchone()
    return ligne[0] if ligne else None


def _trouver_article(cur, nom_article: str) -> dict:
    """Rapprochement par nom NORMALISÉ (migration 046) : insensible à la
    casse, aux accents, aux espaces multiples et aux tirets.

    Retourne :
      * {"trouvee": False} si aucune fiche ne correspond ;
      * {"trouvee": True, ...} si UNE seule fiche correspond ;
      * {"trouvee": False, "ambigu": [noms...]} si PLUSIEURS fiches
        portent un nom équivalent après normalisation — l'appelant doit
        présenter la paire douteuse au responsable, jamais choisir d'office.
    """
    cur.execute(
        "SELECT id, nom, unite, prix_achat, prix_vente FROM articles "
        "WHERE normaliser_nom_article(nom) = normaliser_nom_article(%s) "
        "ORDER BY id",
        (nom_article,),
    )
    lignes = cur.fetchall()
    if not lignes:
        return {"trouvee": False}
    if len(lignes) == 1:
        return dict(
            trouvee=True, id=lignes[0][0], nom=lignes[0][1],
            unite=lignes[0][2], prix_achat=lignes[0][3], prix_vente=lignes[0][4],
        )
    return {
        "trouvee": False,
        "ambigu": [f"{l[0]} ({l[1]})" for l in lignes],
    }


def _trouver_ou_marquer_fournisseur(cur, nom_fournisseur: str, autoriser_creation: bool, rapport: Rapport) -> Optional[int]:
    if not nom_fournisseur:
        return None
    cur.execute("SELECT id FROM fournisseurs WHERE lower(btrim(nom)) = lower(btrim(%s))", (nom_fournisseur,))
    ligne = cur.fetchone()
    if ligne:
        return ligne[0]
    if not autoriser_creation:
        rapport.fournisseurs_en_attente.append(nom_fournisseur)
        return None
    cur.execute("INSERT INTO fournisseurs (nom) VALUES (%s) RETURNING id", (nom_fournisseur,))
    nouvel_id = cur.fetchone()[0]
    rapport.fournisseurs_crees.append(nom_fournisseur)
    return nouvel_id


def _traiter_ligne(
    cur,
    connexion: psycopg.Connection,
    ligne: LigneImport,
    nom_fichier: str,
    utilisateur_id: int,
    autoriser_creation_fournisseurs: bool,
    rapport: Rapport,
) -> None:
    """Toutes les écritures d'UNE ligne, dans une seule savepoint : une
    erreur (contrainte violée, article introuvable...) annule uniquement
    cette ligne, jamais les lignes déjà traitées avant elle."""
    repere = f"L{ligne.numero}"

    site_id = _trouver_site(cur, ligne.site)
    if site_id is None:
        rapport.erreurs.append(f"{repere} ({ligne.nom!r}) : site {ligne.site!r} inconnu.")
        return

    fournisseur_id = _trouver_ou_marquer_fournisseur(
        cur, ligne.fournisseur, autoriser_creation_fournisseurs, rapport
    )
    if ligne.fournisseur and fournisseur_id is None and not autoriser_creation_fournisseurs:
        rapport.erreurs.append(
            f"{repere} ({ligne.nom!r}) : fournisseur {ligne.fournisseur!r} inconnu, "
            "ligne ignorée (voir --confirmer-fournisseurs)."
        )
        return

    existante = _trouver_article(cur, ligne.nom)
    if not existante.get("trouvee") and existante.get("ambigu"):
        rapport.a_trancher.append(
            f"{repere} : {ligne.nom!r} — plusieurs fiches existantes "
            f"({', '.join(existante['ambigu'])}) — ligne ignorée, à trancher."
        )
        return

    quantite_decimale = ligne.quantite != int(ligne.quantite)

    if not existante.get("trouvee"):
        cur.execute(
            "INSERT INTO articles (nom, categorie, unite, prix_achat, prix_vente, "
            "fournisseur_id, quantite_decimale_autorisee) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (ligne.nom, ligne.categorie or None, ligne.unite, ligne.prix_achat,
             ligne.prix_vente, fournisseur_id, quantite_decimale),
        )
        article_id = cur.fetchone()[0]
        rapport.articles_crees.append(f"{ligne.nom!r} (id={article_id})")
    else:
        article_id = existante["id"]
        rapport.fiches_reutilisees.append(
            f"{repere} : {ligne.nom!r} -> fiche existante id={article_id} (site {ligne.site})"
        )
        if existante["unite"] != ligne.unite:
            rapport.avertissements.append(
                f"{repere} ({ligne.nom!r}) : unité du fichier ({ligne.unite!r}) différente "
                f"de la fiche existante ({existante['unite']!r}) — vérifier qu'il s'agit bien "
                "du même article avant de valider."
            )
        if quantite_decimale:
            cur.execute("SELECT quantite_decimale_autorisee FROM articles WHERE id = %s", (article_id,))
            if not cur.fetchone()[0]:
                rapport.avertissements.append(
                    f"{repere} ({ligne.nom!r}) : quantité décimale ({ligne.quantite}) mais la "
                    "fiche existante n'autorise pas les quantités décimales — le chargement "
                    "sera refusé par la base."
                )

    motif = _motif_ligne(nom_fichier, ligne)
    if _deja_charge(cur, article_id, site_id, motif):
        rapport.deja_charges.append(f"{repere} : {ligne.nom!r} au site {ligne.site} (motif identique déjà enregistré).")
        return

    cur.execute(
        "SELECT enregistrer_inventaire_initial(%s::integer, %s::integer, %s::numeric, %s::integer, %s::varchar)",
        (article_id, site_id, ligne.quantite, utilisateur_id, motif),
    )
    nouveau_total = cur.fetchone()[0]
    rapport.charges.append(
        f"{repere} : {ligne.nom!r} +{ligne.quantite} {ligne.unite} au site {ligne.site} "
        f"(zone {ligne.zone or '—'}) -> stock total {nouveau_total}"
    )


def importer(
    connexion: psycopg.Connection,
    lignes: list[LigneImport],
    nom_fichier: str,
    utilisateur_id: int,
    autoriser_creation_fournisseurs: bool,
) -> Rapport:
    rapport = Rapport()
    with connexion.cursor() as cur:
        cur.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier("qf_responsable")))

        for ligne in lignes:
            repere = f"L{ligne.numero}"
            if ligne.nom.startswith("__ERREUR_LECTURE__"):
                rapport.erreurs.append(f"{repere} : ligne illisible ({ligne.nom.split(':', 1)[1]})")
                continue
            if not ligne.nom:
                rapport.erreurs.append(f"{repere} : nom d'article vide, ligne ignorée.")
                continue
            if ligne.quantite <= 0:
                rapport.erreurs.append(f"{repere} ({ligne.nom!r}) : quantité invalide ({ligne.quantite}).")
                continue
            if not ligne.unite:
                rapport.erreurs.append(f"{repere} ({ligne.nom!r}) : unité manquante.")
                continue

            rapport_ligne = Rapport()
            try:
                with connexion.transaction():
                    _traiter_ligne(
                        cur, connexion, ligne, nom_fichier, utilisateur_id,
                        autoriser_creation_fournisseurs, rapport_ligne,
                    )
            except psycopg.Error as exc:
                # Le savepoint ci-dessus a annulé toutes les écritures de
                # cette ligne (fournisseur/article créés y compris) : on ne
                # garde donc AUCUNE des entrées de rapport_ligne, seulement
                # l'erreur, pour ne jamais annoncer une création qui n'a en
                # réalité pas survécu.
                rapport.erreurs.append(f"{repere} ({ligne.nom!r}) : {str(exc).strip()}")
            else:
                rapport.fusionner(rapport_ligne)
                rapport.erreurs += rapport_ligne.erreurs

    return rapport


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--fichier", required=True, type=Path, help="Fichier Excel (.xlsx) du stock initial.")
    analyseur.add_argument("--utilisateur-id", required=True, type=int, help="id (table utilisateurs) du responsable qui mène l'import.")
    analyseur.add_argument("--config", type=Path, default=RACINE / "server" / "config.ini", help="config.ini (section [database]).")
    analyseur.add_argument("--executer", action="store_true", help="Committe réellement (par défaut : simulation, ROLLBACK systématique).")
    analyseur.add_argument("--confirmer-fournisseurs", action="store_true", help="Autorise la création des fournisseurs absents du référentiel.")
    args = analyseur.parse_args()

    if not args.fichier.exists():
        print(f"fichier introuvable : {args.fichier}", file=sys.stderr)
        return 2

    lignes = lire_excel(args.fichier)
    if not lignes:
        print("aucune ligne à importer (fichier vide au-delà de l'en-tête).", file=sys.stderr)
        return 1

    config = lire_config(args.config)
    with psycopg.connect(**config) as connexion:
        rapport = importer(
            connexion,
            lignes,
            nom_fichier=args.fichier.name,
            utilisateur_id=args.utilisateur_id,
            autoriser_creation_fournisseurs=args.confirmer_fournisseurs,
        )
        if args.executer:
            connexion.commit()
        else:
            connexion.rollback()

    rapport.imprimer(simulation=not args.executer)
    if not args.executer:
        print("\nSIMULATION — rien n'a été écrit. Relancer avec --executer pour committer réellement.")
    return 1 if rapport.erreurs else 0


if __name__ == "__main__":
    raise SystemExit(main())
