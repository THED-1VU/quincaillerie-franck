-- ============================================================================
-- 040 — Chantier B : réconciliation ventes.vendeur_id / employe_id
--        (addendum point c, question 3 — enfin tranchée).
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (2026-09-25) : le vendeur d'une vente est
-- TOUJOURS une fiche employé du module RH (`employes`), jamais un compte
-- utilisateur — des aides occasionnels négocient un prix sans jamais se
-- connecter au logiciel. `ventes.vendeur_id` référençait `utilisateurs(id)`
-- depuis la migration 020 (2026-09-13) ; ce cycle unifie le modèle sur
-- `employes`, la même notion que `declarations_article_offert.employe_id`
-- (migration 039).
--
-- Deux notions RESTENT distinctes, volontairement non fusionnées : le
-- VENDEUR (qui a négocié le prix, `ventes.vendeur_id`) et le DÉCLARANT/
-- ENCAISSEUR (`ventes.utilisateur_id`/`utilisateur_caisse_id`, toujours un
-- compte) — un vendeur sans compte reste une personne réelle, jamais
-- confondue avec qui saisit ou encaisse.
--
-- Aucune correspondance historique inventée (2026-09-25, confirmé par le
-- propriétaire) : le projet est encore avant son premier lancement réel
-- (point j, reprise du stock initial, non traité) — aucune vente réelle à
-- protéger. Toute valeur de vendeur_id qui ne correspondrait plus à un
-- employé réel après ce changement de cible est mise à NULL avant d'ajouter
-- la nouvelle contrainte, plutôt que de la laisser faire échouer la
-- migration — comportement sûr si cette migration est rejouée un jour sur
-- une base qui contiendrait déjà des ventes réelles.
--
-- Présélection automatique du vendeur (aujourd'hui basée sur la coïncidence
-- « le compte connecté partage l'espace d'identifiants du vendeur ») :
-- volontairement PAS remplacée par un lien compte<->employé — hors
-- périmètre de cette réconciliation (décision du propriétaire, validation
-- du plan, 2026-09-25). Le vendeur reste choisi manuellement à chaque vente.
--
-- Même convention que la migration 039 : un employé avec site_id NULL
-- couvre les deux sites (même principe que le responsable).
-- ============================================================================

ALTER TABLE ventes DROP CONSTRAINT ventes_vendeur_id_fkey;

UPDATE ventes SET vendeur_id = NULL
 WHERE vendeur_id IS NOT NULL
   AND vendeur_id NOT IN (SELECT id FROM employes);

ALTER TABLE ventes ADD CONSTRAINT ventes_vendeur_id_fkey
  FOREIGN KEY (vendeur_id) REFERENCES employes(id);

COMMENT ON COLUMN ventes.vendeur_id IS
    'Personne ayant négocié le prix et rempli la ligne du facturier papier '
    '(addendum point c) — une fiche employé (module RH), PAS un compte '
    'utilisateur (décision 2026-09-25, migration 040) : un vendeur peut '
    'n''avoir jamais eu de compte. Distincte de utilisateur_id (qui saisit) '
    'et de utilisateur_caisse_id (qui encaisse), même si les trois '
    'coïncident souvent en pratique. Un employé site_id NULL couvre les '
    'deux sites (même convention que declarations_article_offert.employe_id, '
    'migration 039).';

INSERT INTO schema_migrations (version, nom)
VALUES ('040', 'vendeur_employe')
ON CONFLICT (version) DO NOTHING;
