#!/usr/bin/env python3
"""Chargement des créances existantes depuis un fichier Excel (point b).

Décision du propriétaire (2026-09-25, addendum point b) : la reprise du
cahier de crédit (15 à 25 clients débiteurs) suit le même principe que le
chargement du stock initial (point j) — un chargement progressif, jamais un
import unique qui dupliquerait ce qui a déjà été chargé, une simulation
obligatoire avant tout chargement réel.

Colonnes attendues dans la feuille active du fichier Excel (première ligne =
en-têtes, insensible à la casse) :
    nom, telephone, plafond_credit, montant, site, motif

- ``telephone`` identifie un client existant s'il correspond exactement à
  une fiche déjà présente (le nom seul est trop ambigu — deux clients
  peuvent porter le même prénom usuel). À défaut de téléphone dans la
  ligne, on retombe sur une correspondance stricte par ``nom``.
- ``plafond_credit`` est optionnel — 100 000 FCFA par défaut (même
  convention que ``POST /clients``) si la ligne ne le précise pas.
- ``site`` doit correspondre exactement (insensible à la casse) au ``nom``
  d'une ligne de la table ``sites`` — c'est le site auquel la créance
  reprise est attribuée pour le reporting, jamais un filtre (un client est
  toujours partagé entre les deux sites, migration 045).
- ``motif`` est un texte libre optionnel (ex. « reprise cahier avril
  2026 ») ; un motif par défaut est utilisé si absent.

Idempotence : avant de charger une ligne, le script vérifie si une créance
portant EXACTEMENT le même motif (nom du fichier + numéro de ligne, voir
_motif_ligne) existe déjà pour ce client — si oui, la ligne est signalée
« déjà chargée » et ignorée. Rejouer deux fois le même fichier ne charge
donc jamais deux fois la même créance.

SÉCURITÉ (aucune annulation possible après coup — l'historique n'est jamais
effacé) : par défaut ce script est en SIMULATION SEULE (ROLLBACK
systématique). Il faut l'option --executer, explicite, pour committer
réellement.

Usage :
    python db/outils/importer_creances_initiales.py --fichier creances.xlsx \
        --utilisateur-id 1
        [--executer] [--config server/config.ini]
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

COLONNES_ATTENDUES = ["nom", "telephone", "plafond_credit", "montant", "site", "motif"]

MOTIF_PAR_DEFAUT = "Reprise du cahier papier"


@dataclass
class LigneImport:
    numero: int
    nom: str
    telephone: str
    plafond_credit: float
    montant: float
    site: str
    motif: str


@dataclass
class Rapport:
    clients_crees: list = field(default_factory=list)
    clients_reutilises: list = field(default_factory=list)
    charges: list = field(default_factory=list)
    deja_charges: list = field(default_factory=list)
    avertissements: list = field(default_factory=list)
    erreurs: list = field(default_factory=list)

    def fusionner(self, autre: "Rapport") -> None:
        self.clients_crees += autre.clients_crees
        self.clients_reutilises += autre.clients_reutilises
        self.charges += autre.charges
        self.deja_charges += autre.deja_charges
        self.avertissements += autre.avertissements

    def imprimer(self, simulation: bool) -> None:
        titre = "SIMULATION (aucune écriture)" if simulation else "CHARGEMENT RÉEL"
        print(f"\n===== {titre} : reprise des créances =====")
        for etiquette, liste in (
            ("Clients créés", self.clients_crees),
            ("Clients existants réutilisés", self.clients_reutilises),
            ("Créances chargées", self.charges),
            ("Déjà chargées (ignorées, idempotence)", self.deja_charges),
        ):
            print(f"\n-- {etiquette} : {len(liste)}")
            for texte in liste:
                print(f"   {texte}")
        if self.avertissements:
            print(f"\n-- Avertissements ({len(self.avertissements)}, non bloquants) :")
            for texte in self.avertissements:
                print(f"   {texte}")
        if self.erreurs:
            print(f"\n-- ERREURS ({len(self.erreurs)}, lignes ignorées) :")
            for texte in self.erreurs:
                print(f"   {texte}")
        total_charge = sum(1 for _ in self.charges)
        print(
            f"\nBilan : {total_charge} créance(s) chargée(s), "
            f"{len(self.deja_charges)} déjà présente(s), "
            f"{len(self.erreurs)} en erreur."
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
                telephone=str(valeur(rangee, "telephone") or "").strip(),
                plafond_credit=float(valeur(rangee, "plafond_credit") or 100000),
                montant=float(valeur(rangee, "montant") or 0),
                site=str(valeur(rangee, "site") or "").strip(),
                motif=str(valeur(rangee, "motif") or "").strip() or MOTIF_PAR_DEFAUT,
            ))
        except (TypeError, ValueError) as exc:
            resultat.append(LigneImport(
                numero=n, nom=f"__ERREUR_LECTURE__:{exc}", telephone="", plafond_credit=0,
                montant=0, site="", motif="",
            ))
    return resultat


def _motif_ligne(nom_fichier: str, ligne: LigneImport) -> str:
    """Identifiant d'idempotence — mêmes fichier + numéro de ligne -> même
    motif -> une ré-exécution ne recharge jamais deux fois la même ligne."""
    base = f"Import créances initiales - {nom_fichier} L{ligne.numero} - {ligne.motif}"
    return base[:200]


def _deja_charge(cur, client_id: int, motif: str) -> bool:
    cur.execute(
        "SELECT 1 FROM creances WHERE client_id = %s AND vente_id IS NULL AND motif = %s",
        (client_id, motif),
    )
    return cur.fetchone() is not None


def _trouver_site(cur, nom_site: str) -> Optional[int]:
    cur.execute("SELECT id FROM sites WHERE lower(btrim(nom)) = lower(btrim(%s))", (nom_site,))
    ligne = cur.fetchone()
    return ligne[0] if ligne else None


def _trouver_client(cur, ligne: LigneImport) -> Optional[int]:
    if ligne.telephone:
        cur.execute("SELECT id FROM clients WHERE btrim(telephone) = btrim(%s)", (ligne.telephone,))
        trouve = cur.fetchone()
        if trouve:
            return trouve[0]
        return None
    cur.execute("SELECT id FROM clients WHERE lower(btrim(nom)) = lower(btrim(%s))", (ligne.nom,))
    trouve = cur.fetchone()
    return trouve[0] if trouve else None


def _traiter_ligne(cur, ligne: LigneImport, nom_fichier: str, utilisateur_id: int, rapport: Rapport) -> None:
    repere = f"L{ligne.numero}"

    site_id = _trouver_site(cur, ligne.site)
    if site_id is None:
        rapport.erreurs.append(f"{repere} ({ligne.nom!r}) : site {ligne.site!r} inconnu.")
        return

    client_id = _trouver_client(cur, ligne)
    if client_id is None:
        cur.execute(
            "INSERT INTO clients (nom, telephone, plafond_credit) VALUES (%s, %s, %s) RETURNING id",
            (ligne.nom, ligne.telephone or None, ligne.plafond_credit),
        )
        client_id = cur.fetchone()[0]
        rapport.clients_crees.append(f"{ligne.nom!r} (id={client_id})")
    else:
        rapport.clients_reutilises.append(f"{repere} : {ligne.nom!r} -> fiche existante id={client_id}")

    motif = _motif_ligne(nom_fichier, ligne)
    if _deja_charge(cur, client_id, motif):
        rapport.deja_charges.append(f"{repere} : {ligne.nom!r} (motif identique déjà enregistré).")
        return

    cur.execute(
        "SELECT enregistrer_creance_initiale("
        "%s::integer, %s::numeric, %s::integer, %s::integer, %s::varchar) AS encours",
        (client_id, ligne.montant, site_id, utilisateur_id, motif),
    )
    encours = cur.fetchone()[0]
    rapport.charges.append(
        f"{repere} : {ligne.nom!r} +{ligne.montant} FCFA (site {ligne.site}) -> encours total {encours}"
    )


def importer(connexion: psycopg.Connection, lignes: list[LigneImport], nom_fichier: str, utilisateur_id: int) -> Rapport:
    rapport = Rapport()
    with connexion.cursor() as cur:
        cur.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier("qf_responsable")))

        for ligne in lignes:
            repere = f"L{ligne.numero}"
            if ligne.nom.startswith("__ERREUR_LECTURE__"):
                rapport.erreurs.append(f"{repere} : ligne illisible ({ligne.nom.split(':', 1)[1]})")
                continue
            if not ligne.nom:
                rapport.erreurs.append(f"{repere} : nom de client vide, ligne ignorée.")
                continue
            if ligne.montant <= 0:
                rapport.erreurs.append(f"{repere} ({ligne.nom!r}) : montant invalide ({ligne.montant}).")
                continue

            rapport_ligne = Rapport()
            try:
                with connexion.transaction():
                    _traiter_ligne(cur, ligne, nom_fichier, utilisateur_id, rapport_ligne)
            except psycopg.Error as exc:
                rapport.erreurs.append(f"{repere} ({ligne.nom!r}) : {str(exc).strip()}")
            else:
                rapport.fusionner(rapport_ligne)
                rapport.erreurs += rapport_ligne.erreurs

    return rapport


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--fichier", required=True, type=Path, help="Fichier Excel (.xlsx) des créances existantes.")
    analyseur.add_argument("--utilisateur-id", required=True, type=int, help="id (table utilisateurs) du responsable qui mène l'import.")
    analyseur.add_argument("--config", type=Path, default=RACINE / "server" / "config.ini", help="config.ini (section [database]).")
    analyseur.add_argument("--executer", action="store_true", help="Committe réellement (par défaut : simulation, ROLLBACK systématique).")
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
        rapport = importer(connexion, lignes, nom_fichier=args.fichier.name, utilisateur_id=args.utilisateur_id)
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
