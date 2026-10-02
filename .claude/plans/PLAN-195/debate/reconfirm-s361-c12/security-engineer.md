---
plan: PLAN-195
ceremony: reconfirm-s361-c12
archetype: Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (auth/crypto VETO holder)
subject_sha256: 93e4b83f4fd4fa848385f1cb0e92b610226588e468fbc7e8f3f3ce13adda5379
base_sha256: e05f5f3f5d11c7910509bcbeb34255bb00295675198b2a6441896d8b0d4067d3
generated_at: 2026-10-02T08:41:10Z
veto: RETIRADO-MANTIDO
w0_round2_verdict: REQUEST-CHANGES
p0_found: false
---

> **Regra de divulgação respeitada.** Nenhuma linha deste registro funciona como desvio: as
> formas aparecem em prosa, sem string concreta, e a matriz privada não foi lida. Siglas:
> `cbs` = `.claude/hooks/check_bash_safety.py`; `cce` = `.claude/hooks/check_canonical_edit.py`;
> `fz` = `.claude/hooks/check_bash_canonical_forensic.py`. Os três são byte-iguais no `main`
> (`f829b29a`) e na sombra (sha256 de `cbs` e `cce` conferidos nos dois lados). Nenhum comando
> destrutivo, de escrita ou da classe indireta foi executado nem simulado; nenhum git de escrita.

## 1. Sujeito e conferência do sha

- Sombra (`…/shadows/b7-195w0/wt`, HEAD `399efbaa` + árvore suja), plano: `shasum -a 256` =
  `93e4b83f4fd4fa848385f1cb0e92b610226588e468fbc7e8f3f3ce13adda5379`. **Este é o sujeito.**
- `main` (`f829b29a`), plano: `e05f5f3f5d11c7910509bcbeb34255bb00295675198b2a6441896d8b0d4067d3`
  (igual no arquivo e em `git show f829b29a:<plano>`).
- Cadeia desde a minha retirada anterior (`c8cec366…a1ff`, commit `6a9abb10`):
  `6fa9aa40` → `89a406be…`, `304ec478` → `e05f5f3f…`. Diff integral `6a9abb10..304ec478`
  (16+/6−): `external_wait`, nota do checkbox do debate, entrada do histórico e o texto do C11
  passando de PENDENTE a REGISTRADA. Tudo está na lista «não reabrem» do meu registro
  `reconfirm-s361/security-engineer.md` §5.6 (status, histórico, incorporação das condições).
  - P2-nit: o C11 parafraseia a minha P1 omitindo a perna do meio («transição da exceção em que
    o comando, como um todo, faz edição canônica»). Como o C11 incorpora os dois arquivos
    «como se estivessem escritos aqui» e o «inclusive» não é exaustivo, a condição inteira vale;
    o arquivo de registro é a fonte.

## 2. O que mudou (`git diff --no-index` main × sombra, 20 linhas, só adições)

- Goal, depois do item 12: a remissão «→ item C12: resíduo 13.»
- Apêndice: o item C12 (resíduo 13 = destino literal não byte-igual à grafia da guarda:
  variante de grafia e apelido no sistema de arquivos; fica residual, não escopo da W2; a W2
  decide na abertura se traz a metade de grafia; fonte única passa a «Goal + C12»; §6.6 da W0
  com 13 itens; exige reconfirmação dos dois portadores).
- Nada mais mudou: Thesis, escopos de W1a/W1b/W1c/W2, OQ-8/9/10, Prova, Divulgação e regra de
  parada estão byte a byte iguais ao `e05f5f3f`.

## 3. Conferência das âncoras do C12 no código

| Âncora | O que o C12 afirma | O que o disco mostra | Veredito |
|---|---|---|---|
| `cbs:2222-2240` | O E3 normaliza só o `./` inicial e o caminho absoluto sob a raiz. | `_is_canonical` interno do E3: tira um `./` inicial; para caminho absoluto, `normpath` só-texto e prefixo da raiz comparado com caixa. Caminho relativo não passa por `normpath`; caixa nunca é dobrada. | **Verdadeiro.** |
| `cce:949-985` | A guarda casa por segmento, com caixa. | `_fnmatch_segments`/`_match_segments` com `fnmatch.fnmatchcase`. É a função que o E3 importa (`cbs:2216`) junto com `_CANONICAL_GUARDS` CRU. | **Verdadeiro para o que o E3 chama.** Ver P2-b abaixo. |
| `cbs:2531-2534` | O apelido só se resolve com chamada ao sistema de arquivos, que o próprio arquivo recusa. | A recusa registrada é a da «metade de EXECUÇÃO» do E4 (toggle), com três motivos: syscall no orçamento do hook, `RuntimeError` em laço de link (classe fail-open), janela TOCTOU. Os motivos valem igualmente para o E3. | **Verdadeiro para o USO de um apelido pré-existente; incompleto para a CRIAÇÃO** (P2-a). |

Fatos adicionais do disco, relevantes para a decisão:

1. **A metade de grafia tem precedente só-texto no MESMO arquivo e no módulo da guarda.** O E4
   compara o caminho do toggle com `normpath(...).lower()` (`cbs:3123`; nota de caixa em
   `cbs:2544-2558`). O classificador do Edit/Write dobra caixa (`cce:866-917`, PLAN162_FIX_CASEFOLD,
   marcado P0 nos dois rails que o usam) e resolve o caminho (`cce:821-863`). O E3 é o único
   consumidor de `_CANONICAL_GUARDS` que não dobra caixa. A classe «variante de caixa em casamento
   de caminho protegido» já ocorreu duas vezes (PLAN-162 S1 no Edit/Write e no kernel; Codex S292
   P1-A no E4). Esta seria a terceira.
2. **A criação de apelido por executor de link é visível no texto.** O E3 trata o executor de
   link como COPY e checa só o caminho de destino (`cbs:2037`, `:2361-2374`); a origem é tratada
   como leitura. O E4 já recusa, por string, criar link que nomeia o toggle nas duas posições de
   operando (`cbs:3777-3787`; justificativa em `cbs:2846-2862`). Para os demais caminhos
   canônicos essa recusa não existe.
3. **O hook forense classifica com o classificador do Edit/Write.** `fz:63-69` chama
   `cce._is_canonical`, que dobra caixa e resolve o caminho (seguindo link). Logo, um alvo
   literal com outra grafia ou apelido de link simbólico, escrito por uma das quatro formas
   literais do forense, deixa o breadcrumb `canonical_edit_completed` depois do fato (sem
   bloquear). Evidência de teste da dobra: `test_canonical_edit_plan162_findings.py:514-536`.

## 4. Decisão do VETO

**VETO: RETIRADO MANTIDO** sobre o sha256 `93e4b83f…5379`, com as condições novas abaixo.

**Tratar a subclasse como resíduo declarado, em vez de escopo da W2, é aceitável no meu
escopo?** Sim para a metade que exige resolver o sistema de arquivos. Para as duas metades
só-texto, sim **só como declaração provisória**, com a condição P1 abaixo. Motivos para não
levantar o VETO:
- o Goal promete **elevar o custo**, não fechar fronteira; o resíduo 2 (script em arquivo) já
  dá um caminho de custo equivalente, declarado;
- a lacuna fica **declarada pela forma** no Goal (via C12), na §6.6 e no vetor 2 do doc de
  ameaças: não há afirmação de cobertura no sentido inseguro;
- a W1 deixa o E3 byte-idêntico, então nada do que a W1 faz depende desta decisão;
- a condição é aplicável na abertura da W2 sem reescrever o escopo pré-registrado.

Condições:

- **P1-C12 — W2: as metades só-texto do resíduo 13 entram por padrão.** Na abertura da W2
  (ou da W2a/W2b dona do E3), o pacote decide as duas metades com padrão **INCLUIR**:
  - (a) **grafia**: normalização só-texto do alvo literal (dobra de caixa ASCII com `lower`,
    como o PLAN162_FIX_CASEFOLD; colapso de segmentos redundantes também para caminho
    relativo, ancorado na raiz), sempre ACRESCENTANDO candidatos e nunca trocando o original,
    para que só possa adicionar casamentos;
  - (b) **criação de apelido**: o executor de link cujo operando de origem é caminho canônico
    é recusado, no molde do E4 (`cbs:3777-3787`).
  - Excluir qualquer das duas exige motivo registrado no pacote (por exemplo, falso-positivo
    medido no replay da OQ-1) **e** um FU nomeado `PLAN-195-FOLLOWUP-<slug>`, como os resíduos
    11 e 12 têm.
  - Se a W2 trouxer alguma metade, o mesmo pacote atualiza o item 13 da §6.6 e da ADR-201.
  - Fica residual sem condição só o **USO** de um apelido pré-existente (link simbólico ou
    físico criado fora do Bash ou em sessão anterior), pelos motivos de `cbs:2531-2534`.
  - Estas transições são ALLOW→BLOCK: entram na prova (i) como bloqueio novo, nunca na exceção
    BLOCK→ALLOW da W2.
- **P2-a — precisão do C12 (apelido).** A frase «o apelido só se resolve com chamada ao
  sistema de arquivos dentro do hook» vale para o USO de um apelido existente; a CRIAÇÃO por
  executor de link é visível no texto. A recusa citada (`cbs:2531-2534`) é a do E4, cujos
  motivos valem igualmente para o E3. Incorporar esta precisão literalmente não reabre.
- **P2-b — precisão do C12 (guarda).** «A guarda casa com caixa» é exato para a função que o E3
  chama (`cce:949-985`); o classificador do Edit/Write e o hook forense dobram caixa e resolvem
  o caminho (`cce:821-863`, `:898-917`). A diferença sustenta a P1-C12 (a cura de caixa já existe
  no módulo) e a P1 da W0 abaixo.

Continuam valendo todas as condições de `reconfirm-s361/security-engineer.md` §5 (as quatro da
rodada 2; W1-ADR e o evento de desarme; prova (k); limite da EXPRESSÃO do verbo de busca na W2;
a P1 do C7 × W2 e as cinco P2).

**Escopo desta retirada.**
- Vale para o sha256 `93e4b83f…5379` e não cobre a reconfirmação do Threat Detection Engineer.
- Não a reabrem: marcar checkbox, mudar status ou histórico, incorporar literalmente (ou de
  forma mais estrita) estas condições, e corrigir a W0 (docs fora do plano).
- Qualquer outra edição na Thesis, no Goal, nos escopos de W1a/W1b/W1c/W2, nas OQ-8/9/10, na
  Prova, na Divulgação, na regra de parada ou no texto do C12 além das precisões P2-a/P2-b
  exige nova reconfirmação por diff.

## 5. W0 — rodada 2 do refutador de segurança

Sujeito: `git -C <sombra> diff` de `docs/security-bash-canonical-guards.md` (213 linhas) e
`docs/threat-model.md` (16 linhas). Linhas abaixo = linhas na sombra.

### 5.1 Curas da rodada 1

| Achado r1 | Cura | Conferência no disco | Estado |
|---|---|---|---|
| P1 — falta a subclasse de grafia | §1.2 (`:56-59`), intro da §6 (`:247`), Classe B da §6.6 (`:301-310`), resíduo 13 (`:333`), vetor 2 do doc de ameaças (`:2143`) | Âncoras `cbs:2222-2240` e `cce:949-985` verdadeiras (§3). | **Curada**, mas abriu a P1 nova da §5.2. |
| P2 — «Direct sibling forms» | Parágrafo `:292-299` | `cbs:275` (separação em `&&`, `||`, `;`, `|`), `cbs:107` (quatro prefixos lançadores), trio com posições fixas e comparação com caixa (`cbs:364-465`; `:458`). Recheck só-topo em falha de parse (`cbs:587-608`), sem recursão. | **Curada.** Pela forma: categorias, nenhum token. |
| P2 — contadores 16 de 19 | §1 `:36-37`, §3 `:107-108`, §5 `:212` | `_ADVISORY_ROWS = {17, 18, 34}` (`test_check_bash_safety_canonical_matrix.py:122`); docstring do teste: 15 de 19 na Wave B.3 + linha 33 na S207; linha 19 dobrada no R2 da Wave B (`cbs:2157-2161`). 15 + 16 = 31. | **Curada.** |
| P2 — léxico da §2 | `:65-79` | `shlex.shlex(posix=True, punctuation_chars=…)` + `whitespace_split` (`cbs:2190-2192`); três fail-closed: lexer (`:2193-2208`), corpo não tokenizável e teto de 16 KiB (`:2307-2315`); fail-open do import (`:2214-2218`); `main()` fail-open (`:4227-4233`); forense devolve `False` em falha (`fz:63-69`). | **Curada.** |
| P2 — `wave-b-audit.md` inexistente | `:12`, `:112-113`, `:352`, `:419` | «Not in the public tree»: verdadeiro (`git log --all` vazio no repo público). «Archived»: **não verificável**; o arquivo não está no repo público, no histórico dele nem no arquivo privado local. | **Parcial** — P2 abaixo. |
| P2 — vetor 7 | `threat-model.md:2148` + nota `:46-56` | Ponteiro para a Classe A e declaração honesta de que o vetor 7 não foi re-revisado. | **Curada**, com P2-nit abaixo. |

### 5.2 Achados novos

- **P1 — afirmação falsa de detecção (aberta pela cura da P1 r1).** Ao pôr o alvo literal
  com outra grafia DENTRO da Classe B, três frases passaram a afirmar que nada além do
  `PreToolUse` observa essa subclasse:
  - `docs/security-bash-canonical-guards.md:216-219` («It does not observe … the §6.6 class»);
  - `docs/security-bash-canonical-guards.md:312-313` («For classes A and B the `PreToolUse`
    matcher is the only detection»);
  - `docs/threat-model.md:2143` («PreToolUse is the only detection and has no rule for it»;
    coluna Owner «NONE for the §6.6 class»).

  O disco desmente a parte da grafia e do apelido simbólico. O forense classifica o alvo pelo
  classificador do Edit/Write (`fz:63-69` → `cce._is_canonical`), que dobra caixa e resolve o
  caminho (`cce:821-863`, `:898-917`). Um alvo literal com outra grafia, ou um link simbólico
  criado antes, escrito por uma das quatro formas literais do forense, deixa o breadcrumb depois
  do fato. A afirmação continua verdadeira para o alvo COMPUTADO e para a Classe A.

  O erro está no sentido conservador (subestima), por isso não é P0. Mas é afirmação falsa num
  doc cuja função na W0 é descrever a cobertura REAL, e esconde do analista um canal de
  detecção que existe.
  - **Cura, pela forma:** nos três sítios, restringir o «only detection» ao alvo computado e à
    Classe A, e acrescentar que um alvo literal com outra grafia, ou um apelido simbólico, só
    deixa rastro forense (sem bloqueio) nas quatro formas literais da §5, porque o forense
    classifica pelo classificador do Edit/Write.
  - No vetor 2, a coluna Owner passa a dizer, por exemplo: «NONE preventive for the §6.6 class;
    forensic breadcrumb only for a respelled literal in the four §5 shapes».
  - Nenhuma string concreta é necessária. Que o forense só vê quatro formas já está publicado.
- **P2 — «archived» não verificável** (`:12`, `:112-113`, `:352`, `:419`). Trocar por «not in
  the public tree» ou «not published». Não afirmar arquivamento sem localizar o arquivo.
- **P2 — «the guard matches … case-sensitively»** (`:306-308`). Exato para a função que o E3
  chama, ambíguo para «a guarda» em geral: o Edit/Write e o forense dobram caixa. Escrever «the
  segment matcher E3 calls» (ou equivalente). Resolve junto com a P1.
- **P2-nit — vetor 7** (`threat-model.md:2148`). «direct spelling only — indirect forms: §6.6
  Class A»: a Classe A também abriga as formas diretas irmãs, que não são indiretas. Sugestão:
  «canonical spelling only — other forms: §6.6 Class A».
- **P2-nit — `_scan_blob` «recurses into bodies»** (`:290`). Ele olha UM nível (uma tokenização
  e uma varredura de substring; `cbs:2304-2329`) e não re-tokeniza. Em efeito, a substring cobre
  qualquer profundidade para literal exato. Sugestão: «inspects bodies».
- **P2-nit — prefácio dos residuais** (`:318`, «stay open even after the planned cure»).
  Coerente hoje; se a W2 trouxer metade do item 13 (P1-C12), o item 13 muda no mesmo pacote.

### 5.3 Critério de receita de contorno

**Nenhum trecho funciona como receita.** As linhas que antes traziam comandos concretos para as
linhas 17, 18 e 34 da matriz e para o vetor da §6.4 saíram; as §6.1-6.5 e a §6.6 ficaram pela
forma. O parágrafo «Direct sibling forms» é o mais granular: enumera dimensões (separador,
agrupamento, palavra reservada, lançador, caixa, ordem de opção, divergência de tokenizador),
não tokens, e o hook é público. Fica no limite aceito pela regra «pela FORMA». A cura da P1
acima também não precisa de string concreta.

### 5.4 Bateria observada (artefatos da sombra; não reexecutada)

- O check da W0: `### §6.6 ` presente (1) e as três âncoras falsas ausentes (`grep -nF` rc 1).
- Freshness `--dry-run --verbose`: saída byte-igual à do baseline (`cmp`), e `Status` e
  `Last updated` do doc de ameaças intocados no diff.
- `test_threat_model_coverage`: 22 passed.

**Veredito W0 rodada 2: REQUEST-CHANGES** (uma P1 nova, de cura textual curta; nenhum P0).

VETO: RETIRADO MANTIDO (sha256 93e4b83f…5379), com P1-C12 para a abertura da W2.
