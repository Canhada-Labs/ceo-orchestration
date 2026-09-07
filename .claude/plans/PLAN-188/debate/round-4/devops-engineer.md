---
round: 4
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer (critic — gates, CI, ceremony mechanics, generated surfaces)
generated_at: 2026-09-07T01:05:00Z
---

## Verdict

**ADJUST — 2 itens BLOQUEANTES.**

## Summary

- **Os 14 must-fix do round 3 estão absorvidos e re-verificados em disco.** M1/M2:
  `ceremony-lint.yml:75` é `continue-on-error: true`, `:77` abre `set -uo pipefail`
  (sem `-e`), `:81-82` fecha em `|| true`, `:72` diz «ADVISORY nesta fase» — a frase
  «devolve rc 1» saiu e o controle virou o par `--list` × `--list --shell-only`
  (`--shell-only` NÃO existe hoje: `grep -n shell-only` = vazio, logo é entrega, como
  o plano diz). M5/M12: as duas suítes entraram na W0a e ambas existem, são oráculo
  **0** e são coletadas (`pytest.ini:38-46` lista `.claude/scripts/tests`);
  `test_check_ceremony_script.py` tem 198 linhas, `make_repo` em `:35` e
  `test_r8_exec_bit_under_plans_is_blocking` em `:104`;
  `_workflow_paths_lists` está em `test_release_workflow_asserts.py:1095` e
  `test_ownership_paths_present_in_both_filters` em `:1167`. M4: o oráculo responde
  **1** para `.claude/adr/ADR-200-x.md` e a W3 perdeu o rótulo «docs». M6:
  `grep -c "scripts/ceremony" s345-rail-classes.txt` = **0**. M7:
  `ownership-nightly.yml` roda em `schedule`/`workflow_dispatch` sem `paths:` e faz o
  mesmo `shasum -a 256 -c` do manifesto. M14: o filtro é `is_tracked`
  (`check-ceremony-script.py:329-330`), com a razão escrita em `:326-328`.
- **O censo único reproduz por derivação.** Na árvore VIVA o `--json` devolve
  `discovered_total` 122 / `tracked` 109 / 121 sob `.claude/plans/**` / 55 arquivos com
  BLOCKING, dos quais 42 waivados e **13 não-rastreados**; R8 28/28; `floor` 41;
  `waivers_active` 44; `blocking_unwaived` **0**. Subtraindo os 13 untracked:
  109 / 108 / 42 — exatamente a tabela do §Riscos. `_KERNEL_PATHS` = **110**, manifesto
  ADR-192 = **9** membros, 33 de 48 `OWNER-*(SIGN|LAND)*.sh` citam `sentinel-signers`,
  sha256 do instrumento bate.
- **O que sobra é UMA classe, e é a minha:** *uma promessa de controle vermelho e uma
  superfície GERADA que não têm dono no file assignment da wave que as cria.*

## Riscos

### P1-1 — BLOQUEANTE — as SETE recusas nomeadas do leitor prometem controle vermelho, e o AC-1 não conta nenhuma delas

`§Approach:397-401` escreve, sobre o leitor do manifesto: «o conjunto de RECUSAS
NOMEADAS entregue pela W0, **cada uma com controle vermelho**: chave desconhecida,
chave duplicada, chave obrigatória ausente, valor multi-linha, `TAB` dentro de valor,
path absoluto em `paths`, arquivo com `CRLF`» — sete.

O AC-1, depois da cura M8, fixa o piso da W0 em **7 vermelhos** e os ENUMERA
(`:974-975`): `inv1`, `inv3a`, `inv3b`, `inv3c`, `inv4`, `inv5`, `inv10`. Nenhum é
recusa do leitor. E a W0b (`:820-823`) entrega **6 arquivos** —
`inv1_rail_set.sh`, `inv3_abs_path.sh`, `inv4_baseline.sh`, `inv5_scope.sh`,
`inv10_signer.sh`, `run.sh` — nenhum deles do leitor.

Consequência mecânica: o runner imprime `7/7` VERDE com as sete recusas do
`read_manifest.py` sem um único controle. E é justamente esse arquivo o **parser
fail-CLOSED no ponto exato onde o Owner assina** (`§Approach:135-136`, com essas
palavras). A cura M8 corrigiu a aritmética das invariantes e deixou intacta a
aritmética do leitor — a mesma classe («contagem publicada ≠ enumeração exigida»),
num sítio novo.

Agrava: `.claude/scripts/ceremony/` **não está** em `pytest.ini:38-46`, então nenhum
teste do leitor seria coletado se fosse escrito ali; e os 7 vermelhos que existem são
`.sh` sem executor enquanto a OQ-9 estiver aberta. Hoje o leitor não tem controle em
NENHUMA das duas superfícies.

**Ajuste (sem decidir OQ):** ou o AC-1 enumera os ids das recusas e a W0b ganha o
arquivo de controle correspondente (o piso deixa de ser 7), ou `§Approach:397-401`
deixa de prometer «cada uma com controle vermelho» e diz onde essas recusas são
provadas. Um dos dois textos tem de mudar.

### P1-2 — BLOQUEANTE — a W3 cria um ADR e não leva a superfície GERADA que conta ADRs

`§Items W3` (`:899-930`) fixa 6 paths: o `ADR-2xx`, `measure-rail-classes-v2.py`,
`.sha256`, `cohort-records.sha256`, `rail-classes-rebased.txt` e este plano.
`CLAUDE.md` **não está** entre eles.

Medido no HEAD: `CLAUDE.md:54` afirma «**198 ADRs**»; `ls .claude/adr/ADR-*.md | wc -l`
= **198**; `.claude/scripts/check-claude-md-claims.py:141-145` tem o check «ADR count»
com `claim_regex=r"\b(\d+)\s+ADRs\b"` e `disk_count_fn=_count_adrs` (`:81-83`), e
`python3 .claude/scripts/check-claude-md-claims.py` sai **rc 0** hoje.
`.claude/scripts/local/verify-counts.sh:196` deriva a mesma contagem
(`DERIVED_ADRS`, «exact» pelo comentário de `:35`).

Logo, no instante em que a W3 escreve o ADR, o gate de corpus fica VERMELHO e o pacote
não fecha — e `CLAUDE.md` §0 declara os arquivos do Gate 1 «cache-stable», editáveis
«only at an explicit closeout». Isto é o oposto de um risco teórico: `CLAUDE.md` §4
manda rodar os gates de corpus sobre a árvore STAGED, e é exatamente aí que ele acende.

O plano é rigoroso em nomear artefatos que o `Check:` consome (M10 acrescentou dois) e
omite a superfície que a própria wave INVALIDA. Nota adicional: a memória do repo
registra que `verify-counts` não cobre `ARCHITECTURE`/`GUIA`/`FAQ`/`npm-README`, então
um segundo grupo de sítios pode driftar em silêncio se citarem a contagem.

**Ajuste:** a W3 nomeia o sítio que reconcilia a contagem (`CLAUDE.md:54` no mínimo, e
o comando de regeneração das superfícies), ou declara que a wave fecha com o gate
vermelho e quem o reconcilia — e reconta os paths (6 → 7 no braço (a) da OQ-1).

### P2-3 — o AC-4 nomeia DUAS bases de comparação diferentes

Cabeçalho (`:1114-1116`): «contra a base congelada de 23,1 %
(`.claude/plans/PLAN-188/s345-rail-classes.txt`)».
Check, passo (2) (`:1200-1203`): «a comparação é contra
`.claude/plans/PLAN-188/rail-classes-rebased.txt` …, **nunca contra**
`s345-rail-classes.txt`, que é a base da regra ANTIGA».

É o mesmo AC dizendo o contrário de si mesmo. A cura M10 acrescentou o artefato novo e
não emendou o cabeçalho. (Na prática as duas saídas devem coincidir classe a classe
sobre o corpus da S345 — `grep -c "scripts/ceremony"` = 0 —, o que torna o defeito
textual, mas é precisamente o texto que o Owner lê para marcar o AC.)

### P2-4 — o `bash -n` do AC-1 não tem executor nomeado, e o membro `.py` do toolkit não tem NENHUM

O AC-1 exige «`bash -n` + `shellcheck` limpos» (`:955`) e a nota de custo (`:1049-1058`)
declara automática só «a metade *shellcheck limpo*», nomeando `validate.yml:341-359` —
que confirmei: `find .claude/scripts .claude/hooks -name '*.sh'`, recursivo, com a única
exclusão `.claude/scripts/owner-ceremony/archive/*` (`:354`), logo cobre o endereço novo.
Mas `grep -rn "bash -n" .github/workflows/*.yml` devolve **nada**: a outra metade não é
automática nem entra na OQ-9, que está redigida como «quem EXECUTA o **runner de
controles**» (`:1266-1268`).

Pior no `.py`: `read_manifest.py` não é `.sh` (fora do `find` do `validate.yml`) e
`.claude/scripts/ceremony/` não está em `pytest.ini:38-46` — não há sintaxe, import nem
coleta que o toque em CI. A lição da casa é literal aqui: «py_compile não prova vida
module-level — importar/coletar prova».

**Ajuste:** nomear o sítio do `bash -n` (ou declarar que o `shellcheck` do
`validate.yml` o subsume, com a razão escrita) e nomear a superfície que compila/importa
o `read_manifest.py` — sem isso o único julgamento do leitor em CI é o `ceremony-lint`,
que mede R1-R4/R8 por regex de TEXTO, nunca se o arquivo sequer parseia.

### P2-5 — a R8 alargada torna o exec-bit acidental um erro que só a cerimônia repara

Verificado: `check-ceremony-script.py:192-194` escopa a R8 a `.claude/plans/` com a razão
que o plano cita, e a decisão (c) a alarga ao toolkit root. Verificado também que a única
rota de escape do lint é o waiver por sha256 de CONTEÚDO — e o AC-6 põe
`ceremony-lint-waivers.json` no manifesto ADR-192, isto é, todo append passa a exigir
bump ASSINADO (o próprio AC-6 escreve o custo, `:1281-1289`).

O que não está escrito é a interação com `CLAUDE.md` §4: «o exec-bit volta no primeiro
`git add -A` se for largado só do índice». A partir do AC-6, um exec-bit reintroduzido
por acidente numa wave livre do toolkit é BLOCKING sem rota barata: a correção do modo é
trivial, mas se o pacote já tiver sido waivado, o re-armamento por conteúdo exige novo
waiver ⇒ novo bump assinado. O plano nomeia o mecanismo (`§Approach:236-238`) e não
nomeia esse custo de recuperação.

### P3-6 — o controle de EVENTO prova o PREDICADO, e o AC-6 (ii) depende de DUAS entregas em waves diferentes

Sem achado novo, só precisão de leitura: o instrumento de `test_release_workflow_asserts.py`
casa globs por `fnmatch` — o próprio plano escreve o limite («prova o PREDICADO de
gatilho, não a fiação do motor de eventos», `:1004-1007`), e concordo que é a régua certa.
Mas o vermelho (ii) do AC-6 exige as duas metades — gatilho (W0) **e** membresia
(W1) — e o parágrafo `:1272-1280` diz «é ELE que liga o append de waiver ao `shasum -c`»
sem repetir a metade da membresia que o próprio M7 escreveu 700 linhas antes. Verificado
que o step só confere MEMBROS: `smoke-install.yml:355-360` é `shasum -a 256 -c "$M"`.
Uma linha de reforço no AC-6 evita que um leitor marque o AC com metade da máquina.

## O que falta antes de executar (OQ que o Owner ratifica — não decididas aqui)

1. **OQ-7** e **OQ-9** seguem pré-condições da W0, como o plano escreve; nada neste round
   as move. A OQ-9 continua a valer para o runner e para o quarto sítio.
2. **OQ-1, OQ-2, OQ-4, OQ-5, OQ-6, OQ-8** abertas por desenho.
3. Nenhuma OQ nova. Os dois bloqueantes acima são de TEXTO e de FILE ASSIGNMENT — não
   pedem decisão do Owner, pedem cura na próxima revisão.

## Contagem

- **BLOQUEANTES: 2** (P1-1, P1-2).
- ADJUST, não REJECT: a arquitetura das dez invariantes, o corte de waves e as decisões
  (a)–(c) do §Approach continuam de pé, e todos os 14 must-fix do round 3 reproduzem em
  disco.
