---
round: 2
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer (Principal)
generated_at: 2026-09-02T17:40:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- **Dez dos meus onze must-fix do round 1 estão RESOLVIDOS, um PARCIAL, nenhum aberto.**
  Resolvidos: `fail-fast: false` + gate de forma (§3 W4, C-K13, e as duas matrizes da casa
  estão mesmo em `validate.yml:1578` e `:1613`); baseline de node-ids pela UNIÃO com os dois
  passes (§3 W4 + AC-6); composite bootstrap com `gens>=2` e o `shasum -c` do ADR-192 (§3 W4);
  nome de job preservado, agora com **3** sítios — verifiquei o terceiro,
  `templates/.github/workflows/validate.yml.template:33` (§3 W4, C-K16); toolchain replicado
  com assert (§3 W4, C-K15); enforce da W1 com `spawn_model_recorded` e
  `CEO_SPAWN_MODEL_REQUIRED=1` UNSET (§3 W1); os dois ids no piso VETO durante a transição
  (§3 W3); sonda de concorrência re-desenhada com controle positivo, célula de output alto e
  célula de dois terminais, com a OQ-4 reaberta (§3 W0-US2 + AC-2 + §2 pergunta 2); sonda de
  hookabilidade antes do rail (§3 W0-US6 + OQ-5); correlation id nos dois projetos com
  veredito de recusa (§3 W5-US3 + AC-8).
- **PARCIAL: o meu must-fix 6 (delta de runner-minutos medido e gated no PLAN-184).** O
  plano ganhou AC-11 e OQ-8, que é progresso real, mas o AC não tem instrumento e a
  dependência não está declarada. Verifiquei no `PLAN-184-ci-cost-routing.md`: o endpoint
  clássico de billing responde **410**, o que sobrou agrega por **mês sem eixo de workflow**
  e atribui os minutos de 8-core ao **repositório errado**, a base de tempo canônica e a
  fórmula de conversão são um item **ABERTO** `[P0][US4]`, a reconciliação por-run é outro
  `[P0][US5]` com os números marcados `NÃO-DERIVADOS`, e o plano inteiro está em `status:
  draft`. O AC-11 do PLAN-186 está ancorado nisso e o `depends_on:` cita só o PLAN-169.
- **Dois riscos que a revisão criou, mais um que o AC novo tornou decisivo.** O AC-11 mede
  minutos sem distinguir runner pago de runner grátis, e isso reprova a matriz do Smoke por
  um número que custa zero. O composite bootstrap não pode conter o `actions/checkout`. E,
  agora que runner-minutos viraram AC em vez de nota de rodapé, o mecanismo escolhido para o
  Validate é o mais caro dos dois disponíveis: os dois steps mais pesados do job já são
  re-executados por `hook-tests-python-matrix (3.12)`, e nenhuma das duas rotas baixa do mesmo
  piso de 10m39s.

## Risks

- **R-DEV16 — HIGH — o AC-11 mede minutos sem distinguir runner pago de runner grátis.**
  O repo é público. `smoke-install.yml:196` roda em `ubuntu-latest`, cujos minutos são
  gratuitos para repositório público; `validate.yml:36` e as duas matrizes rodam em `Ceo`,
  larger runner pago por budget de org. A matriz do Smoke por step multiplica minutos de
  `ubuntu-latest` por ~15 legs — provavelmente 2× a 3× o total de hoje — e o AC-11
  («runner-minutos totais ≤ 1,3× do baseline pré-matriz») a reprova por um número que não
  custa nada, enquanto o mesmo AC passa folgado no Validate, que é onde o dinheiro está.
  Um AC que morde no lugar errado ou é relaxado por exceção, ou vira teatro.
  *Mitigação:* denominar o AC-11 por CLASSE de runner. Minutos de `Ceo` convertidos em
  dólares e comparados ao teto do PLAN-184; minutos de `ubuntu-latest` REPORTADOS e gated,
  se for o caso, contra o limite de jobs concorrentes da conta, não contra custo.
  Esforço: 10-20k tokens, dentro da W4.

- **R-DEV17 — HIGH — o AC-11 está gated numa base de custo que o próprio PLAN-184 declara
  não-derivada, e a dependência não está no `depends_on:`.** Verificado em disco: o
  PLAN-184 está em `status: draft`; seu `[P0][US4]` («congelar o baseline de confirmação —
  comando/endpoint, base de tempo canônica em US$/dia-calendário, fórmula de conversão») está
  ABERTO; seu `[P0][US5]` diz que enquanto as duas bases de custo por-run não reconciliarem,
  «os números US$ 194 / US$ 224 permanecem marcados NÃO-DERIVADOS»; e o próprio plano
  registra que o endpoint clássico dá **HTTP 410**, que o substituto devolve nove itens
  agregados por MÊS sem eixo de workflow, e que ele atribui os minutos de 8-core ao
  repositório `-private` em vez do público. O AC-11 do PLAN-186 diz «comparados ao teto
  diário do PLAN-184 A0» sem nomear como o número do PLAN-186 é produzido. É o mesmo defeito
  que esta revisão curou nos irmãos: o AC-1 foi reancorado no que a W0 provou e o AC-6 ganhou
  um ponto de medição exato; o AC-11 não ganhou nenhum.
  *Mitigação:* nomear o instrumento no próprio AC — soma de `gh run view <id> --json jobs`
  por classe de runner, que é o método que o `[P0][US5]` do PLAN-184 já elegeu — e declarar
  `depends_on: [PLAN-169, PLAN-184]`, ou escrever que o AC-11 se compara a um baseline
  LOCAL de 3 runs verdes pré-matriz e NÃO ao teto diário enquanto o PLAN-184 não fechar.
  Esforço: 15-30k tokens / 0,5 sessão.

- **R-DEV18 — HIGH — agora que runner-minutos são AC, o mecanismo escolhido para o Validate é
  o mais caro dos dois, e o barato é uma deleção.** Verificado em disco: o job
  `hook-tests-python-matrix` roda, no `push`, em 3.9 **e 3.12**,
  `pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/` nos
  dois passes (`validate.yml:1636-1646`) — exatamente a união dos dois steps mais caros do
  job `validate`, «Run Python hook unit tests» (`:454`, 5m57s) e «Run Python script unit
  tests» (`:539`, 8m05s), que também rodam em 3.12. São 14m02s dos 22m22s do job. Somando
  `hook-tests-dual-rail` (3.11, `native_subagents` 0 e 1), `.claude/hooks/tests/` roda
  **cinco vezes por push**. Splitar re-executa em VMs novas o que uma terceira VM já executa;
  e as duas rotas batem no MESMO piso, porque o bound do workflow é
  `hook-tests-python-matrix (3.12)` a 10m39s, um job que a W4 não toca.

  | rota | job `validate` | caminho crítico | minutos `Ceo` da porção |
  |---|---|---|---|
  | hoje | 22m22s | 10m39s (bound alheio) | 22m22s |
  | split em 3 jobs | ~3m50s + 3 jobs | 10m39s | ~26m21s (1,18×) |
  | deduplicar os 2 steps | ~8m20s | 10m39s | ~8m20s (0,37×) |

  O split não compra relógio sobre a deleção e custa ~+4 min pagos por push contra −14 min.
  **Em defesa do split:** `validate.yml` não tem nenhum `if: always()` (contei: zero), então
  hoje um teste de hook vermelho impede o installer-matrix e os script tests de rodarem —
  atribuição independente é um ganho real que a deleção não dá. As duas coisas são
  COMPLEMENTARES, não alternativas.
  *Mitigação:* medir a deleção primeiro, numa execução, e só então decidir se os ~8m20s
  restantes merecem split — cuja justificativa passa a ser atribuição, não velocidade. A
  deleção é gated pelo MESMO baseline de node-ids que o plano já exige, mais uma declaração
  de delta de ambiente: `PYTHONPATH: "."` está no matrix e ausente nos dois steps do
  `validate`, e para `.claude/scripts/tests/` o dual-rail não dá cobertura, logo a deleção
  deixaria essa raiz rodando SÓ com `PYTHONPATH` setado.
  Esforço da medição: 20-40k tokens / 0,5 sessão.

- **R-DEV19 — MEDIUM — o composite bootstrap não pode conter o `actions/checkout`.**
  §3 W4 lista «checkout, fetch do pin e das tags, `--unshallow` com guard `gens>=2`,
  `Gate-scripts integrity` do ADR-192, jq, setup-python» dentro de
  `.github/actions/smoke-bootstrap`. Uma referência local (`uses: ./.github/actions/...`)
  exige que o repositório JÁ esteja em disco no job, então o checkout tem de ser o primeiro
  step de cada leg, fora do composite. Falha alto na primeira execução, não em silêncio — mas
  o «gate que asserta que TODO leg usa o composite» passa a ter de asseverar DUAS coisas.
  Nota boa: `check-action-sha-drift.py` já isenta `./` e `docker://` (`_EXEMPT_PREFIXES`,
  linha 83), então o composite local não quebra o gate C12.
  *Mitigação:* mover o checkout para fora, e o gate asserta `actions/checkout` pinado +
  `uses: ./.github/actions/smoke-bootstrap` em cada leg. Esforço: trivial, dentro da W4.

- **R-DEV20 — LOW-MEDIUM — o AC-6 tem um teto que a W4 não controla.** Com qualquer das duas
  rotas o caminho crítico do Validate para em `hook-tests-python-matrix (3.12)`, 10m39s
  medidos. O alvo «≤ 14 min» é atingível hoje com ~3 min de folga, mas essa folga pertence a
  um job fora do escopo da wave: se ele crescer, o AC-6 reprova por motivo alheio, e a leitura
  natural será «a matriz regrediu».
  *Mitigação:* escrever no AC-6 qual é o job-bound e sua duração medida, para que um AC-6
  vermelho seja diagnosticável sem re-derivar. Esforço: trivial.

## Must-fix (blocking)

1. **AC-11 denominado por classe de runner** — dólares para `Ceo`, minutos de
   `ubuntu-latest` reportados e não gated por custo. Sem isso o AC reprova a matriz do Smoke
   por minutos gratuitos e passa no Validate, que é onde o dinheiro está. (R-DEV16)
2. **AC-11 ganha instrumento nomeado e a dependência é declarada** — soma por classe de
   runner via `gh run view <id> --json jobs`, e ou `depends_on: [PLAN-169, PLAN-184]`, ou o
   AC compara contra um baseline local de 3 runs verdes pré-matriz enquanto os dois `[P0]`
   do PLAN-184 seguirem abertos e seus números marcados `NÃO-DERIVADOS`. (R-DEV17)
3. **Medir a rota de deduplicação antes de construir o split do Validate** — uma execução,
   gated pelo baseline de node-ids que o plano já exige, com o delta de `PYTHONPATH` e a
   cobertura de `.claude/scripts/tests/` declarados. Se a deleção for recusada por cobertura,
   a recusa fica escrita e o split segue. (R-DEV18)
4. **O `actions/checkout` sai do composite** e o gate de uso asserta checkout + composite em
   cada leg. (R-DEV19)

## Nice-to-have (advisory)

1. AC-6 nomeia o job-bound (`hook-tests-python-matrix (3.12)`, 10m39s medidos) para que um
   vermelho seja diagnosticável sem re-derivação. (R-DEV20)
2. **Não** compartilhar o `.git` entre legs do Smoke por artifact ou cache para evitar 15
   `--unshallow`: isso re-introduziria exatamente o acoplamento entre jobs que a revisão
   acabou de provar ausente (`GITHUB_ENV`, `GITHUB_OUTPUT`, artifacts e `actions/cache` dão
   zero nos dois workflows). Deepen por leg, e o custo entra no dimensionamento do timeout.
3. Registrar no §3 W4 que `.claude/hooks/tests/` roda cinco vezes por push hoje — é o número
   que explica o custo do Validate e o candidato natural da próxima rodada de corte, com ou
   sem matriz.
4. Manter os filtros de path `push` e `pull_request` do Smoke idênticos e não introduzir
   filtro por leg. O comentário «KEEP IDENTICAL» documenta um buraco já pago uma vez; foi o
   único advisory do meu round 1 que não apareceu no plano revisado.
5. O composite `.github/actions/smoke-bootstrap` é asset interno de CI: não deve vazar para
   `templates/.github/`, e o classificador de paridade não deve passar a tratar
   `.github/actions/` como árvore entregue.

## Unseen by the original plan

1. Os dois steps mais caros do job `validate` já são cobertos por
   `hook-tests-python-matrix (3.12)`; `.claude/hooks/tests/` roda cinco vezes por push. A
   duplicação ficou invisível enquanto runner-minutos eram nota de rodapé e virou decisiva
   quando a revisão criou o AC-11.
2. Ambas as rotas do Validate param no mesmo piso de 10m39s, que pertence a um job fora do
   escopo da W4 — o alvo de −43 % é atingido por qualquer uma, e nenhuma vai além.
3. `validate.yml` não tem nenhum `if: always()`: hoje um step vermelho no meio do job impede
   os posteriores de rodar. Isso é o argumento REAL a favor do split, e o plano justifica o
   split por velocidade, que é onde ele não ganha.
4. Referência local a composite exige checkout prévio — o composite não pode se auto-hospedar.
5. Minutos de `ubuntu-latest` são gratuitos num repo público e minutos de `Ceo` não; um AC
   único sobre «runner-minutos totais» trata as duas coisas como a mesma moeda.
6. O PLAN-184, ao qual o AC-11 se ancora, está em `draft` com a base de custo em dois itens
   `[P0]` abertos, o endpoint clássico em 410, o agregado mensal sem eixo de workflow e a
   atribuição de 8-core apontando para o repositório errado.

## What I would NOT change

1. **Toda a §3 W4 herdada do round 1.** `fail-fast: false` com gate de forma, baseline de
   node-ids pela união dos dois passes, composite bootstrap com `gens>=2` e o `shasum -c` do
   ADR-192, nome de job preservado nos três sítios, toolchain replicado com assert, timeouts
   por leg preservando as cem linhas de derivação como ledger. Está tudo correto e nada disso
   deve ser «simplificado» na implementação.
2. **A ordem Validate antes de Smoke**, e o gate de perf permanecendo em `ubuntu-latest`.
3. **Não paralelizar o V-block do LAND.** Continua fora, pelas mesmas razões.
4. **A W0 antes da W3.** Condicionar a W3 à resposta da US4 sobre precedência `inherit` × pin
   é a decisão mais forte desta revisão: se `inherit` vence, o piso VETO não é enforcement de
   runtime, e isso é um achado de governança maior que a wave que o descobriu.
5. **A OQ-4 reaberta e o AC-2 exigindo controle positivo do detector.** Não afrouxar isso
   porque a repetição custa tempo de janela.
6. **O escape declarado da W5-US3** — se correlacionar as duas cadeias for proibitivo, o ADR
   declara a incorrelação como limite aceito, no molde do ADR-190. Declarar um limite é
   melhor que um rail que finge cobrir.
7. **A recusa de Haiku sem evidência de torneio**, escrita no `tier_mix_rationale` justamente
   para que ninguém «restaure» a opção mais barata depois de ler o estudo.
