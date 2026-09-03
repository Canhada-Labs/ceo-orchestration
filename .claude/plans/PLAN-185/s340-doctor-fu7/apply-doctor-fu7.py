#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply-doctor-fu7.py — DERIVACAO do pack `doctor-fu7` (PLAN-185-FOLLOWUP, S340).

O que este pack e, e o que ele NAO e
------------------------------------
A metade FU-7 do PLAN-185-FOLLOWUP ("doctor.sh como 3o consumidor de
`_wbm_dst_refuses`") JA ESTAVA LANDADA quando este pack foi construido
(S337, commit `6160578`; medido em `b6dce78`: 7 chamadas do predicado em
`scripts/doctor.sh`, secao D do e2e com D.0..D.4, todos os ~5 sitios de
escrita no adopter pre-voados). Este pack NAO reimplementa aquilo.

Ele fecha o defeito de CLASSE que a auditoria do FU-7 encontrou ao lado:
`doctor.sh` DESCARTA registros do manifesto no ingest (traversal, path
absoluto, caractere de controle, ancestral symlinkado, digest malformado,
relpath duplicado) e o descarte e SILENCIOSO. Medido em `b6dce78` com um
registro forjado `<sha>  ../outside/victim.txt` no manifesto do adopter:
doctor imprime `OK: 535`, `Refused: 0` e sai `rc=0` — um "tudo certo" sobre
um manifesto adulterado. E a MESMA classe que `test-doctor.sh` D.10 curou em
S261 para o LEAF symlinkado ("reported, not silently dropped"), uma camada
acima; e o `uninstall.sh` ja NOMEIA a sua ("unsafe manifest path", e2e U.2)
enquanto o doctor nao nomeia nada.

Cura: todo registro descartado no ingest e (i) NOMEADO numa linha propria,
com o nome sanitizado (nao-imprimivel -> '?', capado em 160 chars) e a lista
capada em 20 entradas + contador do excedente; (ii) contado no sumario numa
linha `Dropped:` que so aparece quando ha descarte (instalacao sa mantem a
saida BYTE-IDENTICA); (iii) somado a UNRESOLVED, entao um manifesto que
doctor nao conseguiu verificar inteiro sai `rc=1` em vez de `rc=0`.

Medicao que autoriza o (iii): instalacao legitima descarta ZERO registros —
`--profile core` copy 535/535 e `--link` 349/349 (S340, arvore b6dce78).

Rail r2 (land S340, codex REJECT 1 P1 + 2 P2 — todos curados aqui): (a) o
sanitizador so rejeitava \\n \\r \\t — qualquer byte de controle e inseguro (E3
alargada + E10), com perna e2e D.7 como controle positivo (E12); (b) um manifesto
com TODOS os registros descartados saia pelo ramo de manifesto vazio ANTES do
relatorio — o ramo agora relata primeiro (E11); (c) a recusa do derivador deixava
a arvore parcialmente aplicada — `_apply` faz snapshot e rollback atomico.
Rail r3 (land S340, codex 1 P2 — curado): `[[:cntrl:]]` depende de locale (sob LC_ALL=C
so C0+DEL; um 0x9b cru passava). E13 introduz `_field_has_control_bytes` (C0/DEL, C1
como UTF-8 valido e bytes 8-bit soltos via validacao iconv), E3/E10 passam por ele e
E14 e a perna e2e D.8 (0x9b sob LC_ALL=C) como controle positivo.
Rail r4 (land S340, codex 1 P1 + 1 P2 — curados): (a) `read -r` descarta/trunca no NUL
antes de qualquer check por campo — E15 recusa o manifesto CRU com NUL antes do loop
(fail-closed, exit 2), E16 = perna e2e D.9; (b) EVIDENCE/baseline-diff/regen-baseline
descreviam a v1 — regenerados para a versao final (v4).

Uso:
    python3 apply-doctor-fu7.py --root <arvore-em-HEAD>
    python3 apply-doctor-fu7.py --root <arvore> --check-only
    python3 apply-doctor-fu7.py --list-paths

Saidas: 0 = aplicado (ou aplicavel com --check-only); 1 = recusa nomeada;
2 = erro de uso. Stdlib-only, Python >= 3.9, sem PEP 604 em runtime.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

DOCTOR_REL = "scripts/doctor.sh"
E2E_REL = "scripts/tests/test-installer-write-safety-e2e.sh"
BASELINE_REL = ".claude/scripts/data/installer-write-safety-baseline.txt"
CENSUS_REL = ".claude/scripts/check-installer-write-safety.py"

# Marcador de ja-aplicado: uma string que so existe DEPOIS deste pack.
APPLIED_MARK = "_mark_dropped"

# --------------------------------------------------------------------------
# (path, ancora EXATA, substituto, ocorrencias esperadas)
# Toda ancora e contada ANTES de qualquer escrita: uma recusa deixa a arvore
# intocada.
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # ------------------------------------------------------- E1: o coletor
    (
        DOCTOR_REL,
        'SANITIZED="$WORKDIR/manifest.sanitized"\n'
        ': > "$SANITIZED"\n'
        '_DUP_GUARD="\n'
        '"\n'
        '_INVALID="\n'
        '"\n',
        'SANITIZED="$WORKDIR/manifest.sanitized"\n'
        ': > "$SANITIZED"\n'
        '_DUP_GUARD="\n'
        '"\n'
        '_INVALID="\n'
        '"\n'
        '\n'
        '# PLAN-185-FOLLOWUP FU-7 (S340) — a record this sanitizer DROPS is a record\n'
        '# doctor never verifies, and every drop below used to be SILENT. MEASURED at\n'
        "# b6dce78: with `<sha>  ../outside/victim.txt` appended to an adopter's\n"
        '# manifest, doctor printed `OK: 535`, `Refused: 0` and exited 0 — an\n'
        '# all-clear over a manifest that had been edited. Nothing was written outside\n'
        '# (the drop is what prevents that, and e2e D.5 asserts the bytes), but the\n'
        '# REPORT is the other half of doctor\'s contract: `rc=0` means "I verified\n'
        '# this tree", and it did not. Same class test-doctor.sh D.10 cured in S261\n'
        '# one layer down (a symlinked LEAF is "reported, not silently dropped"), and\n'
        '# the class uninstall.sh already names on its side ("unsafe manifest path",\n'
        '# e2e U.2).\n'
        '#\n'
        '# A legitimate install drops NOTHING — measured S340 on this tree: 535/535\n'
        '# records survive a copy install and 349/349 survive a --link install — so a\n'
        '# non-zero count here means the manifest is malformed or crafted, which is\n'
        '# why the count is folded into UNRESOLVED (rc 1) below and not merely\n'
        '# printed. On a healthy install the output stays BYTE-IDENTICAL: both the\n'
        '# listing and the summary line are conditional on DROPPED_COUNT > 0.\n'
        'DROPPED_COUNT=0\n'
        '_DROPPED=""\n'
        '_DROP_LIST_CAP=20\n'
        '_mark_dropped() {\n'
        '  # $1 = reason (fixed text from THIS file). $2 = the MANIFEST-SUPPLIED\n'
        '  # string — never echoed raw: the unsafe class it belongs to INCLUDES\n'
        "  # control characters, and this line goes to the operator's terminal, where\n"
        "  # an escape sequence rewrites what he believes he read. Non-printable => '?'\n"
        '  # (LC_ALL=C, so the classification is byte-wise), and the name is capped so\n'
        '  # one crafted 4 KB record cannot bury the rest of the report.\n'
        '  DROPPED_COUNT=$((DROPPED_COUNT + 1))\n'
        '  [ "$DROPPED_COUNT" -le "$_DROP_LIST_CAP" ] || return 0\n'
        '  _md_safe="$( printf \'%s\' "$2" | LC_ALL=C tr -c \'[:print:]\' \'?\' | cut -c1-160 )"\n'
        '  _DROPPED="${_DROPPED}    DROPPED ($1): ${_md_safe}\n'
        '"\n'
        '}\n',
        1,
    ),
    # ------------------------------------------ E2: LINK malformado (sem alvo)
    (
        DOCTOR_REL,
        '        *) continue ;;   # malformed LINK (no target) — drop\n',
        '        *) _mark_dropped "malformed LINK record (no target)" "$rest"; continue ;;\n',
        1,
    ),
    # ----------------------------------------- E3: alvo do LINK vazio/controle
    (
        DOCTOR_REL,
        '      case "$target" in\n'
        "        ''|*[$'\\n\\r\\t']*) continue ;;\n"
        '      esac\n',
        '      if [ -z "$target" ] || _field_has_control_bytes "$target"; then\n'
        '        _mark_dropped "LINK target empty or carrying a control byte" "$rel"; continue\n'
        '      fi\n',
        1,
    ),
    # ------------------------------------- E4: LINK com relpath inseguro / dup
    (
        DOCTOR_REL,
        '      if _relpath_unsafe "$rel" link; then continue; fi\n'
        '      if _seen_before "$rel"; then _mark_invalid "$rel"; continue; fi\n',
        '      if _relpath_unsafe "$rel" link; then\n'
        '        _mark_dropped "unsafe manifest path (traversal, absolute, control character, or symlinked ancestor)" "$rel"\n'
        '        continue\n'
        '      fi\n'
        '      if _seen_before "$rel"; then\n'
        '        _mark_invalid "$rel"\n'
        '        _mark_dropped "duplicate relpath (ambiguous — every record for it is dropped)" "$rel"\n'
        '        continue\n'
        '      fi\n',
        1,
    ),
    # --------------------------------- E5: registro de arquivo (4 descartes)
    (
        DOCTOR_REL,
        '      [ "$digest" != "$line" ] || continue\n'
        '      case "$digest" in\n'
        '        *[!0-9a-f]*) continue ;;\n'
        '      esac\n'
        '      [ "${#digest}" -eq 64 ] || continue\n'
        '      if _relpath_unsafe "$rel" file; then continue; fi\n'
        '      if _seen_before "$rel"; then _mark_invalid "$rel"; continue; fi\n',
        '      if [ "$digest" = "$line" ]; then\n'
        '        _mark_dropped "malformed record (no two-space separator)" "$line"\n'
        '        continue\n'
        '      fi\n'
        '      case "$digest" in\n'
        '        *[!0-9a-f]*) _mark_dropped "malformed record (digest is not hexadecimal)" "$rel"; continue ;;\n'
        '      esac\n'
        '      if [ "${#digest}" -ne 64 ]; then\n'
        '        _mark_dropped "malformed record (digest is not 64 characters)" "$rel"\n'
        '        continue\n'
        '      fi\n'
        '      if _relpath_unsafe "$rel" file; then\n'
        '        _mark_dropped "unsafe manifest path (traversal, absolute, control character, or symlinked ancestor)" "$rel"\n'
        '        continue\n'
        '      fi\n'
        '      if _seen_before "$rel"; then\n'
        '        _mark_invalid "$rel"\n'
        '        _mark_dropped "duplicate relpath (ambiguous — every record for it is dropped)" "$rel"\n'
        '        continue\n'
        '      fi\n',
        1,
    ),
    # ------------------------- E6: 2a passada (o registro anterior do dup cai)
    (
        DOCTOR_REL,
        '    case "$_INVALID" in\n'
        '      *"\n'
        '$rel_probe\n'
        '"*) continue ;;\n'
        '    esac\n',
        '    case "$_INVALID" in\n'
        '      *"\n'
        '$rel_probe\n'
        '"*) _mark_dropped "duplicate relpath (this earlier record is dropped too)" "$rel_probe"; continue ;;\n'
        '    esac\n',
        1,
    ),
    # ---------------------------- E7: o relatorio + a dobra em UNRESOLVED
    (
        DOCTOR_REL,
        '_log "==> Verifying $( wc -l < "$SANITIZED" | tr -d \' \' ) manifest records"\n',
        '# PLAN-185-FOLLOWUP FU-7 (S340): what the sanitizer dropped is reported BEFORE\n'
        '# the verification it is missing from, and counted as unresolved — a record\n'
        '# doctor could not read is a finding, not a silence. UNRESOLVED is folded here\n'
        '# (not at the drop sites) because the counters block above initialises it.\n'
        'if [ "$DROPPED_COUNT" -gt 0 ]; then\n'
        '  _log ""\n'
        '  _log "==> Manifest records DROPPED at ingest — NOT verified below"\n'
        '  _log "    (a valid install drops none: measured 535/535 copy, 349/349 --link):"\n'
        '  printf \'%s\' "$_DROPPED"   # each entry already carries its own newline\n'
        '  if [ "$DROPPED_COUNT" -gt "$_DROP_LIST_CAP" ]; then\n'
        '    _log "    ... and $(( DROPPED_COUNT - _DROP_LIST_CAP )) more (names sanitized: non-printable shown as \'?\', truncated to 160 characters)"\n'
        '  fi\n'
        '  UNRESOLVED=$((UNRESOLVED + DROPPED_COUNT))\n'
        'fi\n'
        '_log "==> Verifying $( wc -l < "$SANITIZED" | tr -d \' \' ) manifest records"\n',
        1,
    ),
    # ------------------------------------------- E8: a linha do sumario
    (
        DOCTOR_REL,
        '_log "    Orphans:   $ORPHAN_COUNT (candidates, report-only)"\n',
        '_log "    Orphans:   $ORPHAN_COUNT (candidates, report-only)"\n'
        '# Conditional ON PURPOSE (S340): a healthy run must keep printing exactly the\n'
        '# summary it printed before this pack — the line appears only when there is\n'
        '# something to report.\n'
        'if [ "$DROPPED_COUNT" -gt 0 ]; then\n'
        '  _log "    Dropped:   $DROPPED_COUNT (unsafe or malformed manifest records — NOT verified)"\n'
        'fi\n',
        1,
    ),
    # ------------------------------------------------ E9: as pernas D.5 e D.6
    (
        E2E_REL,
        '# ---------------------------------------------------------------------------\n'
        '# U — uninstall.sh confinement (PLAN-183 §9.8 + rail r1 S337).',
        '# ---------------------------------------------------------------------------\n'
        '# D.5 — a manifest record that ESCAPES the target. uninstall.sh has had this\n'
        '# leg since S337 (U.2) because uninstall REMOVES what the manifest names;\n'
        '# doctor WRITES what it names and had no leg at all. MEASURED at b6dce78\n'
        '# (pre-cure): the ingest sanitizer drops the record, so nothing lands outside\n'
        '# — the property that matters, asserted first below — but the drop was\n'
        '# SILENT: `OK: 535`, `Refused: 0`, rc 0, i.e. a clean bill of health for a\n'
        '# manifest that had been edited. Post-cure the drop is NAMED, counted in the\n'
        '# summary, and unresolved (rc 1). Both halves are asserted, because only the\n'
        '# second one was ever red.\n'
        '# ---------------------------------------------------------------------------\n'
        'echo "==> D.5 a manifest record that escapes the target is NAMED, not silently dropped"\n'
        '_mkcase d5-traversal\n'
        '_install\n'
        'if [ "$RC" -ne 0 ]; then\n'
        '  bad "D.5 — install failed (rc=$RC, see $LOG)"\n'
        'else\n'
        '  printf \'ADOPTER FILE OUTSIDE THE TARGET\\n\' > "$OUTSIDE/victim.txt"\n'
        '  D5_BEFORE="$( shasum -a 256 < "$OUTSIDE/victim.txt" | awk \'{print $1}\' )"\n'
        '  # A digest that does NOT match the outside file: a doctor that VERIFIED this\n'
        '  # record would classify DRIFT and repair it — writing through the `../`.\n'
        "  printf '%s  ../outside/victim.txt\\n' \\\n"
        '    "$( printf \'FRAMEWORK BYTES\\n\' | shasum -a 256 | awk \'{print $1}\' )" \\\n'
        '    >> "$TARGET/.claude/.install-manifest.sha256"\n'
        '  LOG="$CASE/doctor.log"; _doctor --repair --yes-file "../outside/victim.txt"\n'
        '  D5_AFTER="$( shasum -a 256 < "$OUTSIDE/victim.txt" | awk \'{print $1}\' )"\n'
        '  [ "$D5_BEFORE" = "$D5_AFTER" ] \\\n'
        '    && ok "D.5 — the outside file is byte-identical (nothing written through the ../ record)" \\\n'
        '    || bad "D.5 — the outside file CHANGED through a ../ manifest record ($D5_BEFORE -> $D5_AFTER)"\n'
        '  grep -q "DROPPED (unsafe manifest path" "$LOG" \\\n'
        '    && ok "D.5 — the dropped record is NAMED in the run output" \\\n'
        '    || bad "D.5 — the ../ record was dropped SILENTLY (no DROPPED line in $LOG)"\n'
        '  grep -q "Dropped:   1 " "$LOG" \\\n'
        '    && ok "D.5 — the summary counts exactly one dropped record" \\\n'
        '    || bad "D.5 — no \'Dropped:   1\' summary line (see $LOG)"\n'
        '  [ "$RC" -ne 0 ] \\\n'
        '    && ok "D.5 — doctor exits non-zero (rc=$RC): an unread record is an unresolved finding" \\\n'
        '    || bad "D.5 — doctor exited 0 over a manifest it did not fully read"\n'
        'fi\n'
        '\n'
        '# ---------------------------------------------------------------------------\n'
        '# D.6 — a SYMLINKED ANCESTOR under the target (the doctor analogue of U.1).\n'
        '# With `.claude/scripts` moved out and replaced by a link, all 196 records\n'
        '# under it resolve through that link. MEASURED pre-cure: the sanitizer drops\n'
        '# every one of them (nothing is written behind the link — asserted on the\n'
        "# outside file's bytes) and doctor then reports the SURVIVORS as OK and exits\n"
        '# 0: a healthy verdict for an install whose whole scripts/ tree it never\n'
        '# looked at. Post-cure: NAMED, counted, rc 1 — and this leg is what exercises\n'
        '# the 20-entry listing cap, since 196 > 20.\n'
        '# ---------------------------------------------------------------------------\n'
        'echo "==> D.6 records behind a symlinked ancestor are NAMED, not silently unverified"\n'
        '_mkcase d6-ancestor\n'
        '_install\n'
        'D6_LEAF="$( basename "$D_REL" )"\n'
        'if [ "$RC" -ne 0 ]; then\n'
        '  bad "D.6 — install failed (rc=$RC, see $LOG)"\n'
        'elif [ ! -f "$TARGET/$D_REL" ]; then\n'
        '  bad "D.6 — $D_REL was not delivered; the leg cannot run"\n'
        'else\n'
        '  mv "$TARGET/.claude/scripts" "$OUTSIDE/scripts-jail"\n'
        '  ln -s "$OUTSIDE/scripts-jail" "$TARGET/.claude/scripts"\n'
        '  printf \'\\n# adopter edit\\n\' >> "$OUTSIDE/scripts-jail/$D6_LEAF"\n'
        '  D6_BEFORE="$( shasum -a 256 < "$OUTSIDE/scripts-jail/$D6_LEAF" | awk \'{print $1}\' )"\n'
        '  LOG="$CASE/doctor.log"; _doctor --repair --yes-file "$D_REL"\n'
        '  D6_AFTER="$( shasum -a 256 < "$OUTSIDE/scripts-jail/$D6_LEAF" | awk \'{print $1}\' )"\n'
        '  [ "$D6_BEFORE" = "$D6_AFTER" ] \\\n'
        '    && ok "D.6 — the file behind the symlinked ancestor is byte-identical" \\\n'
        '    || bad "D.6 — doctor wrote THROUGH the symlinked ancestor ($D6_BEFORE -> $D6_AFTER)"\n'
        '  grep -q "DROPPED (unsafe manifest path" "$LOG" \\\n'
        '    && ok "D.6 — the records behind the symlinked ancestor are NAMED" \\\n'
        '    || bad "D.6 — a whole subtree was dropped SILENTLY (see $LOG)"\n'
        '  grep -qE "^    Dropped:   [0-9]+ " "$LOG" \\\n'
        '    && ok "D.6 — the summary carries a Dropped: count" \\\n'
        '    || bad "D.6 — no Dropped: line in the summary (see $LOG)"\n'
        '  grep -q "more (names sanitized" "$LOG" \\\n'
        '    && ok "D.6 — the listing cap is exercised (a crafted manifest cannot bury the report)" \\\n'
        '    || bad "D.6 — no cap line; expected more than 20 dropped records under .claude/scripts/"\n'
        '  [ "$RC" -ne 0 ] \\\n'
        '    && ok "D.6 — doctor exits non-zero (rc=$RC)" \\\n'
        '    || bad "D.6 — doctor exited 0 while a whole subtree went unverified"\n'
        'fi\n'
        '\n'
        '# ---------------------------------------------------------------------------\n'
        '# U — uninstall.sh confinement (PLAN-183 §9.8 + rail r1 S337).',
        1,
    ),
    # ---- rail r2 (land S340, codex REJECT: 1 P1 + 2 P2) — cures below ----
    # E10 (P1): _relpath_unsafe rejected only \n \r \t; any control byte is unsafe.
    (
        DOCTOR_REL,
        '  case "$_ru_rel" in\n'
        "    *[$'\\n\\r\\t']*) return 0 ;;\n"
        '  esac\n',
        '  if _field_has_control_bytes "$_ru_rel"; then return 0; fi\n',
        1,
    ),
    # E11 (P2): an all-dropped manifest exited before the drop report — report first.
    (
        DOCTOR_REL,
        'if [ ! -s "$SANITIZED" ]; then\n'
        '  echo "ERROR: manifest at $MANIFEST contains no valid records after sanitization." >&2\n',
        'if [ ! -s "$SANITIZED" ]; then\n'
        '  # PLAN-185-FOLLOWUP FU-7 (S340, rail r2 P2): when EVERY record was rejected the\n'
        '  # drop report further down is never reached — print it here first, so an\n'
        '  # all-dropped manifest still tells the operator what was dropped and why.\n'
        '  if [ "$DROPPED_COUNT" -gt 0 ]; then\n'
        '    _log "==> Manifest records DROPPED at ingest — every record was rejected:"\n'
        '    printf \'%s\' "$_DROPPED"\n'
        '    if [ "$DROPPED_COUNT" -gt "$_DROP_LIST_CAP" ]; then\n'
        '      _log "    ... and $(( DROPPED_COUNT - _DROP_LIST_CAP )) more (names sanitized: non-printable shown as \'?\', truncated to 160 characters)"\n'
        '    fi\n'
        '    _log "    Dropped:   $DROPPED_COUNT (unsafe or malformed manifest records — NOT verified)"\n'
        '  fi\n'
        '  echo "ERROR: manifest at $MANIFEST contains no valid records after sanitization." >&2\n',
        1,
    ),
    # E12 (P1, positive control): e2e leg D.7 — control byte in a relpath.
    (
        E2E_REL,
        '# ---------------------------------------------------------------------------\n'
        '# U — uninstall.sh confinement',
        '# ---------------------------------------------------------------------------\n'
        '# D.7 — a manifest relpath carrying a CONTROL BYTE other than \\n \\r \\t (here ESC,\n'
        '# the start of a terminal escape sequence). Rail S340 r2 (codex P1): the ingest\n'
        '# sanitizer only rejected newline/CR/tab, so such a record was ACCEPTED, then\n'
        "# classified MISSING/DRIFT and its name interpolated RAW into the operator's\n"
        '# terminal. Post-cure: rejected at ingest as unsafe (any [[:cntrl:]] byte),\n'
        "# NAMED with the byte shown as '?', and no raw ESC ever reaches the log.\n"
        '# ---------------------------------------------------------------------------\n'
        'echo "==> D.7 a manifest relpath with a control byte is DROPPED, never echoed raw"\n'
        '_mkcase d7-control-byte\n'
        '_install\n'
        'if [ "$RC" -ne 0 ]; then\n'
        '  bad "D.7 — install failed (rc=$RC, see $LOG)"\n'
        'else\n'
        '  D7_REL="$( printf \'docs/\\033[2Jevil.md\' )"\n'
        "  printf '%s  %s\\n' \\\n"
        '    "$( printf \'FRAMEWORK BYTES\\n\' | shasum -a 256 | awk \'{print $1}\' )" "$D7_REL" \\\n'
        '    >> "$TARGET/.claude/.install-manifest.sha256"\n'
        '  LOG="$CASE/doctor.log"; _doctor --repair --yes-file "docs/evil.md"\n'
        '  grep -q "DROPPED (unsafe manifest path" "$LOG" \\\n'
        '    && ok "D.7 — the control-byte record is NAMED as dropped" \\\n'
        '    || bad "D.7 — the control-byte record was NOT dropped at ingest (see $LOG)"\n'
        '  if LC_ALL=C grep -q "$( printf \'\\033\' )" "$LOG"; then\n'
        '    bad "D.7 — a RAW ESC byte reached the doctor output (terminal-control injection)"\n'
        '  else\n'
        '    ok "D.7 — no raw control byte in the doctor output"\n'
        '  fi\n'
        '  [ "$RC" -ne 0 ] \\\n'
        '    && ok "D.7 — doctor exits non-zero (rc=$RC)" \\\n'
        '    || bad "D.7 — doctor exited 0 over a manifest with a control-byte record"\n'
        'fi\n'
        '\n'
        '# ---------------------------------------------------------------------------\n'
        '# U — uninstall.sh confinement',
        1,
    ),
    # E13 (r3 P2): locale-independent control-byte predicate, shared by E3 and E10.
    (
        DOCTOR_REL,
        '_relpath_unsafe() {\n',
        '_field_has_control_bytes() {\n'
        '  # Locale-INDEPENDENT control-byte test (rail S340 r3, codex P2). Under\n'
        '  # LC_ALL=C bash matches RAW bytes, so C0 (0x00-0x1f) and DEL are caught\n'
        '  # whatever locale the operator runs doctor in; C1 controls are caught both as\n'
        '  # valid UTF-8 (U+0080-U+009F = C2 80..C2 9F) and as stray 8-bit bytes (a raw\n'
        '  # 0x9b, the 8-bit CSI, is never valid UTF-8 — any non-ASCII field is validated\n'
        "  # with iconv; no iconv ⇒ non-ASCII is refused, fail-closed). The framework's\n"
        '  # own manifests are ASCII, so on a sane install this never spawns anything.\n'
        '  local LC_ALL=C\n'
        '  case "$1" in\n'
        '    *[[:cntrl:]]*) return 0 ;;\n'
        "    *$'\\xc2'[$'\\x80'-$'\\x9f']*) return 0 ;;\n"
        "    *[$'\\x80'-$'\\xff']*)\n"
        '      [ "$_ICONV_OK" -eq 1 ] || return 0\n'
        '      printf \'%s\' "$1" | iconv -f UTF-8 -t UTF-8 >/dev/null 2>&1 || return 0\n'
        '      ;;\n'
        '  esac\n'
        '  return 1\n'
        '}\n'
        '_ICONV_OK=0\n'
        'command -v iconv >/dev/null 2>&1 && _ICONV_OK=1\n'
        '_relpath_unsafe() {\n',
        1,
    ),
    # E14 (r3 P2, positive control): e2e leg D.8 — raw 0x9b under LC_ALL=C.
    (
        E2E_REL,
        '# ---------------------------------------------------------------------------\n'
        '# U — uninstall.sh confinement',
        '# ---------------------------------------------------------------------------\n'
        '# D.8 — the same class under LC_ALL=C: a RAW 8-bit C1 byte (0x9b, the 8-bit CSI)\n'
        '# in a relpath. Rail S340 r3 (codex P2): [[:cntrl:]] is locale-dependent — under\n'
        '# C/POSIX it sees only C0+DEL, so 0x9b passed the v2 guard and reached the\n'
        '# output raw. The ingest test is now locale-independent (C1 as UTF-8, stray\n'
        '# 8-bit bytes via UTF-8 validation), so the record is dropped whatever locale\n'
        '# doctor runs in. Asserted under LC_ALL=C on purpose.\n'
        '# ---------------------------------------------------------------------------\n'
        'echo "==> D.8 a raw C1 byte in a manifest relpath is DROPPED even under LC_ALL=C"\n'
        '_mkcase d8-c1-byte\n'
        '_install\n'
        'if [ "$RC" -ne 0 ]; then\n'
        '  bad "D.8 — install failed (rc=$RC, see $LOG)"\n'
        'else\n'
        '  D8_REL="$( printf \'docs/\\233evil.md\' )"\n'
        "  printf '%s  %s\\n' \\\n"
        '    "$( printf \'FRAMEWORK BYTES\\n\' | shasum -a 256 | awk \'{print $1}\' )" "$D8_REL" \\\n'
        '    >> "$TARGET/.claude/.install-manifest.sha256"\n'
        '  LOG="$CASE/doctor.log"\n'
        '  env LC_ALL=C bash "$DOCTOR" "$TARGET" --repair --yes-file "docs/evil.md" >"$LOG" 2>&1; RC=$?\n'
        '  grep -q "DROPPED (unsafe manifest path" "$LOG" \\\n'
        '    && ok "D.8 — the raw-C1 record is NAMED as dropped under LC_ALL=C" \\\n'
        '    || bad "D.8 — the raw-C1 record was NOT dropped under LC_ALL=C (see $LOG)"\n'
        '  if LC_ALL=C grep -q "$( printf \'\\233\' )" "$LOG"; then\n'
        '    bad "D.8 — a RAW 0x9b byte reached the doctor output under LC_ALL=C"\n'
        '  else\n'
        '    ok "D.8 — no raw C1 byte in the doctor output"\n'
        '  fi\n'
        '  [ "$RC" -ne 0 ] \\\n'
        '    && ok "D.8 — doctor exits non-zero (rc=$RC)" \\\n'
        '    || bad "D.8 — doctor exited 0 over a manifest with a raw C1 record"\n'
        'fi\n'
        '\n'
        '# ---------------------------------------------------------------------------\n'
        '# U — uninstall.sh confinement',
        1,
    ),
    # E15 (r4 P1): NUL bytes are invisible to read -r — refuse the RAW manifest first.
    (
        DOCTOR_REL,
        'while IFS= read -r line || [ -n "$line" ]; do\n'
        '  [ -n "$line" ] || continue\n'
        '  case "$line" in\n'
        "    '#'*) continue ;;\n",
        '# PLAN-185-FOLLOWUP FU-7 (S340, rail r4 P1): `read -r` DROPS or truncates at a\n'
        '# NUL byte before any per-field check can see it, so a record carrying 0x00 is\n'
        '# not sanitizable line by line — it is unparseable security input and fails\n'
        '# CLOSED here, on the RAW bytes, before the line loop (same exit class as an\n'
        '# empty/corrupted manifest). Counted with tr on the raw file: locale-independent.\n'
        '_nul_count="$( LC_ALL=C tr -cd \'\\000\' < "$MANIFEST" | wc -c | tr -d \' \' )"\n'
        'if [ "${_nul_count:-0}" -gt 0 ]; then\n'
        '  echo "ERROR: manifest at $MANIFEST carries $_nul_count NUL byte(s) — unparseable (corrupted or tampered); refusing to verify." >&2\n'
        '  echo "       Run upgrade.sh to regenerate the baseline." >&2\n'
        '  exit 2\n'
        'fi\n'
        '\n'
        'while IFS= read -r line || [ -n "$line" ]; do\n'
        '  [ -n "$line" ] || continue\n'
        '  case "$line" in\n'
        "    '#'*) continue ;;\n",
        1,
    ),
    # E16 (r4 P1, positive control): e2e leg D.9 — NUL inside a manifest record.
    (
        E2E_REL,
        '# ---------------------------------------------------------------------------\n'
        '# U — uninstall.sh confinement',
        '# ---------------------------------------------------------------------------\n'
        "# D.9 — a NUL byte INSIDE a manifest record. Rail S340 r4 (codex P1): bash's\n"
        '# `read -r` drops (or, on 3.2, truncates at) the NUL before any per-field check\n'
        '# runs, so `<sha>  docs/<NUL>evil.md` was parsed as a clean-looking record and\n'
        '# doctor carried on. Post-cure the RAW manifest is scanned for NUL before the\n'
        '# line loop and refused as unparseable (exit 2) — fail-closed on input.\n'
        '# ---------------------------------------------------------------------------\n'
        'echo "==> D.9 a NUL byte in the manifest is refused before parsing"\n'
        '_mkcase d9-nul\n'
        '_install\n'
        'if [ "$RC" -ne 0 ]; then\n'
        '  bad "D.9 — install failed (rc=$RC, see $LOG)"\n'
        'else\n'
        "  printf '%s  docs/\\000evil.md\\n' \\\n"
        '    "$( printf \'FRAMEWORK BYTES\\n\' | shasum -a 256 | awk \'{print $1}\' )" \\\n'
        '    >> "$TARGET/.claude/.install-manifest.sha256"\n'
        '  D9_NULS="$( LC_ALL=C tr -cd \'\\000\' < "$TARGET/.claude/.install-manifest.sha256" | wc -c | tr -d \' \' )"\n'
        '  [ "$D9_NULS" -eq 1 ] \\\n'
        '    && ok "D.9 — the crafted manifest carries exactly one NUL byte (fixture sane)" \\\n'
        '    || bad "D.9 — fixture broken: $D9_NULS NUL byte(s) in the manifest"\n'
        '  LOG="$CASE/doctor.log"; _doctor --repair --yes-file "docs/evil.md"\n'
        '  grep -q "NUL byte" "$LOG" \\\n'
        '    && ok "D.9 — doctor refuses the manifest and NAMES the NUL byte" \\\n'
        '    || bad "D.9 — no NUL refusal: the record was parsed around the NUL (see $LOG)"\n'
        '  [ "$RC" -ne 0 ] \\\n'
        '    && ok "D.9 — doctor exits non-zero (rc=$RC)" \\\n'
        '    || bad "D.9 — doctor exited 0 over a manifest carrying a NUL byte"\n'
        'fi\n'
        '\n'
        '# ---------------------------------------------------------------------------\n'
        '# U — uninstall.sh confinement',
        1,
    ),
]

TOUCHED: List[str] = []
for _rel, _o, _n, _c in EDITS:
    if _rel not in TOUCHED:
        TOUCHED.append(_rel)
# O baseline do censo NAO e editado por ancora: ele e REGERADO pela propria
# ferramenta (regra do plano-pai: toda wave que toca `scripts/` regenera o
# baseline no MESMO patch). Ele entra em TOUCHED porque o land precisa dele no
# escopo — mas nunca e escrito a mao.
TOUCHED.append(BASELINE_REL)


class Refuse(Exception):
    pass


# Rail r3 (S340): os DOIS write-candidates que o predicado E13 acrescenta — ambos
# redirecionamentos para /dev/null, nenhum escreve no adopter. Identificados pelo
# hash de conteudo que o censo imprime (estavel sob renumeracao).
DECLARED_NEW_SITES: Set[str] = {
    "47ab7820643a26c6",   # printf '%s' "$1" | iconv -f UTF-8 -t UTF-8 >/dev/null 2>&1 || return 0
    "8720061f6e06825a",   # command -v iconv >/dev/null 2>&1 && _ICONV_OK=1
}


def _site_hash(site: str) -> str:
    """Ultimo campo ':'-separado de uma entrada do censo (hash de conteudo)."""
    return site.rsplit(":", 1)[-1]


def _census_site_set(text: str) -> Set[str]:
    """As entradas do baseline SEM o numero de linha.

    O checker casa por (path, kind, digest) — o numero de linha e informativo.
    Comparar o CONJUNTO sem ele responde a pergunta que importa aqui: este pack
    criou (ou matou) algum sitio de escrita? Se sim, a regeneracao esconderia
    a mudanca dentro de 291 linhas de renumeracao, e o pack deve RECUSAR.
    """
    out: Set[str] = set()
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) < 3:
            out.add(line)
            continue
        parts[1] = "LINE"
        out.add(":".join(parts))
    return out


def _plan(root: Path) -> None:
    problems: List[str] = []
    for rel in TOUCHED + [CENSUS_REL]:
        p = root / rel
        if not p.is_file():
            problems.append("%s: ausente" % rel)
    if problems:
        raise Refuse("\n".join("  - " + x for x in problems))

    # Ja aplicado? O marcador so existe DEPOIS deste pack.
    doc = (root / DOCTOR_REL).read_text(encoding="utf-8")
    if APPLIED_MARK in doc:
        problems.append("%s: ja contem '%s' — arvore ja patchada?"
                        % (DOCTOR_REL, APPLIED_MARK))
    e2e = (root / E2E_REL).read_text(encoding="utf-8")
    if "D.5 a manifest record that escapes" in e2e:
        problems.append("%s: ja contem a perna D.5 — arvore ja patchada?" % E2E_REL)

    # Cada ancora, contada no texto ORIGINAL (as edicoes deste pack sao
    # disjuntas: nenhuma reescreve o texto que outra ancora).
    cache = {}
    for rel, old, new, count in EDITS:
        if rel not in cache:
            cache[rel] = (root / rel).read_text(encoding="utf-8")
        found = cache[rel].count(old)
        if found != count:
            head = old.splitlines()[0][:70] if old.splitlines() else ""
            problems.append("%s: ancora '%s...' ocorre %d vez(es), esperado %d"
                            % (rel, head, found, count))
    if problems:
        raise Refuse("\n".join("  - " + x for x in problems))


def _apply(root: Path) -> List[str]:
    """Apply every edit, then regenerate the census baseline — ATOMICALLY.

    Rail r2 (land S340, codex P2): the refusal paths below used to run only
    after every edit had been written, so a REFUSED run left the tree partially
    applied. Every file is snapshotted before its first write and restored on
    ANY failure; a refusal now leaves the tree byte-identical to the input.
    """
    written: List[str] = []
    originals: Dict[str, str] = {}

    def _snap(rel: str) -> None:
        if rel not in originals:
            originals[rel] = (root / rel).read_text(encoding="utf-8")

    def _rollback() -> None:
        for rel, text in originals.items():
            (root / rel).write_text(text, encoding="utf-8")

    try:
        for rel, old, new, count in EDITS:
            _snap(rel)
            p = root / rel
            text = p.read_text(encoding="utf-8")
            if text.count(old) != count:
                raise Refuse("%s: ancora deixou de bater durante a aplicacao "
                             "(edicoes nao-disjuntas?)" % rel)
            p.write_text(text.replace(old, new, count), encoding="utf-8")
            if rel not in written:
                written.append(rel)

        # ------------------------------------------------------------ baseline
        # Regra do plano-pai (PLAN-185): toda wave que toca `scripts/` regenera o
        # baseline do censo NO MESMO PATCH — e SEMPRE pela ferramenta, nunca a mao.
        # As edicoes acima inserem linhas em `scripts/doctor.sh`, entao as entradas
        # renumeram; o CONJUNTO de sitios tem de ficar identico, e um pack que
        # criasse um sitio de escrita novo teria de dize-lo em vez de escondê-lo na
        # renumeracao. Snapshot -> regenerar -> comparar sem o numero de linha ->
        # RECUSAR (com rollback) se o conjunto mudou.
        _snap(BASELINE_REL)
        bl = root / BASELINE_REL
        before = _census_site_set(originals[BASELINE_REL])
        proc = subprocess.run(
            [sys.executable, str(root / CENSUS_REL),
             "--repo-root", str(root), "--write-baseline"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if proc.returncode != 0:
            raise Refuse("%s --write-baseline saiu %d:\n%s"
                         % (CENSUS_REL, proc.returncode,
                            proc.stdout.decode("utf-8", "replace")[-2000:]))
        after = _census_site_set(bl.read_text(encoding="utf-8"))
        # Rail r3 (S340): o predicado `_field_has_control_bytes` (E13) traz DOIS
        # redirecionamentos `>/dev/null` (a validacao UTF-8 por iconv e a sonda
        # `command -v iconv`) que o censo lista como write-candidate
        # "indeterminado". Nao escrevem no adopter — mas a regra do plano-pai e
        # DIZER, nunca esconder: os dois sitios sao declarados aqui pelo hash de
        # conteudo, tem de aparecer no baseline regenerado, e QUALQUER outro
        # ganho ou perda continua a recusar (com rollback).
        declared_present = {x for x in after if _site_hash(x) in DECLARED_NEW_SITES}
        if len(declared_present) != len(DECLARED_NEW_SITES):
            raise Refuse("sitios declarados ausentes do baseline regenerado: %s"
                         % sorted(DECLARED_NEW_SITES - {_site_hash(x) for x in declared_present}))
        if before != (after - declared_present):
            gained = sorted((after - declared_present) - before)
            lost = sorted(before - after)
            raise Refuse(
                "o censo MUDOU de conjunto (nao so renumerou) — este pack nao pode "
                "criar nem matar sitio de escrita alem dos DECLARADOS:\n"
                + "\n".join(["  + " + x for x in gained[:10]]
                            + ["  - " + x for x in lost[:10]]))
        written.append(BASELINE_REL)
        return written
    except BaseException:
        _rollback()
        raise


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="arvore em HEAD a patchar")
    ap.add_argument("--check-only", action="store_true",
                    help="so verifica as ancoras; nao escreve nada")
    ap.add_argument("--list-paths", action="store_true",
                    help="imprime os paths tocados (um por linha) e sai")
    args = ap.parse_args(argv)
    if args.list_paths:
        for rel in TOUCHED:
            print(rel)
        return 0
    if not args.root:
        ap.error("--root e obrigatorio (exceto com --list-paths)")
    root = Path(args.root).resolve()
    if not (root / ".claude").is_dir() or not (root / "scripts").is_dir():
        sys.stderr.write("apply-doctor-fu7: --root nao parece um checkout: %s\n" % root)
        return 2
    try:
        _plan(root)
        if args.check_only:
            print("apply-doctor-fu7: %d edicao(oes) aplicaveis em %d path(s); nada escrito"
                  % (len(EDITS), len(TOUCHED)))
            return 0
        written = _apply(root)
    except Refuse as exc:
        sys.stderr.write("apply-doctor-fu7: RECUSADO\n%s\n" % exc)
        return 1
    print("apply-doctor-fu7: %d edicao(oes) aplicadas em %d path(s):"
          % (len(EDITS), len(written)))
    for rel in written:
        print("  " + rel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
