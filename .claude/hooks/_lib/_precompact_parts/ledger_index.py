"""Bounded on-disk plan and ledger index."""
from __future__ import annotations

_LEDGER_INDEX_MAX_SECTIONS = 5
_LEDGER_INDEX_MAX_BYTES = 65536


def _plan_id_from_path(path: str) -> Optional[str]:
    """``PLAN-NNN`` from a repo-relative path, by PATH SHAPE alone.

    Matches ONLY ``.claude/plans/PLAN-NNN/...`` (plan dir) — espelho
    FIEL do ``derive_scope`` canonico (rail r21 P2-b: o arquivo de plano
    NAO classifica direto; cai em unmatched e segue a perna AC). No
    session state, no env, no audit log — emenda r1-C6."""
    base = ".claude/plans/"
    if not path.startswith(base + "PLAN-"):
        return None
    tail = path[len(base):]
    ident = tail[:8]
    if len(tail) < 9 or not ident[5:8].isdigit():
        return None
    if tail[8] == "/":
        return ident
    # Rail r21 P2-b (remove o branch `-` que a r7 apenas apertara): o
    # `derive_scope` CANONICO so aceita plan_dir (`PLAN-NNN/**`) e paths
    # AC-declarados — um 3o shape (o ARQUIVO de plano) fazia este espelho
    # eleger plano DIFERENTE do checkpoint no mesmo commit (empate
    # PLAN-010-x.md vs PLAN-020/n.md ⇒ pointers divergentes). Fidelidade
    # de espelho e o contrato; o arquivo de plano cai em unmatched e
    # segue a MESMA perna AC do canonico.
    return None


#: Rail r6 P2-c — a perna (b) do ``derive_scope`` (plan_ac), espelhada.
#: Espelho LITERAL de ``check_ledger_checkpoint.py`` (o contrato de hooks
#: proibe import hook-a-hook): _AC_PATH_RE / _PLAN_FILE_GLOB /
#: _PLAN_FILE_ID_RE / _AC_SCAN_MAX_FILES / _AC_SCAN_MAX_BYTES.
_LEDGER_AC_PATH_RE = re.compile(
    r"\[P[0-3]\]\[US[0-9]{1,6}[a-z]{0,2}\]\[([^\[\]\n]{1,200})\]"
)
_LEDGER_PLAN_FILE_GLOB = "PLAN-[0-9][0-9][0-9]-*.md"
_LEDGER_PLAN_FILE_ID_RE = re.compile(r"^(PLAN-[0-9]{3})-")
_LEDGER_AC_SCAN_MAX_FILES = 200
_LEDGER_AC_SCAN_MAX_BYTES = 256 * 1024
#: Rail r9 P2-b — cap de paths considerados no matching plan_ac (o loop e
#: O(paths x ACs); um commit gigante nao pode estourar o budget do hook).
_LEDGER_AC_MATCH_MAX_PATHS = 500
#: Rail r10 P2-c — cap de entradas materializadas do commit (pre-dedupe;
#: `-m` repete por parent) e fatia de budget do indice OPCIONAL (r10
#: P2-b: o indice nunca come o tempo reservado ao _write_snapshot).
_LEDGER_GIT_PATHS_MAX = 2000
_LEDGER_INDEX_MAX_SHARE_S = 1.0


def _open_index_directory(path: str, parent_fd: Optional[int] = None) -> int:
    """Open one real directory relative to an already validated parent.

    The repository root is the trust anchor; components below it are opened
    one at a time. Unsupported no-follow primitives make the optional index
    unavailable rather than falling back to a pathname read.
    """
    if not all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW")):
        raise OSError("no-follow directory reads unavailable")
    before = os.stat(path, dir_fd=parent_fd, follow_symlinks=False)
    if not stat_mod.S_ISDIR(before.st_mode):
        raise OSError("index ancestor is not a real directory")
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                 dir_fd=parent_fd)
    try:
        after = os.fstat(fd)
        if (not stat_mod.S_ISDIR(after.st_mode)
                or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)):
            raise OSError("index directory changed identity")
    except BaseException:
        os.close(fd)
        raise
    return fd


@contextlib.contextmanager
def _plan_index_directory(cwd: str) -> Iterator[int]:
    """Hold the repository/.claude/plans descriptor chain for the scan."""
    descriptors: List[int] = []
    try:
        descriptors.append(_open_index_directory(os.path.abspath(cwd)))
        for component in (".claude", "plans"):
            descriptors.append(_open_index_directory(component, descriptors[-1]))
        yield descriptors[-1]
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def _read_index_plan(
    directory_fd: int, name: str,
    limit: int = _LEDGER_AC_SCAN_MAX_BYTES + 1,
) -> bytes:
    """Read a bounded regular leaf; never follow a link or block on a FIFO.

    ``limit`` is the byte cap of the CALLER, because the two call sites
    promise different ceilings: the AC index reads cap+1 so it can DETECT
    overflow, while the ledger reader keeps its own smaller 64 KiB cap.
    """
    if not all(hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_NONBLOCK")):
        raise OSError("no-follow nonblocking file reads unavailable")
    before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if not stat_mod.S_ISREG(before.st_mode):
        raise OSError("index plan is not a regular file")
    # O_NONBLOCK covers a regular-to-FIFO swap between stat and open;
    # fstat then refuses the changed type/identity before any read.
    fd: Optional[int] = os.open(
        name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd,
    )
    try:
        with os.fdopen(fd, "rb") as fh:
            fd = None  # the file object now owns the descriptor
            after = os.fstat(fh.fileno())
            if (not stat_mod.S_ISREG(after.st_mode)
                    or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)):
                raise OSError("index plan changed type or identity")
            return fh.read(limit)
    finally:
        if fd is not None:
            os.close(fd)


def _ac_path_index_mirror(
    cwd: str, deadline: float
) -> Tuple[Dict[str, str], bool]:
    """``(AC path -> PLAN-NNN, complete)`` — perna plan_ac espelhada.

    Bounded pelos MESMOS caps do checkpoint + o wall deadline
    compartilhado; em path repetido o MENOR plan id vence (determinismo).
    Nada aqui consulta session state, env ou audit log (emenda r1-C6).

    Rail r15 P2-b: ``complete=False`` em QUALQUER corte — enumeracao falha,
    >200 arquivos de plano (o slice esconderia planos), deadline no meio,
    arquivo ilegivel, ou AC alem do cap de 256 KiB de UM arquivo (lido
    cap+1 para detectar). Um mapeamento parcial elege plano ERRADO no
    tie-break do chamador; o chamador recusa o indice inteiro. The AC grammar
    and matching rules mirror the checkpoint; filesystem reads additionally
    require a no-follow directory chain and a stable regular-file identity.
    An unsafe candidate invalidates the whole index, including earlier ACs.
    """
    index: Dict[str, str] = {}
    try:
        if time.monotonic() >= deadline:
            return {}, False
        with _plan_index_directory(cwd) as directory_fd:
            # Scan the held descriptor itself: a second pathname-based glob
            # could follow an ancestor replaced after the directory checks.
            # scandir errors remain visible (glob otherwise swallows them).
            all_files: List[str] = []
            with os.scandir(directory_fd) as entries:
                for entry in entries:
                    if time.monotonic() >= deadline:
                        return {}, False
                    if not fnmatch.fnmatchcase(entry.name, _LEDGER_PLAN_FILE_GLOB):
                        continue
                    all_files.append(entry.name)
                    if len(all_files) > _LEDGER_AC_SCAN_MAX_FILES:
                        return {}, False
            all_files.sort()
            for plan_file in all_files:
                if time.monotonic() >= deadline:
                    return {}, False
                m = _LEDGER_PLAN_FILE_ID_RE.match(plan_file)
                if m is None:
                    continue
                plan_id = m.group(1)
                raw_bytes = _read_index_plan(directory_fd, plan_file)
                if len(raw_bytes) > _LEDGER_AC_SCAN_MAX_BYTES:
                    return {}, False
                text = raw_bytes.decode("utf-8", "replace")
                for ac_path in _LEDGER_AC_PATH_RE.findall(text):
                    candidate = ac_path.strip().strip("`").strip()
                    # "./" is a PREFIX, not a character class: lstrip
                    # would remove the leading dot from `.claude/...`.
                    while candidate.startswith("./"):
                        candidate = candidate[2:]
                    if not candidate or candidate.startswith("<"):
                        continue
                    current = index.get(candidate)
                    if current is None or plan_id < current:
                        index[candidate] = plan_id
            if time.monotonic() >= deadline:
                return {}, False
    except FileNotFoundError:
        # ENOENT is ABSENCE, not unsafe input: an adopter with no
        # `.claude/plans`, or a plan file that vanished mid-scan. The
        # index is refused either way; staying silent keeps the
        # breadcrumb below forensic instead of firing on every
        # PreCompact of such a repo.
        return {}, False
    except Exception:
        _breadcrumb("plan AC index unavailable or unsafe — refusing partial scope")
        return {}, False
    return index, True


def _ledger_index(cwd: str, deadline: float) -> Dict[str, Any]:
    """PLAN-179 W2 US7 — the snapshot's LEDGER INDEX (a pointer, not a copy).

    Derives the active plan from the PATHS of the last commit — NEVER from
    ``_resolve_plan_id`` (emenda r1-C6: a trigger derived from session state
    re-inherits root cause E2; ``check_ledger_checkpoint.derive_scope``
    established the paths-only discipline and BOTH its legs are mirrored
    LITERALLY, not imported — hook contract forbids hook-to-hook imports:
    plan_dir paths AND AC-declared implementation paths (plan_ac, rail r6
    P2-c via ``_ac_path_index_mirror``); most in-scope paths wins, ties
    break on the LOWEST plan id). Returns

      ``{plan_id, ledger_path, present, sections, last_commit}``

    or ``{}`` when no plan is derivable from paths. ``sections`` (``## ``
    headers, sanitized + clamped, ≤5) and ``last_commit`` live in the
    SNAPSHOT for the /memory-scratchpad recall path; the PostCompact half
    renders only the STRUCTURAL pair (path + short sha) — section titles
    are file content and never enter the instruction stream (same Codex R5
    P1-1 doctrine as the checkbox label). Fail-open on every git/IO
    failure; bounded by the shared wall deadline."""
    # Rail r10 P2-b: o indice e OPCIONAL e roda ANTES do _write_snapshot —
    # a fatia dele no budget compartilhado e limitada, reservando o resto
    # para o snapshot e os passos de gate que ainda tem timeouts fixos
    # proprios. Um repositorio lento degrada o INDICE, nunca o snapshot.
    deadline = min(deadline, time.monotonic() + _LEDGER_INDEX_MAX_SHARE_S)
    if time.monotonic() > deadline:
        return {}
    # Rail r9 P2-a: `-m` porque um commit de MERGE sob combined-diff
    # devolve lista VAZIA (o pointer sumia em commit valido); `-z` porque
    # o quoting C de nomes nao-ASCII (`"src/\303\251.py"`) nunca casaria
    # shape nem AC. Rail r26 P1-a: `--first-parent` porque `-m` sozinho
    # devolve a UNIAO dos diffs contra TODOS os parents — num merge, as
    # mudancas que ja estavam na MAINLINE entravam no tie-break e um
    # PLAN-010 do historico vencia o PLAN-042 que o merge de fato
    # INTRODUZIU (pointer errado). O delta vs primeiro parent e o que o
    # merge trouxe. Rail r10 P2-c: o slice cap vem ANTES do dedupe
    # (materializacao limitada mesmo num commit gigante).
    names = _git(
        ["log", "-1", "-m", "--first-parent", "--name-only",
         "--format=", "-z"], cwd,
        timeout_s=deadline - time.monotonic(), raw=True,
    )
    if not names:
        return {}
    # Rail r11 P2-c: paths VERBATIM — `-z` ja da os limites exatos e um
    # strip por path colaria ` .claude/...` (filename legal com espaco)
    # no path canonico do plano, apontando o pointer ERRADO. Filtra so
    # campos vazios. Rail r11 P2-d: `maxsplit` limita a materializacao de
    # strings pequenas; o residuo (ultimo elemento) cai no slice. O
    # output em si ja e limitado por timeout x throughput da fatia de
    # 1.0s (r10) — fronteira declarada, transiente e sub-segundo.
    _parts = names.split("\0", _LEDGER_GIT_PATHS_MAX)
    # Rail r14 P2-a: derivacao de escopo PARCIAL nao elege plano — um
    # tie-break sobre contagens truncadas pode apontar o LEDGER ERRADO
    # (pior que nenhum). Qualquer truncamento => {}. Rail r15 P3-c: o
    # residuo do maxsplit e truncamento SO se carrega path de verdade —
    # em exatamente 2000 paths o NUL final produz um residuo VAZIO e um
    # commit legitimo no limite perderia o pointer.
    truncated = (
        len(_parts) > _LEDGER_GIT_PATHS_MAX
        and _parts[_LEDGER_GIT_PATHS_MAX] not in ("", "\n")
    )
    seen_paths = list(dict.fromkeys(
        p
        for p in _parts[:_LEDGER_GIT_PATHS_MAX]
        if p and p != "\n"
    ))
    counts: Dict[str, int] = {}
    unmatched: List[str] = []
    for stripped in seen_paths:
        pid = _plan_id_from_path(stripped)
        if pid is not None:
            counts[pid] = counts.get(pid, 0) + 1
        else:
            unmatched.append(stripped)
    # Rail r6 P2-c: derive_scope tem DUAS pernas e o espelho trazia so a
    # primeira — um commit tocando apenas implementation paths declarados
    # por AC (`[P?][USn][path]`) derivava indice VAZIO, e o US7 omitia o
    # pointer exatamente no commit que o checkpoint-rail associa a um
    # plano. A perna plan_ac roda so para paths nao-casados, sob o mesmo
    # deadline (prefix-match de diretorio identico ao derive_scope).
    if unmatched:
        # Rail r9 P2-b: o matching e O(paths x ACs) e o mirror pode
        # retornar JA no deadline — sem cap nem re-check, um commit
        # gigante estourava o budget do PreCompact ANTES do
        # _write_snapshot (perder o snapshot para ganhar um pointer e
        # inverter a prioridade do hook). Cap + deadline por path.
        # Rail r14 P2-a: exaustao ou cap NAO seguem com contagem
        # parcial — escopo truncado elege plano ERRADO no tie-break;
        # marca e recusa abaixo.
        if len(unmatched) > _LEDGER_AC_MATCH_MAX_PATHS:
            truncated = True
        if time.monotonic() > deadline:
            truncated = True
        elif not truncated:
            _ac_index, _ac_complete = _ac_path_index_mirror(cwd, deadline)
            # Rail r15 P2-b: espelho INCOMPLETO (>200 planos, arquivo
            # ilegivel, AC alem do cap por-arquivo, deadline) elege plano
            # errado no tie-break — recusa o indice inteiro.
            if not _ac_complete:
                truncated = True
                _ac_index = {}
            if _ac_index:
                for path in unmatched:
                    if time.monotonic() > deadline:
                        truncated = True
                        break
                    pid = _ac_index.get(path)
                    if pid is None:
                        for ac_path, candidate in _ac_index.items():
                            if ac_path.endswith("/") and path.startswith(ac_path):
                                pid = candidate
                                break
                            if path.startswith(ac_path + "/"):
                                pid = candidate
                                break
                    if pid is not None:
                        counts[pid] = counts.get(pid, 0) + 1
            # O mirror pode ter parado NO deadline com indice incompleto:
            # o re-check pos-fase cobre essa perna tambem.
            if time.monotonic() > deadline:
                truncated = True
    if truncated:
        return {}
    if not counts:
        return {}
    best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    rel = ".claude/plans/%s/LEDGER.md" % best
    out: Dict[str, Any] = {
        "plan_id": best,
        "ledger_path": _sanitize_text(rel, _PATH_CLAMP),
        "present": False,
        "sections": [],
        "last_commit": "",
    }
    # rc.1 re-pass part 5 H3 — `os.path.isfile` follows symlinks, and so did
    # the pathname `open` this block used. A `.claude/plans/PLAN-NNN/LEDGER.md`
    # symlinked OUTSIDE the repository made this reader copy up to 64 KiB of
    # Markdown headings from ANOTHER tree into the continuity snapshot
    # (reproduced: an `## EXFIL-HEADING-OUTSIDE-REPO` heading landed in the
    # blob). Leaf-only `O_NOFOLLOW` did NOT close the class: a symlinked
    # `PLAN-NNN` ANCESTOR was still traversed and delivered the same external
    # bytes (re-reproduced on the cured AC-index tree). The chain the AC index
    # opens component by component is REUSED here, so neither an ancestor nor
    # the leaf can be a link. Fail-closed on INPUT is the house rule
    # (CLAUDE.md §4): a ledger this reader cannot prove is a regular
    # file inside the tree yields a DEGRADED index, never external content.
    # Fail-OPEN on infrastructure is unchanged — every refusal here returns
    # the degraded pointer, never an exception into `gate()`.
    try:
        with _plan_index_directory(cwd) as _plans_fd:
            _plan_fd = _open_index_directory(best, _plans_fd)
    except Exception:
        # Absent, or an ancestor this reader cannot prove is a real directory:
        # the honest "no ledger yet" answer.
        return out
    try:
        try:
            _lst = os.stat("LEDGER.md", dir_fd=_plan_fd, follow_symlinks=False)
        except OSError:
            # Absent, or a leaf we cannot stat: the honest "no ledger yet".
            return out
        if stat_mod.S_ISLNK(_lst.st_mode):
            _breadcrumb("ledger is a symlink — refusing to follow (degraded)")
            return out
        if not stat_mod.S_ISREG(_lst.st_mode):
            _breadcrumb("ledger is not a regular file — index degraded")
            return out
        out["present"] = True
        # Rail r1 P2-5: the shared wall deadline is re-checked before EACH
        # further step — on a slow repository the first `git log` can consume
        # most of the budget, and an unconditional follow-up would run its own
        # fixed 2s timeout PAST the deadline, delaying the compaction beyond
        # the hook's stated budget. A degraded index (no sections / no sha) is
        # honest; a late one is not.
        if time.monotonic() > deadline:
            return out
        try:
            # Rail r17 P2-d: leitura BINARIA — read(n) de TextIO conta CHARS e
            # um LEDGER multibyte estourava o teto declarado em BYTES. O helper
            # confinado mantem o cap de 64 KiB, recusa link e folha nao-regular,
            # nao bloqueia em FIFO e re-checa tipo+identidade por fstat DEPOIS
            # do open, fechando a janela TOCTOU do stat acima.
            text = _read_index_plan(
                _plan_fd, "LEDGER.md", _LEDGER_INDEX_MAX_BYTES,
            ).decode("utf-8", "replace")
            sections: List[str] = []
            for line in text.splitlines():
                if time.monotonic() > deadline:
                    break
                if line.startswith("## "):
                    sections.append(_sanitize_text(line[3:].strip(), _LABEL_CLAMP))
                    if len(sections) >= _LEDGER_INDEX_MAX_SECTIONS:
                        break
            out["sections"] = sections
        except OSError as exc:
            # Covers the identity/type change the old inline fstat reported
            # separately: the section list stays EMPTY on both paths. The only
            # delta is that the repo-derived last_commit below still runs; no
            # attacker-controlled byte reaches the snapshot through it.
            _breadcrumb("ledger read failed (%s)" % str(exc)[:60])
    finally:
        os.close(_plan_fd)
    if time.monotonic() > deadline:
        return out  # rail r1 P2-5: no second git call past the deadline
    out["last_commit"] = _sanitize_text(
        _git(
            ["log", "-1", "--format=%h", "--", rel], cwd,
            timeout_s=deadline - time.monotonic(),  # rail r2 P2-f
        ),
        16,
    )
    return out
