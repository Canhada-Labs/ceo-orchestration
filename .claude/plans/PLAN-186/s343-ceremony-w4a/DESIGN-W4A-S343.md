# DESIGN — wave-s343-w4a (PLAN-186 W4a, montada na noite S343)

> Nada aqui é fonte de número. Os valores que os gates comparam vivem em
> `EXPECTED-BASELINE.txt`, e é de lá que `finalize-w4a.sh`,
> `OWNER-S343-W4A-SIGN.sh`, `OWNER-S343-W4A-LAND.sh` e
> `OWNER-S343-W4A-MEASURE.sh` os leem. Este documento explica DECISÕES.

## 1. O que a wave é, em uma frase

Deletar do job `validate` os dois steps cuja união exata de node-ids o job
`hook-tests-python-matrix` já roda — e, de carona, executar o bump do
`timeout-minutes` do Smoke Install que o Owner difere desde 2026-09-01,
porque o gatilho declarado dele é exatamente «a próxima wave que já toque
`.github/workflows/`».

## 2. Por que a deleção não é uma aposta

O AC-16 tem dois braços. O de **cobertura** foi fechado na S341 e é
RE-DERIVADO aqui, sobre este HEAD, porque a suíte cresceu desde então: os
números da S341 (7 474 / 6 063 / 13 537) já não descrevem esta árvore. A
propriedade, medida hoje:

| recorte | \|A\| hooks | \|B\| scripts+optimizer | A ∩ B | A ∪ B | matriz |
|---|---|---|---|---|---|
| todos | 7 476 | 6 122 | 0 | 13 598 | 13 598 |
| `-m 'not serial'` | 6 982 | 5 670 | 0 | 12 652 | 12 652 |
| `-m 'serial'` | 494 | 452 | 0 | 946 | 946 |

`sha256` da lista ordenada é igual dos dois lados nos três recortes. A
comparação é por CONJUNTO **de propósito**: um gate que só soma aceitaria uma
troca 1-por-1 em silêncio. As contagens declaradas são a segunda perna — elas
pegam o caso em que os dois lados encolhem juntos.

O braço de **execução** são três corridas serializadas, e é o que o
`OWNER-S343-W4A-MEASURE.sh` produz DEPOIS do land.

## 3. Onze edições, e por que cada uma existe

| id | path | edição | por quê |
|---|---|---|---|
| E1 | `validate.yml` | o comentário da nota de double-collection deixa de citar «Run Python script unit tests» pelo nome | E2/E3 apagam esse step. Trocar o código e deixar a prosa velha é a classe `feedback-reconcile-the-conclusions-not-just-the-table` |
| E2 | `validate.yml` | step A fora (com a linha em branco que o separa do banner seguinte) | sem a linha em branco a deleção deixaria duas em branco seguidas |
| E3 | `validate.yml` | step B + o CORPO do banner dele + a régua de FECHAMENTO | a régua de ABERTURA sobrevive e passa a abrir o banner do step PLAN-152 seguinte — por isso a âncora começa no título, não na régua |
| E4 | `validate.yml` | o `env:` da matriz ganha a declaração da perda aceita de `CEO_HOOK_ADAPTER` | a perda tem de estar escrita ONDE o próximo leitor procura, não só num plano |
| E6..E11 | `validate.yml` | os OUTROS SEIS comentários que apontavam para os steps deletados passam a nomear o `hook-tests-python-matrix` | o E1 curou UM sítio; o rail codex r2 achou a CLASSE. «Rail acha a classe, censo MECÂNICO a fecha» — o censo está no V6c, nas duas pernas |
| E5 | `smoke-install.yml` | `126 -> 150` + bloco novo de derivação MEDIDA | ver §5 |

O E1 e o E4 vieram do artefato `validate.deletion.yml.txt` que a S341 deixou
revisado; a árvore-sombra desta wave saiu BYTE-IDÊNTICA a ele (verificado por
`diff`, §6 do EVIDENCE). Isso é deliberado: o `.txt` passou por 21 rodadas de
rail na S341 e re-derivá-lo diferente jogaria fora essa revisão. O que a wave
NÃO reaproveita é a segunda cópia (`validate.deletion.measure.yml.txt`, que
adiciona uma branch descartável a `on.push.branches`): as três corridas
acontecem no `main`, sob sentinel, e a cópia MEASURE-ONLY não tem função aqui.

## 4. O delta de ambiente é duplo, e nenhum lado é «corrigido»

`CEO_HOOK_ADAPTER: claude` existia só no step A, que rodava só
`.claude/hooks/tests`. A matriz roda hooks + scripts + optimizer num ÚNICO
pytest: setá-la lá ALTERARIA o ambiente de scripts/optimizer, que rodavam com
ela ausente tanto no step B quanto na matriz. Como é o default documentado do
adapter, a ausência exercita o MESMO caminho. Perda ACEITA, declarada em E4.

`PYTHONPATH: "."` só existe na matriz. Hoje a suíte roda com e sem; depois, só
com. Recuperar exigiria uma dimensão de matriz que dobra o custo de um job
PAGO. Perda ACEITA.

## 5. O bump do timeout: por que 150, e o que o número NÃO afirma

O gatilho. A memória da S336 registra três, e o que fira é o terceiro: «a
próxima wave que já toque `.github/workflows/` — aí entra de carona, custo
marginal ~zero». Os outros dois **não** dispararam: nenhuma run passou de
101 min e não houve `cancelled` sem causa. Isso está escrito no comentário do
próprio arquivo, para que ninguém leia 150 como resposta a uma emergência.

A base. Todo bloco acima do novo compõe ESTIMATIVAS por step. O bloco novo
mede: wall do JOB `smoke` (`startedAt`→`completedAt`, que é o que
`timeout-minutes` fecha — a nota da S336 lia `1h32` de um RUN, e o mesmo run
mede 92m32s como JOB), nos sete runs verdes mais recentes: de 73m18s a
92m32s. Isso estabelece a FAIXA observada, e nada além dela: o rail r4
apontou (P3, aceito) que os sete runs compartilham a definição do workflow
mas **não** a carga executada — `826688f` mexeu no `smoke-install.sh`,
`ba15c71` no `doctor.sh` e na e2e de write-safety, e este job invoca os
dois. Atribuir o spread ao RUNNER exigiria execuções repetidas no MESMO
sha, que ninguém fez. O bloco dimensiona sobre o MÁXIMO observado e não
afirma causa: 126 dá 33m28s de folga (1,36×); 150 dá 57m28s (1,62×).

O que o número **não** é: previsão. `AGENTS.md:9-11` proíbe claim de
velocidade, e um teto de timeout não é medida de duração. O comentário diz
isso explicitamente e pede re-aperto sobre um p95 real.

## 6. O V-block foi desenhado para ESTA wave, não copiado

| gate | pergunta |
|---|---|
| G6 | os dois steps e o `126` EXISTEM em HEAD? (uma deleção vácua sairia verde sem ele) |
| V1a/V1b | quantos `.py` e `.sh` o patch toca? DECLARADO 0/0 — é guarda de ESCOPO |
| V1c | os dois YAML parseiam; 7 jobs / 1 job; `validate` com 48 steps; `smoke` com 150; a matriz ainda roda as 3 raízes nos 2 passes |
| V3 | `HEAD + derivador == pós-patch`, byte a byte |
| V4 | actionlint com os flags EXATOS do step da CI + `check-action-sha-drift --offline` |
| V5 | **a cobertura, re-derivada** (§2) |
| V6 | não-vácuo pós-patch: steps fora, adapter fora, `150` presente, ledger aditivo PRESERVADO |
| V6c | **o censo dos comentários órfãos**, nas duas pernas: 6 literais velhos a ZERO E o nome do job novo × 8 (`EXPECTED_MATRIX_JOB_MENTIONS`) — só a perna de ausência passaria com os comentários APAGADOS |
| G7 | **a janela de required-check, MEDIDA na config viva** — ver §8 |
| V2 | os 6 testes que LEEM os workflows vivos (conjunto derivado por grep, não lembrado) |
| V8/V9 | corpus: claims, verify-counts, contaminação, ceremony-lint, governança COMPLETA, map, env-hygiene, plugin |

Sobre o V2 não ter contagem declarada: esses 6 arquivos crescem por trabalho
alheio a esta wave, e um número congelado abortaria o land por um teste que
alguém adicionou de madrugada — um gate que reprova pelo motivo errado. O que
uma contagem pegaria (um arquivo que parou de coletar em silêncio) é checado
por conjunto: cada um dos 6 tem de contribuir com ≥ 1 node-id.

## 7. Kernel

`.github/workflows/validate.yml` ∈ `_KERNEL_PATHS`. Isso foi VERIFICADO
carregando `check_arbitration_kernel.py` (não lembrado de uma lista), e o
harness re-verifica ao vivo (T20f): se o path sair do kernel, o override do
LAND vira cerimônia sem sujeito e o comentário passa a mentir.

## 8. O que esta wave NÃO faz, e o residual que exige decisão

Nada de `fail-fast`, matriz, composite ou split — W4b.

O residual real: `docs/BRANCH-PROTECTION.md:101-105` documenta UM status check
obrigatório, o do job `validate`. Depois desta deleção ele não roda mais as
suítes de hooks/scripts. Numa PR, uma matriz vermelha coexistiria com um
Validate «verde». As duas metades — config server-side (que não volta com
`git revert`) e a linha do doc — ficam FORA deste patch: a config não é um
path, e o doc sem a config documentaria um estado inexistente.

**O que MUDOU depois do rail r1.** O codex levantou este P1 de forma
independente, com a mesma citação de linha. Uma nota num sentinel não é cura
para um achado que o rail levanta: virou o **G7** do LAND, que LÊ a config
viva por `gh api .../branches/<branch>/protection/required_status_checks` e
classifica em quatro estados —
`covered` (os dois legs já são obrigatórios: passa em silêncio),
`unprotected` (404: a janela não se abre hoje, e o gate diz por quê),
`window` (há required checks e os legs não estão neles) e
`unreadable` (sem permissão / remote não-GitHub). Nos dois últimos o land
**para** até o Owner passar `CEO_W4A_REQUIRED_CHECK_ACK=I-ACCEPT`, com o
comando de remediação impresso. Um aviso impresso no meio de um V-block de
vários minutos é um aviso que ninguém lê; um gate que para, não.

Nota de escopo honesta: o `main` deste repo recebe push direto por cerimônia,
então a janela é a rota de PR — não a rota que este land usa.

## 9. O que as seis rodadas de rail custaram, e o que ficou

Sete achados reais no patch. Dois viraram GATES do land (o G7 da janela de
required-check; o V6c do censo de comentarios). Quatro eram imprecisoes na
prosa que a propria wave acrescentou — e as quatro sao da MESMA classe que a
wave existe para curar: um arquivo que se contradiz, ou que afirma uma causa
que a evidencia nao carrega.

A licao operacional que fica: **cada cura cria uma superficie que ninguem
revisou.** As rodadas 4 e 5 acharam defeitos DENTRO das curas das rodadas 3 e
4; a rodada 6, apontada exatamente para as linhas acrescentadas, veio limpa.
Parar na primeira rodada limpa seria ter parado na r2.
