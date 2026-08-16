#!/usr/bin/env python3
"""Gera verdict-fields + envelope pair-rail-verdict para a rc.4 a partir da
evidência CORRENTE em repass-rc4/. Fail-CLOSED em toda checagem (nunca
`assert`: PYTHONOPTIMIZE apagaria o gate). Uso:

  python3 gen-envelope-rc4.py --stage fields --parent <sha40> \\
      --conditions-file <md>          # OBRIGATORIO se algum rail = GWC
  # -> Owner: gpg --detach-sign --armor verdict-fields-v1.3.0-rc.4.md
  python3 gen-envelope-rc4.py --stage envelope --sig <.asc>

Derivacoes dos artefatos REAIS (nunca digitadas): inputs_hash pela funcao
do proprio validador; MANIFEST-rc4 verificado; transcript_hash =
sha256(t1||t2); parent VINCULADO ao candidato do runner/PROVENANCE; a
DECISAO agregada e DERIVADA dos 2 rails (GWC se qualquer um for GWC);
as CONDICOES entram nos FIELDS (material assinado); payload codex
verificado via check_pair_rail --verify-codex-pin; assinatura VERIFICADA
antes de embutir; escrita atomica sem seguir symlink. stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

REPO = pathlib.Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip())
EV = REPO / ".claude/plans/PLAN-177/repass-rc4"
FIELDS = REPO / ".claude/plans/PLAN-177/verdict-fields-v1.3.0-rc.4.md"
ENVELOPE = REPO / ".claude/governance/pair-rail-verdict-v1.3.0-rc.4.md"
GOV = REPO / ".claude/governance"
TAG = "v1.3.0-rc.4"
SIGNER_FPR = "AE9B236FDAF0462874060C6BCFCFACF00335DC74"

ARTIFACTS = [
    "MANIFEST-rc4.sha256", "PROVENANCE-rc4.md",
    "diff-rc4-1.patch", "diff-rc4-2.patch",
    "paths-rc4-1.manifest.txt", "paths-rc4-2.manifest.txt",
    "payload-rc4-1.redacted.txt", "payload-rc4-2.redacted.txt",
    "transcript-rc4-1.log", "transcript-rc4-2.log",
    "verdict-rc4-1.txt", "verdict-rc4-2.txt",
    "run-rc4-repass.sh",
]
# Este gerador vive em PLAN-177/ (fora de repass-rc4/) de proposito — nao e
# evidencia do re-pass, nao entra no MANIFEST nem na allowlist.


def die(msg: str) -> "None":
    sys.stderr.write("FATAL: %s\n" % msg)
    sys.exit(2)


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_atomic_regular(path: pathlib.Path, text: str) -> None:
    """Refuse symlink/non-regular targets; same-dir tmp + atomic rename."""
    if path.is_symlink():
        die("%s is a symlink — refusing to write through it" % path)
    if path.exists() and not path.is_file():
        die("%s exists and is not a regular file" % path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".gen-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "v", str(REPO / ".github/scripts/validate-pair-rail-verdict.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rail_decisions() -> "list[str]":
    out = []
    for n in (1, 2):
        v = (EV / ("verdict-rc4-%d.txt" % n)).read_text(encoding="utf-8")
        lines = [ln for ln in v.splitlines() if ln.startswith("VERDICT:")]
        # o rail as vezes repete a linha final; exigir que TODAS concordem
        toks = set()
        for ln in lines:
            m = re.match(r"VERDICT:\s*(GO-WITH-CONDITIONS|GO|NO-GO)\b", ln)
            if not m:
                die("parte %d: VERDICT ilegivel: %r" % (n, ln))
            toks.add(m.group(1))
        if len(toks) != 1:
            die("parte %d: decisoes divergentes na mesma saida: %r" % (n, toks))
        out.append(toks.pop())
    return out


def runner_candidate() -> str:
    """O candidato que o runner efetivamente revisou (PROVENANCE + runner)."""
    prov = (EV / "PROVENANCE-rc4.md").read_text(encoding="utf-8")
    m = re.search(r"Candidato: ([0-9a-f]{40})", prov)
    if not m:
        die("PROVENANCE sem 'Candidato: <sha40>'")
    prov_sha = m.group(1)
    run = (EV / "run-rc4-repass.sh").read_text(encoding="utf-8")
    m2 = re.search(r'^CANDIDATE_SHA="([0-9a-f]{40})"', run, re.M)
    if not m2:
        die("runner sem CANDIDATE_SHA")
    if m2.group(1) != prov_sha:
        die("runner pin %s != PROVENANCE candidato %s" % (m2.group(1), prov_sha))
    return prov_sha


def verified_codex_pin() -> "dict":
    proc = subprocess.run(
        [sys.executable, str(REPO / ".claude/hooks/check_pair_rail.py"),
         "--verify-codex-pin"],
        stdout=subprocess.PIPE, universal_newlines=True, cwd=str(REPO))
    try:
        d = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        die("check_pair_rail --verify-codex-pin: saida ilegivel: %r" % proc.stdout)
    if d.get("status") != "verified":
        die("codex payload NAO verificado: %r" % d)
    if d.get("sha256") != d.get("expected_sha256"):
        die("codex payload sha != manifest")
    return d


def build_fields(parent: str, conditions_text: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", parent or ""):
        die("--parent deve ser sha40")
    for a in ARTIFACTS:
        if not (EV / a).is_file():
            die("artefato ausente: %s" % a)
    rc = subprocess.call(["shasum", "-a", "256", "-c", "MANIFEST-rc4.sha256",
                          "--status"], cwd=str(EV))
    if rc != 0:
        die("MANIFEST-rc4 nao verifica")
    prov = (EV / "PROVENANCE-rc4.md").read_text(encoding="utf-8")
    if "RUNNER-OVERALL: rc=" not in prov:
        die("PROVENANCE sem RUNNER-OVERALL")
    cand = runner_candidate()
    if parent != cand:
        die("--parent %s != candidato revisado %s (a evidencia cobre OUTRA "
            "arvore; re-rode o re-pass ou corrija o parent)" % (parent, cand))
    d1, d2 = rail_decisions()
    if "NO-GO" in (d1, d2):
        # Owner-ratified closure route: a NO-GO rail may only ride under an
        # explicit CONDITIONS text naming it as a declared residual.
        if not conditions_text or "RESIDUAL" not in conditions_text.upper():
            die("rail NO-GO (%s/%s) sem secao de condicoes declarando o "
                "RESIDUAL ratificado pelo Owner" % (d1, d2))
        verdict = "GO-WITH-CONDITIONS"
    elif "GO-WITH-CONDITIONS" in (d1, d2):
        verdict = "GO-WITH-CONDITIONS"
    else:
        verdict = "GO"
    if verdict == "GO-WITH-CONDITIONS" and not conditions_text:
        die("GO-WITH-CONDITIONS exige --conditions-file (vai no material assinado)")

    val = load_validator()
    inputs_hash = val.compute_inputs_hash(
        REPO, GOV / "pair-rail-inputs-hash-manifest.txt")
    manifest_sha = sha256_file(GOV / "pair-rail-inputs-hash-manifest.txt")
    delta_manifest_sha = sha256_file(EV / "MANIFEST-rc4.sha256")
    th = hashlib.sha256()
    th.update((EV / "transcript-rc4-1.log").read_bytes())
    th.update((EV / "transcript-rc4-2.log").read_bytes())
    transcript_hash = th.hexdigest()

    pin = verified_codex_pin()
    codex_ver = subprocess.check_output(
        ["codex", "--version"], universal_newlines=True).strip().split()[-1]
    py = "%d.%d.%d" % sys.version_info[:3]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "verdict: %s" % verdict,
        "generated_at: %s" % now,
        "ttl_hours: 24",
        "parent_sha: %s" % parent,
        "release_tag: %s" % TAG,
        "inputs_hash: %s" % inputs_hash,
        "inputs_hash_paths_manifest_sha: %s" % manifest_sha,
        "delta_allowlist:",
        "  - .claude/governance/pair-rail-verdict-%s.md" % TAG,
        "  - .claude/plans/PLAN-177/verdict-fields-%s.md" % TAG,
    ]
    for a in ARTIFACTS:
        lines.append("  - .claude/plans/PLAN-177/repass-rc4/%s" % a)
    lines += [
        "delta_manifest: .claude/plans/PLAN-177/repass-rc4/MANIFEST-rc4.sha256",
        "delta_manifest_sha256: %s" % delta_manifest_sha,
        "tool_versions:",
        "  codex_cli: %s" % codex_ver,
        "  codex_target_triple: %s" % pin["target_triple"],
        "  codex_payload_sha256: %s" % pin["sha256"],
        "  claude_code: claude-fable-5",
        "  python: %s" % py,
        "transcript_hash: %s" % transcript_hash,
        "rail_decisions: [part1=%s, part2=%s]" % (d1, d2),
        "findings: [ga-repass-t2-t12-NOGO-curados-por-rodada, "
        "t13-part1-%s-part2-%s, "
        "lote-B-PLAN-178-44-rounds-2GOs-sentinel-SENT-PLAN178-LOTEB]"
        % (d1.lower().replace("-", ""), d2.lower().replace("-", "")),
    ]
    if conditions_text:
        # As condicoes SAO material assinado: entram nos fields como
        # sub-mapa de linhas (bare key + indented list), grammar-safe.
        lines.append("conditions:")
        for ln in conditions_text.rstrip("\n").splitlines():
            ln = ln.rstrip()
            if not ln:
                continue
            # linhas de lista markdown viram itens; prosa vira item tambem
            item = ln.lstrip("- ").strip()
            item = item.replace("#", "\u2116")  # nunca introduzir comentario YAML
            lines.append("  - %s" % item)
    return "\n".join(lines) + "\n"


def verify_sig(sig_path: pathlib.Path) -> None:
    proc = subprocess.run(
        ["gpg", "--status-fd", "1", "--verify", str(sig_path), str(FIELDS)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    good = [ln for ln in proc.stdout.splitlines()
            if ln.startswith("[GNUPG:] VALIDSIG ")]
    if proc.returncode != 0 or not good:
        die("assinatura NAO verifica contra %s:\n%s" % (FIELDS, proc.stderr))
    if SIGNER_FPR not in good[0]:
        die("assinatura de OUTRO signatario: %s" % good[0])


def build_envelope(fields_text: str, sig_b64: str) -> str:
    verdict = [ln for ln in fields_text.splitlines()
               if ln.startswith("verdict:")][0].split(":", 1)[1].strip()
    body = fields_text.rstrip("\n") + "\ngpg_signature: base64:%s\n" % sig_b64
    parts = [
        "# Pair-Rail Verdict - %s" % TAG, "",
        "```yaml", body.rstrip("\n"), "```", "",
        "## Signature verification recipe", "",
        'base64 -d do valor apos "base64:" -> .asc destacado; verificar contra',
        ".claude/plans/PLAN-177/verdict-fields-%s.md (commitado junto)." % TAG,
        "Signer CFCFACF00335DC74. As CONDICOES fazem parte do material assinado",
        "(sub-mapa `conditions:` dos fields).", "",
        "<!-- VERDICT: %s -->" % verdict,
        "## Review record - re-pass do CANDIDATO rc.4 (advisory input)", "",
        "- Contexto: re-pass do hold sobre a rc.3 (12/08) NO-GO com 4 P1;",
        "  curas PLAN-177 + Lote B PLAN-178 (sentinel SENT-PLAN178-LOTEB,",
        "  rail 44 rounds) em main. Re-pass do CANDIDATO: t2..t12 NO-GO com",
        "  curas a cada rodada (quarentenas repass-rc4-20260816-tN-NOGO/,",
        "  cronica em repass-rc4-advisory-preparent/NOTA.md) -> t13 (rodada",
        "  FINAL declarada) fechado por decisao Owner-ratificada; decisoes",
        "  por rail em `rail_decisions:` (material assinado).",
        "- Reviewer: codex-cli (codex exec --sandbox read-only), prompt +",
        "  diff atraves do redactor ADR-114 como UM pipeline; pin ADR-182",
        "  VERIFICADO (check_pair_rail --verify-codex-pin) antes de gerar.", "",
        "## Derivacoes (parte do material assinado)", "",
        "- transcript_hash = sha256(transcript-rc4-1.log || transcript-rc4-2.log).",
        "- inputs_hash RECOMPUTADO nesta arvore com compute_inputs_hash do",
        "  proprio validador; validado localmente com o argv literal do step-15.",
        "- parent_sha VINCULADO ao candidato do runner/PROVENANCE (gerador",
        "  recusa qualquer outro SHA).",
        "- delta_manifest_sha256 pina MANIFEST-rc4.sha256 (12 entradas, runner",
        "  incluso). Payloads raw NAO commitados; pins em PROVENANCE-rc4.md.", "",
        "## Excecoes herdadas (registro)", "",
        "V1/V2/V4/V5 do trem (verdict-fields-v1.3.0-rc.2.md §Condicoes) seguem",
        "abertas pela rota (b) ratificada: curas STAGED no pack W3 (PLAN-169),",
        "landa por cerimonia GPG apos o GA com re-staging por ITEM semantico.", "",
    ]
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("fields", "envelope"), required=True)
    ap.add_argument("--parent")
    ap.add_argument("--sig")
    ap.add_argument("--conditions-file")
    a = ap.parse_args()
    if a.stage == "fields":
        conds = ""
        if a.conditions_file:
            conds = pathlib.Path(a.conditions_file).read_text(encoding="utf-8")
        write_atomic_regular(FIELDS, build_fields(a.parent, conds))
        print("wrote", FIELDS)
        return 0
    if not a.sig:
        die("--stage envelope exige --sig")
    sig_path = pathlib.Path(a.sig)
    verify_sig(sig_path)
    fields_text = FIELDS.read_bytes().decode("utf-8")
    val = load_validator()
    # o material assinado precisa passar na PROPRIA gramatica dos twins
    probe = "```yaml\n%s```\n" % fields_text
    if val.noncanonical_top_level_lines(probe):
        die("fields nao passam na gramatica canonica: %r"
            % val.noncanonical_top_level_lines(probe))
    write_atomic_regular(
        ENVELOPE,
        build_envelope(fields_text,
                       base64.b64encode(sig_path.read_bytes()).decode("ascii")))
    # re-verificar: o base64 embutido decodifica para a mesma assinatura
    env = ENVELOPE.read_bytes().decode("utf-8")
    m = re.search(r"^gpg_signature: base64:(\S+)$", env, re.M)
    if not m or base64.b64decode(m.group(1)) != sig_path.read_bytes():
        die("assinatura embutida != .asc")
    print("wrote", ENVELOPE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
