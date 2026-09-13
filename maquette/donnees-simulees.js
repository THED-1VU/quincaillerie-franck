/* =============================================================================
   donnees-simulees.js — DONNÉES FACTICES pour la maquette d'ergonomie.
   -----------------------------------------------------------------------------
   Ce fichier est le SEUL endroit où vivent des données dans la maquette.
   Lors du câblage réel (cycles ultérieurs), il sera remplacé par des appels au
   serveur. Aucun écran ne doit inventer de donnée en dehors d'ici.

   RÈGLE MÉTIER RESPECTÉE ICI : le comptage d'inventaire est « à l'aveugle ».
   La liste à compter (inventaire.html) et la synthèse des écarts
   (tableau-bord.html) sont RÉELLES depuis le cycle 7 (chantier C7,
   `/inventaire/...`) — ce fichier ne porte donc plus aucune donnée
   d'inventaire, simulée ou non. La quantité attendue par le système n'a
   jamais existé ici et n'existe toujours nulle part côté page.
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

  // Tableau de bord responsable (mobile) : plus aucune donnée simulée ici.
  // Ventes du jour et alertes de stock réelles depuis les cycles 5 et 8,
  // écarts réels depuis le cycle 7 — voir tableau-bord.html.

};

// fcfa() a déménagé dans api.js (cycle 11) : un utilitaire d'affichage
// partagé n'est pas une donnée simulée, et stock.html (nouveau, cycle 11)
// en a besoin pour le responsable sans charger ce fichier.
