"""Modèles Pydantic des requêtes et réponses de l'API."""

from __future__ import annotations

from datetime import date as _date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


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
    papier. Trois façons d'exprimer le prix, UNE SEULE à la fois (décision
    2026-09-22, addendum point f — remise en montant OU en pourcentage, au
    choix) :
      * ``prix_unitaire`` : le prix négocié TTC directement (addendum,
        point d — comportement historique, inchangé) ;
      * ``remise_montant`` : une remise en FCFA par unité, appliquée au
        prix catalogue du moment ;
      * ``remise_pct`` : une remise en pourcentage du prix catalogue.
    Dans les deux derniers cas, le serveur résout ``prix_unitaire`` à
    partir du prix catalogue réel de l'article — jamais une valeur
    inventée par le client."""

    article_id: int
    quantite: Decimal = Field(gt=0)
    prix_unitaire: Optional[float] = Field(default=None, ge=0)
    remise_montant: Optional[float] = Field(default=None, ge=0)
    remise_pct: Optional[float] = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def _un_seul_mode_de_prix(self) -> "LigneVenteDemande":
        fournis = [v is not None for v in (self.prix_unitaire, self.remise_montant, self.remise_pct)]
        if sum(fournis) != 1:
            raise ValueError(
                "Fournir exactement un des trois : prix_unitaire, remise_montant ou remise_pct."
            )
        return self


class DemandeVente(BaseModel):
    """``site_id`` n'est utilisé QUE pour un compte responsable (deux
    sites) : pour un agent comptabilité, le site vient toujours de sa
    session, jamais du corps de la requête.

    ``numero_facturier`` et ``vendeur_id`` sont obligatoires depuis le
    cycle 27 (addendum, point c, décidé le 2026-09-13) : référence du
    carnet papier tenu par le responsable, et personne ayant négocié le
    prix — voir ``db/migrations/020_facturier_vendeur.sql``.

    ``remise_globale_montant``/``remise_globale_pct`` (décision
    2026-09-22, addendum point f) : remise sur la vente ENTIÈRE, mécanisme
    séparé d'une remise par ligne — au plus un des deux, aucun n'est
    obligatoire (pas de remise globale par défaut).

    ``client_id`` (addendum point b, décidé le 2026-09-25) : obligatoire
    uniquement quand ``mode_paiement == 'credit_client'`` — la vérification
    elle-même (obligatoire, client actif, plafond) est faite dans la route,
    pas ici, car elle dépend de l'état de la base."""

    site_id: Optional[int] = None
    mode_paiement: str = Field(min_length=1, max_length=30)
    numero_facturier: str = Field(min_length=1, max_length=30)
    vendeur_id: int
    lignes: List[LigneVenteDemande] = Field(min_length=1)
    remise_globale_montant: Optional[float] = Field(default=None, ge=0)
    remise_globale_pct: Optional[float] = Field(default=None, ge=0, le=100)
    client_id: Optional[int] = None

    @model_validator(mode="after")
    def _au_plus_une_remise_globale(self) -> "DemandeVente":
        if self.remise_globale_montant is not None and self.remise_globale_pct is not None:
            raise ValueError(
                "Fournir au plus un des deux : remise_globale_montant ou remise_globale_pct."
            )
        return self


class LigneEcartReponse(BaseModel):
    """Un écart signalé au comptable au moment même de la saisie — jamais un
    refus (addendum, point e) : la quantité demandée dépassait le stock
    disponible, la différence a été consignée pour le responsable."""

    article_id: int
    quantite_manquante: float


class ReponseVente(BaseModel):
    vente_id: int
    site_id: int
    numero_facturier: str
    sous_total_ht: float
    taux_tva: float
    montant_tva: float
    total_ttc: float
    remise_totale: float
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
    quantite_comptee: Decimal = Field(ge=0)


class ReponseComptage(BaseModel):
    """Ne renvoie JAMAIS quantite_attendue ni ecart — voir
    server/app/routes/inventaire.py."""

    comptage_id: int
    article_id: int
    moment: str
    quantite_comptee: float


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
    quantite_decimale_autorisee: bool = False
    """Décision 2026-09-22 (addendum, point f) : entier seulement si faux
    (défaut) — décidé par article, comme l'unité elle-même."""


class ReponseArticle(BaseModel):
    article_id: int
    nom: str
    unite: str
    quantite_decimale_autorisee: bool


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
    quantite_decimale_autorisee: Optional[bool] = None


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
    quantite_decimale_autorisee: bool


class DemandeEntreeStock(BaseModel):
    article_id: int
    site_id: Optional[int] = None
    quantite: Decimal = Field(gt=0)
    motif: Optional[str] = Field(default=None, max_length=200)


class ReponseMouvementStock(BaseModel):
    """Réponse générique à un mouvement de stock : le nouveau stock du
    (article, site) visé, jamais plus (pas de fuite d'autres colonnes)."""

    article_id: int
    site_id: int
    quantite_stock: float


class DemandeTransfert(BaseModel):
    """Transfert multi-site (décision 2026-09-19) : UN article, deux sites.
    La ligne de stock de destination est créée automatiquement si absente."""

    article_id: int
    site_origine: int
    site_destination: int
    quantite: Decimal = Field(gt=0)
    motif: str = Field(min_length=1, max_length=200)


class ReponseTransfert(BaseModel):
    article_id: int
    site_origine: int
    site_destination: int
    quantite_stock_origine: float
    quantite_stock_destination: float


# ---------------------------------------------------------------------------
# Casse : déclaration -> validation (migration 036, point f, décision
# 2026-09-22) — n'importe quel rôle qui touche au stock peut déclarer,
# seul le responsable peut valider (ce qui décrémente réellement le stock).
# ---------------------------------------------------------------------------

class DemandeDeclarationCasse(BaseModel):
    article_id: int
    site_id: Optional[int] = None
    quantite: Decimal = Field(gt=0)
    motif: str = Field(min_length=1, max_length=200)
    observation: Optional[str] = Field(default=None, max_length=500)


class ReponseDeclarationCasse(BaseModel):
    declaration_id: int
    statut: str


class ReponseCasseDetail(BaseModel):
    """Une déclaration de casse, pour la liste de celles en attente de
    validation par le responsable."""

    declaration_id: int
    article_id: int
    article_nom: str
    site_id: int
    quantite: float
    motif: str
    observation: Optional[str] = None
    declarant_id: int
    declarant_nom: str
    date_declaration: datetime
    statut: str


class DemandeValidationCasse(BaseModel):
    """Corps vide — le déclarant n'a rien à fournir de plus ; le validateur
    vient de la session, jamais du corps de la requête."""


class ReponseValidationCasse(BaseModel):
    declaration_id: int
    article_id: int
    site_id: int
    quantite_stock: float


# ---------------------------------------------------------------------------
# Retour client : déclaration -> validation (migration 036, point f,
# décision 2026-09-22) — validation du responsable obligatoire, état de la
# marchandise vérifié avant toute réintégration, trois issues possibles.
# ---------------------------------------------------------------------------

class DemandeDeclarationRetourClient(BaseModel):
    article_id: int
    vente_id: int
    quantite: Decimal = Field(gt=0)
    issue: Literal["echange", "avoir_client", "remboursement_especes"]
    etat_marchandise: Literal["revendable", "invendable"]
    motif: Optional[str] = Field(default=None, max_length=200)


class ReponseDeclarationRetourClient(BaseModel):
    declaration_id: int
    statut: str


class ReponseRetourClientDetail(BaseModel):
    declaration_id: int
    article_id: int
    article_nom: str
    vente_id: int
    site_id: int
    quantite: float
    issue: str
    etat_marchandise: str
    motif: Optional[str] = None
    declarant_id: int
    declarant_nom: str
    date_declaration: datetime
    statut: str
    mode_paiement: str
    client_nom: Optional[str] = None


class DemandeValidationRetourClient(BaseModel):
    """``confirmation_remboursement`` : exigé explicitement (``True``) pour
    valider une déclaration dont l'issue est un remboursement espèces —
    refusé sinon, quelle que soit la déclaration."""

    confirmation_remboursement: bool = False


class ReponseValidationRetourClient(BaseModel):
    declaration_id: int
    article_id: int
    site_id: int
    quantite_stock: float


# ---------------------------------------------------------------------------
# Article offert : déclaration -> validation (migration 039, point f,
# décision 2026-09-22/24) — distinct d'une remise à 100 % (migration 037,
# qui la refuse). employe_id : qui a physiquement offert l'article (fiche
# RH), distinct du compte qui saisit la déclaration — exigence du
# 2026-09-24 (« le geste le plus facile à détourner »).
# ---------------------------------------------------------------------------

class DemandeDeclarationArticleOffert(BaseModel):
    article_id: int
    site_id: Optional[int] = None
    quantite: Decimal = Field(gt=0)
    motif: str = Field(min_length=1, max_length=200)
    employe_id: int
    vente_id: Optional[int] = None
    client_nom: Optional[str] = Field(default=None, max_length=150)


class ReponseDeclarationArticleOffert(BaseModel):
    declaration_id: int
    statut: str


class ReponseArticleOffertDetail(BaseModel):
    """Une déclaration d'article offert, pour la liste de celles en attente
    de validation par le responsable."""

    declaration_id: int
    article_id: int
    article_nom: str
    site_id: int
    quantite: float
    valeur_normale: float
    vente_id: Optional[int] = None
    client_nom: Optional[str] = None
    employe_id: int
    employe_nom: str
    motif: str
    declarant_id: int
    declarant_nom: str
    date_declaration: datetime
    statut: str


class DemandeValidationArticleOffert(BaseModel):
    """Corps vide — le déclarant n'a rien à fournir de plus ; le validateur
    vient de la session, jamais du corps de la requête."""


class ReponseValidationArticleOffert(BaseModel):
    declaration_id: int
    article_id: int
    site_id: int
    quantite_stock: float


class DemandeRetourFournisseur(BaseModel):
    mouvement_origine_id: int
    quantite: Decimal = Field(gt=0)
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
    bcrypt (``securite.hacher_mot_de_passe``) et ne le restitue jamais.
    ``role`` reste le rôle PRINCIPAL ; ``roles`` (optionnel, cycle 41) porte
    la liste complète des rôles cumulés — petit effectif, addendum point h
    question 4, décidée le 2026-09-22."""

    nom_complet: str = Field(min_length=1, max_length=150)
    identifiant: str = Field(min_length=1, max_length=50)
    mot_de_passe: str = Field(min_length=8, max_length=200)
    role: Literal["agent_stock", "agent_comptabilite"]
    site_id: int
    roles: list[Literal["agent_stock", "agent_comptabilite"]] = []


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
    roles: list[str] = []


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


# ---------------------------------------------------------------------------
# Crédit client (addendum, point b, décidé le 2026-09-25) — clients,
# créances, règlements. Partagé entre les deux sites (site_id informatif,
# jamais un filtre) ; plafond par client, 100 000 FCFA par défaut ;
# règlements partiels alloués en FIFO (jamais liés à une créance précise) ;
# aucune relance automatique, aucun intérêt.
# ---------------------------------------------------------------------------

class DemandeClient(BaseModel):
    nom: str = Field(min_length=1, max_length=150)
    telephone: Optional[str] = Field(default=None, max_length=30)
    plafond_credit: float = Field(default=100000, ge=0)
    site_id: Optional[int] = None


class ReponseClient(BaseModel):
    id: int
    nom: str
    telephone: Optional[str] = None
    plafond_credit: float
    site_id: Optional[int] = None
    actif: bool
    encours: float


class DemandeReglementCreance(BaseModel):
    montant: float = Field(gt=0)
    motif: Optional[str] = Field(default=None, max_length=200)


class ReponseReglementCreance(BaseModel):
    client_id: int
    encours: float


class ReponseVieillissementCreances(BaseModel):
    tranche: str
    montant: float
