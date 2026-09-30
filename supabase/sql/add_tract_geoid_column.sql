-- Add `tract_geoid` column to projects_merged_conf1 (idempotent).
--
-- This column stores the 11-digit Census Bureau tract GEOID
--   (state FIPS [2] + county FIPS [3] + tract code [6])
-- derived from each project's coordinates via spatial join against
-- public/censuscommunityresilience.geojson.
--
-- It is intentionally separate from the legacy `FIPSCODE` field in
-- the source Excel (which contains city/place codes for some rows
-- and 0 for others) so the two semantics are never mixed.
--
-- Stored as text to preserve any leading zeros.
--
-- Run this once in the Supabase SQL Editor before running:
--   npm run sync-tract-geoid

alter table public.projects_merged_conf1
  add column if not exists tract_geoid text;

create index if not exists projects_merged_conf1_tract_geoid_idx
  on public.projects_merged_conf1 (tract_geoid);
