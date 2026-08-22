---
id: PLAN-174
title: Geração de cerimônia de release — template endurecido + lint de classes + cortes rc/GA declarativos
status: reviewed
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169]
budget_tokens: 250-450k (FIRMADO S302e r4; W1-W2 100-150k, W3 100-200k, W4 50-100k)
budget_sessions: 3-5
context_risk: medium
external_wait: "WAIVER DO OWNER (S316, 2026-08-20, chat): o milestone 'W3/W4 do 169 landados' foi waivado para W1-W2 — GA v1.3.0 saiu (2026-08-17), W3/169 landou (e5ce982), W4/169 segue aberta; o Owner autorizou W1-W2 ANTES dos trens 182/183 exatamente para baratear as cerimônias deles (baseline congelada por comando na W1: a classe de scripts consumiu 34 dos 44 rounds do trem v1.3.0 — a citação original '31/38' não reproduz do disco). W3-W4 DESTE plano mantêm o gate original. DEADLINE inalterado: slice W1-W3 verde até D-2 do corte v1.4.0-rc.1, senão ABORT-PATH: o corte usa a cerimônia manual e o piloto migra p/ o trem seguinte"
tags: [release, ceremony, codegen, review-cost, seed]
---

# PLAN-174 — A máquina gera o que hoje se revisa

> **SEMENTE (S302, 2026-08-11).** Nascida da auditoria total
> (framework-total-audit, 14 agentes): a MAIOR fatia isolada do custo
> de reviewer do trem v1.3.0 foi bash descartável de cerimônia — a
> semente citava "31 dos 38 rounds" revisando scripts one-shot (~94KB
> de bash bespoke, 6 scripts OWNER-* distintos num único trem), não
> produto. **[Correção do debate r1 (S316): o denominador da semente
> NÃO reproduz do disco — a contagem derivada por comando é 34 de 44
> rounds na classe de scripts; ver §4 e o catálogo. A DIREÇÃO da
> semente sobrevive (77% do custo), os números ficam substituídos.]**
> E a semente estimava ~40-50% de achados mecânicos recorrentes —
> medido no debate r1: ~34% (28 de ~83); a cauda que decide GO/NO-GO é
> semântica (seção B do catálogo).

## 1. Hipótese

Se os cortes rc/GA forem EMITIDOS por um gerador a partir de um input
declarativo pequeno (1-2KB: versão, tag, superfícies, gates, ordem),
o rail passa a revisar o INPUT + o gerador (uma vez, com soak) em vez
de 42KB de bash novo por trem. Efeito esperado (a medir): a classe
"27 rounds de scripts" cai para ~5.

## 2. Escopo

- **W1 — catálogo-DELTA contra o contrato que JÁ EXISTE** (reescrita
  pelo debate r1 — F1/F6/F8): `docs/OWNER-CEREMONY-CONTRACT.md` é o
  catálogo pré-existente não-enforçado (o MUST de geração tem
  conformidade **0/27** — nenhum script de cerimônia carrega
  `AUTO-GENERATED`). Entregáveis: (i) post-mortem de por que o MUST
  falhou (hipótese: o gerador serve canonical-edit com sentinel, não
  corte de tag/publish — se confirmada, o catálogo separa as DUAS
  famílias); (ii) mapa regra-do-contrato → enforcement
  (arquivo:linha | NENHUM); (iii) catálogo em DUAS seções — **A:
  lintáveis** (as 6 conhecidas + tag-baseline não verificada/pin
  nunca-lido + escrita via symlink no DESTINO + cura decorativa +
  exec-bit fora do binding) e **B: invariantes de máquina de estado**
  (retomada, idempotência, fronteira irreversível remota, binding de
  evidência por CONTEÚDO — a classe DOMINANTE, ~15 achados), que viram
  checklist do template W3 e pauta permanente do rail que o lint NÃO
  substitui; (iv) tabela classe→frequência→rounds derivada do corpus
  congelado (`SCRIPTS-MANIFEST.sha256`); (v) baseline do W4 congelada
  por comando citado; (vi) fronteira dos scripts de assinatura fora do
  repo (9 em `~/canhada-labs/`, 0 versionamento) DECLARADA — decisão do
  Owner entre trazê-los ao repo ou registrar fora-de-alcance, e **se a
  rota for fora-de-alcance, a claim de redução de custo e a baseline do
  W4 são recalculadas EXCLUINDO a família de assinatura no mesmo commit
  da decisão** (codex r1); (vii) ADR
  curto de disciplina de erro em cerimônia (`-e` sim/não + idioma de rc
  esperado — as duas metades do trem v1.3.0 usaram disciplinas opostas
  e AMBAS produziram defeito).
- **W2 — enforcement na ordem instrumento-existente-primeiro**
  (reescrita pelo debate r1 — F2/F4/F5; ordem corrigida pelo codex r1):
  (a) shellcheck sobre os scripts de cerimônia RODA DENTRO do workflow
  novo (job `shellcheck-ceremony`, flags cirúrgicas
  `check-extra-masked-returns`, SC2154, SC2034; NUNCA `--enable=all`) —
  a extensão do `find` do `validate.yml:306` é o passo de MIGRAÇÃO
  pós-183-W2, nunca deste lote; (b) descoberta por PROPRIEDADE DE
  CONTEÚDO — nunca glob de nome — em função única compartilhada, lista
  descoberta impressa, piso pinado que falha se o conjunto encolher, e
  controle positivo obrigatório: a classe `grep|tail -1` TEM de ser
  achada nos 4 `run-*.sh` de `PLAN-166/repass-*/`; (c)
  `.claude/scripts/check-ceremony-script.py` (stdlib + testes) SÓ para
  as classes que o shellcheck não expressa — regra 1 = check de
  proveniência `AUTO-GENERATED`; regras SEMÂNTICAS (a classe real é
  "`|| true` seguido de afirmação de sucesso sobre estado remoto
  irreversível", não `|| true` cru); split BLOCKING/ADVISORY; **a saída
  do lint carrega a linha literal de AUTOLIMITAÇÃO** ("cobre as classes
  sintáticas da seção A; NÃO cobre retomada, idempotência, fronteira
  irreversível remota nem binding de evidência — pauta do rail"), e
  isso é AC; **escape hatch com forma fixada**:
  `CEO_CEREMONY_LINT_UNLOCK=<sha256 do arquivo>` +
  `CEO_CEREMONY_LINT_UNLOCK_REASON` obrigatório, ambos no audit trail
  (evento advisory; unlock sem motivo = bloqueio mantido) — padrão
  ADR-186. Wire: job CI PRÓPRIO em arquivo de workflow NOVO e
  NÃO-templatizado (DECISÃO do CEO registrada no consenso, com a
  divergência de C anotada e herdeiro nomeado) — `validate.yml` só
  DEPOIS de o PLAN-183 W2 fixar o ramo do drift-gate. **CI é O GATE; a
  perna local é git hook clássico opt-in, ENTREGUE (instalador + doc),
  declarado bypassável e NUNCA contado como camada de enforcement** —
  `.git/hooks` está vazio hoje.
- **W3 — estender `generate-ceremony.sh`** para emitir cortes rc/GA
  de input declarativo; o gerado passa `bash -n` + lint W2 por
  construção; corpo ASCII-safe (lição heredoc-em-$()); retomada
  (MONITOR/SKIP_TO_PUSH/TERMINAL) vira feature do template, não
  reinvenção por trem.
- **W4 — piloto no primeiro corte da v1.4.0**: rail revisa input
  declarativo + diff do gerador; contar rounds e comparar com a
  baseline v1.3.0 (12-17h de reviewer externo/trem).

## 2b. Controles e rollback (Codex r1 — obrigatórios antes de W4)

- **Positive control do lint (W2):** o gate só entra com controle que
  FALHA quando o enforcement é removido (alinhado ao censo do
  PLAN-171 W0); cada classe **LINTÁVEL (seção A do catálogo)** tem
  caso-vermelho no CI — as invariantes da seção B têm checklist no
  template W3 e pauta de rail, NÃO caso de lint (codex r1: exigir
  caso-vermelho de classe declaradamente não-lintável era AC
  impossível).
- **Equivalência de invariantes (W3):** cerimônia GERADA passa suíte
  de equivalência — sentinel/anchor-sha/scope/dois-rails-de-signer
  PRESENTES e verificados; dry-run em clone compara as GARANTIAS
  (não os bytes) contra a cerimônia manual baseline; qualquer
  divergência de garantia = vermelho. **A lista canônica de garantias
  DERIVA de `docs/OWNER-CEREMONY-CONTRACT.md`** (debate r1) — sem lista
  canônica, o golden test é vacuous gate.
- **Loop de fechamento da revisão (AC do W3, registrado pelo debate r1
  — rounds 12+25 do trem v1.3.0):** a cerimônia gerada emite a
  evidência de revisão dos PRÓPRIOS scripts em diretório pinado
  independentemente, FORA do delta manifest da release — sem isso o
  delta guard entra em laço infinito de re-assinatura (somar quebra
  set-equality; não somar reprova no G0; regenerar cria versão
  não-revisada).
- **Rollback e modo do piloto (r2 P2 — desambiguado):** trem 1
  (v1.4.0) = piloto SHADOW: a cerimônia gerada roda em dry-run em
  clone, EM PARALELO à cerimônia manual que executa o corte real;
  trem 2 = produção com a gerada, com último ponto seguro de fallback
  ANTES de tag/publish (a fronteira irreversível nunca roda pela via
  nova sem a manual disponível). A manual permanece CANÔNICA até os
  dois trens verdes (1 shadow + 1 produção); falha em qualquer ponto
  ⇒ fallback manual sem cerimônia extra.

## 3. Guard-rails

- O gerador é superfície canônica: cerimônia + pair-rail no gerador,
  UMA vez — é exatamente a troca que paga (revisão amortizada).
- Nenhuma mudança no CONTEÚDO das garantias da cerimônia (sentinel,
  anchor-sha, dois rails de signer, scope=∅ antes de commit).
- Se o piloto W4 não reduzir rounds ≥40% vs baseline, reportar
  NEGATIVO e manter template+lint (W1/W2 valem sozinhos).

## 4. Pronto-para-execução (S302e)

**ACs por wave (W1/W2 reescritos pelo debate r1):** W1 = catálogo-DELTA
em duas seções, ≥10 classes (6 conhecidas + as novas do r1), cada
lintável com exemplo REAL citado (round/arquivo) e caso-vermelho
executável, cada invariante da seção B com o round que a originou;
post-mortem 0/27 registrado; tabela classe→frequência→rounds derivada
por comando; baseline do W4 congelada por comando citado; fronteira dos
scripts de assinatura declarada. W2 = shellcheck estendido + descoberta
por conteúdo com controle positivo (a classe 3 achada nos 4 arquivos
fora do glob antigo = prova de que o escopo enxerga o alvo) + lint
próprio com positive control (remover o lint ⇒ vermelho no censo do
171-W0); FP: zero-FP exigido SÓ das classes BLOCKING; ADVISORY publica
taxa de disparo medida; resíduo histórico = cura OU waiver pinado por
sha256 do CONTEÚDO (datado, com motivo, contado pelo CI; waiver por
caminho PROIBIDO; baseline só encolhe — teste falha se crescer). W3 =
gerador re-emite os cortes rc.3 e GA v1.3.0 a partir de input
declarativo reconstruído; AC: equivalência de GARANTIAS (§2b, lista
derivada do contrato) contra os scripts reais que executaram — é o
golden test. W4 = piloto shadow no trem v1.4.0 (§2b); métrica primária
em ROUNDS vs ROUNDS [debate r1: o denominador "38/31" NÃO reproduz do
disco (44 vereditos / 34 transcripts, 27 no corpus de scripts) — a
baseline usada pelo W4 é a congelada por comando na W1]; alvo do §3 =
redução ≥40% na classe de scripts; horas de reviewer como métrica
SECUNDÁRIA.

**Runbook sessão 1:** extrair o catálogo W1 dos rounds reais
(read-only sobre PLAN-166/repass-rc3-scripts/) + esqueleto do lint.

### Registro de execução — W1 fechada; W2 executada com wire STAGED (S316, 2026-08-20)

Debate L3 round-1 executado (3 críticos, 3× ADJUST, consenso PROCEED;
revisão cross-model codex r1 REJECT → r2 → r3 com todas as curas
aplicadas — inclusive "consenso inventado" no F5, corrigido para
decisão do CEO com divergência registrada).

**W1 — FECHADA.** Catálogo-DELTA em `PLAN-174/catalog.md`: post-mortem
0/25 (sonda por comando; causa = gerador serve canonical-edit, não
corte), mapa contrato→enforcement, DUAS seções (10 classes lintáveis /
6 invariantes de máquina de estado com rounds citados), tabela de
frequência derivada (38 `||true`/83 cmdsubst/61 shasum em 3.755 LoC),
baseline W4 congelada por comando (**34/44** — substitui o irreprodutível
"31/38"), fronteira dos 9 signing scripts declarada (decisão do Owner
pendente, com consequência de recálculo), draft do ADR de disciplina de
erro (formaliza no closeout — cache discipline do CLAUDE.md).

**W2 — executada; wire de CI STAGED por bloqueio LEGÍTIMO.**
- `check-ceremony-script.py` landado: descoberta por CONTEÚDO
  (os.walk), 54 descobertos/41 rastreados, piso=41, R1-R8 com split
  BLOCKING/ADVISORY, waivers sha256-pinados
  (`ceremony-lint-waivers.json`, 41 entradas datadas com motivo;
  generate-ceremony.sh com waiver que EXPIRA na W3), unlock ADR-186
  (sha + motivo obrigatório), autolimitação literal na saída.
- Controle positivo do escopo PASSOU: R3 achada exatamente nos 4
  `run-*.sh` fora do glob antigo. Testes: 15/15 verdes
  (`tests/test_check_ceremony_script.py`) — caso-vermelho por classe
  BLOCKING, re-arme de waiver por edição, unlock-sem-motivo mantém
  bloqueio, piso, untracked-não-gateia.
- **~~Wire BLOQUEADO pelo guard ADR-182~~ — O BLOQUEIO NÃO EXISTE MAIS
  (verificado S321).** A redação abaixo descrevia um pin em 0.144.x
  divergindo do instalado 0.147.0. **A cerimônia de re-pin já
  aconteceu**, no `32e29b1` (SENT-S318, "re-pin codex 0.147.0
  ADR-182 §5") — o texto deste plano e a memória do projeto é que não
  foram atualizados, e o bloqueio sobreviveu como claim envelhecida por
  duas sessões.

  Verificado COMPORTAMENTALMENTE, não por leitura do commit:

  | | |
  |---|---|
  | `codex-cli-pin-manifest.json` pina | **0.147.0** |
  | `codex --version` | **0.147.0** |
  | sha256 do payload real | `19c4f144c5226a9f…` |
  | sha256 pinado no manifesto | `19c4f144c5226a9f…` |
  | veredito | **payload casa o pin, byte a byte** |

  **A W2 está DESTRAVADA.** O que falta é só o land do wire:
  `ceremony-lint.yml` + installer de pre-commit, ambos rastreados em
  `PLAN-174/staged-w2/`. **W2 só FECHA com o wire landado e o job verde
  no CI** — o AC não fecha vacuamente, e essa parte continua valendo.

**Debate:** Codex r1→r3 (GO no r2); `/debate start PLAN-174` no
início da execução; o GERADOR em si passa por cerimônia
canonical-edit + pair-rail quando for landar (§3).
