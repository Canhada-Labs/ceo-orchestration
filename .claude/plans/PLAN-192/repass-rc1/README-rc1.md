<!-- Material do kit de corte da v1.4.1-rc.1 (PLAN-192). Este arquivo é rastreado ANTES do
     candidato e não muda no commit do veredito: o guard de delta o recusaria por nome. -->

# Re-pass do candidato v1.4.1-rc.1 — escopo, o que fica de fora e critério de parada

## 1. O que é esta release, medido

Patch FORA DE ORDEM sobre o GA v1.4.0 (tag `23b79dda` → commit `f9db82ec`, 2026-09-15). Medido em
2026-09-18 sobre `v1.4.0..737814a5` (antes da relmeta e do bump): 101 arquivos, dos quais 58 em
`.claude/plans/` e 6 em `docs/research/`; os outros 37 são o que este re-pass divide entre «dentro» e
«fora». Os três diffs das partes abaixo têm 54 / 34 / 82 KB a `-U1`, muito abaixo do teto do redator
(262.144 bytes sobre o INPUT); o bump acrescenta 12 arquivos de uma linha à parte 2.

Depois dessa medição landou a correção da cifra aproximada de testes nos docs (`~15,400` → `~16,200`;
o `verify-counts` completo do preflight acusava drift: 16.231 coletados, fora da banda de ±5 %). Ela
toca 9 arquivos de uma ou duas linhas; `docs/FAQ.md` e `docs/WHAT-WE-ARE.md` entraram na parte 2 por
causa dela, e `CLAUDE.md` segue fora (§4).

**Rodada 2.** A rodada 1 (candidato `9e9840b2`, o commit do bump) devolveu `NO-GO` nas três partes por
cinco condições declaradas falsas contra o código — 7, 10, 12, 14 e 15 —, sem P0. Está arquivada em
`.claude/plans/PLAN-192/repass-rc1-20260918-NOGO-r1/`, com a triagem em `record.md`. O candidato da
rodada 2 corrige TEXTO e nenhum código: as condições, o `CHANGELOG.md`, os dois docs de operador e este
README. Os achados de código da rodada 1 seguem abertos e declarados (seção D das condições).

## 2. As três partes, na ordem de risco para o adopter

| parte | o que é | por que nesta ordem |
|---|---|---|
| 1 | `.claude/hooks/check_workflow_launch.py` + `.claude/hooks/_lib/launch_ledger.py` | é o código que RODA na sessão do adopter, antes e depois de toda chamada da tool `Workflow`, e é o único que pode BLOQUEAR |
| 2 | `.claude/settings.json`, `templates/settings/**`, `scripts/build-plugin.py`, `.claude/scripts/env-inventory.json`, `CHANGELOG.md`, `INSTALL.md`, `README.md`, `README.pt-BR.md`, `npm/**`, os sítios de versão do bump (`VERSION`, `.claude/.framework-version`, `.claude-plugin/**`, `pyproject.toml`, `SBOM.md`, `SECURITY.md`, `VERSIONING.md`, `docs/ARCHITECTURE.md`) e os docs de inventário (`docs/COMMAND-SKILL-HOOK-MAP.md`, `docs/CTO-GUIDE.md`, `docs/GUIA-COMPLETO.md`, `docs/README.md`, `docs/FAQ.md`, `docs/WHAT-WE-ARE.md`) | é por onde o hook CHEGA (ou não chega) registrado, e é onde a release afirma coisas ao adopter |
| 3 | `.claude/scripts/ceo-launches.py`, `approval_gate.py`, `test_refs.py`, `mutant_sandbox.py`, `worktree_lock.py`, `phase_checkpoint.py`, `docs/workflow-recovery.md`, `docs/approval-gate.md` | são chamadas por vontade do operador; nenhuma roda sozinha |

### O manifesto de cada parte é DERIVADO, nunca uma lista fixa

A pathspec acima é a INTENÇÃO; `paths-rc1-N.manifest.txt` é derivado dela contra o candidato no momento
do run (`git diff --name-only v1.4.0..candidato -- <pathspec>`). Os sítios de versão só mudam no commit
do bump, que é o candidato: uma lista medida antes esqueceria exatamente eles.

## 3. Cobertura anterior, citada dentro do próprio prompt

- Partes 1 e 3 (`ceo-launches.py`): PLAN-190 W1 — debate r1 (3 críticos, consenso PROCEED) e SEIS
  rodadas de pair-rail, as cinco primeiras `NO-GO` com cura de classe a cada uma; a r6 foi a rodada
  final, sem P0; assinado pelo Owner em `075beed9`. O P2 da r6 sobre `relaunch --out` é a W1.1, curada
  neste delta com prova por mutação.
- Parte 2: a registração nos templates viajou no mesmo patch assinado da W1; os sítios de versão são
  escritos pelo `release.sh bump` e não têm rail próprio.
- Parte 3, as cinco CLIs de W2/W3: landaram LIVRES, com testes e SEM rodada de pair-rail. **A rodada 1
  deste re-pass foi a primeira revisão cruzada delas** e achou pelo menos um P1 ou P2 em cada uma das
  cinco — abertos, listados no `CHANGELOG.md` `[1.4.1]` e nos vereditos arquivados.

## 4. O que fica FORA, e por quê

| fora | motivo |
|---|---|
| `.claude/hooks/tests/**`, `.claude/scripts/tests/**`, `tests/**` (inclui as fixtures) | não são entregues a adopters; são o oráculo, e o oráculo roda no CI do candidato |
| `.claude/plans/**`, `docs/research/**` | registro de trabalho; não são entregues |
| `CLAUDE.md` | contrato de operação DESTE repositório; o adopter recebe `templates/CLAUDE.md`, que não mudou |
| `.claude/governance/codex-cli-pin.txt` e `codex-cli-pin-manifest.json` | re-pin do codex sob cerimônia assinada própria (`PLAN-189/codex-pin*/`); `.claude/governance/` não é entregue a adopters |
| `.claude/scripts/local/release.sh`, `.claude/governance/gate-scripts-manifest.txt`, `.claude/scripts/tests/test_release_bump_sites.py` | a relmeta-141, sob cerimônia assinada própria (`PLAN-192/relmeta/`); engenharia de release. O manifesto e o teste não são entregues. O `release.sh` É entregue, só pelo `upgrade.sh` (ele enumera `.claude/scripts/` recursivamente e o predicado de exclusão não exclui `.claude/scripts/local/`; a instalação fresca copia só o nível de cima) — a rodada 1 corrigiu esta linha, que dizia «não entregue» |

Do que está fora, só o `release.sh` chega à árvore de um adopter, e nenhum hook, comando, settings,
template, skill ou script de nível de cima entregue o referencia. A divergência instalação × upgrade
sobre `.claude/scripts/local/` é achado aberto da rodada 1.

## 5. Critério de parada (fixado ANTES da 1.ª rodada — PLAN-192 §Approach)

- `NO-GO` só por condição declarada FALSA contra o código ou por P0. Um P1 não declarado vai para
  «NEW FINDINGS (annex)» e entra no material assinado.
- No máximo DUAS rodadas de re-pass. Se a 2.ª ainda der `NO-GO`, PARAR e levar as duas ao Owner. Não há
  3.ª rodada por conta própria.
- Uma parte morta por capacidade do modelo (sem veredito, com a assinatura do servidor no transcript)
  NÃO é uma rodada: o runner a re-tenta até 2 vezes e a PROVENANCE declara quantas mortes houve.
- Toda tentativa, completa ou parcial, é preservada: o runner recusa rodar por cima de evidência
  anterior. Para re-rodar, arquive o diretório inteiro como `repass-rc1-<data>-NOGO-rN/`.

## 6. As condições declaradas

`CONDITIONS-rc1.md`, neste diretório. Elas viajam em TODAS as partes como DADO para o revisor, e o
snapshot bruto que ele viu (`CONDITIONS-rc1.reviewed.md`) é o que entra nos fields assinados — mudar
uma vírgula depois da revisão exige novo re-pass. A condição 1 é a decisão do Owner sobre o anexo da
v1.4.0 (PLAN-192 OQ-1).

## 7. Codex pinado, sem tocar na máquina

O runner lê a versão de `.claude/governance/codex-cli-pin-manifest.json`, resolve `@openai/codex@<versão>`
por `npx` num cache próprio (`.npx-cache/`, ignorado pelo git), verifica o sha256 do payload nativo
contra o manifesto pelo mesmo oráculo do pair-rail-gate (`check_pair_rail.py --verify-codex-pin`,
fail-CLOSED) e põe um shim no início do PATH. O modelo vai por `-m`, lido da tabela raiz de
`~/.codex/config.toml` ou de `CODEX_MODEL`, e a PROVENANCE registra o valor e a origem.

## 8. Onde o candidato entra

O candidato é o HEAD de `origin/main` gravado em `CANDIDATE.sha` depois do CI verde — pelo passo 5 do
`OWNER-RC1-CUT.sh`, ou pelo CEO quando ele roda o re-pass antes da cerimônia (o passo 6 reconhece a
evidência completa e não re-roda). Na rodada 1 era o commit do bump (`release: v1.4.1`, `9e9840b2`); na
rodada 2 é o commit de correção de texto que senta sobre ele. O runner nunca lê o candidato de uma
constante, e o commit do veredito senta DIRETAMENTE sobre o candidato: `parent_sha` == pai do commit
que introduz o veredito.
