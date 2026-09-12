"""Modèles Pydantic des requêtes et réponses de l'API."""

from __future__ import annotations

from typing import Optional

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
