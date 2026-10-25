# GO-002.6: the goal sandbox, built by goal_checks.ensure_image() from this file alone (an empty context) and
# named by this file's hash, so any change here is a new image name. A changed line is a change Dorian approves.
# The base: Playwright 1.64.1 on Ubuntu noble (Python 3.12, Node 24, corepack, browsers in /ms-playwright),
# pinned by digest. Added (amended 2026-10-25): PostgreSQL 16 with its contrib extensions (pg_trgm), at one
# pinned package version, on PATH, so a goal test can start its own throwaway database as the sandbox user.
# ponytail: the pin fails the build when Ubuntu retires that version; the fix is a one-line version bump.
FROM mcr.microsoft.com/playwright:v1.64.1-noble@sha256:47b510dd9230bf0b9bfc9b20102241e577ea7a99334ab4c3ca19f19770e9b8ea
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-16=16.15-0ubuntu0.24.04.1 \
 && rm -rf /var/lib/apt/lists/*
ENV PATH=/usr/lib/postgresql/16/bin:$PATH
