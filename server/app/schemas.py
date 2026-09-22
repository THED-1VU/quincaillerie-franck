"""Modèles Pydantic des requêtes et réponses de l'API."""

from __future__ import annotations

from datetime import date as _date, datetime
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
    session, jamais du corps de la requête.

    ``numero_facturier`` et ``vendeur_id`` sont obligatoires depuis le
    cycle 27 (addendum, point c, décidé le 2026-09-13) : référence du
    carnet papier tenu par le responsable, et personne ayant négocié le
    prix — voir ``db/migrations/020_facturier_vendeur.sql``."""

    site_id: Optional[int] = None
    mode_paiement: str = Field(min_length=1, max_length=30)
    numero_facturier: str = Field(min_length=1, max_length=30)
    vendeur_id: int
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
    numero_facturier: str
    sous_total_ht: float
    taux_tva: float
    montant_tva: float
    total_ttc: float
    ecarts: List[LigneEcartReponse]


class DemandeAnnulationVente(BaseModel):
    """Motif obligatoire — annuler_vente() (cycle 17) le refuse de toute
    façon, mais Pydantic bloque déjà une chaîne vide en amont."""

    motif: str = Field(min_length=1, max_length=200)


class ReponseAnnulationVente(BaseModel):
    vente_id: int
    montant_ttc: float
    articles_restitues: int


class ReponseRegularisationEcart(BaseModel):
    """Réponse à la régularisation d'un écart de vente à découvert
    (chantier C5, cycle 17) — ``regulariser_ecart_vente()`` ne renvoie rien
    (VOID) : la route relit l'écart après coup pour confirmer son nouvel
    état, plutôt que de renvoyer un simple 204 muet."""

    ecart_id: int
    regularise: bool


class DemandeComptage(BaseModel):
    """Un comptage à l'aveugle : SEULE la quantité comptée vient du client.

    ``quantite_attendue`` n'existe même pas comme champ ici — l'envoyer
    n'aurait de toute façon aucun effet (figée par la base, migration 003),
    mais elle est absente du modèle pour qu'aucun code ne puisse même
    l'écrire par erreur."""

    article_id: int
    site_id: Optional[int] = None
    moment: Literal["matin", "soir"]
    quantite_comptee: int = Field(ge=0)


class ReponseComptage(BaseModel):
    """Ne renvoie JAMAIS quantite_attendue ni ecart — voir
    server/app/routes/inventaire.py."""

    comptage_id: int
    article_id: int
    moment: str
    quantite_comptee: int


class DemandeRegularisationComptage(BaseModel):
    """Décision du responsable sur un écart de comptage constaté
    (cycle 36) : traçabilité pure, jamais d'effet sur le stock."""

    type_resolution: Literal[
        "erreur_de_comptage", "retrouve", "vol_presume", "casse_deja_enregistree"
    ]
    motif: Optional[str] = Field(default=None, max_length=200)


class ReponseRegularisationComptage(BaseModel):
    regularisation_id: int
    comptage_id: int
    type_resolution: str
    motif: Optional[str] = None
    date_regularisation: str


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
    prix_achat: Optional[float] = Field(default=None, ge=0)
    prix_vente: Optional[float] = Field(default=None, ge=0)


class ReponseArticle(BaseModel):
    article_id: int
    nom: str
    unite: str


class DemandeModificationArticle(BaseModel):
    """Modification d'un article existant (cycle 11). Tous les champs sont
    optionnels : seuls ceux fournis sont modifiés. ``prix_achat``,
    ``prix_vente`` et ``fournisseur_id`` sont ignorés pour un agent stock —
    même principe que ``DemandeArticle`` pour la création. La quantité et le
    seuil d'alerte n'existent délibérément PAS ici (ni sur la fiche, depuis
    le cycle 35) : toute quantité passe par une fonction de mouvement,
    jamais par une modification de fiche."""

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
    prix_achat: Optional[float] = None
    prix_vente: Optional[float] = None


class DemandeEntreeStock(BaseModel):
    article_id: int
    site_id: Optional[int] = None
    quantite: int = Field(gt=0)
    motif: Optional[str] = Field(default=None, max_length=200)


class ReponseMouvementStock(BaseModel):
    """Réponse générique à un mouvement de stock : le nouveau stock du
    (article, site) visé, jamais plus (pas de fuite d'autres colonnes)."""

    article_id: int
    site_id: int
    quantite_stock: int


class DemandeTransfert(BaseModel):
    """Transfert multi-site (décision 2026-09-19) : UN article, deux sites.
    La ligne de stock de destination est créée automatiquement si absente."""

    article_id: int
    site_origine: int
    site_destination: int
    quantite: int = Field(gt=0)
    motif: str = Field(min_length=1, max_length=200)


class ReponseTransfert(BaseModel):
    article_id: int
    site_origine: int
    site_destination: int
    quantite_stock_origine: int
    quantite_stock_destination: int


class DemandeCasse(BaseModel):
    article_id: int
    site_id: Optional[int] = None
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


# ---------------------------------------------------------------------------
# Clôture de caisse (addendum, point g, décidé le 2026-09-13) — une clôture
# PAR SITE. L'attendu et l'écart ne sont JAMAIS saisis ni recalculés côté
# client : ``cloturer_caisse()`` (migration 019) les calcule seule.
# ---------------------------------------------------------------------------

class DemandeClotureCaisse(BaseModel):
    """``espece_comptee`` est seul obligatoire (la caisse physique certaine) ;
    les montants Mobile Money comptés restent optionnels (addendum, question 4
    non tranchée : aucun relevé d'opérateur n'est rapproché automatiquement).
    ``site_id`` suit le même principe que pour une vente ou un article :
    obligatoire pour un responsable (deux sites), jamais lu pour un autre rôle
    (de toute façon seul le responsable a accès à cette route).
    ``cloture_rectificative_de`` : identifiant de la clôture à corriger — NULL
    pour une clôture normale."""

    site_id: Optional[int] = None
    date_cloture: _date
    espece_comptee: float = Field(ge=0)
    orange_money_compte: Optional[float] = Field(default=None, ge=0)
    mtn_momo_compte: Optional[float] = Field(default=None, ge=0)
    autre_compte: Optional[float] = Field(default=None, ge=0)
    commentaire: Optional[str] = Field(default=None, max_length=500)
    cloture_rectificative_de: Optional[int] = None


class ReponseClotureCaisse(BaseModel):
    """Reflète exactement la ligne renvoyée par ``cloturer_caisse()`` — aucun
    champ recalculé par l'application : l'attendu et l'écart viennent tels
    quels de la fonction PostgreSQL."""

    cloture_id: int
    site_id: int
    date_cloture: _date
    attendu_especes: float
    attendu_orange_money: float
    attendu_mtn_momo: float
    attendu_autre: float
    compte_especes: float
    compte_orange_money: Optional[float] = None
    compte_mtn_momo: Optional[float] = None
    compte_autre: Optional[float] = None
    ecart_especes: float
    ecart_orange_money: Optional[float] = None
    ecart_mtn_momo: Optional[float] = None
    ecart_autre: Optional[float] = None
    commentaire: Optional[str] = None
    utilisateur_id: int
    cloture_rectificative_de: Optional[int] = None


# ---------------------------------------------------------------------------
# Gestion des comptes (chantier C2, cycle 32) — réservée au responsable.
# Le responsable crée des AGENTS uniquement (agent_stock / agent_comptabilite,
# site obligatoire — décision du 2026-09-20) : le premier compte responsable
# relève de l'outil C0-C, jamais de cette route.
# ---------------------------------------------------------------------------

class DemandeCompte(BaseModel):
    """Création d'un compte agent par le responsable. ``mot_de_passe`` est le
    mot de passe EN CLAIR envoyé une seule fois ; le serveur le hache en
    bcrypt (``securite.hacher_mot_de_passe``) et ne le restitue jamais."""

    nom_complet: str = Field(min_length=1, max_length=150)
    identifiant: str = Field(min_length=1, max_length=50)
    mot_de_passe: str = Field(min_length=8, max_length=200)
    role: Literal["agent_stock", "agent_comptabilite"]
    site_id: int


class ReponseCompte(BaseModel):
    """Profil public d'un compte — JAMAIS le hachage du mot de passe."""

    id: int
    nom_complet: str
    identifiant: str
    role: str
    site_id: Optional[int] = None
    actif: bool
    doit_changer_mot_de_passe: bool
    date_creation: datetime


class DemandeReinitialisationMotDePasse(BaseModel):
    """Le responsable saisit le nouveau mot de passe d'un agent (cycle 38) :
    >= 8 caractères, jamais restitué, changement forcé à la première
    connexion."""

    mot_de_passe: str = Field(min_length=8, max_length=200)


class ReponseReinitialisationMotDePasse(BaseModel):
    compte_id: int
    doit_changer_mot_de_passe: bool


class DemandeActifCompte(BaseModel):
    actif: bool
