---
adr_id: ADR-182-AMEND-1
amends: ADR-182
title: Pin automático verificado do Codex CLI — verificador em processo próprio, registro local só-acréscimo, hook só-consulta e matriz de recusa fail-closed
status: PROPOSED
draft: true
draft_note: "RASCUNHO de entrada da rodada 2 do debate do PLAN-194 (ajuste 18 do consenso da rodada 1). NÃO é o arquivo canônico: o canônico nasce só no pacote de ADR (Q5), com o nome proposto .claude/adr/ADR-182-AMEND-1-codex-auto-pin-provenance.md."
proposed_at: 2026-10-02
proposed_by: CEO (S361 — PLAN-194 W3.2; consenso da rodada 1, §2(a), §2(c), §2(e), §6 W3-1..W3-10, ajustes 21–34)
decided_by: pendente — Owner (cerimônia GPG do pacote de ADR), depois do PROCEED da rodada 2
risk_tier: A
debate_required: true
debate_record: .claude/plans/PLAN-194/debate/round-1/consensus.md (rodada 1 — W3 RUN-ANOTHER-ROUND, VETO de Segurança LEVANTADO; condição de retirada = MF-W3-1..11 neste texto + decisões 3 a 6 escritas)
veto_floor: ADR-052 (security-engineer VETO — cadeia de suprimento, T-8 do docs/CROSS-LLM-THREAT-MODEL.md)
related_plans: [PLAN-194, PLAN-195, PLAN-163, PLAN-081]
related_adrs: [ADR-182, ADR-111, ADR-052, ADR-055-AMEND-3, ADR-001, ADR-081, ADR-149, ADR-161, ADR-192]
amends_targets:
  - ADR-182 §2 (tabela de braços — linha «payload sha256 != manifest entry»)
  - ADR-182 §3 (um núcleo, três consumidores)
  - ADR-182 §5 (cerimônia de atualização do pin, inclusive o passo 5)
  - ADR-182 §Consequences (o cache futuro por caminho/mtime/tamanho)
  - docs/CROSS-LLM-THREAT-MODEL.md §T-8, itens 1 e 5 da mitigação (no MESMO pacote)
unchanged_explicitly:
  - codex-cli-pin-manifest.json (formato, dono, cerimônia — nenhuma automação escreve nele)
  - codex-cli-pin.txt (faixa >=0.128.0,<0.157.0 intocada na W3)
  - validate-pair-rail-verdict.py e o passo 15 do release.yml
  - os braços INFRA do ADR-182 §2 (manifesto ausente/ilegível, lançador ou payload ausente)
---

# ADR-182-AMEND-1 — Pin automático verificado do Codex CLI

## §0 Como ler este rascunho

- **Estado.** PROPOSED, rascunho. Serve de entrada para a rodada 2 do debate (W3). Não autoriza
  pacote nenhum. A W3 continua BLOQUEADA até o PROCEED da rodada 2 (Q3, S361).
- **Legenda.** **[disco]**: conferido nesta redação, no HEAD `6fa9aa40`. **[consenso]**: conferido pelo
  sintetizador da rodada 1 (§0 do `consensus.md`). **[a medir]**: depende da W0.6 ou de sonda; o valor
  literal NÃO é inventado aqui. **[Owner]**: depende de decisão escrita do Owner (§19).
- **Repositório público.** Classes de defeito, invariantes e ids de lane. Nenhum caminho da pasta
  privada do Owner. Nenhuma receita de contorno de guarda: as costuras de teste e o kill-switch do
  ADR-182 §2 são citados pela FUNÇÃO, nunca pelo literal.
- **Rastreabilidade.** A tabela da §23 liga cada must-fix MF-W3-1..11 do portador do VETO à seção que o
  endereça. Cada seção cita o MF que cumpre.

## §1 Contexto

### 1.1 O que o ADR-182 deixou

O ADR-182 fechou o T-8 pinando o PAYLOAD nativo (não o lançador) num manifesto assinado
(`.claude/governance/codex-cli-pin-manifest.json`, hoje 0.156.1, um único triple
`aarch64-apple-darwin` **[disco]**), com um núcleo único `verify_codex_payload()`
(`check_pair_rail.py:589-747` **[disco]**) consumido pelo hook, pelo Gate 4 do
`.claude/scripts/local/pair-rail-gate.sh` (`:179-221` **[disco]**) e pelo validador do passo 15 do
`release.yml` (`:708-763` **[disco]**). Toda versão nova exige a cerimônia do §5 (edição do manifesto
sob sentinela, GPG do Owner).

### 1.2 Por que mudar agora

- **Decisão do Owner (S359, 2026-09-30):** «Pin automático verificado (Recomendado)» — não mexer nisso
  a cada versão. O re-pin manual vira plano B.
- **Cadência medida [consenso]:** 23 estáveis desde 2026-08-25, mediana de 22,0 h entre versões, 16 de
  22 intervalos abaixo de 48 h. Cerimônia por versão = ~1 cerimônia por dia.

### 1.3 O que a rodada 1 achou no desenho original (e que este texto corrige)

| achado | onde estava | correção aqui |
|---|---|---|
| C1 — conferir procedência DENTRO do hook PreToolUse (timeout 210 s, `settings.json:285` [consenso]) baixando ~331 MB vira allow por timeout | desenho (a) «na 1.ª vez que o rail vê uma versão nova, confere sozinho» | §4, §7: verificador em processo próprio; o hook nunca usa rede |
| C2 — «sem rede / sem atestado» podia cair em INFRA; no hook, INFRA = o rail some (allow, `check_pair_rail.py:1512-1524` [disco]) | pergunta 5 do plano | §8: todo «presente, mas não verificado» é fail-CLOSED |
| L-9 — «o rail segue na última versão verificada» é falso: o `npm i -g` sobrescreve o payload no MESMO caminho | pergunta 5 e controle W3.4(c) | a frase passa a ser «**bloqueia até verificar ou reinstalar a versão verificada**»; «segue na última verificada» só vale com a promoção em duas fases (§4.3) |
| C3 — stdlib não verifica assinatura; comparar dois campos da mesma resposta é coerência, não autenticidade | desenho sugerido da pergunta 2 | §4.2 passo V-5, §19 R-1 |
| C4 — a sonda executa o binário | W3.3 | §4.2: verificar → sondar → aceitar |
| C5 — o registro é uma 2.ª fonte de verdade | pergunta 1 | §9, §10 |
| C6 — modelo e esforço herdados do config global | desenho (c) | §12 |
| (c) do consenso — «W3.6 depois da W7» | pergunta 7 | §15, §16: W3.6 logo depois do LAND; cortes pela rota 2 |

## §2 Escopo honesto — o que o pin protege

- O pin protege a **identidade e a integridade do REVISOR** cujo veredito o framework registra (o par
  cruzado da rail). Ele **não protege a máquina**: o Owner roda o app e a CLI do Codex fora do
  framework, e um binário malicioso já teria executado ali antes de qualquer hook.
- Vale **só para este repositório**. Adopters não recebem `.claude/governance/`; neles o pin resolve
  como INFRA (aberto), como hoje (`CLAUDE.md` §4). Estender o pin automático aos adopters é onda
  própria (follow-up, nice-to-have 4 do portador do VETO).
- Sob o mesmo UID não há fronteira (registro, chave HMAC 0600, manifesto na árvore): o que esta emenda
  compra contra um processo do mesmo UID é DETECÇÃO (§11, cruzamento no boot), não prevenção (§19 R-5).

## §3 Decisão — visão geral

Três papéis, um núcleo:

```
  Owner (comando explícito; ≤ 1×/semana ou sob demanda)
        │
        ▼
  ┌───────────────────────────────┐  rede, download, tarball, npm, sonda, canário
  │ VERIFICADOR (processo próprio) │  — tudo AQUI, fora de qualquer guard
  │ Fase 1: staging → procedência  │
  │   → sonda/canário → evento HMAC│──► cadeia HMAC (evento durável, §11)
  │   → registro                   │──► REGISTRO local só-acréscimo (§9)
  │ Fase 2: promoção (npm i -g)    │
  └───────────────────────────────┘
                                         ▲ leitura local, sem rede
  ┌───────────────────────────────┐      │
  │ NÚCLEO verify_codex_payload()  │──────┘ (só com consulta ao registro habilitada)
  │  hash do payload + consulta    │◄── manifesto assinado (inalterado)
  └───────────────────────────────┘
     ▲ hook (manifesto ∪ registro)   ▲ CLI (só-manifesto por padrão)   ✗ release, envelope, kit
```

**Invariantes (o rail da rodada 2 audita o texto contra eles):**

- **I1.** O manifesto continua a ÚNICA âncora assinada. Nenhuma automação escreve nele. A trilha de
  release segue ancorada no manifesto da árvore tagueada.
- **I2.** O registro só **ACRESCENTA** confiança a um sha fora do manifesto, e só para um triple que o
  manifesto já tem (o manifesto dá o `path`). Nunca retira a confiança do manifesto. Qualquer dúvida
  sobre o registro = **zero confiança extra** (nunca INFRA).
- **I3.** O hook nunca usa rede, nunca baixa, nunca executa antes do hash. Ele hasheia o payload a cada
  invocação, como hoje: nenhum atalho por mtime ou tamanho.
- **I4.** Nada executa bytes não verificados: nem o verificador (sonda e canário só depois da
  procedência), nem os chamadores livres (§13).
- **I5.** Todo «binário presente, mas não verificado» é SECURITY fail-CLOSED. INFRA só nos braços que já
  eram INFRA no ADR-182 §2.
- **I6.** Cada aceitação automática substitui uma assinatura humana, então vira evento durável na
  cadeia HMAC ANTES de a linha do registro existir.
- **I7.** O registro nunca é lido pelo validador do passo 15, pelo `gen-envelope-ga.py`, pelo kit de
  corte nem pelo runner do re-pass.

## §4 O verificador (MF-W3-2, MF-W3-3, MF-W3-7)

### 4.1 Onde roda e o que nunca faz

- Script próprio, stdlib-only, Python ≥ 3.9 (nome proposto `.claude/scripts/codex-auto-pin-verify.py`;
  o oráculo `--is-canonical` decide a classe do path na abertura do pacote). Roda em processo PRÓPRIO,
  disparado por comando explícito. **Nunca** roda dentro de hook, guard, `/ceo-boot` ou Workflow.
- **Os bytes do verificador passam por cerimônia:** ele entra no manifesto ADR-192
  (`.claude/governance/gate-scripts-manifest.txt`) no mesmo pacote, porque o que ele grava substitui
  uma assinatura. O sha dele vai no registro e no evento. (Decisão deste rascunho; o portador do VETO
  confirma ou pede guarda canônica.)
- Ele **não re-implementa** o núcleo: resolve e hasheia payloads pelas funções do `check_pair_rail.py`
  (ADR-182 §3), e as constantes canônicas desta emenda moram no núcleo, para o hook revalidar o mesmo
  conjunto (§7).
- Saídas: `0` = registrado (ou já registrado, idempotente); `1` = recusado em QUALQUER célula da
  matriz A (§8), com `cell` no JSON; `2` = uso inválido. Não existe saída «INFRA com sucesso»: falha de
  rede é falha do verificador, e o resultado é o mesmo de qualquer recusa (nada registrado).

### 4.2 Fase 1 — verificar e registrar (ordem obrigatória)

| passo | o que faz | recusa em |
|---|---|---|
| V-0 | Pré-voo: piso de `df`, diretório de staging próprio (criado pelo verificador, removido por limpeza CONFINADA a ele), ação de aceitação presente no registro de ações do `audit_emit` (§11), registro local legível e íntegro | A-06, A-22, A-23 |
| V-1 | Metadado: packument completo de `@openai/codex` por `urllib`, HTTPS com verificação de certificado, na URL-base CONSTANTE do registro; teto de bytes; guarda o cabeçalho `Date` da resposta | A-01..A-05 |
| V-2 | Seleção da candidata pela regra da §5 (gramática estrita, carência no relógio do registro, ≤ `latest`, sem `deprecated`, ≥ piso) | A-07..A-11 |
| V-3 | Staging SEM execução: instala a versão EXATA (lançador + artefato de plataforma) num prefixo próprio, com scripts de ciclo de vida suprimidos, ambiente do npm montado do zero (registro fixo, sem `.npmrc` do usuário ou do projeto, sem variáveis `npm_config_*` herdadas) | A-04, A-18 |
| V-4 | Tarball de PLATAFORMA (`<v>-<sufixo>`) baixado por `urllib` da URL `dist.tarball` (mesmo host constante), em fluxo, com teto; sha512 em fluxo == `dist.integrity` | A-03, A-05, A-16 |
| V-5 | Procedência: atestado de proveniência SLSA v1 do lançador E da plataforma; `subject` = purl exato, digest = `dist.integrity`; identidade fixada (§6); assinatura pelo mecanismo medido na W0.6 (**[a medir]**, §19 R-1) | A-12..A-16 |
| V-6 | Membro do payload: no tarball de V-4, o ÚNICO membro regular no caminho exato `package/vendor/<triple>/bin/codex`, lido em fluxo sem extrair; sha256 com teto de tamanho descomprimido | A-17 |
| V-7 | Vínculo staging ↔ atestado: o payload materializado em V-3 (resolvido pelo núcleo, como o hook resolve) tem sha256 == V-6, e o pacote de plataforma materializado tem versão `<v>-<sufixo>` exata | A-18 |
| V-8 | Sonda (só agora o binário roda, e é o payload VERIFICADO de V-7, executado direto, como o hook faz): subcomandos `exec`, `review`, `app-server` e a união das FLAGS dos chamadores (`--sandbox`, `-o`/`--output-last-message`, `--output-schema`, `--color`, `--model`/`-m`, `--skip-git-repo-check`, `-c`, `--ignore-user-config` se adotada, e o ajuste de esforço na forma confirmada) | A-19 |
| V-9 | Canário funcional: um `exec` mínimo com o argv REAL do rail (o da §12) sobre um diff fixo, devolvendo JSON de veredito parseável na forma esperada. Gasta cota do Codex: obedece ao freio Q2 | A-20 |
| V-10 | Quarentena consultada: (versão, triple, sha) em quarentena ⇒ recusa permanente | A-21 |
| V-11 | Evento `codex_auto_pin_accepted` (nome proposto) emitido e CONFIRMADO na cadeia HMAC (o verificador drena o próprio spool fora de qualquer guard; a forma de confirmação é do builder). Sem confirmação ⇒ não registra | A-22 |
| V-12 | Linha de aceitação acrescentada ao registro (§9), sob trava própria, com `fsync` do arquivo e do diretório | A-23 |
| V-13 | Limpeza confinada do staging (o payload de staging nunca é caminho de execução do rail) | — |

**Proibições (MF-W3-3):** criptografia de assinatura escrita à mão; chamar de «assinatura conferida» a
comparação de dois campos da mesma resposta do registro; desligar verificação de certificado TLS
diante de cadeia de CA ausente (a saída é instalar a cadeia, e até lá a célula A-02 recusa).

### 4.3 Fase 2 — promoção

- Só depois de uma Fase 1 verde para AQUELA versão (célula P-02). Feita pelo verificador sob flag
  explícita de promoção, ou pelo Owner à mão, sempre com a **versão exata registrada** (nunca a `latest`
  crua, nunca `npm update -g`) e o mesmo ambiente de npm limpo e sem scripts de ciclo de vida.
- Depois do `npm i -g`, o verificador roda o núcleo no caminho do hook (consulta ao registro
  habilitada) sobre o lançador do PATH: tem de dar `verified_auto` com o sha registrado. Divergência ⇒
  célula P-01: o hook já bloqueia (sha desconhecido) e o verificador manda ao rollback (§14).
- Com as duas fases, «o rail segue na última versão verificada» volta a ser verdade **para quem usa a
  rota do verificador**: o global só é sobrescrito depois da aprovação. Para um `npm i -g` cru, vale a
  regra: **bloqueia até verificar ou reinstalar a versão verificada** (MF-W3-1).

### 4.4 Disco, rede e configuração (MF-W3-2; `CLAUDE.md` §4, regra S358)

- Diretório de staging próprio, criado pelo verificador; limpeza confinada a ele; piso de `df` antes de
  baixar (A-06); nenhum clone ou cópia fora dele.
- Tetos de tamanho em constantes canônicas, separados para metadado, atestado, tarball comprimido e
  membro descomprimido. Valor = 2× o maior medido na W0.6 (**[a medir]**). Acima do teto ⇒ recusa e
  limpeza (A-05).
- URL-base do registro em constante; todo download (tarball, atestado) tem de ficar no MESMO host;
  redirect para outro host ⇒ A-03. Proxy do ambiente não relaxa TLS.
- O npm, quando usado (staging, verificador sigstore), roda com ambiente montado do zero: registro
  fixo, arquivo de config de usuário vazio dentro do staging, cwd no staging, nenhuma `npm_config_*`
  herdada. Divergência observada do registro efetivo ⇒ A-04 (Unseen 8 do portador do VETO).

### 4.5 Cadência

Adoção sob demanda ou no máximo 1× por semana, sob o freio Q2 (nenhuma rodada nova do Codex acima de
80% do semanal). O `/ceo-boot` NÃO dispara o verificador; no máximo informa (§14).

## §5 Regra de elegibilidade (MF-W3-9; consenso §2(a))

A candidata é a **estável mais nova** que cumpre TODAS:

1. **Gramática estrita (MF-W3-4).** O lançador tem versão base estável `X.Y.Z` (dígitos, sem zero à
   esquerda, sem pré-release, sem metadado de build). O artefato de plataforma tem versão IGUAL, por
   comparação de string, a `X.Y.Z-<sufixo>`, onde `<sufixo>` vem de uma tabela canônica triple → sufixo
   com só as entradas medidas (hoje uma: `aarch64-apple-darwin` → `darwin-arm64`, **[disco]**
   manifesto e ADR-182 §5). Qualquer outro pré-release é recusado — inclusive a armadilha medida
   **[consenso]**: dist-tag `release-0.159.0-alpha.12.1-alpha-darwin-arm64` →
   `0.159.0-alpha.12.1-darwin-arm64` (alpha com sufixo de plataforma).
2. **Carência ≥ 48 h, no relógio do registro.** Idade = `Date` (cabeçalho da resposta do registro, sob
   TLS) − `time[...]` do packument, tomando o MAIS TARDIO entre a publicação do lançador `X.Y.Z` e a do
   artefato `X.Y.Z-<sufixo>`. O relógio local não entra. `Date` ausente ou ilegível ⇒ recusa. A
   constante `48` é canônica e tem teste. A espera é `external_wait` (relógio do npm).
3. **≤ `latest`.** A `latest` é TETO, nunca prova: ela própria tem de passar na gramática estrita
   (senão, nenhuma candidata), e a candidata é ≤ `latest` em ordem semver de estáveis.
   **Nunca «== `latest`»** (pela cadência medida, «== latest + 48 h» pararia o pin em ~73% dos dias).
4. **Sem `deprecated`** no lançador nem no artefato de plataforma.
5. **≥ piso do manifesto** (`package_version` do manifesto assinado). Efeito monotônico: quando uma
   cerimônia futura subir o manifesto, as entradas do registro abaixo do novo piso perdem a confiança
   sozinhas (H-07).

Exemplo **[consenso]**, 2026-10-02T00:20Z: 0.160.0 (~4 h) e 0.159.3 (~25 h) não elegíveis; 0.159.2
(~48,3 h) elegível. O pin anda ~2 dias atrás da `latest`, sem cerimônia.

## §6 Identidade fixada do construtor e leitura do payload (MF-W3-4)

- **Constantes canônicas de identidade** (no núcleo, com teste), conferidas no statement in-toto de
  CADA atestado (lançador e plataforma):
  - `predicateType` = proveniência SLSA v1;
  - repositório-fonte do Codex CLI, caminho do workflow de publicação e forma da ref de tag amarrada à
    versão base `X.Y.Z`;
  - id do construtor (runner hospedado);
  - `subject.name` = purl exato do pacote (o de PLATAFORMA para o payload), `subject.digest.sha512` =
    `dist.integrity` decodificado.

  Os valores literais vêm dos atestados reais da 0.156.1 e da 0.160.0, capturados na W0.6 com data
  (**[a medir]**). Este rascunho não os inventa. Um atestado SLSA válido emitido por OUTRO repositório
  ou workflow é recusado (A-14), mesmo com digests coerentes.
- **Vínculo assinatura ↔ identidade [a medir].** Se a assinatura for conferida pelo verificador do npm
  (W0.6) e a identidade for lida pelo verificador desta emenda, os dois têm de ver o MESMO bundle. A
  W0.6 mede se isso é garantível; se não for, a identidade conferida vale para a cópia do verificador e
  o resíduo é declarado (§19 R-1).
- **Chave de aceitação.** O sha256 do payload LOCAL é igual ao sha256 do ÚNICO membro regular no
  caminho exato do tarball atestado, lido em fluxo: sem extrair para disco, sem link simbólico ou
  físico, sem nome duplicado. O metadado local (versão relatada pelo lançador) é só dica de busca,
  nunca prova.

## §7 O hook e o núcleo (MF-W3-1, MF-W3-2)

- `verify_codex_payload()` ganha um parâmetro de consulta ao registro, **desligado por padrão**. O
  hook o liga; a CLI só o liga com flag explícita (§10).
- Ordem dentro do núcleo (sem rede, sem execução): triple → manifesto (inalterado) → payload
  resolvido → sha256 → `== manifesto`? ⇒ `verified` (`pin_source = manifest`) → senão, se a consulta
  está ligada: registro carregado e validado (§9) → entrada válida para (triple, sha) ⇒
  `verified_auto` (`pin_source = registry`) → senão `mismatch` ⇒ BLOCK.
- **Revalidação a cada leitura.** O núcleo confere a evidência gravada contra as constantes canônicas
  ATUAIS (identidade, carência, gramática, modos de assinatura permitidos, `path` igual ao da entrada
  do manifesto, triple do host, versão ≥ piso). Entrada fora das constantes = sem confiança (H-07).
  Isso não detém quem forja a evidência de forma coerente sob o mesmo UID (§19 R-5), mas impede que uma
  linha incompleta ou de esquema antigo conceda confiança.
- **Bloqueio.** Sha desconhecido ⇒ `{decision: block}` com mensagem que nomeia o verificador e a
  reinstalação da versão verificada. Nenhuma variável de ambiente relaxa a comparação; a costura de
  teste do registro segue o padrão das costuras do ADR-182 §2 (honrada só no modo de teste, inerte no
  caminho vivo, com controle negativo).
- **Custo.** O registro é minúsculo (uma linha por versão adotada, ≤ 1/semana) e tem teto de tamanho.
  O custo dominante segue sendo o hash do payload (~260 MB), como hoje.

## §8 Matriz de recusa (MF-W3-1; QA must-fix 11)

Toda célula abaixo é pré-registrada. O builder codifica UMA ação esperada por célula; o CEO pode ajustar
valores, não remover células.

### 8.A Verificador (adoção) — efeito comum: **nada registrado**; o rail não muda; se o sha novo já estiver no global, o hook bloqueia (H-03)

| célula | condição | resultado | saída |
|---|---|---|---|
| A-01 | sem rede (DNS, conexão, tempo) em qualquer busca | recusa; **nunca INFRA** | 1 |
| A-02 | falha de TLS (cadeia de CA ausente, certificado inválido, nome) | recusa; verificação de certificado nunca é desligada | 1 |
| A-03 | URL de tarball/atestado fora do host constante, ou redirect para outro host | recusa | 1 |
| A-04 | registro efetivo do npm ≠ constante (config herdada) | recusa | 1 |
| A-05 | resposta acima do teto (metadado, atestado, tarball, membro descomprimido) | recusa + limpeza confinada | 1 |
| A-06 | piso de `df` não atendido | recusa ANTES de baixar | 1 |
| A-07 | versão fora da gramática estrita (pré-release, alpha com sufixo de plataforma, build, zero à esquerda, sufixo ≠ o do triple) | não candidata | 1 se nenhuma restar |
| A-08 | idade < 48 h (máximo das duas publicações) ou `Date` ausente/ilegível | não candidata / recusa | 1 se nenhuma restar |
| A-09 | candidata > `latest`, ou `latest` fora da gramática | não candidata / nenhuma candidata | 1 |
| A-10 | `deprecated` no lançador ou na plataforma | não candidata | 1 se nenhuma restar |
| A-11 | abaixo do piso do manifesto | não candidata | 1 se nenhuma restar |
| A-12 | sem atestado de proveniência SLSA v1 (lançador ou plataforma) | recusa | 1 |
| A-13 | atestado de OUTRO pacote ou versão (`subject` ≠ purl esperado) | recusa | 1 |
| A-14 | identidade divergente (repo, workflow, ref, `predicateType`, construtor) com digests coerentes | recusa | 1 |
| A-15 | assinatura do atestado inválida | recusa **se** a W0.6 validar o mecanismo; senão a célula é NÃO DETECTÁVEL pelo verificador e fica ACEITA e DECLARADA (§19 R-1) **[Owner]** | 1 / declarada |
| A-16 | digests incoerentes: sha512 do tarball ≠ `dist.integrity`, ou digest do `subject` ≠ `dist.integrity` | recusa | 1 |
| A-17 | membro do payload ausente, duplicado, não regular, caminho ≠ exato, ou acima do teto | recusa | 1 |
| A-18 | staging: payload materializado ≠ sha de A-17; versão de plataforma materializada ≠ `<v>-<sufixo>`; script de ciclo de vida não suprimido | recusa + relato de anomalia | 1 |
| A-19 | sonda reprovada (subcomando ou flag obrigatória ausente) — reencena o A7 | recusa | 1 |
| A-20 | canário reprovado (saída ≠ 0, veredito não parseável, forma divergente) ou inconclusivo (cota, capacidade, tempo) | recusa; inconclusivo pode ser re-tentado depois | 1 |
| A-21 | (versão, triple, sha) em quarentena | recusa permanente | 1 |
| A-22 | ação de aceitação ausente do registro de ações do `audit_emit`, ou evento não confirmado na cadeia | recusa; a linha do registro NÃO é gravada | 1 |
| A-23 | registro existente não confiável (§9), ou falha de trava/escrita/`fsync` | recusa; nada gravado, nada promovido | 1 |
| A-24 | (triple, sha) já registrado e válido | idempotente, nenhuma linha nova | 0 |
| P-01 | promoção: sha do global depois do `npm i -g` ≠ sha registrado | o hook já bloqueia (H-03); relato «promoção divergente»; rollback §14 | 1 |
| P-02 | promoção pedida sem Fase 1 verde para a versão | recusa | 1 |

### 8.B Hook (cada invocação L3+; sem rede, sem download, sem execução antes do hash)

| célula | condição | status | efeito |
|---|---|---|---|
| H-01 | sha == entrada do manifesto | `verified`, `pin_source=manifest` | executa o caminho verificado |
| H-02 | sha ∉ manifesto; ∈ registro confiável; entrada revalidada; fora de quarentena | `verified_auto`, `pin_source=registry` | executa o caminho verificado |
| H-03 | sha ∉ manifesto ∪ registro | `mismatch` | **BLOCK**, nomeia o verificador e a reinstalação |
| H-04 | sha registrado, mas em quarentena | `mismatch` | **BLOCK** |
| H-05 | registro AUSENTE | zero confiança extra (não INFRA) | H-01 ou H-03 |
| H-06 | registro presente e não confiável (ilegível, malformado, cadeia local quebrada, modo/dono/tipo errados, link, acima do teto) | zero confiança extra; `registry_untrusted` no detalhe | H-01 com aviso, ou H-03 (**BLOCK**) |
| H-07 | entrada com evidência fora das constantes atuais (identidade, carência, gramática, modo de assinatura, `path`, triple, piso) | aquela entrada sem confiança | H-03 (**BLOCK**) se nada mais casar |
| H-08 | triple não derivável ou ausente do manifesto | `triple_missing` | **BLOCK** (inalterado; o registro não cria triple) |
| H-09 | manifesto presente e malformado | `mismatch` | **BLOCK** (inalterado) |
| H-10 | manifesto ausente/ilegível; lançador ausente; payload não resolvido/ilegível | `infra` | inalterado (ADR-182 §2): o rail some com aviso — §19 R-8 |
| H-11 | costura de override do binário posta | mesmo caminho: hash + (manifesto ∪ registro); ausente ⇒ `mismatch` | inalterado |
| H-12 | qualquer tentativa de rede, download ou execução no caminho do hook | proibido por construção | provado por teste (guarda de socket + espião) |

### 8.C CLI e trilha de release

| célula | consumidor | condição | resultado |
|---|---|---|---|
| C-01 | `--verify-codex-pin` SEM flag | qualquer | só-manifesto; o registro NÃO é aberto; saídas 0/1/3 do ADR-182; JSON + `pin_source`; sha só-registrado ⇒ `mismatch`/1 |
| C-02 | `--verify-codex-pin` COM a flag explícita (nome proposto `--allow-auto-pin`) | qualquer | mesmo resultado do hook; `verified_auto`/0 com `pin_source=registry` |
| R-01 | validador do passo 15 | veredito com sha só auto-pinado | `VERDICT_INVALID` (saída 3) — inalterado; é a célula (d) dos controles |
| R-02 | `gen-envelope-ga.py` | sha/versão ≠ manifesto | recusa — inalterado |
| R-03 | runner do re-pass | global auto-pinado (≠ manifesto) | rota 2; a PROVENANCE registra a versão do manifesto e a rota |
| R-04 | Gate 4 do `pair-rail-gate.sh --phase 6` | global auto-pinado | **falha por desenho** (pré-voo da trilha de release, «antes da tag») |

## §9 O registro (MF-W3-5)

- **Onde.** `<runtime_state_dir>/codex-auto-pin/`, resolvido por `_lib/runtime_paths.py`
  (`runtime_state_dir()`, `:139-161` **[disco]**; ADR-001, nunca slug derivado à mão). FORA de `state/`
  (`spool_writer._state_dir()` = `<audit_dir>/state/`, `:265` **[disco]**), portanto fora do alcance do
  GC da W2 e da limpeza W2.6 (por caminho e por nome: nenhum padrão de PID). FORA da árvore git (não
  suja o SIGN, R-DO14). Em SUBDIRETÓRIO e com extensão que não é `.jsonl`: a varredura de limpeza do
  CC já apagou `*.jsonl` de topo em `~/.claude/projects/` (S357).
- **Modos e forma.** Diretório 0700, arquivo 0600, dono == euid, arquivo regular, aberto sem seguir
  link; teto de tamanho. Qualquer violação ⇒ registro não confiável (H-06).
- **Só-acréscimo.** O verificador nunca reescreve, trunca ou apaga. Quarentena é linha nova. Cada linha
  leva `seq` monotônico e `prev_sha256` (sha da linha anterior), que detecta edição ou truncamento no
  meio (não no fim, e não contra o mesmo UID — §19 R-5).
- **Esquema v1 (campos mínimos).** Linha de aceitação: `schema`, `kind=accept`, `seq`, `prev_sha256`,
  `package`, `version`, `platform_version`, `target_triple`, `payload_path`, `payload_sha256`,
  `npm_integrity` (plataforma e lançador), `attestation_sha256` (plataforma e lançador), `identity`
  (os campos da §6), `signature_mode`, `published_at` (as duas), `registry_date`, `grace_hours`,
  `latest_at_check`, `probe` (resultado + lista conferida), `canary` (resultado + sha do argv),
  `verifier_sha256`, `kernel_sha256`, referência do evento HMAC, `recorded_at` (UTC). Linha de
  quarentena: `schema`, `kind=quarantine`, `seq`, `prev_sha256`, `target_triple`, `payload_sha256`,
  `version`, `reason`, `recorded_at`. `kind` desconhecido ⇒ não confiável.
- **Leitores.** Só o núcleo (no caminho do hook e na CLI com flag) e, por meio da CLI com flag, o
  detector de deriva e o cruzamento do boot (§14). **Nunca** o passo 15, o `gen-envelope-ga.py`, o kit
  nem o runner do re-pass (I7). **Escritor:** só o verificador.
- **Perda do registro** = direção segura: todas as versões só-registradas passam a bloquear até nova
  Fase 1. A recuperação é rodar o verificador de novo.
- **Não é o cache do ADR-182 §Consequences.** O registro não dispensa o hash a cada invocação (Unseen 10
  do portador do VETO).

## §10 Contrato de cada consumidor (MF-W3-5; R-DO3)

| consumidor | lê o registro? | aceita `verified_auto`? | contrato |
|---|---|---|---|
| hook `check_pair_rail.py` (PreToolUse, L3+) | sim | sim | §7, matriz 8.B |
| CLI `--verify-codex-pin` sem flag | **não** | não | só-manifesto, saída idêntica à do ADR-182 + `pin_source`; é o padrão de todo chamador existente |
| CLI com flag explícita | sim | sim | o Check da W3 e o detector de deriva usam esta forma e exigem `pin_source = registry` para versão fora do manifesto |
| Gate 4 do `pair-rail-gate.sh` (fase 6, `:208` **[disco]**) | não (chamada sem flag, inalterada) | não | pré-voo da trilha de release; com global auto-pinado reprova por desenho (R-04) |
| `run-ga-repass.sh` rota 1/rota 2 (`PLAN-193/repass-ga/run-ga-repass.sh:246-306` **[disco]**) | não | não | rota 1 só se o global É a versão do manifesto e verifica sem flag; senão rota 2 (npx da versão do manifesto em cache próprio + oráculo sem flag + shim) |
| validador do passo 15 | **nunca** | não | inalterado; ancorado no manifesto da árvore tagueada |
| `gen-envelope-ga.py` / kit de corte | **nunca** | não | inalterados; versão e sha do manifesto, lidos da PROVENANCE |
| verificador (§4) | escreve e lê | — | único escritor |

## §11 Evento de aceitação na cadeia HMAC (MF-W3-6; consenso §2(e))

- **Por quê.** Hoje a assinatura GPG do Owner é a evidência de cada re-pin. A aceitação automática
  SUBSTITUI essa assinatura, então precisa de evidência durável. Ação fora de `_KNOWN_ACTIONS` vira
  breadcrumb (`audit_emit.py:5260-5262` [consenso]). O precedente do ADR-055-AMEND-3 (preferir
  breadcrumb para não tocar o kernel) **não se aplica**: ali não se substituía assinatura.
- **O quê.** UM pacote de kernel de registro de ações (`_lib/audit_emit.py`: `_KNOWN_ACTIONS`, ramo de
  `_scrub_` dedicado e deny-by-default, SPEC do audit-log e contagens, como os precedentes):
  - `codex_auto_pin_accepted` (nome proposto) — campos: versão, versão de plataforma, triple, sha256 do
    payload, `npm_integrity`, `attestation_sha256`, identidade, `signature_mode`, `verifier_sha256`,
    resultado da sonda e do canário;
  - `codex_auto_pin_quarantined` (nome proposto) — triple, sha, versão, motivo;
  - **promoção** de `pair_rail_codex_pin_mismatch`, hoje só breadcrumb (`check_pair_rail.py:1201-1204`
    **[disco]**).
- **Fato de disco que o pacote tem de tratar [disco].** O emissor do hook, `_emit_audit()`
  (`check_pair_rail.py:1212-1236`), escreve só no sumidouro de teste e no stderr: ele NÃO chama o
  `emit_generic`, nem para ações já registradas (`pair_rail_codex_unavailable`), apesar do comentário
  de `:1185-1194`. Promover o `pair_rail_codex_pin_mismatch` exige REGISTRAR (pacote de kernel) e LIGAR
  o sítio de emissão ao `emit_generic` (pacote 1 da W3), com taxa limitada. O mesmo vale para o
  `pair_rail_codex_unavailable`, que esta emenda usa como instrumento (§14). As demais ações do
  `_emit_audit` ficam como estão, declarado.
- **Ordem e vaga.** O pacote de kernel vai em SÉRIE com a W1a do PLAN-195 (colisão em `audit_emit.py`,
  mapa de colisões, linha (a)) e landa ANTES da W3.6. Enquanto ele não landar, o verificador recusa
  gravar (A-22): o código da W3 pode landar, mas nenhuma versão é aceita automaticamente.
- **Ordem dentro do verificador.** Evento primeiro (confirmado), linha do registro depois. Evento sem
  linha = órfão inofensivo (nenhuma confiança concedida). Linha sem evento = ALARME (§14).
- **Alternativa** (evidência só no registro): só por decisão ESCRITA do Owner (decisão 6, §19 R-3).

## §12 Os dois eixos do argv (MF-W3-8; consenso C6)

- **Eixo 1 — binário:** automático, por esta emenda (cadência até diária, adoção ≤ 1×/semana).
- **Eixo 2 — modelo e esforço:** constantes canônicas usadas pelo argv do rail; mudar de modelo é
  cerimônia por GERAÇÃO (coerente com «modelo novo ⇒ re-testar», `CLAUDE.md` §4). Hoje o argv OMITE
  `--model` (`codex_cli_shape.py:110` `DEFAULT_MODEL = None`; `--model` só com valor explícito, `:351`;
  `_VALID_MODELS` sem nenhum `gpt-6*`, `:97-105` **[disco]**), e o revisor herda o
  `~/.codex/config.toml` global, que o app regravou em 2026-10-01 (Q11). O id fixado entra em
  `_VALID_MODELS` (depois da W3b) e no `model-deprecations.json` (WARN de aposentadoria). O valor do par
  é a decisão 5 **[Owner]** (§19 R-4).
- **`--ignore-user-config`** entra no argv SE a sonda (V-8) confirmar a flag na versão E uma medição
  provar que `memories` não carrega com ela (MF-W3-8; Unseen R-SEC10: o config global pode trocar
  provedor/endpoint e ligar memória persistente, que é canal de injeção entre repositórios).
- **Registro por rodada:** versão, sha do payload, `pin_source`, modelo pedido, modelo servido (se o
  `session_meta` o expuser), esforço e sha do config (pré-voo Q11). Id indisponível ⇒ contagem diária
  no boot, nunca silêncio (hoje degrada para advisory, `codex_cli_shape.py:93`).
- **Mesmo argv nas duas trilhas:** os derivadores do kit da 1.4.3 herdam a base do eixo 2, ou o
  material assinado declara a divergência (MF-16 do consenso, ajuste 42).

## §13 Chamadores fora do hook (MF-W3-10; consenso C8)

| chamador | classe do path | executa sozinho? | tratamento |
|---|---|---|---|
| `.claude/scripts/codex_invoke.py:193` (`["codex"] + argv`, PATH) | livre | não | passa pelo núcleo (com a flag) e executa o caminho verificado — pacote 2 |
| `.claude/scripts/run-promotion-gate.py:196-212` (`codex --version`) | livre | não | idem — pacote 2 |
| `.claude/hooks/codex_review_user_code.py:120-131` (hook `Stop`, `codex exec` do PATH) | canônico | **sim, no opt-in** (`CEO_CODEX_USER_REVIEW_AUTO=1`; padrão detect-only, `settings.json:636-645` **[disco]**) | declarado no material assinado com o estado do opt-in; backlog |
| `.claude/workflows/council-audit.js:325` | canônico | não | declarado; backlog |
| daemon `app-server` (atualiza-se fora do pin, lane `CX-06`) | externo | sim | declarado |
| `codex exec review` manual | externo | não | declarado |

Depois da promoção (§4.3), o binário do PATH JÁ é um verificado; o buraco real das rodadas manuais é a
janela entre um `npm i -g` cru e o próximo uso do hook, que o bloqueia (§19 R-9).

## §14 Quarentena, rollback e visibilidade (Critic-C MF-13)

- **Quarentena.** Comando do verificador: acrescenta linha `kind=quarantine` (sempre gravada, mesmo se o
  evento falhar — é redução de confiança) e emite `codex_auto_pin_quarantined`. Efeito: H-04 (BLOCK) e
  A-21 (recusa permanente de re-registro). Quarentena é TERMINAL para (versão, triple, sha); não há
  «desquarentena» automática. Desconfiar da versão do MANIFESTO continua sendo a cerimônia do ADR-182
  (ou o kill-switch global auditado, inalterado).
- **Rollback.** Reinstalar a versão exata anterior já registrada e fora de quarentena (ou a do
  manifesto): o hook verifica OFFLINE (H-02 ou H-01). Qualquer versão registrada e fora de quarentena é
  aceita: rollback é recurso; a defesa contra versão ruim conhecida é a quarentena.
- **Visibilidade (advisory, antes da W3.6):**
  - o detector de deriva (`check-substrate-drift.py`) lê o registro pela CLI com flag: instalado ∈
    registro = sem deriva; instalado ≠ manifesto = informação para o próximo corte, nunca recomendação
    de re-pin (R-DO9);
  - cruzamento no `/ceo-boot`: linha de aceitação SEM evento na cadeia = ALARME; evento de quarentena
    SEM linha = ALARME (quarentena removida); evento de aceitação sem linha = órfão, informativo;
  - contagem diária, por versão, de falhas do rail a partir de eventos DURÁVEIS (`codex_invoke_dispatched`
    com `exit_code`, `check_pair_rail.py:1052-1054` **[disco]**, e `pair_rail_case`), mais o
    `pair_rail_codex_unavailable` depois de ligado (§11). O `codex_invoke_dispatched` tem taxa limitada
    (`audit_emit.py:12390` **[disco]**): a contagem é aproximada, declarado.

## §15 Cortes de release, faixa e T-8 (MF-W3-11, parte mantida; consenso §2(c), C7)

- A faixa do `codex-cli-pin.txt` (`>=0.128.0,<0.157.0`) fica **intocada** na W3. O corte da 1.4.3
  declara o 0.156.1 (versão do manifesto).
- O passo 15 segue exigindo `codex_payload_sha256` == manifesto da árvore tagueada; o validador não muda
  (membro do manifesto ADR-192). Versão só auto-pinada ⇒ `VERDICT_INVALID` (R-01).
- **Limite declarado do validador:** `parse_semver` casa por PREFIXO
  (`validate-pair-rail-verdict.py:355-359` [consenso]), então `0.159.0-alpha.12.1` conta como 0.159.0.
  O passo 15 não garante «só estável»; quem garante é o sha do manifesto.
- **T-8 no MESMO pacote** (`docs/CROSS-LLM-THREAT-MODEL.md:328` em diante **[disco]**): o item 1 passa a
  dizer que o hook confia em «manifesto assinado (Owner) ∪ registro local de pin automático
  (verificador sob ADR-192 + procedência + identidade fixada + carência + sonda/canário + evento
  HMAC)»; o item 5 passa a dizer que a cerimônia é a via do MANIFESTO e da trilha de release, e que o
  gatilho do ADR-111 §2 está preservado e NÃO AVALIÁVEL (§19 R-2); o resíduo ganha R-1, R-5 e R-6 desta
  emenda.

## §16 W3.6 — atualizar o Codex logo depois do LAND (consenso §2(c), rota 2 confirmada)

O disco refuta a NECESSIDADE de «W3.6 depois da W7»: o runner do re-pass já resolve o Codex do
MANIFESTO por npx em cache próprio quando o global é outra versão (rota 2), com igualdade de versão,
oráculo e shim, e o GA 1.4.1 já rodou assim (`PLAN-192/repass-ga/PROVENANCE-ga.md:6` [consenso]).

**Pré-condições (todas; onde indicado, a decisão escrita do Owner substitui):**

1. LAND dos pacotes 1 e 2 da W3.
2. Pacote de kernel do evento (§11) landado — ou a decisão 6 escrita **[Owner]**.
3. Detector de deriva e cruzamento do boot lendo o registro (§14) landados.
4. W0.6 medida; decisão 3 escrita se a W0.6 reprovar **[Owner]**.
5. Os derivadores do kit da 1.4.3 (clones de `PLAN-193/derive-kit-142.py` e `derive-ga-kit-142.py`
   **[disco]**) herdam a rota 2, a igualdade de versão, o oráculo SEM flag e o shim. Controle: kit com
   global ≠ manifesto ⇒ a PROVENANCE registra a versão do manifesto e a rota 2.
6. **Ordem M4 na rota 2 [disco, achado desta redação].** Os runners atuais executam
   `npx -y @openai/codex@<versão do manifesto> --version` ANTES do oráculo
   (`PLAN-193/repass-ga/run-ga-repass.sh:266` contra `:282-286`; `PLAN-192/.../run-ga-repass.sh:203`
   contra `:219-223`): o payload materializado pelo npx roda uma vez sem ter sido conferido contra o
   manifesto. O kit da 1.4.3 inverte (materializar sem executar → oráculo → só então `--version`), ou o
   material assinado declara o resíduo (§19 R-12).
7. Pré-voo do corte declara a rede, os ~331 MB, o piso de `df` e a limpeza confinada do `.npx-cache`; o
   argv do runner alinhado ao eixo 2 (ou divergência declarada); o pré-voo Q11 vale no re-pass da rc e
   do GA.

**Passos:** Fase 1 sobre a candidata ELEGÍVEL do dia (nunca a `latest` crua) → Fase 2 (versão exata) →
1.ª rodada real: CLI com flag = `verified_auto`/0 com `pin_source = registry`; evento na cadeia;
`session_meta` com a versão, o originador `codex_exec` e 0 sessões «guardian» (lanes `CX-06`, `CX-12`);
registro por rodada do eixo 2. Depois disso, a W5.1 usa a versão global auto-pinada como `codex_cli` do
refresh.

**Regra operacional (W3.1):** até o LAND da W3, Codex no 0.156.1, sem `npm update -g`. Depois, só pelo
procedimento acima.

## §17 Controles vermelho→verde exigidos (QA must-fix 9–13; ajuste 25)

Em árvore descartável (escrita), sem rede e sem binário real; nenhuma asserção de tempo absoluto.

- Guarda de socket no módulo de teste inteiro (conectar levanta), com controle POSITIVO de que dispara;
  cada célula A-xx e H-xx da §8 com a sua ação esperada.
- Tarball SINTÉTICO de KB gerado no tmp, com `sha512` == `dist.integrity` sintético == `subject` do
  atestado sintético; UM atestado real de KB (0.156.1 e 0.160.0), capturado com data, só para o formato
  do parser.
- O `npm i -g` modelado sobrescrevendo o payload no MESMO caminho (L-9): versão nova recusada ⇒ o hook
  BLOQUEIA.
- Espião: zero execução de payload não verificado (sonda e canário só depois de V-7); zero rede e zero
  execução no caminho do hook (H-12).
- Sonda e argv com um `codex` stub no PATH temporário: subcomando removido ⇒ versão recusada (reencena
  o A7); argv capturado VERMELHO hoje (sem `--model`) e VERDE com o par e o esforço (e
  `--ignore-user-config`, se adotado).
- Quarentena ⇒ `mismatch`; reinstalar a anterior ⇒ `verified_auto` offline.
- C-01: CLI sem flag ⇒ só-manifesto, registro não aberto. R-01: validador INVALID para versão só
  auto-pinada (célula (d)).
- Costura de teste do registro inerte no caminho vivo (controle negativo, molde
  `test_fixture_ignored_on_live_path_without_test_mode`).
- Constante de 48 h com teste; tabela de gramática com a armadilha medida literal (§5 item 1).
- O Check de sucesso da W3 exige `pin_source = registry` para uma versão FORA do manifesto (verde por
  construção é proibido).

## §18 Cláusulas do ADR-182 emendadas

1. **§2, linha «payload sha256 != manifest entry → fail-CLOSED».** Passa a ser: sha256 do payload ∉
   {entrada do manifesto} ∪ {entradas confiáveis do registro local de pin automático para o mesmo
   triple, consultadas SÓ no caminho do hook e na CLI com flag explícita} ⇒ SECURITY, fail-CLOSED
   block. O registro só acrescenta confiança; ausente, ilegível ou malformado = nenhuma confiança
   extra, nunca INFRA. Os braços INFRA do §2 ficam inalterados.
2. **§3, «um núcleo, três consumidores».** Passa a ser: um núcleo, consumidores com contrato escrito
   (§10 desta emenda). O verificador usa o mesmo núcleo para resolver e hashear.
3. **§5, cerimônia de atualização.** Continua a ÚNICA via para mudar o MANIFESTO (trilha de release e
   piso). Para o HOOK, uma versão nova vale sem cerimônia quando o verificador desta emenda a registra.
   O passo 5 (gatilho do ADR-111 §2, desvio > 5 pp do catch_rate) fica PRESERVADO e declarado NÃO
   AVALIÁVEL até existir corpus com sha e linha de base (o corpus travado não está no repositório
   [consenso]).
4. **§Consequences, «cache por (path, mtime, size) via nova emenda».** Esta emenda NÃO é esse cache: o
   hook segue hasheando o payload a cada invocação.

## §19 Residuais declarados

**Dependentes de decisão do Owner (a decidir pelo Owner; cada uma com a recomendação do CEO):**

- **R-1 — Assinatura do atestado (decisão pendente 3).** Só se a W0.6 reprovar o verificador sigstore
  do npm no projeto-rascunho. **A decidir pelo Owner.** Recomendação: aceitar por escrito «confiança no
  registro via TLS + vínculo de digests + identidade fixada» como resíduo NOMEADO aqui e no material
  assinado; o `signature_mode = registry-trust` só entra no conjunto permitido da constante canônica
  por essa decisão. Consequência declarada: a célula A-15 fica NÃO DETECTÁVEL — um atestado forjado com
  digests coerentes, servido por um registro comprometido, passaria. Recusar devolve o plano B (re-pin
  manual), que o Owner já recusou como rotina. Também aqui: se a W0.6 mostrar que assinatura e
  identidade não podem ser lidas do MESMO bundle, o resíduo de vínculo é declarado (§6).
- **R-2 — Sentinela de qualidade (decisão pendente 4).** **A decidir pelo Owner.** Recomendação: (ii) a
  W3 landa SEM sentinela, declarada; o corpus travado do ADR-111 não está no repositório e o gatilho de
  5 pp fica NÃO AVALIÁVEL até haver corpus com sha e linha de base (m ≥ 3, variância medida com o mesmo
  binário). Sonda e canário cobrem a LIVENESS (classe A7), não a qualidade: uma versão que revisa pior
  passa. Alternativa (i): construir corpus e linha de base antes da W3 (cota do Codex m × N + ~100k
  tokens).
- **R-3 — Evidência só no registro (decisão pendente 6).** Só se o Owner quiser evitar o pacote de
  kernel. **A decidir pelo Owner.** Recomendação: manter o evento na cadeia (§11). Se escolher a
  alternativa: a evidência de cada aceitação fica num arquivo mutável pelo mesmo UID, sem elo na
  cadeia, e o cruzamento do boot (§14) não existe.
- **R-4 — Par modelo/esforço do eixo 2 (decisão pendente 5).** **A decidir pelo Owner.** Recomendação:
  `gpt-6-astra` + `xhigh`, o par em uso de fato, condicionado ao re-teste da Q11. Na mesma decisão:
  adopters herdam o par fixo (conta que não serve o id cai em advisory, visível na contagem diária) ou
  mantêm o padrão da conta.

**Declarados independentemente de decisão:**

- **R-5 — Mesmo UID.** O registro (0600), a chave HMAC (0600) e o manifesto são legíveis e graváveis
  pelo mesmo UID; a cadeia local `prev_sha256` não detecta truncamento do FIM nem forja coerente. A
  defesa é detecção: evento HMAC + cruzamento no boot. Escrita do registro por shell dentro de uma
  sessão não tem guarda dedicada conhecida nesta redação (**a conferir** na abertura do pacote).
- **R-6 — Escopo.** O pin não protege a máquina (§2).
- **R-7 — TOCTOU hash→exec** num caminho absoluto já resolvido (ADR-182, inalterado).
- **R-8 — Braços INFRA inalterados.** Manifesto ausente, lançador ou payload ausente ⇒ o rail some com
  aviso (allow). Mitigação: contagem diária no boot (§14). O registro nunca substitui o manifesto.
- **R-9 — Chamadores declarados** (§13): o hook `Stop` no opt-in, o `council-audit.js`, o daemon
  `app-server` e o `codex exec review` manual; a janela de um `npm i -g` cru até o próximo uso do hook.
- **R-10 — Limite do `parse_semver`** do validador (§15).
- **R-11 — Adopters** seguem em INFRA aberto (sem `.claude/governance/`).
- **R-12 — Ordem M4 na rota 2** dos runners atuais (§16 item 6), se o kit da 1.4.3 não a inverter.
- **R-13 — Dependência de rede dos cortes.** O corte depende de a versão do manifesto (0.156.1) seguir
  baixável no registro.
- **R-14 — Carência ≠ detecção garantida.** 48 h é a janela para a comunidade detectar uma versão
  maliciosa com procedência válida; ninguém mediu essa latência de detecção.
- **R-15 — Downgrade dentro do registro.** Qualquer versão registrada e fora de quarentena é aceita; a
  defesa contra versão ruim conhecida é a quarentena, que é manual.

## §20 Consequências

- (+) O hook deixa de exigir cerimônia por versão; o Owner assina por GERAÇÃO de modelo (eixo 2), não
  por versão da CLI (eixo 1).
- (+) Nenhum trabalho longo dentro de guard: a classe «trabalho longo dentro de guard vira allow por
  timeout» (risco novo do ajuste 46) fica fechada para a W3.
- (+) Cada aceitação vira evidência durável; o mismatch do pin passa a ser evento, não stderr.
- (+) A trilha de release não muda: mesma âncora, mesmo validador, mesma faixa.
- (−) Cada adoção baixa ~331 MB e gasta um canário de cota do Codex.
- (−) O pin anda ~2 dias atrás da `latest`.
- (−) A W3.6 depende do pacote de kernel do evento, em série com a W1a do PLAN-195.
- (−) O Gate 4 da fase 6 reprova com o global auto-pinado (por desenho; a trilha de release usa a rota 2).
- (−) Mais uma superfície de estado local (o registro), com o resíduo de mesmo UID.

## §21 Raio de explosão, pacotes e reversibilidade

- **Pacote 1 (W3):** este AMEND-1 (canônico), `.claude/hooks/check_pair_rail.py` (kernel), o
  verificador novo, teste(s) novos, `docs/CROSS-LLM-THREAT-MODEL.md` (T-8),
  `.claude/governance/gate-scripts-manifest.txt` (ADR-192), mais o índice de ADR e os documentos de
  contagem que o arquivo de emenda arrasta (exceção (4) da regra de WIP).
- **Pacote 2 (W3):** `.claude/hooks/_lib/codex_cli_shape.py` (eixo 2; depois da W3b),
  `.claude/scripts/codex_invoke.py`, `.claude/scripts/run-promotion-gate.py`.
- **Pacote de kernel (à parte, em série com a W1a do PLAN-195):** `_lib/audit_emit.py`, SPEC do
  audit-log, contagens.
- **Fora:** `codex-cli-pin.txt`, o manifesto, o validador, o `release.yml`. O oráculo `--is-canonical`
  roda em todos os paths na abertura de cada pacote.
- **Reversibilidade: ALTA** para a extensão de confiança — reverter o diff do hook deixa o registro
  inerte, e apagar o registro é a direção segura. **MÉDIA** para o registro de ações no kernel (ações
  registradas ficam).

## §22 Alternativas consideradas

| opção | decisão | por quê |
|---|---|---|
| A — conferir procedência dentro do hook, na 1.ª invocação | rejeitada | C1: timeout de 210 s ⇒ allow; o kernel passaria a processar entrada de rede |
| B — re-pin manual por versão (ADR-182 §5) | plano B | o Owner recusou como rotina (~1 cerimônia/dia) |
| C — re-pin do manifesto por script dentro do kit de corte | adiada (follow-up) | tira a cerimônia dos cortes sem trocar a âncora; não serve o hook |
| D — cache do hash por (caminho, mtime, tamanho) | rejeitada | Unseen 10; exige emenda própria e fail-closed em dúvida |
| E — registro dentro da árvore git | rejeitada | suja o SIGN (R-DO14) e vira 2.ª fonte de verdade versionada |
| F — registro em `state/` | rejeitada | alcance do GC da W2 (MF-W3-5) |
| **G — verificador próprio + registro local só-acréscimo + hook só-consulta + evento HMAC** | **escolhida** | fecha C1–C8 sem tocar a trilha de release |

## §23 Rastreabilidade — must-fix do portador do VETO

| MF | exigência (resumo) | endereçado em |
|---|---|---|
| MF-W3-1 | todo «presente, mas não verificado» fail-CLOSED; registro ausente = sem confiança extra; «bloqueia até verificar ou reinstalar» | §3 I2/I5, §4.3, §7, §8 (A-01..A-23, H-03..H-07), §18 item 1 |
| MF-W3-2 | rede, download e tarball fora de qualquer guard; hook só hash e consulta; diretório confinado, `df`, tetos, limpeza | §3 I3, §4.1, §4.4, §7, H-12 |
| MF-W3-3 | medir o verificador sigstore do npm (W0.6); senão decisão escrita do Owner; proibida cripto à mão | §4.2 V-5 e proibições, §6, A-15, §19 R-1 |
| MF-W3-4 | identidade fixada; chave = sha do único membro regular no caminho exato, em fluxo; gramática estrita | §5 item 1, §6, A-07, A-13, A-14, A-17 |
| MF-W3-5 | registro fora de `state/`, 0700/0600, só-acréscimo, evidência completa; leitores; `verified` × `verified_auto`; contrato por consumidor; resíduo de mesmo UID | §9, §10, §8.C, §19 R-5 |
| MF-W3-6 | aceitação = evento durável em `_KNOWN_ACTIONS`; pacote de kernel em série com a W1a do PLAN-195; promover o `pin_mismatch`; alternativa só por decisão escrita | §3 I6, §11, A-22, §19 R-3 |
| MF-W3-7 | verificar → sondar → aceitar; sonda reprovada impede a aceitação | §3 I4, §4.2 (V-8 depois de V-7), A-19, A-20, §17 |
| MF-W3-8 | modelo e esforço explícitos; `--ignore-user-config` se a sonda confirmar + medição de `memories`; registro por rodada | §12, §19 R-4 |
| MF-W3-9 | carência ≥ 48 h no relógio do registro, constante canônica; `latest` necessária nunca prova; sem `deprecated`; ≥ piso | §5 (com a regra de escolha do consenso §2(a): nunca «== `latest`»), A-08..A-11 |
| MF-W3-10 | chamadores automáticos pelo núcleo ou declarados com o opt-in, antes da W3.6 | §13, §19 R-9 |
| MF-W3-11 | faixa intocada; T-8 no mesmo pacote; (W3.6 depois da W7 — REFUTADO pelo disco, consenso §2(c)) | §15, §16, §18 |

## Referências

- `.claude/adr/ADR-182-codex-payload-pin-enforcement.md` (§2 `:85-128`, §3 `:130-141`, §4 `:143-164`,
  §5 `:166-184`, §Consequences `:205-224`).
- `.claude/plans/PLAN-194/debate/round-1/consensus.md` (§0, §2(a), §2(c), §2(e), §6, ajustes 18–34,
  decisões 3–6); `security-engineer.md` (MF-W3-1..11, Unseen 8, 10, 11); `devops-engineer.md` (must-fix
  9–18, R-DO1..R-DO14); `qa-architect.md` (must-fix 9–13, tabela W3-5).
- `.claude/plans/PLAN-194-maintenance-train-v1-4-3.md` §W3 (perguntas 1–7, W3.1–W3.6, plano B).
- Código: `.claude/hooks/check_pair_rail.py`; `.claude/governance/codex-cli-pin-manifest.json`,
  `codex-cli-pin.txt`; `.claude/scripts/local/pair-rail-gate.sh`; `.claude/hooks/_lib/codex_cli_shape.py`;
  `.github/workflows/release.yml` passo 15; `PLAN-192/repass-ga/run-ga-repass.sh` e
  `PLAN-193/repass-ga/run-ga-repass.sh` (rota 2); `.claude/hooks/_lib/runtime_paths.py`;
  `.claude/hooks/_lib/audit_emit.py`; `docs/CROSS-LLM-THREAT-MODEL.md` §T-8.
- ADR-111 §2 (gatilho de 5 pp), ADR-192 (manifesto de gate scripts), ADR-001 (resolvedor de estado),
  ADR-055-AMEND-3 (precedente de breadcrumb — não se aplica), ADR-081 (estimativas em tokens/sessões).
