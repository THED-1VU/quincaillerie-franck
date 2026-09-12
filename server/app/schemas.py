"""Modèles Pydantic des requêtes et réponses de l'API."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class DemandeConnexion(BaseModel):
    identifiant: str = Field(min_length=1, max_length=50)
    mot_de_passe: str = Field(min_length=1, max_length=200)


class ReponseConnexion(BaseModel):
    jeton: str
    expire_dans_secondes: int
    utilisateur_id: int
    nom_complet: str
    role: str
    site_id: Optional[int]
    doit_changer_mot_de_passe: bool


class DemandeChangementMotDePasse(BaseModel):
    mot_de_passe_actuel: str = Field(min_length=1, max_length=200)
    nouveau_mot_de_passe: str = Field(min_length=8, max_length=200)


class ReponseProfil(BaseModel):
    utilisateur_id: int
    nom_complet: str
    role: str
    site_id: Optional[int]
    doit_changer_mot_de_passe: bool


class ReponseDeverrouillage(BaseModel):
    utilisateur_id: int
    tentatives_echouees: int


class LigneVenteDemande(BaseModel):
    """Une ligne telle que saisie par la comptabilité depuis le facturier
    papier : ``prix_unitaire`` est le prix négocié TTC (addendum, point d),
    qui peut légitimement différer du prix catalogue."""

    article_id: int
    quantite: int = Field(gt=0)
    prix_unitaire: float = Field(ge=0)


class DemandeVente(BaseModel):
    """``site_id`` n'est utilisé QUE pour un compte responsable (deux
    sites) : pour un agent comptabilité, le site vient toujours de sa
    session, jamais du corps de la requête."""

    site_id: Optional[int] = None
    mode_paiement: str = Field(min_length=1, max_length=30)
    lignes: List[LigneVenteDemande] = Field(min_length=1)


class LigneEcartReponse(BaseModel):
    """Un écart signalé au comptable au moment même de la saisie — jamais un
    refus (addendum, point e) : la quantité demandée dépassait le stock
    disponible, la différence a été consignée pour le responsable."""

    article_id: int
    quantite_manquante: int


class ReponseVente(BaseModel):
    vente_id: int
    site_id: int
    sous_total_ht: float
    taux_tva: float
    montant_tva: float
    total_ttc: float
    ecarts: List[LigneEcartReponse]


class DemandeComptage(BaseModel):
    """Un comptage à l'aveugle : SEULE la quantité comptée vient du client.

    ``quantite_attendue`` n'existe même pas comme champ ici — l'envoyer
    n'aurait de toute façon aucun effet (figée par la base, migration 003),
    mais elle est absente du modèle pour qu'aucun code ne puisse même
    l'écrire par erreur."""

    article_id: int
    moment: Literal["matin", "soir"]
    quantite_comptee: int = Field(ge=0)


class ReponseComptage(BaseModel):
    """Ne renvoie JAMAIS quantite_attendue ni ecart — voir
    server/app/routes/inventaire.py."""

    comptage_id: int
    article_id: int
    moment: str
    quantite_comptee: int
