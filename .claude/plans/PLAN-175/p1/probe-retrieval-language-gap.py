#!/usr/bin/env python3
"""Sonda do gap de idioma do recuperador de skills (PLAN-175, AC-0.5 e AC-1.3).

Três consultas por par — `en`, `pt` (tradução manual) e `pt_ascii` (a `pt` sem
diacríticos, gerada aqui) — contra dois braços da CLI do recuperador:
`retriever` (o modo que ele escolher) e `static_baseline` (`CEO_SOTA_DISABLE=1`).
Verdade-base GERADA da ROUTING TABLE de `.claude/team.md` (EN = «Work type» sem
parênteses; ouro = skills de «Skill to load»), re-derivada a cada execução:
divergência com o arquivo de pares RECUSA. Acerto = ouro entre os `top_k` com
score > 0. O índice (state-dir) é lido numa cópia temporária; os subprocessos do
recuperador rodam com HOME e destinos de auditoria nesse diretório temporário.
Saída: 0 medido; 2 uso; 3 RECUSA (modo diferente do exigido, erro, falha de
execução ou estouro de tempo do recuperador — nunca contados como erro de
recall —, verdade-base divergente, ouro fora do catálogo/índice).
"""
from __future__ import annotations

import argparse, datetime, hashlib, importlib.util, json, os, re, shlex, shutil, sqlite3, subprocess, sys, tempfile, unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.dont_write_bytecode = True  # os _load abaixo não deixam __pycache__ no repositório (os filhos rodam com -B)
REPO = Path(__file__).resolve().parents[4]
RETRIEVER = REPO / ".claude" / "scripts" / "skill-retrieve.py"
BUILDER = REPO / ".claude" / "scripts" / "skill-index-build.py"
TEAM_MD = REPO / ".claude" / "team.md"
PAIRS_FILE = REPO / ".claude" / "plans" / "PLAN-175" / "evidence" / "language-gap-pairs-30.json"
TOP_K, CUTS, LANGS = 5, (1, 3, 5), ("en", "pt", "pt_ascii")
MODES = ("tfidf", "static", "static-fallback", "rag+tfidf")
EXPAND = {(), ("inputs",), ("recall",)}
LABELS: List[Tuple[str, str]] = []  # (texto, rótulo) para _redact; resolvido uma vez em main


class Refusal(Exception):
    """A sonda não pode responder; o motivo vai na saída e o código é 3."""


def _rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO))

def _redact(text: str) -> str:
    """Tira da saída commitável o state-dir, o checkout e o diretório pessoal."""
    for raw, label in LABELS:
        text = text.replace(raw, label)
    return text

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _utc(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def routing_rows() -> List[Tuple[str, List[str]]]:
    """Linhas da ROUTING TABLE com ao menos uma skill: (consulta EN, ouro)."""
    text = TEAM_MD.read_text(encoding="utf-8")
    if "\n## ROUTING TABLE" not in text:
        raise Refusal("team.md sem a seção ROUTING TABLE")
    rows: List[Tuple[str, List[str]]] = []
    for line in text.split("\n## ROUTING TABLE", 1)[1].split("\n## ", 1)[0].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) < 3 or cells[0] == "Work type" or set(cells[0]) <= set("-: "):
            continue
        gold = list(dict.fromkeys(t.split("/")[-1] for t in re.findall(r"`([a-z0-9-]+(?:/[a-z0-9-]+)?)`", cells[2])))
        if gold:
            rows.append((re.sub(r"\s*\([^)]*\)", "", cells[0]).replace("*", "").strip(), gold))
    return rows


def load_pairs() -> List[Dict[str, object]]:
    pairs = json.loads(PAIRS_FILE.read_text(encoding="utf-8"))["pairs"]
    stored, generated = [(p["en"], p["gold"]) for p in pairs], routing_rows()
    if stored != generated:
        first = next((i for i, (a, b) in enumerate(zip(stored, generated)) if a != b), min(len(stored), len(generated)))
        raise Refusal(f"verdade-base divergente da ROUTING TABLE (arquivo {len(stored)} pares, tabela {len(generated)}; "
                      f"primeira diferença na posição {first + 1}): regenerar os pares e revisar a tradução")
    return pairs


def index_inputs(override: Optional[str], tmp: Path, builder) -> Tuple[Path, Dict[str, object], Set[str]]:
    """Resolve o índice como o recuperador resolve, copia-o e descreve-o."""
    if override:
        src, how = Path(override).resolve(), "--index-path"
    else:
        src, how = Path(_load(RETRIEVER, "skill_retrieve").resolve_index_path()), "skill-retrieve.resolve_index_path()"
    info: Dict[str, object] = {"location": "state-dir local da máquina (<state-dir> = runtime_paths.runtime_state_dir()), fora do repositório; não commitável",
                               "resolved_by": how, "path": _redact(str(src)), "exists": src.is_file()}
    if not src.is_file():
        return src, info, set()
    copy, wal, st = tmp / "skill-index.sqlite", src.with_name(src.name + "-wal"), src.stat()
    shutil.copyfile(src, copy)
    digest = _sha(copy)  # antes de o sqlite abrir a cópia (o fechamento pode fazer checkpoint do WAL)
    if wal.is_file() and wal.stat().st_size:
        shutil.copyfile(wal, tmp / (copy.name + "-wal"))
    try:
        con = sqlite3.connect(str(copy))  # a cópia é descartável: o sqlite pode criar o -shm dela
        try:
            name_col = "raw_slug" if "raw_slug" in [r[1] for r in con.execute("PRAGMA table_info(skills)")] else "slug"
            rows = con.execute(f"SELECT {name_col}, path, content_sha FROM skills").fetchall()
            meta = dict(con.execute("SELECT k, v FROM meta").fetchall())
        finally:
            con.close()
    except sqlite3.DatabaseError as exc:
        raise Refusal(f"índice ilegível: {exc}") from None
    catalog = {str(p.relative_to(REPO)): p for p in builder._iter_skill_md(REPO)}
    indexed = {rel for _, rel, _ in rows}
    changed = sum(1 for _, rel, sha in rows if rel in catalog and hashlib.sha256(builder._extract_indexed_text(
        catalog[rel].read_text(encoding="utf-8"))[1].encode("utf-8", errors="replace")).hexdigest() != sha)
    info.update({
        "measured_on": "cópia byte-idêntica num diretório temporário; o recuperador lê a cópia",
        "bytes": st.st_size, "wal_bytes": wal.stat().st_size if wal.is_file() else None, "sha256": digest,
        "mtime_utc": _utc(st.st_mtime), "age_days": round((datetime.datetime.now().timestamp() - st.st_mtime) / 86400, 2),
        "built_at_utc": _utc(float(meta["built_at"])) if str(meta.get("built_at", "")).isdigit() else None,
        "skills_in_index": len(rows), "skill_files_in_catalog": len(catalog),
        "paths_only_in_catalog": sorted(set(catalog) - indexed), "paths_only_in_index": sorted(indexed - set(catalog)),
        "content_changed_since_build": changed,
        "content_rule": "sha256 do texto indexado (skill-index-build._extract_indexed_text) contra content_sha do índice",
    })
    return copy, info, {r[0] for r in rows}


def child_env(tmp: Path, static: bool) -> Dict[str, str]:
    """Ambiente dos subprocessos: o tf-idf importa audit_emit (rag_router), cujo dreno de saída escreveria
    no state-dir herdado. Remove por PREFIXO todo destino de auditoria e aponta HOME, log e state para `tmp`."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CEO_AUDIT_", "CEO_PROJECT_STATE_DIR", "CLAUDE_PROJECT_DIR"))}
    env.update(HOME=str(tmp / "home"), CEO_AUDIT_LOG_DIR=str(tmp / "audit"), CEO_PROJECT_STATE_DIR=str(tmp / "audit"),
               CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED="0", PYTHONDONTWRITEBYTECODE="1")
    if static:
        env["CEO_SOTA_DISABLE"] = "1"
    return env


def retrieve(task: str, index: Path, env: Dict[str, str]) -> Tuple[str, List[Tuple[str, float]]]:
    cmd = [sys.executable, "-B", str(RETRIEVER), "--json", "--task", task, "--top-k", str(TOP_K),
           "--repo-root", str(REPO), "--index-path", str(index)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=env["HOME"], timeout=120)
    except subprocess.TimeoutExpired:
        raise Refusal("o recuperador excedeu 120 s") from None
    except OSError as exc:
        raise Refusal(f"o recuperador não executou: {exc}") from None
    if proc.returncode != 0:
        raise Refusal(f"recuperador saiu {proc.returncode}: {_redact(proc.stderr.strip())[-300:]}")
    try:
        doc = json.loads(proc.stdout)
    except ValueError:
        raise Refusal("a saída do recuperador não é JSON") from None
    mode, results = doc.get("mode"), doc.get("results")
    if not isinstance(mode, str) or not isinstance(results, list):
        raise Refusal("JSON do recuperador sem `mode` ou `results`")
    return mode, [(str(r.get("slug", "")).split(":")[-1], float(r.get("score", 0.0))) for r in results]


def measure(args: argparse.Namespace, out: Dict[str, object]) -> List[Dict[str, object]]:
    builder, pairs = _load(BUILDER, "skill_index_build"), load_pairs()
    if args.pairs is not None and not 1 <= args.pairs <= len(pairs):
        print(f"erro: --pairs tem de estar entre 1 e {len(pairs)}", file=sys.stderr)
        raise SystemExit(2)
    pairs = pairs[: args.pairs or len(pairs)]
    gold_all = {g for p in pairs for g in p["gold"]}
    outside = sorted(gold_all - {p.parent.name for p in builder._iter_skill_md(REPO)})
    if outside:
        raise Refusal(f"ouro fora do catálogo: {outside}")
    tmp = Path(tempfile.mkdtemp(prefix="p175-probe-"))
    try:
        index, info, index_names = index_inputs(args.index_path, tmp, builder)
        info["gold_missing_from_index"] = sorted(gold_all - index_names) if info["exists"] else []
        out["inputs"]["index"] = info
        if info["gold_missing_from_index"] and args.require_mode == "tfidf":
            raise Refusal(f"ouro ausente do índice (índice defasado): {info['gold_missing_from_index']}")
        (tmp / "home").mkdir(mode=0o700)
        envs = {static: child_env(tmp, static) for static in (False, True)}
        modes: Counter = Counter()
        rows: List[Dict[str, object]] = []
        for pair in pairs:
            folded = "".join(c for c in unicodedata.normalize("NFKD", str(pair["pt"])) if not unicodedata.combining(c))
            queries = {"en": pair["en"], "pt": pair["pt"], "pt_ascii": folded}
            row: Dict[str, object] = {"id": pair["id"], "gold": pair["gold"], "top1": {}}
            for arm, static in (("retriever", False), ("static_baseline", True)):
                row[arm] = {}
                for lang, query in queries.items():
                    mode, results = retrieve(str(query), index, envs[static])
                    if static and mode != "static":
                        raise Refusal(f"{pair['id']}/{lang}: a linha de base devolveu modo {mode!r}, esperado 'static'")
                    if not static:
                        modes[mode] += 1
                        family = {m[: -len("-empty")] if m.endswith("-empty") else m for m in modes}
                        out["mode"] = family.pop() if len(family) == 1 else "mixed"
                        if args.require_mode and out["mode"] != args.require_mode:
                            raise Refusal(f"{pair['id']}/{lang}: o recuperador devolveu modo {mode!r}, exigido {args.require_mode!r}")
                    live = [name for name, score in results if score > 0]
                    if not static:
                        row["top1"][lang] = live[0] if live else None
                    row[arm][lang] = next((i + 1 for i, name in enumerate(live) if name in pair["gold"]), None)
            rows.append(row)
        out["modes_observed"] = dict(modes)
        return rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def summarize(rows: List[Dict[str, object]]) -> Dict[str, object]:
    recall = {arm: {lang: {f"@{k}": sum(1 for r in rows if (r[arm][lang] or TOP_K + 1) <= k) for k in CUTS}
                    for lang in LANGS} for arm in ("retriever", "static_baseline")}
    common = {lang: Counter(r["top1"][lang] for r in rows if r["top1"][lang]).most_common(1) for lang in LANGS}
    return {"recall": recall, "top1_most_common": {k: ({"slug": v[0][0], "count": v[0][1]} if v else None)
                                                   for k, v in common.items()}}


def _fmt(value: object, path: Tuple[str, ...] = (), ind: int = 0) -> str:
    if isinstance(value, dict) and path in EXPAND:
        items = [" " * (ind + 1) + json.dumps(k) + ": " + _fmt(v, path + (k,), ind + 1) for k, v in value.items()]
        return "{\n" + ",\n".join(items) + "\n" + " " * ind + "}"
    if path == ("results",):
        return "[\n" + ",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in value) + "\n ]"
    return json.dumps(value, ensure_ascii=False)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--pairs", type=int, default=None, help="usa os N primeiros pares (padrão: todos)")
    parser.add_argument("--require-mode", choices=MODES, default=None, help="RECUSA se o recuperador devolver outro modo")
    parser.add_argument("--index-path", default=None, help="índice a usar (padrão: o resolvedor do recuperador)")
    parser.add_argument("--json", action="store_true", help="saída JSON")
    args = parser.parse_args(argv)
    home = str(Path.home())
    state = _load(REPO / ".claude" / "hooks" / "_lib" / "runtime_paths.py", "runtime_paths").runtime_state_dir()
    LABELS[:] = [(str(state), "<state-dir>"), (str(REPO), "<repo>"), (home.replace(os.sep, "-"), "<home>"), (home, "$HOME")]
    out: Dict[str, object] = {
        "schema": "plan175-language-gap/2", "generated_at": _utc(datetime.datetime.now().timestamp()),
        "invocation": shlex.join(["python3", _rel(Path(__file__))] + argv), "require_mode": args.require_mode,
        "status": "refused", "reason": None, "mode": None, "numbers_source": "none", "pairs": 0, "top_k": TOP_K,
        "inputs": {"probe_sha256": _sha(Path(__file__)), "retriever": _rel(RETRIEVER), "retriever_sha256": _sha(RETRIEVER),
                   "ground_truth": ".claude/team.md §ROUTING TABLE", "team_md_sha256": _sha(TEAM_MD),
                   "pairs_file": _rel(PAIRS_FILE), "pairs_sha256": _sha(PAIRS_FILE),
                   "rag_sidecar": "desligado na sonda (CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED=0): o sujeito é o tf-idf léxico",
                   "audit_isolation": "subprocessos sem as variáveis HERDADAS CEO_AUDIT_*, CEO_PROJECT_STATE_DIR e CLAUDE_PROJECT_DIR*; "
                                      "CEO_AUDIT_LOG_DIR e CEO_PROJECT_STATE_DIR apontam para <tmp>/audit e HOME para <tmp>/home "
                                      "(o dreno de saída do audit_emit não alcança o state-dir vivo)",
                   "tokenizer_rule": "_lib/embeddings.tokenize é ASCII-only ([A-Za-z0-9]+): letra acentuada parte a palavra "
                                     "(«migrações» vira migra + es); pt_ascii isola só o efeito dos diacríticos",
                   "archetype_boost": "não usado: o reforço por arquétipo independe do idioma e mascararia o efeito",
                   "hit_rule": "acerto = alguma skill do ouro entre os top_k devolvidos com score > 0",
                   "mode_rule": "`tfidf-empty` (nenhum termo da consulta no vocabulário do índice) é o modo tfidf com vetor "
                                "vazio: conta como erro de recall e aparece em modes_observed; sob --require-mode tfidf, os modos static, "
                                "static-fallback e rag+tfidf RECUSAM"},
    }
    try:
        rows = measure(args, out)
    except Refusal as exc:
        out["reason"] = _redact(str(exc))
        print(_fmt(out) if args.json else f"RECUSA: {out['reason']}", file=sys.stdout if args.json else sys.stderr)
        return 3
    out.update(status="measured", numbers_source="measured", pairs=len(rows), **summarize(rows))
    out["results"] = rows
    if args.json:
        print(_fmt(out))
        return 0
    print(f"modo {out['mode']}; {len(rows)} pares; acertos @1/@3/@5 por braço e idioma: {json.dumps(out['recall'])}")
    print(f"top-1 mais frequente do recuperador: {json.dumps(out['top1_most_common'], ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
