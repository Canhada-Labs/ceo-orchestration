#!/usr/bin/env python3
"""apply-opus55-edits.py — a DERIVACAO do patch da wave-opus55 (PLAN-193, S357).

Este script E o material versionado da cerimonia `adopt-opus-5.5` (ADR-149
Amendment 3, decisao do Owner na S357: «Padrão + piso VETO» — o
`claude-opus-5-5` entra no `AVAILABLE_MODELS_WORKING_SET` (no FIM) e no
`VETO_FLOOR_ALLOWED`, vira o pin `model` de sessao; o fallback segue
`claude-opus-5`; os agentes com `veto_floor: true` seguem em `claude-fable-5`).
Clonado em ESTRUTURA do `apply-fable51-edits.py` (PLAN-169, S338).

Ele aplica TODAS as edicoes da wave sobre uma arvore em HEAD, com ancora
EXATA por edicao e contagem declarada — ancora ausente, ambigua ou ja
aplicada e RECUSA nomeada, nunca "best effort". As edicoes vem de DOIS
modulos de dados no mesmo diretorio, concatenados nesta ordem:

    edits_core.py     governanca, settings, upgrade.sh, adapter, espelhos
    edits_pricing.py  superficies de custo / telemetria / docs de preco

Diferenca deliberada em relacao ao molde fable51: cada ancora e contada no
texto PROGRESSIVAMENTE editado do seu path (simulacao em memoria de TODAS as
edicoes antes da primeira escrita). No molde, a contagem era feita no texto
original e a aplicacao era sequencial — duas edicoes no mesmo path podiam
divergir entre o plano e a escrita. Aqui plano e escrita sao o MESMO calculo.

Os dois modulos sao path-DISJUNTOS, e o derivador o VERIFICA: um path
presente nos dois e DADOS INVALIDOS (saida 2) com os paths nomeados — nenhuma
ordem entre metades e adivinhada. Dentro de um modulo, a simulacao
progressiva acima e a garantia.

Manifesto ADR-192 (`.claude/governance/gate-scripts-manifest.txt`): todo
membro tocado pelas edicoes tem a sua linha `sha256  path` re-derivada do
CONTEUDO pos-edicao. O conjunto de membros tocados e DECLARADO
(`EXPECTED_MANIFEST_MEMBERS`): um membro a mais ou a menos e recusa, para
que uma edicao nova num gate script nunca entre sem alguem decidir.

Ratchet installer-write-safety (CLAUDE.md, PLAN-185: uma wave que toca
`scripts/` REGENERA o baseline no mesmo patch): quando uma edicao toca um
`.sh` que o censo le, o derivador copia os `.sh` que o PROPRIO censo
descobre (a funcao `discover_shell_files` do instrumento da arvore) para um
diretorio temporario, com o texto POS-EDICAO nos paths editados, roda o
censo (`run_census` + `render_baseline`, o mesmo calculo do
`--write-baseline`) e usa a saida como o baseline. Nenhuma edicao pode
tocar o baseline, e a DIFERENCA de linhas (path:classe:veredito:forma:
impressao digital, sem o numero de linha) entre o baseline da arvore e o
regenerado tem de ser EXATAMENTE a declarada em `RATCHET_DELTA` no modulo
de dados — um sitio de escrita novo nunca entra no ratchet sem decisao.

Inventario de nomes de env (`.claude/scripts/env-inventory.json`, o que o
`env-inventory-check.py --check` do Validate compara; fix round r11,
R2M-01): o derivador calcula, com o `scan_consumed` do PROPRIO instrumento
da arvore, os nomes CLAUDE_*/ANTHROPIC_*/CEO_* da arvore pos-edicao (a
varredura da arvore em HEAD, sem a contribuicao dos paths editados, unida a
varredura do texto POS-EDICAO desses paths num diretorio temporario) e
compara com os nomes do inventario de HEAD. A diferenca de NOMES tem de ser
EXATAMENTE a declarada em `ENV_INVENTORY_DELTA`; declarada e nao vazia, o
derivador REGISTRA os nomes (entrada na forma do `build_inventory` do
instrumento) e deixa todo o resto do inventario como HEAD o tem — e um
registro de nomes, nao uma regeneracao: o `--check` compara so nomes, e as
evidencias de nomes antigos nao dependem de arquivos fora do pacote. Um
nome novo nunca entra (nem sai) sem decisao.

Uso:
    python3 apply-opus55-edits.py --root <arvore-em-HEAD>
    python3 apply-opus55-edits.py --root <arvore> --check-only   (so ancoras)
    python3 apply-opus55-edits.py --list-paths                   (sem --root)
    ... --require-pricing   recusa se edits_pricing.py estiver ausente
                            (o SIGN / LAND da cerimonia passam SEMPRE esta flag)

Saidas: 0 = aplicado (ou, com --check-only, aplicavel); 1 = recusa nomeada;
2 = erro de uso / modulo de dados invalido. Stdlib-only, Python >= 3.9, sem
PEP 604 em runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent

NEW_ID = "claude-opus-5-5"
MANIFEST_REL = ".claude/governance/gate-scripts-manifest.txt"
#: Membros do manifesto ADR-192 que ESTA wave toca (declarado, nao inferido).
EXPECTED_MANIFEST_MEMBERS = (".claude/scripts/validate-governance.sh",)

#: O ratchet installer-write-safety: baseline DERIVADO, instrumento da arvore.
RATCHET_BASELINE_REL = ".claude/scripts/data/installer-write-safety-baseline.txt"
RATCHET_CENSUS_REL = ".claude/scripts/check-installer-write-safety.py"
#: O que o censo le por padrao (DEFAULT_SCAN_ROOT / EXCLUDED_REL_PREFIXES do
#: instrumento); so decide SE o baseline e regenerado — a descoberta em si
#: e a do instrumento.
RATCHET_SCAN_PREFIX = "scripts/"
RATCHET_EXCLUDED_PREFIXES = ("scripts/tests/",)

#: O inventario de nomes de env: REGISTRADO pelo derivador, instrumento da arvore.
ENV_INVENTORY_REL = ".claude/scripts/env-inventory.json"
ENV_INSTRUMENT_REL = ".claude/scripts/env-inventory-check.py"
#: A forma de um nome (o TOKEN_RE do instrumento, ancorado).
_ENV_NAME_RE = re.compile(r"^(?:CLAUDE|ANTHROPIC|CEO)_[A-Z0-9_]*[A-Z0-9]$")

#: (nome do modulo, obrigatorio?) — na ordem de aplicacao.
DATA_MODULES: Tuple[Tuple[str, bool], ...] = (
    ("edits_core", True),
    ("edits_pricing", False),
)

Edit = Tuple[str, str, str, int]


class Refuse(Exception):
    """Recusa nomeada: a arvore nao e a esperada; nada foi escrito."""


class BadData(Exception):
    """Um modulo de dados nao respeita o formato do registro."""


#: RATCHET_DELTA do modulo de dados: {"removed": [...], "added": [...]}, cada
#: item uma linha do baseline SEM o numero de linha
#: (path:classe:veredito:forma:impressao-digital). Preenchido por load_edits.
_RATCHET_DELTA: Dict[str, List[str]] = {}

#: ENV_INVENTORY_DELTA do modulo de dados: {"added": [...], "removed": [...]},
#: NOMES de env ordenados e sem repeticao. Preenchido por load_edits.
_ENV_DELTA: Dict[str, List[str]] = {}


def _env_delta_of(module: object, fname: str) -> Optional[Dict[str, List[str]]]:
    delta = getattr(module, "ENV_INVENTORY_DELTA", None)
    if delta is None:
        return None
    ok = (isinstance(delta, dict) and sorted(delta) == ["added", "removed"]
          and all(isinstance(delta[k], list)
                  and all(isinstance(x, str) and _ENV_NAME_RE.match(x)
                          for x in delta[k])
                  and delta[k] == sorted(set(delta[k]))
                  for k in ("added", "removed"))
          and not set(delta["added"]) & set(delta["removed"]))
    if not ok:
        raise BadData("%s: ENV_INVENTORY_DELTA fora do formato ({'added': [...], "
                      "'removed': [...]}, NOMES de env ordenados, sem repeticao "
                      "e disjuntos)" % fname)
    return {"added": list(delta["added"]), "removed": list(delta["removed"])}


def _env_delta_declared() -> bool:
    return bool(_ENV_DELTA.get("added") or _ENV_DELTA.get("removed"))


def _ratchet_delta_of(module: object, fname: str) -> Optional[Dict[str, List[str]]]:
    delta = getattr(module, "RATCHET_DELTA", None)
    if delta is None:
        return None
    ok = (isinstance(delta, dict) and sorted(delta) == ["added", "removed"]
          and all(isinstance(delta[k], list)
                  and all(isinstance(x, str) and x.count(":") >= 4 for x in delta[k])
                  and delta[k] == sorted(set(delta[k]))
                  for k in ("added", "removed")))
    if not ok:
        raise BadData("%s: RATCHET_DELTA fora do formato ({'added': [...], "
                      "'removed': [...]}, listas ordenadas sem repeticao de "
                      "linhas sem numero de linha)" % fname)
    return {"added": list(delta["added"]), "removed": list(delta["removed"])}


def _load_module(name: str) -> Optional[List[Edit]]:
    path = HERE / (name + ".py")
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_opus55_" + name, str(path))
    if spec is None or spec.loader is None:
        raise BadData("%s: modulo nao carregavel" % path.name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    edits = getattr(module, "EDITS", None)
    if not isinstance(edits, list) or not edits:
        raise BadData("%s: EDITS ausente ou vazio" % path.name)
    declared = getattr(module, "NEW_ID", NEW_ID)
    if declared != NEW_ID:
        raise BadData("%s: NEW_ID=%r, esperado %r" % (path.name, declared, NEW_ID))
    delta = _ratchet_delta_of(module, path.name)
    if delta is not None:
        if _RATCHET_DELTA:
            raise BadData("%s: RATCHET_DELTA declarado em mais de um modulo"
                          % path.name)
        _RATCHET_DELTA.update(delta)
    env_delta = _env_delta_of(module, path.name)
    if env_delta is not None:
        if _ENV_DELTA:
            raise BadData("%s: ENV_INVENTORY_DELTA declarado em mais de um modulo"
                          % path.name)
        _ENV_DELTA.update(env_delta)
    out: List[Edit] = []
    for i, rec in enumerate(edits):
        ok = (
            isinstance(rec, tuple) and len(rec) == 4
            and isinstance(rec[0], str) and rec[0]
            and not rec[0].startswith("/") and ".." not in Path(rec[0]).parts
            and isinstance(rec[1], str) and rec[1]
            and isinstance(rec[2], str)
            and isinstance(rec[3], int) and not isinstance(rec[3], bool)
            and rec[3] >= 1
            and rec[1] != rec[2]
        )
        if not ok:
            raise BadData("%s: EDITS[%d] fora do formato "
                          "(path relativo, ancora, substituto, contagem>=1)"
                          % (path.name, i))
        out.append(rec)
    return out


def load_edits(require_pricing: bool) -> Tuple[List[Edit], List[str], List[str]]:
    """Devolve (edicoes na ordem, modulos carregados, modulos ausentes)."""
    edits: List[Edit] = []
    loaded: List[str] = []
    missing: List[str] = []
    owner: Dict[str, str] = {}
    for name, required in DATA_MODULES:
        recs = _load_module(name)
        if recs is None:
            if required or (name == "edits_pricing" and require_pricing):
                raise BadData("%s.py ausente em %s" % (name, HERE))
            missing.append(name)
            continue
        shared = sorted(p for p in {r[0] for r in recs} if p in owner)
        if shared:
            raise BadData("%s.py e %s.py tocam o(s) mesmo(s) path(s) %r — as "
                          "metades sao path-disjuntas por contrato"
                          % (owner[shared[0]], name, shared))
        for rec in recs:
            owner[rec[0]] = name
        edits.extend(recs)
        loaded.append(name)
    return edits, loaded, missing


def _in_ratchet_scope(rel: str) -> bool:
    return (rel.startswith(RATCHET_SCAN_PREFIX) and rel.endswith(".sh")
            and not rel.startswith(RATCHET_EXCLUDED_PREFIXES))


def touched_paths(edits: List[Edit]) -> List[str]:
    paths = {e[0] for e in edits}
    if paths & set(EXPECTED_MANIFEST_MEMBERS):
        paths.add(MANIFEST_REL)
    if any(_in_ratchet_scope(p) for p in paths):
        paths.add(RATCHET_BASELINE_REL)
    if _env_delta_declared():
        paths.add(ENV_INVENTORY_REL)
    return sorted(paths)


def _render_inventory(doc: object) -> str:
    """A forma em que o `--generate` do instrumento escreve o inventario."""
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def _register_env_names(root: Path, texts: Dict[str, str],
                        problems: List[str]) -> Optional[str]:
    """O inventario de HEAD com os NOMES que a arvore pos-edicao ganha/perde.

    None quando nada muda (e nada foi declarado) ou quando houve recusa.
    """
    instrument = root / ENV_INSTRUMENT_REL
    base_text = _read(root, ENV_INVENTORY_REL)
    if not instrument.is_file() or base_text is None:
        problems.append("%s / %s: instrumento ou inventario ausente"
                        % (ENV_INSTRUMENT_REL, ENV_INVENTORY_REL))
        return None
    spec = importlib.util.spec_from_file_location("_opus55_envinv", str(instrument))
    if spec is None or spec.loader is None:
        problems.append("%s: instrumento nao carregavel" % ENV_INSTRUMENT_REL)
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        inventory = json.loads(base_text)
        names = inventory["vars"]
        base_scan = mod.scan_consumed(str(root))
    except Exception as exc:  # o instrumento e o inventario sao da arvore
        problems.append("%s: a varredura de HEAD falhou: %r" % (ENV_INSTRUMENT_REL, exc))
        return None
    if (not isinstance(names, dict) or list(names) != sorted(names)
            or _render_inventory(inventory) != base_text):
        problems.append("%s: o inventario de HEAD nao esta na forma que o "
                        "instrumento escreve (vars ordenados, indent=2, "
                        "ensure_ascii=False) — registrar mudaria linhas fora do "
                        "delta" % ENV_INVENTORY_REL)
        return None
    tmp = Path(tempfile.mkdtemp(prefix="opus55-envinv."))
    try:
        for rel, text in texts.items():
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(text.encode("utf-8"))
        post_touched = mod.scan_consumed(str(tmp))
    except Exception as exc:
        problems.append("%s: a varredura pos-edicao falhou: %r" % (ENV_INSTRUMENT_REL, exc))
        return None
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    # A varredura e uma uniao por ARQUIVO: tirar os paths editados da
    # varredura de HEAD e unir a dos seus textos pos-edicao e a varredura
    # da arvore pos-edicao (o conjunto de arquivos nao muda: nenhuma edicao
    # cria ou apaga arquivo).
    post: Dict[str, set] = {}
    for name, paths in base_scan.items():
        kept = [p for p in paths if p not in texts]
        if kept:
            post[name] = set(kept)
    for name, paths in post_touched.items():
        post.setdefault(name, set()).update(paths)
    added = sorted(set(post) - set(names))
    removed = sorted(set(names) - set(post))
    if (added != _ENV_DELTA.get("added", [])
            or removed != _ENV_DELTA.get("removed", [])):
        problems.append(
            "%s: os NOMES de env mudam alem do que ENV_INVENTORY_DELTA declara "
            "— decida antes de derivar\n      acrescentados: %r\n"
            "      removidos: %r\n      declarado: %r"
            % (ENV_INVENTORY_REL, added, removed, _ENV_DELTA))
        return None
    if not added and not removed:
        return None
    fresh = mod.build_inventory({n: sorted(post[n]) for n in added}, "-")["vars"]
    new_vars = {}
    for name in sorted((set(names) - set(removed)) | set(added)):
        new_vars[name] = names[name] if name in names else fresh[name]
    inventory["vars"] = new_vars
    return _render_inventory(inventory)


def _ratchet_rows(text: str) -> List[str]:
    """Linhas de dados do baseline SEM o numero de linha (informativo)."""
    rows: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(":", 5)
        if len(parts) != 6:
            rows.append("MALFORMED:" + line)
            continue
        rows.append(":".join([parts[0]] + parts[2:]))
    return rows


def _regenerate_ratchet(root: Path, texts: Dict[str, str],
                        problems: List[str]) -> Optional[str]:
    """O baseline que o censo da ARVORE escreve sobre a arvore pos-edicao."""
    census = root / RATCHET_CENSUS_REL
    if not census.is_file():
        problems.append("%s: instrumento do censo ausente" % RATCHET_CENSUS_REL)
        return None
    spec = importlib.util.spec_from_file_location("_opus55_census", str(census))
    if spec is None or spec.loader is None:
        problems.append("%s: instrumento nao carregavel" % RATCHET_CENSUS_REL)
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # classes resolvem o proprio modulo
    try:
        spec.loader.exec_module(mod)
        scan = getattr(mod, "DEFAULT_SCAN_ROOT")
        found = mod.discover_shell_files(root / scan, root)
    except Exception as exc:  # o instrumento e da arvore: recusa nomeada
        problems.append("%s: o censo falhou ao descobrir: %r" % (RATCHET_CENSUS_REL, exc))
        return None
    tmp = Path(tempfile.mkdtemp(prefix="opus55-census."))
    try:
        for p in found:
            rel = p.relative_to(root).as_posix()
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if p.is_symlink():
                os.symlink(os.readlink(str(p)), str(dst))
            elif rel in texts:
                dst.write_bytes(texts[rel].encode("utf-8"))
            else:
                shutil.copyfile(str(p), str(dst))
        missing = sorted(r for r in texts if _in_ratchet_scope(r)
                         and not (tmp / r).is_file())
        if missing:
            problems.append("o censo nao descobre path(s) editado(s) %r" % missing)
            return None
        try:
            sites, _files = mod.run_census(tmp, tmp / scan)
        except Exception as exc:
            problems.append("%s: o censo falhou: %r" % (RATCHET_CENSUS_REL, exc))
            return None
        if not sites:
            problems.append("o censo achou ZERO sitios na arvore pos-edicao")
            return None
        return mod.render_baseline(sites)
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


def _read(root: Path, rel: str) -> Optional[str]:
    p = root / rel
    if not p.is_file() or p.is_symlink():
        return None
    # bytes -> str sem traducao de newline: o patch e byte a byte.
    return p.read_bytes().decode("utf-8")


def plan(root: Path, edits: List[Edit]) -> Dict[str, str]:
    """Passo 1 — simula TODAS as edicoes em memoria; recusa antes de escrever.

    Devolve {path: texto final} para cada path tocado (manifesto incluido).
    """
    problems: List[str] = []
    originals: Dict[str, Optional[str]] = {}
    texts: Dict[str, str] = {}
    for rel in sorted({e[0] for e in edits}):
        originals[rel] = _read(root, rel)
        if originals[rel] is None:
            problems.append("%s: arquivo ausente (ou symlink)" % rel)
        elif NEW_ID in originals[rel]:
            # Ja aplicado? O id novo nao pode existir em NENHUM path tocado:
            # aplicar duas vezes duplicaria linhas em silencio.
            problems.append("%s: ja contem %s — arvore ja patchada?" % (rel, NEW_ID))
        else:
            texts[rel] = originals[rel]
    for idx, (rel, old, new, count) in enumerate(edits):
        if rel not in texts:
            continue
        n = texts[rel].count(old)
        if n != count:
            problems.append("%s: edicao #%d — ancora encontrada %dx, esperado %d — %r"
                            % (rel, idx, n, count, old[:70]))
            continue
        texts[rel] = texts[rel].replace(old, new)

    members = sorted(set(texts) & set(EXPECTED_MANIFEST_MEMBERS))
    if members:
        mtext = _read(root, MANIFEST_REL)
        if mtext is None:
            problems.append("%s: ausente" % MANIFEST_REL)
        else:
            listed = set()
            for line in mtext.splitlines():
                parts = line.split("  ", 1)
                if len(parts) == 2 and re.match(r"^[0-9a-f]{64}$", parts[0]):
                    listed.add(parts[1])
            touched_members = sorted(set(texts) & listed)
            if touched_members != sorted(EXPECTED_MANIFEST_MEMBERS):
                problems.append(
                    "%s: membros tocados %r != declarados %r — decida antes de derivar"
                    % (MANIFEST_REL, touched_members, sorted(EXPECTED_MANIFEST_MEMBERS)))
            for rel in EXPECTED_MANIFEST_MEMBERS:
                if rel not in texts:
                    continue
                new_sha = hashlib.sha256(texts[rel].encode("utf-8")).hexdigest()
                pat = re.compile(r"^[0-9a-f]{64}  " + re.escape(rel) + r"$", re.M)
                mtext, n = pat.subn(new_sha + "  " + rel, mtext)
                if n != 1:
                    problems.append("%s: %d linha(s) para %s, esperado 1"
                                    % (MANIFEST_REL, n, rel))
            texts[MANIFEST_REL] = mtext
    elif EXPECTED_MANIFEST_MEMBERS and not problems:
        # Os membros declarados nao foram tocados: a declaracao mente.
        problems.append("nenhum membro declarado do manifesto foi tocado: %r"
                        % (EXPECTED_MANIFEST_MEMBERS,))

    # Ratchet installer-write-safety: REGENERADO, nunca editado a mao.
    if RATCHET_BASELINE_REL in {e[0] for e in edits}:
        problems.append("%s: nenhuma edicao pode tocar o baseline do ratchet — "
                        "ele e REGENERADO pelo censo" % RATCHET_BASELINE_REL)
    elif any(_in_ratchet_scope(r) for r in texts) and not problems:
        before = _read(root, RATCHET_BASELINE_REL)
        after = _regenerate_ratchet(root, texts, problems)
        sys.modules.pop("_opus55_census", None)
        if before is None:
            problems.append("%s: ausente" % RATCHET_BASELINE_REL)
        elif after is not None:
            old_rows, new_rows = _ratchet_rows(before), _ratchet_rows(after)
            removed = sorted(set(old_rows) - set(new_rows))
            added = sorted(set(new_rows) - set(old_rows))
            if (removed != _RATCHET_DELTA.get("removed")
                    or added != _RATCHET_DELTA.get("added")):
                problems.append(
                    "%s: a regeneracao muda linhas que RATCHET_DELTA nao declara "
                    "— decida antes de derivar\n      removidas: %r\n"
                    "      acrescentadas: %r\n      declarado: %r"
                    % (RATCHET_BASELINE_REL, removed, added, _RATCHET_DELTA))
            else:
                texts[RATCHET_BASELINE_REL] = after

    # Inventario de nomes de env: REGISTRADO, nunca editado (R2M-01).
    if ENV_INVENTORY_REL in {e[0] for e in edits}:
        problems.append("%s: nenhuma edicao pode tocar o inventario de env — "
                        "o derivador REGISTRA os nomes" % ENV_INVENTORY_REL)
    elif not problems:
        env_text = _register_env_names(root, texts, problems)
        if env_text is not None:
            texts[ENV_INVENTORY_REL] = env_text
        elif _env_delta_declared() and not problems:
            problems.append("%s: ENV_INVENTORY_DELTA declarado, nada registrado"
                            % ENV_INVENTORY_REL)

    if problems:
        raise Refuse("\n".join("  - " + x for x in problems))
    return texts


def apply(root: Path, texts: Dict[str, str]) -> List[str]:
    written: List[str] = []
    for rel in sorted(texts):
        p = root / rel
        data = texts[rel].encode("utf-8")
        if p.read_bytes() == data:
            continue
        # write_bytes trunca o arquivo existente: o modo (bit x) fica intacto.
        p.write_bytes(data)
        written.append(rel)
    return written


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="arvore em HEAD a patchar")
    ap.add_argument("--check-only", action="store_true",
                    help="so verifica as ancoras; nao escreve nada")
    ap.add_argument("--list-paths", action="store_true",
                    help="imprime os paths tocados (um por linha) e sai")
    ap.add_argument("--require-pricing", action="store_true",
                    help="recusa se edits_pricing.py estiver ausente")
    args = ap.parse_args(argv)
    try:
        edits, loaded, missing = load_edits(args.require_pricing)
    except BadData as exc:
        sys.stderr.write("apply-opus55-edits: DADOS INVALIDOS: %s\n" % exc)
        return 2
    for name in missing:
        sys.stderr.write("apply-opus55-edits: NOTA: %s.py ausente — aplicando so %s "
                         "(use --require-pricing na cerimonia)\n"
                         % (name, "+".join(loaded)))
    if args.list_paths:
        # Sem --root: a lista e uma propriedade do SCRIPT + modulos, nao de
        # uma arvore (o SIGN e o LAND a consomem para a bijecao com o EXPECTED).
        for rel in touched_paths(edits):
            print(rel)
        return 0
    if not args.root:
        ap.error("--root e obrigatorio (exceto com --list-paths)")
    root = Path(args.root).resolve()
    if not (root / ".claude").is_dir():
        sys.stderr.write("apply-opus55-edits: --root nao parece um checkout: %s\n" % root)
        return 2
    try:
        texts = plan(root, edits)
    except Refuse as exc:
        sys.stderr.write("apply-opus55-edits: RECUSADO\n%s\n" % exc)
        return 1
    if args.check_only:
        print("apply-opus55-edits: %d edicao(oes) aplicaveis em %d path(s) [%s]; nada escrito"
              % (len(edits), len(texts), "+".join(loaded)))
        return 0
    written = apply(root, texts)
    print("apply-opus55-edits: %d edicao(oes) aplicadas em %d path(s) [%s]:"
          % (len(edits), len(written), "+".join(loaded)))
    for rel in written:
        print("  " + rel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
