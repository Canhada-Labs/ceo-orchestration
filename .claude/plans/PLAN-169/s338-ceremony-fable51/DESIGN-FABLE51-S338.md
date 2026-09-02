# DESIGN — wave-fable51 (S338, 2026-09-01) — cerimônia `adopt-fable-5.1`

**Ratificação (Owner, AskUserQuestion na abertura da S338):** «Só no working
set» — rota (c) de três: `claude-fable-5-1` entra no
`AVAILABLE_MODELS_WORKING_SET` do ADR-149; `VETO_FLOOR_ALLOWED`, o
`FALLBACK_MODEL_CHAIN` e o pin `model` dos três espelhos ficam como estão.
Runbook de origem: memória `project-fable-51-adoption-map` (S337): id
`claude-fable-5-1` confirmado na doc oficial (dateless — NUNCA anexar data),
ordem normativa = append-at-end, mudança ADITIVA (`claude-fable-5` segue).

## Decisões de desenho

1. **A fonte manda no resto.** A única edição SEMÂNTICA é o append no bloco
   do ADR; os dois `availableModels` são a saída do gerador
   (`generate-available-models.py --check` = `MATCH (7 ids, ADR order
   preserved)`, 4b/V4). Os três espelhos INDEPENDENTES
   (`validate-governance.sh`, `tier_policy_cli.VALID_MODEL_IDS`,
   `smoke-install-parity.sh`) NÃO derivam — `test_adr149_validator_parity.py`
   os amarra por IGUALDADE DE CONJUNTO (a lição S225: literais espelhados
   driftam em silêncio), então viajam no mesmo patch ou a suíte reprova.
2. **Um derivador para 25 paths.** A wave toca 6 formas de arquivo (JSON
   gerado, case-arm de shell, tuplas Python, YAML, markdown, linha de
   manifesto). Em vez de N fragments jq, o material versionado é
   `apply-fable51-edits.py`: 39 edições `(path, âncora EXATA, substituto,
   contagem)`, planejadas ANTES de qualquer escrita (âncora ausente/ambígua
   ⇒ recusa nomeada, árvore intocada) e com guarda de dupla aplicação (o id
   novo em QUALQUER path tocado ⇒ recusa). A prova de reprodutibilidade é a
   mesma do 183batch, só que sobre todos os paths: worktree temporário em
   HEAD + script == árvore pós-patch, `cmp` byte a byte (4a/V3).
3. **O `upgrade.sh` entra por NECESSIDADE medida, não por zelo.** v1.2.0 e
   v1.3.0 shiparam a lista de 6 ids (`git show v1.3.0:templates/settings/
   settings.base.json`), que era o `new` da política de 3 estados. Com um
   `new` de 7, a lista de 6 não é `old` nem `new` ⇒ ADOPTER-CUSTOMIZED ⇒
   ninguém recebe o 7º id, e a parity e2e do Smoke (Route B: install no pin
   v1.2.0 → upgrade → compara com install fresco) fica VERMELHA. A cura
   segue o precedente do mesmo arquivo (`OLD_PAIR_RAIL_CAPS = (60, 150)`:
   «o conjunto dos defaults SHIPADOS e superados, não um literal»): a chave
   `superseded` lista arrays congelados; o match é byte-exato (valores E
   ordem), então um array reordenado continua PRESERVED. `old` fica o de 4
   ids (adopter pré-rc nunca atualizado). Tudo derivado por
   `--print-settings-baselines` nos testes — sem literal re-digitado, salvo
   o literal CONGELADO da lista de 6 em `TestSupersededShippedBaseline`, que
   existe exatamente para não ser removido.
4. **Custo é a classe T1.5.** Modelo da frota sem linha de preço = custo $0
   em silêncio (foi assim que o 4.8 e o Fable 5 nasceram invisíveis). As 5
   tabelas + 2 detectores + alias do normalizador entram com o teste da frota
   (`test_model_fleet_presence.py`) ampliado — e `provider-pricing.md` porque
   a tabela primária É consumida (`_cost.py`, `budget-summary.py`,
   `ceo-cost.py`, `ceo-info.py`).
5. **O pin NÃO flipa — e isto está DECLARADO, não omitido.**
   `test_template_dogfood_parity.py` exige pin IDÊNTICO nos três espelhos
   (`EXPECTED_PIN`), e o `upgrade.sh` migra o pin por baseline: flipar é
   tudo-ou-nada com custo default do adopter ×2 e uma migração nova. É outra
   decisão. Para o Owner trabalhar em 5.1 nesta máquina basta
   `.claude/settings.local.json` com `"model": "claude-fable-5-1"` (camada de
   maior precedência; o `--check` do gerador resolve o overlay). O V4/V6
   PROVAM que o pin e o fallback não mudaram.
6. **KERNEL:** `settings.json` ∈ `_KERNEL_PATHS`; o LAND arma o override no
   menor escopo (molde 183batch/179close/adrgate; T20e do harness avalia o
   par contra `_override_granted()` VIVO).
7. **`scripts/` tocado ⇒ ratchet devido no MESMO patch** (regra do
   CLAUDE.md §5). Medido: rc 0 SEM regenerar o baseline — edições de literal
   e de branch não criam sítio de escrita. O V9e continua rodando: um sítio
   novo que entrasse por engano ficaria vermelho.

8. **O rail muda o desenho, não só o texto (r1/r2).** (a) `learn._tier_rank`
   é um ladder LITERAL, não derivado do ADR: um id admitido em
   `VALID_MODEL_IDS` sem rank vale -1 e inverte a direção do gate de
   demote — a cura é o rank 7 + um teste de PARIDADE allowlist↔ladder (a
   classe fecha para o próximo append; a derivação da autoridade continua
   sendo o W4.3 do PLAN-169). (b) A premissa «nenhuma superfície modela
   cache-read» estava ERRADA: `budget-summary.py` aplica 0.10× fixo — e a
   página oficial de pricing resolveu o conflito do S337: 5.1 = 0.025×
   ($0.25/MTok), o único modelo fora do padrão ⇒ multiplicador por modelo.
   (c) Dois ids Fable tornam o alias bare `fable` AMBÍGUO por doutrina; o
   custo real era TBD em todo spawn nativo cujo meta carrega o alias — a
   cura preserva a doutrina (nunca adivinhar) e usa a evidência EXATA do
   transcript. (d) `price_for` do registro canônico resolvia `-1` como se
   fosse um pin datado: só `^\d{8}$` resolve agora; adicionar row à mão
   quebraria a proveniência (Owner fetch + checksum) — 5.1 fica UNKNOWN lá
   até o re-fetch.
   (e) `success-receipt.py:_DEFAULT_PRICING` era PRÉ-gen-5 — o único
   espelho de preço que o teste da frota não amarrava; em sessão mista o
   recibo descartava a frota corrente em silêncio (r3). A cura é a frota
   inteira, não só o 5.1: é a classe, e a guarda nova a fecha para o
   próximo append. Os outros espelhos de `model-deprecations.json:223`
   foram varridos: `generate-dispatch`/`spot-check-findings` sem tabela,
   `_ADAPTIVE_ONLY_MODELS` casa por prefixo (correto sem edição).
9. **Claim minha corrigida pelo instrumento.** Afirmei que a parity e2e
   ficaria vermelha sem `superseded`; medido: `settings.json` é divergência
   ACEITA («keys, not bytes») — a CI não pegaria. A cura ficou mais
   necessária, não menos; o texto foi corrigido nos três lugares.

## O que fica FORA, nomeado

- Rotas (a)/(b) (floor + agents) — amendment futuro do Owner, por medição.
- `_lib/model_routing.py` (`_ROUTING_TABLE`), enum `MODEL_ID` dos hooks,
  `set-quality-profile.sh` (derivado), `team.md`/SKILL do FinOps
  (Gate-1/2 cache-stable — closeout).
- `CHANGELOG.md` (registrado no corte da v1.4.0, como o precedente 8ed9f6f).
- `_VALID_MODELS` de `codex_cli_shape.py` (allowlist do CODEX, não da
  Anthropic — item do checklist do PLAN-176, não desta cerimônia).

## Números medidos (fontes no EXPECTED-BASELINE.txt)

- 30 paths: 5 canônicos (KERNEL 1) + 25 livres; 1 membro do manifesto; 19
  `.py` + 3 `.sh`; unit 351/2 (após r1–r3); generator 7 ids; floor 3; superseded 1;
  id novo em HEAD 0×; parity smoke PASS em 35 s; governança completa
  `Errors: 0`; verify-counts rc 0; ratchet rc 0.

## Mold-findings

- O harness herdado usava `grep -ohE '_expect [A-Z0-9_]+'` (já curado no
  batch); mantido. Nenhum mold-finding novo até a r1 do rail.
