-- ============================================================
-- Research Pipeline: Unified Supabase Schema Migration
-- ============================================================
-- Run this against your Supabase project to create the unified
-- schema. This replaces the separate documents, mermaid_diagrams,
-- and perspectives tables with a coherent structure.
--
-- Prerequisites: pgvector extension enabled
-- ============================================================

-- Ensure pgvector is available
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 1. RESEARCH LIBRARIES
-- A library is a named research project (e.g., a BibTeX collection)
-- ============================================================
CREATE TABLE IF NOT EXISTS research_libraries (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name          TEXT NOT NULL,                          -- e.g., "STIG Automation 2025"
  description   TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now(),
  metadata      JSONB DEFAULT '{}'::jsonb               -- flexible metadata bucket
);

CREATE INDEX IF NOT EXISTS idx_research_libraries_name ON research_libraries(name);

-- ============================================================
-- 2. CITATIONS
-- Individual papers/articles with verification status
-- ============================================================
CREATE TABLE IF NOT EXISTS citations (
  id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  library_id        BIGINT REFERENCES research_libraries(id) ON DELETE CASCADE,
  citation_key      TEXT NOT NULL,                       -- BibTeX key e.g., "smith_2024"
  entry_type        TEXT,                                -- @article, @misc, @inproceedings
  title             TEXT NOT NULL,
  authors           TEXT,
  year              INT,
  journal           TEXT,
  abstract          TEXT,
  doi               TEXT,
  arxiv_id          TEXT,
  url               TEXT,
  bibtex_raw        TEXT,                                -- original BibTeX entry

  -- Verification fields (from AutoResearchClaw 4-layer system)
  verification_status  TEXT DEFAULT 'unverified'         -- unverified, verified, failed, hallucinated
    CHECK (verification_status IN ('unverified', 'verified', 'failed', 'hallucinated')),
  doi_verified      BOOLEAN DEFAULT FALSE,
  arxiv_verified    BOOLEAN DEFAULT FALSE,
  semantic_score    FLOAT,                               -- 0-1 semantic match confidence
  llm_relevance     FLOAT,                               -- 0-1 LLM-assessed relevance
  verification_log  JSONB DEFAULT '[]'::jsonb,           -- audit trail of verification steps
  verified_at       TIMESTAMPTZ,

  -- Discovery metadata
  source            TEXT DEFAULT 'bibtex_import',         -- bibtex_import, openalex, semantic_scholar, arxiv
  discovered_at     TIMESTAMPTZ DEFAULT now(),

  -- Embedding for semantic search
  embedding         vector(1536),                        -- OpenAI text-embedding-3-small

  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now(),
  metadata          JSONB DEFAULT '{}'::jsonb,

  UNIQUE(library_id, citation_key)
);

CREATE INDEX IF NOT EXISTS idx_citations_library ON citations(library_id);
CREATE INDEX IF NOT EXISTS idx_citations_verification ON citations(verification_status);
CREATE INDEX IF NOT EXISTS idx_citations_doi ON citations(doi) WHERE doi IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_citations_arxiv ON citations(arxiv_id) WHERE arxiv_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_citations_source ON citations(source);

-- ============================================================
-- 3. THEMATIC MAPS (replaces mermaid_diagrams)
-- Mermaid diagrams + theme inventories for a library
-- ============================================================
CREATE TABLE IF NOT EXISTS thematic_maps (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  library_id      BIGINT REFERENCES research_libraries(id) ON DELETE CASCADE,
  version         INT DEFAULT 1,
  mermaid_code    TEXT NOT NULL,                         -- raw mermaid syntax
  mermaid_markdown TEXT,                                 -- fenced markdown block
  theme_inventory JSONB,                                 -- structured theme data
  planned_tree    TEXT,                                  -- planned tree markdown

  embedding       vector(1536),

  created_at      TIMESTAMPTZ DEFAULT now(),
  metadata        JSONB DEFAULT '{}'::jsonb,

  -- Link to Google Drive artifact
  gdrive_file_id  TEXT,
  gdrive_url      TEXT
);

CREATE INDEX IF NOT EXISTS idx_thematic_maps_library ON thematic_maps(library_id);

-- ============================================================
-- 4. PERSPECTIVES (writing angle / audience / sub-themes)
-- ============================================================
CREATE TABLE IF NOT EXISTS research_perspectives (
  id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  library_id          BIGINT REFERENCES research_libraries(id) ON DELETE CASCADE,
  topic               TEXT NOT NULL,
  target_market       TEXT NOT NULL,
  writing_perspective TEXT NOT NULL,
  sub_themes          JSONB NOT NULL,                    -- ["theme1", "theme2", ...]
  perspective_json    JSONB,                             -- full perspective.json
  perspective_markdown TEXT,                             -- rendered markdown

  embedding           vector(1536),

  created_at          TIMESTAMPTZ DEFAULT now(),
  metadata            JSONB DEFAULT '{}'::jsonb,

  gdrive_file_id      TEXT,
  gdrive_url          TEXT
);

CREATE INDEX IF NOT EXISTS idx_perspectives_library ON research_perspectives(library_id);

-- ============================================================
-- 5. DISCOVERY RUNS
-- Track literature discovery executions
-- ============================================================
CREATE TABLE IF NOT EXISTS discovery_runs (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  library_id      BIGINT REFERENCES research_libraries(id) ON DELETE CASCADE,
  query_terms     JSONB NOT NULL,                        -- search terms used
  sources_searched JSONB NOT NULL,                       -- ["openalex", "semantic_scholar", "arxiv"]
  results_found   INT DEFAULT 0,
  new_citations   INT DEFAULT 0,                         -- how many were actually new
  run_type        TEXT DEFAULT 'manual'                   -- manual, scheduled
    CHECK (run_type IN ('manual', 'scheduled')),
  status          TEXT DEFAULT 'running'
    CHECK (status IN ('running', 'completed', 'failed')),
  error_log       TEXT,
  started_at      TIMESTAMPTZ DEFAULT now(),
  completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_discovery_runs_library ON discovery_runs(library_id);

-- ============================================================
-- 6. GAP ANALYSIS
-- Identified gaps in the research library
-- ============================================================
CREATE TABLE IF NOT EXISTS research_gaps (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  library_id      BIGINT REFERENCES research_libraries(id) ON DELETE CASCADE,
  gap_description TEXT NOT NULL,
  suggested_queries JSONB,                               -- search queries to fill the gap
  severity        TEXT DEFAULT 'medium'
    CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  status          TEXT DEFAULT 'open'
    CHECK (status IN ('open', 'investigating', 'filled', 'wont_fill')),
  filled_by       BIGINT REFERENCES citations(id),       -- citation that filled this gap
  created_at      TIMESTAMPTZ DEFAULT now(),
  resolved_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_gaps_library ON research_gaps(library_id);
CREATE INDEX IF NOT EXISTS idx_gaps_status ON research_gaps(status);

-- ============================================================
-- FUNCTIONS: Paginated document reader
-- ============================================================
CREATE OR REPLACE FUNCTION read_library_citations(
  p_library_id    BIGINT,
  p_after_sort_key BIGINT DEFAULT NULL,
  p_after_id      BIGINT DEFAULT NULL,
  p_page_size     INT DEFAULT 200
)
RETURNS TABLE (
  id              BIGINT,
  content         TEXT,
  metadata        JSONB,
  sort_key        BIGINT,
  next_after_sort_key BIGINT,
  next_after_id   BIGINT,
  returned_count  INT
)
LANGUAGE plpgsql AS $$
DECLARE
  row_count INT;
BEGIN
  RETURN QUERY
  WITH page AS (
    SELECT
      c.id,
      COALESCE(c.abstract, '') AS content,
      jsonb_build_object(
        'title', c.title,
        'authors', c.authors,
        'year', c.year,
        'doi', c.doi,
        'citation_key', c.citation_key,
        'verification_status', c.verification_status,
        'source', c.source
      ) AS metadata,
      c.id AS sort_key
    FROM citations c
    WHERE c.library_id = p_library_id
      AND (p_after_sort_key IS NULL OR c.id > p_after_sort_key)
    ORDER BY c.id
    LIMIT p_page_size
  )
  SELECT
    page.id,
    page.content,
    page.metadata,
    page.sort_key,
    page.sort_key AS next_after_sort_key,
    page.id AS next_after_id,
    (SELECT count(*)::int FROM page) AS returned_count
  FROM page;
END;
$$;

-- ============================================================
-- FUNCTIONS: Semantic search across citations
-- ============================================================
CREATE OR REPLACE FUNCTION match_citations(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count     INT DEFAULT 10,
  p_library_id    BIGINT DEFAULT NULL
)
RETURNS TABLE (
  id              BIGINT,
  title           TEXT,
  authors         TEXT,
  abstract        TEXT,
  citation_key    TEXT,
  similarity      FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.title,
    c.authors,
    c.abstract,
    c.citation_key,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM citations c
  WHERE (p_library_id IS NULL OR c.library_id = p_library_id)
    AND c.embedding IS NOT NULL
    AND 1 - (c.embedding <=> query_embedding) > match_threshold
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================
-- FUNCTIONS: Match thematic maps (for backward compat)
-- ============================================================
CREATE OR REPLACE FUNCTION match_thematic_maps(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count     INT DEFAULT 5
)
RETURNS TABLE (
  id              BIGINT,
  mermaid_code    TEXT,
  similarity      FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.id,
    t.mermaid_code,
    1 - (t.embedding <=> query_embedding) AS similarity
  FROM thematic_maps t
  WHERE t.embedding IS NOT NULL
    AND 1 - (t.embedding <=> query_embedding) > match_threshold
  ORDER BY t.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================
-- FUNCTIONS: Library summary stats
-- ============================================================
CREATE OR REPLACE FUNCTION get_library_stats(p_library_id BIGINT)
RETURNS TABLE (
  total_citations     INT,
  verified_citations  INT,
  failed_citations    INT,
  unverified_citations INT,
  with_abstracts      INT,
  sources_breakdown   JSONB,
  open_gaps           INT,
  thematic_maps_count INT,
  perspectives_count  INT
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    (SELECT count(*)::int FROM citations WHERE library_id = p_library_id),
    (SELECT count(*)::int FROM citations WHERE library_id = p_library_id AND verification_status = 'verified'),
    (SELECT count(*)::int FROM citations WHERE library_id = p_library_id AND verification_status = 'failed'),
    (SELECT count(*)::int FROM citations WHERE library_id = p_library_id AND verification_status = 'unverified'),
    (SELECT count(*)::int FROM citations WHERE library_id = p_library_id AND abstract IS NOT NULL AND abstract != ''),
    (SELECT jsonb_object_agg(source, cnt) FROM (SELECT source, count(*)::int as cnt FROM citations WHERE library_id = p_library_id GROUP BY source) sub),
    (SELECT count(*)::int FROM research_gaps WHERE library_id = p_library_id AND status = 'open'),
    (SELECT count(*)::int FROM thematic_maps WHERE library_id = p_library_id),
    (SELECT count(*)::int FROM research_perspectives WHERE library_id = p_library_id);
END;
$$;
