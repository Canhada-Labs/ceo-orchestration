#!/usr/bin/env python3
"""Material VERSIONADO da cerimonia rel-meta (PLAN-169, corte da v1.4.0-rc.1).

Aplica as DUAS edicoes que destravam `release.sh` para a v1.4.0, e
CONFERE uma terceira pre-condicao que outro pacote ja landou. O
`finalize-relmeta.sh` roda este script numa arvore limpa, deriva o patch
por `git diff` e reverte; o LAND prova `HEAD + este script == patch` byte
a byte. Nada aqui e digitado a partir de memoria: as contagens do
CHANGELOG saem de `verify-counts.sh --json` e o roster de planos/ADRs sai
do `git log`/`git diff` da faixa `v1.3.0..HEAD`.

  python3 apply-relmeta-edits.py --repo <root> [--check]

`--check` nao escreve: so imprime as derivacoes e valida que TODAS as
ancoras batem (uso do harness). stdlib only, Python >= 3.9.

O CHANGELOG NAO E ALVO DE ESCRITA. A secao `## [1.4.0]` e o rotulo
`as of v1.4.0` do preambulo foram landados pelo pacote de docs em
`e242544`; escrever de novo colidiria. Aqui eles sao PRE-CONDICAO:
`assert_changelog_ready()` exige exatamente uma secao, o rotulo na versao
alvo, e as quatro contagens do preambulo batendo o oraculo vivo. Um
CHANGELOG que nao chegou ainda e recusa nomeada, nunca uma escrita
silenciosa por cima do trabalho de outro pacote.

POR QUE ISTO E UMA CERIMONIA. `.claude/governance/gate-scripts-manifest.txt`
e CANONICO (o oraculo `check_canonical_edit.py --is-canonical` responde 1),
e `.claude/scripts/local/release.sh` e MEMBRO desse manifesto — o oraculo
responde 0 para ele, mas mudar um byte seu sem re-pinar o sha derruba os
4 workflows que conferem o manifesto. As duas metades so sao verdadeiras
juntas, logo viajam numa assinatura so.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

EDIT_COUNT_DECLARED = 2

RELEASE_SH = ".claude/scripts/local/release.sh"
MANIFEST = ".claude/governance/gate-scripts-manifest.txt"
CHANGELOG = "CHANGELOG.md"

BASE_TAG = "v1.3.0"
TARGET_BASE = "1.4.0"


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
    """Planos citados nos assuntos de commit + ADRs tocados na faixa."""
    log = run(repo, "log", "--format=%s", "%s..HEAD" % BASE_TAG)
    plans = sorted(set(re.findall(r"PLAN-\d{3}", log)))
    names = run(repo, "diff", "--name-only", "%s..HEAD" % BASE_TAG,
                "--", ".claude/adr/")
    adrs = sorted(set(re.findall(r"ADR-\d{3}", names)))
    if not plans:
        die("nenhum PLAN-NNN na faixa %s..HEAD — faixa errada?" % BASE_TAG)
    if not adrs:
        die("nenhum ADR-NNN tocado na faixa — faixa errada?")
    return plans, adrs


def derive_counts(repo: pathlib.Path) -> Dict[str, int]:
    """Contagens VIVAS pelo mesmo oraculo que o gate usa."""
    proc = subprocess.run(
        ["bash", ".claude/scripts/local/verify-counts.sh", "--json",
         "--no-tests"],
        cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True)
    # rc != 0 significa DRIFT; nesse caso o corte nao pode acontecer de
    # qualquer jeito — recusa nomeada, nunca contagem digitada a mao.
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


def build_per_release_block(plans: List[str], adrs: List[str]) -> str:
    # Os ADRs sao LISTADOS, nunca escritos como faixa `primeiro -> ultimo`:
    # a faixa afirmaria que tudo entre as pontas entrou, e o conjunto real e
    # esparso (ADR-001 foi EMENDADO, nao criado, nesta janela).
    scope = ("%s (ADRs tocados: %s)"
             % (" / ".join(plans), " ".join(adrs)))
    return (
        'TARGET_BASE="%s"\n'
        'RELEASE_TITLE="per-project audit family + compaction continuity + '
        'installer write-safety"\n'
        '# O tag vale pelo TREM INTEIRO do CHANGELOG [%s], nunca pelo plano\n'
        '# mais novo. Este bloco e DERIVADO por\n'
        '# .claude/plans/PLAN-169/s349-ceremony-relmeta/apply-relmeta-edits.py\n'
        '# a partir de `git log %s..HEAD` (planos CITADOS nos assuntos de\n'
        '# commit da faixa) e do conjunto de ADRs tocados na mesma faixa —\n'
        '# nao digite nada aqui a mao.\n'
        'RELEASE_SCOPE="%s"\n'
        # NENHUMA crase e NENHUM cifrao nao-escapado aqui dentro: o valor vive
        # numa string de aspas DUPLAS em bash, onde crase e substituicao de
        # comando e $NOME e expansao. O guard _assert_block_is_inert() abaixo
        # recusa o bloco se um deles reaparecer — foi assim que o V2 do LAND
        # pegou uma versao anterior desta prosa (shellcheck SC1073/SC1064).
        # RECONCILIADO com a entrada [1.4.0] do CHANGELOG (landada em
        # e242544): este texto vai para DENTRO da anotacao ASSINADA da tag,
        # entao tem de dizer o mesmo que o adotante le no changelog.
        # NENHUMA crase e NENHUM cifrao nao-escapado: o valor vive numa
        # string de aspas DUPLAS em bash, onde crase e substituicao de
        # comando e $NOME e expansao. assert_block_is_inert() recusa o bloco
        # se um deles reaparecer — foi assim que o V2 do LAND pegou uma
        # versao anterior desta prosa (shellcheck SC1073/SC1064).
        'RELEASE_HEADLINE="A correcao que mais importa para quem ja instalou:\n'
        'da v1.0.0 ate a v1.3.0 o upgrade NUNCA entregou as arvores docs/ e\n'
        '.github/ que a instalacao entrega. Quem instalou uma vez e so\n'
        'atualizou depois ficou com os arquivos originais para sempre, sem\n'
        'aviso. Agora as duas arvores sao entregues com hash-gate contra as\n'
        'geracoes git da FONTE: uma copia intacta de geracao anterior e\n'
        'substituida, e qualquer coisa que voce editou e PRESERVADA em voz\n'
        'alta. Uma tabela de rotas, tres leitores.\n'
        '\n'
        'Seguranca: o instalador nao escreve mais fora do diretorio que voce\n'
        'entrega a ele (destino que era symlink ou hardlink pendente), e um\n'
        'handle de GitHub com barra nao deixa mais o CODEOWNERS com zero\n'
        'bytes para sempre. Um predicado de confinamento, produtor e\n'
        'consumidor na mesma gramatica.\n'
        '\n'
        'Auditoria: sob o mesmo HOME, cadeias HMAC de projetos diferentes\n'
        'deixam de se entrelacar — cada projeto tem diretorio de estado,\n'
        'chave e salt proprios. O limite fica declarado, nao escondido: sob\n'
        'o mesmo UID um processo ainda le o diretorio e a chave do outro, e\n'
        'fechar isso exigiria UID separado.\n'
        '\n'
        'E a parte honesta: a continuidade de compaction que da nome a este\n'
        'trem so shipou depois de o primeiro desenho ser MEDIDO e nao\n'
        'entregar nada. Sem afirmacao de velocidade — governanca e\n'
        'auditabilidade, como sempre."\n'
        % (TARGET_BASE, TARGET_BASE, BASE_TAG, scope)
    )


def assert_block_is_inert(block: str) -> None:
    """O bloco PER-RELEASE vira quatro strings de ASPAS DUPLAS em bash.

    Dentro delas, crase e substituicao de comando e ``$NOME`` e expansao de
    variavel — as duas coisas fariam o driver EXECUTAR prosa e embutir o
    resultado no anotacao da tag ASSINADA. Uma versao anterior deste bloco
    carregava ``verify_chain()`` entre crases e o V2 do LAND a reprovou por
    shellcheck (SC1073/SC1064); este predicado fecha a classe na fonte, e
    nao no revisor.
    """
    bad = []
    # Comentarios de bash sao inertes — mas so ANTES da primeira string
    # multilinha. Depois que `RELEASE_HEADLINE="` abre, uma linha comecando
    # com `#` esta DENTRO da string, e ali crase volta a ser substituicao.
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
    if bad:
        die("bloco PER-RELEASE nao e inerte em aspas duplas:\n  %s"
            % "\n  ".join(bad))


def edit_release_sh(text: str, block: str) -> str:
    """Substitui o bloco PER-RELEASE inteiro, ancorado nas duas pontas."""
    start = 'TARGET_BASE="1.3.0"\n'
    end = '\nRC_NUM="1"\n'
    i = text.find(start)
    if i < 0:
        die("ancora inicial do bloco PER-RELEASE ausente em %s" % RELEASE_SH)
    j = text.find(end, i)
    if j < 0:
        die("ancora final (RC_NUM) ausente depois do bloco PER-RELEASE")
    if text.count(start) != 1:
        die("ancora inicial do bloco PER-RELEASE nao e unica")
    return text[:i] + block + text[j + 1:]


def assert_changelog_ready(text: str, counts: Dict[str, int]) -> None:
    """PRE-CONDICAO, nao edicao: o CHANGELOG da release ja tem de estar la.

    A secao `## [1.4.0]` e o rotulo `as of v1.4.0` do preambulo foram
    landados pelo pacote de docs (`e242544`). Esta cerimonia NAO os
    escreve — ela recusa seguir se eles nao estiverem presentes e
    consistentes, que e a unica coisa que o corte precisa saber.

    Tres perguntas, todas fail-CLOSED:
      1. existe EXATAMENTE uma secao `^## \[1.4.0\]`? (duas seriam
         ambiguidade; zero significa que o pacote de docs nao landou)
      2. o preambulo tem EXATAMENTE um claim de contagens, e ele diz
         `vX` na versao alvo? (a regra `changelog/header` do
         verify-counts exige um so, e o rotulo estar na versao errada e
         a afirmacao envelhecendo)
      3. as quatro contagens do claim batem o oraculo vivo?
    """
    body_at = re.search(r"(?m)^## \[", text)
    if not body_at:
        die("CHANGELOG sem nenhuma secao '## [' — arquivo errado?")

    secs = re.findall(r"(?m)^## \[%s\]" % re.escape(TARGET_BASE), text)
    if len(secs) == 0:
        die("CHANGELOG sem a secao [%s]. Esta cerimonia NAO escreve o "
            "CHANGELOG — ela exige que o pacote de docs da release ja o "
            "tenha landado. Rode o pacote de docs primeiro." % TARGET_BASE)
    if len(secs) > 1:
        die("CHANGELOG com %d secoes [%s] — ambiguidade, nao aprovacao"
            % (len(secs), TARGET_BASE))

    preamble = text[:body_at.start()]
    hdr_rx = re.compile(
        r"v([\d.]+): (\d+) skills, (\d+) slash commands, (\d+) ADRs, "
        r"(\d+) `_lib` modules\)")
    ms = list(hdr_rx.finditer(preamble))
    if len(ms) != 1:
        die("CHANGELOG: %d claims de contagem no preambulo (a regra "
            "changelog/header do verify-counts exige exatamente 1)" % len(ms))
    m = ms[0]
    if m.group(1) != TARGET_BASE:
        die("o claim de contagens do preambulo diz v%s, esperado v%s — o "
            "pacote de docs landou a secao mas nao re-rotulou o preambulo"
            % (m.group(1), TARGET_BASE))
    got = {
        "skills": int(m.group(2)), "commands": int(m.group(3)),
        "adrs": int(m.group(4)), "lib": int(m.group(5)),
    }
    bad = ["%s: preambulo=%d vivo=%d" % (k, got[k], counts[k])
           for k in ("skills", "commands", "adrs", "lib") if got[k] != counts[k]]
    if bad:
        die("claim de contagens do CHANGELOG defasado: %s" % "; ".join(bad))


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--today", default="")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    repo = pathlib.Path(a.repo).resolve()
    if not (repo / ".git").exists():
        die("%s nao parece a raiz de um repositorio" % repo)

    today = a.today or run(repo, "log", "-1", "--format=%cs").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
        die("--today deve ser YYYY-MM-DD (recebido %r)" % today)

    plans, adrs = derive_train(repo)
    counts = derive_counts(repo)
    block = build_per_release_block(plans, adrs)
    assert_block_is_inert(block)

    rp = repo / RELEASE_SH
    cp = repo / CHANGELOG
    mp = repo / MANIFEST
    for p in (rp, cp, mp):
        if p.is_symlink() or not p.is_file():
            die("alvo nao e arquivo regular: %s" % p)

    # Pre-condicao, conferida em --check E na aplicacao: nao escrevemos o
    # CHANGELOG, exigimos que ele ja esteja pronto.
    assert_changelog_ready(cp.read_text(encoding="utf-8"), counts)

    rel_new = edit_release_sh(rp.read_text(encoding="utf-8"), block)
    rel_sha = hashlib.sha256(rel_new.encode("utf-8")).hexdigest()
    man_new = edit_manifest(mp.read_text(encoding="utf-8"), rel_sha)

    applied = 0
    if not a.check:
        rp.write_text(rel_new, encoding="utf-8")
        mp.write_text(man_new, encoding="utf-8")
        applied = 2
        # Prova imediata: o sha gravado no manifesto e o do arquivo em disco.
        on_disk = hashlib.sha256(rp.read_bytes()).hexdigest()
        if on_disk != rel_sha:
            die("sha de release.sh em disco (%s) != o gravado no manifesto (%s)"
                % (on_disk, rel_sha))
        if applied != EDIT_COUNT_DECLARED:
            die("aplicadas %d edicoes, declaradas %d"
                % (applied, EDIT_COUNT_DECLARED))

    sys.stdout.write(
        "plans: %s\nadrs: %s..%s\ncounts: %s\n"
        "release.sh sha256 (pos-edicao): %s\nedits: %d/%d (CHANGELOG: pre-condicao CONFERIDA, nao escrita)%s\n"
        % (" ".join(plans), adrs[0], adrs[-1], json.dumps(counts, sort_keys=True),
           rel_sha, applied, EDIT_COUNT_DECLARED,
           "  (--check: NADA escrito)" if a.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
