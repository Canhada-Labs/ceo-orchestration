#!/usr/bin/env python3
"""Gera verdict-fields + envelope pair-rail-verdict para o GA v1.4.1 a
partir da evidencia CORRENTE em repass-ga/. Fail-CLOSED em toda checagem
(nunca `assert`: PYTHONOPTIMIZE apagaria o gate). Uso:

  python3 gen-envelope-ga.py --stage fields --parent <sha40> \\
      --conditions-file <md>          # OBRIGATORIO se algum rail = GWC
  # -> Owner: gpg --detach-sign --armor verdict-fields-v1.4.1.md
  python3 gen-envelope-ga.py --stage envelope --sig <.asc>
  python3 gen-envelope-ga.py --stage verify --sig <.asc>  # retomada, sem escrita

DERIVADO por .claude/plans/PLAN-192/derive-ga-kit-141.py do gerador da rc.1
(gen-envelope-rc1.py; fonte e sha256 em SOURCES, no derivador): TAG, diretorio
da evidencia e a prosa do review record sao os do GA. NAO edite a mao. Duas
propriedades herdadas:

  1. `codex_cli` NAO vem de `codex --version`. A versao vem da linha
     `- codex:` da PROVENANCE, que o runner escreve a partir do pin que ele
     proprio VERIFICOU, e este gerador re-valida contra a faixa do
     `codex-cli-pin.txt` e contra o manifesto ADR-182 antes de escrever — a
     MESMA checagem que o step 15 do release.yml faz sobre o envelope.
  2. `SIGNER_FPR` nao e uma constante digitada. Ele e DERIVADO de duas
     fontes independentes — o fingerprint dentro da assinatura do envelope
     PRECEDENTE e o registro `.claude/sentinel-signers.txt` — e as duas
     TEM de concordar.

Demais derivacoes, todas dos artefatos REAIS e nunca digitadas: inputs_hash
pela funcao do proprio validador; MANIFEST-ga verificado; transcript_hash =
sha256 da concatenacao ordenada dos transcripts; parent VINCULADO ao
candidato do runner/PROVENANCE; a DECISAO agregada e DERIVADA dos rails;
as CONDICOES entram nos FIELDS (material assinado); assinatura VERIFICADA
antes de embutir; escrita atomica sem seguir symlink. stdlib only, >= 3.9.

GA: `tool_versions.claude_code` e MEDIDO no --stage fields (`claude --version`
da maquina que gera os fields, fora do repo; recusa nomeada se ausente ou
ilegivel) — a VERSAO do Claude Code CLI, nao o modelo. Na verificacao (envelope
e verify) o valor ASSINADO e conservado, como o generated_at: um auto-update do
Claude Code entre o passo 9 e o 11 nao invalida a assinatura.
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
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

REPO = pathlib.Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip())
PLAN = ".claude/plans/PLAN-192"
EV = REPO / PLAN / "repass-ga"
TAG = "v1.4.1"
FIELDS = REPO / PLAN / ("verdict-fields-%s.md" % TAG)
ENVELOPE = REPO / ".claude/governance" / ("pair-rail-verdict-%s.md" % TAG)
GOV = REPO / ".claude/governance"
PRECEDENT = GOV / "pair-rail-verdict-v1.4.0.md"
SIGNERS = REPO / ".claude/sentinel-signers.txt"
NPARTS = 3
PARTS = list(range(1, NPARTS + 1))

REVIEWED_CONDITIONS = "CONDITIONS-ga.reviewed.md"
ARTIFACTS = ["MANIFEST-ga.sha256", "PROVENANCE-ga.md", "CANDIDATE.sha",
             REVIEWED_CONDITIONS]
for _p in PARTS:
    ARTIFACTS += [
        "diff-ga-%d.patch" % _p,
        "paths-ga-%d.manifest.txt" % _p,
        "payload-ga-%d.redacted.txt" % _p,
        "transcript-ga-%d.log" % _p,
        "verdict-ga-%d.txt" % _p,
    ]
ARTIFACTS.append("run-ga-repass.sh")
ARTIFACTS = sorted(set(ARTIFACTS))
# Este gerador vive em PLAN-192/ (FORA de repass-ga/) de proposito — nao e
# evidencia do re-pass, nao entra no MANIFEST nem na delta_allowlist.


def die(msg: str) -> None:
    sys.stderr.write("FATAL: %s\n" % msg)
    sys.exit(2)


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_atomic_regular(path: pathlib.Path, text: str) -> None:
    """Recusa symlink/nao-regular; temporario no MESMO dir + rename atomico."""
    if path.is_symlink():
        die("%s e symlink — recuso escrever atraves dele" % path)
    if path.exists() and not path.is_file():
        die("%s existe e nao e arquivo regular" % path)
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


def signer_fpr() -> str:
    """DUAS fontes independentes, que TEM de concordar.

    (a) o fingerprint embutido na assinatura do envelope PRECEDENTE
        (subpacote 33 `issuer fpr v4`, lido por `gpg --list-packets` sobre a
        assinatura decodificada — nao exige o material assinado);
    (b) o registro rastreado `.claude/sentinel-signers.txt`.

    Uma constante digitada seria uma terceira fonte, envelhecendo sozinha.
    """
    if not PRECEDENT.is_file():
        die("envelope precedente ausente: %s" % PRECEDENT)
    m = re.search(r"^gpg_signature: base64:(\S+)$",
                  PRECEDENT.read_text(encoding="utf-8"), re.M)
    if not m:
        die("envelope precedente sem gpg_signature base64")
    try:
        raw = base64.b64decode(m.group(1), validate=True)
    except Exception as exc:
        die("gpg_signature do precedente nao decodifica: %s" % exc)
    fd, tmp = tempfile.mkstemp(suffix=".asc")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        proc = subprocess.run(["gpg", "--list-packets", tmp],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True)
    finally:
        os.unlink(tmp)
    if proc.returncode != 0:
        die("gpg --list-packets recusou a assinatura do precedente")
    mm = re.search(r"issuer fpr v4 ([0-9A-F]{40})", proc.stdout)
    if not mm:
        die("assinatura do precedente sem subpacote de issuer fpr")
    from_env = mm.group(1)

    if not SIGNERS.is_file():
        die("registro de signatarios ausente: %s" % SIGNERS)
    reg = [ln.strip() for ln in SIGNERS.read_text(encoding="utf-8").splitlines()
           if ln.strip() and not ln.strip().startswith("#")]
    fprs = [ln.split()[0].upper() for ln in reg]
    if from_env not in fprs:
        die("fingerprint do envelope precedente (%s) nao esta em %s: %r"
            % (from_env, SIGNERS, fprs))

    # Seam de AUTO-TESTE, recusado fora do scratchpad declarado. Existe so
    # para `test-ga-kit.sh` exercitar fields -> assinatura -> envelope com
    # uma chave DESCARTAVEL. Relaxa EXATAMENTE uma coisa — qual fingerprint e
    # aceita — e nunca a exigencia de VALIDSIG nem a derivacao acima, que
    # continua rodando e podendo abortar. O valor vem por ARGUMENTO explicito
    # (variavel dedicada), nunca de sentinela dentro do material.
    if os.environ.get("GA_SELFTEST") == "1":
        scratch = os.environ.get("GA_SELFTEST_SCRATCH", "/nonexistent")
        if not (os.path.realpath(str(REPO)) + os.sep).startswith(
                os.path.realpath(scratch) + os.sep):
            die("GA_SELFTEST=1 fora do scratchpad declarado — recusado")
        sub = os.environ.get("GA_SELFTEST_SIGNER_FPR", "")
        if not re.fullmatch(r"[0-9A-F]{40}", sub):
            die("auto-teste exige GA_SELFTEST_SIGNER_FPR (40 hex maiusculos)")
        sys.stderr.write(
            "AVISO: auto-teste — fingerprint aceita trocada para %s\n" % sub)
        return sub
    return from_env


def provenance_text() -> str:
    p = EV / "PROVENANCE-ga.md"
    if not p.is_file():
        die("PROVENANCE-ga.md ausente — o runner nao rodou")
    return p.read_text(encoding="utf-8")


def pinned_codex(prov: str) -> Dict[str, str]:
    """A tripla do codex vem da PROVENANCE, e e re-validada contra os pins."""
    m = re.search(r"^- codex: (\S+) / (\S+) / payload (\S+)$", prov, re.M)
    if not m:
        die("PROVENANCE sem a linha '- codex: <ver> / <triple> / payload <sha>'")
    ver, triple, payload = m.group(1), m.group(2), m.group(3)
    if "stub" in (ver, triple, payload):
        die("PROVENANCE de um run com CODEX_BIN=stub — evidencia de harness, "
            "nunca de release")
    if not re.fullmatch(r"[0-9a-f]{64}", payload):
        die("payload da PROVENANCE nao e um sha256: %r" % payload)
    # (a) a versao declarada tem de estar na faixa do pin — a MESMA checagem
    # que o step 15 do release.yml faz sobre o envelope.
    val = load_validator()
    min_v, max_v = val.parse_pin_range(GOV / "codex-cli-pin.txt")
    if not (min_v and max_v):
        die("codex-cli-pin.txt sem faixa parseavel — recuso gerar sem o gate")
    if not val.semver_in_range(ver, min_v, max_v):
        die("codex_cli %s fora da faixa do pin (%s .. %s) — o step 15 "
            "rejeitaria o envelope" % (ver, min_v, max_v))
    # (b) o payload declarado tem de ser o do manifesto ADR-182, para o triple.
    man = json.loads((GOV / "codex-cli-pin-manifest.json").read_text(encoding="utf-8"))
    entry = (man.get("payloads") or {}).get(triple)
    if not entry:
        die("pin-manifest sem entrada para o triple %r" % triple)
    if entry.get("sha256") != payload:
        die("payload declarado (%s) != manifesto (%s)" % (payload, entry.get("sha256")))
    if man.get("package_version") != ver:
        die("package_version do manifesto (%r) != versao declarada (%r)"
            % (man.get("package_version"), ver))
    return {"codex_cli": ver, "target_triple": triple, "sha256": payload}


def rail_decisions() -> List[str]:
    out = []
    for n in PARTS:
        v = (EV / ("verdict-ga-%d.txt" % n)).read_text(encoding="utf-8")
        lines = [ln for ln in v.splitlines() if ln.startswith("VERDICT:")]
        if len(lines) != 1:
            die("parte %d: esperado exatamente um VERDICT, recebido %d" % (n, len(lines)))
        m = re.fullmatch(r"VERDICT: (GO-WITH-CONDITIONS|GO|NO-GO)(?:\s.*)?", lines[0])
        if not m:
            die("parte %d: VERDICT ilegivel: %r" % (n, lines[0]))
        out.append(m.group(1))
    return out


def verify_manifest() -> None:
    """Todos os artefatos da tentativa, exatamente uma vez e pelos bytes."""
    for name in ARTIFACTS:
        path = EV / name
        if path.is_symlink() or not path.is_file():
            die("artefato ausente ou nao-regular: %s" % name)
    entries = {}
    for line in (EV / "MANIFEST-ga.sha256").read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match or match.group(2) in entries:
            die("MANIFEST-ga com registro malformado ou duplicado")
        entries[match.group(2)] = match.group(1)
    expected = set(ARTIFACTS) - {"MANIFEST-ga.sha256"}
    if set(entries) != expected:
        die("MANIFEST-ga nao cobre exatamente os %d artefatos da tentativa" % len(expected))
    for name, digest in entries.items():
        if sha256_file(EV / name) != digest:
            die("MANIFEST-ga nao verifica: %s" % name)


def reviewed_conditions(prov: str, supplied: Optional[str] = None) -> str:
    """O texto assinado deve ser o MESMO snapshot bruto fornecido ao revisor."""
    path = EV / REVIEWED_CONDITIONS
    if path.is_symlink() or not path.is_file():
        die("snapshot de condicoes revisadas ausente ou nao-regular")
    raw = path.read_bytes()
    pins = re.findall(
        r"^- condicoes declaradas no prompt \(DATA para o revisor\): "
        r"CONDITIONS-ga\.reviewed\.md sha256 ([0-9a-f]{64})$", prov, re.M)
    if len(pins) != 1 or pins[0] != hashlib.sha256(raw).hexdigest():
        die("condicoes revisadas divergem do hash da PROVENANCE — novo re-pass necessario")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        die("condicoes revisadas nao sao UTF-8 valido")
    if supplied is not None and supplied != text:
        die("condicoes para assinatura diferem das revisadas — novo re-pass necessario")
    source = EV / "CONDITIONS-ga.md"
    if source.is_symlink() or (source.exists() and not source.is_file()):
        die("condicoes de entrada nao sao arquivo regular sem symlink")
    current = source.read_bytes() if source.exists() else b""
    if current != raw:
        die("condicoes de entrada mudaram desde a revisao — novo re-pass necessario")
    return text


def runner_candidate(prov: str) -> str:
    """O candidato que o runner efetivamente revisou (3 fontes concordando)."""
    m = re.search(r"Candidato: ([0-9a-f]{40})", prov)
    if not m:
        die("PROVENANCE sem 'Candidato: <sha40>'")
    prov_sha = m.group(1)
    cand_file = (EV / "CANDIDATE.sha").read_text(encoding="utf-8").strip()
    if cand_file != prov_sha:
        die("CANDIDATE.sha (%s) != candidato da PROVENANCE (%s)"
            % (cand_file, prov_sha))
    run = (EV / "run-ga-repass.sh").read_text(encoding="utf-8")
    if 'CAND_FILE="$OUT/CANDIDATE.sha"' not in run:
        die("o runner nao le o candidato de CANDIDATE.sha — runner trocado?")
    return prov_sha


CLAUDE_CODE_RE = r"claude-code-cli-[0-9]+\.[0-9]+\.[0-9]+"


def claude_code_version() -> str:
    """tool_versions.claude_code MEDIDO: `claude --version` da maquina que gera os
    fields, rodado FORA do repo (cwd = diretorio temporario do sistema). Devolve
    `claude-code-cli-X.Y.Z` (so a versao, forma segura para a gramatica dos twins).
    Ausente, rc != 0 ou saida sem versao: recusa nomeada, nunca um valor digitado."""
    exe = shutil.which("claude")
    if not exe:
        die("claude ausente no PATH: tool_versions.claude_code e MEDIDO por "
            "`claude --version` (nunca digitado)")
    try:
        proc = subprocess.run([exe, "--version"], stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, universal_newlines=True,
                              timeout=60, cwd=tempfile.gettempdir(), check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        die("`claude --version` falhou: %s" % exc)
    out = (proc.stdout or "").strip()
    m = re.match(r"([0-9]+\.[0-9]+\.[0-9]+)(?![0-9.])", out)
    if proc.returncode != 0 or not m:
        die("`claude --version` ilegivel (rc=%s): %r" % (proc.returncode, out[:80]))
    return "claude-code-cli-%s" % m.group(1)


def build_fields(parent: str, conditions_text: str, generated_at: Optional[str] = None,
                 claude_code: Optional[str] = None) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", parent or ""):
        die("--parent deve ser sha40")
    verify_manifest()
    prov = provenance_text()
    cand = runner_candidate(prov)
    if parent != cand:
        die("--parent %s != candidato revisado %s (a evidencia cobre OUTRA "
            "arvore; re-rode o re-pass ou corrija o parent)" % (parent, cand))

    decisions = rail_decisions()
    if "NO-GO" in decisions:
        die("rail NO-GO (%s): TODAS as partes devem aprovar; RESIDUAL nao autoriza o corte"
            % ", ".join(decisions))
    elif "GO-WITH-CONDITIONS" in decisions:
        verdict = "GO-WITH-CONDITIONS"
    else:
        verdict = "GO"
    if [ln for ln in prov.splitlines() if ln.startswith("RUNNER-OVERALL:")] != ["RUNNER-OVERALL: rc=0"]:
        die("PROVENANCE exige exatamente um RUNNER-OVERALL: rc=0")
    reviewed_conditions(prov, conditions_text)
    if verdict == "GO-WITH-CONDITIONS" and not conditions_text:
        die("GO-WITH-CONDITIONS exige --conditions-file (vai no material assinado)")

    val = load_validator()
    inputs_hash = val.compute_inputs_hash(
        REPO, GOV / "pair-rail-inputs-hash-manifest.txt")
    manifest_sha = sha256_file(GOV / "pair-rail-inputs-hash-manifest.txt")
    delta_manifest_sha = sha256_file(EV / "MANIFEST-ga.sha256")
    th = hashlib.sha256()
    for n in PARTS:                      # ordem DECLARADA: 1..NPARTS
        th.update((EV / ("transcript-ga-%d.log" % n)).read_bytes())
    transcript_hash = th.hexdigest()

    pin = pinned_codex(prov)
    py = "%d.%d.%d" % sys.version_info[:3]
    now = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cc = claude_code if claude_code is not None else claude_code_version()
    if not re.fullmatch(CLAUDE_CODE_RE, cc):
        die("tool_versions.claude_code fora da forma medida: %r" % cc)

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
        "  - %s/verdict-fields-%s.md" % (PLAN, TAG),
    ]
    for a in ARTIFACTS:
        lines.append("  - %s/repass-ga/%s" % (PLAN, a))
    lines += [
        "delta_manifest: %s/repass-ga/MANIFEST-ga.sha256" % PLAN,
        "delta_manifest_sha256: %s" % delta_manifest_sha,
        "tool_versions:",
        "  codex_cli: %s" % pin["codex_cli"],
        "  codex_target_triple: %s" % pin["target_triple"],
        "  codex_payload_sha256: %s" % pin["sha256"],
        "  claude_code: %s" % cc,
        "  python: %s" % py,
        "transcript_hash: %s" % transcript_hash,
        "rail_decisions: [%s]" % ", ".join(
            "part%d=%s" % (n, d) for n, d in zip(PARTS, decisions)),
        "findings: [ga-3-partes-por-risco-do-adotante, %s, "
        "cobertura-declarada-em-repass-ga-README-ga]"
        % ", ".join("p%d-%s" % (n, d.lower().replace("-", ""))
                    for n, d in zip(PARTS, decisions)),
    ]
    if conditions_text:
        # As condicoes SAO material assinado: entram nos fields como sub-mapa
        # de linhas (chave nua + lista indentada), grammar-safe.
        lines.append("conditions:")
        for ln in conditions_text.rstrip("\n").splitlines():
            ln = ln.rstrip()
            if not ln:
                continue
            item = ln.lstrip("- ").strip()
            item = item.replace("#", "\u2116")  # nunca introduzir comentario YAML
            lines.append("  - %s" % item)
    return "\n".join(lines) + "\n"


def verify_fields_evidence(fields_text: str) -> None:
    """Reconstroi os fields contra a evidencia atual antes de embutir a assinatura.

    So o timestamp e a versao MEDIDA do Claude Code assinados sao conservados;
    todo o resto, incluindo o hash do
    manifesto que fecha o snapshot bruto, deve permanecer byte-identico.
    """
    parents = re.findall(r"^parent_sha: ([0-9a-f]{40})$", fields_text, re.M)
    dates = re.findall(r"^generated_at: (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)$", fields_text, re.M)
    if len(parents) != 1 or len(dates) != 1:
        die("fields sem parent_sha/generated_at unicos e canonicos")
    # GA: a versao MEDIDA do Claude Code assinada e conservada como o timestamp
    # (um auto-update entre a assinatura e a verificacao nao a invalida).
    ccs = re.findall(r"^  claude_code: (%s)$" % CLAUDE_CODE_RE, fields_text, re.M)
    if len(ccs) != 1:
        die("fields sem tool_versions.claude_code unico e na forma medida")
    expected = build_fields(parents[0], reviewed_conditions(provenance_text()), dates[0],
                            ccs[0])
    if fields_text != expected:
        die("fields assinados divergem da evidencia atual — novo re-pass/assinatura necessario")


def verify_sig(sig_path: pathlib.Path, fpr: str) -> None:
    proc = subprocess.run(
        ["gpg", "--status-fd", "1", "--verify", str(sig_path), str(FIELDS)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    good = [ln for ln in proc.stdout.splitlines()
            if ln.startswith("[GNUPG:] VALIDSIG ")]
    if proc.returncode != 0 or not good:
        die("assinatura NAO verifica contra %s:\n%s" % (FIELDS, proc.stderr))
    if fpr not in good[0]:
        die("assinatura de OUTRO signatario: %s" % good[0])


def build_envelope(fields_text: str, sig_b64: str, fpr: str) -> str:
    verdict = [ln for ln in fields_text.splitlines()
               if ln.startswith("verdict:")][0].split(":", 1)[1].strip()
    body = fields_text.rstrip("\n") + "\ngpg_signature: base64:%s\n" % sig_b64
    parts = [
        "# Pair-Rail Verdict - %s" % TAG, "",
        "```yaml", body.rstrip("\n"), "```", "",
        "## Signature verification recipe", "",
        'base64 -d do valor apos "base64:" -> .asc destacado; verificar contra',
        "%s/verdict-fields-%s.md (commitado junto)." % (PLAN, TAG),
        "Signer %s. As CONDICOES fazem parte do material assinado" % fpr[-16:],
        "(sub-mapa `conditions:` dos fields).", "",
        "<!-- VERDICT: %s -->" % verdict,
        "## Review record - re-pass do GA v1.4.1 (advisory input)",
        "",
        "- Contexto: GA v1.4.1 = promocao da v1.4.1-rc.1 depois do hold ADR-103.",
        "  A rodada 3 do re-pass da rc.1 revisou o candidato 7602fbe4 (3/3",
        "  GO-WITH-CONDITIONS; veredito assinado em 51bd2345, o commit da tag).",
        "  Patch FORA DE ORDEM sobre o GA v1.4.0: ledger de lancamento + guard de",
        "  retomada da tool Workflow, a correcao do relaunch --out e cinco CLIs",
        "  livres. O re-pass cobre o delta em %d partes por raio de dano ao" % NPARTS,
        "  adotante; o que fica de fora esta DECLARADO em",
        "  %s/repass-ga/README-ga.md — nao omitido." % PLAN,
        "- Nada foi curado entre a rc.1 e o GA: o que a rc.1 declarou aberto (as",
        "  secoes A a D das condicoes e os achados dos vereditos da rodada 3 dela)",
        "  segue known-open. O anexo P1 do envelope da v1.4.0 NAO e curado: a cura",
        "  foi re-alvejada para a v1.4.2 em 2026-09-18 (PLAN-192 OQ-1; e o que o",
        "  CHANGELOG [1.4.1] e a anotacao da tag dizem), e em 2026-09-22 o Owner",
        "  fez da v1.4.2 uma release expressa que nao a leva e a re-declara aberta:",
        "  nenhuma versao esta prometida para ela (condicao 1 do material assinado).",
        "- Declarado no GA (secao E das condicoes, condicao 23): o hook PreToolUse",
        "  da tool Workflow grava uma copia do arquivo que um scriptPath nomeia",
        "  antes da decisao de permissao do harness; known-open, com a cura",
        "  alvejada para a v1.4.2.",
        "- O envelope da rc.1 prometeu que o do GA diria, item a item, o que foi",
        "  curado. Para cada item que a rc.1 declarou aberto a resposta e a mesma:",
        "  nenhum foi curado entre a rc.1 e o GA, e todos seguem known-open",
        "  (cabecalho das condicoes, com os dois P1 da rodada 3).",
        "- A PROVENANCE diz, por parte, se algum arquivo da pathspec mudou desde o",
        "  candidato da rc.1. Entre a tag da rc.1 e o candidato revisado (no G0 e no",
        "  passo 5) o OWNER-GA-CUT.sh recusa o corte se mudar caminho fora de",
        "  CLAUDE.md e dos planos numerados; sobre o candidato entra so o commit do",
        "  veredito (este envelope, os fields e a evidencia do re-pass).",
        "- tool_versions.claude_code e a versao do Claude Code CLI MEDIDA por",
        "  `claude --version` na maquina que gerou os fields; nao e o modelo que",
        "  orquestrou o kit.",
        "- Cada parte cita, dentro do proprio prompt, as rodadas de rail que",
        "  ja revisaram aquele conteudo, para que uma condicao possa nomear a",
        "  cobertura em vez de tratar o conteudo como inedito.",
        "- Reviewer: codex-cli na versao que o manifesto ADR-182 pina — o binario",
        "  global quando ele e o pinado, senao npx num cache proprio (a rota esta",
        "  na PROVENANCE) — com o payload nativo VERIFICADO contra o manifesto",
        "  antes de qualquer revisao; versao, triple e sha256 do payload estao em",
        "  tool_versions e sao re-validados por este gerador.",
        "- Pipeline: prompt + diff atraves do redator ADR-114 como UM pipeline;",
        "  worktree DETACHED no SHA candidato (a tag GA ainda nao existe).",
        "",
        "## Derivacoes (parte do material assinado)", "",
        "- transcript_hash = sha256(transcript-ga-1.log || ... || "
        "transcript-ga-%d.log), nesta ordem." % NPARTS,
        "- inputs_hash RECOMPUTADO nesta arvore com compute_inputs_hash do",
        "  proprio validador.",
        "- parent_sha VINCULADO ao candidato do runner/PROVENANCE/CANDIDATE.sha",
        "  (o gerador recusa qualquer outro SHA, e exige que as tres fontes",
        "  concordem).",
        "- tool_versions.codex_cli vem da PROVENANCE do run PINADO, nunca de",
        "  `codex --version` da maquina, e e re-validado contra",
        "  codex-cli-pin.txt pela funcao do PROPRIO validador.",
        "- delta_manifest_sha256 pina MANIFEST-ga.sha256 (%d entradas, runner"
        % (NPARTS * 5 + 4),
        "  incluso). Payloads raw NAO commitados; pins em PROVENANCE-ga.md.",
        "",
    ]
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("fields", "envelope", "verify"), required=True)
    ap.add_argument("--parent")
    ap.add_argument("--sig")
    ap.add_argument("--conditions-file")
    a = ap.parse_args()
    fpr = signer_fpr()
    if a.stage == "fields":
        conds = ""
        if a.conditions_file:
            conds = pathlib.Path(a.conditions_file).read_bytes().decode("utf-8")
        write_atomic_regular(FIELDS, build_fields(a.parent, conds))
        print("wrote", FIELDS)
        return 0
    if not a.sig:
        die("--stage envelope/verify exige --sig")
    sig_path = pathlib.Path(a.sig)
    fields_raw = FIELDS.read_bytes()
    signature_raw = sig_path.read_bytes()
    verify_sig(sig_path, fpr)
    if FIELDS.read_bytes() != fields_raw or sig_path.read_bytes() != signature_raw:
        die("fields ou assinatura mudaram durante a verificacao")
    fields_text = fields_raw.decode("utf-8")
    verify_fields_evidence(fields_text)
    val = load_validator()
    # O material assinado precisa passar na PROPRIA gramatica dos twins.
    probe = "```yaml\n%s```\n" % fields_text
    bad = val.noncanonical_top_level_lines(probe)
    if bad:
        die("fields nao passam na gramatica canonica: %r" % bad)
    if a.stage == "verify":
        print("verified", FIELDS)
        return 0
    write_atomic_regular(
        ENVELOPE,
        build_envelope(fields_text,
                       base64.b64encode(signature_raw).decode("ascii"),
                       fpr))
    # Re-verificar: o base64 embutido decodifica para a MESMA assinatura.
    env = ENVELOPE.read_bytes().decode("utf-8")
    m = re.search(r"^gpg_signature: base64:(\S+)$", env, re.M)
    if not m or base64.b64decode(m.group(1)) != sig_path.read_bytes():
        die("assinatura embutida != .asc")
    print("wrote", ENVELOPE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
