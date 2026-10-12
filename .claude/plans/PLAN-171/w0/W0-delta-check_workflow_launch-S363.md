# PLAN-171 W0-delta — `check_workflow_launch.py` pelo método das três metades (S363)

> **Escopo.** Um hook só: `.claude/hooks/check_workflow_launch.py`, com a
> biblioteca que decide por ele, `.claude/hooks/_lib/launch_ledger.py`.
> Ele entrou no `.claude/settings.json` em 2026-09-17, pelo `075beed9d5f3`
> (PLAN-190 W1), depois do censo W0. Por isso ficou fora do `L` da S348 e
> virou a «dívida nomeada» do §6 de `W0-consolidated-verdict-S348.md`.
> Este relatório é o item W2 de `PLAN-171-FOLLOWUP-lote2-generated-figures`.
>
> **Método.** O do lote 2 (`lote-2-S347.md` §4), com as três metades
> obrigatórias: verde como está, vermelho com o enforcement removido, verde
> de novo depois do `git restore`. Antes de CADA execução o driver purga o
> espelho de bytecode do clone sob `sys.pycache_prefix` (e qualquer
> `__pycache__` local) e roda o pytest com `PYTHONDONTWRITEBYTECODE=1`.
>
> **Medido em 2026-10-12, das 13:13:40Z às 13:15:05Z**, num clone
> descartável (`git clone --no-hardlinks`) do shadow do builder, no commit
> `572d3fbd98443daabb200f3f6a5ef67d3babdac1` (branch `s363/plans-pb2`; o
> hook e a biblioteca são os mesmos de `origin/main` `3e32a1ff0d5f`, sobre
> o qual o branch foi aberto). Nenhuma edição em árvore viva. O próprio
> driver apagou o clone e o espelho de bytecode dele ao terminar
> (`clone_exists_after_cleanup: false`, `mirror_exists_after_cleanup: false`).
> O driver está reproduzido inteiro no §6, com o sha256.

## 1. Registro, suítes e CI

- **Registro** (`.claude/settings.json`, par matcher → `command`, lido em
  2026-10-12): `PreToolUse` / `Workflow` (l. 362 → l. 366) e `PostToolUse` /
  `Workflow` (l. 532 → l. 536). O mesmo arquivo atende os dois eventos.
- **Onde está o enforcement.** O guard de retomada vive em `_guard` e é
  aplicado por `decide_pre` (definida na l. 950 de `_lib/launch_ledger.py`),
  na l. 968: `decision = _guard(manifest, resume, d, env)`. O hook devolve
  essa `decision` ao harness.
- **Suítes que exercitam o hook:**
  - `.claude/hooks/tests/test_check_workflow_launch.py` — 107 testes,
    ponta a ponta: subprocesso novo, evento JSON no stdin, decisão no stdout,
    do jeito que o `settings.json` invoca. Segundo o docstring do arquivo,
    cada caso isola `CLAUDE_PROJECT_DIR`, `HOME` e o diretório de auditoria
    numa árvore temporária.
  - `tests/unit/test_launch_ledger.py` — 29 testes das funções da
    biblioteca; segundo o docstring, num diretório de ledger temporário.
- **CI** (configuração lida, execução não exercitada aqui):
  `.claude/hooks/tests/` roda no `validate.yml`, job `hook-tests-dual-rail`
  (l. 1599; step na l. 1627) e job `hook-tests-python-matrix` (l. 1640; step
  na l. 1691), e também em `coverage.yml:108` e `release.yml:390`.
  `tests/unit` roda no `validate.yml`, job `validate` (l. 38), step «Run
  v1.0.1 test roots (PLAN-152 tests-01)» (l. 568). Os três jobs do
  `validate.yml` carregam `if: vars.CEO_SOTA_DISABLE != '1'` (l. 44, 1600 e
  1641): a execução deles é condicional, como o lote 2 já declarava.

## 2. Tabela

| # | Gate (hook) | Controle positivo (node id) | Como está | Enforcement removido | Restaurado | Verdito | O que o controle prova |
|---|---|---|---|---|---|---|---|
| 1 | workflow-launch (guard de retomada) | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_resume_with_different_args_is_blocked_with_counts_only_reason` | PASS | **FAIL** — `E AssertionError: None != 'block'` | PASS | **verde** | bloqueia a retomada de um Workflow quando os `args` diferem do lançamento registrado e ligado por `tool_use_id`, com motivo só de contagens |

O controle positivo roda dentro do arquivo dele; o resultado de cada
metade, por arquivo, é este (rc e linha final do pytest, copiados do log
de cada execução):

| Metade | Arquivo | rc | Linha final do pytest | `.pyc` purgados antes |
|---|---|---|---|---|
| (i) como está | `test_check_workflow_launch.py` | 0 | `107 passed in 25.60s` | 11 |
| (i) como está | `test_launch_ledger.py` | 0 | `29 passed in 0.47s` | 0 |
| (ii) mutante | `test_check_workflow_launch.py` | **1** | `25 failed, 82 passed in 24.82s` | 0 |
| (ii) mutante | `test_launch_ledger.py` | **1** | `3 failed, 26 passed in 0.49s` | 0 |
| (iii) restaurado | `test_check_workflow_launch.py` | 0 | `107 passed in 27.63s` | 0 |
| (iii) restaurado | `test_launch_ledger.py` | 0 | `29 passed in 0.57s` | 0 |

Antes da metade (iii), o driver confere a restauração: `git restore` com
rc 0, `git status --porcelain` vazio e a linha original de novo presente
uma única vez no arquivo.

Os 11 `.pyc` achados antes da primeira execução já estavam no espelho do
clone. O único processo Python que rodou com o clone como diretório
corrente antes dela foi a sonda `python3 -m pytest --version` do próprio
driver, que não usa `PYTHONDONTWRITEBYTECODE`. Uma sonda à parte, no
mesmo dia, confirmou a origem: num clone novo do mesmo commit, só esse
comando deixa 11 `.pyc` no espelho. A purga os removeu; nas cinco
execuções seguintes ela não achou nenhum.

## 3. O mutante

Uma linha de `decide_pre`. O guard continua rodando e gravando o
resultado no manifesto (`manifest["guard"]`); só a decisão que ele devolve
ao harness é descartada. Aplicado por substituição exata de texto, que o
driver exige casar uma única vez (`anchor_count: 1`). Diff medido no
clone:

```diff
diff --git a/.claude/hooks/_lib/launch_ledger.py b/.claude/hooks/_lib/launch_ledger.py
index 74b55cc5..2664c671 100644
--- a/.claude/hooks/_lib/launch_ledger.py
+++ b/.claude/hooks/_lib/launch_ledger.py
@@ -965,7 +965,7 @@ def decide_pre(event: Dict[str, Any], d: Path, env: Optional[Dict[str, str]] = N
     resume = manifest.get("resume_from_run_id") if manifest["guard"]["result"] == "none" else None
     if resume:
         try:
-            decision = _guard(manifest, resume, d, env)
+            _guard(manifest, resume, d, env)  # MUTANT W0-delta: decision discarded
         except Exception as exc:  # noqa: BLE001 — recorded, never silent
             manifest["guard"] = {"result": "inconclusive", "error": type(exc).__name__, "diff": [], "counts": {}}
             decision = {}
```

## 4. Os 28 testes que foram ao vermelho

Primeira linha `E` de cada falha, tirada do log da metade (ii). Nenhuma é
erro de coleta: as 28 falham numa asserção ou num acesso ao resultado do
hook.

- **20** afirmam o bloqueio diretamente (`None != 'block'`): 17 no arquivo
  ponta a ponta e as 3 do arquivo da biblioteca.
- **1** lê o motivo do bloqueio e cai em `KeyError: 'reason'`, porque o
  dicionário de bloqueio não chegou.
- **7** afirmam um aviso que o guard emite sem bloquear
  (`WORKFLOW-RESUME-ADVISORY`, `WORKFLOW-RESUME-FORCED`, `PROCEEDS`, o
  texto do vínculo heurístico, o `hookEventName` do `additionalContext`).
  Eles ficam vermelhos porque o mutante descarta toda a saída do guard, e
  não só o bloqueio.

| # | Node id | Primeira linha `E` |
|---|---|---|
| 1 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_a_script_path_record_without_a_snapshot_keeps_the_args_guard_and_no_script_verdict` | `E AssertionError: None != 'block'` |
| 2 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_absent_and_null_args_are_different_inputs_for_the_guard` | `E AssertionError: None != 'block' : recorded ABSENT, resumed with null` |
| 3 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_block_reason_names_the_deliberate_change_route_accurately` | `E KeyError: 'reason'` |
| 4 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_blocked_attempt_never_poisons_single_unbound_binding` | `E AssertionError: None != 'block'` |
| 5 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_blocked_script_only_attempt_is_never_a_binding_candidate` | `E AssertionError: None != 'block'` |
| 6 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_call_declaration_releases_a_script_only_block` | `E AssertionError: None != 'block'` |
| 7 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_deeply_nested_args_are_never_a_silent_unrecorded_allow` | `E AssertionError: None != 'block'` |
| 8 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_difference_at_the_end_of_a_long_value_is_blocked` | `E AssertionError: None != 'block'` |
| 9 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_env_force_releases_a_script_block_and_records_forced` | `E AssertionError: 'WORKFLOW-RESUME-FORCED' not found in '' : an env override is announced, never silent` |
| 10 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_force_declared_in_the_call_releases_that_call_only` | `E AssertionError: None != 'block'` |
| 11 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_force_records_and_allows` | `E AssertionError: 'WORKFLOW-RESUME-FORCED' not found in '' : a forced resume is announced, never silent` |
| 12 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_guard_advisory_mode_keeps_ledger_but_never_blocks` | `E AssertionError: 'WORKFLOW-RESUME-ADVISORY' not found in ''` |
| 13 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_hostile_script_paths_are_recorded_unreadable_and_args_still_guarded` | `E AssertionError: None != 'block' : args still differ: not_a_regular_file` |
| 14 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_key_order_change_is_blocked_and_relaunch_prints_the_original_order` | `E AssertionError: None != 'block'` |
| 15 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_lone_surrogates_in_inputs_still_record_and_still_block` | `E AssertionError: None != 'block' : an unencodable input must not turn a block into a silent allow` |
| 16 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_malformed_force_declarations_never_release` | `E AssertionError: None != 'block' : 'CEO_WORKFLOW_RESUME_FORCE:'` |
| 17 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_named_workflow_args_still_guarded_without_a_script_hash` | `E AssertionError: None != 'block' : an unavailable script hash never hides an args difference` |
| 18 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_notices_reach_the_model_as_additional_context` | `E AssertionError: None != 'PreToolUse'` |
| 19 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_only_the_exact_value_one_releases_through_the_environment` | `E AssertionError: None != 'block' : '0'` |
| 20 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_proceeding_advisory_never_asks_to_reissue_the_call` | `E AssertionError: 'PROCEEDS' not found in ''` |
| 21 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_resume_with_different_args_is_blocked_with_counts_only_reason` | `E AssertionError: None != 'block'` |
| 22 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_resume_with_different_script_same_args_is_advisory_by_default` | `E AssertionError: 'WORKFLOW-RESUME-ADVISORY' not found in ''` |
| 23 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_script_enforce_never_blocks_over_a_weak_bind` | `E AssertionError: 'bound heuristically' not found in '' : the advisory names the route (manual bind), not a flag already set` |
| 24 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_script_guard_enforce_blocks_script_change` | `E AssertionError: None != 'block'` |
| 25 | `.claude/hooks/tests/test_check_workflow_launch.py::CheckWorkflowLaunchE2E::test_write_failure_keeps_the_block_and_leaves_a_breadcrumb` | `E AssertionError: None != 'block' : a decision computed from valid evidence survives a write failure` |
| 26 | `tests/unit/test_launch_ledger.py::CompareAndIndex::test_a_computed_block_survives_a_failure_to_persist_the_call` | `E AssertionError: None != 'block'` |
| 27 | `tests/unit/test_launch_ledger.py::CompareAndIndex::test_decide_pre_records_every_call_and_blocks_only_verified_args_diff` | `E AssertionError: None != 'block'` |
| 28 | `tests/unit/test_launch_ledger.py::CompareAndIndex::test_unbound_launches_excludes_attempts_the_guard_blocked` | `E AssertionError: None != 'block'` |

## 5. O que este censo NÃO afirma

- **O mutante remove toda a saída do guard ao harness**: o bloqueio e os
  avisos. O vermelho prova que as suítes enxergam essa saída. Que elas
  enxerguem o bloqueio em particular está provado pelos 20 testes que o
  afirmam diretamente, não pelo total de 28.
- **A metade PostToolUse não foi alvo do mutante.** O vínculo do run id
  (`decide_post`) e a gravação do manifesto têm testes próprios, que
  continuaram verdes na metade (ii) (82 + 26) porque não dependem da
  decisão descartada. Sobre eles, este censo só afirma o «verde como
  está».
- Não afirma que o controle cobre a superfície inteira do hook, nem que o
  matcher `Workflow` casa em campo, nem que os jobs de CI rodam (a condição
  `CEO_SOTA_DISABLE` não foi exercitada).
- Um teste tem limite de tempo de relógio:
  `test_manifest_written_even_when_git_is_slow` exige que o hook responda em
  menos de 4 s com um `git` falso que dorme 4 s. Passou nas três metades
  nesta máquina, com outros agentes rodando ao mesmo tempo. Isso não prova
  que passe em qualquer runner.
- O vermelho foi obtido com UM mutante. Ele prova que as suítes enxergam
  esse mecanismo, não que o mecanismo esteja completo.

## 6. Como refazer

Driver usado nesta medição, byte a byte (137 linhas; sha256
`203eed5959002f57bb880be05e7be2e0b013d3808bc030d61269dc5ee243e9e7`). Para conferir que o bloco abaixo é o mesmo arquivo:

```
awk '/^```python census_driver.py$/{f=1;next} /^```$/{f=0} f' \
  .claude/plans/PLAN-171/w0/W0-delta-check_workflow_launch-S363.md | shasum -a 256
```

Invocação, com o shadow e um diretório de trabalho vazio (o clone nasce em
`<WORK>/clone` e é apagado no fim; o driver recusa rodar com menos de 20 GB
livres ou se `<WORK>/clone` já existir):

```
python3 census_driver.py <SHADOW> <WORK> s363/plans-pb2
```

```python census_driver.py
#!/usr/bin/env python3
"""W0-delta census of check_workflow_launch (PLAN-171-FOLLOWUP-lote2-generated-figures, W2).

usage: census_driver.py <SHADOW> <WORK> <BRANCH>
Three halves over a DISPOSABLE clone <WORK>/clone of <BRANCH> from <SHADOW>:
  (i) as-is, (ii) one mutant in _lib/launch_ledger.py decide_pre, (iii) after git restore.
Each test file runs in its OWN serial pytest process, PYTHONDONTWRITEBYTECODE=1, with the
clone's bytecode mirror under sys.pycache_prefix (and any local __pycache__) purged before
every run (lote-2 §4). Writes <WORK>/results.json + one log per run; deletes the clone and
its mirror at the end. Never writes to <SHADOW>. Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

TARGET = ".claude/hooks/_lib/launch_ledger.py"
OLD = "            decision = _guard(manifest, resume, d, env)\n"
NEW = "            _guard(manifest, resume, d, env)  # MUTANT W0-delta: decision discarded\n"
FILES = [".claude/hooks/tests/test_check_workflow_launch.py", "tests/unit/test_launch_ledger.py"]
PY = "/usr/bin/python3"


def sh(cmd, cwd=None, env=None, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def mirror_dir(clone: Path) -> Path:
    prefix = sh([PY, "-c", "import sys;print(sys.pycache_prefix)"])[1].strip()
    return Path(prefix + str(clone))


def purge(clone: Path) -> int:
    n = 0
    m = mirror_dir(clone)
    if m.is_dir():
        for _root, _dirs, files in os.walk(m):
            n += sum(1 for f in files if f.endswith(".pyc"))
        shutil.rmtree(m)
    for pc in list(clone.rglob("__pycache__")):
        if pc.is_dir():
            n += sum(1 for f in pc.iterdir() if f.suffix == ".pyc")
            shutil.rmtree(pc)
    return n


def first_e_lines(text: str) -> dict:
    cur, first = None, {}
    for ln in text.splitlines():
        m = re.match(r"^_+ (\S+) _+$", ln)
        if m:
            cur = m.group(1)
            continue
        if cur and ln.startswith("E ") and cur not in first:
            first[cur] = ln.strip()
    return first


def run_file(clone: Path, work: Path, half: str, f: str) -> dict:
    purged = purge(clone)
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_PROJECT_DIR")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [PY, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "-rf", "--tb=short", f]
    t0 = time.monotonic()
    rc, out, err = sh(cmd, cwd=str(clone), env=env)
    wall = round(time.monotonic() - t0, 1)
    (work / ("run-%s-%s.log" % (half, Path(f).stem))).write_text(
        "$ " + " ".join(cmd) + "\n" + out + "\n--- stderr ---\n" + err)
    lines = out.splitlines()
    summary = [ln for ln in lines if re.search(r"\d+ (passed|failed|error)", ln) and " in " in ln]
    return {"half": half, "file": f, "rc": rc, "summary": summary[-1] if summary else None,
            "failed": [ln.split(" ", 1)[1] for ln in lines if ln.startswith(("FAILED ", "ERROR "))],
            "first_e": first_e_lines(out), "pyc_purged_before": purged, "wall_s": wall}


def main(argv) -> int:
    shadow, work, branch = Path(argv[1]), Path(argv[2]), argv[3]
    clone = work / "clone"
    res = {"free_gb_before": round(shutil.disk_usage("/").free / 1e9, 1),
           "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if res["free_gb_before"] < 20 or clone.exists():
        print("ABORT: free disk < 20 GB or clone path exists")
        return 2
    projects = Path.home() / ".claude" / "projects"
    before = {p.name for p in projects.iterdir()} if projects.is_dir() else set()
    rc = sh(["git", "clone", "-q", "--no-hardlinks", "--single-branch", "--branch", branch,
             str(shadow), str(clone)], cwd=str(work))[0]
    if rc != 0:
        print("ABORT: clone rc=%d" % rc)
        return 3
    res["clone_head"] = sh(["git", "rev-parse", "HEAD"], cwd=str(clone))[1].strip()
    res["shadow_head"] = sh(["git", "rev-parse", "HEAD"], cwd=str(shadow))[1].strip()
    res["python"] = sh([PY, "--version"])[1].strip()
    res["pytest"] = " ".join(x.strip() for x in sh([PY, "-m", "pytest", "--version"], cwd=str(clone))[1:]).strip()
    res["status_asis"] = sh(["git", "status", "--porcelain"], cwd=str(clone))[1]
    runs = [run_file(clone, work, "asis", f) for f in FILES]
    tgt = clone / TARGET
    src = tgt.read_text(encoding="utf-8")
    res["anchor_count"] = src.count(OLD)
    if res["anchor_count"] != 1:
        print("ABORT: mutant anchor count != 1")
        return 4
    res["mutant_line"] = src[: src.index(OLD)].count("\n") + 1
    tgt.write_text(src.replace(OLD, NEW, 1), encoding="utf-8")
    res["mutant_diff"] = sh(["git", "diff", "--", TARGET], cwd=str(clone))[1]
    runs += [run_file(clone, work, "red", f) for f in FILES]
    res["restore_rc"] = sh(["git", "restore", "--", TARGET], cwd=str(clone))[0]
    res["status_restored"] = sh(["git", "status", "--porcelain"], cwd=str(clone))[1]
    res["anchor_count_restored"] = tgt.read_text(encoding="utf-8").count(OLD)
    runs += [run_file(clone, work, "restored", f) for f in FILES]
    res["runs"] = runs
    after = {p.name for p in projects.iterdir()} if projects.is_dir() else set()
    slug = str(clone).replace("/", "-")
    res["projects_dirs_with_clone_slug"] = sorted(n for n in after - before if n == slug or "work-lote2" in n)
    res["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    m = mirror_dir(clone)
    if m.is_dir():
        shutil.rmtree(m)
    shutil.rmtree(clone)  # confined: <WORK>/clone only
    res["clone_exists_after_cleanup"] = clone.exists()
    res["mirror_exists_after_cleanup"] = m.exists()
    (work / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    for r in runs:
        print(r["half"], r["file"], "rc=%d" % r["rc"], r["summary"], "red=%d" % len(r["failed"]),
              "pyc_purged=%d" % r["pyc_purged_before"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

Uma primeira execução, minutos antes (13:10:30Z às 13:11:55Z), com um
rascunho deste mesmo driver (caminhos fixos no código, limpeza feita à
mão), deu as mesmas seis linhas finais de pytest em contagem e o mesmo
conjunto de 28 testes vermelhos. Os números deste relatório são os da
segunda execução, a do driver acima.

## 7. Substrato

- Data: 2026-10-12 (UTC).
- Máquina: macOS 27.0.1 (build 26A434), arm64.
- Python: `/usr/bin/python3` 3.9.6; pytest 7.3.0; Claude Code 2.1.295.
- `sys.pycache_prefix` = `~/Library/Caches/com.apple.python`. Ele segue o
  `HOME`: os subprocessos do hook nos testes ponta a ponta recebem um
  `HOME` temporário e gravam o bytecode deles dentro da árvore temporária
  de cada teste.
- Disco livre antes da medição, lido pelo driver: 253,3 GB (10⁹ bytes).
- Nenhum diretório com o slug do clone apareceu em `~/.claude/projects`
  entre o início e o fim do driver.
