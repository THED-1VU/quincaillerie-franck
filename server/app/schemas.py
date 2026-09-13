"""Modèles Pydantic des requêtes et réponses de l'API."""

from __future__ import annotations

from datetime import date as _date
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


class DemandeArticle(BaseModel):
    """``site_id`` n'est utilisé QUE pour un compte responsable (deux
    sites) : pour un agent stock, le site vient toujours de sa session.
    ``prix_achat``/``prix_vente`` sont ignorés s'ils sont envoyés par un
    agent stock (la base le refuserait de toute façon — GRANT par colonne,
    migration 008) — la route ne les inclut simplement pas dans l'INSERT
    pour ce rôle, plutôt que de laisser PostgreSQL renvoyer une erreur brute."""

    nom: str = Field(min_length=1, max_length=150)
    unite: str = Field(min_length=1, max_length=30)
    categorie: Optional[str] = Field(default=None, max_length=80)
    fournisseur_id: Optional[int] = None
    site_id: Optional[int] = None
    prix_achat: Optional[float] = Field(default=None, ge=0)
    prix_vente: Optional[float] = Field(default=None, ge=0)


class ReponseArticle(BaseModel):
    article_id: int
    nom: str
    unite: str
    site_id: int


class DemandeModificationArticle(BaseModel):
    """Modification d'un article existant (cycle 11). Tous les champs sont
    optionnels : seuls ceux fournis sont modifiés. ``prix_achat``,
    ``prix_vente`` et ``fournisseur_id`` sont ignorés pour un agent stock —
    même principe que ``DemandeArticle`` pour la création. ``quantite_stock``
    et ``seuil_alerte`` n'existent délibérément PAS ici : toute quantité
    passe par une fonction de mouvement (cycle 9), jamais par une
    modification de fiche."""

    nom: Optional[str] = Field(default=None, min_length=1, max_length=150)
    unite: Optional[str] = Field(default=None, min_length=1, max_length=30)
    categorie: Optional[str] = Field(default=None, max_length=80)
    fournisseur_id: Optional[int] = None
    prix_achat: Optional[float] = Field(default=None, ge=0)
    prix_vente: Optional[float] = Field(default=None, ge=0)


class ReponseModificationArticle(BaseModel):
    """``prix_achat``/``prix_vente`` restent ``None`` dans la réponse à un
    agent stock — jamais relus depuis la base pour ce rôle, pas seulement
    masqués après coup."""

    article_id: int
    nom: str
    categorie: Optional[str] = None
    unite: str
    site_id: int
    prix_achat: Optional[float] = None
    prix_vente: Optional[float] = None


class ReponseArticleAutreSite(BaseModel):
    """Un article de l'AUTRE site, pour choisir la destination d'un
    transfert (cycle 11) — jamais de prix ni de quantité."""

    id: int
    nom: str
    unite: str
    site_id: int


class DemandeEntreeStock(BaseModel):
    article_id: int
    quantite: int = Field(gt=0)
    motif: Optional[str] = Field(default=None, max_length=200)


class ReponseMouvementStock(BaseModel):
    """Réponse générique à un mouvement de stock : le nouveau stock, jamais
    plus (pas de fuite d'autres colonnes d'articles)."""

    article_id: int
    quantite_stock: int


class DemandeTransfert(BaseModel):
    article_id_origine: int
    article_id_destination: int
    quantite: int = Field(gt=0)
    motif: str = Field(min_length=1, max_length=200)


class ReponseTransfert(BaseModel):
    article_id_origine: int
    article_id_destination: int
    quantite_stock_origine: int
    quantite_stock_destination: int


class DemandeCasse(BaseModel):
    article_id: int
    quantite: int = Field(gt=0)
    motif: str = Field(min_length=1, max_length=200)


class DemandeRetourClient(BaseModel):
    article_id: int
    vente_id: int
    quantite: int = Field(gt=0)
    motif: Optional[str] = Field(default=None, max_length=200)


class DemandeRetourFournisseur(BaseModel):
    mouvement_origine_id: int
    quantite: int = Field(gt=0)
    motif: Optional[str] = Field(default=None, max_length=200)


# ---------------------------------------------------------------------------
# Chantier C6 (comptabilité et RH, cycle 16) — hors clôture de caisse
# (addendum, point g, non tranché).
# ---------------------------------------------------------------------------

class DemandeTransaction(BaseModel):
    """Recette ou dépense HORS vente — une vente crée déjà sa propre
    recette automatiquement (``routes/ventes.py``). ``site_id`` suit le
    même principe que pour une vente ou un article : obligatoire pour un
    responsable (deux sites), ignoré pour un agent (son site vient
    toujours de sa session)."""

    type: Literal["recette", "depense"]
    montant: float = Field(gt=0)
    description: Optional[str] = Field(default=None, max_length=200)
    employe_id: Optional[int] = None
    site_id: Optional[int] = None


class ReponseTransaction(BaseModel):
    transaction_id: int
    site_id: int
    type: str
    montant: float
    description: Optional[str] = None
    employe_id: Optional[int] = None


class DemandeEmploye(BaseModel):
    nom_complet: str = Field(min_length=1, max_length=150)
    poste: Optional[str] = Field(default=None, max_length=100)
    telephone: Optional[str] = Field(default=None, max_length=30)
    type_contrat: Literal["permanent", "temporaire"] = "permanent"
    salaire_mensuel: float = Field(ge=0)
    site_id: Optional[int] = None
    date_embauche: Optional[_date] = None


class ReponseEmploye(BaseModel):
    employe_id: int
    nom_complet: str
    poste: Optional[str] = None
    telephone: Optional[str] = None
    type_contrat: str
    salaire_mensuel: float
    site_id: Optional[int] = None
    actif: bool


class DemandeAbsenceConge(BaseModel):
    employe_id: int
    type: Literal["absence", "conge"]
    date_debut: _date
    date_fin: _date
    motif: Optional[str] = Field(default=None, max_length=200)


class ReponseAbsenceConge(BaseModel):
    id: int
    employe_id: int
    type: str
    date_debut: _date
    date_fin: _date
    motif: Optional[str] = None


class DemandeAvanceSalaire(BaseModel):
    employe_id: int
    montant: float = Field(gt=0)
    motif: Optional[str] = Field(default=None, max_length=200)


class ReponseAvanceSalaire(BaseModel):
    id: int
    employe_id: int
    montant: float
    motif: Optional[str] = None
    remboursee: bool
