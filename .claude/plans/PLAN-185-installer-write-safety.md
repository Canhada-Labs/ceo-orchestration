---
id: PLAN-185
title: "Seguranca de escrita do installer: symlink pendente escreve FORA do target, e --github-owner corrompe CODEOWNERS para sempre"
status: executing
created: 2026-08-24
reviewed_at: 2026-08-26
executing_at: 2026-08-26
owner: CEO
depends_on: []
level: L3
budget_tokens: 120-220k (W0 10-20k; W1 50-90k; W2 40-70k; W3 20-40k) — revisto no debate round-1, que mediu 7 escritores em vez de 1
budget_sessions: 2-3
context_risk: low
external_wait: "nenhum. Os dois defeitos estao REPRODUZIDOS; nao ha janela de dados nem decisao de terceiro a esperar."
eta_calendar: "W0 mesmo-dia (read-only). W1/W2/W3 dependem de UMA cerimonia GPG do Owner sobre CINCO canonicos (oraculo = 1 em cada) — ver §4.1."
tags: [seguranca, installer, symlink, escrita-fora-do-target, adopter, canonico]
---

# PLAN-185 — Seguranca de escrita do installer

> **Por que este plano existe separado.** Os dois defeitos abaixo foram
> reproduzidos em installs REAIS durante a S325 e estao registrados no
> `PLAN-183` §9.1/§9.2, que os classificou como "plano proprio, classe
> seguranca". O Owner ratificou essa disposicao em 2026-08-24. A razao de nao
> serem uma wave do PLAN-183: aquele plano esta travado em tres OQs abertas, e
> subordinar correcao de escrita-fora-do-target a uma fila bloqueada e o
> oposto de tratar seguranca como seguranca.

## 1. Os dois defeitos, com a reprodução

> **Âncoras re-derivadas contra HEAD `f787cf2` (debate round-1, C1).** As três
> coordenadas que este plano citava (`:1466-1472`, `:2139-2159`, `:1508`) estavam
> MORTAS, e uma delas sustentava uma afirmação FALSA. Toda citação abaixo traz o
> NOME DA FUNÇÃO ao lado da linha: nome de função não apodrece.

### F1 — escrita FORA do `$TARGET` via destino não confinado (GRAVE)

Os escritores de destino do `install.sh` decidem se escrevem com um teste de
existência que **segue** o symlink (`-e`). Um link **pendente** faz `-e` dar
FALSO, e a escrita seguinte vai **através** do link — fora da árvore do target.

**Reproduzido (S325):** plantar um symlink pendente de `docs/rotation-log.md`
apontando para `/tmp/<dir>/pwned.md` num target limpo e rodar o install em modo
`maintainer` ⇒ `exit 0`, log `COPIED:`, e o arquivo escrito FORA do target. O
installer reporta sucesso.

**Não é um sítio: são sete** (predicado → escrita, medidos no vivo):
`install_template` `:959`→`:964-965`; `install_reference_personas`
`:1446`→`:1449-1450`; `install_docs_template` `:1514`→`:1519-1520`; o render do
CODEOWNERS em `install_github_templates` `:1626`→`:1642-1643`; `build_settings`
`:1720`→`:1729`/`:1737`/`:1761`/`:1774`; `install_protocol_pointer`
`:2113`→`:2139`/`:2142`; e `portable_sed_inplace` `:2171`, cujo temporário tem
nome PREVISÍVEL (`:2174`) dentro da árvore do target.

**A defesa existe, mas são DOIS mecanismos com semânticas OPOSTAS — e a citação
antiga apontava para nenhum deles.** `:2139-2142` é o render do ponteiro
`PROTOCOL.md`, ele próprio um dos sete escritores desguardados, sem uma linha de
symlink. Os reais: `_assert_no_symlink_parents()` (`:863`, componentes
INTERMEDIÁRIOS, `exit 1`, **um único chamador** — `install_one:910`) e o
disjunto de FOLHA `[[ -e "$dst" || -L "$dst" ]]` (`:900` dry-run, `:913` real),
que **PULA** e continua; mais um terceiro precedente de PULAR, o skip `-L "$f"`
de `apply_placeholder_substitutions` (`:2293`, mensagem `:2301`).

Consequência para o desenho: é a classe "ramo local" que o `CLAUDE.md` §4 proíbe
na forma por OMISSÃO, e **não existe "guarda existente" a reusar** — existem
dois fragmentos inline com veredictos divergentes. A W1 CRIA a primeira função
de destino; não extrai uma pronta.

### F2 — `--github-owner` com `/` aborta e deixa CODEOWNERS de 0 bytes, para sempre (GRAVE)

O `sed` de `install_github_templates` (`install.sh:1643`) interpola o valor da
flag **sem escapar o delimitador**:

```
sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g" "$codeowners_src" > "$dst"
```

**Reproduzido:** um valor contendo `/` ⇒ `exit 1`,
`sed: bad flag in substitute command`, e o destino com **0 bytes**. O
redirecionamento `>` cria o arquivo ANTES do `sed` falhar, então o vazio
sobrevive ao aborto.

**São DOIS `sed`, não um.** O segundo é `:1635`, a sonda de byte-compare do ramo
EXISTS, com `2>/dev/null`: handle inválido ⇒ a sonda aborta em SILÊNCIO, o `cmp`
nunca roda, `_append_delivered_template` (`:1637`) nunca é chamado, e o veredito
de POSSE muda — do lado do upgrade isso aterrissa em `PRESERVED (unclaimed)`. É
o ramo que a fixture (c) percorre. O terceiro consumidor, `_add_sub
"OWNER_HANDLE"` (`:2193`), já é seguro: delimitador `|` com escape de `[|&\]`
(`:2188`). **E o valor é persistido sem validação** (`:2829`), enquanto
`_read_install_state_github_owner` (`upgrade.sh:3679`) sai `3` para o que a
gramática recuse — o upgrade degrada em silêncio para handle vazio e troca de
ramo de entrega.

O que torna isso permanente são **duas** coisas: o arquivo de 0 bytes vira
**EXISTS-skipped para sempre** (`:1626`) **e** o rollback não o alcança — o
snapshot (`:821-824`) e o `cleanup_on_failure` (`:737`) cobrem **apenas**
`$TARGET/.claude`, nunca `docs/` nem `.github/`. O adopter fica com um CODEOWNERS
vazio que o GitHub trata como "sem donos", e `upgrade.sh` **não consegue**
recuperá-lo: sem `github_owner` registrado ele cai em `PRESERVED (unclaimed)` e
nunca re-renderiza.

## 2. Escopo, e o que fica FORA

Dentro: as curas em `scripts/install.sh`, a conversão de `scripts/upgrade.sh` em
CONSUMIDOR dos predicados compartilhados (deixar duas cópias divergirem é o
mecanismo exato dos defeitos D1–D4 do PLAN-183), os testes que as provam, e o
censo da CLASSE.

**Hard link entra em escopo.** `-L` não o vê: um segundo nome do mesmo inode faz
`cp`/`>` escreverem em arquivo fora do target sem que nenhum teste de PATH
enxergue. O lado do upgrade já recusa (`_up_tpl_multilink_refuses`,
`upgrade.sh:3857`, sobre `_up_tpl_nlink` `:3842`); afirmar que "a CLASSE está
fechada" com hard link aberto seria falso.

Fora, declarado:
- **F3** (os dois ramos do CODEOWNERS não serem exclusivos no tempo) fica no
  `PLAN-183` §9.3 — é defeito de paridade, não de escrita; e nada aqui depende
  das três OQs daquele plano.
- **Harnesses de vendor** (`_codex_harness.sh`, `_grok_harness.sh`: 4 sítios) e
  ferramentas locais (`install-npm.sh`, `measure-repo-size.sh`: 2). Mesma forma,
  superfície diferente. A rota (ii) do censo §5.1 os alargaria para 24 sítios,
  14 deles `indeterminado` porque o matcher não situa a escrita dentro de
  funções de 177–253 linhas — para vários a cura é *encurtar a função*,
  refatoração que esta wave não abre. Ficam no baseline com a razão registrada.
- **A exatidão da gramática de handle perante a doc do GitHub.** A regex viva
  aceita hífen final e hífens consecutivos, que o GitHub recusa. A propriedade
  que importa aqui é o conjunto fechado `[A-Za-z0-9-]` não conter `/`, `&`,
  `\`, `|`, newline nem espaço — e essa vale. Apertar divergiria de `upgrade.sh`
  sem ganho de segurança; item próprio, com fonte citada, quando houver rede.

## 3. Waves

### W0 — censo da CLASSE antes de curar um sitio (read-only, sem cerimonia)

> **Status S326 (2026-08-24): RASCUNHO no disco, NAO commitado.** Um Security Engineer entregou
> `.claude/scripts/check-installer-write-safety.py` (273 sitios; 12 desguardados + 15
> `indeterminado` = 27 bloqueantes, 4 de `sed`), o baseline
> `.claude/scripts/data/installer-write-safety-baseline.txt`, 56 testes com controle POSITIVO em
> arvore-sombra, e o relatorio `PLAN-185/w0-censo-S326.md`. O pair-rail devolveu TRES levas de P1
> da MESMA classe (fail-open por forma nao modelada): 8 e 7 curados (§7, §7-ter), 9 ABERTOS
> (§7-quater). Classe que regenera apos 3 passadas = arquitetura errada (PROTOCOL anti-padrao 6),
> daí a 4ª passada INVERTIDA que o Owner ratificou (§4). Ate la os 4 arquivos ficam untracked
> (nunca `git add -A` com eles no disco); as checkboxes seguem ABERTAS tambem pela clausula "roda
> em CI" (wiring em `validate.yml` e canonico — vai no pacote; linha exata no relatorio §8).

A licao que este repo ja pagou duas vezes (PLAN-182: 16 modulos; PLAN-167:
`_ownership_verdict`): curar os sitios reportados e deixar a classe viva
converte defeito latente em defeito vivo na proxima wave que alargar o
dominio de entrada.

- [ ] `[P0]` Censo de TODOS os sitios que decidem escrita por teste de
      existencia que segue symlink (`-e`, `-f`, `-d` sem `-L`), em
      `scripts/*.sh`, com o veredito por sitio: guardado / desguardado /
      nao-aplicavel.
      Check: o censo e um SCRIPT versionado, nao uma medicao de sessao, e
      roda em CI; falha se um sitio desguardado novo aparecer. Contagem 0
      REPROVA — significa que o padrao de busca esta errado, nao que o repo
      esta limpo. **Piso re-medido no debate round-1: `install.sh` sozinho tem
      SETE escritores desguardados (§1), entao um censo que devolva menos que
      isso para este arquivo esta com o matcher quebrado.** O ">= 2" que este
      Check pedia era satisfeito por um instrumento cego a cinco deles.
- [ ] `[P0]` Censo de toda interpolacao de valor de flag em `sed`/`awk` sem
      escape de delimitador, mesmo escopo.
      Check: idem — script versionado, e um controle POSITIVO que planta uma
      interpolacao insegura numa arvore-sombra e exige VERMELHO. Piso: os
      DOIS `sed` de `$GITHUB_OWNER` (`:1635` e `:1643`), nao um.
- [ ] `[P1]` A 4ª passada estende o escopo do censo a `scripts/doctor.sh` e
      IMPRIME o escopo varrido. O baseline atual não tem entrada de
      `doctor.sh`, e isso hoje é ambíguo entre "sem sítio" e "fora do escopo"
      — ambiguidade que um censo não pode ter.
      Check: o instrumento imprime a lista de arquivos varridos; se
      `doctor.sh` estiver na lista com zero sítios, isso é um FATO medido,
      não uma omissão.

### W1 — confinamento de DESTINO (F1 em todos os escritores; canonico: exige cerimonia)

> **A partição "W1 cura F1, W2 cura F2" não sobreviveu ao debate (C3).** O sítio
> da F2 (`:1626-1643`) é ele próprio um sítio da F1, e uma partição que os
> separa deixa esse vetor aberto ENTRE as duas waves. W1 e W2 são uma superfície
> só, entregue num pacote só; a divisão abaixo é de assunto, não de janela.

- [ ] `[P0]` **Um predicado de CONFINAMENTO DE DESTINO, com dono decidido.**
      A função vive em `scripts/_framework_manifest_set.sh`, ao lado de
      `_wbm_source_confined` (`:621`) — a biblioteca sourced que já OWNS
      predicados desta família e que os três scripts de entrega carregam.
      **Por quê ali e não em `install.sh`:** pôr a função no `install.sh`
      fecharia a porta para `upgrade.sh` e `doctor.sh`, que hospedam a mesma
      classe, e o custo evitado (um path a menos no Scope) é ilusório — o
      arquivo já entra no Scope pela W2 `[P0]`. Assinatura espelhando a de
      origem: `_wbm_dst_refuses <target_root> <rel_path>` → `0` = recusar,
      motivo em `_WBM_DST_REFUSE_WHY`; sem `echo`, sem `exit`. Recusa:
      relpath não confinado (vazio, absoluto, com `..`), COMPONENTE existente
      que seja symlink, folha symlink (pendente ou não), e `nlink > 1` na
      folha. Fail-CLOSED quando o predicado falta, igual a
      `_install_src_refuses` (`:1470-1481`).
      Check: teste unitário por forma recusada, cada um com controle POSITIVO
      (remover a cláusula ⇒ vermelho NOMEANDO a forma). O `for comp in
      $parent_rel` sem aspas de `:872` é corrigido no mesmo passo (hoje um
      componente com `*` sofre expansão de pathname).
- [ ] `[P0]` **Predicado ≠ política: o veredito é do CHAMADOR.** A função só
      responde "este destino deve ser recusado?". `install_one` preserva o
      SKIP que os testes atuais fixam (`:913`); os escritores novos RECUSAM
      de forma nomeada, ACUMULAM, e a RUN falha no fim com o sumário — **nem
      aborto no meio da entrega** (`exit 1` in-loco, como
      `_assert_no_symlink_parents:878` faz hoje, multiplica pontos de aborto
      parcial) **nem silêncio** (SKIP mudo é fail-open na entrega).
      Check: fixture provando que `install_one` continua PULANDO e que um
      escritor novo RECUSA, na mesma run.
- [ ] `[P0]` **PRÉ-VOO antes da primeira escrita.** O rollback cobre
      **apenas** `$TARGET/.claude` (snapshot `:821-824`,
      `cleanup_on_failure:737`); `docs/` e `.github/` nunca entram, então uma
      recusa in-loco no meio da entrega deixa o target MISTO. O predicado
      roda sobre TODOS os destinos de `install_docs_templates` e
      `install_github_templates` ANTES da primeira escrita.
      Check: fixture com symlink pendente no SEGUNDO destino ⇒ o install
      recusa sem ter escrito o PRIMEIRO (asserção: o primeiro não existe).
- [ ] `[P0]` **Os SETE escritores passam pela MESMA função** (§1): `:959`,
      `:1446`, `:1514`, `:1626`, `:1720`, `:2113`, e o temporário de
      `portable_sed_inplace` (`:2174`) ganha nome imprevisível no diretório
      de destino.
      Check: por escritor — symlink PENDENTE para fora ⇒ recusa nomeada e o
      arquivo externo **não existe** (asserção nos BYTES, nunca no exit code);
      symlink RESOLVIDO para fora ⇒ mesma recusa; hard link ⇒ mesma recusa;
      sem symlink ⇒ install inalterado (não-regressão). Prova de uso
      COMPORTAMENTAL, nunca `grep`: reverter a função deixa os SETE vermelhos.
- [ ] `[P1]` **Um teste de FORMA fecha a classe; contagem de baseline não.**
      Nenhum `[[ -e "$dst" ]]` (ou irmão) seguido de escrita, em
      `scripts/*.sh`, fora do predicado compartilhado.
      Check: verde hoje; plantar um escritor com a forma antiga numa
      árvore-sombra o deixa VERMELHO nomeando o path. A contagem do baseline
      mede delta contra uma allowlist — evidência SECUNDÁRIA, não fechamento.
- [ ] `[P2]` O ramo `--dry-run` consulta o mesmo predicado. Hoje `:951`,
      `:1438`, `:1506`, `:1621` e `:1695` usam `-e` puro e o preview MENTE
      sobre um symlink pendente ("would COPY") — e é o output com que o
      adopter decide.

### W2 — a cura de F2 (canonico: mesma cerimonia)

- [ ] `[P0]` **A gramática de handle é REUSADA, não reescrita.**
      `scripts/upgrade.sh:3700` já embute
      `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`, e o comentário de `:3674-3678`
      diz que existe para que o upgrade não possa reproduzir ESTE defeito,
      citando o PLAN-183 §9.2 pelo nome. A regex é adotada **verbatim** como
      dono compartilhado em `scripts/_framework_manifest_set.sh`, e
      `upgrade.sh` vira CONSUMIDOR **no mesmo patch** (OQ-5).
      Check: um teste prova que os dois executáveis resolvem a MESMA função,
      e uma fixture de contrato prova o ciclo install-escreve ⇒ upgrade-lê —
      hoje uma divergência de gramática faz
      `_read_install_state_github_owner` sair `3` e o upgrade degradar em
      silêncio para handle vazio.
- [ ] `[P0]` **Validar no PARSE e antes de PERSISTIR.** `--github-owner` é
      hoje aceito cru em `:479`. A validação entra ali (único ponto que cobre
      os três consumidores de uma vez) **e** antes de `:2829` gravar no
      install-state — `GITHUB_OWNER` é global e o próximo chamador não passa
      pelo parse. Isso torna os DOIS `sed` (`:1635`, `:1643`) seguros por
      construção.
      Check: fixture (a) abaixo + a perna do install-state do AC-2.
- [ ] `[P0]` **Escrita ATÔMICA, na forma que já funciona no repo.** `mktemp`
      **no diretório de DESTINO** (mesmo filesystem — `mv` a partir de
      `/tmp`, como `:1634` faz, degrada para copy+unlink e sob ENOSPC
      reintroduz o 0-byte que esta wave existe para matar), nome
      IMPREVISÍVEL (`portable_sed_inplace:2174` demonstra o furo do nome
      fixo), `chmod 0644` explícito (`mktemp` cria `0600`, e um CODEOWNERS
      ilegível para o time é regressão que bytes e linhas não pegam), e
      `trap` de limpeza. Precedente correto: `_up_tpl_write`
      (`upgrade.sh:3800`, `mktemp "$_utw_dir/..."` em `:3803`). Copiar
      qualquer das duas formas do `install.sh` regenera a classe DENTRO da
      cura.
      Check: a fixture (b) assere também o MODO.
- [ ] `[P0]` **Três fixtures, reescritas.**
      **(a)** `--github-owner 'a/b'` ⇒ falha nomeada ANTES de qualquer
      `mkdir` e **nenhum** `.github/CODEOWNERS` criado (asserção de path
      inexistente, não só o exit); SEGUNDA perna com symlink pendente em
      `$TARGET/.github/CODEOWNERS` ⇒ mesma recusa, com asserção nos bytes do
      alvo externo (este sítio é ele próprio um sítio de F1 — §1).
      **(b)** handle válido ⇒ asserções **DERIVADAS**, nunca constantes:
      linhas do renderizado `==` linhas da fonte; `grep -c "$HANDLE"` `==`
      `grep -c '{{OWNER_HANDLE}}'` da fonte (11 hoje, derivado no teste);
      bytes `> 0`; modo `0644`; e **só depois**
      `grep -c '{{OWNER_HANDLE}}' == 0` (a negativa sozinha é satisfeita por
      arquivo vazio, que é exatamente o defeito). **As constantes `1442 bytes
      / 33 linhas` SAEM:** medido, 1442/33 é o tamanho do template
      NÃO-renderizado; o renderizado é `1266 + 11 × len(handle)`, então a
      asserção antiga só passaria para um handle de exatamente 16 caracteres
      e ficaria vermelha na próxima edição legítima do template.
      **(c)** destino de 0 bytes pré-existente ⇒ ver o `[P0]` seguinte; e a
      sonda de `:1635` também recusa handle inválido.
      As três ficam VERMELHAS com a cura revertida.
- [ ] `[P0]` **A auto-cura de 0 bytes exige PROVENIÊNCIA, não contagem de
      bytes.** Tamanho não distingue "o `sed` abortou" de "o adopter esvaziou
      de propósito" — truncar para zero é um modo real de DESLIGAR roteamento
      de revisão obrigatória, e reescrever re-liga donos num repositório de
      terceiro (classe D4 do PLAN-183, que já custou uma sessão). O framework
      já registra autoria: `_append_delivered_template` (`:1637`/`:1645`) e o
      install-state (`:2829`). Recupera-se **só** com (0 bytes) E
      (proveniência prova autoria), de forma RUIDOSA (`RECOVERED:` +
      `_state_record_op`); sem prova, `WARNING` nomeado, nunca escrita
      silenciosa. Default e alternativa em **OQ-1**.

### W3 — o contrato de ameaça e o registro arquitetural (canonico: mesma cerimonia)

- [ ] `[P0]` A superfície de ESCRITA DE DESTINO do installer entra em
      `docs/threat-model.md`. Hoje o arquivo modela symlink / hardlink /
      absoluto / `..` **só** para extração de tarball (T-004, `:631-644`,
      `squad-import.py`); a escrita do installer não está no contrato.
      **Aviso operacional, planejado e não descoberto na cerimônia:** o
      `CLAUDE.md` §5 registra que `check-threat-model-freshness.py` REESCREVE
      esse arquivo (`accepted → stale`) e derruba o P0 de qualquer SIGN — o
      passo de reverter esse flip entra no roteiro do pacote.
      Check: o item novo cita os sete escritores e o predicado que os fecha.
- [ ] `[P1]` ADR curto registrando a decisão **"predicado na biblioteca,
      política no chamador"**, com os três consumidores previstos
      (`install.sh`, `upgrade.sh`, `doctor.sh`) — a fronteira de 3+ módulos
      que o próprio gate de arquitetura exige.

## Acceptance criteria

- [ ] AC-1 `[P0]` F1 não reproduz em **nenhum** dos sete escritores: a
      reprodução da §1 termina com **zero bytes escritos fora do target** e
      recusa NOMEADA. **O critério é BYTES, nunca exit code** — o defeito
      atual sai `exit 0` com log `COPIED:`, e a política por chamador (W1
      `[P0]`) permite que a run siga sem `exit` não-zero no ponto da recusa.
      Check: os SETE testes da W1 verdes, e VERMELHOS com a função revertida
      por `git stash` do plant.
- [ ] AC-2 `[P0]` F2 não reproduz, em três pernas: **(i)** handle inválido ⇒
      falha nomeada e nenhum `.github/CODEOWNERS` criado; **(ii)** handle
      inválido ⇒ `github_owner` **não** é gravado no install-state (validação
      de `:2829` — sem ela o handle corrompido degrada silenciosamente a
      entrega do próximo upgrade); **(iii)** CODEOWNERS de 0 bytes
      pré-existente é curado por um install subsequente **quando a
      proveniência prova autoria**, e recebe `WARNING` nomeado quando não.
      **Declaração:** a rota de UPGRADE é impotente por construção — o
      install aborta no `sed` antes de `:2829` gravar o handle, e sem handle
      registrado o upgrade cai em `PRESERVED (unclaimed)` e nunca
      re-renderiza. A recuperação exige `install.sh --github-owner <handle>`,
      e isso entra no texto da mensagem de erro.
      Check: as três fixtures da W2 verdes; a (c) prova a recuperabilidade.
- [ ] AC-3 `[P0]` A CLASSE está fechada na população que esta wave cura, e o
      instrumento roda em CI. **Critério (rota (i) do censo §5.1):** zero
      sítios BLOQUEANTES de classe A em `install.sh` e `upgrade.sh` — **19 →
      0**, medido sobre o baseline de 27 entradas; os 8 restantes (4
      `_codex_harness.sh`, 2 `_framework_manifest_set.sh`, 1
      `install-npm.sh`, 1 `measure-repo-size.sh`) ficam no baseline com a
      razão registrada. "Zero desguardados" *tout court* era inalcançável
      dentro do escopo declarado, e um AC que só passa alargando a wave é um
      AC que será relaxado sob pressão.
      Check: (a) o censo roda no per-PR em `validate.yml`, que **não tem
      filtro `paths:`** — sem a armadilha de "gate que a mudança não
      dispara"; (b) plantar um sítio desguardado numa árvore-sombra o deixa
      VERMELHO nomeando o path; (c) o teste de FORMA da W1 `[P1]` é o que
      fecha a classe — a contagem é evidência secundária; (d) e2e novo em
      `scripts/tests/*.sh` entra nas **DUAS** listas `paths:` do
      `smoke-install.yml` (`:5` e `:108`, que o arquivo manda manter
      idênticas) **e** ganha step invocador **e** controle NEGATIVO (renomear
      o e2e ⇒ o step falha por arquivo ausente, nunca passa calado).
      Polaridade do gate per-PR: **OQ-3**.
- [ ] AC-4 `[P1]` UMA cerimônia cobrindo W1+W2+W3: sentinel na forma VIVA,
      Scope **DERIVADO do patch** no finalize (nunca à mão — a S324 errou
      duas vezes), `touched − scope = ∅` antes do commit.
      **O gate NÃO é sobre canônicos:** medido em
      `PLAN-182/OWNER-S326-LAND.sh:186-195`, ele compara `git apply
      --numstat` — TODO path do patch — contra o bloco assinado. Os
      não-canônicos entram no Scope também, ou o land reprova.
      **Conjunto ESPERADO** (a derivação manda; a lista existe para
      dimensionar o pedido ao Owner): canônicos (oráculo = 1 em `f787cf2`) —
      `scripts/install.sh`, `scripts/upgrade.sh`,
      `scripts/_framework_manifest_set.sh`, `.github/workflows/validate.yml`,
      `.github/workflows/smoke-install.yml`; não-canônicos —
      `check-installer-write-safety.py`, o baseline (curar REMOVE linhas
      dele), os testes novos, `docs/threat-model.md`, o ADR da W3, e este
      plano.
      Check: `_sentinel_grants_path` devolve True para cada path CANÔNICO
      tocado, e o gate `touched − scope` sai zero sobre o conjunto INTEIRO.

## 4. Cerimonia

`scripts/install.sh` e **CANONICO** (oraculo `--is-canonical` = 1), logo W1, W2
e W3 exigem sentinel assinado pelo Owner. A W0 e read-only e nao exige nada.
(O numero de canonicos no Scope NAO e um: ver §4.1.)

Recomendacao do CEO: **uma** cerimonia cobrindo W1+W2+W3, porque tocam a mesma
superficie — cerimonias separadas pagariam o custo em dobro para o mesmo Scope,
e deixariam uma janela em que metade da classe esta curada.

**Decisão do Owner (2026-08-25, S328, AskUserQuestion, verbatim): «4ª passada
INVERTIDA + W1/W2 em pacote (Recomendado)».** O que isso autoriza, e só isso:

1. A **4ª passada** do censo da W0 INVERTE a regra: o instrumento
   (`check-installer-write-safety.py`) enumera as formas PROVADAS seguras,
   cada uma com controle positivo (remover a guarda ⇒ vermelho nomeado), e
   classifica todo o resto como `indeterminado`. Os 19 achados abertos do
   pair-rail (9 do §7-quater de `PLAN-185/w0-censo-S326.md` + 10 de
   `PLAN-183/w5-ceremony/rail-materials-round-1.md`) viram fixtures de
   regressão; o censo re-derivado sai em `PLAN-185/w0-censo-S328.md`. Os 4
   arquivos hoje untracked são commitados (paths explícitos, nunca `-A`)
   quando o rail sair limpo — isso fecha as duas checkboxes da W0, exceto a
   cláusula "roda em CI" (wiring em `validate.yml` é canônico: vai no pacote).
2. `/debate` round-1 sobre a proposta W1+W2 **antes** de qualquer patch.
3. Flips autorizados: `draft → reviewed` (com `reviewed_at`) **após**
   consensus `design-coherent` do round-1; `reviewed → executing` no commit da
   W0. Se o debate devolver ESCALATE/VETO, o pacote NÃO se monta e a pergunta
   entra no §6 abaixo.
4. W1+W2 numa ÚNICA cerimônia (pacote S328-C), **empilhada** sobre a árvore
   final do pacote A do PLAN-183, porque tocam os mesmos arquivos
   (`scripts/install.sh`, `scripts/upgrade.sh`). Entrega conforme a decisão
   Q4 da mesma rodada: push granular do não-canônico + pacotes independentes
   com um único script da manhã (`PLAN-183/OWNER-S328-MORNING.sh`).

### 4.1 Dimensionamento do Scope — comunicado ANTES da assinatura (debate C11)

A frase "`scripts/install.sh` é canônico (oráculo = 1), logo W1 e W2 exigem
sentinel" continua verdadeira e **subdimensionada em 5×**. Medido em `f787cf2`,
o pacote pede assinatura sobre **cinco** canônicos: `scripts/install.sh`,
`scripts/upgrade.sh`, `scripts/_framework_manifest_set.sh`,
`.github/workflows/validate.yml` e `.github/workflows/smoke-install.yml`. E o
gate de land compara TODO path do patch contra o Scope, então os não-canônicos
do AC-4 viajam no mesmo bloco assinado. O Owner precisa disso ANTES de assinar —
descobrir o dimensionamento no land é o que aborta a cerimônia.

**Empacotamento (não vinculante):** um Scope, dois commits. A F1 muda fluxo de
controle em sete funções e a F2 muda um contrato de VALOR compartilhado com o
`upgrade.sh`; dois commits dentro do mesmo Scope assinado preservam `git revert
<sha>` por defeito, sem custo de assinatura.

## 5. Limitacao honesta

Os dois defeitos foram reproduzidos por mim em installs reais, mas **nao ha
evidencia de exploracao**. F1 exige que algo plante um symlink no target
antes do install — num fluxo normal o adopter e quem controla o target, entao
o vetor realista e um target compartilhado ou um repositorio clonado de
terceiro, nao um ataque remoto. Isso nao reduz a gravidade da cura (o
installer nao deve escrever fora do diretorio que recebeu), mas situa a
urgencia: e correcao de robustez com blast radius alto, nao incidente.

**Residual declarado — TOCTOU.** Entre o predicado e a escrita há uma janela
irredutível em shell: nada impede que o destino vire symlink depois da checagem.
Não é motivo para não guardar; é motivo para dizer o que a guarda entrega — ela
reduz a janela, não a fecha. E o cenário onde importa é exatamente o do parágrafo
acima. Fechar de verdade exigiria `openat`/`O_NOFOLLOW`, que bash não oferece.

**Segundo residual.** `mv` sobre um destino que é symlink SUBSTITUI o link por
arquivo regular — mais seguro que o `cp` atual, mas destrói em silêncio um
symlink deliberado do adopter. O predicado da W1 cobre; fica registrado para que
a cura da W2 não o reintroduza por descuido.

## 6. Open questions

O debate round-1 (2026-08-26) devolveu cinco decisões de POLÍTICA, não de
desenho. Nenhuma bloqueia a execução: cada uma tem um **default conservador que
a noite implementa**, escolhido para ser o mais fácil de reverter. O Owner
decide de manhã; onde ele discordar, a mudança é local e barata.

- **OQ-1 — Recuperar o CODEOWNERS de 0 bytes: quando?** 0 bytes não distingue
  "o `sed` abortou" de "o adopter esvaziou de propósito" (desligar roteamento de
  revisão sem apagar o path é uso real). **Default:** recuperar **só com
  EVIDÊNCIA** de autoria (`_append_delivered_template` ou `github_owner` no
  install-state); com prova, recuperação RUIDOSA (`RECOVERED:` +
  `_state_record_op`); sem prova, `WARNING` nomeado apontando `scripts/doctor.sh`
  e a edição manual, nunca escrita silenciosa. **Alternativa:** recuperar sempre
  que o arquivo tiver 0 bytes — mais simples, ao custo de reescrever estado do
  adopter (classe D4 do PLAN-183).

- **OQ-2 — `--github-owner org/team` é sintaxe VÁLIDA, e a gramática o rejeita.**
  `templates/.github/CODEOWNERS.template:14` é `@{{OWNER_HANDLE}}`, então
  `org/team` completa `@org/team` — CODEOWNERS de TIME. O input que dispara a F2
  não é erro de digitação. **Default:** manter a gramática estreita (o que
  `upgrade.sh:3700` já decidiu; `/` é o delimitador do `sed`), com a mensagem de
  falha DIZENDO que handles de time não são suportados por esta flag e apontando
  a edição manual. **Alternativa:** suportar time exige delimitador não-`/` em
  todos os consumidores — wave própria.

- **OQ-3 — Polaridade do gate do censo no per-PR.** A 4ª passada INVERTIDA
  classifica como `indeterminado` toda forma não provada segura (hoje 15).
  Bloquear `indeterminado` per-PR cria deadlock: um refactor com forma
  nova-mas-segura deixa o repo vermelho até alguém estender a allowlist, e
  destravar passa pelos canônicos ao redor. **Default:** per-PR bloqueia
  **apenas** desguardado NOVO (delta contra o baseline) e o `exit 2` de
  contagem-zero; `indeterminado` é contado, IMPRESSO e vira ratchet no
  `ownership-nightly.yml` (`schedule:` ignora `paths:`) — precedente:
  `ownership-expected-reds.txt` + `ownership-nightly-gate.sh`. **Alternativa:**
  bloquear `indeterminado` per-PR desde já, aceitando o deadlock como custo.

- **OQ-4 — Rollback: pré-voo ou snapshot estendido?** O snapshot cobre só
  `$TARGET/.claude`; `docs/` e `.github/` ficam fora, e é por isso que o 0-byte
  sobrevive. **Default:** **pré-voo** (W1 `[P0]`) — recusar antes da primeira
  escrita, zero estado parcial, sem mexer na semântica de rollback.
  **Alternativa:** estender o snapshot a `docs/`+`.github/` — cobre mais
  (inclusive falhas que não são de destino), mas muda o comportamento de backup
  do installer e cresce o patch.

- **OQ-5 — `upgrade.sh` convertido a consumidor no MESMO patch?** Deixar duas
  cópias da gramática e do predicado divergirem é o mecanismo exato de D1–D4
  (PLAN-183, seis sessões de main vermelho). **Default:** SIM, mesmo patch — é a
  razão de o Scope ter cinco canônicos (§4.1). **Alternativa:** cerimônia
  separada, com o Owner pagando uma segunda assinatura e reabrindo, nesse
  intervalo, a classe que este plano fecha.

Perguntas NOVAS que surgirem durante a execução autônoma NÃO têm resposta na
noite (o Owner está ausente): registram-se aqui como OQ numerada, a unidade
correspondente fica BLOQUEADA nesse ponto, e a decisão é do Owner na manhã
seguinte — nunca do CEO.
