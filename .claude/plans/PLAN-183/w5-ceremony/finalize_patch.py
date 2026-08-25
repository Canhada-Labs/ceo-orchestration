#!/usr/bin/env python3
"""finalize_patch.py — gera o patch assinavel da cerimonia W5 (PLAN-183, S327).

O que este script faz, e por que cada passo existe:

1. ``git add -N`` para TODO arquivo untracked da arvore-sombra.
   Sem isso ``git diff HEAD`` NAO enxerga arquivo novo e ele some do patch
   ASSINADO em silencio (medido: ``git diff HEAD`` puro devolve so o arquivo
   modificado; apos ``add -N`` aparece ``new file mode``). A W5 adiciona
   arquivos de teste novos, entao esta perna e obrigatoria — e tem controle
   positivo proprio em ``--self-test``.
2. Gera o patch com ``git diff HEAD --binary`` (staged + unstaged, relativo ao
   HEAD da sombra) e calcula o sha256.
3. DERIVA a lista de paths tocados com ``git apply --numstat`` rodado na arvore
   VIVA (modo checagem, nao aplica nada). Scope escrito a mao ja foi corrigido
   duas vezes neste plano e continuou incompleto nas duas.
4. Classifica cada path tocado:
     (a) canonico? — oraculo ``check_canonical_edit.py --is-canonical``;
     (b) membro do manifesto ADR-192 (``gate-scripts-manifest.txt``)?
   Membro tocado SEM o manifesto tocado no mesmo patch => RECUSA (a licao do
   ``verify-counts.sh`` na S326: o oraculo responde 0 para um membro, mas
   editar membro passa pela cerimonia e exige bump do sha no manifesto).
   Membro tocado COM manifesto tocado: confere na SOMBRA (que ja e a arvore
   pos-patch) que o sha declarado casa o conteudo do membro.
5. Escreve o bloco ``Scope:`` do sentinel (entre os marcadores HTML) e o
   ``Patch-sha256:`` do sentinel e do PROPOSED-PATCH.md a partir dos paths
   DERIVADOS.

Uso:
    python3 .claude/plans/PLAN-183/w5-ceremony/finalize_patch.py \\
        --shadow /caminho/da/sombra \\
        --out .claude/plans/PLAN-183/w5-ceremony/S327-W5-DELIVERY.patch

    python3 .claude/plans/PLAN-183/w5-ceremony/finalize_patch.py --self-test

Saidas: 0 = patch finalizado; 1 = recusa nomeada; 2 = erro de uso/infra.

Stdlib-only, Python >= 3.9 (sem PEP 604 em runtime, sem match).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

# Marcadores do sentinel — o parser do hook (check_canonical_edit.py, Tier 1)
# so le Scope DENTRO deles; um BEGIN sem END bem formado e fail-CLOSED la.
BEGIN_MARKER = "<!-- BEGIN SIGNED SCOPE -->"
END_MARKER = "<!-- END SIGNED SCOPE -->"

MANIFEST_REL = ".claude/governance/gate-scripts-manifest.txt"
ORACLE_REL = ".claude/hooks/check_canonical_edit.py"


class Refuse(Exception):
    """Recusa nomeada (exit 1). Nunca uma excecao anonima."""


def _run(cmd: List[str], cwd: Optional[str] = None, check: bool = True) -> str:
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=False
    )
    if check and proc.returncode != 0:
        raise Refuse(
            "comando falhou (rc=%d): %s\n  stdout: %s\n  stderr: %s"
            % (proc.returncode, " ".join(cmd), proc.stdout.strip(), proc.stderr.strip())
        )
    return proc.stdout


def _run_bytes(cmd: List[str], cwd: Optional[str] = None) -> bytes:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, check=False)
    if proc.returncode != 0:
        raise Refuse(
            "comando falhou (rc=%d): %s\n  stderr: %s"
            % (proc.returncode, " ".join(cmd), proc.stderr.decode("utf-8", "replace"))
        )
    return proc.stdout


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# 1 + 2 — intent-to-add e geracao do patch
# --------------------------------------------------------------------------
def untracked_paths(shadow: str) -> List[str]:
    """Untracked NAO ignorados da sombra (porcelain -z, rename aborta)."""
    raw = _run_bytes(["git", "-C", shadow, "status", "--porcelain=v1", "-z"])
    out: List[str] = []
    fields = raw.split(b"\x00")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry:
            continue
        xy = entry[:2].decode("utf-8", "replace")
        path = entry[3:].decode("utf-8", "surrogateescape")
        if "R" in xy or "C" in xy:
            # -z: a origem do rename vem no PROXIMO registro.
            i += 1
            raise Refuse(
                "rename/copia na arvore-sombra (%s -> %s): o Scope nao expressa "
                "rename; resolva na sombra antes de finalizar" % (xy, path)
            )
        if xy == "??":
            out.append(path)
    return out


def build_patch(shadow: str, add_intent: bool = True) -> bytes:
    """Gera o patch da sombra.

    ``add_intent=False`` existe SO para o controle positivo do --self-test:
    e a forma DEFEITUOSA (bare ``git diff``), que perde arquivo novo.
    """
    if add_intent:
        new_files = untracked_paths(shadow)
        for rel in new_files:
            _run(["git", "-C", shadow, "add", "-N", "--", rel])
    return _run_bytes(["git", "-C", shadow, "diff", "HEAD", "--binary"])


# --------------------------------------------------------------------------
# 3 — derivacao dos paths tocados (na arvore VIVA, modo checagem)
# --------------------------------------------------------------------------
def touched_paths(repo_root: str, patch_path: str) -> List[str]:
    out = _run(["git", "apply", "--numstat", patch_path], cwd=repo_root)
    paths: List[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            raise Refuse("linha de --numstat nao parseavel: %r" % line)
        rel = parts[2]
        if " => " in rel or rel.startswith("\""):
            raise Refuse(
                "path de rename/quoted em --numstat (%r): o Scope assinado nao "
                "expressa rename nem path com caractere especial" % rel
            )
        paths.append(rel)
    if not paths:
        raise Refuse("o patch nao toca arquivo nenhum")
    dupes = sorted({p for p in paths if paths.count(p) > 1})
    if dupes:
        raise Refuse("path repetido em --numstat: %s" % ", ".join(dupes))
    return sorted(paths)


# --------------------------------------------------------------------------
# 4 — classificacao: canonicidade + manifesto ADR-192
# --------------------------------------------------------------------------
def oracle_canonical(repo_root: str, paths: List[str]) -> Dict[str, int]:
    oracle = os.path.join(repo_root, ORACLE_REL)
    if not os.path.isfile(oracle):
        raise Refuse("oraculo de canonicidade ausente: %s" % ORACLE_REL)
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = repo_root
    proc = subprocess.run(
        [sys.executable, oracle, "--is-canonical", "-"],
        input="\n".join(paths) + "\n",
        capture_output=True, text=True, cwd=repo_root, env=env, check=False,
    )
    if proc.returncode != 0:
        raise Refuse(
            "oraculo de canonicidade falhou (rc=%d): %s"
            % (proc.returncode, proc.stderr.strip())
        )
    verdicts: Dict[str, int] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        rel, _, flag = line.rpartition("\t")
        if flag not in ("0", "1"):
            raise Refuse("oraculo nao respondeu 0|1 para %r (saida %r)" % (rel, flag))
        verdicts[rel] = int(flag)
    missing = [p for p in paths if p not in verdicts]
    if missing:
        raise Refuse("oraculo nao classificou: %s" % ", ".join(missing))
    return verdicts


def parse_manifest(path: str) -> Dict[str, str]:
    """`<sha256>  <relpath>` por linha -> {relpath: sha}."""
    members: Dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = re.match(r"^([0-9a-f]{64})\s+(\S.*)$", line)
            if not m:
                raise Refuse("linha %d do manifesto ADR-192 nao parseavel: %r" % (lineno, line))
            members[m.group(2).strip()] = m.group(1)
    if not members:
        raise Refuse("manifesto ADR-192 vazio: %s" % path)
    return members


def check_manifest_consistency(
    repo_root: str, shadow: str, touched: List[str]
) -> List[str]:
    """Recusa se um membro do manifesto foi tocado sem bump do sha.

    A conferencia do VALOR usa a SOMBRA, que ja e a arvore pos-patch: o sha
    declarado no manifesto da sombra tem de casar o conteudo do membro na
    sombra. Devolve a lista de membros tocados (para o relatorio).
    """
    live_manifest = os.path.join(repo_root, MANIFEST_REL)
    if not os.path.isfile(live_manifest):
        raise Refuse("manifesto ADR-192 ausente na arvore viva: %s" % MANIFEST_REL)
    members = parse_manifest(live_manifest)
    touched_set = set(touched)
    touched_members = sorted(touched_set & set(members.keys()))
    if not touched_members:
        return []
    if MANIFEST_REL not in touched_set:
        raise Refuse(
            "o patch toca membro(s) do manifesto ADR-192 sem tocar o manifesto:\n"
            + "".join("    %s\n" % m for m in touched_members)
            + "  Todo membro editado exige bump do sha em %s NO MESMO patch\n"
            "  (licao verify-counts.sh, S326: o oraculo responde 0 para um\n"
            "  membro, mas edicao de membro passa pela cerimonia)." % MANIFEST_REL
        )
    shadow_manifest = os.path.join(shadow, MANIFEST_REL)
    if not os.path.isfile(shadow_manifest):
        raise Refuse("manifesto ADR-192 ausente na sombra: %s" % shadow_manifest)
    shadow_members = parse_manifest(shadow_manifest)
    bad: List[str] = []
    for rel in touched_members:
        declared = shadow_members.get(rel)
        member_file = os.path.join(shadow, rel)
        if declared is None:
            bad.append("%s: sumiu do manifesto na sombra" % rel)
            continue
        if not os.path.isfile(member_file):
            bad.append("%s: membro ausente na sombra" % rel)
            continue
        actual = _sha256_file(member_file)
        if declared != actual:
            bad.append(
                "%s: manifesto declara %s, conteudo da sombra e %s"
                % (rel, declared[:16], actual[:16])
            )
    if bad:
        raise Refuse(
            "manifesto ADR-192 inconsistente na sombra:\n"
            + "".join("    %s\n" % b for b in bad)
        )
    return touched_members


# --------------------------------------------------------------------------
# 5 — escrita do sentinel e do PROPOSED-PATCH.md
# --------------------------------------------------------------------------
def write_scope(sentinel_path: str, paths: List[str]) -> None:
    with open(sentinel_path, encoding="utf-8") as fh:
        text = fh.read()
    if BEGIN_MARKER not in text or END_MARKER not in text:
        raise Refuse(
            "sentinel sem o par de marcadores %s / %s — o parser Tier-1 do hook "
            "e fail-CLOSED sem eles" % (BEGIN_MARKER, END_MARKER)
        )
    if text.count(BEGIN_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise Refuse("marcadores de scope duplicados no sentinel — recusado")
    head, _, rest = text.partition(BEGIN_MARKER)
    region, _, tail = rest.partition(END_MARKER)

    approved = re.search(r"^Approved-By:.*$", region, flags=re.M)
    plans = re.search(r"^Plans:.*$", region, flags=re.M)
    if approved is None or plans is None:
        raise Refuse(
            "regiao assinada precisa conter 'Approved-By:' e 'Plans:' — o SIGN "
            "preenche o Approved-By, mas a LINHA tem de existir no draft"
        )
    # Ordem OBRIGATORIA dentro da regiao: Approved-By -> Plans -> Scope.
    # `Plans:` DEPOIS de `Scope:` e terminador do bloco e truncaria a lista.
    bullets = "".join("  - %s\n" % p for p in paths)
    new_region = "\n%s\n%s\nScope:\n%s" % (
        approved.group(0).rstrip(), plans.group(0).rstrip(), bullets
    )
    with open(sentinel_path, "w", encoding="utf-8") as fh:
        fh.write(head + BEGIN_MARKER + new_region + END_MARKER + tail)


def write_sha_field(path: str, sha: str, field: str = "Patch-sha256") -> None:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    pattern = r"^(%s:)[ \t]*\S*[ \t]*$" % re.escape(field)
    new, n = re.subn(pattern, r"\1 " + sha, text, count=1, flags=re.M)
    if n != 1:
        raise Refuse(
            "campo '%s:' nao encontrado (ou duplicado) em %s" % (field, path)
        )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)


# --------------------------------------------------------------------------
# fluxo principal
# --------------------------------------------------------------------------
def finalize(
    repo_root: str,
    shadow: str,
    out_path: str,
    sentinel: str,
    proposed: str,
    quiet: bool = False,
) -> int:
    def say(msg: str) -> None:
        if not quiet:
            sys.stdout.write(msg + "\n")

    if not os.path.isdir(os.path.join(shadow, ".git")) and not os.path.isfile(
        os.path.join(shadow, ".git")
    ):
        raise Refuse("--shadow nao e um repositorio git: %s" % shadow)
    shadow_rp = os.path.realpath(shadow)
    root_rp = os.path.realpath(repo_root)
    if shadow_rp == root_rp:
        raise Refuse(
            "--shadow aponta para a arvore VIVA: o patch tem de sair de uma "
            "arvore-sombra, nunca do repositorio que vai receber o land"
        )

    shadow_base = _run(["git", "-C", shadow_rp, "rev-parse", "HEAD"]).strip()
    live_head = _run(["git", "-C", root_rp, "rev-parse", "HEAD"]).strip()
    if shadow_base != live_head:
        raise Refuse(
            "a sombra nao esta baseada no HEAD vivo:\n"
            "    sombra: %s\n    vivo  : %s\n"
            "  Um patch gerado contra outra base aterrissa sobre conteudo\n"
            "  diferente do assinado. Rebase a sombra e refinalize."
            % (shadow_base, live_head)
        )

    patch = build_patch(shadow, add_intent=True)
    if not patch:
        raise Refuse("a sombra nao tem diferenca contra o HEAD — nada a finalizar")
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(out_path, "wb") as fh:
        fh.write(patch)
    sha = _sha256_bytes(patch)
    say("  patch: %s (%d bytes)" % (out_path, len(patch)))
    say("  sha256: %s" % sha)

    new_file_count = patch.count(b"\nnew file mode ")
    say("  arquivos NOVOS no patch: %d" % new_file_count)

    touched = touched_paths(root_rp, os.path.abspath(out_path))
    say("  paths tocados (DERIVADOS de git apply --numstat): %d" % len(touched))

    verdicts = oracle_canonical(root_rp, touched)
    canonical = [p for p in touched if verdicts[p] == 1]
    members = check_manifest_consistency(root_rp, shadow_rp, touched)

    for p in touched:
        marks = []
        if verdicts[p] == 1:
            marks.append("CANONICO")
        if p in members:
            marks.append("MEMBRO-ADR-192")
        say("    %-62s %s" % (p, " ".join(marks) if marks else ""))
    say("  canonicos: %d   membros do manifesto tocados: %d"
        % (len(canonical), len(members)))

    write_scope(sentinel, touched)
    write_sha_field(sentinel, sha)
    # Binding EXPLICITO da base: o SIGN exige Patch-base == HEAD antes de
    # gravar o Anchor-SHA. Sem este campo a igualdade seria inferida, e uma
    # sombra rebasada silenciosamente produziria uma ancora que nao descreve
    # o que sera landado.
    write_sha_field(sentinel, shadow_base, field="Patch-base")
    write_sha_field(proposed, sha)
    say("  base do patch (Patch-base): %s" % shadow_base)
    say("  Scope, Patch-sha256 e Patch-base escritos em:")
    say("    %s" % sentinel)
    say("    %s" % proposed)
    say("")
    say("  PROXIMO PASSO: commite os materiais, depois assine.")
    return 0


# --------------------------------------------------------------------------
# --self-test
# --------------------------------------------------------------------------
def _git(cwd: str, *args: str) -> None:
    _run(["git", "-C", cwd] + list(args))


def self_test() -> int:
    """Controle POSITIVO da perna `git add -N`.

    Constroi uma sombra sintetica com (a) um arquivo rastreado MODIFICADO e
    (b) um arquivo NOVO, e prova:
      RED  — o patch gerado SEM `add -N` (a forma antiga) PERDE o arquivo novo;
      GREEN— o patch gerado COM `add -N` o carrega como `new file mode`.
    """
    failures: List[str] = []
    tmp = tempfile.mkdtemp(prefix="finalize-selftest-")
    shadow = os.path.join(tmp, "shadow")
    os.makedirs(shadow)
    _git(shadow, "init", "-q", ".")
    _git(shadow, "config", "user.email", "selftest@example.invalid")
    _git(shadow, "config", "user.name", "selftest")
    with open(os.path.join(shadow, "tracked.txt"), "w", encoding="utf-8") as fh:
        fh.write("linha original\n")
    _git(shadow, "add", "tracked.txt")
    _git(shadow, "commit", "-q", "-m", "base")

    with open(os.path.join(shadow, "tracked.txt"), "w", encoding="utf-8") as fh:
        fh.write("linha modificada\n")
    os.makedirs(os.path.join(shadow, "sub"))
    with open(os.path.join(shadow, "sub", "brand_new.py"), "w", encoding="utf-8") as fh:
        fh.write("# arquivo novo\n")

    # (a) controle NEGATIVO da cura = forma antiga, sem add -N.
    bare = build_patch(shadow, add_intent=False)
    if b"brand_new.py" in bare:
        failures.append(
            "CONTROLE VACUO: o patch SEM add -N ja continha o arquivo novo — "
            "o controle nao reproduz o defeito que a cura fecha"
        )
    else:
        sys.stdout.write(
            "  RED  (controle) patch sem `git add -N` PERDE sub/brand_new.py "
            "-- defeito reproduzido\n"
        )

    # (b) a cura.
    cured = build_patch(shadow, add_intent=True)
    if b"brand_new.py" not in cured:
        failures.append("a cura NAO trouxe o arquivo novo para o patch")
    elif b"new file mode" not in cured:
        failures.append("o arquivo novo entrou sem cabecalho `new file mode`")
    else:
        sys.stdout.write(
            "  GREEN(cura)     patch com `git add -N` carrega sub/brand_new.py "
            "como `new file mode`\n"
        )

    # (c) os paths DERIVADOS batem com os dois arquivos.
    patch_file = os.path.join(tmp, "s.patch")
    with open(patch_file, "wb") as fh:
        fh.write(cured)
    derived = touched_paths(shadow, patch_file)
    if derived != ["sub/brand_new.py", "tracked.txt"]:
        failures.append("paths derivados inesperados: %r" % derived)
    else:
        sys.stdout.write("  GREEN(derivacao) numstat devolve %r\n" % derived)

    # (d) write_scope produz a ordem que o hook parseia.
    sent = os.path.join(tmp, "wave-x-approved.md")
    with open(sent, "w", encoding="utf-8") as fh:
        fh.write(
            "# draft\n\nPatch-sha256:\nPatch-base: TO-FILL-AT-FINAL-PATCH\n\n%s\n"
            "Approved-By: @x TO-FILL-AT-SIGN\n"
            "Plans: PLAN-000\nScope:\n  - placeholder\n%s\n"
            % (BEGIN_MARKER, END_MARKER)
        )
    write_scope(sent, derived)
    write_sha_field(sent, "a" * 64)
    write_sha_field(sent, "b" * 40, field="Patch-base")
    with open(sent, encoding="utf-8") as fh:
        body = fh.read()
    region = body.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0]
    order_ok = (
        region.index("Approved-By:") < region.index("Plans:") < region.index("Scope:")
    )
    if not order_ok:
        failures.append("write_scope quebrou a ordem Approved-By -> Plans -> Scope")
    elif "  - placeholder" in region:
        failures.append("write_scope manteve o bullet placeholder")
    elif "Patch-sha256: " + "a" * 64 not in body:
        failures.append("write_sha_field nao preencheu o campo")
    elif "Patch-base: " + "b" * 40 not in body:
        failures.append("write_sha_field nao preencheu Patch-base")
    else:
        sys.stdout.write(
            "  GREEN(sentinel) ordem Approved-By/Plans/Scope, sha e base ok\n"
        )

    # (e) sombra == arvore viva e RECUSADO.
    try:
        finalize(shadow, shadow, os.path.join(tmp, "x.patch"), sent, sent, quiet=True)
        failures.append("finalize aceitou --shadow == arvore viva")
    except Refuse:
        sys.stdout.write("  GREEN(guard)    --shadow == arvore viva e recusado\n")

    if failures:
        sys.stderr.write("\nSELF-TEST FALHOU:\n")
        for f in failures:
            sys.stderr.write("  - %s\n" % f)
        return 1
    sys.stdout.write("\n  SELF-TEST: 5 asserções verdes (1 controle positivo RED).\n")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Finaliza o patch assinavel da cerimonia W5 (PLAN-183)."
    )
    ap.add_argument("--shadow", help="arvore-sombra com as edicoes")
    ap.add_argument("--out", help="caminho do patch a gerar")
    ap.add_argument(
        "--sentinel",
        default=".claude/plans/PLAN-183/wave-w5-approved.md",
        help="sentinel-draft cujo Scope sera escrito",
    )
    ap.add_argument(
        "--proposed",
        default=".claude/plans/PLAN-183/w5-ceremony/PROPOSED-PATCH.md",
        help="registro cujo Patch-sha256 sera escrito",
    )
    ap.add_argument("--repo-root", default=None, help="raiz do repo vivo (default: git toplevel)")
    ap.add_argument("--self-test", action="store_true", help="controle positivo do add -N")
    args = ap.parse_args(argv)

    if args.self_test:
        try:
            return self_test()
        except Refuse as exc:
            sys.stderr.write("SELF-TEST/ABORT: %s\n" % exc)
            return 1

    if not args.shadow or not args.out:
        ap.error("--shadow e --out sao obrigatorios (ou use --self-test)")

    try:
        repo_root = args.repo_root or _run(
            ["git", "rev-parse", "--show-toplevel"]
        ).strip()
        sentinel = args.sentinel
        proposed = args.proposed
        if not os.path.isabs(sentinel):
            sentinel = os.path.join(repo_root, sentinel)
        if not os.path.isabs(proposed):
            proposed = os.path.join(repo_root, proposed)
        for p, label in ((sentinel, "sentinel"), (proposed, "PROPOSED-PATCH.md")):
            if not os.path.isfile(p):
                raise Refuse("%s ausente: %s" % (label, p))
        return finalize(repo_root, args.shadow, args.out, sentinel, proposed)
    except Refuse as exc:
        sys.stderr.write("\nABORT: %s\n" % exc)
        return 1
    except OSError as exc:
        sys.stderr.write("\nINFRA: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
