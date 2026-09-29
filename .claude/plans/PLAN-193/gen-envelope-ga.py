#!/usr/bin/env python3
"""Gera verdict-fields + envelope pair-rail-verdict para o GA v1.4.2 a
partir da evidencia CORRENTE em repass-ga/. Fail-CLOSED em toda checagem
(nunca `assert`: PYTHONOPTIMIZE apagaria o gate). Uso:

  python3 gen-envelope-ga.py --stage fields --parent <sha40> \\
      --conditions-file <md>          # OBRIGATORIO se algum rail = GWC
  # -> Owner: gpg --detach-sign --armor verdict-fields-v1.4.2.md
  python3 gen-envelope-ga.py --stage envelope --sig <.asc>
  python3 gen-envelope-ga.py --stage verify --sig <.asc>  # retomada, sem escrita

DERIVADO por .claude/plans/PLAN-193/derive-ga-kit-142.py do gerador da v1.4.2-rc.1
(PLAN-193/gen-envelope-rc1.py; fonte e sha256 em SOURCES, no derivador): TAG,
diretorio da evidencia, envelope precedente e a prosa do review record sao os do
GA. NAO edite a mao. Duas propriedades herdadas:

  1. `codex_cli` NAO vem de `codex --version`. A versao vem da linha
     `- codex:` da PROVENANCE, que o runner escreve a partir do pin que ele
     proprio VERIFICOU, e este gerador re-valida contra a faixa do
     `codex-cli-pin.txt` e contra o manifesto ADR-182 antes de escrever — a
     MESMA checagem que o step 15 do release.yml faz sobre o envelope.
  2. `SIGNER_FPR` nao e uma constante digitada. Ele e DERIVADO de duas
     fontes independentes — o fingerprint dentro da assinatura do envelope
     PRECEDENTE e o registro `.claude/sentinel-signers.txt` — e as duas
     TEM de concordar. No GA o precedente e o envelope assinado da
     v1.4.2-rc.1, o ultimo desta linha de release (introduzido pelo commit
     da tag dela); na rc.1 era o do GA v1.4.1.

E duas que a rc.1 desta release ja carregava (a segunda, completada no GA):

  3. `tool_versions.claude_code` e MEDIDO no --stage fields (`claude --version`
     da maquina que gera os fields, rodado fora do repo; recusa nomeada se ausente
     ou ilegivel) — a VERSAO do Claude Code CLI, nao o modelo. Na verificacao
     (envelope e verify) o valor ASSINADO e conservado, como o generated_at: um
     auto-update do Claude Code entre o --stage fields e o --stage verify nao
     invalida a assinatura.
  4. A sonda das condicoes VERDE contra o candidato. O gerador da rc.1 lia so a
     linha da PROVENANCE; este le tambem o RELATORIO (probe-ga.txt, pinado pelo
     MANIFEST) e as duas fontes TEM de concordar: a linha na forma exata que o
     runner escreve com a sonda em rc 0; o relatorio sem linha FAIL/INFRA,
     terminando na unica linha `SONDA: 0 FALSA(S), 0 sem medida`, com cada
     verificacao da sonda do kit (PROBE_IDS: os ids da lista CHECKS da sonda,
     pinados ao derivar e conferidos contra a sonda derivada) numa linha OK
     exatamente uma vez e nenhuma linha OK de outro id, a arvore (C0-tree) DESTE
     candidato, a projecao de tamanho de exatamente as partes do re-pass, a unica
     linha MAPA com esses mesmos ids e o numero de linhas OK que a PROVENANCE
     declara. Evidencia de um run em modo REPORT-ONLY do harness, ou relatorio
     vazio, vermelho, de outro candidato ou parcial (uma verificacao que nao
     rodou, ou repetida no lugar de outra), e recusa nomeada — nunca vira fields.

Demais derivacoes, todas dos artefatos REAIS e nunca digitadas: inputs_hash
pela funcao do proprio validador; MANIFEST-ga verificado; transcript_hash =
sha256 da concatenacao ordenada dos transcripts; parent VINCULADO ao
candidato do runner/PROVENANCE; a DECISAO agregada e DERIVADA dos rails;
as CONDICOES entram nos FIELDS (material assinado); assinatura VERIFICADA
antes de embutir; escrita atomica sem seguir symlink. stdlib only, >= 3.9.
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
PLAN = ".claude/plans/PLAN-193"
EV = REPO / PLAN / "repass-ga"
TAG = "v1.4.2"
FIELDS = REPO / PLAN / ("verdict-fields-%s.md" % TAG)
ENVELOPE = REPO / ".claude/governance" / ("pair-rail-verdict-%s.md" % TAG)
GOV = REPO / ".claude/governance"
# Precedente = o ultimo envelope ASSINADO desta linha de release: o da v1.4.2-rc.1,
# introduzido pelo commit da tag dela. O fingerprint da assinatura dele TEM de
# estar no registro de signatarios (signer_fpr).
PRECEDENT = GOV / "pair-rail-verdict-v1.4.2-rc.1.md"
SIGNERS = REPO / ".claude/sentinel-signers.txt"
NPARTS = 4
PARTS = list(range(1, NPARTS + 1))

REVIEWED_CONDITIONS = "CONDITIONS-ga.reviewed.md"
ARTIFACTS = ["MANIFEST-ga.sha256", "PROVENANCE-ga.md", "CANDIDATE.sha",
             REVIEWED_CONDITIONS, "probe-ga.txt"]
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
# Este gerador vive em PLAN-193/ (FORA de repass-ga/) de proposito — nao e
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


PROBE_LINE_RE = r"^- sonda das condicoes: (.*)$"
# A linha que o runner (fase 3b) escreve quando a sonda sai rc 0; o numero vem de
# `grep -c '^OK '` sobre o PROPRIO relatorio.
PROBE_LABEL_RE = r"verde \(([1-9][0-9]*) linhas OK, nenhuma FALSA; probe-ga\.txt\)"
PROBE_REPORT = "probe-ga.txt"
PROBE_GREEN_TAIL = "SONDA: 0 FALSA(S), 0 sem medida"
PROBE_TREE_RE = r"OK   C0-tree: arvore == ([0-9a-f]{12}); "
PROBE_SIZE_RE = r"OK   SIZE parte ([0-9]+): "
PROBE_ID_RE = r"OK   ([^\s:]+): "
PROBE_MAP_PREFIX = "MAPA condicao -> ids: "
PROBE_MAP_ITEM_RE = r"(cabecalho|[0-9]+): ([^\s:;]+(?: [^\s:;]+)*)"
# Os ids das verificacoes da sonda do kit (a lista CHECKS de probe-conditions-ga.py),
# PINADOS pelo derivador, que recusa derivar se nao forem exatamente os ids da sonda
# derivada. Num relatorio verde, cada um esta numa linha OK exatamente uma vez.
PROBE_IDS = (
    "C0-tree", "C0-base", "C0-npm", "C0-rc", "C0-frozen", "C0-cut-gates", "C1-annex-v1.4.0",
    "C2-carried-1.4.1", "C3-fn04", "C4-relaunch-out", "C5-pin", "C6-effort", "C7-cc-floor",
    "C8-adapter", "C9-codex-pin", "C10-tools", "C11-scope", "C11-parts-rc", "C12-delivery",
    "C12-plan-decisions", "C13-rc-annex", "C14-rc-p2", "C15-install-pin",
)


def probe_refuse(why: str) -> None:
    die("o relatorio da sonda das condicoes (%s, no MANIFEST) %s — evidencia que nao prova "
        "a sonda VERDE contra o candidato, nunca de release" % (PROBE_REPORT, why))


def probe_green(prov: str, cand: str) -> None:
    """A sonda das condicoes ficou VERDE contra ESTE candidato (runner, fase 3b).

    Duas fontes, que TEM de concordar: a linha da PROVENANCE, na forma exata que o
    runner escreve com a sonda em rc 0, e o PROPRIO relatorio probe-ga.txt, pinado
    pelo MANIFEST (verify_manifest ja conferiu os bytes). Do relatorio, lido pelas
    linhas como o `grep -c` do runner as conta: nenhuma linha FAIL/INFRA (as formas de
    afirmacao FALSA e de sem medida); a ultima linha e `SONDA: 0 FALSA(S), 0 sem
    medida` e e a unica linha SONDA; o numero de linhas OK e o que a PROVENANCE
    declara; toda linha OK e de uma verificacao de PROBE_IDS ou de projecao de
    tamanho, e cada verificacao de PROBE_IDS esta numa linha OK exatamente uma vez
    (nenhuma ausente, repetida ou de outro id); a linha OK da arvore (C0-tree) nomeia
    ESTE candidato; ha uma linha OK de projecao de tamanho para cada parte do re-pass,
    e so para elas; e a unica linha MAPA mapeia exatamente os ids de PROBE_IDS e SIZE.
    Relatorio ausente, vazio, vermelho, de outro candidato ou de um run parcial (uma
    verificacao que nao rodou, ou repetida no lugar de outra): recusa nomeada."""
    lines = re.findall(PROBE_LINE_RE, prov, re.M)
    if len(lines) != 1 or not lines[0].startswith("verde ("):
        die("a PROVENANCE nao diz que a sonda das condicoes ficou verde contra o candidato "
            "(%r) — evidencia de ensaio (REPORT-ONLY) ou de um runner trocado, nunca de release"
            % (lines[0] if lines else None))
    label = re.fullmatch(PROBE_LABEL_RE, lines[0])
    if not label:
        die("a linha da sonda das condicoes na PROVENANCE (%r) nao tem a forma que o runner "
            "escreve com a sonda em rc 0 — runner trocado ou linha editada, nunca de release"
            % lines[0])
    path = EV / PROBE_REPORT
    if path.is_symlink() or not path.is_file():
        probe_refuse("esta ausente ou nao e arquivo regular")
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeError:
        probe_refuse("nao e UTF-8 valido")
    rows = text.split("\n")
    if rows and rows[-1] == "":
        rows.pop()
    bad = [r for r in rows if r.startswith(("FAIL", "INFRA"))]
    if bad:
        probe_refuse("tem %d linha(s) de afirmacao FALSA ou sem medida, a primeira: %r"
                     % (len(bad), bad[0][:160]))
    if not rows or rows[-1] != PROBE_GREEN_TAIL:
        probe_refuse("nao termina em %r (ultima linha: %r)"
                     % (PROBE_GREEN_TAIL, rows[-1][:160] if rows else None))
    if [r for r in rows if r.startswith("SONDA")] != [PROBE_GREEN_TAIL]:
        probe_refuse("tem mais de uma linha SONDA")
    oks = [r for r in rows if r.startswith("OK ")]
    if len(oks) != int(label.group(1)):
        probe_refuse("tem %d linha(s) OK e a PROVENANCE declara %s"
                     % (len(oks), label.group(1)))
    seen = {}  # type: Dict[str, int]
    sizes = []  # type: List[int]
    for r in oks:
        size = re.match(PROBE_SIZE_RE, r)
        if size:
            sizes.append(int(size.group(1)))
            continue
        cid = re.match(PROBE_ID_RE, r)
        if not cid or cid.group(1) not in PROBE_IDS:
            probe_refuse("tem uma linha OK que nao e de verificacao da sonda do kit nem de "
                         "projecao de tamanho (%r)" % r[:160])
        seen[cid.group(1)] = seen.get(cid.group(1), 0) + 1
    missing = [i for i in PROBE_IDS if i not in seen]
    if missing:
        probe_refuse("nao tem a linha OK de %d verificacao(oes) da sonda do kit (%s): run "
                     "parcial ou sonda trocada" % (len(missing), ", ".join(missing)))
    repeated = [i for i in PROBE_IDS if seen[i] != 1]
    if repeated:
        probe_refuse("repete a linha OK de %s: cada verificacao da sonda conta UMA vez"
                     % ", ".join(repeated))
    trees = [re.match(PROBE_TREE_RE, r) for r in oks if r.startswith("OK   C0-tree: ")]
    if len(trees) != 1 or trees[0] is None or trees[0].group(1) != cand[:12]:
        probe_refuse("nao confere a arvore DESTE candidato (%s): linha OK C0-tree ausente, "
                     "repetida ou de outro commit" % cand[:12])
    if sorted(sizes) != PARTS:
        probe_refuse("nao projeta o tamanho de exatamente as partes %r (linhas OK SIZE das "
                     "partes %r)" % (PARTS, sorted(sizes)))
    maps = [r for r in rows if r.startswith("MAPA")]
    if len(maps) != 1 or not maps[0].startswith(PROBE_MAP_PREFIX):
        probe_refuse("nao tem exatamente uma linha %r (tem %d linha(s) MAPA)"
                     % (PROBE_MAP_PREFIX.rstrip(), len(maps)))
    mapped = set()
    for item in maps[0][len(PROBE_MAP_PREFIX):].split("; "):
        pair = re.fullmatch(PROBE_MAP_ITEM_RE, item)
        if not pair:
            probe_refuse("tem a linha MAPA fora da forma que a sonda escreve (item %r)"
                         % item[:80])
        mapped.update(pair.group(2).split(" "))
    want = set(PROBE_IDS) | {"SIZE"}
    if mapped != want:
        probe_refuse("tem a linha MAPA com outros ids que os da sonda do kit (a mais: %s; "
                     "ausentes: %s)" % (sorted(mapped - want), sorted(want - mapped)))


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
    probe_green(prov, cand)
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
        "findings: [ga-4-partes-por-risco-do-adotante, sonda-das-condicoes-verde, %s, "
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
    # A versao MEDIDA do Claude Code assinada e conservada como o timestamp (um
    # auto-update entre a assinatura e a verificacao nao a invalida).
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
        "## Review record - re-pass do CANDIDATO v1.4.2 (advisory input)",
        "",
        "- Contexto: GA v1.4.2 = promocao da v1.4.2-rc.1 depois do hold ADR-103.",
        "  A rodada 1 do re-pass da rc.1 revisou o candidato 9b5b1b40 (4/4",
        "  GO-WITH-CONDITIONS; veredito assinado em 9a486d29, o commit da tag).",
        "  Release expressa sobre o GA v1.4.1 (PLAN-193): Claude Opus 5.5 como",
        "  modelo de sessao fixado, a politica de esforco, o piso de versao do",
        "  Claude Code, o adapter live, a cura do FN-04, a publicacao do",
        "  relaunch --out, o re-pin do Codex e tres CLIs novas. O re-pass do GA",
        "  cobre o delta v1.4.1..candidato em %d partes por raio de dano ao" % NPARTS,
        "  adotante, a mesma particao da rc.1; o que fica de fora esta",
        "  DECLARADO em %s/repass-ga/README-ga.md — nao omitido." % PLAN,
        "- Nada foi curado entre a rc.1 e o GA: o que o envelope assinado da",
        "  v1.4.2-rc.1 declarou aberto segue known-open, RE-DECLARADO nas",
        "  condicoes do GA (material assinado) — o anexo P1 do envelope da",
        "  v1.4.0, sem versao prometida para a cura (PLAN-193 OQ-3), e o que o",
        "  envelope do GA v1.4.1 declarou aberto, fora o que a rc.1 declarou",
        "  curado: o CASO da condicao 23 daquele envelope (a CLASSE dela segue",
        "  declarada, nao provada esgotada) e a escrita e a limpeza do",
        "  relaunch --out da condicao 14, para o NOME do destino.",
        "- O anexo assinado dos vereditos da rc.1 segue ABERTO, declarado pela",
        "  forma nas condicoes do GA — tres P1: uma CLI que, apontada para outro",
        "  checkout, importa e executa codigo Python dele; comando de cerimonia",
        "  recomendado com caminho sem aspas (injecao de shell por nome de",
        "  arquivo); uma verificacao de pacote que confere o cabecalho e nao o",
        "  destino que o extrator real normaliza (colisao de payload). Nenhum P2",
        "  daqueles vereditos e curado no GA (o da documentacao que pede",
        "  --pin v1.4.2 descrevia a falha enquanto a tag do GA nao existe).",
        "- A PROVENANCE diz, por parte, se algum arquivo da pathspec mudou desde o",
        "  candidato da rc.1. Se, entre a tag da rc.1 e o HEAD, mudar caminho fora",
        "  de CLAUDE.md e dos planos numerados, o OWNER-GA-CUT.sh recusa o corte;",
        "  sobre o candidato entra so o commit do veredito (este envelope, os",
        "  fields e a evidencia do re-pass).",
        "- Antes do codex, cada afirmacao sobre codigo das condicoes foi conferida",
        "  contra o candidato pela sonda do kit (probe-ga.txt, no MANIFEST). Este",
        "  gerador le o RELATORIO da sonda, alem da linha da PROVENANCE, e recusa",
        "  evidencia em que os dois nao digam juntos VERDE contra ESTE candidato:",
        "  nenhuma afirmacao falsa nem sem medida, cada verificacao da sonda do",
        "  kit numa linha OK exatamente uma vez (nenhuma ausente, repetida ou de",
        "  outro id, e o mapa de condicoes da sonda com esses mesmos ids), a",
        "  arvore do candidato, a projecao de tamanho de cada parte e a mesma",
        "  contagem de linhas OK.",
        "- tool_versions.claude_code e a versao do Claude Code CLI MEDIDA por",
        "  `claude --version` na maquina que gerou os fields; nao e o modelo.",
        "- Cada parte cita, dentro do proprio prompt, a revisao que aquele conteudo",
        "  ja teve, para que uma condicao possa nomear a cobertura em vez de tratar",
        "  o conteudo como inedito.",
        "- Reviewer: codex-cli na versao que o manifesto ADR-182 pina — o binario",
        "  global quando ele e o pinado, senao npx num cache proprio (a rota esta",
        "  na PROVENANCE) — com o payload nativo VERIFICADO contra o manifesto",
        "  antes de qualquer revisao; versao, triple e sha256 do payload estao em",
        "  tool_versions e sao re-validados por este gerador.",
        "- Pipeline: prompt + diff atraves do redator ADR-114 como UM pipeline;",
        "  worktree DETACHED no SHA candidato (a tag v1.4.2 ainda nao existe).",
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
        "- delta_manifest_sha256 pina MANIFEST-ga.sha256 (%d entradas, runner e"
        % (NPARTS * 5 + 5),
        "  sonda inclusos). Payloads raw NAO commitados; pins em PROVENANCE-ga.md.",
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
