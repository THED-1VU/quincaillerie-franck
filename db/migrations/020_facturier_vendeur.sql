-- ============================================================================
-- 020 — Chantier C5 : numéro de facturier papier + vendeur (addendum,
-- point c, décidé le 2026-09-13).
-- ----------------------------------------------------------------------------
-- Périmètre VOLONTAIREMENT réduit au socle décidé, rien de plus :
--   - numero_facturier : référence du carnet papier, transcrite par le
--     comptable au moment de la saisie (PAS un numéro généré par le
--     logiciel — le facturier papier existe déjà, indépendamment de ce
--     projet). Obligatoire et unique sur toute NOUVELLE vente (voir
--     server/app/routes/ventes.py) ; NULL toléré en base pour les ventes
--     déjà enregistrées avant ce cycle, jamais rétro-inventé.
--   - vendeur_id : la personne qui a négocié le prix et rempli la ligne du
--     carnet — distincte de utilisateur_id (qui SAISIT la vente dans le
--     logiciel, souvent après coup) et de utilisateur_caisse_id (qui
--     ENCAISSE). Les trois peuvent coïncider ou non.
--
-- Explicitement PAS traité ce cycle (questions 2 à 5 de l'addendum, point c,
-- non tranchées) :
--   - format exact du numéro au-delà du préfixe (question 2) — aucune
--     séquence ni longueur imposée, uniquement le préfixe par site ci-dessous ;
--   - vendeur sans compte utilisateur, ex. apprenti (question 3) —
--     vendeur_id référence TOUJOURS un compte existant, aucune liste de
--     vendeurs séparée n'est créée ;
--   - blocage vs alerte à la saisie sans numéro (question 4) — les deux
--     champs sont simplement obligatoires (Pydantic + CHECK), ce qui
--     revient à un blocage, cohérent avec « obligatoire » déjà décidé ;
--   - seuil de validation d'un écart de prix, rapport « écarts de prix par
--     vendeur » (question 5) — AUCUN rapport construit ce cycle, aucun
--     seuil inventé.
-- ============================================================================

ALTER TABLE ventes ADD COLUMN IF NOT EXISTS numero_facturier VARCHAR(30);
ALTER TABLE ventes ADD COLUMN IF NOT EXISTS vendeur_id INTEGER REFERENCES utilisateurs(id);

COMMENT ON COLUMN ventes.numero_facturier IS
    'Référence du carnet papier (facturier), transcrite par le comptable — '
    'PAS un numéro généré par le logiciel. Préfixe par site vérifié par '
    'chk_ventes_numero_facturier_prefixe_site ci-dessous ; format au-delà '
    'du préfixe volontairement libre (addendum point c, question 2 non '
    'tranchée). NULL toléré pour les ventes antérieures au cycle 27, '
    'jamais rétro-inventé.';

COMMENT ON COLUMN ventes.vendeur_id IS
    'Personne ayant négocié le prix et rempli la ligne du facturier papier '
    '(addendum point c) — distincte de utilisateur_id (qui saisit) et de '
    'utilisateur_caisse_id (qui encaisse), même si les trois coïncident '
    'souvent en pratique. Référence toujours un compte existant '
    '(question 3 non tranchée : pas de liste de vendeurs séparée).';

-- Unicité du numéro de facturier — une ligne de carnet ne peut pas
-- correspondre à deux ventes distinctes dans le logiciel. Une contrainte
-- UNIQUE simple tolère plusieurs NULL (ventes historiques) sans conflit
-- entre elles, comportement standard PostgreSQL.
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS uq_ventes_numero_facturier;
ALTER TABLE ventes ADD CONSTRAINT uq_ventes_numero_facturier UNIQUE (numero_facturier);

-- Préfixe par site (décidé : MAG- au Magasin de stock, CPT- au Comptoir) —
-- seule partie du format tranchée par le propriétaire ; le reste après le
-- préfixe est libre (question 2 non tranchée). Ne s'applique qu'aux
-- valeurs non nulles, pour ne jamais invalider une vente historique.
ALTER TABLE ventes DROP CONSTRAINT IF EXISTS chk_ventes_numero_facturier_prefixe_site;
ALTER TABLE ventes ADD CONSTRAINT chk_ventes_numero_facturier_prefixe_site
    CHECK (
        numero_facturier IS NULL
        OR (site_id = 1 AND numero_facturier LIKE 'MAG-%')
        OR (site_id = 2 AND numero_facturier LIKE 'CPT-%')
    );

CREATE INDEX IF NOT EXISTS idx_ventes_vendeur_id ON ventes(vendeur_id);

-- Aucun GRANT supplémentaire nécessaire : les privilèges sur `ventes` posés
-- à la migration 008 sont au niveau de la TABLE (GRANT SELECT, INSERT,
-- UPDATE ON ventes ... TO qf_responsable, qf_agent_comptabilite), donc déjà
-- valables pour ces deux nouvelles colonnes.

INSERT INTO schema_migrations (version, nom)
VALUES ('020', 'facturier_vendeur')
ON CONFLICT (version) DO NOTHING;
