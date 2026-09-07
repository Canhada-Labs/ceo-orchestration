# PLAN-171 W0 — veredito consolidado dos seis lotes (S348)

> Este documento não mede nada de novo. Cada número abaixo foi LIDO nos
> seis relatórios já landados em `.claude/plans/PLAN-171/w0/` (lote-1
> a lote-6) e cada um carrega a citação `arquivo:linha` de onde veio.
> Onde este documento soma números (ex.: total de gates nos seis
> lotes), a soma é aritmética simples sobre valores já publicados —
> não uma nova contagem sobre o repositório.

## Glossário (1 linha por termo, para quem não acompanhou os seis lotes)

- **hook** — um script que a ferramenta de IA executa automaticamente
  antes ou depois de uma ação (editar um arquivo, rodar um comando),
  registrado em `.claude/settings.json`.
- **gate** — o mecanismo de controle que um hook implementa; pode
  BLOQUEAR a ação (recusar) ou só OBSERVAR (registrar e deixar passar).
- **controle positivo** — um teste automatizado que PROVA que o gate
  funciona: ele monta a condição que deveria disparar o bloqueio e
  verifica que o gate realmente bloqueia.
- **três metades** — o método de medição deste censo: rodar o mesmo
  controle três vezes — (1) como o código está hoje, (2) depois de
  remover o mecanismo de bloqueio (o controle deve FALHAR), (3) depois
  de restaurar o código (o controle deve voltar a PASSAR). Só as três
  juntas provam que o teste enxerga o mecanismo — não é decorativo. A
  terceira metade (restauração) só entrou no método a partir do lote 2
  (achado de defeito de instrumento, ver §2).
- **vácuo** (`controle vácuo`) — um teste que TEM a forma de um
  controle positivo mas nunca poderia falhar (por exemplo, foi marcado
  `SKIPPED` e nunca roda de verdade).
- **opt-in** — um mecanismo que só passa a bloquear se alguém ligar
  deliberadamente uma variável de ambiente; por padrão (sem a variável)
  ele permite a ação.

## 1. A partição: quantos hooks existem e como os seis lotes os dividem

Os seis lotes usam a MESMA partição determinística, derivada por
instrumento (não acordada entre sessões): `L` = os arquivos de hook
registrados em `.claude/settings.json`, na ordem de primeira ocorrência.

- `.claude/settings.json` tem **15 eventos**, **50 entradas** de hook,
  das quais **49 nomeiam um arquivo `*.py`** (a diferença — 1 — é uma
  entrada `echo` inline que não nomeia arquivo), resolvendo em
  **`|L| = 48` arquivos `.py` distintos** — `.claude/plans/PLAN-171/w0/lote-4-S347.md:39-42`
  (a mesma aritmética é reconfirmada em `lote-2-S347.md:36`, `lote-3-S347.md:43` e `lote-6-S347.md:35`).
- O lote 1 (`.claude/plans/PLAN-171/w0/lote-1-S345.md`, S345) audita 10
  gates citando **8 arquivos** distintos; **6** desses arquivos estão em
  `L` (`check_canonical_edit.py`, `check_bash_safety.py`,
  `check_agent_spawn.py`, `check_pair_rail.py`,
  `check_anti_ceo_overhead.py`, `accel_dispatch.py`) e **2**
  (`adequacy_gate.py`, `audit_emit.py`) não são hooks registrados
  diretamente — `.claude/plans/PLAN-171/w0/lote-2-S347.md:36-37,41,85-87`
  (mesma contagem em `lote-3-S347.md:44-46` e `lote-4-S347.md:44-46`).
- Removidos os 6 arquivos do lote 1, resta **`|R| = 42`**
  (`48 − 6 = 42`) — `lote-2-S347.md:39,88`. `R` é fatiado, por
  construção da partição (não por acordo entre sessões), em:
  `lote 2 = R[0:10]`, `lote 3 = R[10:20]`, `lote 4 = R[20:30]`,
  `lote 5 = R[30:36]`, `lote 6 = R[36:42]` —
  `lote-5-S347.md:38-40`, `lote-6-S347.md:37`.

| Lote | Fatia de `R` | Hooks nesta fatia | Relatório |
|---|---|---|---|
| 1 | (fora da partição `R` — runbook original §7 do plano) | 10 gates / 8 arquivos, 6 em `L` | `lote-1-S345.md` |
| 2 | `R[0:10]` | 10 | `lote-2-S347.md` |
| 3 | `R[10:20]` | 10 | `lote-3-S347.md` |
| 4 | `R[20:30]` | 10 | `lote-4-S347.md` |
| 5 | `R[30:36]` | 6 | `lote-5-S347.md` |
| 6 | `R[36:42]` | 6 | `lote-6-S347.md` |

**Cobertura de `L`:** 6 (do lote 1) + 42 (`R` inteiro, lotes 2-6) =
**48 de 48** arquivos de `L` — 100% do roster registrado em
`settings.json` tem pelo menos uma linha de censo em algum dos seis
relatórios.

## 2. Tabela por lote — o que foi medido, com que método, e o veredito

| Lote | Gates medidos | Método (metades) | Verde | Vácuo | Sem controle | Sem-controle-por-design | UNREGISTERED | Classe de bloqueio medida (resumo do próprio lote) |
|---|---|---|---|---|---|---|---|---|
| 1 | 10 | 2 metades (como está / removido) — a 3.ª metade (restauração) ainda não existia como método | 10 | 0 | 0 | 0 | 0 | 8 bloqueiam diretamente; 2 advisory-por-desenho (`adequacy` sinaliza sem bloquear; `audit-emit` é default-deny, descarta kwargs sem bloquear a ferramenta) — `lote-1-S345.md:19-44,53-58` |
| 2 | 10 | 3 metades (introduzidas NESTE lote, após achado de defeito de instrumento — bytecode do macOS falsificando a medição, `lote-2-S347.md:171-192`) | 10 | 0 | 0 | 0 | 0 | 3 linhas advisory (`protocol-semver-cascade`, `budget`, `read-injection`); `read-injection` tem rota de bloqueio **opt-in** sob `CEO_UNICODE_HARDBLOCK=1`, MEDIDA nas três metades no próprio Apêndice F; `adversary` é gated por `CEO_ADVERSARY` e foi medido com o enforcement LIGADO — `lote-2-S347.md:91-136,138-151` |
| 3 | 10 | 3 metades | 9 | 0 | **1** (`check_cost_envelope.py`) | 0 | 0 | 4 bloqueiam diretamente (`worktree-writer`, `config-protection`, `confidence-gate`, `subagent-fabrication`); 5 observadoras com chaves opt-in MEDIDAS no Apêndice G (`ledger-checkpoint`, `audit_log`, `output-safety`, `skill-reference-read`, `output-secrets`); 1 marcada **sem controle** (`cost-envelope` — ver §4) — `lote-3-S347.md:106-134,553-559` |
| 4 | 10 | 3 metades | 10 | 0 | 0 | 0 | 0 | **8 de 10 são observadoras** (só detecção, sem emissão medida); só 2 têm construto de bloqueio medido (`check_mcp_response.py` sob `CEO_MCP_SCANNER_MODE=strict`, opt-in; `SessionStart.py`, consumo de veredito de bloqueio do validador) — `lote-4-S347.md:135-158` |
| 5 | 6 | 3 metades | 6 | 0 | 0 | 0 | 0 | 2 de 6 bloqueiam, **ambas opt-in** (`codex_review_user_code.py` sob `CEO_CODEX_USER_REVIEW_BLOCK=1`; `review_loop.py` sob `CEO_REVIEW_LOOP=1`); as outras 4 têm ZERO construtos de bloqueio nas quatro formas varridas — `lote-5-S347.md:124-133` |
| 6 | 6 | 3 metades | 6 | 0 | 0 | 0 | 0 | **5 de 6 são observadoras** (medidas por `measure-optin.py` com probe dinâmico: 0 de nenhuma rodada bloqueou); 1 (`config-change`) tem construto de bloqueio medido diretamente na metade vermelha do Apêndice B — `lote-6-S347.md:108-133` |

Nota de método: a coluna "Vácuo" está zerada nos seis relatórios, mas o
lote 3 registra um candidato que TERIA sido um vácuo se usado sem
checagem — `test_fail_with_enforce_blocks` do `check_confidence_gate`
está `SKIPPED` (retirado pelo ADR-019-AMEND-1) e o relatório usa, em
seu lugar, o substituto que prova vermelho de verdade
(`test_confidence_gate_class_block.py`) — `lote-3-S347.md:136-160`.

## 3. Totais consolidados e o veredito da W0 em uma frase

Somando as colunas do §2 (aritmética sobre os números já citados,
nenhuma medição nova):

| Métrica | Total |
|---|---|
| Gates/linhas de censo (10+10+10+10+6+6) | **52** |
| Verde | **51** |
| Vácuo | 0 |
| Sem controle | **1** (`check_cost_envelope.py`, caminho de bloqueio) |
| Sem-controle-por-design | 0 |
| UNREGISTERED | 0 |
| Arquivos de `L` cobertos | **48 de 48 (100%)** |

**Veredito da W0 em uma frase:** o censo cobre 100% dos 48 arquivos de
hook registrados em `.claude/settings.json` (52 linhas de gate, porque
o lote 1 audita 10 gates sobre 8 arquivos e 2 arquivos ficam de fora de
`L`), com 51 de 52 linhas providas de controle positivo comprovadamente
vermelho (e, a partir do lote 2, restaurado verde de novo); a exceção é
`check_cost_envelope.py`, cujo caminho de bloqueio existe no código
(`check_cost_envelope.py:281`, citado em `lote-3-S347.md:178`) mas
nenhuma medição do lote 3 demonstra um controle dele — o AC do §7 do
plano (`.claude/plans/PLAN-171-governance-imports-provenance.md:170-172`:
«100% dos hooks com {positive control OU registro
"sem-controle-por-design" justificado}») fica a UMA linha de fechar:
essa linha está classificada **sem controle**, que o próprio lote 3
distingue explicitamente de **sem-controle-por-design** — não há
registro que justifique a ausência, só o fato medido de que ela falta
(`lote-3-S347.md:190-195`). O que a W0 NÃO prova, e nenhum dos seis
relatórios afirma o contrário: que qualquer gate roda em produção
(a medição é sobre o CÓDIGO, não sobre o tráfego real de sessões) e
que a execução condicional de CI (`if: vars.CEO_SOTA_DISABLE != '1'`
nos jobs de hook do `validate.yml`, citado em todos os seis lotes) foi
alguma vez exercitada.

## 4. Dívida declarada da W0 (lida dos relatórios, não nova)

- **`check_cost_envelope.py` — sem controle do caminho de bloqueio.**
  Existem 59 testes em `.claude/hooks/_lib/tests/test_cost_envelope.py`
  — 53 exercitam a biblioteca de aritmética e 6 carregam o hook só para
  testar uma função auxiliar (`_looks_like_swarm_dispatch`); nenhum dos
  59 toca o `{"decision": "block", ...}` do hook. Verdito: **sem
  controle**, não sem-controle-por-design — é follow-up, não conserto
  do lote (que é um censo) — `lote-3-S347.md:176-195`.
- **11 arquivos de hook em disco fora de `L`** (`.claude/hooks/` tem
  hoje **59** arquivos `*.py`; `L` (`settings.json`) só alcança **48**):
  `adequacy_gate.py`, `auto_boot.py`, `check_codex_stop_review.py`,
  `check_harness_config.py`, `check_tier_policy_misrouting_24h.py`,
  `emit_architect_outcome.py`, `latency_report.py`, `policy_dispatch.py`,
  `route.py`, `turbo_profile.py`, `verify_after_edit.py` — 11 nomes,
  medidos por instrumento (`remainder.py`) — `lote-2-S347.md:219-230`
  (reconfirmado em `lote-6-S347.md:215-221`). Duas notas adicionais no
  mesmo censo: `check_harness_config.py` É executado, mas diretamente
  por um step de CI (`.github/workflows/validate.yml:1137`), sem passar
  por evento de hook; `check_codex_stop_review.py` está registrado,
  mas em OUTRO registry (`templates/codex/hooks.json:98`, campo
  `command`) — `lote-2-S347.md:231-232`. E dois validadores bloqueantes
  do trem de release (`validate-pair-rail-verdict.py`,
  `_release_tag_guard.py`) seguem DEFERIDOS pelo próprio lote 1 (§3),
  fora de `L` por não serem hooks registrados — `lote-2-S347.md:233-234`.
- **A condição `if:` dos jobs de CI não foi exercitada.** Os jobs de
  hook do `validate.yml` (`hook-tests-python-matrix`,
  `hook-tests-dual-rail`) carregam `if: vars.CEO_SOTA_DISABLE != '1'`
  — um admin do repo pode desligá-los por variável, e nenhum dos seis
  lotes rodou com essa variável setada para provar o caminho oposto.
  Citado em todos os seis relatórios; ver por exemplo
  `lote-1-S345.md:30-35` e `lote-6-S347.md:149-153`. O runner (a
  máquina que executa o job) também não foi exercitado por este censo.
- **O replay de seletores `-m`/`-k` é necessário, mas não suficiente.**
  O lote 6 mede, por `--collect-only`, se um node id SOBREVIVE ao
  seletor de cada step — mas isso não prova que o `if:` do job passou
  nem que o ambiente do runner se comporta igual; dois steps do
  `mutation-gate.yml` colecionam os alvos e em seguida o próprio
  seletor `-k` os deseleciona por completo — `lote-6-S347.md:170-186`.
- **Follow-ups já nomeados, ainda sem plano próprio no disco** (são
  citados como texto no registro de execução do plano principal e no
  registro de rail do lote 2, não existem como arquivo
  `PLAN-171-FOLLOWUP-*.md` na data desta consolidação — verificado por
  `ls .claude/plans/`):
  - `PLAN-171-FOLLOWUP-lote2-generated-figures` — as figuras de
    contagem dos §§1/4/5 e Apêndices A/B/D do lote 2 seguem literais no
    gerador (não recalculadas por comando) —
    `.claude/plans/PLAN-171-governance-imports-provenance.md:272-274`.
  - `PLAN-171-FOLLOWUP-readinjection-docstring` — o docstring canônico
    de `check_read_injection.py` ainda diz "always allows", o que a
    medição do lote 2 já mostrou ser falso (rota opt-in de bloqueio);
    a correção sai por cerimônia GPG, não por este censo —
    `.claude/plans/PLAN-171-governance-imports-provenance.md:274-275`.
- **Lacuna de corpus declarada pelo lote 4**: nenhum teste do roster
  afirma a EMISSÃO do evento de auditoria para as quatro linhas cujo
  controle prova só a DETECÇÃO (o mecanismo que decide que há algo a
  observar, não o registro do evento em si) — `lote-4-S347.md:157-158,
  Apêndice G`.

## 5. O que isto NÃO fecha

- **As waves W1-W5 do PLAN-171** seguem tal como estavam antes desta
  consolidação: esta W0 é só o censo dos gates (o Runbook sessão 1 do
  §7 do plano). Nenhuma linha aqui altera o escopo, o status ou os ACs
  de W1 (batch-approval), W2 (manifesto de proveniência de leituras),
  W3 (FILE ASSIGNMENT write-time), W4 (living documentation) ou W5
  (higiene de worktree) — esses continuam exatamente como o plano
  principal os descreve em `.claude/plans/PLAN-171-governance-imports-provenance.md:56-101`.
- **A revisão de portfólio S348 recomendou RE-ESCOPAR o PLAN-171, com
  concordância 3/3** dos críticos: "Só a W0 (censo dos gates) entrega:
  4 de 6 lotes landados. W3 duplica um flip já agendado; W5 servia ao
  E5 do 172, congelado" —
  `.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md:40`
  (citação verbatim da tabela do §2 daquele documento, linha do
  PLAN-171). Essa recomendação está **PENDENTE de ratificação do Owner
  em 2026-09-07** — a revisão de portfólio não é, por si, uma decisão
  executória.
- **Nota factual sobre essa citação**: ela foi commitada em `7f6b564`
  às 2026-09-06 22:41:55, e nesse instante "4 de 6 lotes landados" era
  exato; os lotes 5 e 6 landaram DEPOIS, em `ef4c1b3` (22:48:17) e
  `690c3e2` (23:26:39) — ambos posteriores à revisão de portfólio. Ou
  seja: no momento desta consolidação (S348), a W0 tem os **6 de 6**
  lotes landados, não os 4 de 6 que a revisão de portfólio via quando
  foi escrita. Este documento não decide se isso muda a recomendação
  de re-escopo — só registra que a premissa factual da citação mudou
  depois dela ter sido escrita, para quem for ratificar a decisão em
  2026-09-07 ter o dado atualizado.
- **Este documento não roda `/debate` nem é uma cerimônia de
  aprovação.** É uma consolidação de leitura — soma e organiza números
  já publicados. Qualquer decisão de fechar, re-escopar ou continuar o
  PLAN-171 continua exigindo o processo de governança normal do
  repositório (Plan → Debate → Execute para L3+, PROTOCOL.md).
