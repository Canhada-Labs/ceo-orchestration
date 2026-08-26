---
adr_id: ADR-194
title: A rota de entrega é DADO compartilhado — um resolvedor destino→(fonte, transformação) para os três consumidores, e as duas árvores entram na decisão de propriedade
status: ACCEPTED
date: 2026-08-24
accepted: 2026-08-25 (assinatura GPG do Owner sobre wave-w5-approved.md — land 6304f66 — e decisão verbatim S328 «Pista MISTA — braço C (Recomendado)»)
plan: PLAN-183 (W5; D1/D3/OQ-5; OQ-4 medida em S327)
proposed_by: CEO (S327 night-run)
decided_by: Owner — a assinatura GPG de `.claude/plans/PLAN-183/wave-w5-approved.md` É a ratificação (ocorrida em 2026-08-25; o flip textual para ACCEPTED chega ao main pela cerimônia, pacote S328-A, não pelo land 6304f66)
risk_tier: A
debate_required: true
related_plans: [PLAN-183, PLAN-167, PLAN-168, PLAN-182]
related_adrs: [ADR-155, ADR-155-AMEND-1, ADR-190, ADR-192]
---

# ADR-194 — A rota de entrega é DADO compartilhado, não um ramo em cada script

**Status:** ACCEPTED — ratificado pela assinatura GPG do Owner sobre
`PLAN-183/wave-w5-approved.md` (assinatura criada 2026-08-25 11:53:12Z; land `6304f66`,
2026-08-25 09:08:28 -0300) e pela decisão verbatim de 2026-08-25 (S328): «Pista MISTA — braço C
(Recomendado)». **Enforcement commits:** `6304f66` (D3 + D1 + emenda OQ-5) e `738007e` (deepen
do histórico antes da paridade).

## Context

**D1 (produto).** `scripts/upgrade.sh` nunca entregou `docs/` nem `.github/`. Medido na árvore
viva: `grep -c 'github' scripts/upgrade.sh` = **0**; `grep -c 'docs'` = **3**, as três
COMENTÁRIO (`:1623`, `:3104`, `:3206`). O install entrega as duas por `install_docs_templates`
(`install.sh:1476`) e `install_github_templates` (`:1488`), ambas atrás de `CEREMONY != user`
(guardas `:1484` e `:1525`) — daí a assinatura `maintainer:1 user:0` da paridade.

**D3 (produção).** `_framework_manifest_set.sh:430-437` resolve `$_wbm_hash_root/$_wbm_rel`
**sem fallback**: `docs/BRANCH-PROTECTION.md` casa o homônimo da RAIZ (bytes errados) e
`.github/*.template` cai no `continue` — some do baseline **em silêncio**. Mas D3 é **latente
por NÃO-ENTRADA**, não vivo: `_framework_target_entries()` (`:113`) nunca enumera as duas
árvores — medido, a única linha do arquivo que as menciona é o comentário de contrato em `:492`,
e `grep -c 'delivery-routes'` ali = **0**. As 6 rotas nunca chegam ao resolvedor ⇒ **curar só a
resolução é byte-idêntico ao baseline**; a enumeração alarga junto.

**A FORMA.** Não existe UM resolvedor de fonte, existem três:
`scripts/tests/_parity_classify.py:335` (`_src_digest`), `scripts/doctor.sh:418`
(`_route_source`, curado na S325) e o gerador canônico — este ainda reconstruindo o path
localmente. Estender o domínio de entrada antes de curar a forma converte ~25 sítios latentes em
vivos de uma vez (razão medida 1 : 25). Precedente do próprio repo: PLAN-167/168 colapsou
propriedade em `_ownership_verdict()` (`:494`, pura de **nove** dimensões — `:495` são 9
posicionais; "10 dimensões" no `CLAUDE.md` §4 é folclore) e PLAN-182 colapsou 16 re-derivações
de slug; o §4 avisa que ramo local reabre a classe.

## Options considered

**(A) Manter a resolução por script, corrigindo cada ramo local.** É o que já se tentou: os três
consumidores existem porque cada correção parou no sítio, e erram diferente — ordem errada
(identity antes), hash do arquivo errado, cópia com a fonte errada (vazamento REPRODUZIDO na
S325). **Rejeitada:** reabre a classe que PLAN-167/168 e PLAN-182 fecharam, justo quando o
domínio de entrada dobra.

**(B) UMA tabela de rotas lida por todos os consumidores — ESCOLHIDA.** Dado compartilhado entre
bash e Python (a forma de `ownership_table.tsv`).

**(C) Guardar a rota dentro de `ownership_table.tsv`.** **Rejeitada — são perguntas diferentes
(§8.5.2).** `HASH_SOURCE` é enum de **ORIGEM**
(`HASH_SOURCE`/`HASH_PRIOR_RECORD`/`HASH_CANONICAL_POINTER`/`HASH_TARGET`, `:398-410`) e seu
próprio ramo faz `_hash_file "$FMS_SOURCE_ROOT/$_wbm_rel"` — relpath de DESTINO sob a raiz de
fonte, isto é, **já assume identidade**. O manifesto persiste só digest + relpath de destino,
então `doctor.sh` não tem de onde RECUPERAR a fonte, e `CODEOWNERS.template → CODEOWNERS` **mais
renderização** é inexprimível ali.

## Decision

### §1 A tabela é a verdade, e tem TRÊS leitores
`scripts/delivery-routes.tsv` (6 rotas; colunas `dest src transform flag_dep
origin note`) é a ÚNICA fonte de `destino → (fonte, transformação)`. Leitores:
`_parity_classify.py` e `doctor.sh` (convertidos na S325) e agora
`scripts/_framework_manifest_set.sh` — **o terceiro e último**, e o único canônico;
segunda cópia é o ramo local proibido. Idiom copiado de `doctor.sh:418-449`; piso
bash 3.2 ⇒ varredura linear, sem `declare -A`.

| rc | significado | efeito |
|---|---|---|
| 0 | rota `identity` com fonte | resolve `$root/<fonte>` |
| 1 | sem linha para o destino | comportamento de HOJE (`$root/$rel`), inalterado |
| 2 | RENDERIZADA ou linha malformada | **não registra**, e NOMEIA o path |

O rc=2 é a decisão que importa: o *skip* está certo (bytes renderizados não existem em checkout
nenhum), a **omissão silenciosa** é o defeito. E `${transform:-}` fica
**unbraced-default-VAZIO** — `${transform:-identity}` foi o achado fail-OPEN do rail (S325) que
reabriu vazamento de contaminação real.

**Um acessador, não um por campo (emenda S327, rail r5-F4).** `_wbm_route_meta <destino>` imprime
`<fonte><TAB><transformação>` de uma linha JÁ validada; `_wbm_route_src` é a projeção *identity*
dela. Um segundo call-site que precise do `transform` chama o acessador — o ramo do
`.github/CODEOWNERS` renderizado em `upgrade.sh` puxava os dois campos com `awk` próprio sobre o
TSV, o **quarto** parser que as Consequences vetam pelo nome, e que não herdava validador nenhum
nem a cura de linha final sem newline (r4-F4). Anti-rot: `S.12` de
`test-manifest-delivery-route.sh` reprova se `awk` sobre a tabela reaparecer em
`upgrade.sh`/`install.sh`/`doctor.sh`.

**A tabela diz COMO rotear; o CÓDIGO diz ONDE a entrega pode escrever (emenda S327, rail r5-F1).**
`_wbm_route_dest_declared` (r3) é uma whitelist que lê a MESMA tabela que deveria restringir — uma
tabela hostil bem-formada declara os próprios destinos e a whitelist concorda. Medido (S327): a
linha `.git/hooks/pre-commit ← scripts/install.sh` (`identity`) passa TODO portão léxico, mantém
`routes == rows`, é copiada no destino ausente, registrada no manifesto, e o upgrade sai 0. O
**DOMÍNIO de entrega** é constante de CÓDIGO, inalcançável por qualquer input: destinos sob
`docs/` ou `.github/` — as duas árvores que esta wave entrega, por desenho (§4) — e fontes sob
`templates/`. Ele é checado no ÚNICO choke point (`_wbm_route_row_ok`), logo os três leitores o
herdam: a linha cai fora de `_wbm_route_dests`, `routes < rows` fica verdadeiro e a pré-condição
AC-9 recusa a entrega INTEIRA com `exit 3`. **Alargar o domínio é emenda DESTE ADR, nunca edição
de tabela.**

**O domínio enumera FORMAS INERTES, não uma subárvore (emenda S327, rail r7-F1).** "Sob `.github/`"
não é a propriedade que esta wave precisa: medido (S327), a versão por subárvore aceitava
`.github/dependabot.yml`, `.github/workflows/pwn.yml` e — o caso que decide — a rota shipada
`validate.yml.template` com quatro caracteres a menos no destino, `.github/workflows/validate.yml`,
que entregaria um workflow **VIVO** ao adopter contradizendo o `note` da própria tabela ("the
adopter never gets a live workflow from install") com o upgrade saindo 0. O domínio passou a ser a
enumeração exata, em CÓDIGO: `docs/<nome>.md` (um segmento, Markdown), `.github/CODEOWNERS`,
`.github/CODEOWNERS.template` e `.github/workflows/<nome>.template` (um segmento sob `workflows/`,
e é o sufixo `.template` que impede o GitHub Actions de carregar o arquivo). Qualquer outra forma é
recusa NOMEADA. É a mesma inversão que a r3-F1 e o PLAN-185 W0 já pagaram — enumerar o PROVADO
seguro em vez de imaginar a próxima forma insegura.

**A FONTE é fisicamente confinada ao checkout em execução (emenda S327, rail r7-F2).** O destino
tem confinamento físico desde a r1-F2; a fonte tinha só o predicado léxico, e `[ -f ]`, `cp`,
`cat`, `sed` e o sha256 **seguem symlink**. Medido (S327): com
`templates/docs/BRANCH-PROTECTION.md` sendo um link para um arquivo regular fora do checkout, os
bytes entregues batiam sha a sha com o arquivo de FORA — conteúdo estrangeiro instalado como
conteúdo do framework, e registrado no manifesto como framework-owned. `_wbm_source_confined`
(biblioteca, UM dono, consumido por `install.sh`, `upgrade.sh` e `doctor.sh`) recusa qualquer
componente symlink do path e exige que o ancestral EXISTENTE mais profundo resolva sob o
`SOURCE_DIR` físico. "Ancestral existente mais profundo", e não "o pai", para que uma fonte
simplesmente AUSENTE — a pista `--pin` — mantenha o veredito `SKIPPED (source missing)` da r2-F2
em vez de virar uma recusa de confinamento. Um checkout real deste framework tem ZERO symlinks
(medido), então a regra não custa nada em produção — mas os oráculos precisaram passar a copiar
`templates/` de verdade em vez de symlinká-lo.

**A escrita no destino é ATÔMICA, e um destino multi-link é recusado (emenda S327, rail r7-F3).**
Um hard link é um segundo NOME para o mesmo inode: nenhuma checagem de PATH o enxerga, e o destino
continua sendo um arquivo regular fisicamente dentro do `$TARGET`. Medido (S327), pré-cura, nos
dois mecanismos: `cp src dst` e `cat src > dst` mudaram os bytes do arquivo de FORA do alvo, e o
`chmod` da normalização de modo mudou o modo dele. A cura é ESTRUTURAL — arquivo temporário no
MESMO diretório, modo definido nesse inode novo, e `mv -f` (rename) sobre o destino —, com a
recusa nomeada de `nlink > 1` como cinturão auditável em cima. O temporário deliberadamente NÃO usa
`_up_tmpbase` (r5-F3): aquela função responde "onde fica o SCRATCH?", e isto não é scratch, é o
destino sendo preparado; `rename(2)` não atravessa sistema de arquivos.

**A tabela vem do CHECKOUT em execução, e de mais lugar nenhum (emenda S327, rail r6-F3).**
O override de ambiente foi **REMOVIDO**, não endurecido: a rodada 5 o mantinha atrás de um switch
de teste mais a exigência de que o path vivesse sob `${TMPDIR:-/tmp}`, e as DUAS condições são
setáveis por quem já consegue influenciar o ambiente de um upgrade — setar `TMPDIR` é o mesmo
gesto de setar a tabela. Era um carregador de fixture morando dentro de um entrypoint de
produção, não uma fronteira de confiança. Hoje `_WBM_ROUTES_TSV` (nome deliberadamente FORA do
prefixo `FMS_*` que marca os knobs de entrada da biblioteca) é resolvido
INCONDICIONALMENTE no source da biblioteca a partir do próprio `BASH_SOURCE` dela — a atribuição
sobrescreve qualquer valor herdado. Existe **UMA** re-atribuição de produção, o snapshot do
`upgrade.sh` que sobrevive ao `--pin` (r2-F2): código em processo, depois do source, nunca leitura
de ambiente; os oráculos asseguram que não aparece uma segunda. Fixture agora é **árvore COPIADA**
(`_mk_source_copy` nos três oráculos): o checkout de teste carrega a própria
`scripts/delivery-routes.tsv`, e a biblioteca dele lê a tabela dele — que é exatamente a forma de
um checkout parcial ou adulterado em campo.

**O CABEÇALHO é pré-condição de TODO leitor (emenda S327, rail r6-F2).** A rodada 4 pôs
`_wbm_route_table_ok` só na frente do `doctor.sh`. Medido (S327) nos outros dois leitores: com a
linha de cabeçalho apagada, ou com os nomes da 2ª/3ª coluna corrompidos, `_wbm_route_dests`
enumerava os 6 destinos, `_wbm_route_rows_total` contava 6, `routes == rows` valia — a
pré-condição AC-9 PASSAVA — e `_wbm_route_src` resolvia uma fonte com `rc=0`. Um cabeçalho não é
decoração: é a afirmação de que a coluna 2 significa "fonte" e a 3 "transformação"; sem ele as
linhas são uma tupla sem rótulo que o leitor está adivinhando, e o palpite dirige escritas. A
pergunta mudou para `_wbm_route_table_gate` — UMA implementação, memoizada por PATH da tabela
(o `doctor.sh` pergunta uma vez por registro de manifesto; uma passada extra por registro mediu
~20 ms cada) e chamada pelos TRÊS laços que abrem a tabela. Tabela inutilizável ⇒ `rc=2` em todos
os leitores, zero rotas, e uma linha nomeada UMA vez. **`rc=1` deixou de responder por "tabela
ausente"**: `rc=1` é resolvido pelo fallback identity `$root/$rel` em todo chamador, o que para uma
tabela ausente é o D3/D4 chegando por um arquivo que falta — foi por isso que a r4-F3 precisou de
um portão separado no doctor. E `_write_baseline_manifest` abandona a escrita INTEIRA nesse caso:
substituir um manifesto correto por um quase-vazio é o que o uninstall e o doctor leem em seguida.

### §2 Enumeração é por ARQUIVO, e vem de quem entregou
As duas árvores entram em `_framework_target_entries()` via
`FMS_DELIVERED_TEMPLATES` = exatamente os paths que o caller entregou naquele run,
nunca glob de diretório — a regra do `ADR-155-AMEND-1` §3: *delivered* = registro
de entrega EFETIVA, não presença de arquivo e não cerimônia. Tabela ausente ⇒ lista
vazia (fail-closed). `.github/CODEOWNERS` e `.github/CODEOWNERS.template` são
**mutuamente exclusivos por run** (`install.sh:1496` elif vs `:1511` else): emitir
os dois garante um miss espúrio.

### §3 Registro por byte-compare, espelhando o precedente
`install.sh:1318-1329` registra `if [[ "$INSTALL_ONE_WROTE" = "1" ]] || cmp -s <fonte> <target>`
— **também quando não escreveu**. A regra "PRESERVED/SKIPPED ficam fora", isolada, é REGRESSÃO:
derruba os 5 registros num SEGUNDO install e embarca VERDE, porque nenhum Check roda install
duas vezes. Reconciliada com `upgrade.sh:3110-3115` (mantém INSTALLED/REFRESHED/**IDENTICAL**,
exclui PRESERVED/SKIPPED): o critério é *o framework deixou os bytes dele no path*.
**Armadilha:** `install_docs_template` (`:1446`) **nunca** seta `INSTALL_ONE_WROTE` (é de
`install_one`, `:877`/`:905`/`:919`) ⇒ precisa de flag própria, e a metade `cmp -s` compara o
relpath de **FONTE** — o que não tinha resolvedor até §1.
**Escopo do byte-compare (emenda S327, rail r4-F1):** o byte-compare vale para uma rota que ESTE
run processou (o `|| cmp -s` de `install.sh:1318-1329` vive DENTRO da função de entrega). Um run
que não entregou — `ceremony=user`, `--dry-run`, pré-condição falha — não tem evidência nenhuma
sobre esses bytes: bytes iguais são coincidência até que se saiba quem os pôs ali. A única
evidência admissível nesse caso é o REGISTRO ANTERIOR com digest batendo; sem isso, não registra.

### §4 Propriedade das duas árvores: hash-gate, com a colisão declarada
Rota **(ii)** da OQ-5, decidida pelo Owner em 2026-08-24: refresh gateado contra as
gerações conhecidas, derivadas do **histórico git por arquivo**
(`upgrade.sh:3204-3212` — o contrato exige que o commit que muda o doc APENDE o hash
da geração substituída), nunca de tags.

**Argumento de colisão:** bytes idênticos são prova de origem quando o CONTEÚDO é
framework-específico. Medido: `templates/.github/CODEOWNERS.template` = 33 linhas / 1442 b, 10
linhas de regra, **9 nomeando `.claude/` e `PROTOCOL.md`** — um adopter não escreve isso por
acaso. *Correção de medição:* 1442 b é o TEMPLATE; o RENDERIZADO tem 11 ocorrências de
`{{OWNER_HANDLE}}`, logo seu tamanho depende do handle (1321 b com handle de 5 caracteres) — o
que é, ele mesmo, a razão de os bytes entregues não existirem em checkout nenhum. **Risco
residual concentrado em `docs/*`**, onde um adopter plausivelmente é dono: aceito, declarado e
real — `uninstall.sh` remove arquivos cujo sha bate com o registro (`uninstall.sh:5-8`).

### §5 Emenda da OQ-5 (a rota (ii) não alcançava quem ela existe para curar)
`upgrade.sh:798` resolve `CEREMONY_EFFECTIVE="user"` sem install-state legível, e a
entrega é gateada em `CEREMONY != user` ⇒ o adopter HISTÓRICO não recebia nada.
**Emenda:** install-state ilegível **mas `.claude/.framework-version` presente ⇒
tratar como adopter e ENTREGAR** — o marcador é a evidência de que o diretório já é
adopter, a distinção que o fail-safe perde. O default de diretório que nunca recebeu
install **não muda**, e a sonda **NÃO pode** setar `_CEREMONY_PERSIST=1` (`:800-803`:
só RECORDED/EXPLICIT persistem; persistir a inferência tornaria UMA migração perdida
permanente). **Teste obrigatório:** o Check roda num e2e **sem o
pin** `v1.2.0` (`test-install-upgrade-parity-e2e.sh:110`) — com o pin o install já
grava `.install-state.json` e a perna é estruturalmente cega.

### §6 A PISTA do gerador (OQ-4) — MEDIDA na S327; ratificação = assinatura
**O Owner decidiu medir antes de ratificar; a medição está em
`PLAN-183/w5-oq4-measurement-S327.md` (braços A/B/C em clones separados, S327).** Resultado:
os três braços são indistinguíveis em todos os oráculos de regressão (ownership e2e com RED set
exato `{OWN-0016, OWN-0024, OWN-0027}`, paridade, unit, baseline, rota); no install fresco os
manifestos de B e C são byte-idênticos (5/5 rotas; a 6ª é exclusiva); A registra 0/5 — o D3 era
latente-por-não-entrada. A única diferença entre as pistas é a continuidade do `CODEOWNERS`
RENDERIZADO no upgrade: bytes que não existem em checkout nenhum só entram por `hash_source`
declarado. **Decisão registrada neste ADR (a assinatura de `wave-w5-approved.md` a ratifica):
pista MISTA — as 5 rotas verbatim ficam na pista não-condicional; só `.github/CODEOWNERS` entra
na condicional (`HASH_TARGET` na entrega, `HASH_PRIOR_RECORD` na continuidade), declarada em TODO
caminho de entrega.** Custo medido: +22 linhas de código sobre a pista não-condicional e **ZERO
linhas em `scripts/tests/ownership_table.tsv`** — a moldura "2-3 linhas de TSV" estava errada:
o orçamento é enumeração + declaração + resolução, não linhas de tabela. Residual declarado: a
posse das duas árvores é decidida pelo hash-gate da entrega (§4) + o `hash_source` do
`CODEOWNERS`, não por uma superfície nova em `_ownership_verdict()`; estender a propriedade
"UMA decisão" (CLAUDE.md §4) às duas árvores é wave própria (W5-c), não este ADR.

Por que a pista decide se as linhas novas valem algo: `HASH_SOURCE` tem **um** consumidor
(`:395-405`), atrás de `elif _wbm_is_conditional` (`:320`), e tanto `_wbm_is_conditional` quanto
`_wbm_declared_hash_source` (`:311`) cobrem **exatamente 4 paths** (`SPEC/v1`, `SPEC/v1/*`,
`PROTOCOL.md`, `.claude/.framework-version`). Na pista NÃO-condicional — onde as 6 rotas caem
hoje — linhas novas no TSV são **inertes**.

| braço | o que instala | o que mede |
|---|---|---|
| A | HEAD intocado | a linha de base própria, medida (nunca a prosa) |
| B | enumeração + leitor de rota + resolução NÃO-condicional, 6 rotas | se a pista simples basta |
| C | B menos CODEOWNERS; `.github/CODEOWNERS` na pista CONDICIONAL com `hash_source` declarado | a hipótese MISTA — 5 verbatim fora, só o renderizado dentro |

Precedente que justifica medir: `install.sh:2508-2510` registra que **a tentativa anterior desta
wave regrediu 24 células** por deixar installs frescos sem declaração. **Até o veredito, ZERO
linhas se escrevem em `scripts/tests/ownership_table.tsv`** (medido: 15 colunas, 65 linhas de
dados).

### §7 Ratificação da OQ-4 (2026-08-25) — a pista MISTA é decisão, não hipótese
O Owner ratificou a OQ-4 em 2026-08-25 (S328). Resposta verbatim: **«Pista MISTA — braço C
(Recomendado)»**. A ratificação é RETROATIVA: o braço C já É o conteúdo do patch de `6304f66`.
Duas referências na árvore pós-land — `w5-ceremony/PROPOSED-PATCH.md:89` declara "pista MISTA
(braço C), que é o conteúdo deste patch", e `_wbm_declared_hash_source` vive em
`_framework_manifest_set.sh:376` com UM consumidor em `:1085` (as citações `:311`/`:320` do §6 são
da árvore PRÉ-land). Nenhuma linha de código muda por causa desta seção.

**O que a ratificação FIXA.** (1) A pista é MISTA: as 5 rotas verbatim ficam na não-condicional, e
só `.github/CODEOWNERS` entra na condicional. (2) O custo é ZERO linhas em
`scripts/tests/ownership_table.tsv`; a moldura "2-3 linhas de TSV" do enunciado da OQ-4 está
refutada pela medição da S327. (3) A posse de `docs/` e `.github/` é decidida pelo hash-gate da
entrega (§4) mais o `hash_source` declarado do `CODEOWNERS`, não por superfície nova em
`_ownership_verdict()`. (4) Estender a propriedade "UMA decisão" às duas árvores permanece wave
própria (W5-c), com OQ própria.

**Checkout raso — a direção do erro é o que torna o defeito observável.** No run `32845976930`,
com `fetch-depth: 1`, o hash-gate do `upgrade.sh` não enxerga a geração `v1.2.0` da FONTE e
classifica os 3 templates como `PRESERVED`; a paridade maintainer acusa `STALE 3`. Reproduzido
local: fonte `--depth 1` ⇒ 3, `--unshallow` ⇒ 0. `PRESERVED` é a direção SEGURA: falta de
evidência nunca sobrescreve o arquivo do adopter. Foi ela que converteu histórico incompleto em
divergência de paridade VISÍVEL, em vez de sobrescrita silenciosa. Um gate que respondesse
`REFRESHED` à mesma falta de evidência teria posto bytes do framework sobre bytes do adopter, com
o run saindo verde. Cura em `738007e`: o deepen roda ANTES da paridade em `smoke-install.yml`.

**Este ADR não mantém nada PROPOSED.** O land `6304f66` CRIOU este arquivo com `status: PROPOSED`
(medido em `git show 6304f66:.claude/adr/ADR-194-delivery-route-resolution.md`, linha 4). O flip
textual para `ACCEPTED` é edição canônica posterior e entra no main pelo pacote de cerimônia
S328-A. O ato que ratifica permanece a assinatura sobre o sentinel, não o commit que a reescreve.

**Obrigação solidária do contrato-raiz.** O `CLAUDE.md` §5 descreve o estado deste ADR em prosa —
hoje diz *"status textual `PROPOSED` — o flip é edição canônica da próxima cerimônia"* e *"OQ-4 foi
MEDIDA (…), não decidida"*. As duas afirmações ficam **falsas** no instante em que este arquivo vira
`ACCEPTED`. O `CLAUDE.md` é lido no Gate 1 de **toda** sessão nova, então um contrato-raiz que
contradiz o ADR canônico não é imprecisão de documentação: é governança errada entregue por padrão,
a cada boot, até alguém notar. A atualização das duas frases pertence ao **mesmo** pacote de
cerimônia que faz este flip — não a um closeout posterior.

## Consequences

**Positivas (+)** — "qual é a fonte deste destino?" ganha **um** dono, e um quarto
reimplementador vira veto de revisão, não questão de estilo. O rc=2 troca omissão silenciosa por
falha nomeada. D1 fecha a ÚNICA causa restante do vermelho de paridade: pós-D2 o e2e é
`STALE 3 / UNCLASSIFIED 0` — **D1 é load-bearing para o verde; D2 deu diagnóstico**.

**Negativas (−)** — as duas árvores passam a ter propriedade declarada ⇒ o hash-gate pode tomar
arquivo adopter-owned byte-idêntico a uma geração antiga (§4: risco ACEITO e testado como caso).
O registro em SEGUNDO install (byte-compare) tem de ficar: derrubá-lo embarca verde. E
`delivery-routes.tsv` está ausente das DUAS listas `paths:` de
`.github/workflows/smoke-install.yml` (medido: grep = 0) — com um script canônico lendo a
tabela, typo só-na-tabela não dispara e2e nenhum; fechar na MESMA cerimônia.

**Neutras (~)** — os membros do manifesto do ADR-192 não mudam de substância, mas tocar
`scripts/tests/ownership-nightly-gate.sh` ou `ownership-expected-reds.txt` (linhas 5-6 do
manifesto) exige bump do sha ⇒ o manifesto canônico entra no Scope (lição de `verify-counts.sh`,
S326). E verificar por `grep` é TAUTOLÓGICO (S325: apontar uma rota para fonte
errada-mas-existente manteve 10 testes verdes, porque as asserções comparavam contra a própria
tabela) — a verdade vem dos call-sites.

## Blast radius

**L3+.** Oráculo `python3 .claude/hooks/check_canonical_edit.py --is-canonical`, medido nesta
sessão — **canônico=1**: `scripts/install.sh`, `scripts/upgrade.sh`,
`scripts/_framework_manifest_set.sh`, `.claude/governance/gate-scripts-manifest.txt` e **este
próprio ADR** (`.claude/adr/` = 1). **Canônico=0 mas dentro do Scope assinado** (o gate G4
compara todo path tocado, sem filtro de canonicidade): `scripts/doctor.sh`,
`scripts/delivery-routes.tsv`, `scripts/tests/_parity_classify.py`,
`scripts/tests/ownership_table.tsv`, `scripts/tests/ownership-expected-reds.txt`,
`docs/ownership-decision-table.md`, `CLAUDE.md` e os testes novos. CI: `smoke-install.yml`,
`ownership-nightly.yml`; em campo, adopters passam a receber por upgrade duas árvores que nunca
receberam.

## Verification

- **Leitor de rota:** controles positivos (remover a tabela / apontar para fonte
  errada-mas-existente / remover uma linha / inventar uma linha) ⇒ os TRÊS consumidores
  VERMELHOS, a mensagem NOMEANDO o plant.
- **Baseline:** `test_install_baseline_manifest.sh` — rotas entregues registradas com o digest
  da FONTE certa; a renderizada não registrada.
- **Paridade (o observador real das rotas novas):**
  `test-install-upgrade-parity-e2e.sh --mode maintainer` e `--mode user`, com `user` em 0; a
  perna da OQ-5 roda com `CEO_PARITY_PIN` fora de `v1.2.0`.
- **Regressão de propriedade:** `test-ownership-verdict-unit.sh` (milissegundos) +
  `ownership-nightly-gate.sh`; id-set RED **exatamente** `{OWN-0016, OWN-0024, OWN-0027}`, sem
  TIMEOUT/ESCAPE/AMBIG, `CELL_TIMEOUT` pinado em 180 (`test-ownership-table.sh:41` traz default
  60; o CI usa 180 em `ownership-nightly.yml:131`) — sob carga o default flaka em TIMEOUT, que o
  gate trata como falha.
- **Limite declarado do instrumento:** o e2e de ownership **não vê** as rotas novas —
  `_relpath_for` (`test-ownership-table.sh:117-123`) conhece só `spec|protocol|marker`; ele é
  detector de REGRESSÃO das 3 superfícies antigas, e quem observa as novas é a paridade + o
  teste de baseline.
- **Verde-total é sinal de PARAR**, não de sucesso (`ownership-nightly-gate.sh` falha também com
  encolhimento): significa que a tabela-verdade mudou.
- **Evidência do land (2026-08-25):** `OWNER-S327-LAND.sh` V1–V6 verdes, V7 diferido ao nightly
  (`--ownership-e2e=defer`), V5 com `EXPECTED_PARITY_MAINTAINER_STALE=0`. **Ainda NÃO observado
  neste ADR:** a primeira rodada do nightly sobre D1+D3 (cron `43 6 * * *`) só ocorre depois deste
  texto, e o conjunto RED **esperado** — não medido — é `{OWN-0016, OWN-0024, OWN-0027}`, o mesmo
  declarado em `scripts/tests/ownership-expected-reds.txt`. Registrar o resultado de uma execução
  futura como se fosse evidência colhida é fabricar auditoria; o resultado real entra aqui depois
  de a rodada acontecer, ou não entra.

## References

`PLAN-183` §8.5 (a FORMA), §8.5.1 (as três rotas), §8.5.2 (origem ≠ rota), §8.7 + bloco OQ-5
ratificado, §8.8 (ordem e medição pin↔HEAD), Open questions OQ-4 · `ADR-155` (manifesto
baseline) + `ADR-155-AMEND-1` §3 (under-claim) · `ADR-190` (a tabela de propriedade É o
contrato; INV-1..4) — este ADR **estende**, não emenda: acrescenta a peça de ROTA ao lado da de
ORIGEM · `ADR-192` (manifesto dos gate-scripts; armadilha do bump) · `PLAN-167`/`PLAN-168`
(`_ownership_verdict()`) e `PLAN-182` (`_lib/runtime_paths.py`, 16 → 0), os dois precedentes de
"um resolvedor único + o censo que prova que ninguém re-deriva localmente".
