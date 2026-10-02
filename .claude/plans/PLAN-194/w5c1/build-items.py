#!/usr/bin/env python3
"""build-items.py — instrumento v2 da W5c.1 (PLAN-194): re-teste pago do Sonnet 5.5.

O lado Python INTEIRO do re-teste pré-registrado em ``PREREG.md`` (mesmo
diretório). O lado de orquestração é ``wf-model-ab.js``; os três arquivos têm
sha256 em ``SHA256SUMS``. Stdlib só, Python >= 3.9.

Modos (exatamente um por chamada)
---------------------------------
  --check                 SEM gasto. Reconstrói os itens duas vezes em
                          diretórios descartáveis e exige bytes idênticos
                          (determinismo) E igualdade com ``EXPECTED``; confere a
                          origem S357 quando ela está no disco; roda o autoteste
                          do executor, do cegamento e do placar contra um
                          ``claude`` FALSO (controles vermelho→verde da regra de
                          validade e das células). Saída 0 = tudo confere.
  --print-manifest        imprime os sha256 que a construção produz (é assim que
                          ``EXPECTED`` foi preenchida; não grava nada).
  --plan                  imprime o plano dos 40 ensaios (ABBA, etiquetas t01–t40).
  --build OUT             materializa ``items/<ID>/prompt.txt``, ``keys/<ID>.json``
                          e ``controls/<ID>.txt`` em OUT e RECUSA (saída 1) se
                          qualquer sha256 divergir de ``EXPECTED``.
  --trial OUT --item ID --model M --rep N --tag tNN
                          UM ensaio pago (``claude -p`` hermético). Nunca repete
                          um ensaio válido; no máximo ``MAX_ATTEMPTS`` tentativas
                          por etiqueta; teto de gasto do run inteiro.
  --blind OUT --salt S    copia as respostas válidas + o controle de cada item
                          para ``blind/<ID>/R<k>.txt`` (rótulos opacos derivados
                          do sal; nomes de modelo redigidos). Depois disso,
                          ``--trial`` recusa.
  --record-grade OUT --item ID --label Rk --found yes|partial|no --fp N --rationale T
                          grava UMA nota do avaliador cego.
  --score OUT --salt S    aplica a regra PRÉ-REGISTRADA (validade antes das
                          células) e grava ``OUT/score.json``. Saída 0 = PASS,
                          1 = FAIL, 2 = INCONCLUSIVO ou INVÁLIDO.

De onde vêm os itens
--------------------
D01–D10 são os 10 defeitos REAIS do instrumento S357 (``wf-effort-ab.js``,
sha256 ``ORIGIN_WF_SHA256``; resultado ``effort-ab.json``, sha256
``ORIGIN_JSON_SHA256``). Os arquivos de item da S357 viviam num scratchpad
que não existe mais, então os itens são RECONSTRUÍDOS aqui, de forma
determinística, a partir das receitas que o JSON de origem registra: 7 por
``git cat-file blob <pai-do-fix>:<arquivo>`` e D02, D04 e D06 pela receita
gravada (cópia staged, pós-imagem de arquivo novo dentro de um patch,
base + hunks de um patch). O recorte (≤ 220 linhas, numeração original), o
texto de propósito e a chave de correção são DADOS desta tabela — escritos
antes de qualquer gasto e pinados por sha256. A comparação da W5c.1 é
INTERNA (Sonnet 5 × Sonnet 5.5 sobre os MESMOS itens v2); os números da S357
(Opus 5.5) não são linha de base.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Constantes pré-registradas (PREREG.md §2–§5). Mudar qualquer uma muda o
# sha256 deste arquivo, e um sha diferente do SHA256SUMS INVALIDA o run.
# --------------------------------------------------------------------------
INSTRUMENT_VERSION = "w5c1-v2"
ORIGIN_JSON_DEFAULT = "~/ceo-owner-tools/s357/results/effort-ab.json"
ORIGIN_JSON_SHA256 = "b01d4e3982266d09aa17120f87c8001e19e2221521483313777fdb0219a8f101"
ORIGIN_WF_SHA256 = "c57102c33a7d66210cbf0465d3f999a01b3e39c691febb624237c51ee8449128"

CC_VERSION_REQUIRED = "2.1.287 (Claude Code)"
ARMS = ("claude-sonnet-5", "claude-sonnet-5-5")  # braço de referência, braço sob teste
EFFORT = "xhigh"
PER_TRIAL_BUDGET_USD = 2
PER_TRIAL_WALL_S = 540
MAX_ATTEMPTS = 3
RUN_BUDGET_USD = 40.0
# US$ por milhão de tokens — iguais nos dois braços (preço público do Sonnet 5 e
# do Sonnet 5.5); escrita de cache = 1,25 × a entrada (TTL de 5 min).
PRICE_PER_MTOK = {"input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 2.50}
DELTA_PP = 10            # δ de não-inferioridade, em pontos percentuais (= 2 de 20)
COST_RATIO_NUM, COST_RATIO_DEN = 6, 5   # regra de custo: 1,2× = 6/5
VOID_LIMIT = 5           # vazios por braço (de 20) a partir do qual o ensaio é INCONCLUSIVO
REPS = (1, 2)
MAX_EXCERPT_LINES = 220
SALT_RE = re.compile(r"\A[A-Za-z0-9]{16,64}\Z")
TAG_RE = re.compile(r"\At[0-9]{2}\Z")
LABEL_RE = re.compile(r"\AR[0-9]{1,2}\Z")
MODEL_NAME_RE = re.compile(r"(?i)claude[-_ ]?sonnet[-_ ]?5(?:[-_.]5)?|sonnet[-_ ]?5(?:[-_.]5)?")

REVIEW_INSTRUCTION = (
    "Review this code for correctness, robustness and security defects. List each "
    "concrete defect with the line number(s), what goes wrong, and a minimal fix. "
    "Do not list style nits."
)

# --------------------------------------------------------------------------
# Tabela dos itens. ``origin`` repete, byte a byte, os campos do JSON de
# origem que identificam o item (conferidos por ``--check`` quando o JSON
# está no disco). ``anchors``: (literal, ocorrência 1-based, deslocamento).
# --------------------------------------------------------------------------
ITEMS: List[Dict[str, Any]] = [
    {
        "id": "D01",
        "origin": {
            "fix_commit": "94a4f58949c7",
            "file": ".github/scripts/validate-pair-rail-verdict.py",
            "defect_class": "regex anchoring: unanchored closing fence ends the signed YAML body early and hides a later NO-GO (secondary: universal-newline read, parse error mapped to softenable infra exit)",
        },
        "fix_commit": "94a4f58949c7ef1ea169cc9ab1799c907a0e821b",
        "recipe": {"kind": "blob", "rev": "cd98b14f3b3f48bee9a08088e051b1e387ec0fa3",
                   "path": ".github/scripts/validate-pair-rail-verdict.py"},
        "display": "validate-pair-rail-verdict.py",
        "lang": "python",
        "purpose": ("This Python script is a release-pipeline step: it validates a signed "
                    "pair-rail verdict artifact (a Markdown file whose decision fields live in "
                    "a single fenced yaml block) and may only let a release proceed on an "
                    "authorizing decision."),
        "segments": [(85, 295)],
        "primary": [('m = re.search(r"(?m)^```yaml[ \\t]*\\n(.*?)^```", text, re.DOTALL)', 1, 0)],
        "secondary_anchors": [('return parse_verdict_text(path.read_text(encoding="utf-8"))', 1, 0)],
        "class": "regex anchoring of the closing fence",
        "defect": ("_extract_single_yaml_block closes the yaml block at the FIRST line that merely "
                   "starts with three backticks: the closer `^```` has no end anchor, so a line such "
                   "as ```not-a-closer (or ````) ends the body early. Everything after that false "
                   "closer is never parsed nor counted, so a later `verdict: NO-GO` (or a duplicated "
                   "key) inside the real block is hidden and the artifact can validate as GO."),
        "fix": "anchor the closer to a whole fence line, e.g. ^```[ \\t]*(?:\\n|\\Z).",
        "secondary": ("parse_verdict_file reads with read_text(), whose universal-newline translation "
                      "removes a CR the grammar promises to reject before the control-character "
                      "check sees it."),
        "found_if": ("the answer names the closing-fence pattern of the extractor (the regex at the "
                     "primary line) as matching any line that begins with three backticks AND says "
                     "that content after that early/false closer is ignored (hidden decision or "
                     "duplicate key)."),
        "partial_if": ("the answer flags the fence regex as fragile without the 'later content is "
                       "hidden' consequence, OR names only the secondary defect (CR / universal "
                       "newlines)."),
        "control": "negative",
        "negative_answer": (
            "1. Line 97: ACCEPTED_DECISIONS is a tuple; a frozenset would make the membership "
            "test O(1) and signal immutability.\n"
            "2. Lines 284-287: when a nested key repeats under the same parent, the later value "
            "silently overwrites the earlier one; raise on duplicate nested keys instead.\n"
        ),
    },
    {
        "id": "D02",
        "origin": {
            "fix_commit": "3a83b765d3a9",
            "file": ".claude/hooks/_lib/audit_emit.py (staged copy .claude/plans/PLAN-179/staged-w01/...; pre-fix via git show 3a83b765d3a9^:<staged path>)",
            "defect_class": "TOCTOU/symlink: predictable temp path opened with open('w') and chmod, both following a pre-planted symlink, so any writable file can be overwritten (secondary: fixed-prefix GC window starves)",
        },
        "fix_commit": "3a83b765d3a93d0d20f51b3cb09dc1fc6df04c66",
        "recipe": {"kind": "blob", "rev": "88e56dee1a3ab39d2eecfed02ddfffe0cd9bdfdc",
                   "path": ".claude/plans/PLAN-179/staged-w01/.claude/hooks/_lib/audit_emit.py"},
        "display": "audit_emit.py",
        "lang": "python",
        "purpose": ("This Python module is the audit-event library used by hooks; the excerpt is "
                    "the helper that decides whether a context-pressure event should be emitted, "
                    "keeping a small per-session marker file under the project's state directory."),
        "segments": [(8421, 8596)],
        "primary": [('"." + marker.name + "." + str(os.getpid()) + ".tmp"', 1, 0),
                    ('with open(str(tmp), "w", encoding="utf-8") as fh:', 1, 0),
                    ('os.chmod(str(tmp), 0o600)', 1, 0)],
        "secondary_anchors": [("for _e in directory.iterdir():", 1, 0)],
        "class": "TOCTOU / symlink-following write to a predictable temp path",
        "defect": ("should_emit_context_pressure re-arms the marker through a PREDICTABLE temp path "
                   "(`.<marker>.<pid>.tmp` in the shared state directory) opened with "
                   "open(tmp, 'w'), which follows a pre-planted symlink and truncates/writes its "
                   "target: an arbitrary-file-write primitive. The separate os.chmod afterwards "
                   "also follows the link and leaves a window with default permissions."),
        "fix": ("create the temp with os.open(O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW, 0o600) and a "
                "random suffix (or tempfile.mkstemp in that directory), write through the fd, "
                "unlink it on failure, then os.replace."),
        "secondary": ("_gc_context_pressure_markers always scans the same first _scan_cap "
                      "directory entries, so expired markers behind that prefix are never "
                      "reclaimed (starvation)."),
        "found_if": ("the answer identifies that the temp/marker write follows a symlink at a "
                     "predictable path (TOCTOU, symlink attack, arbitrary file overwrite) at the "
                     "temp-path / open lines."),
        "partial_if": ("the answer mentions only the chmod-after-create permission window, or a "
                       "generic race on the temp file without symlink-following / overwrite, OR "
                       "names only the secondary defect (GC starvation)."),
        "control": "positive",
    },
    {
        "id": "D03",
        "origin": {
            "fix_commit": "cc0023517aee",
            "file": "scripts/install.sh",
            "defect_class": "injection into sed program + non-atomic truncating redirect: a '/' in --github-owner leaves a 0-byte CODEOWNERS that later runs skip forever (secondary: [[ -e ]] is false for a dangling symlink, so writes land outside $TARGET)",
        },
        "fix_commit": "cc0023517aee85438ebf4236ecd3b6a667608e0f",
        "recipe": {"kind": "blob", "rev": "00f56df544d7ec7caa631c9c683aad1bc4bd9232",
                   "path": "scripts/install.sh"},
        "display": "install.sh",
        "lang": "bash",
        "purpose": ("This Bash script installs a governance framework into a target repository; "
                    "the excerpt shows the option parsing for --github-owner and the step that "
                    "renders .github/CODEOWNERS from a template."),
        "segments": [(1, 30), (209, 209), (476, 479), (1601, 1670)],
        "primary": [('GITHUB_OWNER="${2:-}"; shift 2 ;;', 1, 0),
                    ('sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g" "$codeowners_src" > "$dst"', 1, 0)],
        "secondary_anchors": [('elif [[ -e "$dst" ]]; then', 1, 0)],
        "class": "injection into a sed program + non-atomic truncating redirect",
        "defect": ("--github-owner is stored verbatim and interpolated into the sed program "
                   "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g. A handle containing '/' (or '&', '\\', "
                   "a newline) breaks or alters the substitution. The shell has already opened "
                   "> \"$dst\", so the destination is created/truncated before sed fails; under "
                   "set -euo pipefail the run aborts and leaves a 0-byte .github/CODEOWNERS that "
                   "every later run skips forever because [[ -e \"$dst\" ]] is now true."),
        "fix": ("validate the handle against the GitHub handle grammar (and/or escape it for "
                "sed); render to a temp file in the same directory and mv it into place only on "
                "success."),
        "secondary": ("[[ -e \"$dst\" ]] is false for a dangling symlink, so the redirect follows "
                      "the link and writes outside $TARGET."),
        "found_if": ("the answer identifies that the unvalidated/unescaped --github-owner value is "
                     "injected into the sed s-command (a '/', '&' or '\\' in the handle breaks or "
                     "changes the substitution)."),
        "partial_if": ("the answer names only the non-atomic truncating redirect / empty-file "
                       "outcome without the sed injection, OR only the dangling-symlink write, OR "
                       "a generic 'validate input' without naming the sed program."),
        "control": "negative",
        "negative_answer": (
            "1. Line 1644: the SUBSTITUTED message does not say which template version was "
            "rendered; include the source path so operators can audit the install.\n"
            "2. Line 1642: `mkdir -p \"$TARGET/.github\"` has its exit status ignored; check it "
            "explicitly instead of relying on set -e.\n"
        ),
    },
    {
        "id": "D04",
        "origin": {
            "fix_commit": "185057060286",
            "file": ".claude/hooks/_lib/launch_ledger.py (patch v4: new-file post-image inside git show 62ad94c7bfa4:.claude/plans/PLAN-190/w1/p190-w1.patch)",
            "defect_class": "fail-open validation: a non-finite or future created_epoch passes the TTL comparison, so a force token never expires (secondary: malformed token returns before unlink or record)",
        },
        "fix_commit": "185057060286246e1e1e040ba2122e136991082e",
        "recipe": {"kind": "patch_newfile", "rev": "62ad94c7bfa43805cce66e9c13eb35dcfa59161f",
                   "patch": ".claude/plans/PLAN-190/w1/p190-w1.patch",
                   "target": ".claude/hooks/_lib/launch_ledger.py"},
        "display": "launch_ledger.py",
        "lang": "python",
        "purpose": ("This Python module records every Workflow launch in an on-disk ledger and "
                    "guards resumed runs; an operator can write a one-shot override token that "
                    "releases a blocked resume."),
        "segments": [(87, 94), (408, 449), (559, 615)],
        "primary": [('if t - float(data["created_epoch"]) > FORCE_TOKEN_TTL_S:', 1, 0),
                    ('if not isinstance(data, dict) or not isinstance(data.get("created_epoch"), (int, float)):', 1, 0)],
        "secondary_anchors": [('data = json.loads(p.read_text(encoding="utf-8"))', 1, 0)],
        "class": "fail-open validation of a timestamp (non-finite / future epoch)",
        "defect": ("consume_force_token only checks that created_epoch is an int/float and then "
                   "tests now - created_epoch > TTL. json.loads accepts NaN, Infinity and 1e999 "
                   "(-> inf): with NaN the comparison is always False, and with a future or "
                   "infinite epoch the age is negative, so such a token never expires and can "
                   "release a blocked resume at any later time."),
        "fix": ("require math.isfinite(epoch) and 0 <= now - epoch <= TTL (reject future "
                "timestamps); treat anything else as expired/unreadable."),
        "secondary": ("a token that fails to parse returns None before p.unlink() and without an "
                      "index record, so a garbled token is neither removed nor recorded."),
        "found_if": ("the answer identifies that a NaN / infinite / future created_epoch passes the "
                     "TTL check so the token never expires (any of these values, with the "
                     "never-expires consequence)."),
        "partial_if": ("the answer says the epoch is weakly validated (e.g. bool accepted, no "
                       "range check) without the never-expires bypass, OR names only the "
                       "secondary defect (unparseable token not unlinked/recorded)."),
        "control": "positive",
    },
    {
        "id": "D05",
        "origin": {
            "fix_commit": "478703208efe",
            "file": ".claude/scripts/ceo-launches.py",
            "defect_class": "silent truncation: the return value of a single os.write is ignored, so a short write reports success and a write error leaves the partial O_EXCL file with no cleanup",
        },
        "fix_commit": "478703208efe42b050304979e39f448a9f94e1da",
        "recipe": {"kind": "blob", "rev": "38eb917c63f985415bd90c93b4ecc1aac8f0f135",
                   "path": ".claude/scripts/ceo-launches.py"},
        "display": "ceo-launches.py",
        "lang": "python",
        "purpose": ("This Python CLI reads and reuses a Workflow launch ledger; `relaunch --out "
                    "FILE` copies the recorded script snapshot to a new file that an operator "
                    "then passes back as the script to run."),
        "segments": [(1, 30), (100, 183)],
        "primary": [("        os.write(fd, data)", 1, 0)],
        "secondary_anchors": [],
        "class": "silent truncation (short write ignored)",
        "defect": ("_write_new_file calls os.write(fd, data) once and ignores its return value. "
                   "os.write may write fewer bytes than requested, so a truncated copy of the "
                   "snapshot is reported as success ('snapshot copied to ...'); and if os.write "
                   "raises after O_EXCL created the file, the partial file is left on disk with "
                   "no cleanup."),
        "fix": ("loop until every byte is written (or write through os.fdopen(fd, 'wb')), check "
                "close(), and unlink the file this call created on any failure."),
        "secondary": "",
        "found_if": ("the answer identifies that the os.write return value (short write) is "
                     "ignored, so an incomplete file can be reported as a successful copy."),
        "partial_if": ("the answer names only the missing cleanup of the partial file on an "
                       "exception, without the short-write mechanism."),
        "control": "negative",
        "negative_answer": (
            "1. Line 155: cmd_relaunch prints the snapshot path before it knows whether "
            "--out can be written; print errors first so the output is not misleading.\n"
            "2. Line 112: the O_EXCL open should also pass O_CLOEXEC so the descriptor is not "
            "inherited by child processes.\n"
        ),
    },
    {
        "id": "D06",
        "origin": {
            "fix_commit": "3c155edfb69c",
            "file": "scripts/install.sh (wave-C shadow: git archive b0e992f3b6df scripts/install.sh, then git apply of the install.sh hunks from git show 6f9fafbf779a:.claude/plans/PLAN-185/s329-ceremony-C/C.patch; line 780 matches the record; cure landed in cc0023517aee)",
            "defect_class": "env leakage: _ATOMIC_TMP_PENDING is never initialized before the EXIT trap, so an inherited value makes the trap rm -f an arbitrary file, even under --dry-run",
        },
        "fix_commit": "3c155edfb69cba4d60b96ca7125c8da142267812",
        "recipe": {"kind": "blob_plus_patch",
                   "rev": "b0e992f3b6df478eacbce2afc2641153a934e9c0", "path": "scripts/install.sh",
                   "patch_rev": "6f9fafbf779a52cb7831c8355fb7ac01a5a4e6d9",
                   "patch": ".claude/plans/PLAN-185/s329-ceremony-C/C.patch",
                   "target": "scripts/install.sh"},
        "display": "install.sh",
        "lang": "bash",
        "purpose": ("This Bash script installs a governance framework into a target repository "
                    "with rollback on failure; the excerpt shows its global variable setup, the "
                    "EXIT trap handler and an atomic-write helper."),
        "segments": [(359, 384), (739, 803), (1925, 1966)],
        "primary": [('if [[ -n "${_ATOMIC_TMP_PENDING:-}" ]]; then rm -f "$_ATOMIC_TMP_PENDING" 2>/dev/null || true; fi', 1, 0)],
        "secondary_anchors": [("trap cleanup_on_failure EXIT", 2, 0)],
        "class": "environment leakage into an EXIT trap (uninitialized global)",
        "defect": ("_ATOMIC_TMP_PENDING is never initialized at startup (unlike the other globals, "
                   "e.g. _CREATED_LINK_RELPATHS), but the EXIT trap cleanup_on_failure runs "
                   "rm -f \"$_ATOMIC_TMP_PENDING\" whenever it is non-empty. A value inherited "
                   "from the caller's environment therefore makes every exit, including --dry-run "
                   "and a successful install, delete an arbitrary file named by that variable."),
        "fix": ("initialize _ATOMIC_TMP_PENDING=\"\" with the other globals before the trap is "
                "installed, so the trap can only remove a path this run staged."),
        "secondary": "",
        "found_if": ("the answer identifies that _ATOMIC_TMP_PENDING can come from the inherited "
                     "environment (it is never initialized) and the EXIT trap then deletes that "
                     "arbitrary path."),
        "partial_if": ("the answer says the trap deletes a path without verifying it was staged by "
                       "this run, without naming the inherited/uninitialized variable."),
        "control": "positive",
    },
    {
        "id": "D07",
        "origin": {
            "fix_commit": "cd1cec1c022c",
            "file": "scripts/_framework_manifest_set.sh",
            "defect_class": "early return skips a fail-closed check: freshly creating .claude/.gitignore bypasses tracked-sensitive-file detection (secondary: head under callers' pipefail -> SIGPIPE 141 aborts the run)",
        },
        "fix_commit": "cd1cec1c022cd78b914892f123967fcdf171a98b",
        "recipe": {"kind": "blob", "rev": "94a4f58949c7ef1ea169cc9ab1799c907a0e821b",
                   "path": "scripts/_framework_manifest_set.sh"},
        "display": "_framework_manifest_set.sh",
        "lang": "bash",
        "purpose": ("This Bash library is sourced by an installer and an upgrader; the excerpt "
                    "makes sure per-machine state and a local permission overlay inside .claude/ "
                    "are excluded from version control."),
        "segments": [(1, 12), (855, 1021)],
        "primary": [('echo "    CREATED: .claude/.gitignore"', 1, 1)],
        "secondary_anchors": [('| head -5 )"', 1, 0)],
        "class": "early return skips a fail-closed check",
        "defect": ("In _apply_claude_dir_gitignore the branch that CREATES .claude/.gitignore "
                   "returns 0 right after writing it, skipping the two "
                   "_gitignore_reassert_effective calls that the other branch runs. Those calls "
                   "are what detect sensitive paths (.claude/settings.local.json, .claude/state/) "
                   "that are ALREADY TRACKED by git, so an adopter whose overlay is already "
                   "committed gets a green install and the file stays commit-eligible."),
        "fix": ("do not return after creating the file; fall through to (or call) the "
                "effectiveness and tracked-path checks for the freshly created file."),
        "secondary": ("`git ls-files ... | head -5` under the callers' pipefail can make ls-files "
                      "die of SIGPIPE (exit 141) and abort the run before the migration message."),
        "found_if": ("the answer identifies that the creation branch returns before the "
                     "effectiveness / already-tracked checks, so tracked sensitive files are not "
                     "detected on that path."),
        "partial_if": ("the answer names only the secondary defect (head + pipefail / SIGPIPE), or "
                       "says the create branch skips 'validation' without connecting it to the "
                       "tracked-file / effectiveness check."),
        "control": "negative",
        "negative_answer": (
            "1. Lines 941-962: _claude_dir_gitignore_body passes many arguments to printf; a "
            "heredoc would be easier to maintain and review.\n"
            "2. Lines 897-903: every re-assertion appends another comment block, so repeated "
            "runs keep growing the .gitignore file.\n"
        ),
    },
    {
        "id": "D08",
        "origin": {
            "fix_commit": "43bb12688d49",
            "file": ".claude/hooks/check_canonical_edit.py",
            "defect_class": "first-match instead of all-match: the multi-path gate breaks at the first canonical candidate and decides once, so later ungranted canonical paths pass (secondary: CWD-vs-repo_root relative-path fail-open; except->allow in decide())",
        },
        "fix_commit": "43bb12688d495d458dc6431354c6ce55aacbd9fe",
        "recipe": {"kind": "blob", "rev": "8c7877aa581a69f274b6debce23f415cdb410254",
                   "path": ".claude/hooks/check_canonical_edit.py"},
        "display": "check_canonical_edit.py",
        "lang": "python",
        "purpose": ("This Python PreToolUse hook blocks edits to canonical governance paths unless "
                    "an Owner-signed sentinel grants them; a single tool call may carry several "
                    "candidate paths."),
        "segments": [(1, 10), (683, 703), (1119, 1161), (1291, 1406)],
        "primary": [("if _is_canonical(candidate, repo_root):", 1, 0),
                    ("                    break", 1, 0)],
        "secondary_anchors": [("return _emit_allow()", 3, 0)],
        "class": "first-match instead of all-match",
        "defect": ("In main() the multi-candidate scan breaks at the FIRST canonical candidate and "
                   "decide() is then called once, for that single path. If an event carries "
                   "several canonical paths and the sentinel grants only the first one, the "
                   "later ungranted canonical paths are never checked and the edit is allowed."),
        "fix": ("check every candidate: block if ANY canonical candidate lacks a granting "
                "sentinel (most-restrictive-wins), and fail closed if the scan errors."),
        "secondary": ("decide() returns allow when the repo-relative resolve of a confirmed "
                      "canonical path raises; _is_canonical resolves a relative path only against "
                      "the process CWD; an exception in _is_canonical is swallowed by `continue`."),
        "found_if": ("the answer identifies that only the first canonical candidate is gated "
                     "(break on first match), so other canonical paths in the same call bypass "
                     "the sentinel check."),
        "partial_if": ("the answer names only the fail-open branches (except -> allow, swallowed "
                       "exception) or the CWD-relative resolution, without the first-match "
                       "bypass."),
        "control": "positive",
    },
    {
        "id": "D09",
        "origin": {
            "fix_commit": "9af6114f78a3",
            "file": ".claude/scripts/persona_demand_scan.py",
            "defect_class": "silent misparse of an external-tool argument: git approxidate drops '--since=168h', the window collapses to now, and git exits 0 (checked in a scratch repo with git 2.54.0: 0 of 3 commits returned)",
        },
        "fix_commit": "9af6114f78a3d48605c108c0ae952b501f8afc2b",
        "recipe": {"kind": "blob", "rev": "843eb5777513b6880d342ada82becc996093690a",
                   "path": ".claude/scripts/persona_demand_scan.py"},
        "display": "persona_demand_scan.py",
        "lang": "python",
        "purpose": ("This Python script scans recent local git history (a bounded commit and time "
                    "horizon) to detect review demands and emit each of them once."),
        "segments": [(1, 24), (57, 59), (101, 109), (200, 249), (285, 323)],
        "primary": [('f"--since={hours}h",', 1, 0)],
        "secondary_anchors": [],
        "class": "silent misparse of an external-tool argument",
        "defect": ("_scan_commit_files passes --since={hours}h (i.e. --since=168h) to git log. "
                   "Git's approxidate parser does not understand a bare 'h' suffix: '168h' is "
                   "silently discarded (small values such as '2h' are read as a day of the "
                   "month), the cutoff collapses to 'now', git exits 0 with an (almost) empty "
                   "log, and the scanner silently misses demands from the intended 7-day window."),
        "fix": ("pass an absolute cutoff (ISO-8601 UTC computed as now - hours) or a form git "
                "documents, such as --since='168 hours ago'."),
        "secondary": "",
        "found_if": ("the answer identifies that '--since=168h' (the 'h' suffix) is not a duration "
                     "git understands, so the time window is wrong or empty without an error."),
        "partial_if": ("the answer flags the --since argument format as suspicious without the "
                       "silent wrong/empty-window consequence, OR names only that _git swallows "
                       "git errors and returns an empty string."),
        "control": "negative",
        "negative_answer": (
            "1. Lines 226-249: the three _path_matches branches repeat the same DemandEvent "
            "construction; factor it into one helper so the branches cannot drift apart.\n"
            "2. Lines 296 and 320: CEO_PERSONA_DEMAND_LEDGER_DISABLED is read twice (in "
            "detect_all and in scan); read it once and pass the flag down.\n"
        ),
    },
    {
        "id": "D10",
        "origin": {
            "fix_commit": "cd98b14f3b3f",
            "file": ".claude/scripts/local/_release_tag_guard.py",
            "defect_class": "line-separator semantics: str.splitlines() splits on VT/FF/NEL/U+2028 etc., so 'verdict: GO<VT>#NO-GO' reads as exact GO in all three readers (secondary: an unanchored first ```yaml match lets a quoted envelope shadow the real one)",
        },
        "fix_commit": "cd98b14f3b3f48bee9a08088e051b1e387ec0fa3",
        "recipe": {"kind": "blob", "rev": "0272508d9e579f233fd453ee787c8c1012440b21",
                   "path": ".claude/scripts/local/_release_tag_guard.py"},
        "display": "_release_tag_guard.py",
        "lang": "python",
        "purpose": ("This Python helper runs fail-closed checks before a release tag is signed, "
                    "including reading the decision recorded in a signed verdict file (a "
                    "Markdown file with a fenced yaml block)."),
        "segments": [(1, 6), (96, 104), (200, 243), (269, 334), (421, 502)],
        "primary": [("for raw in block.group(1).splitlines():", 1, 0),
                    ("for raw in block.group(1).splitlines():", 2, 0)],
        "secondary_anchors": [('block = re.search(r"```yaml[ \\t]*\\n(.*?)```", text, re.DOTALL)', 1, 0)],
        "class": "line-separator semantics (str.splitlines)",
        "defect": ("The yaml block is split with str.splitlines(), which also breaks lines at "
                   "\\v, \\f, \\x1c-\\x1e, \\x85, U+2028 and U+2029. A value such as "
                   "'verdict: GO<VT>#NO-GO' is then read as the exact token GO (the remainder "
                   "becomes a comment line), while a reader that splits only on \\n sees "
                   "'GO<VT>#NO-GO'; the guard can authorise a tag whose signed decision is not GO."),
        "fix": ("split only on '\\n' and reject any control character other than tab / any line "
                "separator other than LF inside the block before parsing."),
        "secondary": ("the block is located with an unanchored re.search for ```yaml ... ```: the "
                      "first occurrence anywhere (e.g. quoted inside a four-backtick block) can "
                      "shadow the real envelope."),
        "found_if": ("the answer identifies that splitlines() splits on non-LF separators "
                     "(VT/FF/NEL/U+2028...) so a hidden separator can change the decision read "
                     "(or make the two readers disagree)."),
        "partial_if": ("the answer names only the unanchored first-match block selection, OR "
                       "says control characters are not rejected without connecting it to "
                       "splitlines()."),
        "control": "positive",
    },
]

ITEM_IDS = tuple(it["id"] for it in ITEMS)
ITEM_BY_ID = {it["id"]: it for it in ITEMS}

# sha256 que a construção TEM de produzir (preenchida por --print-manifest
# antes de qualquer gasto; PREREG.md §3 repete os valores).
EXPECTED: Dict[str, Dict[str, str]] = {
    "D01": {
        "source": "22671e953161a1ccc6a680f9d08bb2d9b00f960a85f2c112e91ae8072ea39494",
        "prompt": "c735c79c1bca8d5bcf3643b293496dbb2b0a0fff088dbafc1629629c394425e3",
        "key": "a38e06f8db5fcd878b4d9c93f4843f53b0eb422d183e3f37c6030ef33a0060ef",
        "control": "0b5935f5cf91f05f35a49fd6c068793a1f044f959776830ebe16128e9e5c2a3c",
    },
    "D02": {
        "source": "3715d1540f75906a4b4f49717553367f2001e91b03160c822afbffe883e9421c",
        "prompt": "346f5de0c045e4dd8f43e677eb12c26559cfa264e4733895ba1428e9020c02e6",
        "key": "45f0f3c9f2125c304cfcc1f0686b7e0108a95ecb02c760ee5afe483ac79a04b5",
        "control": "a0a50d2a05469cd93c77cd9493cfb2eff86490603079a463c18012bbeebe4dcb",
    },
    "D03": {
        "source": "2e405fc29e5dff33fb21e8880c8f25ce9b36e36fec5becdb39cf80e384447651",
        "prompt": "b12f671d85b99dbd9a608d1c8a213dfe6eaa7bfacd95f73d304443f4a68b4601",
        "key": "6e6c8f0f3c833c871ba9600829ccf28c778bfc6978eae926fbe87d1bda8b59b9",
        "control": "9743faabd17d96ac4c8fcc6301d75e37c62891d87784a7db84f6e4658d6b2268",
    },
    "D04": {
        "source": "2731e3a991f4748beeca328b6744827d99c101d9a63cfd189db123f0adb8f8f9",
        "prompt": "622a07ea2548b1bd9ead553e26f45d8a535338d7baadbdadf686c9830d12f714",
        "key": "70c5702f99cca38959d6d88ed02445cfbfe265b4190fbbb1c70bdeb267cc6b49",
        "control": "18a6a8057fb1eabcb145bedb2b89c053c396259a19326423cab546a397a03f11",
    },
    "D05": {
        "source": "8ef72ab914ba84198b942b2c6759df3b2d4e86b85b3bdcbbbe30e3f9774bc2e3",
        "prompt": "c352733b133c7ebea52b8d28c5bad6bc228689561de3f4491cdb7710bb168178",
        "key": "664e9d34a00d79b67abc6dc5ff5ea4d06aa6de1ec0fd6b088a6ad1c02544d888",
        "control": "618a34d379ea4aaa9247f0e50c8aa6f4d7fef962e680907bcd384e9ec986bac0",
    },
    "D06": {
        "source": "1a9c99943e90ca89093b7b5f379ab2a07b903b5d2373978b8de872a7568d8e0a",
        "prompt": "179e9041d52f0129f6e96e80071c0f70d556ea4126fb84bb20678a53bb2c8d7e",
        "key": "36ba504d407b5b4c2e53067240f1035b3367a8f70d6fda71856a8fd4f0f7616e",
        "control": "00dbc2f0153d489be74494508b24bdcbec0cacb2ad62ecd6c0bb691607320b85",
    },
    "D07": {
        "source": "b64812281fe6fd053bf719b63ec56d1695fe34700f71226f39425b8648ed72c0",
        "prompt": "0908bb5f78a21d9e71208655edb3e1c2411f9067bd728947a2d7d83a75b74b3a",
        "key": "031b9b58afce58b030a953b98d5e588b940ad13c15f1b3b946d662db3539518c",
        "control": "149c8c559712cabf613292792a1ca9898d1ebd65af78c0a6754f9a571480467d",
    },
    "D08": {
        "source": "16b86af5d5061afbf972e23891ab400177806c7831a91ec731254cf318bbd7e9",
        "prompt": "89ef9b989abc8f9f1415e5c45fb3f7d2f7d5fb87cf7bd78a9fca58b6655c7536",
        "key": "f64aa3372a98ec3ae596940d2fd469a30ce5dcdf20afdc3e8a5c8c35863cd685",
        "control": "dbc86d4f00bbe5fc0b6388ebf88b701548f19876def0c6549722528847439805",
    },
    "D09": {
        "source": "c382461d8ef845e4ba0efac9695b51f56121a4588037be08cee073682cc98474",
        "prompt": "a60320904cec9f2b5cf5531d44a91727aec06166b10384009030f320ac09e086",
        "key": "5361d97627992985b1c69c47b8263e27c313084472b6639f121816a610b62157",
        "control": "1ec96879bcdce7a1dfc2a3d7b67afc0e559f2b3ed73a6bdf8f4931087e2699a1",
    },
    "D10": {
        "source": "5b677ff583371200d81223e90ae0ad4dad1fdfd423bbe9995c3d0517e42896c1",
        "prompt": "e1ab810b3203980cd3f93db1957e733971b767b940ab73cb7695e5cf461ba2f4",
        "key": "be43dbbad4462fcdf4c5020407135bf63b880e08849193e72347e0ebf8af3bd4",
        "control": "f6c51e5ea04d949581cbda439f2aac17ea9696d9bdcbb307ac7c7c4424cc7bc1",
    },
}


class InstrumentError(Exception):
    """Falha do instrumento (recusa nomeada, nunca 'melhor esforço')."""


# ------------------------------------------------------------------ utilitários
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def instrument_sha256() -> str:
    return sha256_file(os.path.abspath(__file__))


def _atomic_write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")


def _split_lines(text: str) -> List[str]:
    """Divide SÓ em LF (nunca str.splitlines — ver o item D10)."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run(["git", "-C", here, "rev-parse", "--show-toplevel"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_git_env(), timeout=60)
    if r.returncode != 0:
        raise InstrumentError("this file is not inside a git checkout (rev-parse failed)")
    return r.stdout.decode("utf-8").strip()


def _git_env() -> Dict[str, str]:
    # Sem config de sistema/usuário: nenhum filtro, textconv ou apply.whitespace
    # pode mudar os bytes reconstruídos.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["LC_ALL"] = "C"
    return env


def _git_blob(repo: str, rev: str, path: str) -> bytes:
    r = subprocess.run(["git", "-C", repo, "cat-file", "blob", "%s:%s" % (rev, path)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_git_env(), timeout=120)
    if r.returncode != 0:
        raise InstrumentError("git cat-file blob %s:%s failed: %s"
                              % (rev, path, r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout


# ------------------------------------------------------------- reconstrução
def _patch_section(patch_text: str, target: str) -> List[str]:
    header = "diff --git a/%s b/%s" % (target, target)
    lines = patch_text.split("\n")
    starts = [i for i, line in enumerate(lines) if line == header]
    if len(starts) != 1:
        raise InstrumentError("patch: expected exactly one section for %s, found %d"
                              % (target, len(starts)))
    end = starts[0] + 1
    while end < len(lines) and not lines[end].startswith("diff --git "):
        end += 1
    sec = lines[starts[0]:end]
    while sec and sec[-1] == "":
        sec.pop()  # fim do arquivo de patch
    return sec


_HUNK_RE = re.compile(r"\A@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _hunks(sec: List[str]) -> List[Tuple[int, int, int, int, List[str]]]:
    out: List[Tuple[int, int, int, int, List[str]]] = []
    i = 0
    while i < len(sec) and not sec[i].startswith("@@ "):
        i += 1
    while i < len(sec):
        m = _HUNK_RE.match(sec[i])
        if not m:
            raise InstrumentError("patch: malformed hunk header %r" % sec[i])
        a, b = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        c, d = int(m.group(3)), int(m.group(4) if m.group(4) is not None else 1)
        j = i + 1
        body: List[str] = []
        while j < len(sec) and not sec[j].startswith("@@ "):
            body.append(sec[j])
            j += 1
        out.append((a, b, c, d, body))
        i = j
    return out


def _newfile_from_patch(patch_text: str, target: str) -> bytes:
    sec = _patch_section(patch_text, target)
    if not any(line.startswith("new file mode ") for line in sec[:4]):
        raise InstrumentError("patch: section for %s is not a new file" % target)
    hunks = _hunks(sec)
    if len(hunks) != 1 or hunks[0][0] != 0 or hunks[0][1] != 0:
        raise InstrumentError("patch: new file %s must have exactly one @@ -0,0 hunk" % target)
    _, _, _, d, body = hunks[0]
    if len(body) != d or any(not line.startswith("+") for line in body):
        raise InstrumentError("patch: new-file hunk of %s is not %d '+' lines" % (target, d))
    return ("\n".join(line[1:] for line in body) + "\n").encode("utf-8")


def _apply_section(base: bytes, patch_text: str, target: str) -> bytes:
    """Aplicação ESTRITA (sem fuzz, sem deslocamento): contexto divergente é recusa."""
    text = base.decode("utf-8")
    if not text.endswith("\n"):
        raise InstrumentError("base of %s does not end with a newline" % target)
    old = _split_lines(text)
    sec = _patch_section(patch_text, target)
    out: List[str] = []
    pos = 0
    for a, b, c, d, body in _hunks(sec):
        start = a - 1 if b > 0 else a
        if start < pos or start > len(old):
            raise InstrumentError("patch: hunk @@ -%d,%d out of order for %s" % (a, b, target))
        out.extend(old[pos:start])
        pos = start
        n_old = n_new = 0
        for line in body:
            tag, s = line[:1], line[1:]
            if tag == " ":
                if pos >= len(old) or old[pos] != s:
                    raise InstrumentError("patch: context mismatch at %s:%d" % (target, pos + 1))
                out.append(s)
                pos += 1
                n_old += 1
                n_new += 1
            elif tag == "-":
                if pos >= len(old) or old[pos] != s:
                    raise InstrumentError("patch: removal mismatch at %s:%d" % (target, pos + 1))
                pos += 1
                n_old += 1
            elif tag == "+":
                out.append(s)
                n_new += 1
            else:
                raise InstrumentError("patch: unsupported line %r in %s" % (line[:40], target))
        if n_old != b or n_new != d:
            raise InstrumentError("patch: hunk @@ -%d,%d +%d,%d counts do not match its body"
                                  % (a, b, c, d))
    out.extend(old[pos:])
    return ("\n".join(out) + "\n").encode("utf-8")


def reconstruct_source(repo: str, item: Dict[str, Any]) -> bytes:
    rc = item["recipe"]
    if rc["kind"] == "blob":
        return _git_blob(repo, rc["rev"], rc["path"])
    if rc["kind"] == "patch_newfile":
        patch = _git_blob(repo, rc["rev"], rc["patch"]).decode("utf-8")
        return _newfile_from_patch(patch, rc["target"])
    if rc["kind"] == "blob_plus_patch":
        base = _git_blob(repo, rc["rev"], rc["path"])
        patch = _git_blob(repo, rc["patch_rev"], rc["patch"]).decode("utf-8")
        return _apply_section(base, patch, rc["target"])
    raise InstrumentError("unknown recipe kind %r" % rc["kind"])


# ----------------------------------------------------------- prompt e chave
def _resolve_anchor(lines: List[str], anchor: Tuple[str, int, int], item_id: str) -> int:
    literal, occurrence, offset = anchor
    hits = [i + 1 for i, line in enumerate(lines) if literal in line]
    if len(hits) < occurrence:
        raise InstrumentError("%s: anchor %r has %d hit(s), occurrence %d requested"
                              % (item_id, literal, len(hits), occurrence))
    return hits[occurrence - 1] + offset


def _excerpt_numbers(item: Dict[str, Any], n_lines: int) -> List[int]:
    nums: List[int] = []
    prev_end = 0
    for s, e in item["segments"]:
        if not (1 <= s <= e <= n_lines) or s <= prev_end:
            raise InstrumentError("%s: bad segment (%d, %d)" % (item["id"], s, e))
        nums.extend(range(s, e + 1))
        prev_end = e
    if len(nums) > MAX_EXCERPT_LINES:
        raise InstrumentError("%s: excerpt has %d lines (> %d)"
                              % (item["id"], len(nums), MAX_EXCERPT_LINES))
    return nums


def render_prompt(item: Dict[str, Any], src: bytes) -> bytes:
    lines = _split_lines(src.decode("utf-8"))
    nums = set(_excerpt_numbers(item, len(lines)))
    body: List[str] = []
    segs = item["segments"]
    for k, (s, e) in enumerate(segs):
        if k > 0 or s > 1:
            body.append("  ...")
        for n in range(s, e + 1):
            body.append(("%5d  %s" % (n, lines[n - 1])) if lines[n - 1] else ("%5d" % n))
    if segs[-1][1] < len(lines):
        body.append("  ...")
    for anchor in item["primary"] + item["secondary_anchors"]:
        if _resolve_anchor(lines, anchor, item["id"]) not in nums:
            raise InstrumentError("%s: anchor %r falls outside the excerpt" % (item["id"], anchor[0]))
    longest = max([len(m) for line in body for m in re.findall(r"`+", line)] + [0])
    fence = "`" * max(3, longest + 1)
    text = "\n".join([
        item["purpose"],
        "",
        "Excerpt of %s (lines are numbered as in the full file; '...' marks omitted lines):"
        % item["display"],
        "",
        fence + item["lang"],
        "\n".join(body),
        fence,
        "",
        REVIEW_INSTRUCTION,
    ]) + "\n"
    return text.encode("utf-8")


def render_key(item: Dict[str, Any], src: bytes) -> bytes:
    lines = _split_lines(src.decode("utf-8"))
    primary = sorted({_resolve_anchor(lines, a, item["id"]) for a in item["primary"]})
    secondary = sorted({_resolve_anchor(lines, a, item["id"]) for a in item["secondary_anchors"]})
    key = {
        "instrument": INSTRUMENT_VERSION,
        "id": item["id"],
        "file": item["display"],
        "class": item["class"],
        "defect": item["defect"],
        "primary_lines": primary,
        "primary_line_text": [lines[n - 1].strip() for n in primary],
        "minimal_fix": item["fix"],
        "secondary_defect": item["secondary"],
        "secondary_lines": secondary,
        "found_if": item["found_if"],
        "partial_if": item["partial_if"],
        "not_found_if": "anything else; listing many unrelated issues does not earn 'found'.",
        "fix_commit": item["fix_commit"],
        "source_recipe": item["recipe"],
        "source_sha256": sha256_bytes(src),
    }
    return _json_bytes(key)


def render_control(item: Dict[str, Any], src: bytes) -> Tuple[bytes, str]:
    """Controle do avaliador: positivo = a chave na voz de um revisor; negativo =
    dois achados plausíveis que NÃO são o defeito-chave nem o secundário."""
    lines = _split_lines(src.decode("utf-8"))
    if item["control"] == "positive":
        primary = sorted({_resolve_anchor(lines, a, item["id"]) for a in item["primary"]})
        where = ", ".join(str(n) for n in primary)
        text = "1. Line(s) %s: %s Minimal fix: %s\n" % (where, item["defect"], item["fix"])
        return text.encode("utf-8"), "yes"
    return item["negative_answer"].encode("utf-8"), "no"


def build_all(repo: str, out: str) -> Dict[str, Dict[str, str]]:
    manifest: Dict[str, Dict[str, str]] = {}
    for item in ITEMS:
        src = reconstruct_source(repo, item)
        prompt = render_prompt(item, src)
        key = render_key(item, src)
        control, _ = render_control(item, src)
        _atomic_write(os.path.join(out, "items", item["id"], "prompt.txt"), prompt)
        _atomic_write(os.path.join(out, "keys", item["id"] + ".json"), key)
        _atomic_write(os.path.join(out, "controls", item["id"] + ".txt"), control)
        manifest[item["id"]] = {
            "source": sha256_bytes(src),
            "prompt": sha256_bytes(prompt),
            "key": sha256_bytes(key),
            "control": sha256_bytes(control),
        }
    return manifest


def manifest_digest(manifest: Dict[str, Dict[str, str]]) -> str:
    return sha256_bytes(json.dumps(manifest, sort_keys=True).encode("utf-8"))


def compare_expected(manifest: Dict[str, Dict[str, str]]) -> List[str]:
    problems: List[str] = []
    if set(EXPECTED) != set(ITEM_IDS):
        problems.append("EXPECTED does not cover exactly %s" % ",".join(ITEM_IDS))
    for iid in ITEM_IDS:
        for field in ("source", "prompt", "key", "control"):
            want = EXPECTED.get(iid, {}).get(field)
            got = manifest.get(iid, {}).get(field)
            if want != got:
                problems.append("%s.%s: expected %s, built %s" % (iid, field, want, got))
    return problems


# --------------------------------------------------------------------- plano
def build_plan() -> List[Dict[str, Any]]:
    """ABBA por item; o braço que abre alterna com a paridade do item (D01 abre
    com o Sonnet 5, D02 com o Sonnet 5.5, ...). Lote 1 = D01–D05, lote 2 = D06–D10."""
    plan: List[Dict[str, Any]] = []
    for i, iid in enumerate(ITEM_IDS):
        first, second = (ARMS[0], ARMS[1]) if i % 2 == 0 else (ARMS[1], ARMS[0])
        seq = [(first, 1), (second, 1), (second, 2), (first, 2)]
        for k, (model, rep) in enumerate(seq):
            n = i * 4 + k + 1
            plan.append({"tag": "t%02d" % n, "item": iid, "model": model, "rep": rep,
                         "batch": 1 if i < 5 else 2, "order_in_batch": (i % 5) * 4 + k + 1})
    return plan


PLAN = build_plan()
PLAN_BY_TAG = {p["tag"]: p for p in PLAN}


# ------------------------------------------------------------------- ensaio
def _runs_dir(out: str) -> str:
    return os.path.join(out, "runs")


def _load_json(path: str) -> Optional[Any]:
    try:
        with open(path, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError):
        return None


def _all_attempt_records(out: str) -> List[Dict[str, Any]]:
    recs: List[Dict[str, Any]] = []
    d = _runs_dir(out)
    if not os.path.isdir(d):
        return recs
    for name in sorted(os.listdir(d)):
        if name.endswith(".json") and not name.endswith(".result.json"):
            rec = _load_json(os.path.join(d, name))
            if isinstance(rec, dict) and rec.get("schema") == "w5c1.trial/v1":
                recs.append(rec)
    return recs


def _spent_usd(rec: Dict[str, Any]) -> float:
    vals = [v for v in (rec.get("cost_cc_usd"), rec.get("cost_tok_usd")) if isinstance(v, (int, float))]
    return float(max(vals)) if vals else 0.0


def _child_env() -> Dict[str, str]:
    env = {}
    for k, v in os.environ.items():
        if k.startswith("CLAUDE_CODE_") or k in ("CLAUDE_EFFORT", "ANTHROPIC_MODEL",
                                                 "ANTHROPIC_SMALL_FAST_MODEL"):
            continue
        if k.startswith("ANTHROPIC_DEFAULT_") and k.endswith("_MODEL"):
            continue
        env[k] = v
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    return env


def _token_cost(model_usage: Any) -> Tuple[Optional[float], Dict[str, int]]:
    tokens = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    if not isinstance(model_usage, dict) or not model_usage:
        return None, tokens
    fields = {"input": "inputTokens", "output": "outputTokens",
              "cache_read": "cacheReadInputTokens", "cache_write": "cacheCreationInputTokens"}
    seen = False
    for usage in model_usage.values():
        if not isinstance(usage, dict):
            continue
        for k, f in fields.items():
            v = usage.get(f)
            if isinstance(v, int) and not isinstance(v, bool):
                tokens[k] += v
                seen = True
    if not seen:
        return None, tokens
    cost = sum(tokens[k] * PRICE_PER_MTOK[k] for k in tokens) / 1e6
    return round(cost, 6), tokens


def classify_result(data: Any, model: str) -> Dict[str, Any]:
    """Status e VALIDADE de uma saída JSON do ``claude -p`` (PREREG.md §4)."""
    res: Dict[str, Any] = {"status": "error_other", "valid": False, "invalid_reason": None,
                           "served_keys": [], "served_norm": []}
    if not isinstance(data, dict):
        res["invalid_reason"] = "unparseable_result"
        return res
    subtype = str(data.get("subtype") or "")
    if data.get("is_error") is True:
        res["status"] = "error_max_budget" if "budget" in subtype else "error_other"
    elif subtype == "success":
        res["status"] = "success"
    mu = data.get("modelUsage")
    keys = sorted(mu.keys()) if isinstance(mu, dict) else []
    norm = sorted({k[:-4] if k.endswith("[1m]") else k for k in keys})
    res["served_keys"] = keys
    res["served_norm"] = norm
    if res["status"] != "success":
        res["invalid_reason"] = "status_" + res["status"]
    elif norm != [model]:
        res["invalid_reason"] = "served_mismatch:" + ",".join(keys or ["<none>"])
    else:
        res["valid"] = True
    stop = data.get("stop_reason")
    term = data.get("terminal_reason")
    res["stop_reason"] = stop if isinstance(stop, str) else None
    res["terminal_reason"] = term if isinstance(term, str) else None
    res["refusal"] = "refusal" in ("%s %s" % (res["stop_reason"], res["terminal_reason"])).lower()
    return res


def run_trial(out: str, item_id: str, model: str, rep: int, tag: str,
              claude_bin: Optional[str], selftest: bool = False) -> Tuple[int, Dict[str, Any]]:
    """UM ensaio. Saídas: 0 gravado (válido ou não), 3 tentativas esgotadas,
    4 teto de gasto do run, 5 erro do instrumento (nada foi chamado)."""
    plan = PLAN_BY_TAG.get(tag)
    if plan is None or (plan["item"], plan["model"], plan["rep"]) != (item_id, model, rep):
        raise InstrumentError("trial %s/%s/%s/%s is not in the pre-registered plan"
                              % (tag, item_id, model, rep))
    if os.path.isdir(os.path.join(out, "blind")):
        raise InstrumentError("blinding already done in %s: trials are frozen" % out)
    prompt_path = os.path.join(out, "items", item_id, "prompt.txt")
    try:
        with open(prompt_path, "rb") as fh:
            prompt = fh.read()
    except OSError:
        raise InstrumentError("missing %s (run --build first)" % prompt_path)
    if sha256_bytes(prompt) != EXPECTED.get(item_id, {}).get("prompt"):
        raise InstrumentError("%s does not match the pre-registered sha256" % prompt_path)
    runs = _runs_dir(out)
    os.makedirs(runs, exist_ok=True)
    rec_path = os.path.join(runs, tag + ".json")
    current = _load_json(rec_path)
    if isinstance(current, dict) and current.get("valid") is True:
        return 0, dict(current, reused=True)
    attempts = [n for n in os.listdir(runs) if n.startswith(tag + ".attempt") and n.endswith(".json")
                and not n.endswith(".result.json")]
    done = len(attempts) + (1 if isinstance(current, dict) else 0)
    if done >= MAX_ATTEMPTS:
        return 3, {"tag": tag, "status": "attempts_exhausted", "attempts": done}
    if isinstance(current, dict):
        k = len(attempts) + 1
        for suffix in (".json", ".result.json", ".stderr.txt", ".answer.txt"):
            src = os.path.join(runs, tag + suffix)
            if os.path.exists(src):
                os.replace(src, os.path.join(runs, "%s.attempt%d%s" % (tag, k, suffix)))
    spent = sum(_spent_usd(r) for r in _all_attempt_records(out))
    if spent >= RUN_BUDGET_USD:
        return 4, {"tag": tag, "status": "run_budget_exhausted", "spent_usd": round(spent, 4)}
    if not claude_bin:
        raise InstrumentError("claude binary not found on PATH")
    env = _child_env()
    ver = subprocess.run([claude_bin, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env=env, timeout=60)
    cc_version = ver.stdout.decode("utf-8", "replace").strip()
    record: Dict[str, Any] = {
        "schema": "w5c1.trial/v1", "instrument": INSTRUMENT_VERSION,
        "instrument_sha256": instrument_sha256(), "selftest": bool(selftest),
        "tag": tag, "item": item_id, "model": model, "rep": rep, "attempt": done + 1,
        "cc_version": cc_version, "effort": EFFORT, "prompt_sha256": sha256_bytes(prompt),
        "api_key_env_present": "ANTHROPIC_API_KEY" in env,
    }
    if cc_version != CC_VERSION_REQUIRED:
        record.update({"status": "instrument_error", "valid": False,
                       "invalid_reason": "cc_version:" + cc_version})
        _atomic_write(rec_path, _json_bytes(record))
        return 5, record
    argv = [claude_bin, "-p", prompt.decode("utf-8"), "--model", model, "--effort", EFFORT,
            "--output-format", "json", "--setting-sources", "", "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--tools", "", "--permission-mode", "manual",
            "--no-session-persistence", "--max-budget-usd", str(PER_TRIAL_BUDGET_USD)]
    shown = list(argv)
    shown[0] = "<claude>"
    shown[2] = "<prompt sha256=%s>" % record["prompt_sha256"]
    record["argv"] = shown
    work_root = os.path.join(out, "work")
    os.makedirs(work_root, exist_ok=True)
    work = tempfile.mkdtemp(prefix=tag + ".", dir=work_root)
    t0 = time.monotonic()
    timed_out = False
    try:
        with open(os.path.join(runs, tag + ".result.json"), "wb") as fo, \
                open(os.path.join(runs, tag + ".stderr.txt"), "wb") as fe:
            try:
                proc = subprocess.run(argv, cwd=work, env=env, stdout=fo, stderr=fe,
                                      timeout=PER_TRIAL_WALL_S)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                rc = -1
    finally:
        shutil.rmtree(work, ignore_errors=True)
    record["wall_s"] = round(time.monotonic() - t0, 1)
    record["rc"] = rc
    data = _load_json(os.path.join(runs, tag + ".result.json"))
    cls = classify_result(data, model)
    if timed_out:
        cls.update({"status": "error_timeout", "valid": False, "invalid_reason": "status_error_timeout"})
    record.update(cls)
    record["cost_cc_usd"] = data.get("total_cost_usd") if isinstance(data, dict) else None
    cost_tok, tokens = _token_cost(data.get("modelUsage") if isinstance(data, dict) else None)
    record["cost_tok_usd"] = cost_tok
    record["tokens"] = tokens
    if isinstance(data, dict):
        record["duration_ms"] = data.get("duration_ms")
        record["num_turns"] = data.get("num_turns")
        answer = data.get("result")
        if isinstance(answer, str):
            ab = answer.encode("utf-8")
            _atomic_write(os.path.join(runs, tag + ".answer.txt"), ab)
            record["answer_sha256"] = sha256_bytes(ab)
            record["answer_chars"] = len(answer)
    if record.get("valid") and "answer_sha256" not in record:
        record.update({"valid": False, "invalid_reason": "no_answer_text"})
    _atomic_write(rec_path, _json_bytes(record))
    return 0, record


# --------------------------------------------------------------- cegamento
def _final_records(out: str) -> Dict[str, Dict[str, Any]]:
    recs: Dict[str, Dict[str, Any]] = {}
    for p in PLAN:
        rec = _load_json(os.path.join(_runs_dir(out), p["tag"] + ".json"))
        if isinstance(rec, dict):
            recs[p["tag"]] = rec
    return recs


def blind_map(out: str, salt: str) -> Dict[str, List[Dict[str, Any]]]:
    if not SALT_RE.match(salt or ""):
        raise InstrumentError("salt must match [A-Za-z0-9]{16,64}")
    recs = _final_records(out)
    mapping: Dict[str, List[Dict[str, Any]]] = {}
    for item in ITEMS:
        entries: List[Dict[str, Any]] = []
        for p in PLAN:
            rec = recs.get(p["tag"])
            if p["item"] == item["id"] and isinstance(rec, dict) and rec.get("valid") is True:
                entries.append({"kind": "trial", "tag": p["tag"], "model": p["model"], "rep": p["rep"]})
        entries.append({"kind": "control", "control": item["control"]})
        entries.sort(key=lambda e: sha256_bytes(("%s|%s|%s" % (salt, item["id"], e.get("tag", "control"))).encode("utf-8")))
        for k, e in enumerate(entries):
            e["label"] = "R%d" % (k + 1)
        mapping[item["id"]] = entries
    return mapping


def redact(text: str) -> str:
    return MODEL_NAME_RE.sub("[MODEL]", text)


def blind(out: str, salt: str) -> List[Dict[str, str]]:
    mapping = blind_map(out, salt)
    listing: List[Dict[str, str]] = []
    bdir = os.path.join(out, "blind")
    for item in ITEMS:
        for e in mapping[item["id"]]:
            if e["kind"] == "trial":
                rec = _load_json(os.path.join(_runs_dir(out), e["tag"] + ".json")) or {}
                path = os.path.join(_runs_dir(out), e["tag"] + ".answer.txt")
                with open(path, "rb") as fh:
                    raw = fh.read()
                if sha256_bytes(raw) != rec.get("answer_sha256"):
                    raise InstrumentError("answer of %s does not match its record" % e["tag"])
                text = raw.decode("utf-8")
            else:
                with open(os.path.join(out, "controls", item["id"] + ".txt"), "rb") as fh:
                    text = fh.read().decode("utf-8")
            dst = os.path.join(bdir, item["id"], e["label"] + ".txt")
            _atomic_write(dst, redact(text).encode("utf-8"))
            listing.append({"item": item["id"], "label": e["label"], "path": dst})
    return listing


def record_grade(out: str, item_id: str, label: str, found: str, fp: int, rationale: str) -> str:
    if item_id not in ITEM_BY_ID:
        raise InstrumentError("unknown item %r" % item_id)
    if not LABEL_RE.match(label or "") or not os.path.isfile(os.path.join(out, "blind", item_id, label + ".txt")):
        raise InstrumentError("no blind entry %s/%s" % (item_id, label))
    if found not in ("yes", "partial", "no"):
        raise InstrumentError("--found must be yes, partial or no")
    if fp < 0:
        raise InstrumentError("--fp must be >= 0")
    path = os.path.join(out, "grades", item_id, label + ".json")
    _atomic_write(path, _json_bytes({"item": item_id, "label": label, "found": found,
                                     "false_positives": fp, "rationale": rationale[:2000]}))
    return path


# ------------------------------------------------------------------- placar
def _median(vals: Sequence[float]) -> Optional[float]:
    return float(statistics.median(vals)) if vals else None


ACTIONS = {
    "C1": ("PASS", "não-inferior e custo ≤ 1,2× o Sonnet 5: segue para o SIGN; o adapter fica "
                   "sem mudança e a ANT-02 é resíduo declarado («não medida», fora da 1.4.3)."),
    "C2": ("PASS-CUSTO-DECLARADO", "não-inferior e custo > 1,2×: segue para o SIGN com o custo "
                                   "medido declarado no material assinado; ANT-02 «não medida»."),
    "C3": ("FAIL", "inferior por δ (custo ≤ 1,2×): pára antes do SIGN; o Owner decide por "
                   "múltipla escolha; pelo runbook, a W5c sai pela linha de corte."),
    "C4": ("FAIL", "inferior por δ (custo > 1,2×): pára antes do SIGN; o Owner decide por "
                   "múltipla escolha; pelo runbook, a W5c sai pela linha de corte."),
}


def score(out: str, salt: str, allow_selftest: bool = False) -> Tuple[int, Dict[str, Any]]:
    result: Dict[str, Any] = {"instrument": INSTRUMENT_VERSION, "instrument_sha256": instrument_sha256(),
                              "ant02": "não medida", "verdict": None, "cell": None}
    recs = _final_records(out)
    problems: List[str] = []
    for p in PLAN:
        rec = recs.get(p["tag"])
        if rec is None:
            continue
        if (rec.get("item"), rec.get("model"), rec.get("rep")) != (p["item"], p["model"], p["rep"]):
            problems.append("%s: record does not match the plan" % p["tag"])
        if rec.get("selftest") and not allow_selftest:
            problems.append("%s: self-test record in a real run" % p["tag"])
        if rec.get("instrument_sha256") != result["instrument_sha256"]:
            problems.append("%s: instrument sha256 changed during the run" % p["tag"])
        if rec.get("cc_version") != CC_VERSION_REQUIRED:
            problems.append("%s: Claude Code version %r" % (p["tag"], rec.get("cc_version")))
        if rec.get("effort") != EFFORT:
            problems.append("%s: effort %r" % (p["tag"], rec.get("effort")))
    if problems:
        result.update({"verdict": "INVÁLIDO", "problems": problems})
        return 2, result
    mapping = blind_map(out, salt)
    grades: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for iid in ITEM_IDS:
        gdir = os.path.join(out, "grades", iid)
        for e in mapping[iid]:
            g = _load_json(os.path.join(gdir, e["label"] + ".json"))
            if isinstance(g, dict):
                grades[(iid, e["label"])] = g
    control_fail: List[str] = []
    per_arm: Dict[str, Dict[str, Any]] = {m: {"n_valid": 0, "found_yes": 0, "partial": 0, "fp": 0,
                                              "refusals": 0, "cost_pairs": [], "out_tokens": [],
                                              "wall_s": []} for m in ARMS}
    per_item: List[Dict[str, Any]] = []
    for item in ITEMS:
        row: Dict[str, Any] = {"item": item["id"], "class": item["class"]}
        for m in ARMS:
            row[m] = {"yes": 0, "partial": 0, "valid": 0}
        for e in mapping[item["id"]]:
            g = grades.get((item["id"], e["label"]))
            if e["kind"] == "control":
                want = "yes" if e["control"] == "positive" else "no"
                if g is None or g.get("found") != want:
                    control_fail.append(item["id"])
                continue
            if g is None or g.get("found") not in ("yes", "partial", "no"):
                continue  # sem nota = vazio
            rec = recs[e["tag"]]
            arm = per_arm[e["model"]]
            arm["n_valid"] += 1
            row[e["model"]]["valid"] += 1
            if g["found"] == "yes":
                arm["found_yes"] += 1
                row[e["model"]]["yes"] += 1
            elif g["found"] == "partial":
                arm["partial"] += 1
                row[e["model"]]["partial"] += 1
            fp = g.get("false_positives")
            arm["fp"] += fp if isinstance(fp, int) and not isinstance(fp, bool) else 0
            arm["refusals"] += 1 if rec.get("refusal") else 0
            arm["cost_pairs"].append((rec.get("cost_tok_usd"), rec.get("cost_cc_usd")))
            tok = (rec.get("tokens") or {}).get("output")
            if isinstance(tok, int):
                arm["out_tokens"].append(tok)
            if isinstance(rec.get("wall_s"), (int, float)):
                arm["wall_s"].append(float(rec["wall_s"]))
        per_item.append(row)
    n_planned = len(ITEMS) * len(REPS)
    arms_out: Dict[str, Any] = {}
    for m in ARMS:
        a = per_arm[m]
        arms_out[m] = {"n_valid": a["n_valid"], "void": n_planned - a["n_valid"],
                       "found_yes": a["found_yes"], "partial": a["partial"],
                       "false_positives": a["fp"], "refusals": a["refusals"],
                       "median_cost_usd": None,
                       "median_output_tokens": _median([float(x) for x in a["out_tokens"]]),
                       "median_wall_s": _median(a["wall_s"])}
    result["arms"] = arms_out
    result["per_item"] = per_item
    result["controls_failed"] = sorted(set(control_fail))
    if control_fail:
        result["verdict"] = "INCONCLUSIVO"
        result["reason"] = "controle do avaliador falhou em %s" % ",".join(sorted(set(control_fail)))
        return 2, result
    ref, sub = ARMS
    if any(arms_out[m]["void"] >= VOID_LIMIT for m in ARMS):
        result["verdict"] = "INCONCLUSIVO"
        result["reason"] = "vazios >= %d num braço" % VOID_LIMIT
        return 2, result
    # Custo: UMA fonte para TODOS os ensaios válidos dos dois braços — tokens x
    # tabela fixa; senão total_cost_usd; valor ausente, zero ou fonte mista =
    # custo não medido (um zero faria o braço parecer "barato" por engano).
    pairs = per_arm[ref]["cost_pairs"] + per_arm[sub]["cost_pairs"]

    def _usable(idx: int) -> bool:
        return bool(pairs) and all(isinstance(p[idx], (int, float)) and not isinstance(p[idx], bool)
                                   and p[idx] > 0 for p in pairs)

    source = "tokens" if _usable(0) else ("total_cost_usd" if _usable(1) else None)
    if source is None:
        result["verdict"] = "INCONCLUSIVO"
        result["reason"] = "custo não medido (sem fonte única e positiva para todos os ensaios válidos)"
        return 2, result
    idx = 0 if source == "tokens" else 1
    for m in ARMS:
        arms_out[m]["median_cost_usd"] = _median([float(p[idx]) for p in per_arm[m]["cost_pairs"]])
    result["cost_source"] = source
    med_ref, med_sub = arms_out[ref]["median_cost_usd"], arms_out[sub]["median_cost_usd"]
    d_ref, n_ref = arms_out[ref]["found_yes"], arms_out[ref]["n_valid"]
    d_sub, n_sub = arms_out[sub]["found_yes"], arms_out[sub]["n_valid"]
    # não-inferior  <=>  d_sub/n_sub >= d_ref/n_ref - DELTA_PP/100 (aritmética inteira)
    noninferior = 100 * d_sub * n_ref >= 100 * d_ref * n_sub - DELTA_PP * n_ref * n_sub
    cheap = med_sub * COST_RATIO_DEN <= med_ref * COST_RATIO_NUM
    cell = {(True, True): "C1", (True, False): "C2", (False, True): "C3", (False, False): "C4"}[(noninferior, cheap)]
    verdict, action = ACTIONS[cell]
    result.update({"cell": cell, "verdict": verdict, "action": action,
                   "noninferior": noninferior, "cost_ratio": round(med_sub / med_ref, 4),
                   "detection_rate": {ref: round(d_ref / n_ref, 4), sub: round(d_sub / n_sub, 4)}})
    return (0 if verdict.startswith("PASS") else 1), result


# ----------------------------------------------------------------- autoteste
_STUB = r'''#!/usr/bin/env python3
import json, os, sys
if "--version" in sys.argv:
    print(os.environ.get("W5C1_STUB_VERSION", "2.1.287 (Claude Code)"))
    sys.exit(0)
counter = os.environ["W5C1_STUB_COUNTER"]
try:
    with open(counter) as fh:
        before = len(fh.read())
except OSError:
    before = 0
with open(counter, "a") as fh:
    fh.write("x")
model = sys.argv[sys.argv.index("--model") + 1]
assert sys.argv[sys.argv.index("--effort") + 1] == "xhigh"
assert sys.argv[sys.argv.index("--tools") + 1] == ""
mode = os.environ.get("W5C1_STUB_MODE", "ok")
served = model
if mode == "swap" and model == "claude-sonnet-5":
    served = "claude-sonnet-5-5"
if mode == "swapfirst" and model == "claude-sonnet-5" and before < int(os.environ["W5C1_STUB_SWAP_FIRST"]):
    served = "claude-sonnet-5-5"
usage = {served + ("[1m]" if mode == "1m" else ""): {
    "inputTokens": 1000, "outputTokens": 20000 if model == "claude-sonnet-5" else int(os.environ.get("W5C1_STUB_OUT55", "22000")),
    "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}}
if mode == "extra":
    usage["claude-haiku-4-5"] = {"inputTokens": 10, "outputTokens": 10}
if mode == "notokens":
    usage = {served: {"costUSD": 0.3}}
doc = {"type": "result", "subtype": "success", "is_error": False, "result":
       "As Claude Sonnet 5.5 I found: line 1 is wrong.", "modelUsage": usage,
       "total_cost_usd": float(os.environ.get("W5C1_STUB_COST", "0.3")), "duration_ms": 1000,
       "num_turns": 1}
if mode == "budget":
    doc.update({"subtype": "error_max_budget_usd", "is_error": True})
print(json.dumps(doc))
'''


def _selftest(repo: str) -> List[str]:
    """Controles vermelho→verde do executor, do cegamento e do placar (sem gasto)."""
    fails: List[str] = []
    root = tempfile.mkdtemp(prefix="w5c1-selftest.")
    saved = {k: os.environ.get(k) for k in ("W5C1_STUB_VERSION", "W5C1_STUB_COUNTER",
                                            "W5C1_STUB_MODE", "W5C1_STUB_OUT55", "W5C1_STUB_COST",
                                            "W5C1_STUB_SWAP_FIRST")}
    try:
        stub = os.path.join(root, "claude")
        with open(stub, "w", encoding="utf-8") as fh:
            fh.write(_STUB)
        os.chmod(stub, 0o755)
        os.environ["W5C1_STUB_COUNTER"] = os.path.join(root, "calls")
        salt = "SelfTestSalt0123456789"

        def expect(name: str, cond: bool) -> None:
            if not cond:
                fails.append(name)

        def fresh(name: str) -> str:
            out = os.path.join(root, name)
            build_all(repo, out)
            return out

        def calls() -> int:
            try:
                with open(os.environ["W5C1_STUB_COUNTER"]) as fh:
                    return len(fh.read())
            except OSError:
                return 0

        def run_all(out: str) -> None:
            for p in PLAN:
                run_trial(out, p["item"], p["model"], p["rep"], p["tag"], stub, selftest=True)

        def grade_all(out: str, yes_ref: int, yes_sub: int, break_control: bool = False) -> None:
            mapping = blind_map(out, salt)
            count = {ARMS[0]: 0, ARMS[1]: 0}
            for iid in ITEM_IDS:
                for e in mapping[iid]:
                    if e["kind"] == "control":
                        want = "yes" if e["control"] == "positive" else "no"
                        if break_control and iid == "D01":
                            want = "yes"
                        record_grade(out, iid, e["label"], want, 0, "selftest")
                        continue
                    limit = yes_ref if e["model"] == ARMS[0] else yes_sub
                    found = "yes" if count[e["model"]] < limit else "no"
                    count[e["model"]] += 1
                    record_grade(out, iid, e["label"], found, 0, "selftest")

        # (a) caminho válido + reuso: a 2.ª chamada de uma etiqueta válida não chama o claude.
        os.environ["W5C1_STUB_MODE"] = "ok"
        out = fresh("pass")
        run_all(out)
        n = calls()
        rc, rec = run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
        expect("reuse-does-not-call", calls() == n and rec.get("reused") is True)
        expect("valid-record", rec.get("valid") is True and rec.get("cost_tok_usd") == 0.202)
        listing = blind(out, salt)
        expect("blind-count", len(listing) == 50)
        expect("blind-redacts", all("Sonnet" not in open(e["path"], encoding="utf-8").read() for e in listing))
        try:
            run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
            expect("trials-frozen-after-blind", False)
        except InstrumentError:
            pass
        grade_all(out, 18, 16)                                  # 80 % >= 90 % - 10 pp
        rc, res = score(out, salt, allow_selftest=True)
        expect("C1-pass-at-delta-boundary", rc == 0 and res.get("cell") == "C1")
        rc, res = score(out, salt, allow_selftest=False)
        expect("selftest-records-invalid-in-real-run", rc == 2 and res.get("verdict") == "INVÁLIDO")
        grade_all(out, 18, 15)                                  # 75 % < 80 % -> inferior
        rc, res = score(out, salt, allow_selftest=True)
        expect("C3-fail-beyond-delta", rc == 1 and res.get("cell") == "C3")
        grade_all(out, 18, 18, break_control=True)
        rc, res = score(out, salt, allow_selftest=True)
        expect("control-failure-inconclusive", rc == 2 and res.get("controls_failed") == ["D01"])

        # (b) custo > 1,2x -> C2.
        os.environ["W5C1_STUB_OUT55"] = "26000"
        out = fresh("cost")
        run_all(out)
        blind(out, salt)
        grade_all(out, 18, 18)
        rc, res = score(out, salt, allow_selftest=True)
        expect("C2-cost-declared", rc == 0 and res.get("cell") == "C2")
        os.environ["W5C1_STUB_OUT55"] = "22000"

        # (c) id servido != pedido -> inválido; 3 tentativas e esgota; braço vazio -> INCONCLUSIVO.
        os.environ["W5C1_STUB_MODE"] = "swap"
        out = fresh("swap")
        rc, rec = run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
        expect("served-mismatch-invalid", rec.get("valid") is False
               and str(rec.get("invalid_reason")).startswith("served_mismatch:"))
        run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
        run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
        rc, rec = run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
        expect("attempts-exhausted", rc == 3)
        run_all(out)
        blind(out, salt)
        grade_all(out, 20, 20)
        rc, res = score(out, salt, allow_selftest=True)
        expect("void-arm-inconclusive", rc == 2 and res.get("verdict") == "INCONCLUSIVO")

        # (b2) sem tokens no CLI: cai para total_cost_usd em TODOS; custo zero -> INCONCLUSIVO.
        os.environ["W5C1_STUB_MODE"] = "notokens"
        out = fresh("notok")
        run_all(out)
        blind(out, salt)
        grade_all(out, 18, 18)
        rc, res = score(out, salt, allow_selftest=True)
        expect("cost-fallback-total", rc == 0 and res.get("cost_source") == "total_cost_usd")
        os.environ["W5C1_STUB_COST"] = "0"
        out = fresh("zerocost")
        run_all(out)
        blind(out, salt)
        grade_all(out, 18, 18)
        rc, res = score(out, salt, allow_selftest=True)
        expect("zero-cost-inconclusive", rc == 2 and res.get("verdict") == "INCONCLUSIVO")
        os.environ["W5C1_STUB_COST"] = "0.3"

        # (c2) limite de vazios: 5 vazios num braço -> INCONCLUSIVO; 4 -> decide.
        for swap_first, want_rc, name in ((9, 2, "void-limit-5-inconclusive"), (8, 0, "void-4-decides")):
            os.environ["W5C1_STUB_MODE"] = "swapfirst"
            os.environ["W5C1_STUB_SWAP_FIRST"] = str(swap_first)
            os.environ["W5C1_STUB_COUNTER"] = os.path.join(root, "calls-%d" % swap_first)
            out = fresh("void%d" % swap_first)
            run_all(out)
            blind(out, salt)
            grade_all(out, 20, 20)
            rc, res = score(out, salt, allow_selftest=True)
            expect(name, rc == want_rc and res["arms"][ARMS[0]]["void"] == (5 if swap_first == 9 else 4))
        os.environ["W5C1_STUB_COUNTER"] = os.path.join(root, "calls")

        # (c3) prompt adulterado -> recusa; resposta adulterada -> o cegamento recusa.
        os.environ["W5C1_STUB_MODE"] = "ok"
        out = fresh("tamper")
        with open(os.path.join(out, "items", "D01", "prompt.txt"), "ab") as fh:
            fh.write(b" ")
        try:
            run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
            expect("tampered-prompt-refused", False)
        except InstrumentError:
            pass
        out = fresh("tamper2")
        run_all(out)
        with open(os.path.join(out, "runs", "t05.answer.txt"), "ab") as fh:
            fh.write(b" ")
        try:
            blind(out, salt)
            expect("tampered-answer-refused", False)
        except InstrumentError:
            pass

        # (d) chave extra (modelo auxiliar) -> inválido; variante [1m] -> válido.
        os.environ["W5C1_STUB_MODE"] = "extra"
        out = fresh("extra")
        rc, rec = run_trial(out, "D02", ARMS[1], 1, "t05", stub, selftest=True)
        expect("extra-model-key-invalid", rec.get("valid") is False)
        os.environ["W5C1_STUB_MODE"] = "1m"
        out = fresh("onem")
        rc, rec = run_trial(out, "D02", ARMS[1], 1, "t05", stub, selftest=True)
        expect("1m-variant-valid", rec.get("valid") is True)

        # (e) estouro de orçamento por ensaio -> vazio; teto do run -> recusa.
        os.environ["W5C1_STUB_MODE"] = "budget"
        out = fresh("budget")
        rc, rec = run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
        expect("budget-kill-void", rec.get("status") == "error_max_budget" and rec.get("valid") is False)
        os.environ["W5C1_STUB_MODE"] = "ok"
        os.environ["W5C1_STUB_COST"] = "41"
        run_trial(out, "D01", ARMS[1], 1, "t02", stub, selftest=True)
        n = calls()
        rc, rec = run_trial(out, "D01", ARMS[1], 2, "t03", stub, selftest=True)
        expect("run-budget-cap", rc == 4 and calls() == n)
        os.environ["W5C1_STUB_COST"] = "0.3"

        # (f) versão do Claude Code diferente -> erro do instrumento, nada pago.
        os.environ["W5C1_STUB_VERSION"] = "2.1.288 (Claude Code)"
        out = fresh("ccver")
        n = calls()
        rc, rec = run_trial(out, "D01", ARMS[0], 1, "t01", stub, selftest=True)
        expect("cc-version-refused", rc == 5 and calls() == n)
        os.environ["W5C1_STUB_VERSION"] = CC_VERSION_REQUIRED

        # (g) fora do plano -> recusa.
        try:
            run_trial(out, "D01", ARMS[1], 1, "t01", stub, selftest=True)
            expect("off-plan-refused", False)
        except InstrumentError:
            pass
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(root, ignore_errors=True)
    return fails


def _check_origin(path: str) -> List[str]:
    p = os.path.expanduser(path)
    if not os.path.isfile(p):
        print("origin: %s ausente — tabela embutida usada (sha256 pinado em ORIGIN_JSON_SHA256)" % path)
        return []
    with open(p, "rb") as fh:
        raw = fh.read()
    problems: List[str] = []
    if sha256_bytes(raw) != ORIGIN_JSON_SHA256:
        return ["origin: sha256 of %s differs from ORIGIN_JSON_SHA256" % path]
    items = json.loads(raw.decode("utf-8")).get("result", {}).get("items", [])
    by_id = {it.get("id"): it for it in items if isinstance(it, dict)}
    for item in ITEMS:
        o = by_id.get(item["id"])
        if o is None:
            problems.append("origin: %s missing" % item["id"])
            continue
        for f, v in item["origin"].items():
            if o.get(f) != v:
                problems.append("origin: %s.%s differs" % (item["id"], f))
        if not item["fix_commit"].startswith(o.get("fix_commit", "?")):
            problems.append("origin: %s fix_commit prefix differs" % item["id"])
    if not problems:
        print("origin: %s confere (sha256 + %d itens)" % (path, len(ITEMS)))
    return problems


def check(repo: str) -> int:
    problems: List[str] = []
    a = tempfile.mkdtemp(prefix="w5c1-check-a.")
    b = tempfile.mkdtemp(prefix="w5c1-check-b.")
    try:
        man_a = build_all(repo, a)
        man_b = build_all(repo, b)
        if man_a != man_b:
            problems.append("determinism: two builds differ")
        problems.extend(compare_expected(man_a))
        print("manifest digest: %s" % manifest_digest(man_a))
    except InstrumentError as exc:
        problems.append("build: %s" % exc)
    finally:
        shutil.rmtree(a, ignore_errors=True)
        shutil.rmtree(b, ignore_errors=True)
    problems.extend(_check_origin(ORIGIN_JSON_DEFAULT))
    plan_tags = [p["tag"] for p in PLAN]
    if plan_tags != ["t%02d" % n for n in range(1, 41)]:
        problems.append("plan: tags are not t01..t40")
    try:
        st = _selftest(repo)
    except Exception as exc:  # um autoteste que explode é vermelho NOMEADO, nunca traceback mudo
        st = ["aborted (%s: %s)" % (type(exc).__name__, exc)]
    problems.extend("selftest: %s" % f for f in st)
    for p in problems:
        print("FAIL " + p)
    print("check: %s (%d problem(s); selftest %d control(s) red)" % ("OK" if not problems else "FAILED",
                                                                    len(problems), len(st)))
    return 0 if not problems else 1


# ---------------------------------------------------------------------- CLI
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="W5c.1 instrument v2 (see PREREG.md)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--print-manifest", action="store_true")
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--build", metavar="OUT")
    mode.add_argument("--trial", metavar="OUT")
    mode.add_argument("--blind", metavar="OUT")
    mode.add_argument("--record-grade", metavar="OUT")
    mode.add_argument("--score", metavar="OUT")
    ap.add_argument("--item")
    ap.add_argument("--model")
    ap.add_argument("--rep", type=int)
    ap.add_argument("--tag")
    ap.add_argument("--salt")
    ap.add_argument("--label")
    ap.add_argument("--found")
    ap.add_argument("--fp", type=int, default=0)
    ap.add_argument("--rationale", default="")
    ns = ap.parse_args(argv)
    try:
        if ns.plan:
            print(json.dumps(PLAN, indent=1))
            return 0
        repo = _repo_root()
        if ns.check:
            return check(repo)
        if ns.print_manifest:
            tmp = tempfile.mkdtemp(prefix="w5c1-manifest.")
            try:
                man = build_all(repo, tmp)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            print(json.dumps({"digest": manifest_digest(man), "items": man}, indent=1, sort_keys=True))
            return 0
        if ns.build:
            man = build_all(repo, ns.build)
            problems = compare_expected(man)
            for p in problems:
                print("FAIL " + p)
            print(json.dumps({"built": ns.build, "digest": manifest_digest(man),
                              "ok": not problems}, sort_keys=True))
            return 0 if not problems else 1
        if ns.trial:
            if ns.tag is None or not TAG_RE.match(ns.tag):
                raise InstrumentError("--tag must look like t01")
            rc, rec = run_trial(ns.trial, ns.item, ns.model, ns.rep, ns.tag, shutil.which("claude"))
            print(json.dumps({k: rec.get(k) for k in ("tag", "item", "model", "rep", "attempt", "status",
                                                      "valid", "invalid_reason", "served_keys", "refusal",
                                                      "cost_tok_usd", "cost_cc_usd", "wall_s", "reused",
                                                      "attempts", "spent_usd")}, sort_keys=True))
            return rc
        if ns.blind:
            print(json.dumps(blind(ns.blind, ns.salt or ""), indent=1))
            return 0
        if ns.record_grade:
            print(record_grade(ns.record_grade, ns.item or "", ns.label or "", ns.found or "",
                               ns.fp, ns.rationale))
            return 0
        if ns.score:
            rc, res = score(ns.score, ns.salt or "")
            data = _json_bytes(res)
            _atomic_write(os.path.join(ns.score, "score.json"), data)
            res["score_json_sha256"] = sha256_bytes(data)
            print(json.dumps(res, ensure_ascii=False, sort_keys=True))
            return rc
    except InstrumentError as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return 5
    return 2


if __name__ == "__main__":
    sys.exit(main())
