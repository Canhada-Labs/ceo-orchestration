---
plan_id: PLAN-EXAMPLE-ACH
title: "Launch oral history digital archive with IRB governance and community agreement"
status: draft
owner: ceo
level: L3
squad: academic-humanities
profile: core,academic-humanities
created_at: 2026-05-10
---

# Example PLAN — Oral History Digital Archive Launch

> **This is an illustrative example**, not a real plan. It shows
> how the academic-humanities squad coordinates on a digital archive
> that touches all three VETO scopes: human-subjects data and community
> consent (Dr. Nkosi), source attribution and editorial accuracy
> (Prof. Marchand), and repository metadata and licensing (Gabriel Oduya).
>
> Exemplar pattern derived from:
> `.claude/skills/domains/edtech/examples/PLAN-EXAMPLE.md`

## 1. Problem

A university humanities department is launching a publicly accessible
digital archive of 400 oral history recordings collected between 1975-1990
from indigenous communities in a specific region. The recordings have been
held in physical format in the university's special collections. Making
them accessible online raises IRB governance questions (most recordings
predate modern consent standards), community agreement requirements, and
archival metadata standards for long-term preservation.

Sources:
- Physical archive: 400 reel-to-reel recordings, 200 photographs, 50 field
  journals — all held by university special collections
- Community stakeholders: 3 indigenous community representatives with
  interest in the materials and claim to community cultural property
- Original researcher's notes: available but non-digitised

## 2. Scope

**In:**
- IRB review for use and publication of pre-1990 oral history recordings
  as research materials
- Community consultation process and community research agreement
- Digitisation and metadata creation (Dublin Core) for all 650 materials
- Persistent identifier (ARK) assignment for all records
- Public-facing repository with community-controlled access tiers

**Out:**
- Transcription of recordings (Phase 2 — separate project)
- Publication of derived scholarly articles (separate manuscript workflows)
- Digitisation of physical field journals (cost and scope constraint)

## 3. Squad assignments

| Phase | Owner | Deliverable |
|---|---|---|
| P1 — IRB and community | Dr. Amara Nkosi | IRB protocol for pre-1990 materials; community consultation plan (ACH-001) |
| P2 — Community agreement | Dr. Nkosi + Dr. Villanueva | Community research agreement; access tier definition with communities |
| P3 — Licensing audit | Gabriel Oduya | Copyright status of all 650 items; permissions from community (ACH-009) |
| P4 — Digitisation + format | Takeshi Inoue | Open format digitisation (TIFF/FLAC); conversion documentation (ACH-012) |
| P5 — Metadata creation | Gabriel Oduya + Takeshi | Dublin Core metadata for all 650 records; schema validation (ACH-011) |
| P6 — Persistent identifiers | Takeshi Inoue | ARK assigned to every record and collection (ACH-010) |
| P7 — Editorial review | Prof. Helene Marchand | Attribution standards for recordings; contributor credit policy (ACH-007) |
| P8 — Repository launch | CEO + all VETO holders | Dr. Nkosi + Gabriel + Prof. Marchand sign-off |

## 4. Risk axes and VETO holders

- **Dr. Amara Nkosi (IRB/Ethics Coordinator):** Pre-1990 recordings were
  collected under consent standards that may not satisfy modern IRB requirements
  for public digital archive use → BLOCK if IRB protocol for archival use
  has not been approved (ACH-001); BLOCK if community agreement has not been
  executed before any recordings are made publicly accessible (ACH-002).
- **Prof. Helene Marchand (Editor):** Original researchers and community
  speakers must be credited per agreed attribution policy → BLOCK if contributor
  credit and attribution policy has not been agreed with community representatives
  before launch (ACH-007).
- **Gabriel Oduya (Reference Librarian):** Each recording's licensing status
  must be determined — university ownership, community cultural property, or
  joint — before public access is granted → BLOCK if any record with
  unresolved licensing is publicly accessible (ACH-009); BLOCK if any record
  lacks metadata schema conformance or persistent identifier (ACH-010, ACH-011).

## 5. Task chains invoked

- `academic-humanities-new-research-project` — for IRB protocol and
  community agreement phases
- `academic-humanities-digital-archive-population` — for metadata, format,
  identifier, and repository launch phases
- `academic-humanities-manuscript-submission-review` — skipped for this plan
  (applies to derived publications, not the archive itself)

## 6. Acceptance

- IRB protocol approved in writing for use and public access of pre-1990
  materials (ACH-001)
- Community research agreement executed with all 3 community representatives
  before any recordings go public (ACH-002)
- Copyright/licensing status confirmed for all 650 items; community cultural
  property items restricted per community agreement (ACH-009)
- All materials in open formats (TIFF/FLAC) with documented conversion
  process (ACH-012)
- Dublin Core metadata schema validation passes with 0 non-conforming records
  (ACH-011)
- ARK persistent identifiers assigned to all records and collections (ACH-010)
- Attribution and contributor credit policy agreed with community before launch (ACH-007)
- Re-identification risk assessment completed for any materials containing
  identifiable personal information (ACH-004)

## 7. Metrics

- Archive accessibility: 100% of records findable via Dublin Core subject search
- Community engagement: quarterly review meeting with community representatives
  for the first 2 years post-launch
- **IRB compliance audit** (annual — independent review of community agreement
  adherence and access tier enforcement)

## 8. References

- `.claude/skills/domains/academic-humanities/skills/historian/SKILL.md`
- `.claude/skills/domains/academic-humanities/skills/anthropologist/SKILL.md`
- `.claude/skills/domains/academic-humanities/task-chains.yaml` — `academic-humanities-new-research-project`
- `.claude/skills/domains/academic-humanities/task-chains.yaml` — `academic-humanities-digital-archive-population`
- UNDRIP Article 31 — indigenous peoples' right to maintain, control, protect
  and develop their cultural heritage and traditional knowledge
