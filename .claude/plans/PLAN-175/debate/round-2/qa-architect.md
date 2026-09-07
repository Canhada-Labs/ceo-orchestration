---
round: 2
archetype: Principal QA Architect
skill: testing-strategy
agent_persona: (crítico de verificabilidade — controles, desenho de experimento, estatística do plano)
generated_at: 2026-09-07T00:00:00Z
---

## Verdict

ADJUST — **5 itens bloqueantes** (P1). Todos verificados em disco em HEAD.

## Summary (≤ 3 bullets)

- **O que melhorou de verdade:** os 25 ACs têm `Check:` executável; `RECUSA` virou saída de primeira classe (§2.2); o censo do literal é GERADO (AC-4.1 **reproduz**: 10 arquivos, medido); a AC-1.2 está **verde hoje** (o `grep` das formas proibidas devolve nada, e `ceo-boot.py:708` casa `ratio > 0.10`); `--since all` **existe** no leitor (`skill-health.py:737`). C3, C6-censo, K3 e K8 estão curados.
- **O que quebrou ao curar:** as duas pernas novas do §2.1 **tornam o veredito `ARQUIVAR` inalcançável por construção** e **re-impõem o bloqueio de calendário que o §0 declara refutado**. O round 1 pediu guarda; a guarda escrita não deixa a regra responder nada neste repositório.
- **Classe recorrente:** três `Check:` medem a APARÊNCIA (cor do gate, saída impressa) e não o MECANISMO — exatamente o defeito C6 que o round 1 mandou fechar.

## Risks

### R-QA1 [P1 — BLOQUEANTE] A perna 0 zera o conjunto de candidatas: `ARQUIVAR` é um rótulo inalcançável por construção

Medido (censo por limite de palavra sobre `CLAUDE.md`, `.claude/team.md`, `.claude/frontend-team.md`, `.claude/commands/*.md`, `.claude/agents/*.md`, exatamente as fontes do §2.1:108-110):

```
core= 42   candidates_after_perna0= 0   []
absent_from_SKILL_MAP= 3  ['agent-architect','ceo-orchestration','terse-mode']
agent-architect  -> .claude/commands   ceo-orchestration -> CLAUDE.md + .claude/commands   terse-mode -> .claude/commands
```

As 3 skills que a regra antiga arquivava são justamente as cobertas por `.claude/commands/`. **A regra nova arquiva ZERO de 42.** Consequências: o §1 passo 2 (`:72-76`) promete uma poda que sua própria regra não pode produzir; a AC-2.1 (`:388-389`, «a lista é DERIVADA») fica **satisfeita por uma lista vazia**; a W2 — o único pacote CANÔNICO do plano, que pede assinatura do Owner (`:439-443`) — abre com entrada vazia. O plano precisa dizer o que a regra deve responder quando o conjunto candidato é vazio (RECUSA? `catálogo saudável`?) e como a poda `42 → ~25` do §2.3 se sustenta se a perna 0 exclui todo o core.

### R-QA2 [P1 — BLOQUEANTE] `min_window_coverage_days = 90` re-impõe o bloqueio de calendário que o §0 declara caído — e mata os dois controles do W0

§2.1:120 fixa `min_window_coverage_days = 90`; §4:182 mede a família em **16,6 dias**. Logo, hoje e até ~2026-11-19, **toda** skill sai `RECUSA` (§2.2:134). Isso contradiz o §0:44-47 («o bloqueio por CALENDÁRIO caiu … o denominador que o plano pedia já existe») e o `external_wait: none` (`:16`): o denominador de SPAWNS existe (109 ≥ 100), o de COBERTURA não. Efeitos mecânicos:

- **AC-0.2** (`:351-352`) exige veredito `MANTER` para `ceo-orchestration` e o piso de VETO. Sob a perna 1 o veredito é `RECUSA` ⇒ **o AC não pode ficar verde na propriedade que enuncia** (ou fica verde por leitura frouxa «não foi arquivada», que é vacuidade).
- **AC-0.3** (`:353-354`), o controle positivo, exige saída ≠ 0 com a perna 0 **desligada**. Com `RECUSA` dominando, desligar a elegibilidade não muda nada ⇒ **o controle permanece verde com a proteção removida** — o red flag canônico: ele não reproduz o MECANISMO (a perna 0), reproduz a aparência (a skill não foi arquivada).
- **AC-0.4** (`:355-356`) pede `RECUSA` sob telemetria vazia — mas a corrida NORMAL já devolve `RECUSA` para tudo, então o `--force-empty-telemetry` **não discrimina**.

Cura: a cobertura vira função do que existe (histórico atribuível completo + `min_observed_spawns`), ou a perna 1 declara `90d` como alvo FUTURO e o W0 roda com a cobertura real declarada — e os controles AC-0.2/0.3 passam a ser medidos com a perna 1 explicitamente neutralizada, para que a variável sob teste seja a perna 0.

### R-QA3 [P1 — BLOQUEANTE] W0 e W1 são declarados «pacote LIVRE», mas tocam caminho CANÔNICO

Oráculo em HEAD (`python3 .claude/hooks/check_canonical_edit.py --is-canonical`):

```
.claude/hooks/_lib/rag_router.py   1      <- CANÔNICO
.claude/scripts/skill-health.py    0
```

A AC-0.6 (`:359-360`) manda tirar a referência ao follow-up **do código do roteador** — o literal está em `.claude/hooks/_lib/rag_router.py:32`, canônico. A AC-1.6 (`:378-379`) exige um INJETOR que ponha a sugestão no transcript de um spawn; qualquer injetor vive sob `.claude/hooks/`. Logo o §5 (cabeçalhos W0/W1) e o §6:445-446 («Só W0, W1 e W4 são pacotes integralmente livres») são **falsos em HEAD**. Sob a regra da noite, um pacote canônico termina em bloco SIGN, não em land livre — o runbook do §6:447 («primeira sessão: W0 inteira») está dimensionado errado.

### R-QA4 [P1 — BLOQUEANTE] O `Check:` da AC-3.3 não exercita a perna que o C5 mandou testar — e escreve lixo na árvore

`scripts/tests/smoke-install.sh:17` é `TARGET="${1:-}"` e a linha `:34` chama o instalador com **`--profile core,frontend` HARDCODED**. O script não tem parser de flags. A AC-3.3 (`:407-408`) manda rodar `bash scripts/tests/smoke-install.sh --profile core,<domínio>`: isso define `TARGET="--profile"`, faz `mkdir -p "--profile"` e `git init` DENTRO do repositório (`:25-31`), e instala o perfil fixo. Ou seja: **a perna «que de fato regride» não é exercida**, o AC não pode ficar vermelho pela propriedade que enuncia, e o comando tem efeito colateral de escrita. Cura: o `Check:` invoca `scripts/install.sh <tmpdir> --profile core,<domínio>` diretamente, ou o AC nomeia a flag nova que o smoke precisa ganhar.

### R-QA5 [P1 — BLOQUEANTE] O `Check:` da AC-1.4 nunca pode ficar verde

`grep -n "decisao-b" .claude/plans/PLAN-175/decisions/` (`:375`): (a) o diretório **não existe** (`ls` ⇒ *No such file or directory*); (b) mesmo depois de criado, `grep -n` **sem `-r`** sobre um diretório não casa nada — medido em HEAD sobre `.claude/plans/PLAN-175/`: saída vazia, `rc=1`. O AC que ratifica a decisão de idioma — o gate que segura a Fase 1 — tem um verificador que responde «não» para sempre. Cura de uma linha: `grep -rn`, mais o caminho do registro declarado.

### R-QA6 [P2] A AC-4.2 volta a medir a COR do gate, que é o defeito C6

O §4.7:335 diz «o critério novo asserta a CONTAGEM de sítios casados». O `Check:` da AC-4.2 (`:420`) é `bash .claude/scripts/local/verify-counts.sh` mais uma comparação em PROSA («com a contagem de casamentos por documento comparada ao censo»). O instrumento existe e é exportável: `verify-counts.sh:789` e `:795` mantêm `rule_matches_by_doc`, e o comentário `:786` diz para que ele serve. Enquanto o `Check:` não invocar o `--json` e comparar contra a AC-4.1, uma claim REESCRITA que deixa de casar continua invisível — o cenário exato do `:324-325`.

### R-QA7 [P2] A sonda ainda não tem parser: os `Check:` das AC-0.5/AC-1.3 passam flags que hoje são ignoradas

`grep -n "argv|argparse|require-mode|--pairs" .claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py` devolve **nada**. Os `Check:` (`:358`, `:373`) usam `--require-mode tfidf`, `--pairs 30`, `--json`. Numa sonda que ignora `argv`, o código de saída é decidido por causa alheia à propriedade testada — verde possível sobre a sonda NÃO corrigida. Os ACs precisam exigir explicitamente: flag desconhecida ⇒ saída ≠ 0, e `--require-mode tfidf` **recusa** quando o recuperador devolve fallback.

### R-QA8 [P2] Quatro `Check:` imprimem e não asseram — não têm metade VERMELHA

AC-1.1 (`:369`), AC-2.2/AC-2.3 (`:391`, `:393`), AC-4.1 (`:418`) e AC-4.4 (`:424`) rodam comandos que **sempre saem 0** se a ferramenta funciona. Em particular: o controle «166 → 165» da AC-2.2 é enunciado no texto mas o `Check:` é a cor do `verify-counts`, que fica verde tanto com quanto sem arquivamento (basta o documento e o disco concordarem); e a AC-2.3 usa **o mesmo comando** da AC-2.2, então não distingue «restaurou» de «nunca arquivou». Cura: `Check:` que compare DOIS valores derivados (antes/depois) e saia ≠ 0 na igualdade indevida.

### R-QA9 [P3] Plano L3 sem ADR nomeado

`CLAUDE.md` §4 exige ADR formal para escolha arquitetural cross-cutting. O plano decide duas — o destino do arquivo morto fora de `.claude/skills/` (§2.4) e a perna de elegibilidade (§2.1) — e cita apenas ADR-052 e ADR-192, ambos de terceiros. Nenhum `ADR-<NNN>` novo é nomeado em nenhuma onda.

## O que falta antes da execução (OQ para o Owner ratificar)

- **OQ-1.** Com a perna 0 zerando as candidatas (R-QA1), a W2 ainda existe? Se sim, sob que critério — consolidação (§2.3) em vez de telemetria?
- **OQ-2.** `min_window_coverage_days`: 90 (e o plano volta a esperar calendário até ~2026-11-19) ou cobertura declarada do histórico atribuível (e o `external_wait: none` sobrevive)? As duas leituras estão hoje no MESMO texto (R-QA2).
- **OQ-3.** W0/W1 são pacotes canônicos (R-QA3): o Owner aceita duas assinaturas a mais, ou a AC-0.6/AC-1.6 saem da primeira sessão?
- **OQ-4.** A decisão (b) de idioma (AC-1.4): conjunto fechado, dono e critério de morte — e o caminho do registro, para o `Check:` poder existir.
- **OQ-5.** O `external_wait: none` foi ratificado (nota do `:528` e o registro de 2026-09-06); a ratificação vale também para a leitura de OQ-2, ou é preciso re-perguntar?

**BLOCKING: 5** (R-QA1, R-QA2, R-QA3, R-QA4, R-QA5). Nenhum deles exige decisão do Owner para ser ESCRITO — exceto OQ-1/OQ-2, que mudam o escopo. Este round certifica coerência de DESENHO e não autoriza execução.
