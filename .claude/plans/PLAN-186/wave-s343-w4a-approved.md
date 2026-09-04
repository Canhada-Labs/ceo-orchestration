# wave-s343-w4a — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo
> `OWNER-S343-W4A-SIGN.sh` no momento da assinatura; o
> `OWNER-S343-W4A-LAND.sh` aborta no G1 se não casar. Reescrever um byte
> deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-186
Wave: wave-s343-w4a (PLAN-186 W4a — a DELEÇÃO dos dois steps duplicados do job `validate`, mais o bump diferido do `timeout-minutes` do Smoke Install pegando carona. O braço de COBERTURA do AC-16 foi re-derivado sobre este HEAD e a deleção NÃO é recusada por cobertura; o braço de EXECUÇÃO são TRÊS corridas serializadas no `push` do `main`, das quais o próprio LAND é a primeira. Nenhum trabalho de `fail-fast`/matriz/composite entra aqui — isso é a W4b.)
Patch: .claude/plans/PLAN-186/s343-ceremony-w4a/W4A.patch
Patch-sha256: 35e26cdc47e606d12eca45a267d6c147a3ed8f381693a25782f3f823066f6db3
Patch-base: 76578f33eaa25a373643a96d7df908ebd3082408
Anchor-SHA: 93efbb17d7b8c1ef0dfb13ea861fcbc0e32e26b2
Data: 2026-09-04

## O que esta wave entrega

**Dois arquivos, os DOIS canônicos** — e nada além deles. Ambos DERIVADOS de
um único material versionado, `s343-ceremony-w4a/apply-w4a-validate-deletion.py`
(11 edições com âncora exata e contagem declarada; o LAND prova
`HEAD + script == patch` byte a byte no V3).

1. **`.github/workflows/validate.yml`** (canônico, **KERNEL** —
   `_KERNEL_PATHS` de `check_arbitration_kernel.py`): saem os dois steps mais
   caros do job `validate`, porque o job `hook-tests-python-matrix` já roda a
   **união exata** deles, no MESMO evento `push`, em 3.9 e 3.12:
   - E2 `- name: Run Python hook unit tests (CEO_HOOK_ADAPTER=claude default)`
   - E3 `- name: Run Python script unit tests` (com o banner DELE; a régua
     `# ---` de cima sobrevive e abre o banner do step seguinte)
   - E1 + **E6..E11**: os SETE comentários que apontavam para os steps
     deletados («step below», o banner do step de hooks, «dir-collected
     above», «split above» e as duas ocorrências de «directory pins in the
     pytest steps above») passam a nomear o `hook-tests-python-matrix`. Um
     arquivo que se contradiz é a classe
     `feedback-reconcile-the-conclusions-not-just-the-table`; a primeira
     redação curou UM sítio e o rail codex r2 achou a CLASSE — o censo
     mecânico dos 6 restantes está no **V6c** do LAND, nas DUAS pernas
     (ausência dos literais velhos E presença do nome do job novo, porque um
     censo só de ausência passaria com os comentários APAGADOS).
   - E4 o `env:` da matriz ganha a DECLARAÇÃO da perda aceita de
     `CEO_HOOK_ADAPTER`, escrita onde o próximo leitor procura.

2. **`.github/workflows/smoke-install.yml`** (canônico, **não**-kernel):
   E5 `timeout-minutes: 126 -> 150`, com a derivação REESCRITA. O bloco de
   história aditiva NÃO é tocado (ele é o ledger de como se chegou a 126); um
   bloco novo registra as **sete amostras medidas** de wall do JOB `smoke`
   (73m18s … 92m32s) e diz o que a aritmética não dizia: qual é a FAIXA
   observada. O bloco **não atribui causa** — os sete runs compartilham a
   definição do workflow mas não a carga executada, e separar runner de
   carga exigiria execuções repetidas no MESMO sha (achado P3 do rail r4).
   O dimensionamento é sobre o MÁXIMO observado.

## Kernel

`.github/workflows/validate.yml` ∈ `_KERNEL_PATHS`. O LAND arma
`CEO_KERNEL_OVERRIDE` ele mesmo, no menor escopo (export antes do apply,
unset após o commit, backstop no trap), com o par reason-SLUG + `I-ACCEPT`
validado VIVO contra o contrato do hook — mecanismo idêntico ao `wave-fable51`
(`ab56e76`), ao 179close (`bc82651`) e ao adrgate (`cfab980`).

## O delta de ambiente é DUPLO, e os dois lados são perdas ACEITAS

| Variável | Steps deletados | Matriz (o único consumidor a partir daqui) | Tratamento |
|---|---|---|---|
| `CEO_HOOK_ADAPTER: claude` | presente **só no step A** | **ausente** | **NÃO adicionada.** A matriz roda hooks + scripts + optimizer num ÚNICO pytest; setá-la ali ALTERARIA o ambiente de scripts/optimizer, que rodavam com ela ausente tanto no step B quanto na matriz. A variável é o default documentado do adapter, então a ausência exercita o MESMO caminho que o step A exercitava explicitamente. Perda ACEITA, declarada em E4 no próprio arquivo. |
| `PYTHONPATH: "."` | **ausente nos dois** | presente | **Não recuperável sem custo.** Hoje a suíte roda com e sem; depois, só com. Recuperar exigiria uma dimensão de matriz que DOBRA o custo do job pago. Perda ACEITA. |

## A cobertura, RE-DERIVADA sobre este HEAD (não citada da S341)

`pytest --collect-only -q` por raiz, sobre a árvore em HEAD, nos três
recortes que a CI executa:

| Recorte | \|A\| (hooks) | \|B\| (scripts+optimizer) | A ∩ B | A ∪ B | Matriz | Igualdade |
|---|---|---|---|---|---|---|
| todos | 7 476 | 6 136 | **0** | **13 612** | **13 612** | `sha(U) == sha(M)` |
| `-m 'not serial'` | 6 982 | 5 684 | **0** | **12 666** | **12 666** | `sha(U) == sha(M)` |
| `-m 'serial'` | 494 | 452 | **0** | **946** | **946** | `sha(U) == sha(M)` |

A comparação é por CONJUNTO de node-ids (sha256 da lista ordenada), nunca por
contagem: dois conjuntos diferentes podem ter o mesmo tamanho. Os números da
S341 (7 474 / 6 063 / 13 537, serial 924) descreviam uma árvore mais antiga —
a suíte cresceu e a PROPRIEDADE continua valendo. **A deleção não é recusada
por cobertura.** (Re-derivada DE NOVO no LAND real de 2026-09-04, sobre `449f157`, depois que
os materiais congelados em `44c16f4` envelheceram: a sombra em `76578f3` dizia
6 122 / 13 598 e os +14 node-ids são o teste do AC-14, `b53fec1`, 0 seriais —
`s343-ceremony-w4a/EVIDENCE.md` §3-b.)

## O que esta wave NÃO faz

- Nenhum `fail-fast: false` novo, nenhuma matriz nova, nenhum composite
  action, nenhum split do job `validate` em três — isso é a **W4b**, e a
  justificativa dela é ATRIBUIÇÃO DE FALHA, não velocidade (K21).
- Nenhuma previsão de wall-clock. `AGENTS.md:9-11` proíbe claim de speedup; o
  `OWNER-S343-W4A-MEASURE.sh` entrega a SUBTRAÇÃO bruta medida em 3 corridas
  contra os 3 baselines REGISTRADOS por id, e nada mais.
- Nenhum aperto do `timeout-minutes: 25` do job `validate`. Sobre-dimensionar
  não custa nada num run verde; apertar é decisão própria, com p95 real.

## Residuais declarados

- **A MEDIÇÃO acontece DEPOIS do land**, e é o que fecha o AC-16: o push do
  LAND é a corrida **1/3**; o `OWNER-S343-W4A-MEASURE.sh` empurra as outras
  duas, SERIALIZADAS (o `cancel-in-progress` por ref cancela runs
  consecutivos), e escreve `PLAN-186/w4/validate-deletion-RESULT.md`. Enquanto
  esse arquivo não existir, o AC-16 continua ◐.
- `CLAUDE.md:113` cita «margem 38 min no timeout 126» como narração da S337.
  Depois deste land a frase descreve um estado passado. Não é tocada aqui:
  `CLAUDE.md` só muda em closeout, e a afirmação continua verdadeira COMO
  HISTÓRIA. O Owner decide se reescreve no closeout da S343.
- O censo derivado dos dois nomes de step (`grep -rn` sobre a árvore) devolve
  **zero** consumidores VIVOS fora de plans/debate/transcripts (que são
  ledger) e de `.claude/plans/PLAN-169/staged-s318/validate.yml`, que é um
  artefato CONGELADO de evidência. O template do adopter
  (`templates/.github/workflows/validate.yml.template`) já perdeu os dois
  steps em `4f750f0` (PLAN-183 W2) — nada a propagar.
- O sentinel do PLAN-161 (julho) AINDA concede `.github/workflows/*`
  ([[project-deferred-smoke-timeout-and-stale-sentinel]] §2). Este pacote não
  depende dele — traz o próprio — mas o achado segue aberto.
- **O RESIDUAL QUE EXIGE DECISÃO DO OWNER, e que esta wave deliberadamente
  NÃO resolve** (achado r24 P1 do relatório da S340, RE-VERIFICADO hoje em
  `docs/BRANCH-PROTECTION.md:101-105`): o ÚNICO status check obrigatório é
  `validate / Governance, health, contamination, shellcheck`. Depois desta
  deleção esse check não roda mais as suítes de hooks/scripts — quem as roda é
  `hook-tests-python-matrix (3.9)` e `(3.12)`, que **não** são checks
  obrigatórios. Numa PR, uma matriz VERMELHA passaria a coexistir com um
  Validate «verde» e o merge passaria. Duas metades: a config é SERVER-SIDE
  (não volta com `git revert`) e a linha do doc é um arquivo. **Não entram
  neste patch** porque a config não é um path e o doc sem a config seria
  documentação de um estado que não existe. **Mas também não é só uma nota:**
  o rail codex r1 levantou exatamente este P1, e a cura foi um GATE — o
  **G7** do LAND lê a config VIVA (`gh api .../protection/required_status_checks`)
  e, se os dois legs da matriz não estiverem entre os obrigatórios, PARA o
  land até o Owner escolher: fechar a janela agora (config + doc, na mesma
  janela) ou aceitá-la com `CEO_W4A_REQUIRED_CHECK_ACK=I-ACCEPT`. Protection
  ausente (404) é reportado como «a janela não se abre hoje»; API ilegível
  exige o mesmo reconhecimento — nunca um passe silencioso. O
  `OWNER-S343-W4A-MEASURE.sh` repete a decisão como item do checklist do AC-16.
  Nota de escopo: o `main` deste repo recebe push direto por cerimônia, então
  a janela é a rota de PR, não a rota que este land usa.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Plans: PLAN-186
Scope:
  - .github/workflows/smoke-install.yml
  - .github/workflows/validate.yml
<!-- END SIGNED SCOPE -->
