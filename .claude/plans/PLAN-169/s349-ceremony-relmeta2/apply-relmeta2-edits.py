#!/usr/bin/env python3
"""Material VERSIONADO da cerimonia rel-meta-2 (PLAN-169).

POR QUE ELA EXISTE. O land da wave-relmeta (511fdc2) poe
`TARGET_BASE="1.4.0"` no driver, mas o `VERSION` vivo continua `1.3.0`.
Essa janela e ESTRUTURALMENTE vermelha: `test_release_bump_sites.py` monta
os fixtures a partir do VERSION vivo e exige que o driver mire a MESMA
base. Nove testes reprovaram no Validate de 511fdc2 (matriz 3.9 e 3.12).
Um decimo, `test_driver_derives_every_version_string_from_target_base`,
reprovou por outro motivo: um literal `1.4.0` sobrou num COMENTARIO do
bloco PER-RELEASE.

O QUE ESTA CERIMONIA FAZ, e por que tudo tem de viajar junto:

  A. tira o literal de versao do comentario do bloco PER-RELEASE, e
     RE-RODA o predicado do proprio teste sobre o resultado (auto-checagem:
     um segundo literal que eu nao tenha visto aborta aqui).
  B. escreve os SITIOS DE VERSAO pelo ESCRITOR UNICO
     (`_release_bump_sites.py bump --target <TARGET_BASE> --restamp`),
     exatamente como `release.sh bump` os escreveria — nunca por regex
     proprio. Depois disso `release.sh bump` e NO-OP e `preflight` passa.
  C. regenera os manifestos de plugin pelo gerador
     (`scripts/build-plugin.py --write-manifests`), que e o unico dono
     deles.
  D. re-pina o sha de `release.sh` no manifesto ADR-192 DEPOIS de A.

A e D so sao verdadeiras juntas (o manifesto e canonico); B e C so sao
verdadeiras junto de A (a janela vermelha e exatamente TARGET_BASE sem os
sitios). Logo: uma assinatura, um patch.

  python3 apply-relmeta2-edits.py --repo <root> --today YYYY-MM-DD [--check]

`--check` nao escreve: valida as ancoras e imprime as derivacoes.
stdlib only, Python >= 3.9.

NOTA SOBRE O VALOR DE `VERSION`. Ele recebe o semver NU (`1.4.0`), nao
`1.4.0-rc.1`. Nao e escolha minha: e o contrato do proprio driver — "VERSION
carries the BARE semver: the RC lives only in the tag name" — e a fase `tag`
compara `VERSION` com `TARGET_BASE`, nao com a tag. Um `-rc.1` ali casaria
nenhum dos padroes `\\d+.\\d+.\\d+` da tabela de sitios e o gate de drift
passaria vacuo.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import subprocess
import sys
from typing import List

RELEASE_SH = ".claude/scripts/local/release.sh"
MANIFEST = ".claude/governance/gate-scripts-manifest.txt"
BUMP_SITES = ".claude/scripts/local/_release_bump_sites.py"
BUILD_PLUGIN = "scripts/build-plugin.py"
TEST_SRC = ".claude/scripts/tests/test_release_bump_sites.py"
ADR_README = ".claude/adr/README.md"
ADR_DIR = ".claude/adr"
CHANGELOG = "CHANGELOG.md"
TEST_TARGET = ".claude/scripts/tests/test_release_bump_sites.py"
PAYLOAD_DIR = "payload"
STAMP_VERSION = "1.4.0"

# O comentario ofensor, tal como landou em 511fdc2, e a sua substituicao SEM
# literal de versao. O teste proibe QUALQUER `\d+.\d+.\d+` fora da linha
# `TARGET_BASE=`, e um comentario nao e excecao.
OLD_COMMENT = ("# O tag vale pelo TREM INTEIRO do CHANGELOG [1.4.0], nunca "
               "pelo plano\n")
NEW_COMMENT = ("# O tag vale pelo TREM INTEIRO da entrada do CHANGELOG desta "
               "versao,\n"
               "# nunca pelo plano\n")


def die(msg: str) -> None:
    sys.stderr.write("FATAL: %s\n" % msg)
    raise SystemExit(2)


def run(args: List[str], cwd: pathlib.Path, what: str) -> str:
    proc = subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    if proc.returncode != 0:
        die("%s rc=%d:\n%s" % (what, proc.returncode, proc.stdout.strip()))
    return proc.stdout


def semver_rx_from_test(repo: pathlib.Path) -> "re.Pattern":
    """O regex vem do MODULO DE TESTE, nunca reescrito de memoria.

    Reescreve-lo aqui criaria um segundo oraculo que envelhece sozinho — a
    classe exata que este repositorio ja pagou varias vezes.
    """
    t = (repo / TEST_SRC).read_text(encoding="utf-8")
    m = re.search(r"(?m)^SEMVER_RX = re\.compile\((r?[\"'].+?[\"'])\)\s*$", t)
    if not m:
        die("nao achei SEMVER_RX em %s — o teste mudou de forma" % TEST_SRC)
    try:
        return re.compile(eval(m.group(1)))  # literal de string do proprio teste
    except Exception as exc:
        die("SEMVER_RX ilegivel: %s" % exc)


def version_literal_offenders(text: str, rx: "re.Pattern") -> List[str]:
    """Espelho EXATO do predicado de
    `test_driver_derives_every_version_string_from_target_base`."""
    m = re.search(r'(?m)^TARGET_BASE="(\d+\.\d+\.\d+)"$', text)
    if not m:
        die("release.sh sem atribuicao bare-semver de TARGET_BASE")
    target = m.group(1)
    out = []
    for num, line in enumerate(text.splitlines(), 1):
        if line.strip() == 'TARGET_BASE="%s"' % target:
            continue
        for hit in rx.findall(line):
            if re.search(r"v%s-rc\.\d+" % re.escape(hit), line):
                continue
            out.append("%d: %s" % (num, line.strip()))
    return out


def target_base(text: str) -> str:
    m = re.search(r'(?m)^TARGET_BASE="(\d+\.\d+\.\d+)"$', text)
    if not m:
        die("release.sh sem TARGET_BASE")
    return m.group(1)


def edit_manifest(text: str, new_sha: str) -> str:
    lines = text.splitlines(True)
    hits = [k for k, ln in enumerate(lines)
            if ln.rstrip("\n").endswith("  " + RELEASE_SH)]
    if len(hits) != 1:
        die("manifesto ADR-192 com %d linhas para %s (exigido: 1)"
            % (len(hits), RELEASE_SH))
    lines[hits[0]] = "%s  %s\n" % (new_sha, RELEASE_SH)
    return "".join(lines)


# ---------------------------------------------------------------------------
# Edicao E — o indice de ADRs: carimbo + a nota de staleness FALSA.
#
# `.claude/adr/README.md` e CANONICO (o oraculo responde 1; o path esta
# nomeado no bloco de guarda de ADRs do check_canonical_edit.py). Por isso ele
# viaja no MESMO patch assinado, nunca num land livre.
#
# Duas mudancas, e so estas duas:
#   1. o carimbo `last-reviewed` vai para a data e a versao desta release. O
#      formato vem do STAMP_RE do proprio checker, lido do arquivo — nao
#      inventado.
#   2. a nota de staleness do indice e FALSA e vira verdadeira. Ela afirma que
#      as linhas ADR-157..ADR-181 nao estao listadas; a medicao diz o
#      contrario, e este script REFAZ a medicao antes de escrever, para nao
#      trocar uma afirmacao falsa por outra.
# ---------------------------------------------------------------------------
OLD_NOTE_HEAD = "> Index staleness note (pre-existing, PLAN-163 T5.2): rows ADR-157"


def _stamp_rx(repo: pathlib.Path) -> "re.Pattern":
    """O regex do carimbo vem do CHECKER, nunca reescrito de memoria."""
    src = (repo / ".claude/scripts/check-canonical-doc-freshness.py").read_text(
        encoding="utf-8")
    m = re.search(r"STAMP_RE = re\.compile\(\s*\n?\s*(r\"[^\"]+\")\s*\n?\s*\)",
                  src)
    if not m:
        die("nao achei STAMP_RE em check-canonical-doc-freshness.py")
    return re.compile(eval(m.group(1)))


def measure_adr_index(repo: pathlib.Path, text: str):
    """Refaz a medicao que a nota afirma. Devolve (arquivos, ids, ausentes)."""
    adr = repo / ADR_DIR
    files = sorted(adr.glob("ADR-*.md"))
    disk_ids = sorted({f.name[4:7] for f in files})
    cited = (set(re.findall(r"\[ADR-(\d{3})\]\(", text))
             | set(re.findall(r"\|\s*ADR-(\d{3})\s*\|", text))
             | set(re.findall(r"\bADR-(\d{3})\.md", text)))
    missing = sorted(set(disk_ids) - cited)
    return len(files), len(disk_ids), missing


def edit_adr_readme(repo: pathlib.Path, today: str) -> str:
    p = repo / ADR_README
    if p.is_symlink() or not p.is_file():
        die("%s nao e arquivo regular" % ADR_README)
    text = p.read_text(encoding="utf-8")

    n_files, n_ids, missing = measure_adr_index(repo, text)
    if missing:
        die("a nota de staleness NAO e falsa: %d id(s) no disco sem linha no "
            "indice (%s) — corrija o indice, nao a nota"
            % (len(missing), ", ".join(missing[:8])))

    rx = _stamp_rx(repo)
    hits = list(rx.finditer(text))
    if len(hits) != 1:
        die("%s tem %d carimbos last-reviewed (exigido: 1)"
            % (ADR_README, len(hits)))
    new_stamp = "<!-- last-reviewed: %s v%s -->" % (today, STAMP_VERSION)
    text = text[:hits[0].start()] + new_stamp + text[hits[0].end():]

    i = text.find(OLD_NOTE_HEAD)
    if i < 0:
        die("nao achei a nota de staleness do indice em %s" % ADR_README)
    j = text.find("\n\n", i)
    if j < 0:
        die("nao achei o fim do bloco da nota")
    new_note = (
        "> Index note (re-measured %s, cerimonia rel-meta-2): a nota anterior\n"
        "> afirmava que as linhas ADR-157..ADR-181 nao estavam listadas. A\n"
        "> medicao diz o contrario: **%d arquivos `ADR-*.md` no disco, %d ids\n"
        "> distintos** (a diferenca sao as colisoes de id documentadas acima),\n"
        "> e **todo id em disco aparece no indice** — o conjunto de ausentes e\n"
        "> vazio. A afirmacao de atraso era, ela propria, o que estava\n"
        "> desatualizado."
        % (today, n_files, n_ids)
    )
    text = text[:i] + new_note + text[j:]

    # pos-condicao: o carimbo novo tem de casar o regex do CHECKER
    m2 = list(rx.finditer(text))
    if len(m2) != 1 or m2[0].group(0) != new_stamp:
        die("o carimbo escrito nao casa o STAMP_RE do checker")
    if OLD_NOTE_HEAD in text:
        die("a nota falsa sobreviveu a substituicao")
    return text


# ---------------------------------------------------------------------------
# Edicoes F e G — os dois arquivos cujo conteudo novo e PROSA/CODIGO revisado,
# nao uma transformacao derivavel de uma fonte mecanica.
#
# `test_release_bump_sites.py` (a suite do driver, com o mundo sintetico
# derivado) e `SUPPORT.md` (relido pelo pacote de docs) viajam como PAYLOAD ao
# lado deste script, em `s349-ceremony-relmeta2/payload/`. O script os copia e
# verifica o sha256 de cada um contra `payload/PAYLOAD.sha256`.
#
# Por que payload e nao transformacao: uma cadeia de ~20 substituicoes de
# string embutida aqui seria ilegivel para quem assina, e frageis contra
# qualquer reformatacao do alvo. Um arquivo inteiro, com o hash conferido,
# e o que o Owner consegue LER antes de assinar — e continua fazendo
# `HEAD + script == patch` valer byte a byte, que e o que o V1 do LAND prova.
# ---------------------------------------------------------------------------
def install_payload(repo: pathlib.Path, rel_target: str, payload_name: str) -> None:
    # O payload resolve de JUNTO DO SCRIPT, nunca do repo-alvo: o V1 do LAND
    # roda este derivador contra um worktree LIMPO do HEAD, onde o material da
    # cerimonia ainda nao existe. Script e payload viajam juntos, e e isso que
    # faz `HEAD + script == patch` ser verdade tambem naquele worktree.
    src = pathlib.Path(__file__).resolve().parent / PAYLOAD_DIR / payload_name
    if src.is_symlink() or not src.is_file():
        die("payload ausente ou nao-regular: %s" % src)
    man = src.parent / "PAYLOAD.sha256"
    if not man.is_file():
        die("payload/PAYLOAD.sha256 ausente")
    want = None
    for line in man.read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", 1)
        if len(parts) == 2 and parts[1].strip() == payload_name:
            want = parts[0].strip()
    if not want:
        die("PAYLOAD.sha256 sem linha para %s" % payload_name)
    got = hashlib.sha256(src.read_bytes()).hexdigest()
    if got != want:
        die("payload %s: sha256 %s != %s do manifesto" % (payload_name, got, want))
    dst = repo / rel_target
    if dst.is_symlink() or not dst.is_file():
        die("alvo do payload nao e arquivo regular: %s" % dst)
    dst.write_bytes(src.read_bytes())


# ---------------------------------------------------------------------------
# Pre-condicao do CHANGELOG — CONFERIDA, nunca escrita.
#
# Esta cerimonia poe VERSION e os sitios em TARGET_BASE, e o `preflight` do
# corte exige `^## [TARGET_BASE]` no CHANGELOG. A seccao veio de um pacote de
# docs; aqui ela e so verificada. Sem esta checagem a falha so apareceria no
# corte, e nao na cerimonia — que e onde da para consertar sem pressa.
# ---------------------------------------------------------------------------
def assert_changelog_ready(repo: pathlib.Path, base: str) -> None:
    p = repo / CHANGELOG
    if p.is_symlink() or not p.is_file():
        die("%s nao e arquivo regular" % CHANGELOG)
    text = p.read_text(encoding="utf-8")
    secs = re.findall(r"(?m)^## \[%s\]" % re.escape(base), text)
    if len(secs) == 0:
        die("CHANGELOG sem a seccao [%s]. Esta cerimonia NAO escreve o "
            "CHANGELOG — ela exige que o pacote de docs da release ja o tenha "
            "landado, porque o preflight do corte procura essa seccao." % base)
    if len(secs) > 1:
        die("CHANGELOG com %d seccoes [%s] — ambiguidade, nao aprovacao"
            % (len(secs), base))
    body_at = re.search(r"(?m)^## \[", text)
    preamble = text[:body_at.start()] if body_at else text
    hdr = re.search(
        r"v([\d.]+): (\d+) skills, (\d+) slash commands, (\d+) ADRs, "
        r"(\d+) `_lib` modules\)", preamble)
    if not hdr:
        die("CHANGELOG sem o claim de contagens no preambulo (a regra "
            "changelog/header do verify-counts exige exatamente um)")
    if hdr.group(1) != base:
        die("o claim de contagens do preambulo diz v%s, esperado v%s"
            % (hdr.group(1), base))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--today", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    repo = pathlib.Path(a.repo).resolve()
    if not (repo / ".git").exists():
        die("%s nao parece a raiz de um repositorio" % repo)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.today):
        die("--today deve ser YYYY-MM-DD")

    rp = repo / RELEASE_SH
    mp = repo / MANIFEST
    adr_new = edit_adr_readme(repo, a.today)
    for p in (rp, mp, repo / BUMP_SITES, repo / BUILD_PLUGIN, repo / TEST_SRC):
        if p.is_symlink() or not p.is_file():
            die("alvo/ferramenta nao e arquivo regular: %s" % p)

    rx = semver_rx_from_test(repo)
    assert_changelog_ready(repo, target_base(
        (repo / RELEASE_SH).read_text(encoding="utf-8")))
    rel_old = rp.read_text(encoding="utf-8")
    base = target_base(rel_old)

    # --- A. comentario sem literal de versao -------------------------------
    if OLD_COMMENT in rel_old:
        rel_new = rel_old.replace(OLD_COMMENT, NEW_COMMENT, 1)
    elif NEW_COMMENT in rel_old:
        rel_new = rel_old            # idempotente: ja aplicado
    else:
        die("nao achei o comentario ofensor nem a sua substituicao em %s — "
            "o bloco PER-RELEASE mudou de forma" % RELEASE_SH)

    # AUTO-CHECAGEM: rodar o predicado do teste sobre o RESULTADO. Se sobrou
    # qualquer outro literal, aborta nomeando a linha — nunca "provavelmente
    # so tinha um".
    left = version_literal_offenders(rel_new, rx)
    if left:
        die("apos a edicao A ainda ha literal(is) de versao em %s:\n  %s"
            % (RELEASE_SH, "\n  ".join(left)))

    rel_sha = hashlib.sha256(rel_new.encode("utf-8")).hexdigest()
    man_new = edit_manifest(mp.read_text(encoding="utf-8"), rel_sha)

    if a.check:
        sys.stdout.write(
            "CHANGELOG: pre-condicao CONFERIDA (seccao + contagens)\n"
            "adr/README: carimbo -> %s v%s; nota do indice re-medida\n"
            % (a.today, STAMP_VERSION))
        sys.stdout.write(
            "target_base: %s\ncomentario ofensor: %s\n"
            "literais restantes: 0\nrelease.sh sha256 (pos-A): %s\n"
            "sitios de versao: NAO escritos (--check)\n"
            % (base, "presente" if OLD_COMMENT in rel_old else "ja curado",
               rel_sha))
        return 0

    rp.write_text(rel_new, encoding="utf-8")
    mp.write_text(man_new, encoding="utf-8")
    (repo / ADR_README).write_text(adr_new, encoding="utf-8")
    install_payload(repo, TEST_TARGET, "test_release_bump_sites.py")
    # SUPPORT.md saiu daqui: ele landou por conta propria em 39771db, com o
    # carimbo 2026-09-07 v1.4.0 ja no lugar. Manter uma copia no payload seria
    # um segundo original do mesmo arquivo, envelhecendo ao lado do vivo.
    on_disk = hashlib.sha256(rp.read_bytes()).hexdigest()
    if on_disk != rel_sha:
        die("sha de release.sh em disco != o gravado no manifesto")

    # --- B. sitios de versao pelo ESCRITOR UNICO ---------------------------
    run([sys.executable, BUMP_SITES, "bump", "--target", base,
         "--today", a.today, "--restamp", "--root", str(repo)],
        repo, "_release_bump_sites.py bump")

    # --- C. manifestos de plugin pelo GERADOR ------------------------------
    run([sys.executable, BUILD_PLUGIN, "--write-manifests"], repo,
        "build-plugin.py --write-manifests")
    run([sys.executable, BUILD_PLUGIN, "--check"], repo,
        "build-plugin.py --check")

    # --- pos-condicoes que o corte depende ---------------------------------
    ver = (repo / "VERSION").read_text(encoding="utf-8").strip()
    if ver != base:
        die("VERSION ficou %r, esperado %r (o driver compara VERSION com "
            "TARGET_BASE na fase tag)" % (ver, base))
    left = version_literal_offenders(
        rp.read_text(encoding="utf-8"), rx)
    if left:
        die("literal de versao reapareceu em %s:\n  %s"
            % (RELEASE_SH, "\n  ".join(left)))

    # pos-condicao final: o gate de frescor tem de ficar VERDE.
    proc = subprocess.run(
        [sys.executable, ".claude/scripts/check-canonical-doc-freshness.py"],
        cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True)
    if proc.returncode != 0:
        die("gate de frescor ainda VERMELHO apos a edicao E:\n%s"
            % proc.stdout.strip())
    sys.stdout.write(
        "CHANGELOG: pre-condicao CONFERIDA (nao escrito)\n"
        "adr/README: carimbo %s v%s + nota do indice re-medida\n"
        "frescor de docs canonicos: rc 0\n" % (a.today, STAMP_VERSION))
    sys.stdout.write(
        "target_base: %s\nVERSION: %s\nrelease.sh sha256: %s\n"
        "sitios de versao: escritos pelo escritor unico (--restamp)\n"
        "manifestos de plugin: regenerados pelo gerador\n"
        "payload instalado (sha256 conferido): a suite do driver\n"
        % (base, ver, rel_sha))
    return 0


if __name__ == "__main__":
    sys.exit(main())
