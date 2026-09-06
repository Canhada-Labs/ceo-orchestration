---
round: 2
archetype: Principal Security Engineer
skill: security-and-auth
agent_persona: (crítico de trust boundaries, autenticação de gates e supply chain; perfil da linha do SKILL MAP)
generated_at: 2026-09-06T03:20:00Z
---

## Verdict

ADJUST — **3 bloqueantes** (R-SEC1, R-SEC2, R-SEC3).

## Summary (≤ 3 bullets)

- Os 15 must-fix do round 1 estão TEXTUALMENTE fechados: verifiquei em disco
  cada cifra que o arquivo revisado cita e **todas batem** — `= 9` no manifesto
  ADR-192, `33`/`48` nos clones com `sentinel-signers`, `0` para
  `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'`, o sha256 do instrumento
  (`d2234bdf…181062`, `shasum -a 256` no HEAD), `:194` do R8, ADR-192 §4
  superfícies, `validate.yml:354` com a exclusão morta. Nada de prosa passando
  por medida.
- **Onde é forte:** a invariante 10 escolheu a raiz de confiança CERTA —
  `.claude/sentinel-signers.txt` é KERNEL-guarded (`check_arbitration_kernel.py:145`,
  vetor (12) «allowlist injection»), logo consolidar 33 checagens nela não cria
  ponto único forjável. E o §Riscos:326-336 declara honestamente que ADR-192 é
  DETECÇÃO post-hoc, não prevenção.
- **Onde é fraco:** os quatro «sítios de gate» da W0 põem a autoridade sobre o
  toolkit em arquivos com proteção ASSIMÉTRICA, e a descoberta do lint é por
  CONTEÚDO e só `.sh` — de modo que o controle positivo que o plano propõe
  passa enquanto os arquivos que importam escapam. É a forma «verificação que um
  arquivo transplantado satisfaria».

## Risks

### R-SEC1 — P1 (BLOCKING) — a descoberta do lint é por CONTEÚDO e só `.sh`: o leitor fail-closed do manifesto NUNCA será descoberto, e o controle positivo do plano não detecta isso

`check-ceremony-script.py:137` faz `if not fn.endswith(".sh"): continue` e
`:146` só aceita o arquivo se `SHEBANG_RE.match(body) and
CEREMONY_OPS_RE.search(body)` (`:71-73`: `gpg|git tag|gh release|npm
publish|sentinel|approved\.md|VERDICT`). Consequências, ambas contra o texto do
plano:

1. `.claude/scripts/ceremony/read_manifest.py` — o parser fail-CLOSED que o
   `sign.sh` invoca, isto é, o ponto onde entrada não confiável entra na
   cerimônia — é `.py`: entrar em `DISCOVERY_ROOTS` **não o torna
   descobrível**. O AC-1 (`PLAN-188-shared-ceremony-toolkit.md:459`) afirma «o
   `check-ceremony-script.py` DESCOBRE os scripts do toolkit» sem essa
   ressalva, e §Approach:126-133 vende os três sítios como a cura completa do
   falso-verde por endereço.
2. `lib.sh` só é descoberto se o seu corpo casar `CEREMONY_OPS_RE`. Uma
   biblioteca de predicados sobre arquivos (que é exatamente o que o §Items:369
   promete: «invariantes 1, 3, 4, 5 e 10, todas predicados sobre ARQUIVOS») pode
   não conter nenhum daqueles tokens e sair do conjunto descoberto em silêncio.
3. O controle POSITIVO escolhido — «um script do toolkit com `|| true` numa
   linha de `gpg` REPROVA (R2)» (:134-135, :460-462) — contém `gpg`, logo casa
   `CEREMONY_OPS_RE` por construção. Ele prova que a raiz foi adicionada; **não
   prova que os arquivos entregues são vistos**. Verde por fixture.

**Correção mínima:** o AC-1 (W0) exige que o Check imprima o CONJUNTO
descoberto (`--list` já existe, `ceremony-lint.yml:47`) e afirme, arquivo a
arquivo, que cada entregável da W0 está nele; e o plano decide o que faz com
`read_manifest.py` (estender a descoberta a `.py`, ou declarar que o parser fica
fora do lint e nomear o gate que o cobre).

### R-SEC2 — P1 (BLOCKING) — a autoridade do lint mora em dois arquivos canonical=0 e kernel=0, um deles um allowlist por DIGEST com override de CLI

Medido nesta árvore (oráculo `check_canonical_edit.py --is-canonical`, e
membresia kernel por `fnmatch` contra `_KERNEL_PATHS`):

```
.claude/scripts/check-ceremony-script.py     canonical=0   kernel=0
.claude/scripts/ceremony-lint-waivers.json   canonical=0   kernel=0
.github/workflows/ceremony-lint.yml          canonical=1
.github/workflows/smoke-install.yml          canonical=1
.claude/governance/gate-scripts-manifest.txt canonical=1
```

O plano trata os «quatro sítios» como um bloco homogêneo (§Items:352-368) e
conclui que com eles «um toolkit alterado fora de cerimônia fica VISÍVEL»
(§Riscos:323-325). Mas dois dos quatro são livres:

- `check-ceremony-script.py` **contém** `DISCOVERY_ROOTS` e o escopo do R8. Um
  Edit livre remove `.claude/scripts/ceremony` da lista e desarma a cura do C1
  sem tocar em nenhum path canônico. O gate que decide se o gate da assinatura é
  auditado é editável sem cerimônia — e ele **não está** no manifesto ADR-192
  (conferido: os 9 membros são `verify-counts.sh`, `validate-governance.sh`,
  `_release_tag_guard.py`, `check-canonical-doc-freshness.py`,
  `ownership-nightly-gate.sh`, `ownership-expected-reds.txt`, `release.sh`,
  `validate-pair-rail-verdict.py`, `await_release_gate.py`).
- `ceremony-lint-waivers.json` é uma **isenção por digest**: `:297` monta
  `waived_shas` do conteúdo e o waiver anula achados BLOCKING. Append de uma
  entrada com o sha256 do `sign.sh` entregue isenta o toolkit das cinco classes
  que o C1 existe para aplicar. Pior, `:261-262` expõe `--waivers <path>`: um
  invocador escolhe o arquivo de isenções.

**Correção mínima:** o AC-6 deixa de ser «os scripts de gate do toolkit» e passa
a incluir `check-ceremony-script.py` e `ceremony-lint-waivers.json` no manifesto
ADR-192 (ou a OQ-6 os nomeia explicitamente), e o plano declara que um waiver
para path sob `.claude/scripts/ceremony/**` é RECUSA nomeada — a única forma de
não converter «gate novo» em «isenção nova».

### R-SEC3 — P1 (BLOCKING) — a invariante 3 troca um literal de máquina por uma isenção que o próprio material pode carregar

A cura do C7 (§Approach:236-240) diz: «o próprio self-test injeta um MARCADOR
(**variável de ambiente do harness, ou sentinela de conteúdo no fixture**) e o
guard isenta o MARCADOR, não um path». As duas alternativas não são
equivalentes, e uma delas é pior que o literal que substituiu:

- **sentinela de conteúdo no fixture:** o guard de path absoluto roda sobre o
  MATERIAL ASSINADO. Se a isenção é uma string no conteúdo, então quem controla
  o material controla a isenção — o material que carrega o path pessoal carrega
  também o passe. Isenção por NOME, dentro do próprio objeto verificado.
- **variável de ambiente:** herdada por qualquer processo; nada distingue o
  harness do `sign.sh` que o Owner roda na mesma sessão. O repo já pagou essa
  classe (`WHOLE_DIR_OVERRIDE_CARRIERS`, CLAUDE.md §5: carrier de maior
  precedência neutralizado NO IMPORT).

A superfície é a que o próprio plano chama de mais cara (material assinado), e a
invariante 3 é uma das cinco que a W0 tem de falsificar sozinha (§Items:369-370)
— ou seja, isso é decisão da W0, não de wave futura.

**Correção mínima:** o plano ESCOLHE um dos dois braços e escreve por que ele
não é forjável pelo material (p. ex. o guard só isenta quando o alvo está sob um
diretório passado por argumento explícito do runner E o processo não é o
`sign.sh`), com controle vermelho: material com o marcador, fora do self-test,
tem de REPROVAR. Como está, o controle vermelho descrito (:239-240) prova o
contrário do que precisa.

### R-SEC4 — P2 — o alargamento do R8 contradiz a razão escrita do próprio R8, e o plano não a reconcilia

`check-ceremony-script.py:192-194` escopa o R8 a `.claude/plans/` com a razão
literal: «R8 só na superfície de binding assinado (`.claude/plans/`): exec-bit
em ferramenta de `scripts/local/` é legítimo (invocada diretamente)». O
§Approach:129-133 alarga o R8 ao toolkit — que é, por desenho, ferramenta
invocada diretamente pelo Owner. O plano nem afirma que os scripts serão
chamados por `bash <script>` (o que tornaria o exec-bit dispensável) nem discute
a razão que está no código. Risco operacional concreto: a W0 entrega um lint que
reprova o próprio toolkit se alguém der `chmod +x`, e a rota de recuperação
seria… um waiver (R-SEC2).

### R-SEC5 — P2 — a W0 é declarada «canônica por DOIS paths», mas o patch inclui um terceiro arquivo de gate que não é canônico: o pacote mistura camadas de autorização

§Items:352-358 conclui «canônico por DOIS paths» a partir de
`ceremony-lint.yml` = 1 e `smoke-install.yml` = 1. Correto quanto ao oráculo,
mas a consequência prática é que o `Scope:` do sentinel da W0 cobrirá os dois
workflows enquanto `check-ceremony-script.py` entra como edição livre no mesmo
commit assinado. O `land.sh`/`OWNER-*` desta casa checa `touched − scope = ∅`
(CLAUDE.md §5, S321): um path livre no mesmo commit não viola a regra, mas o
Owner assina um sentinel que NÃO nomeia o arquivo que carrega a decisão de
descoberta. Peça ao plano uma frase: o `Scope:` da W0 nomeia os três arquivos de
gate, canônicos ou não, para que a assinatura cubra a decisão inteira.

### R-SEC6 — P3 — `--waivers` e o step de sumário leem o mesmo JSON sem tratamento de erro simétrico

`ceremony-lint.yml:52-57` faz `json.load` do waivers sem `try`, num step
`if: always()`; o lint em si (`:300-301`) é fail-closed em waivers ilegíveis
(«nenhum waiver aplicado»), o que está certo. Divergência menor, mas o plano
acrescenta paths a esse workflow e vale registrar que o step de sumário quebra
onde o gate segue verde — ruído que confunde diagnóstico de gate.

## Dependências e claims verificadas (nenhum P1 aqui — registro para o síntese)

- Invariante 10: `.claude/sentinel-signers.txt` é KERNEL
  (`check_arbitration_kernel.py:145`, vetor (12)) — **não** é ponto único
  forjável. A raiz gêmea da ADR-121
  (`.claude/security/sentinel-signers-registry.yaml`) é canonical **e** kernel
  (`check_canonical_edit.py:365`, `check_arbitration_kernel.py:293`). A escolha
  do plano é a certa; sugiro só que a invariante 10 nomeie o rail DUPLO
  (`check_canonical_edit.py:1392-1396`: legado + registry, qualquer um recusando
  ⇒ fail-CLOSED), para que o `lib.sh` não implemente metade.
- ADR-192 §4 superfícies e o step `smoke-install.yml:355-362` (`shasum -a 256
  -c`, fail-loud) conferem com o texto do plano, inclusive o limite «não existe
  lançador LOCAL que confira o hash antes de executar».
- `check_contamination.py:296-301` / `:318-326` isentam `owner-ceremony/*`,
  `scripts/local/historical/*`, `.claude/scripts/local/*`, `OWNER-*.sh` e
  `archive/*`. Nota FAVORÁVEL ao plano que ele não faz: mover a cerimônia para
  `.claude/scripts/ceremony/` **retira** o toolkit dessas isenções, então o scan
  de contaminação passa a olhá-lo — ganho real, vale escrever.
- `generate-ceremony.sh:6-7` e `:19-30` (G1-G6), `test_generate_ceremony.sh:21`
  (`GEN=`) e `PLAN-174:98` (W3 que estende o gerador) existem como citados; a
  decisão ABSORVER com consumidores nomeados fecha K1.

## O que falta antes de executar (OQs)

Não re-litigo OQ-1..OQ-9. **Uma decisão que o plano precisa ANTES da W0 e que
nenhuma OQ cobre:** a proteção de `check-ceremony-script.py` e de
`ceremony-lint-waivers.json` (R-SEC2). A OQ-6 pergunta pelo toolkit em
`_CANONICAL_GUARDS`; ninguém pergunta pelo LINT e pelo seu arquivo de isenções,
que é onde a cura do C1 pode ser desfeita com um Edit comum. Sugiro OQ-10 com
esse enunciado exato — ou, melhor, absorvê-la no AC-6, porque é entrega, não
gosto.

## Bloqueantes

**3** — R-SEC1, R-SEC2, R-SEC3.
