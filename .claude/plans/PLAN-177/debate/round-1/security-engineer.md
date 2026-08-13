---
plan: PLAN-177
round: 1
critic: security-engineer
created_at: 2026-08-13
---

# Security Engineer — round 1, PLAN-177 (rc.4)

## Verdict

**ADJUST** — 6 must-fix, nenhum VETO.

A arquitetura do P1-4 está certa e é a única que fecha a fronteira: o gate
tem de viver nos DOIS validadores, com igualdade EXATA, e o ponto de
inserção escolhido no `_release_tag_guard.py` é justamente o caminho que
nenhuma variável de repo destrava. Não há nada no plano que degrade um
trust boundary — os must-fix são cirúrgicos sobre uma cura em voo.

Não exerço VETO: o escopo do meu veto (fronteira de confiança, supply
chain, gate de CI que não pode falhar) é o P1-4, e o plano MOVE esse gate
na direção certa. Bloquear a rc.4 seria manter o estado atual, que é
estritamente pior. Os must-fix são condições de mérito, não de bloqueio —
com a ressalva de que M1 e M2 são P0 e, sem eles, o gate novo tem dois
buracos que eu reproduzi nesta sessão.

## Summary

Reproduzi os parsers dos dois validadores com 8 formas de `verdict:` e
verifiquei a cadeia release.yml → release-gate → await-release-gate →
publish linha a linha. Três achados que o plano não cobre:

1. `verdict:` com valor VAZIO não vira string — vira `{}` no validador
   servidor e `[]` no tag guard. O plano escreve literalmente
   `verdict.get("verdict","")`; um `.strip()` em cima disso levanta
   `AttributeError`, e no validador servidor uma exceção não capturada
   sai com **exit 1 = `EXIT_INFRA_ERROR`** — exatamente o único código
   que o `release.yml` roteia pela `CEO_PAIR_RAIL_VERDICT_OPTIONAL`.
   Input malformado saindo pelo ramo de infra é a inversão literal da
   doutrina do `CLAUDE.md` §4.
2. Os dois parsers são **last-wins em chave duplicada**: `verdict: NO-GO`
   seguido de `verdict: GO` resolve para `GO` nos dois. O controle
   "exatamente 1 linha VERDICT" já EXISTE na superfície irmã
   (`OWNER-GA-CUT.sh:382-384`, "rail r11 P1-1") e não está sendo levado
   junto. Não levar é reproduzir a forma exata do P1-4: um controle que
   mora em uma superfície só.
3. O gate no `validate-pair-rail-verdict.py` **não sobrevive** a
   `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` (`release.yml:689` tem
   `continue-on-error` nessa condição — o exit 3 é engolido). A fronteira
   fecha assim mesmo, porque o step seguinte (delta+ancestry) morre
   incondicionalmente com a var ligada (`release.yml:786-789`) e é ele
   que chama `_release_tag_guard.py delta` (`release.yml:851-853`) sem
   `continue-on-error`. Ou seja: **o gate do tag guard é o load-bearing;
   o do validador é defesa em profundidade.** O plano trata os dois como
   equivalentes e a AC-1 não pina essa assimetria.

No W1, a escolha de manter o gate `--ceremony user` preserva
literalmente o dano que o revisor nomeou, num plano cuja razão de existir
é fechar um P1 que já foi re-encontrado por cura parcial.

E o varrimento do `INTEGRITY.md` está sub-escopado: encontrei mais três
promessas falsas no MESMO arquivo, fora das faixas de linha do plano.

## Risks

- **R-S1 (alto, P0).** Um `verdict:` malformado sai como INFRA no
  validador servidor. Com a var de transição desligada (default) o job
  ainda fecha, então não é um bypass hoje — mas o código passa a ter uma
  rota de "decisão ilegível ⇒ ramo que tem escape hatch documentado". É
  a semente da próxima cura parcial.
- **R-S2 (alto, P0).** Chave `verdict:` duplicada resolve para a ÚLTIMA.
  Um envelope cujo corpo humano diz NO-GO e que carrega um segundo
  `verdict: GO` no fim do bloco YAML passa nos dois gates novos. O único
  freio real é a assinatura do Owner sobre a árvore taggeada — que é
  adequada contra atacante externo, e inútil contra erro de edição.
- **R-S3 (médio).** O gate novo depende de o step delta+ancestry
  continuar sem `continue-on-error` e continuar chamando `delta`. Já
  existe assert estrutural para a primeira metade
  (`test_release_workflow_asserts.py:769-787`, "exatamente uma chave
  continue-on-error em release.yml"); não vi assert para a segunda.
- **R-S4 (médio).** W1 introduz uma MUTAÇÃO nova num arquivo
  adopter-owned (`$TARGET/.gitignore`) num caminho que roda REPETIDAMENTE
  (upgrade), não uma vez (install). A idempotência proposta é por linha
  (`grep -Fxq`, `install.sh:1846`): um adopter que REMOVE deliberadamente
  `.claude/state/` recebe a linha de volta em todo upgrade, silenciosamente.
  A allowlist que o plano remove justifica-se hoje exatamente por
  "adopter-owned e não deve ser clobbered" (`_parity_classify.py:123-132`).
- **R-S5 (médio).** `--ceremony user` continua sem entrega: `/night-mode on`
  segue deixando `.claude/settings.local.json` commit-elegível nesses
  adopters — o dano literal do `verdict-ga-1.txt:5`.
- **R-S6 (baixo/operacional).** `OWNER-GA-CUT.sh` só aceita
  `VERDICT: GO` exato (`:387-389`), enquanto os gates novos aceitam
  também `GO-WITH-CONDITIONS`. rc.2 e rc.3 voltaram os dois como
  `GO-WITH-CONDITIONS` (`.claude/governance/pair-rail-verdict-v1.3.0-rc.{2,3}.md:4`)
  ⇒ a probabilidade de o GA bater nesse abort é alta. O cabeçalho do
  próprio script (`:12`) diz o CONTRÁRIO do que o código faz.

## Must-fix

### M1 [P0] — a decisão malformada não pode sair pelo ramo de INFRA

Evidência empírica desta sessão (rodei os dois parsers reais):

| forma de `verdict:` | `_release_tag_guard._parse_verdict` | `validate_pair_rail_verdict.parse_verdict_file` |
|---|---|---|
| `verdict:` (vazio) | `[]` | `{}` |
| `verdict:` + `  - GO` | `['GO']` | `{}` |
| ausente | ausente | ausente |

Causa: `_release_tag_guard.py:219-221` (`if val == "": fields[key] = []`)
e `validate-pair-rail-verdict.py:112-114` (`else: out[k.strip()] = {}`).

O plano prescreve `verdict.get("verdict","")` (§W0 item 1). Se o código
fizer `.strip()` nesse retorno — o padrão de TODOS os leitores vizinhos
(`:232`, `:246`, `:316`) — levanta `AttributeError` não capturada. No
validador servidor isso sai **exit 1 = `EXIT_INFRA_ERROR`**
(`validate-pair-rail-verdict.py:84`), que o docstring `:60-61` descreve
como *"release.yml decides based on CEO_PAIR_RAIL_VERDICT_OPTIONAL"* —
o ramo com escape hatch. `CLAUDE.md` §4: *fail-open em INFRAESTRUTURA,
fail-closed em INPUT*; um campo de decisão malformado é INPUT.

**Cura exigida:** ler cru e type-checar EXPLICITAMENTE antes de comparar,
espelhando o precedente que já existe no mesmo arquivo para
`tool_versions` (`:447-455` type-check + `:456-461` coerção via `str()`):
valor não-`str` ⇒ `EXIT_VERDICT_INVALID` (3) / `E_DECISION`, nunca
exceção. Casos obrigatórios na regressão: `verdict:` vazio, `verdict:`
em forma de lista, campo ausente — nos DOIS validadores.

### M2 [P0] — rejeitar `verdict:` duplicado

Reproduzido: bloco com `verdict: NO-GO` seguido de `verdict: GO` retorna
`'GO'` nos DOIS parsers (last-wins: `_release_tag_guard.py:223`
`fields[key] = val`; `validate-pair-rail-verdict.py:111` `out[k.strip()] = v`).

Isto não é hipotético nem novo neste repo: a superfície irmã já carrega
exatamente esse controle — `OWNER-GA-CUT.sh:382-384` exige
`grep -cE '^VERDICT:' == 1` e morre com *"ambiguo (rail r11 P1-1)"*.
Um gate de decisão que lê a ÚLTIMA de N ocorrências não lê a decisão;
lê *uma* decisão. E a assimetria "o controle existe numa superfície só"
é a forma literal do P1-4 que estamos curando.

**Cura exigida:** contar ocorrências de `^verdict:` dentro do bloco
```yaml``` selecionado e rejeitar `!= 1`. Uma linha de `re.findall` em
cada validador; caso de teste com duas linhas `verdict:` (NO-GO depois
GO) obrigatório.

### M3 [P0] — pinar QUAL gate é o load-bearing, e provar isso estruturalmente

Verificado na cadeia:

- `release.yml:689` — `continue-on-error: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL == '1' }}`
  no step 15 ⇒ **com a var em `1`, o exit 3 do gate novo é engolido.**
- `release.yml:786-789` — o step "Verify verdict delta + ancestry" morre
  com `exit 1` quando a var == `1`, e não tem `continue-on-error`
  (comentário `:748-751` diz que é by design).
- `release.yml:851-853` — esse mesmo step invoca
  `python3 .claude/scripts/local/_release_tag_guard.py delta --repo . --tag "$TAG"`.
- `npm-publish.yml:105-124` + `:220` — `publish` tem
  `needs: await-release-gate`, que observa a CONCLUSÃO do job
  `release-gate` (não do run) e é fail-closed.

**Conclusão:** a fronteira fecha, mas não pela razão que o plano dá. Sob
`CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` o gate do validador NÃO sobrevive; o
release não sai porque o step delta morre antes. O gate que enforça a
decisão em TODOS os modos é o do `_release_tag_guard.py delta()`.

**Cura exigida:** (a) a AC-1 declara essa assimetria em uma frase (o
gate do validador é defesa em profundidade; o do tag guard é o
enforcement); (b) somar um assert estrutural de que o step delta continua
invocando `_release_tag_guard.py delta` — estender a classe W1B* de
`test_release_workflow_asserts.py` (que já pina o `continue-on-error`
único em `:769-787`), não criar um segundo lugar de verdade.

### M4 [P1] — W1: `--ceremony user` mantém o dano que o P1 nomeia

`verdict-ga-1.txt:5` é explícito: *"Fresh `--ceremony user` installs are
affected too because line 1860 skips the ignore setup"*, e a correção
mínima que ele propõe é um `.claude/.gitignore` com `/state/` e
`/settings.local.json`. O plano recusa isso (§W0 item 4 / Context) para
preservar paridade byte-a-byte com o `install.sh`, mantendo o gate
`CEREMONY != user` (`install.sh:1860`).

O gate está CERTO para WS4 — `$TARGET/.gitignore` é arquivo de raiz e um
install `--ceremony user` não cria arquivos de raiz. Mas a consequência é
que esses adopters continuam com `/night-mode on` produzindo
`.claude/settings.local.json` commit-elegível. Verifiquei: **`.claude/.gitignore`
não existe hoje** no repo, e vive DENTRO de `.claude/` — entregável sob
`--ceremony user` sem violar WS4. O caminho proposto pelo revisor é
viável e não colide com a decisão de paridade (é um arquivo diferente).

**Cura exigida — escolha uma, explicitamente:** (a) entregar
`.claude/.gitignore` nos dois caminhos para fechar o modo `user`; ou
(b) declarar o resíduo NOMEADAMENTE no plano e nas release notes como
limitação conhecida. O que não pode acontecer é a terceira opção
silenciosa. `verdict-ga-2.txt:5` — *"This is the prior
`repass-r2/verdict-c.txt:1` P1; its cure is incomplete"* — é o preço
documentado de curar 90% de um achado sem dizer qual 10% ficou.

### M5 [P1] — o varrimento do `INTEGRITY.md` está sub-escopado (mais 3 falsas, +1 no `install-npm.sh`)

O plano lista `:7-15, :23, :30-48, :95-102`. Fora dessas faixas,
verifiquei nesta sessão, no mesmo arquivo:

1. **§GPG key** — *"Project signing key fingerprint published in
   `docs/rotation-log.md` §NPM"*. Não existe §NPM com fingerprint: a
   única linha NPM do arquivo é `docs/rotation-log.md:24`, a
   aposentadoria do `NPM_TOKEN` (OIDC). Promessa falsa.
2. **§GPG key** — *"Public key distributed via ... `.well-known/gpg.asc`"*.
   Não existe diretório `.well-known/` no repo. Promessa falsa.
3. **§CI verification** — *"A new step in `validate.yml` asserts:"* seguido
   de um YAML com `SOURCE_DATE_EPOCH`. O step real do `validate.yml` é
   *"npm packlist gate"* (`.github/workflows/validate.yml:1030`) e não
   tem `SOURCE_DATE_EPOCH` (grep: zero ocorrências). Mecanismo citado
   não existe na forma descrita.
4. **Tabela Contract, linha 1** — coluna "Where enforced" diz
   `.github/workflows/validate.yml` **(to-add)**, dentro de uma tabela
   apresentada como *"Every release tarball MUST satisfy"*. Um "to-add"
   numa tabela de MUST é a classe inteira em uma célula.

E `scripts/install-npm.sh` são **duas** claims, não "3 linhas de
comentário": `:183-184` (*"CI verification (npm-publish.yml) computes the
checksum of the tarball it publishes and appends to the release notes"* —
falso) **e** `:186-190` (receita de consumidor `curl -LO .../SHA256SUMS.txt`
sobre um arquivo que não viaja no tarball — impossível).

**Cura exigida:** o varrimento é do ARQUIVO INTEIRO, não das faixas
enumeradas, e o pack W1 carrega `install-npm.sh:178-190` (o bloco), não
3 linhas.

### M6 [P1] — OQ-3: o gate "Where enforced ⇒ step existe", como escopado, não cobre a tabela

Responde diretamente à OQ-3: **como especificado, o gate é ao mesmo tempo
sub-escopado e frágil.** Sub-escopado porque a coluna "Where enforced"
aponta para `validate.yml` (linha 1) e para "Release operator" / "Release
script (Sprint 17 scope)" — não só para `npm-publish.yml`. Frágil porque
as células são PROSA (*"already passes `--provenance`; requires
`id-token: write` permission (already set)"*), e um parser de markdown
que extraia nome de step daí quebra na próxima edição de forma.

**Desenho robusto (inverter a direção — vocabulário fechado, não NLP):**
acrescentar à tabela uma coluna `Status` de conjunto FECHADO —
`enforced` | `deferred` | `operator` — e o gate:

- lê só as linhas `enforced`;
- exige que a célula nomeie um arquivo de workflow que EXISTE;
- exige que o nome do step venha em backticks e case **verbatim** com uma
  linha `- name:` daquele arquivo;
- falha se aparecer um Status fora do conjunto (fail-closed em
  vocabulário desconhecido — precedente: `feedback-closed-sets-must-be-derived-not-recalled`).

Assim a prosa fica numa coluna que o gate ignora, e o controle positivo é
trivial: marcar uma linha como `enforced` apontando um step inexistente
tem de virar vermelho.

## Nice-to-have

- **N1 (responde OQ-1): `E_DECISION = 13` novo, não reusar `E_VERDICT = 10`.**
  `E_VERDICT` é declarado como *"verdict unusable (missing file/field,
  wildcard, wrong tag, bad parent)"* (`_release_tag_guard.py:70`) — uma
  falha de FORMA. Recusa de decisão é semântica. Com código próprio, a
  regressão prova que o vermelho veio pelo motivo certo; com `10`
  reusado, um refactor futuro pode remover a checagem de decisão e
  manter o teste verde (vermelho por parent_sha ruim satisfaz o mesmo
  assert). No validador servidor, ao contrário, reusar
  `EXIT_VERDICT_INVALID = 3` é a escolha certa: `3` já é "release MUST
  stop" no docstring `:64-66` e um código novo exigiria tocar
  `release.yml`, que é canônico. Mantenha o prefixo `INVALID:` com um
  token distinto (ex.: `INVALID: verdict decision ...`) para o teste
  ancorar no motivo.
- **N2 (responde OQ-2): SIM, `install-npm.sh` entra no pack W1.** É uma
  claim de controle de integridade FALSA dentro de um script CANÔNICO;
  carregar isso como dívida declarada garante o re-encontro no próximo
  re-pass — que é literalmente como o P1-4 nasceu. O custo marginal de
  cerimônia é zero (mesmo sentinel, mesmo pack). Ver M5: são `:178-190`.
- **N3:** a mensagem de erro deve imprimir o CONJUNTO ACEITO literalmente.
  Confirmei que `verdict: go` (minúsculo) é rejeitado sob igualdade exata
  — correto, e eu manteria assim — mas o Owner descobre isso no momento
  da tag. `INVALID: verdict decision 'go' not in {GO, GO-WITH-CONDITIONS}`
  transforma um abort de cerimônia em uma correção de 10 segundos.
- **N4 (R-S6):** o cabeçalho do `OWNER-GA-CUT.sh:12` diz *"exige VERDICT:
  GO ou GO-WITH-CONDITIONS"*, e o código `:387-389` aceita **só**
  `VERDICT: GO` exato. É a mesma classe doc-vs-mecanismo que estamos
  curando, no script que o Owner vai rodar para cortar o GA — e rc.2/rc.3
  voltaram ambos `GO-WITH-CONDITIONS`, então isso VAI ser tocado.
  Corrigir o comentário ou nomear no runbook do W2.
- **N5:** o censo R-4 confere — 10 envelopes vivos + template = 11, todos
  `GO`/`GO-WITH-CONDITIONS`, campo sempre presente. Nenhum histórico
  quebra. O template (`pair-rail-verdict-template.md:13`) é rejeitado
  pelo gate novo, que é o comportamento correto.

## Unseen

- **U1 — a armadilha substring é pior do que "3× na S299", e o template a
  arma.** O conjunto autoritativo mora numa ÚNICA string:
  `pair-rail-verdict-template.md:13` = `verdict: GO | NO-GO | GO-WITH-CONDITIONS`.
  Medido: `startswith("GO")` sobre essa string ⇒ **True**; `"GO" in value`
  ⇒ **True**. E, pior, `"GO" in "NO-GO"` ⇒ **True**. Ou seja, uma checagem
  por substring aceitaria o template não preenchido *e* um `NO-GO`
  literal. Igualdade exata aqui não é preferência de estilo — é a única
  forma que funciona. (Isto SUSTENTA a decisão do plano; registro porque
  a próxima pessoa a "simplificar" esse if precisa ler isto.)
- **U2 — o que realmente prende o envelope não é o `inputs_hash`.** O
  `inputs_hash` é computado sobre o manifesto de scripts de gate
  (`compute_inputs_hash`, `validate-pair-rail-verdict.py:122-142`), **não
  sobre o arquivo do verdito**; e `gpg_signature` é checado só por
  PRESENÇA não-vazia (`:499-502`, cujo próprio comentário diz que a
  verificação real é o `git verify-tag` em outro lugar — que existe:
  `release.yml:639` e `gh release create --verify-tag` em `:961`). Logo o
  único vínculo criptográfico sobre a STRING da decisão é a assinatura do
  Owner sobre a ÁRVORE TAGGEADA. Isso responde a pergunta do fixture: um
  verdito temporário auto-consistente em `/tmp` **nunca** vira bypass,
  porque nada dele alcança a árvore assinada — forjar um envelope real
  exige a chave do Owner ou um push em main + tag assinada. Recomendo uma
  frase no threat-model do plano dizendo isso, porque o texto atual
  (R-1) raciocina sobre `inputs_hash` como se ele prendesse o envelope.
- **U3 — R-1 tem uma consequência de SEQUÊNCIA que o plano não tira.**
  Como a cura muda o `inputs_hash` e o envelope o declara, **nenhum path
  do `pair-rail-inputs-hash-manifest.txt` pode ser tocado depois do
  envelope assinado** — senão o step 15 devolve 3 no momento da tag.
  Isso ordena o W2 mais forte do que "verdito → push → CI → preflight →
  tag": o envelope é a ÚLTIMA escrita antes da tag. (Responde OQ-4: não
  vejo furo na ordem herdada do 166; vejo esta precondição a mais.)
- **U4 — dois consumidores, dois parsers, formas divergentes para o MESMO
  input.** O docstring de `_parse_verdict` (`_release_tag_guard.py:190-198`)
  se declara o leitor de referência e adverte *"never grow a third parser
  of the same signed file"*. Não estamos criando um terceiro parser, mas
  estamos criando um segundo CONSUMIDOR do mesmo campo em dois leitores
  cujas formas para o mesmo input malformado **divergem** (`[]` vs `{}`,
  medido). Mitigação barata: o conjunto aceito e o texto do erro devem
  ser literalmente idênticos nos dois arquivos, com um teste que afirma
  que os dois carregam a mesma tupla. Sem isso, a próxima edição
  diverge em um só lado — que é o padrão de falha deste repo.
- **U5 — W1 muda o contrato do `.gitignore` de "install-once" para
  "upgrade-repetido"** (R-S4). A idempotência por linha
  (`install.sh:1845-1847`) significa que remover deliberadamente
  `.claude/state/` é revertido em todo upgrade. Decidir explicitamente:
  ou a chave de idempotência é o MARCADOR do bloco (`# PLAN-165 CX-3`) —
  presente ⇒ não re-anexa, respeitando a remoção do adopter — ou o
  comportamento atual é documentado como intencional. Com a allowlist
  removida, o e2e de paridade passa a ser o único observador desse
  contrato; ele mede parity install↔upgrade, não "o adopter removeu".

## What I would NOT change

- **Igualdade exata, sem normalização de caixa, sem `startswith`.** U1
  prova empiricamente por que qualquer relaxamento aceita `NO-GO`.
- **Os DOIS validadores, não um.** O P1-4 é uma re-descoberta justamente
  porque a cura anterior cobriu uma superfície só
  (`OWNER-GA-CUT.sh:349-363`). Curar uma agora repetiria o erro em
  escala menor.
- **Não unificar a semântica com o `OWNER-GA-CUT.sh`.** O gate humano ser
  MAIS estrito (só `GO` exato) é a direção segura da assimetria. Unificar
  só pode afrouxar um dos dois.
- **`release.sh` intocado.** `tag()` já invoca o guard com `|| die`
  (`:622-631`); um terceiro sítio de decisão seria um terceiro lugar para
  divergir.
- **Rota (i) do P1-3 FORA da rc.4.** Implementar geração+verificação de
  checksum de tarball é uma sub-feature nova no caminho de publish,
  não-verificável sem cortar tag, durante uma janela de release aberta.
  Honestidade documentada agora + mecanismo no trem v1.4.0 é a ordem
  correta de risco. (E é a metade que o revisor explicitamente ofereceu:
  *"either implement ... or remove the 'enforced today' guarantee"*,
  `verdict-ga-1.txt:19`.)
- **Não wirar `.github/scripts/tests/` na rc.4, e NUNCA pôr a regressão
  lá.** É KERNEL (`validate.yml`) e a suíte nunca rodou; um teste novo
  numa suíte morta seria a instância 17 da classe dentro da própria cura.
- **Remover a allowlist do `_parity_classify.py` no MESMO commit da cura.**
  Entry órfã = MANDATORY-FIRE; separar os dois abriria uma janela em que
  o gate volta a allowlistar o defeito curado.
- **Escopo fechado da rc.4** (perf/node24/W3-W4 fora). Cada superfície a
  mais é superfície de re-pass, e o re-pass é o gate que já disse NO-GO
  duas vezes.
