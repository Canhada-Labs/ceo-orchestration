#!/usr/bin/env python3
"""Material VERSIONADO da cerimonia relmeta-141 (PLAN-192, corte da v1.4.1-rc.1).

Aplica as TRES edicoes que destravam `release.sh` para a v1.4.1:

  1. o bloco PER-RELEASE do driver (TARGET_BASE, titulo, escopo, headline);
  2. o sha256 do driver no manifesto ADR-192 (canonico);
  3. o re-pin CONSCIENTE do teste que fixa o escopo da anotacao da tag.

Derivado de `PLAN-169/s349-ceremony-relmeta/apply-relmeta-edits.py`. O que muda
de verdade: a faixa e `v1.4.0..HEAD`; um conjunto VAZIO de ADRs tocados e um
resultado legitimo (e escrito como tal, nunca como faixa); o teste de escopo
viaja no MESMO patch, porque driver e teste so sao verdadeiros juntos.

  python3 apply-relmeta141-edits.py --repo <root> [--check]

`--check` nao escreve: imprime as derivacoes e valida que TODAS as ancoras
batem. stdlib only, Python >= 3.9.

O CHANGELOG NAO E ALVO DE ESCRITA: a secao `## [1.4.1]` e o rotulo `v1.4.1` do
preambulo sao PRE-CONDICAO (`assert_changelog_ready`).

POR QUE ISTO E UMA CERIMONIA. `.claude/governance/gate-scripts-manifest.txt` e
CANONICO, e `.claude/scripts/local/release.sh` e MEMBRO dele: mudar um byte do
driver sem re-pinar o sha derruba os workflows que conferem o manifesto. E o
titulo, o escopo e a headline vao para DENTRO da anotacao ASSINADA da tag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Dict, List, Tuple

EDIT_COUNT_DECLARED = 3

RELEASE_SH = ".claude/scripts/local/release.sh"
MANIFEST = ".claude/governance/gate-scripts-manifest.txt"
SCOPE_TEST = ".claude/scripts/tests/test_release_bump_sites.py"
CHANGELOG = "CHANGELOG.md"

BASE_TAG = "v1.4.0"
PREV_BASE = "1.4.0"
TARGET_BASE = "1.4.1"

RELEASE_TITLE = "Workflow launch ledger + resume guard (out-of-order patch)"

# Vai para DENTRO da anotacao assinada da tag. ASCII, sem crase, sem cifrao, e
# toda versao escrita com o prefixo v (um semver NU aqui reprovaria o teste
# test_driver_derives_every_version_string_from_target_base).
RELEASE_HEADLINE = """Patch fora de ordem para quem roda pipelines autonomos longos com a
tool Workflow. Todo lancamento passa a ser registrado ANTES do
despacho (sha256 e copia dos bytes do script, args literais, o run de
retomada, a revisao do codigo), e uma retomada sobre args DIFERENTES
do lancamento registrado e recusada em vez de seguir. A chamada exata
volta do ledger por ceo-launches.py relaunch, em vez de ser
reconstruida de memoria. O guard pode BLOQUEAR e o perfil user o
mantem; as saidas sao CEO_WORKFLOW_RESUME_GUARD=0 (so aviso),
CEO_WORKFLOW_LEDGER=0 (desligado) e a declaracao na propria chamada.

Correcao: relaunch --out entregava uma copia truncada com sucesso numa
escrita curta; agora entrega o arquivo inteiro ou nenhum arquivo.

Cinco CLIs de recuperacao e aprovacao chegam sem hook que as imponha.

A parte honesta: o envelope assinado da v1.4.0 prometia curar NESTA
versao os achados P1 do seu anexo. Esta release NAO os cura: e um
patch urgente, por decisao do Owner, e o anexo segue aberto, sem
mudanca, com a cura re-alvejada para a v1.4.2. Sem afirmacao de
velocidade — governanca e auditabilidade, como sempre."""


def die(msg: str) -> None:
    sys.stderr.write("FATAL: %s\n" % msg)
    raise SystemExit(2)


def run(repo: pathlib.Path, *args: str) -> str:
    """git com rc CONFERIDO: um produtor que morre nunca vira string vazia."""
    proc = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if proc.returncode != 0:
        die("git %s rc=%d: %s" % (" ".join(args), proc.returncode,
                                  proc.stderr.strip()))
    return proc.stdout


def derive_train(repo: pathlib.Path) -> Tuple[List[str], List[str]]:
    """Planos citados nos assuntos de commit + ADRs tocados na faixa.

    Um conjunto VAZIO de ADRs e legitimo num patch e e escrito como «nenhum».
    Um conjunto vazio de PLANOS nao e: a faixa estaria errada.
    """
    log = run(repo, "log", "--format=%s", "%s..HEAD" % BASE_TAG)
    plans = sorted(set(re.findall(r"PLAN-\d{3}", log)))
    names = run(repo, "diff", "--name-only", "%s..HEAD" % BASE_TAG,
                "--", ".claude/adr/")
    adrs = sorted(set(re.findall(r"ADR-\d{3}", names)))
    if not plans:
        die("nenhum PLAN-NNN na faixa %s..HEAD — faixa errada?" % BASE_TAG)
    return plans, adrs


def scope_string(plans: List[str], adrs: List[str]) -> str:
    # Os ADRs sao LISTADOS, nunca escritos como faixa `primeiro -> ultimo`.
    return "%s (ADRs tocados: %s)" % (
        " / ".join(plans), " ".join(adrs) if adrs else "nenhum")


def derive_counts(repo: pathlib.Path) -> Dict[str, int]:
    """Contagens VIVAS pelo mesmo oraculo que o gate usa."""
    proc = subprocess.run(
        ["bash", ".claude/scripts/local/verify-counts.sh", "--json",
         "--no-tests"],
        cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True)
    try:
        d = json.loads(proc.stdout)
    except Exception:
        die("verify-counts --json ilegivel (rc=%d): %r"
            % (proc.returncode, proc.stdout[:400]))
    viol = d.get("violations") or []
    if viol:
        die("verify-counts reporta %d drift(s) — corrija ANTES da cerimonia:\n  %s"
            % (len(viol), "\n  ".join(str(v) for v in viol[:6])))
    live = d.get("live") or {}
    out = {}
    for k in ("skills", "commands", "adrs", "lib"):
        v = live.get(k)
        if not isinstance(v, int):
            die("verify-counts sem contagem inteira para %r" % k)
        out[k] = v
    return out


def build_per_release_block(scope: str) -> str:
    return (
        'TARGET_BASE="%s"\n'
        'RELEASE_TITLE="%s"\n'
        '# O tag vale pelo TREM INTEIRO da entrada do CHANGELOG desta versao,\n'
        '# nunca pelo plano\n'
        '# mais novo. Este bloco e DERIVADO por\n'
        '# .claude/plans/PLAN-192/relmeta/apply-relmeta141-edits.py\n'
        '# a partir de `git log %s..HEAD` (planos CITADOS nos assuntos de\n'
        '# commit da faixa) e do conjunto de ADRs tocados na mesma faixa —\n'
        '# nao digite nada aqui a mao.\n'
        'RELEASE_SCOPE="%s"\n'
        'RELEASE_HEADLINE="%s"\n'
        % (TARGET_BASE, RELEASE_TITLE, BASE_TAG, scope, RELEASE_HEADLINE)
    )


def assert_block_is_inert(block: str) -> None:
    """O bloco PER-RELEASE vira quatro strings de ASPAS DUPLAS em bash.

    Dentro delas, crase e substituicao de comando, ``$NOME`` e expansao, e uma
    aspa dupla FECHA a string. Qualquer um dos tres faria o driver executar ou
    truncar prosa que vai para a anotacao ASSINADA da tag.
    """
    bad = []
    lines = block.splitlines()
    headline_at = next(
        (k for k, ln in enumerate(lines) if ln.startswith('RELEASE_HEADLINE="')),
        len(lines))
    for lineno, line in enumerate(lines, 1):
        if lineno - 1 < headline_at and line.lstrip().startswith("#"):
            continue
        if "`" in line:
            bad.append("linha %d: crase (substituicao de comando)" % lineno)
        for m in re.finditer(r"(?<!\\)\$", line):
            bad.append("linha %d, col %d: cifrao nao escapado"
                       % (lineno, m.start() + 1))
        if "\\" in line:
            bad.append("linha %d: barra invertida (escape em aspas duplas)" % lineno)
    for name, value in (("RELEASE_TITLE", RELEASE_TITLE),
                        ("RELEASE_HEADLINE", RELEASE_HEADLINE)):
        if '"' in value:
            bad.append("%s contem aspa dupla — fecharia a string do bash" % name)
        try:
            value.encode("ascii")
        except UnicodeError:
            # o travessao da ultima frase e o unico nao-ASCII admitido (o
            # bloco da v1.4.0 ja o carrega, na mesma frase)
            stripped = value.replace("—", "")
            try:
                stripped.encode("ascii")
            except UnicodeError:
                bad.append("%s contem nao-ASCII alem do travessao" % name)
    if bad:
        die("bloco PER-RELEASE nao e inerte em aspas duplas:\n  %s"
            % "\n  ".join(bad))


def assert_no_bare_semver(block: str) -> None:
    """Espelha test_driver_derives_every_version_string_from_target_base."""
    rx = re.compile(r"\b\d+\.\d+\.\d+\b")
    bad = []
    for lineno, line in enumerate(block.splitlines(), 1):
        if line.strip() == 'TARGET_BASE="%s"' % TARGET_BASE:
            continue
        for hit in rx.findall(line):
            if re.search(r"v%s-rc\.\d+" % re.escape(hit), line):
                continue
            bad.append("linha %d: semver nu %s" % (lineno, hit))
    if bad:
        die("bloco PER-RELEASE com literal de versao nao derivado:\n  %s"
            % "\n  ".join(bad))


def edit_release_sh(text: str, block: str) -> str:
    """Substitui o bloco PER-RELEASE inteiro, ancorado nas duas pontas."""
    start = 'TARGET_BASE="%s"\n' % PREV_BASE
    end = '\nRC_NUM="1"\n'
    if text.count(start) != 1:
        die("ancora inicial do bloco PER-RELEASE ausente ou nao unica em %s"
            % RELEASE_SH)
    i = text.find(start)
    j = text.find(end, i)
    if j < 0:
        die("ancora final (RC_NUM) ausente depois do bloco PER-RELEASE")
    return text[:i] + block + text[j + 1:]


def edit_manifest(text: str, new_sha: str) -> str:
    """Re-pin do sha de release.sh no manifesto ADR-192 (linha unica)."""
    lines = text.splitlines(True)
    hits = [k for k, ln in enumerate(lines)
            if ln.rstrip("\n").endswith("  " + RELEASE_SH)]
    if len(hits) != 1:
        die("manifesto ADR-192 com %d linhas para %s (exigido: 1)"
            % (len(hits), RELEASE_SH))
    lines[hits[0]] = "%s  %s\n" % (new_sha, RELEASE_SH)
    return "".join(lines)


def _wrap_literal(scope: str, indent: str) -> str:
    """O escopo como literais adjacentes de no maximo ~70 colunas uteis."""
    words = scope.split(" ")
    chunks, cur = [], ""
    for w in words:
        cand = (cur + " " + w) if cur else w
        if len(cand) > 66 and cur:
            chunks.append(cur + " ")
            cur = w
        else:
            cur = cand
    chunks.append(cur)
    for c in chunks:
        if '"' in c or "\\" in c:
            die("escopo com aspa ou barra invertida — nao cabe num literal simples")
    return "\n".join('%s"%s"' % (indent, c) for c in chunks)


def edit_scope_test(text: str, old_scope: str, new_scope: str) -> str:
    """Re-pin CONSCIENTE do teste que fixa o escopo da anotacao.

    Ancora = o bloco `assert ( <literais> in proc.stdout )` que reconstitui
    EXATAMENTE o escopo anterior. O escopo anterior vira assercao NEGATIVA:
    nenhuma string da release passada pode sobreviver na anotacao.
    """
    rx = re.compile(
        r'    assert \(\n((?:        "[^"\n]*"\n?)+?) in proc\.stdout\n    \)\n')
    hits = []
    for m in rx.finditer(text):
        lit = "".join(re.findall(r'"([^"\n]*)"', m.group(1)))
        if lit == old_scope:
            hits.append(m)
    if len(hits) != 1:
        die("teste de escopo: %d blocos reconstituem o escopo anterior (exigido: 1)"
            % len(hits))
    m = hits[0]
    old_head = old_scope.split(" (ADRs")[0]
    first_three = " / ".join(old_head.split(" / ")[:3])
    new_block = (
        "    assert (\n%s in proc.stdout\n    )\n"
        "    # o trem da release ANTERIOR nao pode ter sobrevivido na anotacao\n"
        "    assert \"%s\" not in proc.stdout\n"
        % (_wrap_literal(new_scope, "        "), first_three))
    out = text[:m.start()] + new_block + text[m.end():]

    doc_old = ("    Trem %s (re-pinado na cerimonia rel-meta-2): o escopo passou a ser\n"
               % PREV_BASE)
    if out.count(doc_old) != 1:
        die("teste de escopo: ancora do docstring do trem anterior ausente ou nao unica")
    doc_new = (
        "    Trem %s (re-pinado na cerimonia relmeta-141, PLAN-192): derivado por\n"
        "    apply-relmeta141-edits.py de `git log %s..HEAD`; um conjunto VAZIO de\n"
        "    ADRs tocados e escrito como «nenhum», nunca omitido.\n"
        "\n" % (TARGET_BASE, BASE_TAG))
    return out.replace(doc_old, doc_new + doc_old, 1)


def current_scope(release_text: str) -> str:
    m = re.findall(r'(?m)^RELEASE_SCOPE="([^"\n]*)"$', release_text)
    if len(m) != 1:
        die("driver com %d linhas RELEASE_SCOPE de uma linha (exigido: 1)" % len(m))
    return m[0]


def assert_changelog_ready(text: str, counts: Dict[str, int]) -> None:
    """PRE-CONDICAO, nao edicao: o CHANGELOG da release ja tem de estar la."""
    body_at = re.search(r"(?m)^## \[", text)
    if not body_at:
        die("CHANGELOG sem nenhuma secao '## [' — arquivo errado?")
    secs = re.findall(r"(?m)^## \[%s\]" % re.escape(TARGET_BASE), text)
    if len(secs) != 1:
        die("CHANGELOG com %d secoes [%s] (exigido: exatamente 1). Esta cerimonia "
            "NAO escreve o CHANGELOG." % (len(secs), TARGET_BASE))
    if re.search(r"(?m)^## \[Unreleased\]", text):
        die("CHANGELOG ainda tem uma secao [Unreleased] — o que ela descreve "
            "entra ou nao nesta release?")
    preamble = text[:body_at.start()]
    hdr_rx = re.compile(
        r"v([\d.]+): (\d+) skills, (\d+) slash commands, (\d+) ADRs, "
        r"(\d+) `_lib` modules\)")
    ms = list(hdr_rx.finditer(preamble))
    if len(ms) != 1:
        die("CHANGELOG: %d claims de contagem no preambulo (exigido: 1)" % len(ms))
    m = ms[0]
    if m.group(1) != TARGET_BASE:
        die("o claim de contagens do preambulo diz v%s, esperado v%s"
            % (m.group(1), TARGET_BASE))
    got = {"skills": int(m.group(2)), "commands": int(m.group(3)),
           "adrs": int(m.group(4)), "lib": int(m.group(5))}
    bad = ["%s: preambulo=%d vivo=%d" % (k, got[k], counts[k])
           for k in ("skills", "commands", "adrs", "lib") if got[k] != counts[k]]
    if bad:
        die("claim de contagens do CHANGELOG defasado: %s" % "; ".join(bad))
    # A decisao do Owner (PLAN-192 OQ-1) tem de estar ESCRITA na entrada.
    sec = text[text.index("## [%s]" % TARGET_BASE):]
    nxt = re.search(r"(?m)^## \[", sec[4:])
    sec = sec[: nxt.start() + 4] if nxt else sec
    if "Known-open" not in sec or "re-targeted to 1.4.2" not in sec:
        die("a entrada [%s] do CHANGELOG nao declara o anexo da v1.4.0 como "
            "known-open re-alvejado para a 1.4.2 (PLAN-192 OQ-1)" % TARGET_BASE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    repo = pathlib.Path(a.repo).resolve()
    if not (repo / ".git").exists():
        die("%s nao parece a raiz de um repositorio" % repo)

    plans, adrs = derive_train(repo)
    counts = derive_counts(repo)
    scope = scope_string(plans, adrs)
    block = build_per_release_block(scope)
    assert_block_is_inert(block)
    assert_no_bare_semver(block)

    rp, cp, mp, tp = (repo / RELEASE_SH, repo / CHANGELOG, repo / MANIFEST,
                      repo / SCOPE_TEST)
    for p in (rp, cp, mp, tp):
        if p.is_symlink() or not p.is_file():
            die("alvo nao e arquivo regular: %s" % p)

    assert_changelog_ready(cp.read_text(encoding="utf-8"), counts)

    rel_old = rp.read_text(encoding="utf-8")
    old_scope = current_scope(rel_old)
    rel_new = edit_release_sh(rel_old, block)
    if current_scope(rel_new) != scope:
        die("o escopo gravado no driver nao e o derivado")
    rel_sha = hashlib.sha256(rel_new.encode("utf-8")).hexdigest()
    man_new = edit_manifest(mp.read_text(encoding="utf-8"), rel_sha)
    tst_new = edit_scope_test(tp.read_text(encoding="utf-8"), old_scope, scope)

    applied = 0
    if not a.check:
        rp.write_text(rel_new, encoding="utf-8")
        mp.write_text(man_new, encoding="utf-8")
        tp.write_text(tst_new, encoding="utf-8")
        applied = 3
        on_disk = hashlib.sha256(rp.read_bytes()).hexdigest()
        if on_disk != rel_sha:
            die("sha de release.sh em disco (%s) != o gravado no manifesto (%s)"
                % (on_disk, rel_sha))
        if applied != EDIT_COUNT_DECLARED:
            die("aplicadas %d edicoes, declaradas %d" % (applied, EDIT_COUNT_DECLARED))

    sys.stdout.write(
        "scope: %s\ncounts: %s\nrelease.sh sha256 (pos-edicao): %s\n"
        "edits: %d/%d (CHANGELOG: pre-condicao CONFERIDA, nao escrita)%s\n"
        % (scope, json.dumps(counts, sort_keys=True), rel_sha, applied,
           EDIT_COUNT_DECLARED, "  (--check: NADA escrito)" if a.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
