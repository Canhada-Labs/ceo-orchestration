---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: VP Engineering
generated_at: 2026-08-26T19:58:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O diagnóstico e a forma estão certos: F1 e F2 são a mesma classe — "ramo local por omissão", uma
  defesa que existe no corpus e não é chamada num segundo sítio. Curar por UMA função compartilhada
  é o desenho correto.
- **As coordenadas que sustentam o desenho estão erradas em `HEAD b07be9b`.** `install.sh:2139-2159`
  não tem defesa de symlink nenhuma (é `install_protocol_pointer`); a defesa real são DOIS
  mecanismos com semânticas OPOSTAS — `_assert_no_symlink_parents` (`:863-882`) aborta com `exit 1`,
  o disjunto de folha `[[ -e "$dst" || -L "$dst" ]]` (`:900`/`:913`) PULA e continua. O plano pede
  "reusar a mesma guarda" e exige FALHA nomeada na folha; não podem ser verdade juntos.
- **A cura da W2 já existe duas vezes no repositório**, e reescrevê-la reproduz a classe que o plano
  diz fechar: `install.sh:2181-2190` (`_add_sub`, delimitador `|` + escape de `[|&\]`) e
  `upgrade.sh:3679-3704`, que embute `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$` **citando o PLAN-183 §9.2
  pelo nome**. A W2 como desenhada seria a terceira implementação.

## Risks

1. **R-VP1 — a "guarda existente" que a W1 manda reusar não é uma função, e são duas.** Severity:
   CRITICAL.
   O proposal e o plano §1 apontam `install.sh:2139-2159`; ali está o `case "$SOURCE_DIR"` de
   `install_protocol_pointer` (`scripts/install.sh:2138-2144`), sem uma linha de symlink. A defesa
   real é `_assert_no_symlink_parents()` (`:863-882`, componentes INTERMEDIÁRIOS, `exit 1`) mais o
   disjunto de FOLHA `[[ -e "$dst" || -L "$dst" ]]` (`:900`, `:913`), que é texto inline, não
   função. E `install_docs_template` não chama nenhum dos dois: `:1523-1524` faz `mkdir -p` + `cp`
   sem checagem de ancestral. F1 tem DOIS furos; o plano nomeia um.
   Mitigação: reescrever §1 e W1 com as coordenadas vivas; W1 fecha folha E pais, e declara que a
   "extração" CRIA a primeira função de destino — não extrai uma existente.

2. **R-VP2 — AC-1 exige FALHAR onde o precedente PULA; W1 `[P1]` fica insatisfazível.** Severity:
   HIGH.
   `install_one` trata symlink de folha como EXISTS-skip e segue (`scripts/install.sh:913-915`),
   mas AC-1 exige que o install "FALHE de forma nomeada". Se `install_docs_template` falhar onde
   `install_one` pula, os dois sítios não têm o mesmo efeito, e o Check do W1 `[P1]` ("`grep` prova
   que os dois sítios chamam a MESMA função … reverter deixa AMBOS vermelhos") não pode passar.
   Mitigação: separar PREDICADO de POLÍTICA — a função compartilhada só responde "este destino deve
   ser recusado?" e publica o motivo numa variável; cada chamador escolhe pular (`install_one`,
   preservando o comportamento hoje testado) ou abortar. AC-1 passa a exigir "zero bytes fora do
   target + mensagem nomeada", que é o que a §1 reproduziu — não `exit != 0`.

3. **R-VP3 — a cura da F2 já existe no corpus; escrevê-la de novo É a classe.** Severity: CRITICAL.
   `scripts/upgrade.sh:3699-3701` valida o handle com `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`, e o
   comentário logo acima (`:3675-3678`) diz textualmente que existe para que "upgrade.sh não possa
   reproduzir" o defeito do PLAN-183 §9.2 — o MESMO defeito da F2. Em paralelo,
   `scripts/install.sh:2181-2190` (`_add_sub`) já substitui o MESMO `$GITHUB_OWNER` com delimitador
   `|` e escape de `[|&\]` (`:2193`). Um terceiro escape em bash dentro de
   `install_github_templates` é o quarto ramo local do mesmo valor.
   Mitigação: gramática em UM lugar; `install.sh` valida no PARSE (`:479`), antes de qualquer
   consumidor, e a W2 documenta os 4 consumidores (`:1635`, `:1643`, `:2193`, `:2829`).

4. **R-VP4 — gramáticas divergentes quebram o contrato install→upgrade.** Severity: HIGH.
   O proposal pergunta por "hífen não inicial/final, ≤39". A regex viva de `upgrade.sh:3701`
   PERMITE hífen final. Se a W2 adotar a regra mais estrita, um handle aceito por um lado é
   recusado pelo outro: `install.sh:2829` grava `request.github_owner` no
   `.claude/.install-state.json`, e `_read_install_state_github_owner` sai `3` ao lê-lo, deixando
   `_UP_GH_OWNER=""` (`scripts/upgrade.sh:4361-4364`) — o upgrade então troca de ramo em silêncio
   (`:4452`, `:4499`) e entrega `.github/CODEOWNERS.template` em vez do renderizado.
   Mitigação: adotar a regex EXISTENTE verbatim. Se ela tiver de mudar, muda nos dois arquivos na
   MESMA cerimônia, com uma fixture install-escreve ⇒ upgrade-lê.

5. **R-VP5 — AC-3 "zero sítios desguardados" é mecanicamente inalcançável, e o censo já disse
   isso.** Severity: HIGH.
   `.claude/scripts/data/installer-write-safety-baseline.txt` tem 27 entradas (10 `upgrade.sh`, 9
   `install.sh`, 4 `_codex_harness.sh`, 2 `_framework_manifest_set.sh`, 1 `install-npm.sh`, 1
   `measure-repo-size.sh`), e o seu cabeçalho define que "remover uma linha é como uma cura se
   registra" — logo o gate passa COM sítios desguardados listados. O censo §5.1 já classificou o
   W1 `[P1]` como INALCANÇÁVEL e recomendou a rota (i); o plano §3 ainda carrega o texto antigo.
   Mitigação: absorver a rota (i) ANTES de montar o pacote, com a população nomeada ("zero
   bloqueantes de classe A em `install.sh` e `upgrade.sh`"). Custo: ~2-4k tokens, mesma sessão.

6. **R-VP6 — F1 são quatro sítios em `install.sh`, não um.** Severity: HIGH.
   O censo §3.1 mede `:944` (`install_template`), `:1431` (`install_reference_personas`) e o
   `install_docs_template` como byte-idênticos no predicado e na escrita, mais `:1575`
   (`build_settings`) com a mesma forma; verifiquei os dois primeiros no vivo. Curar só
   `install_docs_template` deixa três cópias vivas no mesmo arquivo, e a próxima wave que alargar o
   domínio de entrada reabre a classe — a justificativa literal da W0.
   Mitigação: W1 cobre os quatro chamadores pela função única. Estimativa: +8-15k tokens, mesma
   sessão — o teste é o mesmo com quatro fixtures.

7. **R-VP7 — o segundo `sed` da F2 está no ramo de RECUPERAÇÃO e o plano não o nomeia.** Severity:
   MEDIUM.
   `scripts/install.sh:1635` interpola `$GITHUB_OWNER` sem escape dentro do ramo `EXISTS`, para
   montar a sonda `cmp` do `mktemp` — exatamente o ramo que a fixture (c) da W2 percorre.
   Mitigação: a W2 declara os dois sítios; a fixture (c) assere que a sonda também recusa.

8. **R-VP8 — "0 bytes = corrupção" é o predicado errado, e existe um melhor no repo.** Severity:
   MEDIUM.
   O tamanho não distingue "o `sed` abortou" de "o adopter esvaziou o arquivo de propósito" —
   truncar para zero bytes é um modo real de desligar ownership sem apagar o path. O framework já
   registra PROVENIÊNCIA: `_append_delivered_template` (`scripts/install.sh:1637`, `:1645`) e o
   `.claude/.install-state.json` (`:754`, `:2829`).
   Mitigação: reescrever só quando (0 bytes) E (a proveniência diz que fomos nós que entregamos
   aquele path), emitindo `RECOVERED:` + `_state_record_op` — recuperação silenciosa sobre estado
   do adopter é o que o PLAN-183 D4 já custou uma sessão.

9. **R-VP9 — o corpus inteiro do PLAN-185 está ancorado em coordenadas mortas.** Severity: MEDIUM.
   Plano §1, proposal e o docstring do próprio instrumento
   (`.claude/scripts/check-installer-write-safety.py:19,21,34,37`) citam `:1466`, `:1508`, `:2148`,
   `:2043`. No vivo: `:1512`/`:1519`, `:1643`, `:863`, `:2181`. O baseline casa por
   `(path, class, fingerprint)` e é imune, mas o rail V2 e o Owner leem a prosa.
   Mitigação: re-ancorar citando FUNÇÃO além da linha antes do V2 — nome de função não apodrece.

10. **R-VP10 — uma cerimônia, dois commits.** Severity: LOW. Posição completa na resposta 2 abaixo.

## Must-fix (blocking)

1. Corrigir as coordenadas e a afirmação central da §1/proposal: `install.sh:2139-2159` **não** é a
   defesa de symlink. Nomear `_assert_no_symlink_parents` (`:863-882`) e o disjunto de folha
   (`:900`/`:913`) como os dois mecanismos, com semânticas diferentes (R-VP1).
2. Resolver a contradição FALHA-vs-PULA antes de escrever código: predicado compartilhado + política
   por chamador, e AC-1 re-escrito para "zero bytes fora do target + mensagem nomeada" (R-VP2).
3. Reusar a gramática de handle que já existe em `upgrade.sh:3699-3701` em vez de inventar uma
   segunda; validar no parse da flag (`install.sh:479`), não no sítio de escrita (R-VP3, R-VP4).
4. Absorver a rota (i) do censo §5.1 no texto do W1 `[P1]` e do AC-3 — o critério atual só passa
   alargando o escopo da wave (R-VP5).
5. W1 cobre os quatro sítios de `install.sh` (`:944`, `:1431`, `install_docs_template`, `:1575` ao
   menos triado), não apenas `install_docs_template` (R-VP6).
6. Incluir no Scope os artefatos que a cura OBRIGA a tocar:
   `.claude/scripts/data/installer-write-safety-baseline.txt` (curar remove linhas),
   `.claude/scripts/check-installer-write-safety.py` e `.github/workflows/validate.yml` (wiring da
   AC-3). Sem isso o `touched − scope = ∅` da AC-4 falha no land — previsão mecânica, não opinião.

## Nice-to-have (advisory)

1. Emitir o motivo da recusa em `_WBM_DST_REFUSE_WHY`, espelhando `_WBM_SRC_CONFINE_WHY`
   (`scripts/_framework_manifest_set.sh:621`), para as mensagens ficarem iguais nos dois lados.
2. Um teste de FORMA: nenhum `[[ -e "$dst" ]]` seguido de `cp` fora do predicado, em `scripts/*.sh`.
   Isso fecha a classe estruturalmente; contagem de baseline não fecha (ver resposta 4).
3. Registrar num ADR curto a decisão "predicado na biblioteca, política no chamador" — três
   consumidores previstos (`install.sh`, `upgrade.sh`, `doctor.sh`) é a fronteira de 3+ módulos.

## Unseen by the original plan

1. **A F2 tem um quarto consumidor que já está certo** (`_add_sub`, `:2193`) e um que ninguém
   modelou (`:1635`). O plano trata a F2 como um sítio.
2. **`upgrade.sh` já se defendeu desta exata F2** (`:3675-3704`), citando o PLAN-183 §9.2 — um
   precedente ratificado cuja gramática é a resposta pronta à 2ª pergunta aberta do proposal.
3. **O contrato install→upgrade passa pelo `.install-state.json`** e é sensível à gramática: uma
   validação mais estrita no install é mudança de contrato entre dois executáveis, não validação
   local.
4. **A W1 e a AC-3 disputam o mesmo arquivo**: o baseline é dado do gate E artefato de cura.
5. **`install_docs_template` não tem guarda de ancestral**: mesmo com a folha curada, um `docs/`
   symlinkado escreve fora — `mkdir -p`/`cp` de `:1523-1524` seguem o link do diretório.

## What I would NOT change

- **Separar o PLAN-185 do PLAN-183.** Subordinar escrita-fora-do-target a uma fila bloqueada por OQ
  é o erro que o plano corretamente recusa.
- **A W0 antes da cura, e a 4ª passada invertida.** Sem o censo eu não teria os sítios `:944`/`:1431`
  nem a inalcançabilidade da AC-3 — o instrumento pagou por si.
- **Provar nos BYTES do alvo externo, não no exit code** — a única asserção que o defeito atual
  (`exit 0` + log `COPIED:`) não satisfaz por acidente.
- **A ordem "só depois `grep -c '{{OWNER_HANDLE}}' == 0`"** na fixture (b): a negativa sozinha é
  satisfeita por arquivo vazio, que é precisamente o defeito.

## Respostas diretas às quatro perguntas do CEO

**1. Onde vive a função.** Em `scripts/_framework_manifest_set.sh`, ao lado de
`_wbm_source_confined` (`:621`) — a biblioteca sourced que já OWNS predicados desta família, e que
`install.sh` carrega em `:249-252`. Assinatura espelhando a de origem:
`_wbm_dst_refuses <target_root> <rel_path>` → `0` = recusar, motivo em `_WBM_DST_REFUSE_WHY`; sem
`echo`, sem `exit`. É isso que mantém a porta aberta para `upgrade.sh` (`:1519`, `:1560`, `:1625`)
e `doctor.sh` sem alargar o Scope — eles consomem depois, sem editar a função. Fail-closed quando o
predicado falta, igual a `_install_src_refuses` (`scripts/install.sh:1471-1476`). Checar antes o
oráculo `--is-canonical` do arquivo: se for canônico ele entra no Scope, e isso é custo de Scope,
não motivo para pôr a função em `install.sh`.

**2. Uma cerimônia cobrindo W1+W2.** Sim para UMA cerimônia — Scope é conjunto de paths e ambas
tocam `scripts/install.sh`; duas assinaturas pagariam o Owner em dobro pelo mesmo conjunto. Não
para um commit só: a F1 muda fluxo de controle em quatro funções, a F2 muda um contrato de VALOR
compartilhado com `upgrade.sh`, e dois commits dentro do mesmo Scope assinado preservam
`git revert <sha>` por defeito. O risco real do acoplamento não é o revert — é o item 6 do
Must-fix: sem os artefatos do censo no Scope, `touched − scope = ∅` reprova o land.

**3. Gatear a recuperação de 0 bytes.** Sim, gatear — mas não em "0 bytes AND marcador". O marcador
diz que o framework está instalado; não diz que nós escrevemos AQUELE arquivo. O predicado certo é
proveniência: `_append_delivered_template` / `.install-state.json` já respondem "isto foi entrega
nossa?". Um CODEOWNERS de 0 bytes que nunca entregamos é estado do adopter, e reescrevê-lo é a
classe D4 do PLAN-183 outra vez. A recuperação também tem de ser RUIDOSA (`RECOVERED:` +
`_state_record_op`).

**4. AC-3 segue do desenho?** Não. Segue de duas coisas que o desenho não entrega: o instrumento em
CI **e** um baseline vazio — e o baseline tem 27 entradas por construção, com "remover linha = cura
registrada". Com Scope `install.sh`, os 10 sítios de `upgrade.sh` seguem listados e o gate segue
VERDE: a métrica mede delta contra uma allowlist, não fechamento de classe. O que fecha a classe é
estrutural — nenhuma decisão de escrita por teste de existência fora do predicado compartilhado
(Nice-to-have 2). Recomendo a AC-3 como essa asserção de forma, com a contagem como evidência
secundária.
