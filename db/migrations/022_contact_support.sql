-- ============================================================================
-- 022 — Chantier C12 (cycle 28) : qui prévenir quand la base de données
-- devient injoignable en pleine vente.
-- ----------------------------------------------------------------------------
-- Exigence du propriétaire (2026-09-18) : le message affiché au vendeur doit
-- dire qui prévenir, en français simple. Aucun nom ni numéro n'est connu de
-- ce projet — amorcé à la sentinelle « a_definir » (même principe que
-- boutique_telephone, migration 006) : le message qui l'utilise (voir
-- server/app/main.py) omet simplement cette phrase tant que le paramètre
-- n'est pas fixé, plutôt que d'inventer un contact.
-- ============================================================================

INSERT INTO parametres (cle, valeur, type_valeur, description, modifiable, a_decider, reference_decision)
VALUES
('contact_support_technique', 'a_definir', 'texte',
 'Personne ou numéro à prévenir quand l''application affiche « la base de '
 'données ne répond pas » (cycle 28). Affiché tel quel dans ce message une '
 'fois fixé — jamais inventé.',
 TRUE, TRUE, 'à fournir par le propriétaire')
ON CONFLICT (cle) DO NOTHING;

INSERT INTO schema_migrations (version, nom)
VALUES ('022', 'contact_support')
ON CONFLICT (version) DO NOTHING;
