---
plan: PLAN-183
round: 1
archetype: DevOps & Platform Engineer
created_at: 2026-08-20
source: workflow wf_6568bd64-6d7 (fan-out read-only; artefato gravado pelo CEO)
attribution: retorno estruturado do workflow, validado por marcadores de conteudo
---

## 1. Verdict

**ADJUST** — os três defeitos (A1/A2/A3) são reais e **todas as âncoras que o plano cita batem no disco**; mas a causa-raiz declarada é falsa, o plano é mudo sobre instalações que já existem (o maior buraco), e o censo "4 de 14" é observação de campo tratada como censo.

## 2. Summary

O plano toma um relatório de campo de um adopter real e o converte em quatro waves: ponteiro `PROTOCOL.md` portátil (W1), template de CI que passa fora do framework (W2), resíduo de catálogo (W3), e timeout de hook gated por reprodução (W0/W4). Pela minha lente — install/upgrade, templates, o caminho do adopter, rollback — o plano acerta *o que* está quebrado e erra *por que*. Ele diz que o framework "nunca foi exercitado como adopter"; na verdade ele é exercitado por PR e por nightly, com instalações reais. O que nunca foi exercitado é **`.github/`**. Essa correção é o que muda o plano de um patch pontual para uma cura estrutural — e ao mesmo tempo revela que a cura do W1, como especificada, **não alcança nenhum adopter existente**.

## 3. Risks

**R1 — A cura do A1 é imortalmente inalcançável para quem já instalou.** `scripts/upgrade.sh:1676-1692` classifica o ponteiro comparando `_hash_file(pointer)` contra `_REFRESH_PROTOCOL_CANON_HASH` = hash do que o gerador **atual** escreveria. Mudar o corpo renderizado muda esse hash. Mecanismo: para todo install existente, o arquivo em disco (forma absoluta antiga) deixa de casar com o novo canônico → cai em `_lc="edited"` → `_ownership_verdict` devolve `PRESERVE_OWNED` → `upgrade.sh:1721` imprime *"PRESERVED … pointer NOT refreshed"*. **O adopter que reportou o bug continua com o caminho absoluto para sempre.** Esta é exatamente a rota de "defeito imortal" que o PLAN-168 W2 construiu `_protocol_pointer_is_degraded` (`_framework_manifest_set.sh:736-742`) para escapar.

**R2 — Os templates são fósseis; consertar 4 steps não para a putrefação.** `.github/workflows/validate.yml` vivo: 79.993 bytes, **71 steps**, 9 jobs, `runs-on: Ceo`, `timeout-minutes: 25`, `actions/checkout` SHA-pinado (`de0fac2e…`). `templates/.github/workflows/validate.yml.template`: 226 linhas, **14 steps**, `ubuntu-latest`, `timeout-minutes: 5`, `actions/checkout@v4` sem pin. Nada regenera um do outro, nada diffa os dois. O W2 patcheia 4 steps num arquivo que volta a apodrecer na próxima edição do workflow vivo.

**R3 — O `Contamination check` falha por motivo diferente do que o plano diz, então a cura proposta não cura.** `check_contamination.py:70-73`: `_PATTERN = acme\s*[Ll]edger|example[\s._\-]*owner|Example\s+Owner|[Jj]oao[\s._\-]*[Cc]anhada|Jo[aã]o`. Entregamos a todo adopter um lint que caça **o nome pessoal do mantenedor do framework**, incluindo o token nu `Jo[aã]o`. Mecanismo: um adopter brasileiro (o perfil mais provável dos primeiros adopters) com um "João" em CHANGELOG, AUTHORS, doc que cita commit, ou fixture de teste → CI vermelha inacionável, isenta só por uma allowlist hardcoded de 89 caminhos do framework (`MORNING-REPORT-S214.md`, `docs/opus-4-7-baseline.md`, …). O próprio docstring em `:63` diz *"a maintainer publishing their own fork should replace these with their personal handle"* — e o `install.sh` **não faz substituição nenhuma**. Trocar allowlist não resolve um padrão que caça a identidade errada. Detalhe adicional: `_ALLOWLIST_EXACT` isenta `.github/workflows/validate.yml`, mas o arquivo do adopter chama-se `validate.yml.template` — a isenção nem viaja.

**R4 — W1 quebra a bateria de ownership e o orçamento não cobre.** `scripts/tests/ownership_table.tsv` se declara "THIS FILE IS THE TRUTH" (linha 1), 72 linhas / 65 casos e2e, ~25 min por rodada; `ownership-nightly-gate.sh` falha em **qualquer** diferença contra `ownership-expected-reds.txt` — *inclusive encolhimento* (*"an all-green run means the truth table changed, which is a reason to STOP"*). Mudar o corpo do ponteiro toca `test-protocol-pointer-inv4.sh`, `test-protocol-pointer-render.sh`, `ownership-baseline-map.txt` e plausivelmente o conjunto de reds. W1 orçado em 30-60k tokens não tem folga para um ciclo de re-baseline de 25 min por iteração.

**R5 — Fan-out de instrumento.** W0-US3 ("repo descartável") cria um segundo oráculo do caminho de adopter ao lado de `smoke-install.sh` + `test-ownership-table.sh`. Reabre a classe que os PLAN-167/168 gastaram dois planos fechando: dois oráculos que podem discordar sobre o mesmo fato.

## 4. Must-fix

**MF-1 — Corrigir a causa-raiz (§1, §5 do plano e AC-5).** A afirmação *"nunca exercitado como adopter"* é falsa. `scripts/tests/smoke-install.sh` roda install real em scratch dir e afirma ~20 invariantes de adopter (bits de execução `:137`, ausência de `tests/` `:83`, zero placeholders não-renderizados `:132`); `test-ownership-table.sh` (37 KB) faz ~25 min de installs reais em 65 casos sob `ownership-nightly.yml`; existem ainda `test-install-upgrade-parity-e2e.sh`, `test_install_baseline_manifest.sh`, `test-protocol-pointer-inv4.sh`. Rodei `grep -rln "validate.yml.template\|benchmarks.yml.template"` sobre `scripts/tests/`, `.github/workflows/` e `.claude/scripts/tests/`: **zero ocorrências**. A causa-raiz verificável é: *o instrumento de adopter existe e é forte, mas seu ESCOPO exclui `.github/` — os dois templates de workflow são os únicos artefatos entregues sem teste e sem referência de CI em lugar nenhum.* Reescrever §1/AC-5 assim, e **W0-US3 estende `smoke-install.sh`**, não cria instrumento paralelo.

**MF-2 — W1 ganha bullet [P0] de MIGRAÇÃO + AC próprio.** Adicionar um reconhecedor `_protocol_pointer_is_legacy_absolute` no mesmo molde de `_protocol_pointer_is_degraded` (`_framework_manifest_set.sh:736-742`): re-renderizar a forma absoluta antiga com os valores específicos da invocação extraídos do próprio arquivo, exigir identidade byte-a-byte, falhar **para preservação**. Sem isso a cura só alcança installs novos (R1). AC: *"um install feito com a versão anterior, ao rodar `upgrade.sh`, sai com ponteiro relativo — provado em e2e."*

**MF-3 — Preservação silenciosa vira preservação AVISADA.** O corpo degradado instrui o adopter a editar (`_render_protocol_pointer_degraded`: *"Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout"*). Quem seguiu a instrução fica `edited` → `PRESERVE_OWNED` → nunca curado, e isso está **correto**. Mas o `upgrade.sh` deve então emitir WARNING quando um ponteiro preservado contém caminho absoluto. O bullet P1 atual do W1 trata preservação só como requisito e não vê que ela também é o modo de falha.

**MF-4 — Trocar `CEO_ORCHESTRATION_DIR` por `CEO_PROTOCOL_SOURCE`.** Plano `:140` inventa um nome. `grep -rn "CEO_ORCHESTRATION_DIR"` sobre `scripts/`, `.claude/`, `docs/` devolve **um único hit: o próprio plano**. O knob real e entregue é `CEO_PROTOCOL_SOURCE` (`install.sh:409`) + `--protocol-source` (`install.sh:522`), já persistido no install-state e relido por `upgrade.sh:1600-1616` para continuidade entre upgrades. Um segundo env var forka essa cadeia.

**MF-5 — Re-derivar o censo do W2 do template, step a step, com o mecanismo nomeado.** "4 de 14" é o que um adopter, num perfil, num runner, mediu. Pelo menos mais quatro steps têm modo de falha condicional a adopter:
- `:172 actionlint` — roda `./actionlint "$GITHUB_WORKSPACE/.github/workflows/"*.yml`, ou seja, **linta os workflows do próprio adopter**, que o framework não possui. Qualquer workflow pré-existente com warning → vermelho imposto por nós. O mesmo step faz `bash <(curl -sSL https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)`: execução de código remoto **sem pin**, buscado de `main`, embarcado num template entregue a terceiros — enquanto o workflow vivo SHA-pina `actions/checkout`. Postura de segurança inconsistente entre o que rodamos e o que entregamos.
- `:98 Validate settings.json…` — `python3 -c 'import yaml'`. PyYAML é terceiro; `CLAUDE.md` §3 afirma *"stdlib-only (zero third-party runtime deps)"*. Só funciona porque `ubuntu-latest` pré-instala. Quebra em container slim / runner self-hosted. Dependência de host não declarada num template entregue.
- `:118 Shellcheck` — `sudo apt-get install -y shellcheck`: exige sudo+apt. E shellcheca os scripts **do framework** instalados: warning ali é vermelho que o adopter não pode consertar.
- `:77 Placeholder lint` — lista ALLOWED hardcoded, e o texto de remediação manda *"add it to the ALLOWED list in `.github/workflows/validate.yml`"* — arquivo que o adopter não tem (ele recebeu `validate.yml.template`).

**MF-6 — W2 precisa de um VÍNCULO template↔vivo, não de 4 patches.** Ou um gate de drift (steps do template ⊆ steps do vivo, com allowlist explícita de divergência), ou uma declaração escrita de que o template é um subconjunto mínimo congelado — com o teste que o executa. Sem isso o W2 é patch único num arquivo sem dono (R2).

**MF-7 — Responder a Open Question 3 do W3 com o que já está verificado, e fechá-la.** Não é `install.sh`, nem hook, nem lint de skills. A demoção é escrita por `.claude/scripts/skill-budget-generator.py:362` (`overrides[key] = "name-only"`), que por docstring própria (`:481`) *"demotes 0-dispatch domain-tier skills"*. Grepei esse arquivo por `veto|VETO|risk_class|critical`: **zero ocorrências**. O gerador é comprovadamente cego a status de veto — ranqueia por contagem de dispatch, e skill de veto é 0-dispatch **por construção** (dispara em revisão, não em roteamento). A invariante mora no gerador, como conjunto de exclusão que ele não pode demover, mais asserção nos testes dele. As duas skills do campo existem aqui: `.claude/skills/domains/fintech/skills/financial-correctness-and-math/` e `.../financial-display/`.

**MF-8 — Re-estimar W1 e nomear os artefatos tocados.** Listar quais dos cinco (`ownership_table.tsv`, `ownership-baseline-map.txt`, `ownership-expected-reds.txt`, `test-protocol-pointer-inv4.sh`, `test-protocol-pointer-render.sh`) o W1 espera mexer, e orçar o ciclo de re-baseline em tokens+sessões (R4).

## 5. Nice-to-have

- W2: alinhar `actions/checkout@v4` do template ao SHA-pin do vivo — entregar prática pior do que a que praticamos é gratuito de corrigir.
- Registrar em `docs/` a política de templates: quem é dono, com que frequência é reconciliado, e qual teste o cobre.
- `benchmarks.yml.template` ganhar cabeçalho dizendo que consome `ANTHROPIC_API_KEY` e gasta dinheiro do adopter.
- W0-US1: nomear no plano as fontes candidatas do `/doctor` a checar (config do harness, `~/.claude/`, telemetria local), para a W0 ter critério de parada em vez de busca aberta.

## 6. Unseen

**U1 — O CI entregue é INERTE até o adopter renomear, e ninguém diz isso.** `install.sh:1518-1522` copia preservando o sufixo: `.github/workflows/validate.yml.template`. O GitHub Actions só lê `.yml`/`.yaml` — um arquivo `.template` não executa. Consequências em três direções: (a) baixa a severidade de A2/A3 (ninguém toma vermelho de surpresa sem um ato explícito); (b) **AC-2 ("verde num adopter limpo, provado em PR real") exige um passo de ativação que o plano nunca nomeia**; (c) ninguém escreveu se "CI opt-in por rename" é design ou acidente. Decidir e documentar é mais barato que os quatro patches.

**U2 — O template não tem kill-switch; o vivo tem 16.** `grep -c CEO_SOTA_DISABLE`: **16** em `.github/workflows/validate.yml` (o `if: vars.CEO_SOTA_DISABLE != '1'` em nível de job, `:26`), **0** no template. O adopter recebe o nosso CI sem interruptor. Se o W2 optar por guardas em vez de remoção, essa variável já é o mecanismo estabelecido — e é a diferença entre "o adopter desliga nosso CI num clique de repo-variable" e "o adopter edita YAML que é nosso".

**U3 — `timeout-minutes: 5` é um footgun que este repo já pagou.** Template 5 min vs vivo 25 min, num job que faz `apt-get install shellcheck` + download do actionlint + dois `unittest discover`. A lição já está na memória do projeto: timeout de job aparece como "cancelled" no step **inocente**. Se o W2 mantiver os dois steps de teste atrás de guarda e o adopter escrever testes próprios, ele herda o teto de 5 min. W2 deve fixar o timeout do template deliberadamente e dizer por quê.

**U4 — Não há rota de rollback declarada.** Toda outra superfície do framework tem uma (`CEO_SOTA_DISABLE=1`, `CEO_SENTINEL_UNLOCK`, `--dry-run`, `BAK_DIR`). A cura do A1 reescreve um arquivo na raiz do repo do adopter durante upgrade. O `upgrade.sh:1748` de fato faz backup em `$BAK_DIR/PROTOCOL.md` antes do REFRESH — mas o plano não enuncia a rota e o W1 não tem AC de "adopter recupera o ponteiro anterior".

**U5 — AC-6 é a única AC com dependência externa e não tem canal nem dono.** `external_wait: "nenhum"` no front-matter, mas AC-6 ("achados respondidos ao adopter, inclusive os recusados") é por definição um round-trip externo. Ou nomeia canal e responsável, ou sai do conjunto de ACs e vira item de closeout.

**U6 — `.claude/scripts/local/` também não é instalado** (o glob de `install_scripts_selective` é top-level: `*.sh`, `*.py`, `*.yaml`). O template atual não chama nada de `local/`, mas o workflow vivo chama (`.claude/scripts/local/check-doc-skill-paths.sh`). Se o W2 "aproximar o template do vivo" sem esse cuidado, cria uma segunda referência pendurada da mesma classe do A3.

## 7. What I would NOT change

- **§4 inteira — o tratamento do A5.** Declarar "NÃO REPRODUZI", nomear o que falta (a fonte que o `/doctor` lê) e gatear o W4 atrás do W0 é exatamente certo, e é o oposto do defeito que gerou este plano. Além disso a consequência secundária foi verificada de forma independente e **vale sozinha**: o audit-log não registra timeout de hook, então o framework é cego às próprias paredes falharem em aberto. Manter W0-US2 mesmo que W0-US1 refute o número 71.
- **A6 recusado com razão, e a razão confere.** `templates/.github/CODEOWNERS.template:14` usa `@{{OWNER_HANDLE}}`; o vivo tem `@Canhada-Labs/maintainers` (a exceção documentada no `CLAUDE.md` §4). Registrar a recusa é o que mantém um relatório de campo utilizável — não silenciar o item errado.
- **§3, os não-objetivos explícitos** (não re-litigar PLAN-175/PLAN-182). Disciplina de escopo é o que faz um plano de 2-4 sessões pousar.
- **A insistência do W1 de que o teste de portabilidade entra na bateria EXISTENTE, não numa paralela.** É o instinto certo — e é exatamente a regra que o W0-US3 viola (MF-1). Proteger a regra e corrigir a violação, não o contrário.

---

*Nota de fronteira de instruções: nenhum arquivo lido tentou redirecionar a tarefa. Trabalhei estritamente read-only; nada foi escrito, editado ou movido.*