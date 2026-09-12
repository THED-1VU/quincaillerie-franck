/* =============================================================================
   donnees-simulees.js — DONNÉES FACTICES pour la maquette d'ergonomie.
   -----------------------------------------------------------------------------
   Ce fichier est le SEUL endroit où vivent des données dans la maquette.
   Lors du câblage réel (cycles ultérieurs), il sera remplacé par des appels au
   serveur. Aucun écran ne doit inventer de donnée en dehors d'ici.

   RÈGLE MÉTIER RESPECTÉE ICI : le comptage d'inventaire est « à l'aveugle ».
   La quantité attendue par le système N'EST PAS présente dans ce fichier, ni
   nulle part côté page. Elle n'existe que côté serveur ; l'écart sera calculé
   par la base (voir MODELE_DONNEES.md et le cycle C1). Ne PAS ajouter de champ
   « quantite_attendue » dans DONNEES.inventaire.
   ============================================================================= */

const DONNEES = {

  /* Utilisateur simulé connecté (pour les bandeaux). */
  session: {
    nom: "Awa Franck",
    role: "Responsable",
    site: "Les deux sites",
  },

  /* Catalogue pour l'écran de vente (comptoir).
     prixCatalogue est INDICATIF : le prix réellement facturé est saisi par
     vente (négociation avec le client). Aucune quantité de stock ici : la
     comptabilité ne doit pas la voir. */
  catalogue: [
    { id: "ART-014", nom: "Clou 5 cm",            unite: "kg",     prixCatalogue: 800   },
    { id: "ART-021", nom: "Ciment CIM II 50 kg",  unite: "sac",    prixCatalogue: 6500  },
    { id: "ART-007", nom: "Fer à béton 8 mm",     unite: "barre",  prixCatalogue: 3500  },
    { id: "ART-033", nom: "Peinture blanche 4 L", unite: "bidon",  prixCatalogue: 12000 },
    { id: "ART-041", nom: "Robinet standard",     unite: "pièce",  prixCatalogue: 3000  },
    { id: "ART-052", nom: "Tuyau PVC 100 mm",     unite: "barre",  prixCatalogue: 4500  },
    { id: "ART-060", nom: "Cadenas 40 mm",        unite: "pièce",  prixCatalogue: 2500  },
    { id: "ART-063", nom: "Colle à carrelage 25 kg", unite: "sac", prixCatalogue: 7800  },
    { id: "ART-070", nom: "Disque à tronçonner 230", unite: "pièce", prixCatalogue: 1500 },
    { id: "ART-084", nom: "Vis à bois 4x40 (boîte)", unite: "boîte", prixCatalogue: 2000 },
  ],

  /* « credit_client » existe dans le schéma mais reste désactivé au niveau
     applicatif (addendum, point b — décision du propriétaire, cycle 6) :
     volontairement absent de cette liste, pour qu'il ne soit même pas
     proposable à l'écran plutôt que proposé puis refusé par le serveur.
     Cette liste reste simulée (aucune route ne l'expose), mais ses codes
     doivent rester synchronisés avec server/app/routes/ventes.py. */
  modesPaiement: [
    { code: "especes",       libelle: "Espèces" },
    { code: "orange_money",  libelle: "Orange Money" },
    { code: "mtn_momo",      libelle: "MTN Mobile Money" },
    { code: "autre",         libelle: "Autre" },
  ],

  /* Tableau de bord responsable (mobile). Chiffres figés. */
  tableauBord: {
    date: "mercredi 10 septembre 2026",
    ventesJour: [
      { site: "Comptoir", nbVentes: 14, total: 168500 },
      { site: "Magasin de stock", nbVentes: 6, total: 240000 },
    ],
    alertesStock: [
      { article: "Ciment CIM II 50 kg", site: "Magasin de stock", reste: 4, unite: "sac" },
      { article: "Peinture blanche 4 L", site: "Comptoir", reste: 2, unite: "bidon" },
      { article: "Disque à tronçonner 230", site: "Comptoir", reste: 3, unite: "pièce" },
    ],
    /* Écarts d'inventaire du jour : la valeur est un RÉSULTAT déjà calculé côté
       serveur, affiché au responsable après coup. Ce n'est pas le comptage
       à l'aveugle lui-même. */
    ecartsInventaire: [
      { article: "Ciment CIM II 50 kg", site: "Magasin de stock", moment: "matin", ecart: -2 },
      { article: "Robinet standard", site: "Comptoir", moment: "matin", ecart: 0 },
    ],
  },

  /* Écran de comptage à l'aveugle : UNIQUEMENT de quoi identifier l'article.
     PAS de quantité attendue. PAS de stock. L'agent saisit ce qu'il compte. */
  inventaire: {
    site: "Magasin de stock",
    moment: "matin",
    date: "10 septembre 2026",
    articles: [
      { id: "ART-021", nom: "Ciment CIM II 50 kg", unite: "sac" },
      { id: "ART-007", nom: "Fer à béton 8 mm",    unite: "barre" },
      { id: "ART-052", nom: "Tuyau PVC 100 mm",    unite: "barre" },
      { id: "ART-063", nom: "Colle à carrelage 25 kg", unite: "sac" },
      { id: "ART-070", nom: "Disque à tronçonner 230", unite: "pièce" },
    ],
  },
};

/* Petit utilitaire d'affichage des montants en francs CFA (pas de sous-unité). */
function fcfa(montant) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Math.round(montant)) + " FCFA";
}
