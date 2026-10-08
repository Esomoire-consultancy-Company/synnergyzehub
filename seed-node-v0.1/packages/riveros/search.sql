-- RiverOS governed read-only search function.
-- Apply after packages/riveros/schema.sql.

CREATE OR REPLACE FUNCTION riveros.search_events(
  p_workspace_id UUID,
  p_event_type TEXT DEFAULT NULL,
  p_lifecycle_status TEXT DEFAULT NULL,
  p_object_type TEXT DEFAULT NULL,
  p_actor_type TEXT DEFAULT NULL,
  p_settlement_eligibility TEXT DEFAULT NULL,
  p_commercial_relevance BOOLEAN DEFAULT NULL,
  p_occurred_after TIMESTAMPTZ DEFAULT NULL,
  p_occurred_before TIMESTAMPTZ DEFAULT NULL,
  p_text_query TEXT DEFAULT NULL,
  p_limit INTEGER DEFAULT 50
)
RETURNS SETOF riveros.events
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = pg_catalog, public, riveros
AS $$
  SELECT e.*
  FROM riveros.events AS e
  WHERE e.workspace_id = p_workspace_id
    AND (p_event_type IS NULL OR e.event_type = p_event_type)
    AND (p_lifecycle_status IS NULL OR e.lifecycle_status = p_lifecycle_status)
    AND (p_object_type IS NULL OR e.object_type = p_object_type)
    AND (p_actor_type IS NULL OR e.actor_type = p_actor_type)
    AND (
      p_settlement_eligibility IS NULL
      OR e.settlement_eligibility = p_settlement_eligibility
    )
    AND (
      p_commercial_relevance IS NULL
      OR e.commercial_relevance = p_commercial_relevance
    )
    AND (p_occurred_after IS NULL OR e.occurred_at >= p_occurred_after)
    AND (p_occurred_before IS NULL OR e.occurred_at <= p_occurred_before)
    AND (
      NULLIF(BTRIM(p_text_query), '') IS NULL
      OR to_tsvector(
        'simple',
        CONCAT_WS(
          ' ',
          e.event_type,
          e.action,
          e.object_type,
          e.object_id,
          e.source_system,
          COALESCE(e.metadata::text, '')
        )
      ) @@ websearch_to_tsquery('simple', p_text_query)
    )
  ORDER BY e.occurred_at DESC, e.id DESC
  LIMIT LEAST(GREATEST(COALESCE(p_limit, 50), 1), 200);
$$;

COMMENT ON FUNCTION riveros.search_events(
  UUID, TEXT, TEXT, TEXT, TEXT, TEXT, BOOLEAN,
  TIMESTAMPTZ, TIMESTAMPTZ, TEXT, INTEGER
) IS
  'Read-only, workspace-scoped RiverOS event search using an explicit structured plan.';
