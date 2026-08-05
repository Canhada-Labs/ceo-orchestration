---
round: 3
archetype: Principal Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (core team.md ICs — VETO em auth/token/input-handling per ADR-052)
generated_at: 2026-08-05T00:00:00Z
veto_round_1: LEVANTADO (AC-2 bind conjuntivo verificado literalmente no r2)
veto_round_2: LEVANTADO-CONFIRMADO (marcador rastreado, design v3 re-verificado)
veto_round_3: LEVANTADO (condição (a)(b)(c) verificada literalmente no W0.2 em 2026-08-05; must-fix 2-6 também aplicados)
---

## Verdict

**ADJUST** — nenhuma das mudanças r3-r17 enfraqueceu um controle que eu
exigi (várias fortaleceram), mas o controle NOVO mais poderoso do plano —
o assert de delta server-side — está especificado com uma frase ambígua
sobre POSIÇÃO, e a posição decide se ele é enforcement ou teatro. **VETO
escopado, com condição de levantamento de uma linha.**

## Summary (≤ 3 bullets)

- **Meus controles sobrevivem intactos.** Verifiquei um a um: o bind
  conjuntivo do AC-2 continua conjuntivo e ficou MELHOR especificado
  (GRANT/WAIT/BLOCK por avaliação de ponto, com fixture GRANT obrigatório
  contra a implementação sempre-BLOCK — que era um buraco meu, não deles);
  a semântica de candidato do r14/r16 **não** relaxa o bind, ela só
  impede que a release perca a corrida contra a própria presença na lista
  de runs; a `if` de RC e o `environment` seguem verbatim no job publish;
  os pins são fortalecidos.
- **Duas correções ao meu próprio raciocínio do round 1**, que registro
  porque mudam a leitura do risco: (i) com verdito POR TAG commitado antes
  de cada tag, GA e rc.2 **nunca** apontam para o mesmo commit — o cenário
  R-SEC1 que motivou meu primeiro VETO deixou de ser alcançável por
  construção, e o `head_branch` permanece como defesa em profundidade, não
  como única barreira; (ii) o `gpg_signature` do verdito é só um campo
  não-vazio no validador (`validate-pair-rail-verdict.py:497-502`), mas o
  conteúdo do verdito **está** coberto pela assinatura do Owner via a tag
  assinada sobre a árvore — a corrente é sólida, desde que a ordem dos
  steps seja respeitada (é exatamente o que o VETO cobra).
- **O que quebra:** o assert de delta ancora em `parent_sha` **lido do
  verdito**, e o step que valida esse campo tem duas escotilhas vivas —
  `continue-on-error` e `--parent-sha ""` — ambas acionadas pela mesma
  variável de repositório. Herdar a vizinhança é herdar as escotilhas.

## Risks

**R3-SEC1 — CRITICAL — o assert de delta pode ancorar num `parent_sha`
que ninguém validou.** Verifiquei a mecânica:
`validate-pair-rail-verdict.py:245` faz o bind **só** `if args.parent_sha:`
— com argumento vazio, o campo não é checado. E `release.yml:690-692`
passa `PARENT_SHA_ARG=""` exatamente quando
`vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL == '1'`, a mesma variável que põe
`continue-on-error: true` no step inteiro (`:656`). O W0.2 diz que o novo
assert "entra SERVER-SIDE no `release.yml`, **ao lado** da validação de
verdito existente". Se "ao lado" virar "no mesmo step" ou "no step
seguinte com a mesma condicional", então com essa variável ligada:
`parent_sha` declarado = commit da própria tag → `git diff
parent_sha..HEAD` = vazio → assert passa **vacuamente**, e o GA embarca
qualquer commit pós-review. O controle que existe para provar "nada
landou depois da revisão" seria desarmado pela variável que existe para
tolerar verditos legados.
*Mitigação:* Must-fix 1 (uma frase no plano).

**R3-SEC2 — HIGH — conjunto fechado por NOME não é conjunto fechado.**
O r14 corretamente matou o wildcard `repass-<N>/**`. Mas o texto pina
"os nomes exatos + `MANIFEST.sha256`" e descreve o enforcement como "o
assert rejeita qualquer path extra" — isto é, **igualdade de conjunto de
caminhos**. Se o `MANIFEST.sha256` é ele próprio um dos arquivos pinados
por nome, então reescrever um artefato de evidência **e** o manifest
junto satisfaz o assert: fechado por nome, aberto por conteúdo. É o
mesmo buraco do r14 um nível abaixo.
*Mitigação:* o verdito assinado pina o **sha256 do MANIFEST**, e o assert
roda `shasum -c` sobre ele (conteúdo), além da igualdade de conjunto.

**R3-SEC3 — HIGH — a cerimônia W1 passou a exigir a rota de kernel, e
isso precisa de limite explícito.** Confirmei: `.github/workflows/release.yml`
é entrada EXATA de `_KERNEL_PATHS` (`check_arbitration_kernel.py`, bloco
`(10-11) release.yml + validate.yml -> CI gate bypass (vector 2)`). O
plano acertou em listá-la; o que falta é a disciplina do override. A
razão de o kernel guardar esse arquivo é literalmente "quem edita
release.yml burla o gate de CI" — então armar `CEO_KERNEL_OVERRIDE` para
a cerimônia é o maior privilégio do repo sendo concedido na mesma
release que fecha um P0 de publish. Sem escopo declarado, o override fica
armado além do necessário.
*Mitigação:* nomear no plano o token exato, declarar que ele é
**por-cerimônia** (nunca exportado em `settings.local.json` nem em perfil
de shell), e exigir que o evento de auditoria do override apareça no
ledger da cerimônia — a mesma prova-ao-vivo que a cerimônia 2 de S293 já
produziu para o `night_mode_toggled`.

**R3-SEC4 — MEDIUM — o `approx` de ±5% é um afrouxamento deliberado de
gate, e o motivo declarado é um sintoma não tratado.** O W0.3 justifica a
banda porque "o collect-count real varia com ruído de coleta" e cita
**14.219 com 22 erros de coleta vs 14.172 limpo**. Ou seja: a população
varia porque a coleta ERRA, e a resposta é ampliar a tolerância. ±5% sobre
~14.000 é ±700 casos — largo o bastante para uma família inteira de testes
sumir sem acusar. Isto colide com a lição da casa que o próprio plano cita
em outros pontos ("medição que sustenta decisão TEM de imprimir seus
inputs"; "prefira argumento de CONTAGEM a estimador").
*Mitigação:* manter a banda (o undersell é real), mas exigir que a regra
`approx` **imprima o comando de coleta, o valor observado e a contagem de
erros de coleta**, e que erros de coleta > 0 sejam pelo menos um WARNING
nomeado — banda sem inputs impressos é licença de drift.

**R3-SEC5 — MEDIUM — ordem de steps não declarada = corrente sem prova.**
A confiança do assert de delta vem de a árvore estar coberta pela
assinatura da tag: `release.yml:606-610` (`gpg --import` + `git tag
--verify`) é o que torna o conteúdo do verdito confiável, já que o
validador só checa a presença do campo `gpg_signature`
(`validate-pair-rail-verdict.py:497-502`, comentário explícito). Hoje o
step 15 (`:647`) já vem depois do verify (`:606`) — mas por acidente de
ordenação do arquivo, não por requisito escrito. Um assert novo inserido
ANTES do verify leria a lista pinada de uma árvore ainda não verificada.
*Mitigação:* o plano declara a ordem obrigatória: `Verify tag GPG
signature` → validação do verdito → assert de delta → assert de
ancestralidade. Uma linha.

**R3-SEC6 — LOW/MEDIUM — dois candidatos para a mesma tag.** Investiguei
o cenário que parecia contradizer a rota de recuperação do §Riscos:
re-run de um `release.yml` vermelho **não** cria um segundo run (o mesmo
run muda `conclusion` e incrementa `run_attempt`), então "re-rodar até
verde" é compatível com "candidato exato failed bloqueia". A ambiguidade
sobrevive só no caminho delete+re-tag no MESMO SHA (`concurrency` com
`cancel-in-progress: false`, `release.yml:8-10`): aí existem dois runs
candidatos, um failed e um success.
*Mitigação:* a função de decisão declara a regra de resolução — avaliar o
candidato mais recente por `run_attempt`/`created_at`, e o fixture
correspondente entra na enumeração do AC-2 (que é a fonte única).

## Must-fix (blocking)

1. **[VETO escopado — condição textual] O assert de delta e o de
   ancestralidade são INDEPENDENTES do `CEO_PAIR_RAIL_VERDICT_OPTIONAL`.**
   Levanto o VETO quando o W0.2 disser, textualmente, que os dois asserts
   novos: (a) rodam em step PRÓPRIO, **sem** `continue-on-error`; (b)
   **falham fechado** se `vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL == '1'` ou
   se o `parent_sha` não foi validado com bind não-vazio — nunca
   ancorando num campo que o validador pulou; e (c) rodam **depois** do
   step `Verify tag GPG signature`. Sem (b), a variável de transição vira
   interruptor do controle P0 desta release. Autoridade: ADR-052 (mudança
   de trust/provenance).
2. **Fechar o conjunto por CONTEÚDO, não só por nome (R3-SEC2).** O
   verdito assinado pina o sha256 do `MANIFEST.sha256`; o assert roda
   `shasum -c` além de comparar o conjunto de paths. Controle positivo:
   editar um artefato de evidência + regravar o manifest → o assert TEM
   de falhar.
3. **Declarar a ordem dos steps no `release.yml` (R3-SEC5)** — verify da
   tag → verdito → delta → ancestralidade — como requisito escrito, com
   assert estrutural em `test_release_workflow_asserts.py` (o padrão
   WaveB5 já usa asserts de ordem: `test_rc_exclusion_precedes_publish_command`).
4. **Disciplina do kernel-override (R3-SEC3):** token nomeado, escopo
   por-cerimônia, evento de auditoria no ledger. Sem isso, a cerimônia
   W1 concede o privilégio máximo do repo sem deixar rastro dimensionado.
5. **A regra `approx` imprime seus inputs (R3-SEC4):** comando de coleta,
   valor observado, erros de coleta; erro de coleta > 0 é WARNING nomeado.
   A banda fica; a opacidade não.
6. **Regra de resolução para candidatos múltiplos (R3-SEC6)**, com o
   fixture correspondente na enumeração do AC-2.

## Nice-to-have (advisory)

1. O `await-release-gate` recebe `GH_TOKEN: ${{ github.token }}` no env do
   JOB — correto e mínimo (o job só tem `contents: read` + `actions:
   read`). Vale o comentário de uma linha dizendo que o token é do job e
   não da workflow, para ninguém "simplificar" movendo-o para o topo e
   entregando-o também ao job de publish, que não precisa dele.
2. O §Deferred já tem o ADR break-glass para `CEO_SOTA_DISABLE` e
   `CEO_PAIR_RAIL_VERDICT_OPTIONAL`. Depois do R3-SEC1, esse item deixou
   de ser higiene: dois controles P0 desta release dependem de essas
   variáveis não estarem ligadas. Sugiro promover o gatilho — "antes do
   próximo trem que dependa do verdito", não "plano próprio algum dia".
3. O AC-2 já declara o que a rc.2 não prova. Vale a simétrica para o
   assert de delta: a rc.2 o exercita (r12 tornou-o incondicional), mas o
   caminho GA-específico — delta contendo o verdito **do GA** ancorado no
   parent revisado do hold — só roda no GA.
4. `check-framework-updates.sh` marker-first (r8) continua sendo o leitor
   que eu marquei no round 2 como acoplado ao inventário FMS. Nada mudou
   para pior; só reitero o acoplamento para a cascata.

## Unseen by the original plan

1. **A variável de transição é hoje a chave-mestra de TRÊS controles.**
   Com o r15, `CEO_PAIR_RAIL_VERDICT_OPTIONAL` passa a governar: o step
   15 (via `continue-on-error`), o bind de `parent_sha` (via
   `--parent-sha ""`) e — se herdar a vizinhança — o assert de delta e o
   de ancestralidade. Um único `gh variable set` desarma a corrente
   inteira de provenance desta release. O plano trata cada assert como
   uma peça nova e independente; eles compartilham um interruptor.
2. **A cerimônia W1 tem duas classes de privilégio, não uma.** O plano
   diz "7 superfícies que exigem sentinel" e menciona a rota de kernel
   para o `release.yml`. Mas sentinel e kernel-override são autoridades
   diferentes: a primeira o Owner assina por escopo, a segunda desliga um
   rail que existe justamente porque o sentinel é escapável. Vale
   registrar no `approved.md` **qual** caminho foi landado por qual
   autoridade — senão a leitura forense futura da cerimônia não distingue
   os dois.
3. **O `bump` agora escreve um 12º site que é a âncora forense do
   adopter.** `.claude/.framework-version` entrou em `VERSION_SITES` (bom,
   foi minha condição), o que significa que o mesmo laço que corrige
   contagens de doc agora reescreve a âncora que o `check-framework-updates.sh`
   do adopter usa. Nada de errado — mas o `--restamp` e o fast-path de
   no-op passam a ter alcance sobre uma superfície de confiança, e o
   teste D/D+1 do AC-1 deve incluir o marcador entre os arquivos cuja
   NÃO-ESCRITA é verificada, não só os 4 stamps.

## What I would NOT change

- **A semântica de candidato (r14/r16).** Eu conferi que ela não relaxa o
  bind: os quatro fixtures NUNCA-GRANT (head_branch de rc, SHA de outro
  commit, workflow errado com `release-gate` verde no mesmo ref,
  `workflow_dispatch`) provam que "run verde parecido" nem libera nem
  bloqueia falsamente. Ignorar não-candidatos é obrigatório — o próprio
  run do `npm-publish` está na lista.
- **O fixture GRANT obrigatório.** Minha bateria de round 2 tinha só
  controles negativos; uma implementação sempre-BLOCK passaria em todos.
  Foi um buraco meu e o plano fechou.
- **O assert de delta incondicional na RC (r12).** Escopar ao `--stable`
  deixaria a rc.2 virar baseline não-revisada. Correto, e é o que torna
  o GA≠RC estrutural.
- **`--restamp` exigindo `--npm-readme-reviewed` e excluindo o fast-path
  (r14).** Sem as duas metades, a escotilha seria o bypass do tripwire
  que o OQ-2 inteiro defende.
- **Propriedade condicionada à ENTREGA REAL, não só à ceremony (r17).**
  Inventariar como framework-owned um `SPEC/v1` que o `install_one`
  pulou é o que faria um `uninstall.sh` futuro deletar arquivo de
  adopter. É a mesma classe destrutiva do `VERSION` da raiz, pega uma
  camada mais fundo.
- **O sequenciamento verdito→push main→tag do W2**, e a nota honesta
  sobre o que o `inputs_hash` cobre (payload) versus o que o reviewer lê
  (árvore viva). Dizer mais que isso seria claim falsa; o worktree
  detached no candidato é a mitigação certa e o r17 acertou ao notar que
  exigir worktree da tag era circular.

## Verificação da condição do VETO#3 (pós-aplicação)

**Estado final: VETO#3 LEVANTADO (2026-08-05).** Verificação literal
contra o W0.2 e o §W1 correntes — texto lido, não resumo.

### Condição (a)(b)(c)

| # | Condição (must-fix 1, round 3) | Texto corrente | Estado |
|---|---|---|---|
| (a) | step PRÓPRIO, sem `continue-on-error` | W0.2: "**em step PRÓPRIO, SEM `continue-on-error`, INDEPENDENTE de `CEO_PAIR_RAIL_VERDICT_OPTIONAL`**" | ✅ |
| (b) | falha FECHADO se a var estiver ligada **ou** se `parent_sha` não teve bind não-vazio | W0.2: "os asserts novos FALHAM FECHADO se a var estiver ligada ou se o `parent_sha` não foi validado com bind não-vazio", citando as três evidências que eu levantei — `continue-on-error` em `:656`, `--parent-sha ""` em `:690-692`, e `if args.parent_sha:` em `:245` | ✅ |
| (c) | depois do `Verify tag GPG signature`, com ordem declarada e pinada | W0.2: "rodam DEPOIS do step `Verify tag GPG signature` com a ordem verify→verdito→delta→ancestralidade DECLARADA e pinada por assert estrutural no padrão WaveB5 de ordem" | ✅ |

O ponto que motivou o VETO — "ao lado da validação de verdito existente"
— desapareceu como frase ambígua e virou especificação de posição,
condicional e ordem. Era exatamente o que faltava.

### Must-fix 2-6

| # | Exigência | Texto corrente | Estado |
|---|---|---|---|
| 2 | conjunto fechado por CONTEÚDO (`shasum -c` do MANIFEST pinado) + controle positivo | W0.2: "O conjunto pinado fecha por CONTEÚDO, não só por nome (r3-SEC2): o verdito assinado pina o sha256 do `MANIFEST.sha256` e o assert roda `shasum -c` além da igualdade de conjunto — controle positivo: editar evidência + regravar manifest TEM de falhar" | ✅ |
| 3 | ordem declarada + assert estrutural WaveB5 | absorvido em (c) acima | ✅ |
| 4 | disciplina do kernel-override | §W1, bloco de abertura: token `CEO_KERNEL_OVERRIDE` **POR-CERIMÔNIA**, "nunca exportado em `settings.local.json` nem em perfil de shell", evento de auditoria no ledger com o precedente `night_mode_toggled` da cerimônia 2/S293, e o motivo nomeado ("editar `release.yml` é literalmente o vetor CI gate bypass") | ✅ |
| 5 | `approx` imprime seus inputs; erros de coleta > 0 = WARNING | W0.3: "**a regra IMPRIME seus inputs** (comando de coleta, valor observado e contagem de erros de coleta; erros > 0 = WARNING nomeado — banda sem inputs impressos é licença de drift, e ±700 casos escondem uma família inteira)" | ✅ |
| 6 | resolução de candidatos múltiplos + fixture no AC-2 | W0.2: "Runs múltiplos para o mesmo SHA (delete+re-tag): a função de decisão avalia o candidato mais recente por `run_attempt`/`created_at`, com fixture na enumeração do AC-2" | ✅ |

### Observação de encerramento

Um efeito colateral que vale registrar: com (b), o
`CEO_PAIR_RAIL_VERDICT_OPTIONAL` deixa de ser chave-mestra de três
controles e volta a governar só o que foi desenhado para governar (o
step 15 legado). O item do §Deferred (ADR break-glass para
kill-switches em variáveis de repositório) continua valendo, mas deixou
de ser pré-requisito de segurança desta release — que era a única razão
pela qual eu o teria promovido.

Nenhum VETO aberto: **#1 LEVANTADO**, **#2 LEVANTADO-CONFIRMADO**,
**#3 LEVANTADO**. **PROCEED** do lado de segurança para a cascata V0-V3;
a execução de W1 permanece atrás da cerimônia GPG, como o plano declara.
