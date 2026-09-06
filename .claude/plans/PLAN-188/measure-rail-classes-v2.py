#!/usr/bin/env python3
# ENTRADAS: a arvore de PACOTES de rail da noite (registros rail-round-*.md e
# rail-materials-round-*.md), que fica FORA deste repo (area de scratch da
# sessao) — por isso o diretorio e PARAMETRO e a SAIDA congelada e a evidencia.
"""v2 — block-based classification of the night's rail findings (S345).

A finding BLOCK starts at a line that carries a severity tag (P0..P3, [P1], BLOCKER/BLOCKING, HIGH/MEDIUM/MINOR,
F-N1/F5-A/N1/R2-style ids) or a bullet/numbered line, and runs until the next such start or a blank line.
Class of a block = first matching rule, in this order:
  1. a PATH token in the block (same rules as v1: product / tests / docs / ceremony / instrument / other-path)
  2. keywords: ceremony (SIGN, LAND, harness, finalize, sentinel, trailer, COMMIT-MSG, baseline, materials, rail record,
     Pair-Rail, digest of materials, .asc), docs (EVIDENCE, DESIGN, STATE, claim, plan text, README, citation, prose,
     sentence, docstring-only wording), instrument (derivator, apply script, generator, gen-evidence, measure, control
     script, census cell, evidence_nav, stamp, brief, liveness, codex output), tests (test, pytest, fixture, leg, control
     arm), product (hook, install.sh, upgrade.sh, workflow, composite, gate refuses/allows, fail-open, regex, predicate,
     env var, settings, allowlist row, matcher, os.link, os.replace, cache, tariff, refusal, latch, walk, scandir)
  3. unknown.
Severity buckets: high = P0/P1/BLOCKER/BLOCKING/HIGH; low = P2/P3/MEDIUM/MINOR/none.
Prints global fractions, high-severity fractions, per-pack table, and 3 sample blocks per class for eyeballing.
"""
from __future__ import annotations
import glob
import os
import re
import sys
import time
from collections import Counter, defaultdict

# Diretorio dos pacotes de rail: `--pack-dir <dir>` ou CEO_RAIL_PACK_DIR.
# Sem ele o script RECUSA — nunca varre uma arvore adivinhada.
PK = ''
SINCE = time.mktime(time.strptime('2026-09-04 20:00', '%Y-%m-%d %H:%M'))
PATH_RE = re.compile(r'(?<![\w/])((?:\.claude|\.github|scripts|docs|SPEC|templates|materials|controls|payload|tools|raw|v5-probes)/[\w./\-]+|[\w\-]+\.(?:py|sh|md|json|txt|yml|yaml|patch|tsv))(?::\d+)?')
SEV_RE = re.compile(r'\[?\b(P0|P1|P2|P3|BLOCKER|BLOCKING|HIGH|MEDIUM|MINOR)\b\]?')
START_RE = re.compile(r'^(?:[-*+]\s|\d+[.)]\s|\[?(?:P[0-3]|F-?N?\d+[A-Za-z]?|F\d+-[A-Z]|N\d+|R\d+|M\d+|S\d+-\d+|MP\d+|G\d+|T\d+)\b)')
TEST_RE = re.compile(r'(^|/)tests?/|(^|/)test_[\w\-]+\.py$|test-ceremony')
CEREMONY_RE = re.compile(r'OWNER-[\w\-]+\.sh|finalize[\w\-]*\.sh|test-ceremony[\w\-]*\.sh|-approved\.md|COMMIT-MSG|EXPECTED-BASELINE|PROPOSED-PATCH|^materials/|/materials/|^controls/|/controls/|rail-(?:materials-|land-)?round|SENTINEL|harness|\.asc$|MEASURE\.sh|LAND\.sh|SIGN\.sh')
INSTR_RE = re.compile(r'apply-[\w\-]+\.py|gen-[\w\-]+\.py|[\w\-]*measure[\w\-]*\.py|evidence_nav|cite-check|control_[\w\-]+\.py|qr_stamp|w6-measure|rebuild-materials|re-derive|derivator|_w4b_|collect-nodeids|check-material|check-expected|controls-r\d+\.sh|payload/|raw/|v5-probes/|tools/')
DOCS_RE = re.compile(r'EVIDENCE[\w\-]*\.md|DESIGN[\w\-]*\.md|STATE\.md|BUILDER-CLAIM|REFUTER-VERDICT|\.claude/plans/[\w\-/]+\.md|ADR-\d+|^docs/|/docs/|README|CHANGELOG|\.md$')
PRODUCT_RE = re.compile(r'\.claude/hooks/[\w\-/]+\.py|\.claude/scripts/[\w\-/]+\.py|^scripts/[\w\-]+\.sh|/scripts/[\w\-]+\.sh|\.github/(?:workflows|actions)/|^SPEC/|/SPEC/|^templates/|/templates/|PROTOCOL\.md|settings[\w.]*\.json|\.claude/governance/|\.github/scripts/|team\.md|SKILL\.md|effort\.md|allowlist\.txt')

KW = [
    ('ceremony', re.compile(r'\b(SIGN|LAND|harness|finalize|sentinel|trailer|COMMIT-MSG|EXPECTED-BASELINE|baseline|materials?|rail record|Pair-Rail|\.asc|MEASURE|ceremony|cerim[oô]nia|T\d\d[a-z]?\b|V\d[a-z]?\b|P0-[a-z])\b', re.I)),
    ('docs', re.compile(r'\b(EVIDENCE|DESIGN|STATE\.md|claim|plan text|plano|README|citation|cita[çc][aã]o|prose|prosa|sentence|frase|wording|redação|redacao|section|se[çc][aã]o|§|docstring|comment|coment[aá]rio|narrative|table row|linha \d+|typed|digitad)\b', re.I)),
    ('instrument', re.compile(r'\b(derivator|derivador|apply-|generator|gerador|gen-evidence|measure|medi[çc][aã]o|control script|census cell|c[eé]lula|evidence_nav|stamp|carimb|brief|liveness|codex output|shadow|sombra|probe|sonda|--check-only|second apply|idempot)\b', re.I)),
    ('tests', re.compile(r'\b(test_|pytest|fixture|leg [A-Z]?\d|arm|assert|unittest|node-?id|xdist|deselect)\b', re.I)),
    ('product', re.compile(r'\b(hook|install\.sh|upgrade\.sh|workflow|composite|gate (?:refuses|allows|passes)|fail-?open|fail-?closed|regex|predicate|predicado|env var|environment variable|settings|allowlist row|matcher|os\.link|os\.replace|cache|tariff|tarifa|refusal|recusa|latch|walk|scandir|symlink|manifest|deepen|checkout|PROTOCOL_SOURCE|pointer|ponteiro|quota|resets_at|marker|marcador|budget|beta header|thinking|effort|adapter|adaptador|scan|scanner|_mask_hidden|fence|CommonMark)\b', re.I)),
]
HIGH = {'P0', 'P1', 'BLOCKER', 'BLOCKING', 'HIGH'}


def classify_path(path: str) -> str:
    p = path.strip()
    if TEST_RE.search(p) and not CEREMONY_RE.search(p):
        return 'tests'
    if CEREMONY_RE.search(p):
        return 'ceremony'
    if INSTR_RE.search(p):
        return 'instrument'
    if PRODUCT_RE.search(p):
        return 'product'
    if DOCS_RE.search(p):
        return 'docs'
    return 'other-path'


def classify_block(block: str):
    m = PATH_RE.search(block)
    if m:
        c = classify_path(m.group(1))
        if c != 'other-path':
            return c, 'path:' + m.group(1)
    for name, rx in KW:
        if rx.search(block):
            return name, 'kw'
    if m:
        return 'other-path', 'path:' + m.group(1)
    return 'unknown', ''


def blocks(text: str):
    cur = []
    for line in text.splitlines():
        s = line.rstrip()
        st = s.strip()
        if not st:
            if cur:
                yield '\n'.join(cur); cur = []
            continue
        if st.startswith('#') or st.startswith('Rail-Verdict') or st.startswith('---'):
            if cur:
                yield '\n'.join(cur); cur = []
            continue
        if START_RE.match(st) or SEV_RE.search(st) and not cur:
            if cur:
                yield '\n'.join(cur)
            cur = [st]
        elif cur:
            cur.append(st)
    if cur:
        yield '\n'.join(cur)


def _resolve_pack_dir(argv) -> str:
    d = ''
    for i, a in enumerate(argv):
        if a == '--pack-dir' and i + 1 < len(argv):
            d = argv[i + 1]
        elif a.startswith('--pack-dir='):
            d = a.split('=', 1)[1]
    d = d or os.environ.get('CEO_RAIL_PACK_DIR', '')
    if not d or not os.path.isdir(d):
        raise SystemExit('REFUSE: pass --pack-dir <dir> (or CEO_RAIL_PACK_DIR); got %r' % (d,))
    return os.path.abspath(d)


def main(argv=None) -> int:
    global PK
    PK = _resolve_pack_dir(list(argv if argv is not None else sys.argv[1:]))
    files = []
    for pat in ('*/rail-round-*.md', '*/rail-materials-round-*.md', '*/**/rail-round-*.md', '*/**/rail-materials-round-*.md', '*/**/rail-land-round-*.md'):
        files += glob.glob(os.path.join(PK, pat), recursive=True)
    files = sorted({f for f in files if os.path.getmtime(f) >= SINCE and '/pre-cure' not in f and '.pre-r' not in f})
    total = Counter(); high = Counter(); per_pack = defaultdict(Counter); how = Counter(); samples = defaultdict(list)
    nblocks = 0
    for f in files:
        pack = os.path.relpath(f, PK).split('/')[0]
        text = open(f, encoding='utf-8', errors='replace').read()
        for b in blocks(text):
            sev = SEV_RE.search(b)
            # keep only blocks that look like findings: severity tag OR a path OR an id at start
            if not (sev or PATH_RE.search(b) or re.match(r'^(F-?N?\d+|N\d+|R\d+|M\d+|S\d+-\d+|MP\d+|G\d+)', b)):
                continue
            nblocks += 1
            cls, why = classify_block(b)
            total[cls] += 1; per_pack[pack][cls] += 1; how[why.split(':')[0]] += 1
            if sev and sev.group(1) in HIGH:
                high[cls] += 1
            if len(samples[cls]) < 3:
                samples[cls].append((pack, b[:220].replace('\n', ' | ')))
    n = sum(total.values()) or 1
    print('records=%d packs=%d finding-blocks=%d (classified by: %s)' % (len(files), len(per_pack), nblocks, dict(how)))
    print()
    print('ALL findings by class:')
    for cls, c in total.most_common():
        print('  %-11s %5d  %5.1f%%' % (cls, c, 100.0 * c / n))
    nh = sum(high.values()) or 1
    print('HIGH (P0/P1/BLOCKER/HIGH) by class: total=%d' % nh)
    for cls, c in high.most_common():
        print('  %-11s %5d  %5.1f%%' % (cls, c, 100.0 * c / nh))
    print()
    print('per pack:')
    for pack in sorted(per_pack):
        t = sum(per_pack[pack].values())
        print('  %-24s %4d  %s' % (pack, t, ', '.join('%s=%d' % kv for kv in per_pack[pack].most_common())))
    print()
    print('samples:')
    for cls in ('product', 'tests', 'docs', 'ceremony', 'instrument', 'other-path', 'unknown'):
        for pack, s in samples.get(cls, []):
            print('  [%s] %s :: %s' % (cls, pack, s))
    return 0


if __name__ == '__main__':
    sys.exit(main())
