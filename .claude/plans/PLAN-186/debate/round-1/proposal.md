---
plan: PLAN-186
round: 1
created_at: 2026-09-02T15:00:00Z
source_plan: .claude/plans/PLAN-186-orchestrator-operating-model.md
---

# PLAN-186 — proposta para o round 1

Plano completo: `.claude/plans/PLAN-186-orchestrator-operating-model.md`.
Estudo-base: `docs/research/orchestrator-operating-model-S339.md` (síntese) e
`docs/research/s339-orchestrator-study/01..05-*.md`. Evidência das waves executadas
como ESTUDO (autorização do Owner, S339): `.claude/plans/PLAN-186/w0/` e `w1/`.

## Tese

O orquestrador não tem política de roteamento: tem herança. `CLAUDE_CODE_SUBAGENT_MODEL=inherit`
mais 10 sítios de `agent()` sem `model:` fazem cada fan-out rodar no modelo do assento.
O custo é dominado por cache-read (96,8 % dos tokens), então trocar o assento de Fable 5.1
por Opus 5 rende pouco em dólar (5,5 %) e nada mensurável em quota, que não tem número
oficial por modelo. A alavanca real é (a) `model:` explícito com builders mecânicos em
Sonnet 5 (−US$ 1.369/mês), (b) os 5 pins VETO em `claude-fable-5` (cache-read 4× o do 5.1,
e o code-reviewer roda no rail nativo onde o pin vale), (c) CI em matriz (Validate −43 %,
Smoke −55 %), (d) Step 0 do Spawn Protocol decidindo paralelismo por dependência
sequencial e não só por sobreposição de arquivos.

## Decisões propostas (matriz papel × modelo × effort)

| papel | modelo | effort | camada |
|---|---|---|---|
| assento CEO / sessão que lança night-run | decidir por A/B de 7 dias (Fable 5.1 vs Opus 5) | high | T |
| VETO (5) | claude-fable-5-1 (hoje claude-fable-5) | max | T |
| refutador não-VETO | claude-opus-5 | xhigh | P |
| síntese / REDUCE | claude-fable-5-1 | max | P |
| builder canônico / KERNEL | claude-opus-5 | max | P |
| builder livre / docs | claude-sonnet-5 | high | P |
| pesquisa / leitura | claude-sonnet-5 | high | P |

Regra de effort: escala por incerteza de especificação, não por blast radius.

## Waves (resumo)

W0 instrumento + sondas (livre) · W1 `model:` explícito (livre; derivador pronto) ·
W2 A/B do assento (7 dias) · W3 camada T: pins VETO e pin do assento (GPG) ·
W4 CI em matriz (livre) · W5 doutrina: Step 0 dependência sequencial, teto de effort,
rail de coordenação entre terminais (debate + ADR) · W6 adapter opcional.

## Evidência já produzida (W0/W1 como estudo, S339)

- Instrumento `ceo-cost-transcripts.py` (20/20 testes): 30 d = US$ 10.514 (assento 72 %).
  Refuta em −5,6 % o US$ 11.138 do relatório 05 (dedup falho em turnos Fable 5.1 do
  assento; os outros modelos batem exatos). `w0/instrument-S339.md`.
- Sonda de concorrência (Workflow, 40 agentes Sonnet 5): 0 erros de rate limit até 14
  concorrentes; acima disso o Workflow enfileira (cap local min(16, CPUs−2)); duração da
  mesma tarefa sobe de 5 s (N=4) para 11 s (N=16); ~95 k tokens de contexto por spawn.
  n=1 por N. `w0/concurrency-probe-S339.md`.
- Substrato: `check-substrate-watch.py --probe-installed` mostra drift em 4 componentes
  (Claude Code 2.1.198 → 2.1.258; Codex 0.144.1 → 0.147.0). `w0/substrate-probe-S339.md`.
- Derivador W1 (`w1/apply-w1-explicit-model.py`): 10 sítios reais (não 17 — 7 ocorrências
  eram comentários); 4 Sonnet 5, 2 Opus 5, 4 Fable 5.1; provado em sombra (check/apply/
  `node --check`/guarda de dupla aplicação); patch sha256 b57cf0b8… base 8efe09b.
  [DÚVIDA] `council-audit.js` `lane:${vendor}`: um sítio serve claude/codex/grok — para
  codex/grok o agente é wrapper de transporte. [DÚVIDA] `eval-baseline-n20.js`: o
  `opts.model` tiera só o orquestrador; o modelo avaliado roda via subprocess.

## Open questions

- OQ-1 Owner: autoriza o A/B da W2 antes de mudar pin do assento?
- OQ-2 Owner: rota (a) ou (b) do ADR-149 para os pins VETO em 5.1?
- OQ-3 Owner: ratifica builders mecânicos em Sonnet 5 com critério de morte (2 P1 seguidos ⇒ reverter)?
- OQ-4 medição: teto de concorrência — a sonda respondeu «sem teto de API até 14; fila local acima».
- OQ-5 debate: rail de coordenação entre terminais é hook novo ou doutrina + auditoria?

## Perguntas aos críticos

1. A matriz confunde CUSTO com QUALIDADE em algum papel? Onde Sonnet 5 num builder livre
   pode produzir defeito que o refutador em Opus 5 não pega?
2. O A/B da W2 mede a coisa certa (minutos úteis por janela de 5 h) e o critério de morte
   é falsificável?
3. Migrar os pins VETO para 5.1 muda o piso de capacidade (ADR-052) ou só o custo?
4. Matrizar Validate/Smoke: onde o estado partilhado (GITHUB_ENV, artifacts, deepen do
   histórico) quebra em silêncio?
5. Step 0 por dependência sequencial: como se mede «dependência» antes do fan-out sem
   virar cerimônia?
6. Coordenação entre terminais: risco de permission laundering entre sessões; o que
   um rail mínimo precisa auditar?
7. O que o plano NÃO deveria mudar?
