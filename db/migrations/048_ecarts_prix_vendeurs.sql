-- ============================================================================
-- 048 — Rapport « écarts de prix par vendeur » (point c, question 5, C5/C8).
-- ----------------------------------------------------------------------------
-- Décision du propriétaire (ADDENDUM_CAHIER_DES_CHARGES.md, point c,
-- « Décidé (2026-09-18), question 5 ») :
--   * seuil de signalement d'un prix négocié : 10 % SOUS le prix catalogue ;
--   * valeur de CONFIGURATION (pas une constante figée — modifiable sans
--     redéploiement, même principe que taux_tva / seuil_ecart_caisse_tolere) ;
--   * au-delà du seuil, la vente est SIGNALÉE dans le rapport — elle n'est
--     JAMAIS bloquée (un encaissement déjà fait n'est jamais remis en cause).
--
-- Le blocage historique de ce rapport (question 3 : qui est un vendeur ?)
-- est levé depuis le 2026-09-19 — le vendeur est une fiche EMPLOYÉ
-- (migration 040 : ventes.vendeur_id -> employes(id)), pas un compte.
--
-- Deux objets :
--   1. le paramètre `seuil_ecart_prix_vendeur` (décimal, 10 par défaut,
--      modifiable, décidÉ — jamais a_definir : le chiffre est tranché) ;
--   2. la vue `ecarts_prix_vendeurs` : UNE LIGNE PAR LIGNE DE VENTE payée
--      portant un prix_catalogue connu, avec son écart et son signalement.
--
-- La vue est SECURITY INVOKER : elle s'exécute avec les privilèges DU RÔLE
-- QUI LA LIT, jamais avec ceux de son propriétaire — la Row Level Security
-- par site (migration 008) s'applique donc PLEINEMENT. Un agent comptabilité
-- du Magasin ne verrait pas les écarts du Comptoir à travers elle, alors
-- qu'une vue classique (security definer implicite) les lui montrerait en
-- contournant le cloisonnement. C'est exactement le piège inverse de celui
-- documenté dans la migration 047 (fonction SECURITY DEFINER pour EXPOSER
-- une colonne sans élargir le reste) : ici il ne faut pas élargir.
--
-- Périmètre, volontairement restreint à la décision :
--   * ventes PAYÉES seulement — une vente annulée a restitué l'argent, elle
--     n'a aucun effet économique, aucun écart à signaler ;
--   * lignes avec prix_catalogue NON NULL (capturé par POST /ventes depuis
--     le cycle 42, migration 037) — les lignes antérieures ou écrites hors
--     route applicative n'ont pas cette information, jamais rétro-inventé ;
--   * écartligne à ligne : (prix_catalogue - prix_unitaire) / prix_catalogue.
--     La remise GLOBALE de la vente (037) est un mécanisme SÉPARÉ,
--     volontairement non distribué entre les lignes (décision 2026-09-23) :
--     elle est exposée en colonne informative (remise_globale_montant) mais
--     ne modifie l'écart d'AUCUNE ligne — la distribuer serait inventer une
--     règle que le propriétaire a explicitement refusée ;
--   * un prix payé AU-DESSUS du catalogue (upsell, toléré par 037) donne un
--     écart NÉGATIF, jamais signalé : la décision vise les prix négociés
--     sous le catalogue.
--
-- Lecture réservée au responsable et à l'agent comptabilité (même périmètre
-- que GET /rapports/ventes) : l'agent stock n'a aucun privilège sur ventes
-- (008) et ne reçoit donc aucun GRANT sur la vue.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Paramètre du seuil — décidé, modifiable, jamais bloquant.
-- ----------------------------------------------------------------------------
INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision)
SELECT 'seuil_ecart_prix_vendeur', '10', 'decimal',
       'Seuil de signalement (en % sous le prix catalogue) au-delà duquel '
       'une ligne de vente figure au signalement dans le rapport « écarts '
       'de prix par vendeur ». Signale sans jamais bloquer.',
       TRUE, FALSE, 'Décision 2026-09-18 (addendum point c, question 5)'
WHERE NOT EXISTS (SELECT 1 FROM parametres WHERE cle = 'seuil_ecart_prix_vendeur');

-- ----------------------------------------------------------------------------
-- 2. Vue du rapport.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW ecarts_prix_vendeurs
WITH (security_invoker = true)
AS
SELECT
    v.id                                   AS vente_id,
    v.site_id,
    s.nom                                  AS site_nom,
    v.numero_facturier,
    v.date_vente,
    v.vendeur_id,
    e.nom_complet                          AS vendeur_nom,
    v.remise_globale_montant,
    vl.article_id,
    a.nom                                  AS article_nom,
    vl.quantite,
    vl.prix_catalogue,
    vl.prix_unitaire,
    vl.prix_catalogue - vl.prix_unitaire   AS ecart_unitaire,
    (vl.prix_catalogue - vl.prix_unitaire) * vl.quantite
                                           AS ecart_total,
    ROUND(
        100 * (vl.prix_catalogue - vl.prix_unitaire) / vl.prix_catalogue,
        2
    )                                      AS ecart_pct,
    parametre_numerique('seuil_ecart_prix_vendeur')
                                           AS seuil_pct,
    (100 * (vl.prix_catalogue - vl.prix_unitaire) / vl.prix_catalogue)
        > parametre_numerique('seuil_ecart_prix_vendeur')
                                           AS signale
  FROM ventes v
  JOIN sites s             ON s.id = v.site_id
  JOIN ventes_lignes vl    ON vl.vente_id = v.id
  JOIN articles a          ON a.id = vl.article_id
  LEFT JOIN employes e     ON e.id = v.vendeur_id
 WHERE v.statut = 'payee'
   AND vl.prix_catalogue IS NOT NULL
   AND vl.prix_catalogue > 0;

COMMENT ON VIEW ecarts_prix_vendeurs IS
  'Rapport « écarts de prix par vendeur » (point c Q5, décidé 2026-09-18) : '
  'une ligne par ligne de vente payée à prix_catalogue connu, écart ligne à '
  'ligne sous le catalogue et signalement au-delà du paramètre '
  'seuil_ecart_prix_vendeur (10 %). SECURITY INVOKER : la RLS par site '
  '(008) s''applique au rôle lecteur — un agent comptabilité ne voit que '
  'SON site. La remise globale (037), mécanisme séparé non distribué entre '
  'lignes (décision 2026-09-23), est exposée en colonne informative sans '
  'modifier l''écart d''aucune ligne. Signale, ne bloque jamais.';

GRANT SELECT ON ecarts_prix_vendeurs TO qf_responsable, qf_agent_comptabilite;

INSERT INTO schema_migrations (version, nom)
VALUES ('048', 'ecarts_prix_vendeurs')
ON CONFLICT (version) DO NOTHING;
