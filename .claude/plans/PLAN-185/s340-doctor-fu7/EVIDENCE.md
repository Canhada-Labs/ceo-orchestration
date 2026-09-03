# EVIDENCE — pack `doctor-fu7` (S340, 2026-09-02/03)

> **Versão LANDADA: v4 do derivador (16 edições / 3 paths).** As seções 1–9 abaixo são a
> evidência da **v1** construída na sombra do builder (9 edições; sha do diff
> `eb857692ed3b8a43cbbd8adba89755a2ced494be2562b1a268e4d3ec8fa99bae`) e ficam como histórico da
> construção. O que foi commitado é descrito em **«Land — S340»** no fim deste arquivo e em
> `rail-round-{2,3,4}.md`; `baseline-diff.txt` (HEAD × final) e `regen-baseline.txt` (baseline
> final, com os dois sítios `>/dev/null` declarados) foram REGENERADOS para a v4.

- **Base:** `b6dce787651aaa9c06e842ce9d665cfb9d201ecd` (o commit do pack sonnet5).
- **Sombra do builder (v1):** `<scratch>/shadow-doctor-fu7`.
- **Derivador:** `apply-doctor-fu7.py` (v4 no commit; v1 = 9 edições, sha do diff acima).

Os números das seções 1–9 foram medidos **DEPOIS da última edição da v1** (a sombra foi
recriada do zero e re-derivada quando o passo de regeneração do baseline entrou no script).

## 1. Derivação reproduzível

```
$ git -C <repo> worktree add --detach <scratch>/shadow-doctor-fu7 HEAD
$ python3 apply-doctor-fu7.py --list-paths
scripts/doctor.sh
scripts/tests/test-installer-write-safety-e2e.sh
.claude/scripts/data/installer-write-safety-baseline.txt

$ python3 apply-doctor-fu7.py --root <SHADOW> --check-only ; echo rc=$?
apply-doctor-fu7: 9 edicao(oes) aplicaveis em 2 path(s); nada escrito
rc=0

$ python3 apply-doctor-fu7.py --root <SHADOW> ; echo rc=$?
apply-doctor-fu7: 9 edicao(oes) aplicadas em 3 path(s): ...
rc=0

$ python3 apply-doctor-fu7.py --root <SHADOW> --check-only ; echo rc=$?   # 2a vez
apply-doctor-fu7: RECUSADO
  - scripts/doctor.sh: ja contem '_mark_dropped' — arvore ja patchada?
  - scripts/tests/...: ja contem a perna D.5 — arvore ja patchada?
  - scripts/doctor.sh: ancora '...' ocorre 0 vez(es), esperado 1   (x5)
rc=1
```

## 2. Oráculo de canonicidade — 3/3 LIVRES

```
$ python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>
scripts/doctor.sh                                          0
scripts/tests/test-installer-write-safety-e2e.sh           0
.claude/scripts/data/installer-write-safety-baseline.txt   0
```

## 3. Bancada final (sombra `eb857692…`)

| # | comando | resultado |
|---|---|---|
| 1 | `bash -n scripts/doctor.sh` / `… test-installer-write-safety-e2e.sh` | **OK** (ambos) |
| 2 | `shellcheck -S warning` nos dois `.sh` | **limpo** (rc 0, zero saída) |
| 3 | `bash scripts/tests/test-installer-write-safety-e2e.sh` | **152 passed / 0 failed**, rc 0 |
| 4 | `bash scripts/tests/test-doctor.sh` | **44 passed / 0 failed**, rc 0 |
| 5 | `bash scripts/tests/test-doctor-delivery-route.sh` | **113 passed / 0 failed**, rc 0 |
| 6 | `bash scripts/tests/test-manifest-delivery-route.sh` | **127 passed / 0 failed**, rc 0 |
| 7 | `python3 .claude/scripts/check-installer-write-safety.py` (ratchet) | **rc 0** — «every blocking site is recorded» |
| 8 | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider .claude/scripts/tests/test_check_installer_write_safety.py .claude/scripts/tests/test_parity_source_resolution.py` | **161 passed** em 21,89 s |
| 9 | `bash scripts/tests/smoke-install.sh` | **rc 0** — «==> smoke install OK» (macOS: os 11 steps do CI entregue são LISTADOS, não executados — perna de execução é Linux/`CI=true`) |

**e2e antes × depois** (mesmo comando, mesma sombra antes de aplicar o pack):
**143 passed / 0 failed → 152 passed / 0 failed** (+9 asserções: 4 em D.5, 5 em D.6).

## 4. Controle positivo — as pernas novas VEEM o defeito

Receita documentada no cabeçalho do próprio e2e: árvore pré-cura + o arquivo de
teste PATCHADO.

```
$ mkdir -p <scratch>/ctrl-head && git -C <repo> archive HEAD | tar -x -C <scratch>/ctrl-head
$ cp <SHADOW>/scripts/tests/test-installer-write-safety-e2e.sh <scratch>/ctrl-head/scripts/tests/
$ grep -c _mark_dropped <scratch>/ctrl-head/scripts/doctor.sh     ->  0   (pré-cura, confirmado)
$ bash <scratch>/ctrl-head/scripts/tests/test-installer-write-safety-e2e.sh ; echo rc=$?
    passed : 145
    failed : 7
rc=1
```

As **7** falhas são EXATAMENTE a metade-relatório das pernas novas:

```
FAIL D.5 — the ../ record was dropped SILENTLY (no DROPPED line in …/doctor.log)
FAIL D.5 — no 'Dropped:   1' summary line (see …/doctor.log)
FAIL D.5 — doctor exited 0 over a manifest it did not fully read
FAIL D.6 — a whole subtree was dropped SILENTLY (see …/doctor.log)
FAIL D.6 — no Dropped: line in the summary (see …/doctor.log)
FAIL D.6 — no cap line; expected more than 20 dropped records under .claude/scripts/
FAIL D.6 — doctor exited 0 while a whole subtree went unverified
```

**RED → GREEN:** as mesmas 9 asserções passam na sombra curada (item 3, linha 3).

**As 2 asserções de BYTES passam nas DUAS árvores — e isso é o relato honesto:**
a propriedade de segurança (nada é escrito fora do `$TARGET`) já valia pré-cura,
porque o descarte no ingest é o que a garante. O que estava quebrado, e o que o
controle prova que as pernas veem, é o RELATÓRIO: `rc=0` sobre um manifesto que o
doctor não conseguiu ler inteiro.

## 5. Medição que autoriza o `rc=1` (instalação sã descarta ZERO)

```
mode='copy'    manifest_records=535  verified=535  dropped=0  doctor_rc=0
mode='--link'  manifest_records=349  verified=349  dropped=0  doctor_rc=0
```

E o defeito, medido em `b6dce78` com um registro forjado
`<sha>  ../outside/victim.txt` acrescentado ao manifesto do adopter:

```
pré-cura : OK: 535 | Refused: 0 | (nenhuma menção ao registro) | rc=0
pós-cura : ==> Manifest records DROPPED at ingest — NOT verified below
             DROPPED (unsafe manifest path (traversal, absolute, control
             character, or symlinked ancestor)): ../outside/victim.txt
           Dropped:   1 (unsafe or malformed manifest records — NOT verified)
           rc=1     |  bytes do arquivo externo: IDÊNTICOS nas duas árvores
```

## 6. Saída de instalação SÃ fica byte-idêntica

Mesmo alvo instalado, dois doctors (HEAD × patchado):

```
$ diff <(bash <HEAD>/scripts/doctor.sh   $T) <(bash <SHADOW>/scripts/doctor.sh $T)
3c3
<     Source:   <repo>
---
>     Source:   <SHADOW>
```

Única diferença = a linha `Source:` (o path do checkout que roda), que não vem do
patch. A listagem e a linha `Dropped:` são condicionais a `DROPPED_COUNT > 0`.

## 7. Baseline do censo — regerado PELA FERRAMENTA, e verificado

O `apply-doctor-fu7.py` roda `check-installer-write-safety.py --write-baseline`
como subprocesso e compara o CONJUNTO de sítios (sem o número de linha) antes e
depois, recusando se mudou. Medido:

```
$ diff <(strip baseline_antigo) <(strip baseline_novo)   # strip = sem nº de linha, ordenado
(sem saída)  ->  SET-IDENTICAL: só renumeração
$ grep -c '^<' baseline-diff.txt  ->  291 linhas renumeradas
$ python3 .claude/scripts/check-installer-write-safety.py ; echo rc=$?  ->  rc=0
```

Nenhum sítio de escrita foi criado ou morto por este pack.

## 8. Pair-rail

1 rodada, veredito **APPROVE** (zero achados; o codex corrente não emite
`VERDICT:` — rodada limpa = ausência do bloco `Full review comments:`, medido com
âncora no início da linha: 0 ocorrências). **TREE-INTACT**: o sha do diff é o
mesmo antes e depois (`eb857692…`). Detalhe em `rail-round-1.md`, saída bruta em
`codex-r1.txt`.

## 9. Artefatos neste diretório

| arquivo | o que é |
|---|---|
| `apply-doctor-fu7.py` | o derivador (única forma de mudar a sombra) |
| `DESIGN-doctor-fu7-S340.md` | decisões, tabela de sítios, o que fica fora, residuais |
| `EVIDENCE.md` | este arquivo |
| `rail-round-1.md`, `codex-r1.txt` | a rodada de rail e sua saída bruta |
| `baseline-e2e.log` | e2e na sombra ANTES do pack (143/0) |
| `after-e2e.log` | e2e na sombra intermediária (152/0) — pré-regeneração do baseline |
| `final-e2e.log` | e2e na sombra FINAL (152/0) |
| `control-e2e.log` | controle positivo (145/7 contra árvore pré-cura) |
| `final-test-doctor.log`, `final-route.log`, `final-manifest-route.log` | oráculos de doctor |
| `ratchet.log`, `baseline-diff.txt`, `regen-baseline.txt` | evidência do censo |
| `smoke-install.log` | smoke install (rc 0) |

## Land — S340 (2026-09-03, madrugada autônoma) — versão landada: v4

- Base do land: `b6dce78` (mesma base da sombra). Rail no land: **r2 REJECT** (1 P1 + 2 P2 —
  `rail-round-2.md`), **r3** (1 P2 — `rail-round-3.md`), **r4** (1 P1 + 1 P2 — `rail-round-4.md`),
  todos REAIS ⇒ a cada rodada os 3 paths voltaram ao HEAD e o derivador foi re-aplicado do zero.
  **v4 = 16 edições / 3 paths**: E3 alargada + E10/E11/E12 (r2: qualquer byte de controle;
  relatório no ramo vazio; D.7), E13/E14 (r3: predicado `_field_has_control_bytes` independente
  de locale — C0/DEL byte a byte, C1 como UTF-8, bytes 8-bit soltos via `iconv`, fail-closed sem
  iconv; D.8), E15/E16 (r4: manifesto CRU com NUL recusado antes do loop, `exit 2`; D.9);
  `_apply` com snapshot/rollback atômico; `DECLARED_NEW_SITES` para os dois `>/dev/null` do
  predicado (qualquer outro sítio de escrita segue recusado pelo censo do pack). `--check-only`
  rc 0 → apply → `--check-only` rc 1 (recusa nomeada). Oráculo `--is-canonical` = 0 nos 3 paths.
- Bateria v4 na árvore viva, após a última edição: e2e `test-installer-write-safety-e2e.sh`
  **161/0** (D.7, D.8 e D.9 3/3 cada); `test-doctor.sh` 44/0; `test-doctor-delivery-route.sh`
  113/0; `test-manifest-delivery-route.sh` 127/0; pytest (`test_check_installer_write_safety.py`
  + `test_parity_source_resolution.py`) 161 passed; `smoke-install.sh` rc 0; ratchet rc 0;
  `bash -n` + `shellcheck -S warning` rc 0.
- Controles positivos: (a) e2e sobre árvore PRÉ-CURA = **146/9** — D.7 vermelho em «registro NÃO
  descartado» e «ESC cru» (+ as 7 pernas-relatório de D.5/D.6); (b) e2e sobre HEAD + derivador
  **v2** = **156/2** — D.8 vermelho em «não descartado sob LC_ALL=C» e «0x9b cru»; (c) e2e sobre
  HEAD + derivador **v3** = **160/1** — D.9 vermelho em «sem recusa de NUL»; (d) rollback do
  derivador: censo sabotado (`exit 1`) em worktree ⇒ `RECUSADO`, porcelain só com o sabotador;
  (e) a v3 sem `DECLARED_NEW_SITES` foi recusada pelo próprio censo do pack, com rollback limpo.
- Sonda direta do predicado, idêntica sob `LC_ALL=C.UTF-8` e `LC_ALL=C`: `0x9b` cru, `ESC`,
  `C2 9B`, `DEL` → UNSAFE; `relatório.md`, `Çx.md` → ok. Sonda do NUL: `tr -cd '\000' | wc -c`
  conta 1 num fixture com um NUL.
- Refutação: o refutador Opus reproduziu a derivação v1 byte a byte no próprio worktree,
  confirmou oráculo 0, instalação sã com zero descartes e saída byte-idêntica, e reproduziu o
  defeito (descarte silencioso) — interrompido antes do veredito formal por um pedido de
  permissão do harness a subagentes do `Agent` tool (classe registrada na memória S340). Rail do
  builder: r1 APPROVE (codex reproduziu 152/0 na sombra). Logs brutos e `codex-r*.txt` ficaram
  fora do commit (precedente S338): DESIGN, EVIDENCE, script, `baseline-diff.txt`,
  `regen-baseline.txt` (regenerados para a v4) e `rail-round-{1..4}.md`.
