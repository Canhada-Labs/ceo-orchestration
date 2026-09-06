---
round: 1
archetype: Principal QA Architect
skill: testing-strategy
agent_persona: (nenhuma — arquétipo sem bloco próprio em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-06T07:40:00Z
---

## Verdict

ADJUST — 5 itens BLOCKING (R-QA1, R-QA2, R-QA3, R-QA4, R-QA7).

Nota de escopo: o arquivo citado na convocação (`<ROOT>/.claude/plans/PLAN-175.md`)
**não existe** em HEAD; o plano vive em
`<ROOT>/.claude/plans/PLAN-175-skills-pruning-discovery.md` (172 linhas). Todas as
citações abaixo são desse arquivo.

## Summary (≤ 3 bullets)

- O plano acerta na ORDEM (descoberta antes de poda) e na honestidade do §3.1: reconhecer que o P1 se apoiava num mecanismo morto e idioma-dependente é raro e correto.
- **Onde é forte:** a regra de Fase 2 pela META (não por queda relativa, linhas 33-35), o "ARQUIVAR, não deletar" (linha 42), e o pré-registro da inexecutabilidade do N≥30 como `external_wait` (linhas 147-161).
- **Onde é fraco:** a instrumentação. Cada número que o plano quer medir (janela 90d, N≥100, unknown-ratio, "0 invocações") é pedido a instrumentos que, medidos em HEAD, respondem outra pergunta, respondem VERDE por vácuo, ou não têm consumidor. É a classe `feedback-instrument-green-with-stale-question`, aplicada ao plano que existe para medir.

## Risks

**R-QA1 — P1 — A janela de 90 dias NÃO EXISTE: o log rotaciona a ~10 MB e a retenção real é ~16 dias.**
Medido em `<PK>` (dir de estado do projeto): o log vivo `audit-log.jsonl` tem 11.351 linhas e vai de `2026-09-06T01:58:33Z` a `2026-09-06T07:26:26Z` — **5,5 horas**. O `rotation-manifest.json` confirma `rotated_at: 2026-09-06T01:58:33Z`. Os 8 arquivos rotacionados começam no mais antigo em `2026-08-21T12:13:43Z` ⇒ histórico TOTAL ≈ 16 dias, contra os 90 exigidos em duas frentes: telemetria do P1 (linha 36) e a regra determinística do P2 (linha 39, "0 invocações em ≥90d"). Pior: o leitor default nunca vê os rotacionados — `_iter_audit_events_since` abre só `AUDIT_LOG_DEFAULT` (`.claude/scripts/ceo-boot.py:448-453`, constante em `:81`). Executada no caminho default, a regra determinística classifica **as 42 core como mortas** e o P2 arquiva o catálogo inteiro. `/skill-health` tem a flag certa (`include-rotated`, `.claude/commands/skill-health.md:3` e `:34-35`) e o próprio doc manda usá-la "before treating any dead-skill" — o plano não nomeia flag, nem fonte, nem retenção.
*Mitigação:* o P2 declara a INVOCAÇÃO exata (`/skill-health since=90d include-rotated json`), e um AC preliminar mede a retenção disponível; se < 90d, o gate é de calendário (como o N≥30 já é), não de sessão.

**R-QA2 — P1 — O critério de saída do P1 é satisfazível com denominador ZERO (label alcançável por construção, sem sinal).**
`check_skill_unknown_ratio` retorna **"green"** quando `total == 0` (`ceo-boot.py:695-706`) e sua janela é de **24 h**, não 90 d (`_iter_audit_events_since(hours=24.0)`, `:448`). A frase "<0,10 ⇒ registrado como atingido" (linhas 34-37 e 76-78) fecha, portanto, num repo ocioso. Censo em HEAD do log vivo: **zero eventos `agent_spawn` em 11.351 linhas** (top de ações: `tool_call_lifecycle_recorded` 8766, `output_scan_finding_suppressed` 1359, `output_scan_finding` 807). O `N mínimo = 100 spawns` (linha 36) é PROSA: nenhum instrumento o exige, e o §3.1 usa a saída de 24 h (`no custom-archetype spawns`, linhas 150-152) como se fosse a evidência da janela de 90 d — duas perguntas diferentes, uma conclusão só.
*Mitigação:* o N mínimo vira código (denominador < N ⇒ status `insufficient-sample`, NUNCA `green`), e o AC do P1 cita a saída COM os inputs (janela, denominador, fonte rotacionada).

**R-QA3 — P1 — Fronteira 0,10 com dois donos que discordam exatamente no ponto de decisão.**
Plano: fail-high se ratio **≥ 0,10** (linha 34). Código: `status = "red" if ratio > 0.10 else "yellow" if ratio > 0 else "green"` (`ceo-boot.py:708`). Em ratio == 0,10 o plano ativa a Fase 2 e o instrumento diz "yellow". Célula de fronteira sem dono — a classe que este repo já pagou (contagem/limiar em duas grafias).
*Mitigação:* uma fonte só; se o instrumento é o oráculo do AC, o plano cita `> 0.10` ou o patch move o operador — no MESMO pacote.

**R-QA4 — P1 — O "mecanismo de sugestão" do P1 não tem consumidor em HEAD; o positive control não pode ser escrito.**
`route_query()` está declarado "LOAD-BEARING but **TELEMETRY-ONLY**" e "Do not delete; **do not auto-wire**", com o wire-up explicitamente FORA de escopo e rastreado em outro plano (`PLAN-097-FOLLOWUP-rag-router-wireup`) — `.claude/hooks/_lib/rag_router.py:22-33`. Censo: nenhum hook em `.claude/hooks/*.py` importa `rag_router`/`rag_bridge` (só `_lib/`, testes, `.claude/scripts/skill-retrieve.py` e `.claude/scripts/optimizer/rag_recommender.py`). O AC do P1 exige "spawn sem skill ⇒ sugestão aparece no transcript" (linhas 73-74): não existe canal que escreva no transcript, logo o AC é insatisfazível pela MESMA razão do §3.1 — só que desta vez a peça faltante é o consumidor, não o índice.
*Mitigação:* declarar se o wire-up é pré-requisito (dependência em outro plano) ou escopo do P1; sem isso o P1 não abre como pacote livre.

**R-QA5 — P2 — A sonda do §3.1 não é um controle: descarta o `mode`, converte falha em miss, e um dos três números da tabela é DIGITADO.**
Em `.claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py`: linha 25 atribui `me`/`mp` (o `mode` retornado) e **nunca os usa** — uma rodada em `static-fallback` é contada como "tf-idf" (o controle fica verde com o mecanismo removido); `run()` (linhas 13-21) transforma QUALQUER falha (rc≠0, índice ausente, cwd errado — o path é RELATIVO, linha 14) em `PARSE-FAIL` + lista vazia, indistinguível de miss real; e a linha 30 imprime `(static-fallback medido antes: 4/8)` como **string literal** — a linha do meio da tabela §3.1 (linhas 118-122) é um número tipado, não computado pelo instrumento que a tabela cita como reprodutível (linha 99).
*Mitigação:* asserção dura de `mode` esperado por braço, `check=True` no subprocess (falha ≠ miss), path resolvido a partir do `__file__`, e as 3 linhas da tabela geradas na MESMA execução.

**R-QA6 — P2 — O índice é artefato per-máquina, fora do repo, e ninguém o invalida depois da poda.**
`<PK>/skill-index.sqlite` existe hoje com mtime **2026-08-22** (o dia da sonda S322) — ou seja, o §3.1 continua correto sobre a ausência de bootstrap: o único hit de `skill-index-build` fora de `scripts/` e testes é uma MENÇÃO em docstring (`.claude/hooks/_lib/frontmatter.py:22`). Consequência não coberta por AC: depois do P2 (arquivar core) e do P3 (mover 116 domain), o índice segue indexando slugs que não existem mais, e a sugestão do P1 aponta para skills arquivadas.
*Mitigação:* AC de invalidação (rebuild obrigatório + asserção de que nenhum slug sugerido está em `archive/`), no MESMO pacote da poda.

**R-QA7 — P1 — O AC do P5 não pode ficar VERMELHO na propriedade que enuncia; e o `archive/` do P2 é invisível às duas contagens derivadas.**
(a) `check-claude-md-claims.py` já **roda verde hoje** (`rc=0`, medido) e já deriva de disco com `tolerance=0` (`:87-95`, `:146`, `:157`, `:165`, `:172`). Ele detecta DRIFT entre claim e disco — não detecta "contagem digitada em vez de derivada". Trocar "166" por "N core + M frontend + packs opt-in" não muda o veredito dele em nenhuma direção: o Check não distingue o mundo violado do mundo curado.
(b) Duas superfícies com o número ficam FORA de qualquer gate: `docs/GUIA-COMPLETO.pt-BR.md:73` ("166 skills") e `scripts/install.sh:3732` ("12 fintech skills") — a lista `DOCS` do `verify-counts.sh:562-567` cobre `docs/GUIA-COMPLETO.md` mas **não** o espelho pt-BR, e não cobre `scripts/`.
(c) O rollback do P2 ("`archive/` restaurável", linha 40) colide com as duas derivações: `_count_skills()` usa `_REPO.glob(".claude/skills/**/SKILL.md")` (`check-claude-md-claims.py:89`) e `verify-counts.sh:192` usa `find "$REPO_ROOT/.claude/skills" -name SKILL.md` — ambas RECURSIVAS. Um `.claude/skills/archive/` deixa as 166 contando; um archive fora de `.claude/skills/` muda 4 contagens `exact` de uma vez (`verify-counts.sh:31-34`). Não existe convenção de archive para skills em HEAD (`ls .claude/skills` = `core domains frontend`; zero hits de `skills/archive` em `scripts/`, `.claude/scripts/`, `.github/workflows/`).
*Mitigação:* AC do P5 passa a ser um oráculo que falha se QUALQUER superfície do censo carregar um literal; o censo é derivado por comando, não listado de memória; e o P2 define o path do archive ANTES de arquivar, com a asserção de contagem nas duas derivações.

**R-QA8 — P2 — P3 tem uma dependência que ainda não existe e um AC-mestre sem oráculo nomeado.**
`install.sh:1310-1319` instala `.claude/skills/domains/<domain>/` a partir de `$SOURCE_DIR` — mover os 116 muda o caminho de instalação, não só o repo. O AC-mestre "install/upgrade de adopter SEM packs funciona (smoke)" (linhas 83-84) não nomeia qual smoke (o `smoke-install.sh` hoje é o instrumento que ATIVA e executa o CI entregue). E a dependência declarada, PLAN-171 W1c, é **contract-only e não entregue**: `PLAN-171` está `executing` desde 2026-09-05 (`.claude/plans/PLAN-171-governance-imports-provenance.md:4`), W1c descrito em `:165` e `:189-191`, e o único doc de fronteira em `docs/` é `ownership-decision-table.md` (packs não aparecem lá).
*Mitigação:* P3 fica bloqueado por artefato NOMEADO (path do contrato W1c), não por "W1c"; e o AC-mestre cita o comando do smoke.

**R-QA9 — P3 — Dois `external_wait` para o mesmo plano, em duas fontes.**
Frontmatter: `external_wait: "gatilho: pós-GA v1.3.0; W1c do PLAN-171 primeiro"` (linha 13). Bloco S325: "trate como `external_wait`" pela janela de exposição do N≥30 (linhas 158-161), sem tocar o frontmatter. Um leitor mecânico do frontmatter conclui que o gatilho já passou.
*Mitigação:* o frontmatter absorve o segundo gatilho no mesmo commit em que o bloco S325 é ratificado.

## Faltando antes da execução (OQ para o Owner ratificar)

- **OQ-1** Fonte e janela reais da telemetria: invocação exata com `include-rotated`, e o que fazer com retenção < 90d (medida: ~16 dias).
- **OQ-2** N mínimo mecanizado; `total == 0` deixa de ser `green` (vira `insufficient-sample`).
- **OQ-3** Fronteira `≥ 0,10` vs `> 0.10`: dono único.
- **OQ-4** O wire-up do sugeridor (`PLAN-097-FOLLOWUP-rag-router-wireup`) é pré-requisito ou escopo do P1?
- **OQ-5** Decisão (b) do gap de idioma (linhas 136-140) ANTES de ligar qualquer sugestão em sessão PT — hoje ligar é regressão medida.
- **OQ-6** Rebuild/invalidez do índice pós-poda.
- **OQ-7** Path do `archive/` de skills + efeito nas duas derivações de contagem; censo COMPLETO das superfícies com literal (inclui `docs/GUIA-COMPLETO.pt-BR.md:73` e `scripts/install.sh:3732`).
- **OQ-8** Artefato do W1c (path + data) como bloqueador nomeado do P3.
- **OQ-9** Frontmatter `external_wait` reconciliado com o bloco S325.
