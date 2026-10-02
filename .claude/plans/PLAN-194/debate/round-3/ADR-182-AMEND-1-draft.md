---
adr_id: ADR-182-AMEND-1
amends: ADR-182
title: Pin automático verificado do Codex CLI — verificador em processo próprio (orquestrador Python + auxiliar node com sigstore sob política), registro local só-acréscimo e protegido, hook só-consulta, promoção pelos bytes verificados e matriz de recusa fail-closed
status: PROPOSED
debate_status: "design-coherent na rodada 3 (PROCEED 3/3; debate único do PLAN-194 FECHADO). VETO de Segurança RETIRADO, condicionado à decisão 3 do Owner ESCRITA como ramo (ii) ou ramo (i); «confiança no registro» ⇒ VETO segue LEVANTADO ⇒ ESCALATE-TO-OWNER"
draft: true
draft_revision: "r4 — consenso FINAL da rodada 3 aplicado (§4, itens 18–32; condições de execução 1–23 da §2; decisões na forma da §5). Base: o rascunho r3 em round-2/, mantido INTACTO como registro"
draft_note: "RASCUNHO do texto do pacote de ADR (1b). NÃO é o arquivo canônico: o canônico nasce só no pacote de ADR, com SIGN, com o nome proposto .claude/adr/ADR-182-AMEND-1-codex-auto-pin-provenance.md (oráculo 1)."
proposed_at: 2026-10-02
proposed_by: "CEO (S361 — PLAN-194 W3.2; consensos das rodadas 1, 2 e 3; r3 = §2 condições 1–23, §4 itens 18–32, §5 decisões)"
decided_by: "pendente — a decisão 3 do Owner ESCRITA (ramo (ii) ou ramo (i)) é a condição da retirada do VETO; as decisões 4, 5 e 6 são escritas antes do pacote de ADR (1b); depois, a cerimônia GPG do pacote 1b. Nenhuma decisão do Owner foi tomada até esta revisão"
risk_tier: A
debate_required: true
debate_record:
  - .claude/plans/PLAN-194/debate/round-1/consensus.md (W3 RUN-ANOTHER-ROUND; VETO LEVANTADO; MF-W3-1..11)
  - .claude/plans/PLAN-194/debate/round-2/consensus.md (W3 RUN-ANOTHER-ROUND; VETO LEVANTADO até MF-R2-W3-1..8 + escolha (i)/(ii) do Owner; «confiança no registro» ⇒ ESCALATE)
  - .claude/plans/PLAN-194/debate/round-3/consensus.md (FINAL — W3 PROCEED 3/3, design-coherent; VETO RETIRADO condicionado à decisão 3 escrita; 23 condições de execução; 32 ajustes; approved.md pendente da ratificação do Owner)
measurement_record: "W0.6 do PLAN-194 (2026-10-02, 00:53Z–01:15Z; resumo no LEDGER do PLAN-194; relatório completo fora do repositório, no checkpoint da sessão S361)"
veto_floor: ADR-052 (security-engineer VETO — cadeia de suprimento, T-8 do docs/CROSS-LLM-THREAT-MODEL.md)
related_plans: [PLAN-194, PLAN-195, PLAN-163, PLAN-081]
related_adrs: [ADR-182, ADR-111, ADR-052, ADR-055-AMEND-3, ADR-001, ADR-081, ADR-149, ADR-161, ADR-192]
amends_targets:
  - ADR-182 §2 (tabela de braços — linha «payload sha256 != manifest entry»)
  - ADR-182 §3 (um núcleo, três consumidores)
  - ADR-182 §5 (cerimônia de atualização do pin, inclusive o passo 5)
  - ADR-182 §Consequences (o cache futuro por caminho/mtime/tamanho)
  - docs/CROSS-LLM-THREAT-MODEL.md §T-8, itens 1 e 5 da mitigação (no MESMO pacote)
  - SBOM.md (escopo da afirmação «stdlib-only» = runtime dos hooks; ferramenta de mantenedor declarada; no MESMO pacote)
unchanged_explicitly:
  - codex-cli-pin-manifest.json (formato, dono, cerimônia — nenhuma automação escreve nele)
  - codex-cli-pin.txt (faixa >=0.128.0,<0.157.0 intocada na W3)
  - validate-pair-rail-verdict.py e o passo 15 do release.yml
  - os braços INFRA do ADR-182 §2 (manifesto ausente/ilegível, lançador ou payload ausente)
  - o runtime dos hooks continua stdlib-only (o node entra só no verificador, ferramenta de mantenedor fora de hook)
---

# ADR-182-AMEND-1 — Pin automático verificado do Codex CLI

## §0 Como ler este rascunho

- **Estado.** PROPOSED; **`design-coherent` na rodada 3** (PROCEED 3/3; o debate único do PLAN-194 está
  FECHADO). Este texto (r4) aplica o consenso FINAL da rodada 3 e é o texto do pacote de ADR (1b). Não
  autoriza pacote nenhum: os pacotes da W3 só começam depois que a **decisão 3 do Owner estiver
  ESCRITA** como ramo (ii) ou ramo (i) (§7, §22) — é ela que retira o VETO de Segurança. Se a decisão 3
  for «confiança no registro», o VETO segue LEVANTADO e a W3 vai ao Owner por múltipla escolha
  (ESCALATE-TO-OWNER); o `design-coherent` da W3 deixa de valer. As 23 condições de execução do
  consenso r3 (§29) são pré-condição do SIGN do pacote correspondente, conferidas no rail (V2), sem nova
  rodada.
- **Legenda.** **[disco]**: conferido no HEAD `304ec478` (as âncoras de código citadas foram reconferidas
  nesta revisão). **[W0.6]**: medição de 2026-10-02 (células V-*, L-*, S-*; números citados pelo
  relatório). **[consenso]**: conferido pelo sintetizador da rodada 1, 2 ou 3. **[a medir no pacote
  1a/1b/1c]**: não foi exercitado e é medido, com vermelho e verde, antes de o pacote valer (resultado no
  LEDGER, com substrato). **[Owner]**: depende de decisão escrita do Owner (§22). **[oráculo N]**: valor
  de `check_canonical_edit.py --is-canonical` para o path, medido nesta revisão.
- **Repositório público.** Classes de defeito, invariantes e ids de lane. Nenhum caminho da pasta
  privada do Owner. Nenhuma receita de contorno de guarda: costuras de teste, sumidouros de teste e o
  kill-switch do ADR-182 §2 são citados pela FUNÇÃO, nunca pelo literal.
- **Duas afirmações da r2 eram FALSAS diante da W0.6 e estão corrigidas aqui:** o verificador NÃO é
  «stdlib-only» (a assinatura só se confere chamando `node` com a biblioteca sigstore; §4.1), e os
  downloads NÃO ficam todos «no MESMO host» (o TUF do Sigstore vem de um 2.º host; §4.4).
- **Rastreabilidade.** §29: condições de execução 1–23 do consenso r3 → seção. §27: MF-R2-W3-1..8 →
  seção. §28: lista (b) 1–23 do consenso da rodada 2 → seção. §26: MF-W3-1..11 da rodada 1.

### §0.1 O que mudou na r4 (consenso FINAL da rodada 3)

| tema | r3 | r4 |
|---|---|---|
| status | entrada da rodada 3 | `design-coherent` na rodada 3; `decided_by` pendente da decisão 3 |
| I8 / H-07 | «só confia em linhas gravadas por verificador do ADR-192» (sobre-afirmava) | «linhas que DECLARAM shas listados no ADR-192»; o hook não prova quais bytes escreveram; resíduo nomeado e documentado por teste (H-14) (§3, §4.1, §8) |
| fontes do verificador | só sob ADR-192 (detecção no CI) | guarda contra edição do PRÓPRIO agente (W-07..W-09), landada ANTES do 1.º LAND do 1a (§9.W, §10.4) |
| ids imutáveis | fallback pelo statement | ordem honesta: (a) extensões do certificado-folha verificado pelo parser da própria biblioteca; (b) só por último o statement, declarado como proteção REDUZIDA; S-13/S-14 pré-condição do SIGN do 1a (§6) |
| camada 2 | SKIP = falha só na bateria | MODO OBRIGATÓRIO por variável; Checks do plano o ligam; CI sem `node` = SKIP contado e impresso (§19.2) |
| guarda de rede do filho | [a conferir] | controle positivo VERMELHO antes de qualquer resultado contar; mecanismos de troca (§19.3) |
| P-04 / K-06 | proxy morto | P-04: Fase 2 offline com opções EXPLÍCITAS de proxy e controle positivo de cache vazio; K-06: a materialização do kit segue ONLINE com cache novo, e só o CONTROLE DE FALHA (cache vazio + offline + proxy morto explícito ⇒ falha) se repete (§4.3, §9.P, §9.K) |
| censo | sem as células do boot | B-01..B-04, A-26, fronteiras de relógio T-01..T-04, constante do F-06; o censo afirma que cada teste está na seleção do Check (§9, §19.4) |
| rollback | Fase 1 inteira (com canário) | PULA o canário para sha já registrado ou versão do manifesto; rota de EMERGÊNCIA; modo de execução (§15) |
| instrumento | — | re-verificação logo depois de todo LAND do instrumento (§23, §24) |
| pacotes | 1a = 8 / 7 | contagem com o oráculo por path; o `env-inventory.json` (condição 13) leva o 1a a 9 / 8 — conflito declarado (§24) |
| CLI | `pin_source` | `status == "verified_auto"` E `pin_source == "registry"`; flag DEPOIS do caminho (§11, §19.5) |
| W7 | — | 1b antes da derivação do kit; rota 2 invertida pode ser a 1.ª peça da W7.1; ensaio só-verificação contra a 0.156.1 (§18) |

### §0.2 O que mudou na r3 (desde a r2; histórico)

| tema | r2 | r3 |
|---|---|---|
| assinatura (V-5) | «mecanismo medido na W0.6», [a medir] | `sigstore.verify` COM política (SAN exato, emissor exato, ids imutáveis), sobre os bundles que o verificador buscou; nunca `npm audit signatures` (§4.2, §6) |
| A-12 / A-14 / A-15 | A-15 «aceita e declarada» se a W0.6 reprovasse | os DOIS bundles exigidos pelo verificador; A-14 e A-15 = RECUSA (§9.A) |
| âncora do vínculo | `dist.integrity` | digest do `subject` do bundle VERIFICADO, lido dos mesmos bytes; `dist.integrity` só cruzamento (§4.2 V-6) |
| composição | «stdlib-only» (FALSO) | orquestrador Python + auxiliar `node`, exceção NOMEADA, sob ADR-192 (§4.1) |
| hosts | «MESMO host» (FALSO) | lista FECHADA: registro + CDN do TUF do Sigstore (§4.4) |
| caches | não tratados | npm e TUF NOVOS a cada execução, com asserção de vazio (§4.4, F-08) |
| tetos | [a medir] | valores medidos (§4.4) |
| empacotamento | — | decisão 3 do Owner: ramos (ii) e (i) com testes pré-registrados; «confiança no registro» = ESCALATE (§7) |
| promoção | `npm i -g` novo + P-01 só do `bin/codex` | bytes verificados, sob proxy morto, P-01 da ÁRVORE inteira, quiesce (§4.3) |
| registro × agente | «a conferir» (R-5) | guarda contra escrita do PRÓPRIO agente, com controle positivo, landada antes de o núcleo ler o registro (§10.4) |
| rota 2 do kit | «inverter OU declarar» (R-12) | INVERTIDA, pré-condição da W3.6; o R-12 sai (§17) |
| rollback | «verifica offline» | R-16: exige rede (§15) |
| pacotes | 1 + 2 + kernel | 1b → 1a → 2 + kernel; `SBOM.md`; manifesto ADR-192 (§24) |
| `_emit_audit()` | ligar «no pacote 1» | ligado ao `emit_generic` no pacote 1b; sumidouro de teste só no modo de teste (§12) |

## §1 Contexto

### 1.1 O que o ADR-182 deixou

O ADR-182 fechou o T-8 pinando o PAYLOAD nativo (não o lançador) num manifesto assinado
(`.claude/governance/codex-cli-pin-manifest.json`, hoje 0.156.1, um único triple `aarch64-apple-darwin`
**[disco]**), com um núcleo único `verify_codex_payload()` (`check_pair_rail.py:589-747` **[disco]**)
consumido pelo hook, pelo Gate 4 do `.claude/scripts/local/pair-rail-gate.sh` (`:179-221` **[disco]**) e
pelo validador do passo 15 do `release.yml` (`:708-763` **[disco]**). Toda versão nova exige a cerimônia
do §5 (edição do manifesto sob sentinela, GPG do Owner).

### 1.2 Por que mudar agora

- **Decisão do Owner (S359, 2026-09-30):** «Pin automático verificado (Recomendado)» — não mexer nisso
  a cada versão. O re-pin manual vira plano B.
- **Cadência medida [consenso]:** 23 estáveis desde 2026-08-25, mediana de 22,0 h entre versões, 16 de 22
  intervalos abaixo de 48 h. Cerimônia por versão = ~1 cerimônia por dia.

### 1.3 O que a W0.6 mediu (e que muda a decisão)

- **O comando `npm audit signatures` NÃO serve [W0.6].** Ele verifica o que o REGISTRO declara, não os
  bytes locais: payload adulterado instalado ⇒ exit 0 (V-T2, V-R1); atestado REMOVIDO ⇒ exit 0 (V-P3);
  sem rede com cache quente ⇒ exit 0 (V-N1, V-N3); e não fixa identidade: atestado válido de OUTRO
  repositório passa (S-11, sem política).
- **`sigstore.verify` chamado COM política SERVE [W0.6].** Verde no íntegro (0.160.0 e 0.156.1, S-02,
  S-10); REJECTED em ref, repositório e emissor errados (S-03..S-05), em 1 byte do `subject`, da
  assinatura DSSE e do certificado (S-06..S-08), na entrada do Rekor removida (S-09) e no atestado de
  outro repositório (S-12).
- **O vínculo em stdlib pega o adulterado [W0.6]:** sha512 do tarball baixado = digest do `subject` do
  bundle verificado (L-G1, L-G2; adulterado diverge, L-T2); sha256 do membro `bin/codex` lido em fluxo
  (L-P1 = manifesto assinado `0196e89f…`; adulterado diverge, L-P3); 44 membros regulares, 0 links,
  0 duplicatas (L-M).
- **Fatos de forma [W0.6]:** o TUF do Sigstore vem de `tuf-repo-cdn.sigstore.dev` (2.º host);
  `@openai/codex-darwin-arm64` é ALIAS (404 como pacote; o artefato é `@openai/codex@<X.Y.Z>-darwin-arm64`);
  o pacote de plataforma traz executáveis IRMÃOS fora do sha pinado (`bin/codex-code-mode-host`,
  `codex-path/rg`, `codex-resources/voice/bin/codex-voice-host`, `codex-resources/zsh/bin/zsh`, dylibs).

### 1.4 O que as rodadas 1 e 2 acharam (e que este texto corrige)

| achado | origem | correção aqui |
|---|---|---|
| verificar procedência DENTRO do hook (timeout 210 s) vira allow por timeout | r1 C1 | §4, §8: verificador em processo próprio; o hook nunca usa rede |
| «sem rede / sem atestado» como INFRA = o rail some (allow, `check_pair_rail.py:1512-1524` [disco]) | r1 C2 | §9: todo «presente, mas não verificado» é fail-CLOSED |
| «o rail segue na última verificada» é falso com `npm i -g` | r1 L-9 | «bloqueia até verificar ou reinstalar a versão verificada»; vale «segue na última» só pela promoção do verificador (§4.3) |
| comparar dois campos da mesma resposta não é autenticidade | r1 C3 | §4.2 V-5, §6, §7 |
| a sonda executa o binário | r1 C4 | verificar → sondar → aceitar (§4.2) |
| registro = 2.ª fonte de verdade | r1 C5 | §10, §11 |
| modelo e esforço herdados do config global | r1 C6 | §13 |
| o AMEND-1 contradiz a W0.6 («stdlib-only», «MESMO host», `dist.integrity` cru, A-15 «declarada», A-12 delegada ao npm) | r2 C8 | §4, §6, §7, §9.A |
| a promoção reabre a janela registro → disco para os irmãos | r2 C9 | §4.3 (bytes verificados + P-01 da árvore inteira) |
| a rota 2 do corte executa antes de verificar e roda o lançador | r2 C10 | §17 (rota 2 invertida, shim no `path` verificado) |
| a decisão 3 do plano induzia à variante mais fraca | r2 C11 | §7, §22 |
| `SBOM.md` e ADR-192 | r2 C12 | §4.1, §24 |
| Checks da W3 vácuos ou vermelhos depois da W3.6; literal divergente | r2 C13 | §11, §19.5 |

## §2 Escopo honesto — o que o pin protege

- O pin protege a **identidade e a integridade do REVISOR** cujo veredito o framework registra (o par
  cruzado do rail). Ele **não protege a máquina**: o Owner roda o app e a CLI do Codex fora do
  framework, e um binário malicioso já teria executado ali antes de qualquer hook.
- **Executáveis irmãos.** O hook confere a cada invocação SÓ o `bin/codex` (o payload que ele executa).
  Os irmãos do pacote de plataforma (`bin/codex-code-mode-host`, `codex-path/rg`,
  `codex-resources/voice/bin/codex-voice-host`, `codex-resources/zsh/bin/zsh`, dylibs) e o lançador são
  conferidos UMA vez, na promoção, contra o manifesto de membros do tarball verificado (P-01, §4.3). A
  troca deles DEPOIS da promoção, em tempo de execução, é resíduo de mesmo UID (§21 R-5, R-6), e um
  teste documenta que o hook segue `verified_auto` nesse caso (H-13).
- Vale **só para este repositório**. Adopters não recebem `.claude/governance/`; neles o pin resolve
  como INFRA (aberto), como hoje (`CLAUDE.md` §4). Estender o pin automático aos adopters é onda própria.
- **Procedência prova a origem, não a benignidade.** Um comprometimento do próprio repositório
  `openai/codex` ou do workflow de release produz atestado VÁLIDO com a identidade certa [W0.6 §6.9]; a
  carência de 48 h é a única mitigação (§21 R-14).

## §3 Decisão — visão geral

```
  Owner (comando explícito; ≤ 1×/semana ou sob demanda)
        │
        ▼
  ┌──────────────────────────────────────────┐   hosts: SÓ registro npm + CDN do TUF
  │ VERIFICADOR (processo próprio, fora de    │   caches npm e TUF NOVOS a cada execução
  │ qualquer guard) — sob ADR-192              │
  │  orquestrador Python ──► auxiliar node    │   sigstore.verify COM política
  │  Fase 1: staging → procedência → vínculo  │
  │    → sonda/canário → evento HMAC → linha  │──► cadeia HMAC (evento durável, §12)
  │  Fase 2: promoção pelos BYTES verificados │──► REGISTRO local só-acréscimo (§10)
  │    (proxy morto, quiesce, P-01 da árvore) │       protegido contra escrita do agente
  └──────────────────────────────────────────┘
                                                ▲ leitura local, sem rede
  ┌──────────────────────────────────────────┐ │
  │ NÚCLEO verify_codex_payload()             │─┘ (consulta ao registro só no hook e na CLI com flag)
  │  hash do bin/codex + consulta             │◄── manifesto assinado (inalterado)
  └──────────────────────────────────────────┘◄── manifesto ADR-192 (shas permitidos do verificador)
     ▲ hook (manifesto ∪ registro)   ▲ CLI (só-manifesto por padrão)   ✗ release, envelope, kit, runner
```

**Invariantes (o rail de cada pacote audita o texto contra eles):**

- **I1.** O manifesto do Codex continua a ÚNICA âncora assinada. Nenhuma automação escreve nele. A
  trilha de release segue ancorada no manifesto da árvore tagueada.
- **I2.** O registro só **ACRESCENTA** confiança a um sha fora do manifesto, e só para um triple que o
  manifesto já tem. Nunca retira a confiança do manifesto. Qualquer dúvida sobre o registro = **zero
  confiança extra**, nunca INFRA.
- **I3.** O hook nunca usa rede, nunca baixa, nunca executa antes do hash, e hasheia o `bin/codex` a
  cada invocação: nenhum atalho por mtime ou tamanho. O runtime dos hooks segue stdlib-only.
- **I4.** Nada executa bytes não verificados: nem o verificador (sonda e canário só depois do vínculo),
  nem a promoção (só os bytes verificados), nem o kit de corte (rota 2 invertida, §17), nem os chamadores
  livres (§14).
- **I5.** Todo «binário presente, mas não verificado» é SECURITY fail-CLOSED. INFRA só nos braços que já
  eram INFRA no ADR-182 §2. Toda célula de fronteira do verificador é recusa.
- **I6.** Cada aceitação automática substitui uma assinatura humana, então vira evento durável na
  cadeia HMAC ANTES de a linha do registro existir.
- **I7.** O registro nunca é lido pelo validador do passo 15, pelo `gen-envelope-ga.py`, pelo kit de
  corte nem pelo runner do re-pass.
- **I8 (corrigido na r4 — dizia mais do que o mecanismo prova).** O núcleo só consulta o registro
  depois que a guarda contra escrita do PRÓPRIO agente estiver landada (§10.4), e só confia em linhas
  que **DECLARAM** `verifier_sha256`, `helper_sha256`, `sigstore_pkg_digest` e, no ramo (ii),
  `package_json_sha256` iguais aos shas listados no manifesto ADR-192 da árvore (H-07). **O hook NÃO prova
  quais bytes escreveram a linha:** esses
  valores são autodeclarados pelo processo que grava. O que impede um verificador adulterado de gravar é
  a guarda das FONTES do verificador (W-07..W-09, §10.4), landada antes do 1.º LAND do 1a; o que resta é
  o resíduo nomeado do §21 R-5, documentado por teste (H-14).

## §4 O verificador (MF-W3-2, MF-W3-3, MF-W3-7; MF-R2-W3-1, -3, -4, -7, -8)

### 4.1 Composição, governança e identidade do instrumento

- **Composição — exceção NOMEADA ao «stdlib-only».** O verificador é um **orquestrador Python**
  (stdlib-only, Python ≥ 3.9; nome proposto `.claude/scripts/codex-auto-pin-verify.py`) mais um
  **auxiliar `node`** que chama a biblioteca sigstore (nome proposto
  `.claude/scripts/codex-auto-pin/verify-sigstore.js`). Rede, download, tarball, npm, `node`, sonda e
  canário rodam AQUI, em processo próprio, por comando explícito. **Nunca** dentro de hook, guard,
  `/ceo-boot` ou Workflow. O runtime dos hooks continua stdlib-only: o `node` nunca entra no caminho do
  hook (I3).
- **`node` por caminho absoluto, com versão mínima.** O orquestrador resolve o `node` UMA vez (PATH ou
  flag explícita), exige caminho absoluto de arquivo regular, confere a versão contra a mínima em
  constante canônica (= a do campo `engines` do sigstore fixado no ramo (ii), ou a do npm permitido no
  ramo (i); teste fixa o valor) e grava caminho, versão e sha256 do binário do `node` na linha e no
  evento. Ambiente do `node` montado do zero (`env -i`, `PATH` mínimo, `HOME`/`TMPDIR` no staging,
  nenhuma variável de opções ou de caminho de módulos do node herdada) — F-09.
- **Sob cerimônia (ADR-192).** O verificador `.py`, o auxiliar `.js` e o material do empacotamento
  (ramo (ii): `package.json` + `package-lock.json` com integridade de TODA a árvore; ramo (i): a lista
  canônica de versões e shas de arquivo) entram no manifesto ADR-192
  (`.claude/governance/gate-scripts-manifest.txt`, que é canônico por `.claude/governance/*.txt`
  **[disco]**, `check_canonical_edit.py:232`). Oráculo medido nesta revisão para as FONTES: `.py`,
  auxiliar `.js`, `package.json` e `package-lock.json` = **0** (editáveis pelo agente) — por isso a
  guarda das fontes (§10.4, W-07..W-09) é condição de execução. O ADR-192 DETECTA mudança de bytes no
  CI e no LAND (quem o lê hoje são os workflows de release, publicação, smoke e ownership; nenhum hook o
  lê [consenso r3 §0]); ele não impede edição na sessão.
- **O manifesto ADR-192 é a lista permitida do H-07 — de shas DECLARADOS.** A partir do pacote 1b, o
  núcleo lê, do manifesto ADR-192 da árvore, os sha256 do verificador, do auxiliar e do material de
  empacotamento, e só confia numa linha do registro que **declara** `verifier_sha256`, `helper_sha256`,
  `sigstore_pkg_digest` e, no ramo (ii), `package_json_sha256` IGUAIS a esses valores (um campo por
  arquivo sob o ADR-192: mudar QUALQUER um deles, inclusive só o `package.json`, revoga a linha). **Limite:** o H-07 compara o que a linha DECLARA; não
  prova quais bytes a escreveram. Um verificador editado pelo agente e executado (W-05 permite a
  invocação) declararia os shas legítimos. A defesa contra isso é a guarda das fontes (W-07..W-09); o
  resíduo é nomeado no §21 R-5 e DOCUMENTADO pelo teste H-14 (molde do H-13). Se a guarda das fontes não
  couber antes do 1.º LAND do 1a, o resíduo vai TAMBÉM ao material assinado — nunca fica silencioso.
  Consequências que valem: trocar o verificador é «instrumento mudou» (exige cerimônia ADR-192 e
  re-verificação logo depois do LAND, §24), e uma linha que declara verificador revogado perde a
  confiança sozinha. Manifesto ADR-192 ausente ou malformado ⇒ zero confiança extra (I2).
- **Evidência em repouso (livre, fora do hook).** O check do `/ceo-boot` (`.claude/scripts/ceo-boot.py`,
  [oráculo 0]) compara o sha EM DISCO do verificador, do auxiliar e do lockfile com o manifesto ADR-192 e
  acusa divergência, sem custo no hook (condição 8 do consenso r3). Não fecha a via «editar, executar e
  restaurar»; encurta a janela de uma edição esquecida.
- **Identidade do instrumento gravada** (linha e evento): `signature_mode`, versões de `node`, npm e
  sigstore, `sigstore_pkg_digest` (sha do lockfile no ramo (ii); digest da lista conferida no ramo (i)),
  `package_json_sha256` (só no ramo (ii); ausente no (i)), digest da raiz TUF efetiva depois da
  atualização, `verifier_sha256`, `helper_sha256`, `kernel_sha256`.
- **Reuso do núcleo.** O verificador não re-implementa resolução nem hash de payload: usa as funções e as
  constantes do `check_pair_rail.py` (ADR-182 §3). Por isso o pacote 1b (núcleo) landa ANTES do 1a
  (verificador) (§24).
- **Saídas:** `0` = registrado (ou já registrado, idempotente; ou promovido); `1` = recusado em
  QUALQUER célula A, F ou P (§9), com `cell` no JSON; `2` = uso inválido. Não existe «INFRA com sucesso».

### 4.2 Fase 1 — verificar e registrar (ordem obrigatória)

| passo | o que faz | recusa em |
|---|---|---|
| V-0 | Pré-voo: piso de `df`; diretório de staging NOVO e próprio; caches do npm e do TUF criados vazios DENTRO do staging, com asserção de vazio; `node` e material de empacotamento conferidos (§4.1, §7); manifesto ADR-192 legível; ação de aceitação presente no registro de ações do `audit_emit` (§12); registro local legível e confiável; guarda do registro landada (I8) | A-06, A-22, A-23, F-01..F-03, F-08, F-09 |
| V-1 | Metadado: packument completo de `@openai/codex` por `urllib`, HTTPS com verificação de certificado, da URL-base CONSTANTE do registro; teto; guarda o cabeçalho `Date` | A-01..A-05 |
| V-2 | Seleção da candidata pela regra da §5 | A-07..A-11 |
| V-3 | Tarballs do LANÇADOR (`<X.Y.Z>`) e da PLATAFORMA (`<X.Y.Z>-<sufixo>`) baixados por `urllib` da URL `dist.tarball`, só de host da lista fechada, em fluxo, com teto; sha512 em fluxo de cada um | A-03, A-05 |
| V-4 | Bundles: o verificador busca ele mesmo os atestados dos DOIS pacotes e exige o bundle de procedência SLSA v1 de cada um; falta de qualquer um ⇒ recusa (o npm não reprova a falta, V-P3) | A-12, A-13 |
| V-5 | Assinatura e identidade: o auxiliar `node` chama `sigstore.verify` sobre os bytes de CADA bundle (os mesmos que V-4 gravou no staging), com a política da §6 (SAN exato, emissor exato, ids imutáveis), com o cache TUF NOVO do staging e só o host do TUF da lista fechada; devolve JSON com o veredito por bundle, a política efetiva usada e o digest do `subject` lido do statement VERIFICADO. Nunca `npm audit signatures` | A-14, A-15, F-01..F-07 |
| V-6 | Vínculo: o orquestrador lê o `subject` dos MESMOS bytes do bundle (parse próprio) e exige igualdade com o que o auxiliar devolveu; sha512 de V-3 == digest do `subject` VERIFICADO, para os dois pacotes; `dist.integrity` do packument == o mesmo valor (só cruzamento); campos do statement verificado iguais às constantes (§6) | A-16, A-25 |
| V-7 | Membros: no tarball de plataforma verificado, o ÚNICO membro regular no caminho exato `package/vendor/<triple>/bin/codex`, lido em fluxo sem extrair, sha256 com teto; e o **manifesto de membros** (caminho, tamanho, sha256, tipo, modo) dos DOIS tarballs; qualquer link, duplicata ou membro não regular ⇒ recusa | A-17 |
| V-8 | Staging SEM execução: materializa lançador + plataforma na versão EXATA num prefixo NOVO do staging, com scripts de ciclo de vida suprimidos e ambiente do npm montado do zero (§4.4); a ÁRVORE materializada dos dois pacotes é comparada membro a membro com os manifestos de V-7 (lista fechada de arquivos de controle do npm fora dos pacotes, cada um com teste) | A-04, A-18 |
| V-9 | Sonda (só agora o binário roda, e é o `bin/codex` VERIFICADO do staging, executado direto, como o hook faz): subcomandos `exec`, `review`, `app-server` e a união das FLAGS dos chamadores (`--sandbox`, `-o`/`--output-last-message`, `--output-schema`, `--color`, `--model`/`-m`, `--skip-git-repo-check`, `-c`, `--ignore-user-config` se adotada, e o ajuste de esforço na forma confirmada) | A-19 |
| V-10 | Canário funcional: um `exec` mínimo com o argv REAL do rail (§13) sobre um diff SINTÉTICO fixo (sem conteúdo do repositório — egresso), devolvendo JSON de veredito parseável na forma esperada; política de nova tentativa pré-registrada (§4.5); obedece ao freio Q2 | A-20 |
| V-11 | Quarentena consultada: (versão, triple, sha) em quarentena ⇒ recusa permanente | A-21 |
| V-12 | Evento `codex_auto_pin_accepted` (nome proposto) emitido e CONFIRMADO na cadeia HMAC (o verificador drena o próprio spool fora de qualquer guard; a forma de confirmação é do builder). Sem confirmação ⇒ não registra | A-22 |
| V-13 | Linha de aceitação acrescentada ao registro (§10), sob trava própria, com `fsync` do arquivo e do diretório | A-23 |
| V-14 | Se `--promote`: Fase 2 (§4.3) NESTA execução, antes da limpeza | P-01..P-05 |
| V-15 | Limpeza confinada do staging (caches, prefixo, tarballs); o staging nunca é caminho de execução do rail | — |

**Proibições:** criptografia de assinatura escrita à mão; `npm audit signatures` como decisão; chamar de
«assinatura conferida» a comparação de dois campos da mesma resposta do registro; ler identidade de um
certificado que a stdlib não verificou (a API privada de decodificação de certificado do CPython não
serve, W0.6 §2.3); desligar verificação de certificado TLS diante de cadeia de CA ausente (A-02).

### 4.3 Fase 2 — promoção pelos BYTES verificados (MF-R2-W3-4)

- **Só na MESMA execução** de uma Fase 1 verde para aquela versão (P-02): os bytes verificados e o cache
  do staging só existem até a limpeza de V-15. Não há promoção «à mão» suportada de versão
  auto-pinada; a única instalação crua prevista é a rota de EMERGÊNCIA da versão do manifesto (§15).
- **Quiesce (P-03).** Antes de instalar, o verificador recusa se algum processo estiver executando o
  payload ou os irmãos do prefixo global, conferido por `lsof`/`ps` sobre o CAMINHO, nunca por
  `pgrep -f`. A recusa NOMEIA o PID e o caminho do executável de cada processo (o daemon `app-server` e o
  app do Codex são os candidatos), e o procedimento do runbook lista o que parar (§15). A promoção é
  declarada janela curta de manutenção, com as rodadas de rail paradas. Um hook de outra sessão que
  hashear no meio da troca dá `mismatch` e BLOCK (seguro; ruído declarado).
- **Mecanismo.** Instalação global da versão EXATA a partir do cache do staging que a Fase 1 verificou,
  com o mesmo ambiente de npm montado do zero, scripts suprimidos e prefixo global explícito, igual ao do
  lançador do PATH (P-05).
- **P-04 — prova de zero busca, com opções EXPLÍCITAS (condição 12 do consenso r3).** O `env -i` do
  ambiente do npm REMOVE as variáveis de proxy, então o proxy morto não pode depender delas: a Fase 2
  passa ao npm o modo **offline** e as opções **explícitas** de proxy apontando para um proxy morto (o
  método da W0.6, V-N2/V-N4). Qualquer busca no registro falha ⇒ recusa. **Controle positivo [a medir no
  pacote 1a]:** com o cache do staging ESVAZIADO e o proxy morto explícito, a Fase 2 tem de FALHAR; se
  passar, o mecanismo não prende o npm e a «prova de zero busca» não vale (o pacote não landa).
- **P-01 da árvore inteira.** Depois de instalar, a árvore global do lançador e do alias de plataforma é
  comparada membro a membro (caminho, tamanho, sha256, tipo) com os manifestos de V-7; nenhum
  executável ou arquivo extra fora da lista fechada de exceções do npm; o link de `bin` aponta para o
  lançador promovido. Depois, o verificador roda o núcleo no caminho do hook sobre o lançador do PATH:
  tem de dar `verified_auto` (ou `verified`, na versão do manifesto). Divergência ⇒ P-01 (o hook já
  bloqueia se o `bin/codex` divergir; o verificador manda ao rollback, §15).
- **A linha do registro grava os manifestos de membros** (para conferência posterior fora de hook,
  `--check-installed`, §15).
- **Versão do manifesto.** O mesmo caminho serve para (re)instalar a versão do manifesto pelos bytes
  verificados: Fase 1 sem linha nova (a confiança vem do manifesto), Fase 2 igual.
- Com as duas fases, «o rail segue na última versão verificada» é verdade **para quem usa a rota do
  verificador**: o global só é sobrescrito depois da aprovação. Para um `npm i -g` cru, vale: **bloqueia
  até verificar ou reinstalar a versão verificada** (MF-W3-1); se o cru instalar uma versão JÁ
  registrada, o `bin/codex` confere, mas os irmãos vêm de busca nova não conferida (§21 R-19).

### 4.4 Rede, caches, disco e tetos (MF-W3-2; MF-R2-W3-3)

- **Lista FECHADA de hosts:** o registro npm (URL-base em constante) e `tuf-repo-cdn.sigstore.dev`
  (espelho TUF em constante). Toda URL que o orquestrador busca (packument, tarballs, atestados) tem de
  estar no host do registro; o auxiliar recebe o espelho TUF explícito; o npm recebe o registro
  explícito. Redirect para fora da lista ⇒ A-03. A lista é imposta por configuração explícita de cada
  cliente e por asserção no orquestrador, não por filtro de rede de processo (§21 R-18).
- **Caches NOVOS a cada execução** (npm e TUF), criados dentro do staging e afirmados VAZIOS no início
  (F-08). Com cache quente, «sem rede» dava verde (V-N1, V-N3); com cache novo, sem rede recusa (V-N2,
  V-N4), coerente com A-01. Proxy do ambiente não relaxa TLS.
- **Ambiente do npm montado do zero** (método da W0.6): `env -i` com `PATH` mínimo, `HOME` e `TMPDIR`
  no staging, `--userconfig` e `--globalconfig` apontando para arquivos VAZIOS e DISTINTOS no staging,
  `--cache` no staging, `--registry` constante, nenhuma `npm_config_*` herdada, scripts de ciclo de vida
  suprimidos, sem auditoria nem fundo. Divergência observada do registro efetivo ⇒ A-04.
- **Tetos medidos [W0.6 §5, §6.7] — 2× o maior medido, em constantes canônicas com teste:**

| objeto | maior medido | teto |
|---|---|---|
| packument completo de `@openai/codex` | 16.779.741 B | ~33,6 MB |
| JSON de atestados (por pacote) | 15.173 B | ~30,3 KB |
| tarball de plataforma (comprimido) | 134.311.083 B | ~268,6 MB |
| tarball do lançador (comprimido) | 4.904 B | ~9,8 KB |
| membro `bin/codex` (descomprimido) | 241.555.024 B | ~483,1 MB |
| descomprimido total do pacote de plataforma | 332.972.398 B | ~666 MB |

  Acima do teto ⇒ A-05 e limpeza confinada. Um teto que reprovar uma versão legítima nova é re-medido e
  atualizado CONSCIENTEMENTE por cerimônia, nunca relaxado em linha.
- **Disco (`CLAUDE.md` §4, regra S358):** staging próprio, limpeza confinada a ele, piso de `df` antes de
  baixar (A-06), em constante (o da W0.6, 60 GB livres, até medição própria).

### 4.5 Cadência e canário

- Adoção sob demanda ou no máximo 1× por semana, sob o freio Q2. O `/ceo-boot` NÃO dispara o
  verificador; no máximo informa (§15).
- **Canário:** diff SINTÉTICO fixo, versionado com o verificador (sob ADR-192); nada do repositório sai
  para o provedor.
- **Política de nova tentativa pré-registrada (A-20):** «inconclusivo» (cota, capacidade, tempo) admite
  no máximo 1 nova tentativa na mesma execução, depois de ≥ 10 min, e no máximo 3 execuções por versão
  por semana; «reprovado» (saída ≠ 0 com resposta, veredito não parseável, forma divergente) NÃO admite
  nova tentativa para aquela versão até mudar o verificador ou o argv (cerimônia). Valores ajustáveis
  pelo CEO ANTES da rodada, nunca depois de um resultado.

## §5 Regra de elegibilidade (MF-W3-9; consenso r1 §2(a))

A candidata é a **estável mais nova** que cumpre TODAS:

1. **Gramática estrita (MF-W3-4).** O lançador tem versão base estável `X.Y.Z` (dígitos, sem zero à
   esquerda, sem pré-release, sem metadado de build). O artefato de plataforma tem versão IGUAL, por
   comparação de string, a `X.Y.Z-<sufixo>`, com `<sufixo>` de uma tabela canônica triple → sufixo só
   com as entradas medidas (hoje uma: `aarch64-apple-darwin` → `darwin-arm64`). O nome
   `@openai/codex-darwin-arm64` é ALIAS do lançador, nunca pacote buscado [W0.6 §5]. Qualquer outro
   pré-release é recusado, inclusive a armadilha medida [consenso]: dist-tag
   `release-0.159.0-alpha.12.1-alpha-darwin-arm64` → `0.159.0-alpha.12.1-darwin-arm64`.
2. **Carência ≥ 48 h, no relógio do registro.** Idade = `Date` (cabeçalho da resposta do registro, sob
   TLS) − `time[...]` do packument, tomando o MAIS TARDIO entre a publicação do lançador e a da
   plataforma. A ordem varia: na 0.160.0 a plataforma saiu ~10 s ANTES do lançador; na 0.156.1, ~4,6 min
   DEPOIS [W0.6 §5]. O relógio local não entra. `Date` ausente ou ilegível ⇒ recusa. Constante `48`
   canônica com teste. A espera é `external_wait`.
3. **≤ `latest`.** A `latest` é TETO, nunca prova; ela própria passa na gramática estrita (senão, nenhuma
   candidata). **Nunca «== `latest`».**
4. **Sem `deprecated`** no lançador nem na plataforma.
5. **≥ piso do manifesto** (`package_version` do manifesto assinado). Monotônico: subir o manifesto por
   cerimônia tira a confiança das entradas abaixo do novo piso (H-07).

Exemplo [consenso], 2026-10-02T00:20Z: 0.160.0 (~4 h) e 0.159.3 (~25 h) não elegíveis; 0.159.2 (~48,3 h)
elegível.

## §6 Identidade fixada do construtor (MF-W3-4; MF-R2-W3-1) — literais medidos [W0.6 §4]

**Política passada a `sigstore.verify` (constantes canônicas, com teste que fixa cada literal):**

| campo da política | valor |
|---|---|
| `certificateIdentityURI` (SAN exato) | `https://github.com/openai/codex/.github/workflows/rust-release.yml@refs/tags/rust-v<X.Y.Z>` — `<X.Y.Z>` = versão BASE, sem sufixo; lançador e plataforma levam a MESMA ref |
| `certificateIssuer` (exato) | `https://token.actions.githubusercontent.com` |
| `certificateOIDs` — id IMUTÁVEL do repositório | OID `1.3.6.1.4.1.57264.1.15` = `965415649` |
| `certificateOIDs` — id IMUTÁVEL do dono | OID `1.3.6.1.4.1.57264.1.17` = `14957082` |

- Os ids imutáveis barram renomeação ou recriação do repositório com o mesmo nome. Eles só protegem se
  vierem do CERTIFICADO: as extensões OID são postas pelo Fulcio a partir das claims do token OIDC; o
  statement é AUTORADO pelo workflow que assina, e num repositório recriado com o mesmo nome quem roda o
  workflow obtém a MESMA SAN (a SAN é o caminho, não o id) e escreve no statement os ids que quiser
  [crítica de Segurança r3, R3-SEC2].
- **S-13/S-14 — pré-condição do SIGN do 1a [a medir no pacote 1a] (condição 10 do consenso r3).** A W0.6
  exercitou SAN e emissor (S-02..S-12), não `certificateOIDs`. Na camada 2 (§19.2), na bateria do LAND do
  1a, com SKIP = falha e ANTES do SIGN do 1a, com a MESMA política: S-13 (id do repositório errado) e
  S-14 (id do dono errado) ⇒ REJECTED; S-02 e S-10 ⇒ VERIFIED. O pré-registro é bidirecional: se a
  biblioteca IGNORAR a extensão, S-13/S-14 ficam VERIFIED e o teste fica vermelho; se REJEITAR o
  legítimo, S-02 fica vermelho. Resultado no LEDGER, com substrato (versões de `node` e sigstore).
- **Ordem de fallback, se `certificateOIDs` falhar** (ignorar a extensão ou rejeitar o legítimo):
  - **(a) primeiro:** as extensões `1.3.6.1.4.1.57264.1.15` e `.1.17` do certificado-folha JÁ VERIFICADO
    pela chamada de `sigstore.verify`, lidas pelo parser X.509 da PRÓPRIA biblioteca sigstore, no
    auxiliar, sem ASN.1 escrito à mão e sem a API privada de decodificação do CPython;
  - **(b) só por último:** os ids do statement VERIFICADO (`internalParameters.github.repository_id`,
    `repository_owner_id`), DECLARADOS no material assinado como proteção **REDUZIDA** («repositório
    recriado com o mesmo nome passa»), porque o statement é conteúdo do próprio assinante.
  - A ordem efetivamente usada vai ao LEDGER, à linha do registro (`identity.ids_source`) e ao evento.

**Cruzamento no statement VERIFICADO (V-6, A-25), por igualdade de string com constantes:**
`predicateType` = `https://slsa.dev/provenance/v1`; `buildDefinition.buildType` =
`https://slsa-framework.github.io/github-actions-buildtypes/workflow/v1`;
`externalParameters.workflow.repository` = `https://github.com/openai/codex`;
`externalParameters.workflow.path` = `.github/workflows/rust-release.yml`;
`externalParameters.workflow.ref` = `refs/tags/rust-v<X.Y.Z>`; `runDetails.builder.id` =
`https://github.com/actions/runner/github-hosted`; `subject.name` = `pkg:npm/%40openai/codex@<X.Y.Z>`
(lançador) e `pkg:npm/%40openai/codex@<X.Y.Z>-darwin-arm64` (plataforma); um único `subject` por bundle.

**Âncora do vínculo:** o digest `sha512` do `subject` do bundle VERIFICADO, lido dos MESMOS bytes que
foram passados ao auxiliar. O `dist.integrity` do packument vira só cruzamento (A-16). A chave de
aceitação é o sha256 do ÚNICO membro regular `package/vendor/<triple>/bin/codex`, lido em fluxo do tarball
cujo sha512 = esse digest. O metadado local (versão relatada pelo lançador) é só dica, nunca prova.

## §7 Empacotamento do verificador de assinatura — decisão 3 do Owner (MF-R2-W3-2)

A W0.6 trocou a pergunta: não é mais «assinatura ou confiança no registro», e sim **como empacotar** a
biblioteca sigstore que o auxiliar chama. Nos dois ramos o verificador passa a depender de `node`, e o
`SBOM.md` declara isso (§24). Os testes do ramo ESCOLHIDO ficam pré-registrados; os do outro saem do
pacote quando o Owner decidir.

### Ramo (ii) — RECOMENDADO

- `sigstore` em versão EXATA, com `package.json` e `package-lock.json` de integridade de TODA a árvore
  (inclusive `tuf-js` e transitivos), commitados sob o manifesto ADR-192 junto do verificador.
- Cada execução copia os dois arquivos para o staging NOVO e roda `npm ci` com scripts suprimidos e o
  ambiente npm montado do zero (§4.4); o orquestrador afirma depois a versão instalada do `sigstore` ==
  a fixada.
- `signature_mode = sigstore-policy:ii`; `sigstore_pkg_digest` = sha256 do `package-lock.json` e
  `package_json_sha256` = sha256 do `package.json`, cada um == a sua linha do ADR-192 (H-07). O
  `package.json` tem campo PRÓPRIO porque o `npm ci` o lê (e recusa divergência com o lockfile): uma
  mudança só nele também é mudança do instrumento.
- **Por que recomendado:** o código que toma a decisão criptográfica fica governado pelo repositório
  (cerimônia), não pelo npm do Homebrew, que se atualiza fora da governança. É a preferência do
  portador do VETO e de outro crítico [consenso r2 §2(h)].
- **Testes pré-registrados do ramo (ii):**
  - (ii-1) lockfile com 1 byte alterado numa integridade ⇒ `npm ci` falha ⇒ F-03 (vermelho) / íntegro ⇒
    verde;
  - (ii-2) versão instalada ≠ fixada (lockfile de outra versão, sha fora do ADR-192) ⇒ F-03 / H-07;
  - (ii-3) espião no argv do npm: scripts sempre suprimidos; um pacote de teste com script de ciclo de
    vida que gravaria um marcador ⇒ marcador ausente;
  - (ii-4) variável de opções do node com um `--require` de marcador no ambiente PAI ⇒ marcador ausente
    (ambiente do zero, F-09);
  - (ii-5) camada 2 (§19.2) contra o `sigstore` instalado do lockfile: S-02/S-10 verdes, S-03..S-09,
    S-11 (política), S-12, S-13, S-14 vermelhos;
  - (ii-6) só a linha do `package.json` muda no manifesto ADR-192 (lockfile, verificador e auxiliar
    iguais) ⇒ a linha existente do registro perde a confiança (H-07) — vermelho com o H-07 de 3 campos,
    verde com o de 4.

### Ramo (i)

- O módulo `sigstore` INTERNO do npm instalado (não é API pública; muda de lugar ou de versão num
  upgrade do npm), aceito só se a versão do npm, a versão do `sigstore` e o sha256 de CADA arquivo da
  árvore do módulo constarem de uma lista canônica (sob ADR-192); o auxiliar carrega o módulo por caminho
  absoluto só DEPOIS de o orquestrador conferir os shas.
- Fora da lista ⇒ recusa (F-03). É fail-closed: um upgrade do npm perde VIVACIDADE (adoção recusada até
  a cerimônia que atualiza a lista), não segurança.
- `signature_mode = sigstore-policy:i`; `sigstore_pkg_digest` = digest da lista de arquivos conferida.
- **Testes pré-registrados do ramo (i):**
  - (i-1) 1 arquivo do módulo com 1 byte alterado (cópia) ⇒ F-03 / íntegro ⇒ verde;
  - (i-2) versão do npm fora da lista ⇒ F-03;
  - (i-3) módulo movido (caminho ausente) ⇒ F-03;
  - (i-4) = (ii-4);
  - (i-5) camada 2 contra o módulo interno da versão permitida: mesmas células de (ii-5).

### «Confiança no registro» ⇒ ESCALATE (não é ramo deste texto)

Depois da W0.6, «confiança no registro via TLS + vínculo de digests» deixou de ser resíduo aceitável: há
mecanismo medido que a dispensa (S-02..S-12), e o comando do npm sozinho NÃO detecta a A-15 nem a A-14
(V-T2, V-P3, S-11). Se o Owner a escolher, o VETO de Segurança fica LEVANTADO e a W3 vai ao Owner por
múltipla escolha (ESCALATE-TO-OWNER), sem nova rodada, e o `design-coherent` da W3 deixa de valer.
Recusar a dependência de `node` devolve o plano B (re-pin manual pela cerimônia do ADR-182 §5).

## §8 O hook e o núcleo (MF-W3-1, MF-W3-2)

- `verify_codex_payload()` ganha a consulta ao registro, **desligada por padrão**. O hook a liga; a CLI
  só a liga com flag explícita (§11).
- Ordem dentro do núcleo (sem rede, sem execução): triple → manifesto (inalterado) → payload resolvido
  → sha256 → `== manifesto`? ⇒ `verified` (`pin_source = "manifest"`) → senão, se a consulta está
  ligada: registro carregado e validado (§10) → entrada confiável para (triple, sha) ⇒ `verified_auto`
  (`pin_source = "registry"`) → senão `mismatch` ⇒ BLOCK.
- **Revalidação a cada leitura (H-07).** O núcleo confere a evidência gravada contra as constantes ATUAIS
  (identidade da §6, carência, gramática, `signature_mode` do ramo escolhido, `path` igual ao da entrada
  do manifesto, triple do host, versão ≥ piso) e compara os shas que a linha DECLARA
  (`verifier_sha256`, `helper_sha256`, `sigstore_pkg_digest` e, no ramo (ii), `package_json_sha256`) com o
  manifesto ADR-192 da árvore.
  Entrada fora disso = sem confiança. O que a revalidação NÃO prova: quais bytes escreveram a linha
  (I8; resíduo R-5, teste H-14).
- **Bloqueio.** Sha desconhecido ⇒ `{decision: block}` com mensagem que nomeia o verificador e a
  reinstalação pela versão verificada. Nenhuma variável de ambiente relaxa a comparação; a costura de
  teste do registro segue o padrão das costuras do ADR-182 §2 (honrada só no modo de teste, inerte no
  caminho vivo, com controle negativo).
- **Custo.** O registro é pequeno (uma linha por versão adotada, ≤ 1/semana, com o manifesto de membros)
  e tem teto. O custo dominante segue sendo o hash do `bin/codex` (~240 MB), como hoje.

## §9 Matriz de recusa (MF-W3-1; QA r1 MF-11; QA r2 MF-10, MF-11)

Toda célula é pré-registrada; o builder codifica UMA ação esperada por célula e o teste-censo (§19.4)
liga cada id a ≥ 1 teste. O CEO pode ajustar valores, não remover células.

### 9.A Verificador (adoção) — efeito comum: **nada registrado**; o rail não muda; se o sha novo já estiver no global, o hook bloqueia (H-03)

| célula | condição | resultado | saída |
|---|---|---|---|
| A-01 | sem rede (DNS, conexão, tempo) em qualquer busca, inclusive TUF; com caches novos sempre recusa | recusa; **nunca INFRA** | 1 |
| A-02 | falha de TLS (cadeia de CA ausente, certificado inválido, nome) | recusa; a verificação de certificado nunca é desligada | 1 |
| A-03 | URL fora da lista FECHADA {registro, CDN do TUF}, ou redirect para fora dela | recusa | 1 |
| A-04 | registro efetivo do npm ≠ constante (configuração herdada) | recusa | 1 |
| A-05 | acima de qualquer teto da §4.4 | recusa + limpeza confinada | 1 |
| A-06 | piso de `df` não atendido | recusa ANTES de baixar | 1 |
| A-07 | versão fora da gramática estrita | não candidata | 1 se nenhuma restar |
| A-08 | idade < 48 h (o mais tardio das duas publicações), ou `Date` ausente/ilegível | não candidata / recusa | 1 se nenhuma restar |
| A-09 | candidata > `latest`, ou `latest` fora da gramática | não candidata / nenhuma | 1 |
| A-10 | `deprecated` no lançador ou na plataforma | não candidata | 1 se nenhuma restar |
| A-11 | abaixo do piso do manifesto | não candidata | 1 se nenhuma restar |
| A-12 | falta o bundle de procedência SLSA v1 do lançador OU da plataforma (exigido pelo VERIFICADOR; o npm não reprova, V-P3) | recusa | 1 |
| A-13 | bundle de OUTRO pacote ou versão (`subject.name` ≠ purl esperado) | recusa | 1 |
| A-14 | identidade divergente: SAN, emissor, id do repositório ou id do dono (S-03..S-05, S-12, S-13, S-14) | **recusa** (REJECTED pela política) | 1 |
| A-15 | assinatura DSSE, certificado ou entrada do Rekor inválidos ou ausentes (S-06..S-09) | **recusa** (REJECTED) | 1 |
| A-16 | sha512 do tarball baixado ≠ digest do `subject` do bundle VERIFICADO (lido dos mesmos bytes), ou `dist.integrity` ≠ esse valor (cruzamento) | recusa | 1 |
| A-17 | membro `bin/codex` ausente, duplicado, não regular, caminho ≠ exato, acima do teto; ou qualquer link, duplicata ou membro não regular no tarball | recusa | 1 |
| A-18 | staging: árvore materializada ≠ manifestos de membros; versão materializada ≠ exata; script de ciclo de vida não suprimido | recusa + relato de anomalia | 1 |
| A-19 | sonda reprovada (subcomando ou flag obrigatória ausente) — reencena o A7 | recusa | 1 |
| A-20 | canário reprovado, ou inconclusivo esgotada a política da §4.5 | recusa | 1 |
| A-21 | (versão, triple, sha) em quarentena | recusa permanente | 1 |
| A-22 | ação de aceitação ausente do registro de ações do `audit_emit`, ou evento não confirmado | recusa; a linha NÃO é gravada | 1 |
| A-23 | registro existente não confiável (§10), guarda do registro ausente (I8), ou falha de trava/escrita/`fsync` | recusa; nada gravado, nada promovido | 1 |
| A-24 | (triple, sha) já registrado e confiável | idempotente, nenhuma linha nova | 0 |
| A-25 | statement VERIFICADO com campo fora das constantes da §6 (`predicateType`, `buildType`, workflow, ref, construtor, mais de um `subject`) | recusa | 1 |
| A-26 | duas execuções CONCORRENTES do verificador sobre o mesmo registro | uma recusa (trava própria do registro); a cadeia `seq`/`prev_sha256` fica íntegra | 1 na recusada |

### 9.T Fronteiras de relógio — com relógio INJETADO, nunca tempo absoluto (condição 15 do consenso r3)

| célula | condição | resultado |
|---|---|---|
| T-01 | idade = 47:59:59 (o mais tardio das duas publicações, no relógio do registro) | não candidata (A-08) |
| T-02 | idade = 48:00:00 | candidata |
| T-03 | nova tentativa do canário «inconclusivo» antes de 10 min | recusa (A-20) |
| T-04 | 4.ª execução do verificador para a mesma versão na mesma semana | recusa (A-20) |

### 9.F Fronteira do verificador de assinatura — todas **recusa (1)**, nunca INFRA (QA r2 MF-11)

| célula | condição |
|---|---|
| F-01 | `node` ausente, não executável, caminho não absoluto ou não regular |
| F-02 | `node` abaixo da versão mínima |
| F-03 | sigstore ausente, movido ou com versão ≠ a fixada; (ii) lockfile ≠ linha ADR-192 ou `npm ci` falha; (i) versão do npm, do sigstore ou sha de arquivo fora da lista canônica |
| F-04 | saída do auxiliar não-JSON, ou JSON fora do esquema (veredito, política efetiva, digest do `subject`) |
| F-05 | código de saída do auxiliar ≠ 0 |
| F-06 | tempo excedido (processo do auxiliar morto). O timeout é CONSTANTE CANÔNICA com teste (nome proposto `AUTO_PIN_HELPER_TIMEOUT_S`); valor = 2× o maior tempo medido de `sigstore.verify` dos dois bundles com TUF novo [a medir no pacote 1a] |
| F-07 | chamada SEM a política exata: em produção, o orquestrador recusa resposta cuja política efetiva ≠ a pedida; em teste, o MUTANTE que tira a política faz S-11 virar VERIFIED e o teste fica VERMELHO |
| F-08 | cache do npm ou do TUF NÃO vazio no início (cache quente) |
| F-09 | auxiliar com sha ≠ linha ADR-192, ou ambiente do `node`/npm herdado (variáveis de opções, de caminho de módulos, `npm_config_*`) |

### 9.P Promoção (Fase 2)

| célula | condição | resultado |
|---|---|---|
| P-01 | árvore global (lançador + plataforma) ≠ manifestos de membros verificados (caminho, tamanho, sha256, tipo), executável/arquivo extra fora da lista fechada, link de `bin` errado, ou o núcleo não dá `verified_auto`/`verified` | recusa + relato «promoção divergente»; o hook já bloqueia se o `bin/codex` divergir; rollback §15 |
| P-02 | promoção sem Fase 1 verde NESTA execução | recusa |
| P-03 | quiesce: processo executando o payload ou um irmão do prefixo global (`lsof`/`ps` sobre o caminho) | recusa, nada instalado |
| P-04 | qualquer busca no registro durante a Fase 2 — modo offline + opções EXPLÍCITAS de proxy morto (o `env -i` remove as variáveis); controle positivo: cache do staging ESVAZIADO ⇒ a Fase 2 FALHA | recusa |
| P-05 | prefixo global efetivo ≠ prefixo do lançador do PATH | recusa |

### 9.H Hook (cada invocação L3+; sem rede, sem download, sem execução antes do hash)

| célula | condição | status | efeito |
|---|---|---|---|
| H-01 | sha == entrada do manifesto | `verified`, `pin_source="manifest"` | executa o caminho verificado |
| H-02 | sha ∉ manifesto; ∈ registro confiável; entrada revalidada; fora de quarentena | `verified_auto`, `pin_source="registry"` | executa o caminho verificado |
| H-03 | sha ∉ manifesto ∪ registro | `mismatch` | **BLOCK**, nomeia o verificador |
| H-04 | sha registrado, em quarentena | `mismatch` | **BLOCK** |
| H-05 | registro AUSENTE | zero confiança extra (não INFRA) | H-01 ou H-03 |
| H-06 | registro presente e não confiável (ilegível, malformado, cadeia local quebrada, modo/dono/tipo errados, link, acima do teto) | zero confiança extra; `registry_untrusted` | H-01 com aviso, ou H-03 (**BLOCK**) |
| H-07 | entrada com evidência fora das constantes atuais, ou `verifier_sha256`/`helper_sha256`/`sigstore_pkg_digest`/`package_json_sha256` (este só no ramo (ii)) DECLARADOS ≠ manifesto ADR-192, ou `signature_mode` fora do ramo escolhido, ou manifesto ADR-192 ausente/malformado | aquela entrada sem confiança | H-03 (**BLOCK**) se nada mais casar |
| H-08 | triple não derivável ou ausente do manifesto | `triple_missing` | **BLOCK** (inalterado) |
| H-09 | manifesto presente e malformado | `mismatch` | **BLOCK** (inalterado) |
| H-10 | manifesto ausente/ilegível; lançador ausente; payload não resolvido/ilegível | `infra` | inalterado (ADR-182 §2): o rail some com aviso — §21 R-8 |
| H-11 | costura de override do binário posta | mesmo caminho: hash + (manifesto ∪ registro); ausente ⇒ `mismatch` | inalterado |
| H-12 | qualquer rede, download ou execução no caminho do hook | proibido por construção | provado por teste (guarda de socket + espião) |
| H-13 | irmão do pacote alterado DEPOIS da promoção | segue `verified_auto` | **resíduo documentado por teste** (§2, R-6), não recusa |
| H-14 | verificador SINTÉTICO editado grava linha coerente com `verifier_sha256` FORJADO igual ao do manifesto ADR-192 | o núcleo CONCEDE `verified_auto` | **resíduo documentado por teste** (I8, §21 R-5), não recusa — prova que o H-07 compara shas DECLARADOS |

### 9.W Guarda do registro contra escrita do PRÓPRIO agente (MF-R2-W3-5; §10.4)

| célula | condição | resultado |
|---|---|---|
| W-01 | Edit/Write/MultiEdit/NotebookEdit com destino (resolvido, links seguidos) dentro do diretório do registro | **BLOCK** |
| W-02 | Bash com redirecionamento (inclusive acréscimo) para caminho que nomeia o diretório do registro | **BLOCK** |
| W-03 | Bash com comando de escrita, cópia, movimento, link, truncamento, edição no lugar ou interpretador cujo texto nomeia o diretório do registro | **BLOCK** |
| W-04 | Bash que nomeia o diretório do registro e não se deixa analisar | **BLOCK** (fail-closed na entrada) |
| W-05 | invocação do verificador (o texto não nomeia o registro; o verificador resolve o caminho sozinho) | permitido (controle negativo) |
| W-06 | escrita do PRÓPRIO verificador (processo, não ferramenta do agente) | permitida; fora do alcance da guarda por construção |
| W-07 | Edit/Write/MultiEdit/NotebookEdit numa FONTE do verificador (o `.py`, o auxiliar `.js`, o `package.json`, o `package-lock.json`; no ramo (i), a lista canônica) | **BLOCK** (salvo sentinela de cerimônia, se o mecanismo for `_CANONICAL_GUARDS`) |
| W-08 | Bash com redirecionamento ou comando de escrita direta que nomeia uma FONTE do verificador | **BLOCK** |
| W-09 | Bash que nomeia uma FONTE do verificador e não se deixa analisar | **BLOCK** (fail-closed na entrada) |

Controle positivo de W-01..W-04 e W-07..W-09: a entrada de ferramenta no formato EXATO do agente ⇒
BLOCK; W-05 ⇒ permitido. A guarda das FONTES (W-07..W-09) landa no pacote **1c**, PRIMEIRO da fila, ou no
1b se couber, e sempre **ANTES do 1.º LAND do 1a** (condição 6 do consenso r3).

### 9.K Rota 2 invertida no kit de corte (MF-R2-W3-6; §17)

| célula | condição | resultado |
|---|---|---|
| K-01 | qualquer execução (inclusive `--version`) antes do oráculo | proibida; espião prova zero |
| K-02 | lançador plantado diferente, servido por registro redirecionado pela configuração do usuário | NUNCA executa (ambiente do npm do zero ignora a configuração; o oráculo reprova) |
| K-03 | versão materializada ≠ a do manifesto | o kit morre antes de executar |
| K-04 | oráculo SEM flag ≠ 0 | o kit morre antes de executar |
| K-05 | shim | faz `exec` do `path` VERIFICADO que o oráculo devolve, nunca do lançador |
| K-06 | cache não novo, scripts não suprimidos ou registro ≠ constante. A materialização do kit é ONLINE (aquisição inicial, com cache NOVO, do registro fixo — §17 passo 1); ela NÃO é feita offline. **Controle de falha (condição 12, o mesmo do P-04):** a MESMA invocação do npm do kit, rodada como controle com o cache ESVAZIADO, em modo offline e com o proxy morto passado como opção EXPLÍCITA, tem de FALHAR — prova que o npm do kit obedece às opções explícitas, e não ao ambiente; se passar, o kit não landa | o kit morre |

### 9.B Cruzamento do boot e conferência da árvore instalada (§15; condição 15 do consenso r3)

| célula | condição | resultado |
|---|---|---|
| B-01 | linha de aceitação SEM evento `codex_auto_pin_accepted` correspondente na cadeia | **ALARME** no `/ceo-boot` |
| B-02 | evento de quarentena SEM linha `kind=quarantine` correspondente (quarentena removida) | **ALARME** no `/ceo-boot` |
| B-03 | evento de aceitação SEM linha (órfão: o evento sai antes da linha, I6) | informativo, sem alarme |
| B-04 | `--check-installed` com um membro instalado alterado (caminho, tamanho ou sha256 ≠ manifesto de membros da linha) | divergência RELATADA, com o membro |

### 9.C/R CLI e trilha de release

| célula | consumidor | condição | resultado |
|---|---|---|---|
| C-01 | `--verify-codex-pin` SEM flag | qualquer | só-manifesto; o registro NÃO é aberto; saídas 0/1/3 do ADR-182; JSON + `pin_source`; sha só-registrado ⇒ `mismatch`/1 |
| C-02 | `--verify-codex-pin --allow-auto-pin` | qualquer | mesmo resultado do hook; `verified_auto`/0 com `pin_source == "registry"` |
| R-01 | validador do passo 15 | veredito com sha só auto-pinado | `VERDICT_INVALID` (saída 3) — inalterado; célula (d) dos controles |
| R-02 | `gen-envelope-ga.py` | sha/versão ≠ manifesto | recusa — inalterado |
| R-03 | runner do re-pass / kit | global auto-pinado (≠ manifesto) | rota 2 INVERTIDA (§17); a PROVENANCE registra a versão do manifesto e a rota |
| R-04 | Gate 4 do `pair-rail-gate.sh --phase 6` | global auto-pinado | **falha por desenho**, com mensagem que nomeia a rota 2 e nota de operador (§11) |

## §10 O registro (MF-W3-5; MF-R2-W3-5)

### 10.1 Onde

`<runtime_state_dir>/codex-pin-registry/`, resolvido por `_lib/runtime_paths.py` (`runtime_state_dir()`,
`:139-161` **[disco]**; ADR-001, nunca slug derivado à mão). FORA de `state/` (`<audit_dir>/state/`,
`spool_writer.py:265` **[disco]**), portanto fora do GC da W2 e da W2.6 (por caminho e por nome: nenhum
padrão de PID). FORA da árvore git. Em SUBDIRETÓRIO e com extensão que não é `.jsonl` (a varredura de
limpeza do CC já apagou `*.jsonl` de topo em `~/.claude/projects/`, S357). O nome do diretório é
distinto do nome do verificador, para a guarda casar sem ambiguidade (W-05).

### 10.2 Forma e esquema

- Diretório 0700, arquivo 0600, dono == euid, arquivo regular, aberto sem seguir link; teto de tamanho.
  Violação ⇒ não confiável (H-06).
- **Só-acréscimo.** O verificador nunca reescreve, trunca ou apaga. Quarentena é linha nova. Cada linha
  leva `seq` monotônico e `prev_sha256` (detecta edição ou truncamento no meio; não no fim, nem contra o
  mesmo UID — §21 R-5).
- **Linha de aceitação (v1):** `schema`, `kind=accept`, `seq`, `prev_sha256`, `package`, `version`,
  `platform_version`, `target_triple`, `payload_path`, `payload_sha256`; por pacote (lançador e
  plataforma): `tarball_sha512` (= digest do `subject` verificado), `npm_integrity` (cruzamento),
  `attestation_sha256`, `members` (caminho, tamanho, sha256, tipo, modo); `identity` (SAN, emissor, ids
  imutáveis, campos do statement da §6, `rekor_log_index`); `published_at` (as duas), `registry_date`,
  `grace_hours`, `latest_at_check`; `probe`, `canary` (resultado, sha do argv, tentativas);
  **instrumento:** `signature_mode`, `node_path`, `node_version`, `node_sha256`, `npm_version`,
  `sigstore_version`, `sigstore_pkg_digest`, `package_json_sha256` (ramo (ii)), `tuf_root_digest`,
  `verifier_sha256`, `helper_sha256`,
  `kernel_sha256`; referência do evento HMAC; `recorded_at` (UTC).
- **Linha de quarentena:** `schema`, `kind=quarantine`, `seq`, `prev_sha256`, `target_triple`,
  `payload_sha256`, `version`, `reason`, `recorded_at`. `kind` desconhecido ⇒ não confiável.

### 10.3 Leitores e escritor

Leem: o núcleo (no hook e na CLI com flag) e, pela CLI com flag, o detector de deriva e o cruzamento do
boot (§15). **Nunca** o passo 15, o `gen-envelope-ga.py`, o kit nem o runner do re-pass (I7). Escreve:
só o verificador. Perda do registro = direção segura (as versões só-registradas bloqueiam até nova Fase
1). Não é o cache do ADR-182 §Consequences: o hook segue hasheando a cada invocação.

### 10.4 Guarda contra escrita do PRÓPRIO agente — registro E fontes do verificador (MF-R2-W3-5; consenso r3, condições 4 e 6)

- **Por quê.** O resíduo de mesmo UID cobre um processo ALHEIO (fora do modelo). O agente governado sob
  injeção está DENTRO do modelo: é para ele que existem os guardas de Edit/Write/Bash. Um agente que
  acrescentasse uma linha coerente e instalasse um binário concederia confiança a ele. E o ESCRITOR do
  registro é um script cujas fontes têm oráculo 0 (§4.1): um agente que edite o verificador, o execute
  (W-05) e o restaure grava uma linha que DECLARA os shas legítimos (I8, H-14). Por isso a guarda cobre
  as duas superfícies.
- **Superfície 1 — o registro:** células W-01..W-06 (§9.W). Destino resolvido (links seguidos) para
  Edit/Write; para Bash, casamento por componente de caminho e pelo nome do diretório do registro,
  herdando o portão de análise do comando inteiro do hospedeiro escolhido (entrada não analisável que
  nomeia o registro ⇒ BLOCK). Defesa em profundidade: entrada de negação em `permissions.deny` do
  `.claude/settings.json` para as ferramentas de edição, com a linha de base do
  `check_harness_config.py`.
- **Superfície 2 — as FONTES do verificador** (o `.py`, o auxiliar `.js`, o `package.json`, o
  `package-lock.json`; no ramo (i), a lista canônica): células W-07..W-09. Mecanismo, um dos dois:
  (a) `_CANONICAL_GUARDS` do `check_canonical_edit.py` (`:115` **[disco]**; arquivo de KERNEL,
  `check_arbitration_kernel.py:88` **[disco]**) — as fontes passam a oráculo 1 e a edição pede sentinela
  de cerimônia; cerimônia de kernel, custo marginal sobre o 1b/1c; ou (b) as células W-01..W-04
  estendidas a esses caminhos no mesmo hospedeiro da superfície 1. A escolha é do builder com o oráculo
  na abertura; o controle positivo é o mesmo nos dois.
- **Hospedeiros e colisões (condição 4).** Candidatos medidos nesta revisão: `.claude/hooks/check_bash_safety.py`
  [oráculo 1], `.claude/settings.json` [oráculo 1], `.claude/hooks/check_harness_config.py` [oráculo 1],
  `.claude/hooks/check_canonical_edit.py` [oráculo 1, kernel]. Regras de série, a escrever no mapa de
  colisões do plano antes do 1b/1c: `permissions.deny` do `settings.json` em série W6 → W5c → W3 (1c) /
  W3 do PLAN-195; `check_bash_safety.py` em série com as partes A e B do PLAN-195, re-derivado sobre
  elas — e, se a guarda de Bash precisar dele, a W3.6 entra no caminho crítico do PLAN-195; **preferência:
  outro hospedeiro enquanto a parte B do PLAN-195 estiver em voo**; `check_canonical_edit.py` só se o
  mecanismo (a) for o escolhido. O teste da guarda (nome proposto
  `.claude/hooks/tests/test_codex_pin_registry_guard.py`, [oráculo 0]) cobre W-01..W-09.
- **Controle positivo:** cada célula W-01..W-04 e W-07..W-09 com a entrada de ferramenta no formato
  EXATO do agente ⇒ BLOCK; W-05 ⇒ permitido.
- **Ordem (I8; condição 6).** A guarda do REGISTRO landa no 1b ou antes dele; a guarda das FONTES landa
  ANTES do 1.º LAND do 1a. Se o 1b passar de 8 paths, as duas saem como pacote **1c, PRIMEIRO da fila**.
  O núcleo só passa a consultar o registro no mesmo LAND em que a guarda do registro existe.
- **A família do log de auditoria (condição 5).** A busca do sintetizador da r2 não achou guarda
  dedicada à família do log (log, chave, sal e sidecars) [consenso r2 §0, inconclusivo]. Isso é do
  domínio do VETO (ADR-052) e ganha item com DONO e posição no PLANO antes do SIGN do 1b, com a pergunta
  respondida no disco (existe guarda? com que controle?) — ajuste 11 do consenso r3, aplicado pelo CEO.
  Não bloqueia a W3; bloqueia ficar sem dono. Este texto o referencia; o item vive no plano.
- **Limite honesto:** guarda por texto de comando não detém código arbitrário que calcula o caminho sem
  nomeá-lo; essa classe é comum a todos os guardas de Bash. Defesas que restam: H-07 (linha que declara
  verificador fora do ADR-192 não vale), evento HMAC antes da linha, cruzamento do boot e a evidência em
  repouso das fontes (§4.1; §21 R-5).

## §11 Contrato de cada consumidor (MF-W3-5; R-DO3; QA r2 MF-14)

| consumidor | lê o registro? | aceita `verified_auto`? | contrato |
|---|---|---|---|
| hook `check_pair_rail.py` (PreToolUse, L3+) | sim | sim | §8, §9.H |
| CLI `--verify-codex-pin` sem flag | **não** | não | só-manifesto, saída do ADR-182 + `pin_source`; padrão de todo chamador existente |
| CLI `--verify-codex-pin <caminho do lançador> --allow-auto-pin` | sim | sim | o Check de sucesso da W3 e o da W3.6 usam esta forma e afirmam, no código de saída, **`status == "verified_auto"` E `pin_source == "registry"`** para versão FORA do manifesto. A flag vem DEPOIS do caminho, porque `_verify_pin_cli` toma `argv[0]` como lançador (`check_pair_rail.py:2513` **[disco]**); um teste no 1b (`test_check_pair_rail_auto_pin.py`, [oráculo 0]) fixa essa forma (§19.5) |
| Check da W3.1 | não | não | sem flag; escopo escrito «até o LAND da W3» (0.156.1, só-manifesto) |
| Gate 4 do `pair-rail-gate.sh` (fase 6, `:208` **[disco]**) | não (chamada sem flag) | não | pré-voo da trilha de release («antes da tag»); com global auto-pinado reprova POR DESENHO, e a mensagem nomeia a rota 2 com nota de operador: a saúde diária é a CLI com a flag; o vermelho esperado não é incidente (R-04) |
| `run-ga-repass.sh` / kit da 1.4.3 | não | não | rota 1 só se o global É a versão do manifesto e verifica sem flag; senão rota 2 INVERTIDA (§17) |
| validador do passo 15 | **nunca** | não | inalterado; manifesto da árvore tagueada |
| `gen-envelope-ga.py` / kit | **nunca** | não | inalterados |
| verificador (§4) | escreve e lê | — | único escritor |

**Literal único:** os valores de `pin_source` são `"manifest"` e `"registry"`, e os de `status` para as
duas fontes são `"verified"` e `"verified_auto"`, os do código. Plano (inclusive os resumos da W3.4),
Checks e testes usam esses literais (condição 16 do consenso r3).

## §12 Evento de aceitação na cadeia HMAC (MF-W3-6; consenso r1 §2(e))

- **Por quê.** A aceitação automática SUBSTITUI a assinatura GPG do Owner. Ação fora de
  `_KNOWN_ACTIONS` vira breadcrumb (`audit_emit.py:5260-5262` **[disco]**). O precedente do
  ADR-055-AMEND-3 (breadcrumb para não tocar o kernel) não se aplica: ali não se substituía assinatura.
- **Pacote de kernel de registro de ações** (`_lib/audit_emit.py`: `_KNOWN_ACTIONS`, ramo de `_scrub_`
  dedicado e deny-by-default, SPEC do audit-log e contagens, como os precedentes):
  - `codex_auto_pin_accepted` (nome proposto) — versão, versão de plataforma, triple, sha256 do
    payload, `tarball_sha512` dos dois pacotes, `attestation_sha256`, identidade (SAN, emissor, ids
    imutáveis, `rekor_log_index`), digest do manifesto de membros e TODA a identidade do instrumento
    (§10.2: `signature_mode`, versões de `node`/npm/sigstore, `sigstore_pkg_digest`,
    `package_json_sha256` no ramo (ii), `tuf_root_digest`,
    `verifier_sha256`, `helper_sha256`), resultado da sonda e do canário;
  - `codex_auto_pin_quarantined` (nome proposto) — triple, sha, versão, motivo;
  - **promoção** de `pair_rail_codex_pin_mismatch`, hoje só breadcrumb (`check_pair_rail.py:1201-1204`
    **[disco]**).
- **`_emit_audit()` ligado ao `emit_generic` no pacote 1b.** Hoje ele escreve só no sumidouro de teste e
  no stderr (`check_pair_rail.py:1212-1236` **[disco]**), sem chamar o `emit_generic` nem para ações já
  registradas (`pair_rail_codex_unavailable`), apesar do comentário de `:1185-1194` [confirmado pelo
  portador do VETO na r2]. O pacote 1b liga ao `emit_generic`, com taxa limitada, as ações que esta
  emenda usa como instrumento (`pair_rail_codex_pin_mismatch` depois do registro no kernel,
  `pair_rail_codex_unavailable`); as demais ficam como estão, declarado. **O sumidouro de teste passa a
  ser honrado SÓ no modo de teste**, como as outras costuras do ADR-182 §2.
- **Ordem e vaga.** O pacote de kernel vai em SÉRIE com a W1a do PLAN-195 (colisão em `audit_emit.py`) e
  landa ANTES da W3.6. Enquanto ele não landar, o verificador recusa gravar (A-22).
- **Ordem no verificador.** Evento primeiro (confirmado), linha depois. Evento sem linha = órfão
  inofensivo. Linha sem evento = ALARME (§15).
- **Alternativa** (evidência só no registro): só por decisão ESCRITA do Owner (decisão 6, §22).

## §13 Os dois eixos do argv (MF-W3-8; consenso r1 C6)

- **Eixo 1 — binário:** automático, por esta emenda.
- **Eixo 2 — modelo e esforço:** constantes canônicas usadas pelo argv do rail; mudar de modelo é
  cerimônia por GERAÇÃO. Hoje o argv OMITE `--model` (`codex_cli_shape.py:110` `DEFAULT_MODEL = None`;
  `--model` só com valor explícito, `:351`; `_VALID_MODELS` sem nenhum `gpt-6*`, `:97-105` **[disco]**). O
  id fixado entra em `_VALID_MODELS` (depois da W3b) e no `model-deprecations.json`. O valor do par é a
  decisão 5 **[Owner]**.
- **`--ignore-user-config`** entra SE a sonda (V-9) confirmar a flag na versão E uma medição provar que
  `memories` não carrega com ela.
- **Também na 0.156.1.** O argv fixo (modelo, esforço e `--ignore-user-config`) é sondado UMA vez na
  versão do MANIFESTO, que o corte usa pela rota 2; se faltar flag nela, o corte declara a divergência
  (pré-condição da W3.6, §18).
- **Registro por rodada:** versão, sha do payload, `pin_source`, modelo pedido, modelo servido (se o
  `session_meta` o expuser), esforço, sha do config (pré-voo Q11). Id indisponível ⇒ contagem diária no
  boot, nunca silêncio.
- **Mesmo argv nas duas trilhas:** os derivadores do kit da 1.4.3 herdam o eixo 2, ou declaram a
  divergência.

## §14 Chamadores fora do hook (MF-W3-10; consenso r1 C8)

| chamador | classe do path | executa sozinho? | tratamento |
|---|---|---|---|
| `.claude/scripts/codex_invoke.py:193` (`["codex"] + argv`, PATH) | livre | não | passa pelo núcleo (com a flag) e executa o caminho verificado — pacote 2 |
| `.claude/scripts/run-promotion-gate.py:196-212` (`codex --version`) | livre | não | idem — pacote 2 |
| `.claude/hooks/codex_review_user_code.py:120-131` (hook `Stop`, `codex exec` do PATH) | canônico | **sim, no opt-in** (padrão detect-only, `settings.json:636-645` **[disco]**) | declarado no material assinado com o estado do opt-in; backlog |
| `.claude/workflows/council-audit.js:325` | canônico | não | declarado; backlog |
| daemon `app-server` (atualiza-se fora do pin, lane `CX-06`) | externo | sim | declarado |
| `codex exec review` manual | externo | não | declarado |

Depois da promoção (§4.3), o binário do PATH é um verificado; o buraco das rodadas manuais é a janela
entre um `npm i -g` cru e o próximo uso do hook, que o bloqueia (§21 R-9, R-19).

## §15 Quarentena, rollback e visibilidade

- **Quarentena.** Comando do verificador: linha `kind=quarantine` (sempre gravada, mesmo se o evento
  falhar — é redução de confiança) + `codex_auto_pin_quarantined`. Efeito: H-04 e A-21. TERMINAL para
  (versão, triple, sha). Desconfiar da versão do MANIFESTO continua sendo a cerimônia do ADR-182 (ou o
  kill-switch global auditado, inalterado).
- **Rollback sem depender de cota (condição 18 do consenso r3).** Rollback para um sha JÁ registrado (e
  fora de quarentena) ou para a versão do manifesto, pelo verificador com `--promote`: re-verifica os
  bytes (V-0..V-9, sonda LOCAL incluída, e V-11) e **PULA o canário (V-10)**, que já passou para aquele
  sha (registrado na linha); não grava linha nova (A-24; na versão do manifesto, nenhuma linha) e promove
  pelos bytes verificados. O canário é vivacidade, não segurança. **R-16: o rollback exige rede** (caches
  novos a cada execução), mas **não exige cota**. Reter o cache verificado das 2 últimas versões é
  follow-up nomeado.
- **Rota de EMERGÊNCIA (runbook).** Instalar a versão do MANIFESTO: o hook a aceita por H-01, sem canário
  nem cota. Pelo verificador (Fase 1 sem linha + Fase 2), os irmãos ficam conferidos; por instalação
  CRUA, os irmãos ficam sem conferência (R-19) até a re-promoção ou um `--check-installed`.
- **Modo de execução do verificador (runbook; condição 20 do consenso r3).** Terminal do Owner em
  primeiro plano, ou segundo plano com timeout EXPLÍCITO ≥ o pior caso pré-registrado (downloads +
  `npm ci` + canário + 1 nova tentativa de ≥ 10 min; valor a medir no ensaio da condição 21, §18) —
  **nunca** o padrão de 30 min do CC para Bash em segundo plano.
- **Morte no meio da Fase 2.** O global fica num estado que o P-01 não conferiu. O que o hook faz depende
  do `bin/codex` que sobrou, e há TRÊS desfechos, não um:
  - `bin/codex` presente com sha fora do manifesto ∪ registro ⇒ `mismatch` ⇒ **BLOCK** (H-03);
  - `bin/codex` presente e igual ao registrado (ou ao do manifesto) ⇒ `verified_auto` (ou `verified`) ⇒
    o hook **ACEITA**, e os irmãos podem estar incompletos ou ser de outra versão (R-19), porque o hook
    confere só o `bin/codex` (§2);
  - lançador ausente, ou `bin/codex` não resolvido ou ilegível ⇒ `infra` (`check_pair_rail.py:654`,
    `:725`, `:731` **[disco]**; braço preservado pelo H-10) ⇒ o rail SOME com aviso (allow,
    `:784-786` **[disco]**; §21 R-8) — não é BLOCK.
  Saída nos três: a rota de emergência acima, ou nova execução com `--promote`; até lá, o
  `--check-installed` (B-04) mostra a árvore incompleta. A recusa do quiesce (P-03) nomeia PID e caminho do executável de cada processo, e o
  procedimento lista o que parar (o daemon `app-server` e o app do Codex são os candidatos).
- **Visibilidade (advisory, antes da W3.6):**
  - detector de deriva (`check-substrate-drift.py`, [oráculo 0]) pela CLI com flag: instalado ∈ registro
    = sem deriva; instalado ≠ manifesto = informação para o próximo corte, nunca recomendação de re-pin;
  - cruzamento no `/ceo-boot` (`ceo-boot.py`, [oráculo 0]): B-01 linha de aceitação SEM evento =
    ALARME; B-02 evento de quarentena SEM linha = ALARME; B-03 evento de aceitação sem linha = órfão,
    informativo;
  - evidência em repouso das FONTES do verificador: sha em disco × manifesto ADR-192 (§4.1);
  - `--check-installed` do verificador (fora de hook, sob demanda): re-hash da árvore instalada contra os
    manifestos de membros da linha (~333 MB), B-04 com membro alterado ⇒ divergência relatada; o
    `/ceo-boot` só o RECOMENDA quando o diretório instalado mudar desde a última conferência (custo de
    `stat`);
  - contagem diária, por versão, de falhas do rail a partir de eventos DURÁVEIS
    (`codex_invoke_dispatched` com `exit_code`, `check_pair_rail.py:1052-1054` **[disco]**;
    `pair_rail_case`; `pair_rail_codex_unavailable` depois de ligado). A emissão tem taxa limitada
    (`audit_emit.py:12390` **[disco]**): contagem aproximada, declarado.

## §16 Cortes de release, faixa e T-8 (MF-W3-11, parte mantida; consenso r1 §2(c))

- A faixa do `codex-cli-pin.txt` (`>=0.128.0,<0.157.0`) fica **intocada** na W3. O corte da 1.4.3
  declara o 0.156.1.
- O passo 15 segue exigindo `codex_payload_sha256` == manifesto da árvore tagueada. Versão só
  auto-pinada ⇒ `VERDICT_INVALID` (R-01).
- **Limite declarado do validador:** `parse_semver` casa por PREFIXO (`validate-pair-rail-verdict.py:355-359`
  [consenso]); quem garante «só estável» é o sha do manifesto.
- **T-8 no MESMO pacote 1b** (`docs/CROSS-LLM-THREAT-MODEL.md:328` em diante **[disco]**): o item 1 passa a
  dizer que o hook confia em «manifesto assinado (Owner) ∪ registro local de pin automático
  (verificador sob ADR-192 + `sigstore.verify` com política de identidade + vínculo de bytes + carência +
  sonda/canário + evento HMAC), protegido contra escrita do agente»; o item 5 diz que a cerimônia é a via
  do MANIFESTO e da trilha de release, e que o gatilho do ADR-111 §2 está preservado e NÃO AVALIÁVEL; o
  resíduo ganha os executáveis irmãos, R-5, R-14 e R-16.

## §17 Rota 2 INVERTIDA no kit da 1.4.3 (MF-R2-W3-6) — pré-condição da W3.6

**Fato [disco, consenso r2 §0]:** o runner atual executa `npx -y "$CODEX_PKG" --version` ANTES do oráculo
(`PLAN-193/repass-ga/run-ga-repass.sh:266` contra `:282-286`; `PLAN-192/.../run-ga-repass.sh:203` contra
`:219-223`), herda o `~/.npmrc` e as `npm_config_*`, roda sem suprimir scripts, e o shim faz `exec` do
LANÇADOR, não do `path` verificado. Com a W3.6 antes do corte, a rota 2 vira o caminho PADRÃO de todo
corte, na sessão em que o GPG do Owner está desbloqueado. Declarar não basta: **inverter**.

Os derivadores do kit da 1.4.3 (clones de `PLAN-193/derive-kit-142.py` e `derive-ga-kit-142.py`
**[disco]**) trocam o `npx -y … --version` por:

1. **materializar sem executar:** instalação no prefixo do OUT (`--prefix`), scripts suprimidos, ambiente
   do npm montado do zero (§4.4), registro fixo, cache NOVO, versão EXATA do manifesto;
2. **oráculo SEM flag** sobre o lançador materializado (caminho determinístico; some a busca com `find`);
3. **shim com `exec` do `path` VERIFICADO** que o oráculo devolve (o artefato hasheado é o que roda,
   ADR-182 §2);
4. **só então** qualquer execução, inclusive `--version`.

**Controle:** lançador plantado diferente num registro redirecionado pela configuração NUNCA executa
(K-02), e um espião prova zero execução antes do oráculo (K-01). As células K-01..K-06 entram no
teste-censo. **O R-12 da r2 sai dos resíduos.** Resíduo que fica: os irmãos da versão do manifesto não
são conferidos na rota 2 (o manifesto pina só o `bin/codex`) — §21 R-17.

## §18 W3.6 — atualizar o Codex logo depois do LAND (consenso r1 §2(c); r2 §2(k))

**Pré-condições (todas; onde indicado, a decisão escrita do Owner substitui):**

1. Decisão 3 ESCRITA (ramo (ii) ou (i)) **[Owner]** — sem ela nenhum pacote da W3 começa; os testes do
   ramo escolhido verdes, inclusive a camada 2 em MODO OBRIGATÓRIO (§19.2).
2. LAND dos pacotes 1c (se existir), 1b, 1a e 2 (§24), com a guarda do REGISTRO landada no 1b ou antes e
   a guarda das FONTES do verificador landada antes do 1.º LAND do 1a (§10.4; condição 6).
3. S-13/S-14 medidos na camada 2 e no LEDGER (pré-condição do SIGN do 1a, §6; condição 10) e o controle
   positivo VERMELHO da guarda de rede do `node` filho medido e no LEDGER (§19.3; condição 11).
4. Pacote de kernel do evento (§12) landado — ou a decisão 6 escrita **[Owner]**.
5. Detector de deriva, cruzamento do boot (B-01..B-03) e evidência em repouso das fontes (§4.1, §15)
   landados.
6. **Rota 2 INVERTIDA nos dois derivadores do kit** (§17), com o controle K-01/K-02 e o controle positivo
   do K-06.
7. Argv fixo sondado na 0.156.1 (§13).
8. Runbook do verificador com o modo de execução e o timeout explícito, a rota de EMERGÊNCIA e o
   procedimento do quiesce (§15; condições 18 e 20).
9. **Ensaio em modo SÓ-VERIFICAÇÃO contra a 0.156.1 do manifesto, antes do 1.º `--promote` real**
   (condição 21): a Fase 1 inteira numa versão cujo sha já conhecemos (`0196e89f…`, L-P1 da W0.6), SEM
   gravar linha e SEM Fase 2; o canário obedece ao freio Q2 ou é pulado nesse modo. Resultado no LEDGER,
   com substrato; a `node` v26.3.0 da W0.6 vai ao LEDGER como linha de base da constante de versão mínima
   (§4.1). O ensaio também mede o tempo do pior caso que fixa o timeout explícito do runbook (§15).
10. Pré-voo do corte declara a rede, os ~331 MB, o piso de `df` e a limpeza confinada; argv do runner
    alinhado ao eixo 2 (ou divergência declarada); pré-voo Q11 no re-pass da rc e do GA.

**Ordem com o corte W7 (condição 22).**

- O **1b (pacote de ADR) landa ANTES de começar a derivação do kit da W7**, porque nenhum pacote de ADR
  fica em voo durante o kit; senão a W3.6 escorrega para depois do GA.
- A **inversão da rota 2 pode landar como a PRIMEIRA peça da W7.1** (derivadores com oráculo 0, com os
  controles K-01 e K-02), para a W3.6 não esperar o kit inteiro.

**Passos:** verificador com `--promote` sobre a candidata ELEGÍVEL do dia (nunca a `latest` crua), na
janela de manutenção (quiesce, rodadas paradas), no modo de execução do runbook → 1.ª rodada real: CLI com
`<caminho> --allow-auto-pin` dá `status == "verified_auto"`/0 com `pin_source == "registry"`; evento na
cadeia; `session_meta` com a versão, o originador `codex_exec` e 0 sessões «guardian» (lanes `CX-06`,
`CX-12`); registro por rodada do eixo 2. Depois disso, a W5.1 usa a versão global auto-pinada como
`codex_cli` do refresh.

**Regra operacional (W3.1):** até o LAND da W3, Codex no 0.156.1, sem `npm update -g`. Depois, só pelo
verificador.

## §19 Controles e testes (QA r1 MF-9..13; QA r2 MF-11..15)

Em árvore descartável quando escrevem; nenhuma asserção de tempo absoluto.

### 19.1 Camada 1 — FIAÇÃO fail-closed (CI, Python)

- Stub do subprocesso do auxiliar e do npm: REJECTED, crash, código ≠ 0, timeout, lixo, JSON fora do
  esquema, política efetiva ≠ pedida ⇒ recusa (F-01..F-09).
- Células de FORMA com fixtures sintéticas (tarball e bundle de KB gerados no tmp): A-05, A-16, A-17. As
  células A-14 e A-15 NÃO se provam com fixture sintética (um atestado sintético não carrega assinatura
  válida): ficam na camada 2.
- Guarda de socket do Python no módulo inteiro, com controle POSITIVO de que dispara; H-12 (zero rede e
  zero execução no caminho do hook); espião de zero execução de payload não verificado (sonda e canário
  só depois de V-8).
- O `npm i -g` modelado sobrescrevendo o payload no MESMO caminho (L-9) ⇒ o hook BLOQUEIA.

### 19.2 Camada 2 — criptografia REAL, offline

- **Fixtures como INSTRUMENTO (condição 17).** Os bundles REAIS de procedência da 0.156.1 e da 0.160.0
  (lançador e plataforma; ~15 KB cada, [W0.6 §5]) e uma raiz de confiança TUF FIXADA, num único arquivo
  (nome proposto `.claude/scripts/tests/fixtures/codex_auto_pin_sigstore_fixtures.json`, [oráculo 0]).
  Cada entrada traz, AO LADO dos bytes, o sha256 dos bytes, a data de captura (UTC) e a origem; o bloco
  de metadados fica DENTRO do mesmo arquivo para não somar um path ao 1a. Um teste recomputa cada sha e
  FALHA com fixture trocada ou editada.
- Mutantes: S-03..S-09, S-11 (sem política ⇒ VERIFIED ⇒ o mutante F-07 deixa o teste vermelho), S-12,
  e S-13 (id do repositório errado) e S-14 (id do dono errado) — estes dois pré-condição do SIGN do 1a
  (§6). VERDE só no íntegro com a política certa (S-02, S-10).
- **MODO OBRIGATÓRIO (condição 13).** Uma variável de ambiente (nome proposto
  `CEO_CODEX_AUTO_PIN_CRYPTO_REQUIRED`) faz os testes da camada 2 (classes `crypto_real`) **FALHAREM em
  vez de pular** quando `node`, o material do ramo escolhido ou a raiz fixada faltarem.
  - **Ligam o modo:** a bateria do LAND de todo pacote que toca o verificador, o auxiliar, o material de
    empacotamento, as constantes da §6 ou o núcleo (SKIP = falha no conjunto exato); o Check de SUCESSO
    da W3; o Check da W3.4 do plano. A Fase 1 real roda a mesma chamada.
  - **CI sem `node`:** só pode rodar SEM o modo, com o SKIP CONTADO e IMPRESSO no log, declarado; nunca
    verde silencioso. Um job de CI com `node` e o material do ramo escolhido é follow-up.
  - **Controle positivo:** `node` fora do PATH com o modo ligado ⇒ VERMELHO.
  - **Inventário de ambiente no mesmo pacote (1a) — corrigido na r4.** O `env-inventory-check.py`
    coleta TOKENS `CLAUDE_*`/`ANTHROPIC_*`/`CEO_*` em código de framework — uma constante, docstring ou
    comentário conta, não só uma leitura (`:12-14`, `:107` **[disco]**) — e exclui `tests/` e
    `fixtures/` do scan (`:19-20`; `SKIP_DIRS` em `:75-79` **[disco]**). O `--check` acusa nome NOVO (no
    código, fora do inventário) ou STALE (no inventário, sem ocorrência no código) (`:164-169`
    **[disco]**) e roda como aviso no CI (`.github/workflows/validate.yml:194-198` **[disco]**). Medido
    nesta revisão: `--check` rc 0 no HEAD; 517 nomes no inventário; nenhum com `CRYPTO_REQUIRED`.
    O scan inclui o PRÓPRIO inventário: `.claude/scripts` está nas raízes e `.json` nas extensões
    (`:61-71` **[disco]**), sem exclusão do arquivo. Logo a declaração SÓ no inventário já é ocorrência
    «viva» do token: medido em memória nesta revisão (diff do scan real contra o inventário acrescido do
    nome), `clean`, 518 nomes, zero novo, zero stale. **Não há exigência de o token aparecer no
    verificador `.py`** (nem de função nova). O `.claude/scripts/env-inventory.json` [oráculo 0] é path do
    1a porque a **condição 13 pede a declaração no MESMO pacote** — não por causa do scanner (contagem e
    exceção (5): §24).
- A raiz TUF fixada vale só no teste; em produção o cache TUF é novo e atualizado do CDN (§4.4).

### 19.3 Guarda de rede dos FILHOS (QA r2 MF-13; condição 11 do consenso r3)

- Os subprocessos `node`/npm dos testes rodam com `HTTPS_PROXY`/`HTTP_PROXY` apontando para um proxy
  morto e `NO_PROXY` vazio (molde da W0.6, V-N2/V-N4).
- **Controle positivo VERMELHO ANTES de qualquer resultado contar [a medir no pacote 1a e no 1b]:** um
  fetch do `node` filho FALHA sob o ambiente. Enquanto esse controle não estiver vermelho, nenhum
  resultado da camada 2 nem de célula «sem rede» conta.
- **Se as variáveis de proxy não prenderem o filho** (o `fetch` nativo do `node` pode não honrá-las por
  padrão), o builder troca o mecanismo, com o MESMO controle positivo: (a) nos testes, TUF só de cache
  sobre a raiz fixada (o auxiliar recebe a ordem de não buscar), ou (b) isolamento de rede do processo.
- Resultado do controle e mecanismo escolhido vão ao LEDGER, com substrato.
- A guarda de socket do Python continua para o hook (H-12).

### 19.4 Censo das células (condições 14 e 15 do consenso r3)

- Arquivos nomeados AGORA: `.claude/hooks/tests/test_check_pair_rail_auto_pin.py` [oráculo 0] (H-01..H-14,
  C-01..C-02, R-01) e `.claude/scripts/tests/test_codex_auto_pin_verify.py` [oráculo 0] (A-01..A-26,
  F-01..F-09, P-01..P-05, K-01..K-06 contra um kit sintético, B-01..B-04, T-01..T-04; camadas 1 e 2 em
  classes distintas). As células W-01..W-09 ficam no teste da guarda
  (`.claude/hooks/tests/test_codex_pin_registry_guard.py`, [oráculo 0]; pacote 1b ou 1c, §24).
- Um teste-censo liga cada id de §9 a ≥ 1 teste e compara por CONJUNTO EXATO (molde `_EXPECTED_SITES` do
  `test_verify_counts.py`): célula removida em silêncio fica vermelha; id desconhecido também.
- **O censo também afirma que cada teste mapeado está DENTRO da seleção do Check** que deveria rodá-lo
  (W3.3 ou W3.4): o node id de cada teste ∈ o conjunto de node ids que o Check seleciona. Teste fora da
  seleção ⇒ vermelho.
- Os Checks de W3.3 e W3.4 usam **node ids de classe** (`arquivo::Classe`), nunca `-k`, porque `pin`,
  `auto`, `rail`, `pair`, `check`, `codex` e `verify` são substrings dos nomes dos módulos. W3.3 →
  classe da sonda e do canário; W3.4 e o Check de SUCESSO → classes da matriz, da fronteira, do censo e da
  camada 2 (com o modo obrigatório ligado), a classe do hook (`test_check_pair_rail_auto_pin.py`) **e a
  classe da guarda** (`test_codex_pin_registry_guard.py`, W-01..W-09) — sem esta última, o censo
  («cada teste mapeado está na seleção») ficaria vermelho com a implementação correta. Um texto só, o
  deste AMEND-1; o plano cita, não repete.

### 19.5 Checks da W3 (condições 9 e 23 do consenso r3)

- **Sucesso da W3 e W3.6:** `--verify-codex-pin <caminho do lançador> --allow-auto-pin` e afirmação, no
  código de saída, de **`status == "verified_auto"` E `pin_source == "registry"`** para uma versão FORA
  do manifesto; verde por construção é proibido.
- **Forma do argv (teste no 1b).** A flag vem DEPOIS do caminho do lançador, porque `_verify_pin_cli`
  toma `argv[0]` como lançador (`check_pair_rail.py:2513` **[disco]**: `launcher = argv[0] if argv else
  None`). Um teste fixa a forma exata do Check e falha se a flag puder ser lida como caminho.
- **Validade do instante (condição 23).** O Check de sucesso vale para o instante do fechamento da W3. Se
  uma cerimônia futura puser no manifesto a mesma versão instalada, ele volta a dar `verified`/`manifest`,
  e isso é esperado.
- **W3.1:** sem flag, escopo «até o LAND».
- **Células de controle restantes:** quarentena ⇒ `mismatch`; rollback para sha registrado ⇒
  `verified_auto` depois da re-verificação SEM canário + Fase 2 (com rede, R-16; §15); C-01 (sem flag ⇒
  registro não aberto); R-01 (validador INVALID para versão só auto-pinada); costura do registro inerte
  no caminho vivo (controle negativo, molde `test_fixture_ignored_on_live_path_without_test_mode`);
  constante de 48 h; tabela de gramática com a armadilha medida literal; H-13 e H-14 (resíduos
  documentados).

## §20 Cláusulas do ADR-182 emendadas

1. **§2, linha «payload sha256 != manifest entry → fail-CLOSED».** Passa a ser: sha256 do payload ∉
   {entrada do manifesto} ∪ {entradas confiáveis do registro local de pin automático para o mesmo
   triple, consultadas SÓ no caminho do hook e na CLI com flag explícita} ⇒ SECURITY, fail-CLOSED block.
   O registro só acrescenta confiança; ausente, ilegível ou malformado = nenhuma confiança extra, nunca
   INFRA. Os braços INFRA do §2 ficam inalterados.
2. **§3, «um núcleo, três consumidores».** Passa a ser: um núcleo, consumidores com contrato escrito
   (§11). O verificador usa o mesmo núcleo para resolver e hashear.
3. **§5, cerimônia de atualização.** Continua a ÚNICA via para mudar o MANIFESTO (trilha de release e
   piso). Para o HOOK, uma versão nova vale sem cerimônia quando o verificador desta emenda a registra. O
   passo 5 (gatilho do ADR-111 §2) fica PRESERVADO e declarado NÃO AVALIÁVEL até existir corpus com sha
   e linha de base.
4. **§Consequences, «cache por (path, mtime, size)».** Esta emenda NÃO é esse cache.

## §21 Residuais declarados

**Retirados nesta revisão:** o R-1 da r2 («confiança no registro») sai — virou decisão de EMPACOTAMENTO,
e a confiança no registro é ESCALATE (§7); o R-12 da r2 (ordem M4 na rota 2) sai — a rota 2 é invertida
(§17).

- **R-2 — Sentinela de qualidade (decisão 4 [Owner]).** Recomendação: a W3 landa SEM sentinela,
  declarada; o gatilho de 5 pp do ADR-111 §2 fica NÃO AVALIÁVEL até haver corpus com sha e linha de
  base (m ≥ 3). Sonda e canário cobrem a LIVENESS, não a qualidade.
- **R-3 — Evidência só no registro (decisão 6 [Owner]).** Só se o Owner quiser evitar o pacote de
  kernel. Recomendação: manter o evento na cadeia.
- **R-4 — Par modelo/esforço (decisão 5 [Owner]).** Ver §22.
- **R-5 — Mesmo UID, autodeclaração do instrumento e código arbitrário (vias NOMEADAS; condições 5 e 7
  do consenso r3).**
  - **Processo ALHEIO de mesmo UID:** registro, chave HMAC e manifesto são legíveis e graváveis; a defesa
    é detecção (evento + cruzamento do boot, B-01/B-02).
  - **Via 1 — «agente que edita o verificador e o executa».** O H-07 compara os shas que a linha
    DECLARA (I8): um verificador editado, executado por invocação permitida (W-05) e restaurado grava
    uma linha que declara os shas legítimos, e o núcleo concede confiança — o teste H-14 DOCUMENTA isso.
    Fechada para as formas diretas de escrita pela guarda das FONTES (W-07..W-09), landada antes do 1.º
    LAND do 1a. **Se essa guarda não couber antes do 1a, este resíduo vai TAMBÉM ao material assinado** —
    nunca fica silencioso.
  - **Via 2 — «código que calcula o caminho».** Código arbitrário executado pelo agente que calcula o
    caminho do registro ou de uma fonte sem nomeá-lo escapa de qualquer guarda por texto de comando
    (classe comum a todos os guardas de Bash). Defesas restantes: H-07, evento-antes-da-linha,
    cruzamento do boot e evidência em repouso das fontes (§4.1).
  - **A lacuna de guarda da família do log de auditoria** (log, chave, sal e sidecars) é follow-up COM
    DONO no PLANO — item com dono e posição antes do SIGN do 1b, com a pergunta respondida no disco
    (existe guarda? com que controle?) (condição 5; ajuste 11 do consenso r3). Domínio do VETO (ADR-052).
    Não bloqueia a W3; bloqueia ficar sem dono.
- **R-6 — Escopo.** O pin não protege a máquina; o hook confere só o `bin/codex`; os irmãos são conferidos
  na promoção; a troca deles depois é resíduo de mesmo UID (documentado por H-13).
- **R-7 — TOCTOU hash→exec** num caminho absoluto já resolvido (ADR-182, inalterado).
- **R-8 — Braços INFRA inalterados.** Manifesto ausente, lançador ou payload ausente ⇒ o rail some com
  aviso. Com o `_emit_audit()` ligado, a contagem diária do boot passa a ter instrumento durável.
- **R-9 — Chamadores declarados** (§14).
- **R-10 — Limite do `parse_semver`** do validador (§16).
- **R-11 — Adopters** seguem em INFRA aberto.
- **R-13 — Dependência de rede dos cortes:** a versão do manifesto (0.156.1) tem de seguir baixável.
- **R-14 — Carência ≠ detecção garantida;** um comprometimento do repositório ou do workflow de release
  do upstream gera atestado VÁLIDO com a identidade certa [W0.6 §6.9].
- **R-15 — Downgrade dentro do registro:** qualquer versão registrada e fora de quarentena é aceita.
- **R-16 — O rollback exige rede** (§15), mas não cota (o canário é pulado para sha já registrado).
- **R-21 — Proteção REDUZIDA dos ids imutáveis, SE o fallback (b) da §6 for usado:** ids lidos do statement
  (conteúdo do assinante) ⇒ «repositório recriado com o mesmo nome passa». Declarado no material
  assinado só se S-13/S-14 e o fallback (a) falharem.
- **R-17 — Irmãos na rota 2:** a versão do manifesto materializada pelo kit tem só o `bin/codex`
  conferido (o manifesto pina só ele); os irmãos vêm do registro pela integridade do npm. Follow-up: o
  kit chamar o verificador em modo só-verificação (sem linha) sobre a versão do manifesto.
- **R-18 — Lista fechada de hosts** imposta por configuração explícita e asserção, não por filtro de rede
  de processo.
- **R-19 — `npm i -g` cru de versão JÁ registrada:** o `bin/codex` confere (H-02), mas os irmãos vêm de
  busca nova não conferida até um `--check-installed`.
- **R-20 — Instrumento com dependência de terceiro:** `node` + sigstore (ramo (ii) governado por lockfile;
  ramo (i) pelo npm do Homebrew sob lista canônica); a raiz TUF evolui e é REGISTRADA, não pinada.

## §22 Decisões pendentes do Owner (a decidir pelo Owner; recomendação do CEO; forma final da §5 do consenso r3)

**Nenhuma das decisões abaixo foi tomada até esta revisão.** Cada uma é ESCRITA neste §22, com data e
texto do Owner, assim que sair; as decisões 4, 5 e 6 antes do pacote de ADR (1b) (condição 2 do consenso
r3). Os ramos (ii) e (i) da decisão 3 ficam aqui como ALTERNATIVAS.

1. **Decisão 3 — empacotamento do verificador de assinatura. É ESTA DECISÃO QUE RETIRA O VETO DA W3.**
   - **(ii)** `sigstore` em versão exata, lockfile de integridade de toda a árvore sob o manifesto ADR-192,
     `npm ci` com scripts suprimidos em staging novo: código de terceiro governado pelo repositório.
   - **(i)** o módulo interno do npm, com lista canônica de versões e shas e recusa fora dela: muda num
     upgrade do npm do Homebrew; a falha é fail-closed (perde vivacidade, não segurança).
   - **Recomendação: (ii)**, preferida pelo portador do VETO e por outro crítico. Os testes de cada ramo
     estão pré-registrados na §7.
   - A retirada do VETO vale no INSTANTE em que a decisão estiver ESCRITA como (ii) ou (i). «Confiança no
     registro» ⇒ VETO segue LEVANTADO ⇒ **ESCALATE-TO-OWNER** por múltipla escolha, e o `design-coherent`
     da W3 deixa de valer. Recusar a dependência de `node` ⇒ plano B (re-pin manual).
   - Escrever (ii) ratifica também a exceção (5) da «Regra de WIP» do plano: o pacote 1a com 9 paths (§24).
   - **Texto do Owner:** _(pendente)_
2. **Decisão 4 — sentinela de qualidade.** Recomendação: (ii), landar SEM sentinela, declarada (R-2); o
   gatilho do ADR-111 §2 fica preservado como NÃO AVALIÁVEL até haver corpus com sha e linha de base.
   **Texto do Owner:** _(pendente)_
3. **Decisão 5 — modelo e esforço fixos no argv do rail.** Recomendação: `gpt-6-astra` + `xhigh`,
   condicionado ao re-teste da Q11. O par e as flags (`--ignore-user-config` incluída) precisam existir
   também na 0.156.1, que o corte usa. **Adopters:** recomendação de opt-in, mantendo o padrão da conta,
   porque um id fixo que a conta deles não sirva rebaixa o rail a advisory. **Texto do Owner:**
   _(pendente)_
4. **Decisão 6 — evidência da aceitação automática.** Recomendação: evento na cadeia HMAC (§12); «só no
   registro» apenas por decisão escrita, com o resíduo R-3. **Texto do Owner:** _(pendente)_
5. **Para ciência, sem decisão:** carência de 48 h (o pin anda ~2 dias atrás da `latest`); a W3 tem
   1c/1b, 1a, 2 e kernel, e a W3.6 depende deles e da rota 2 invertida, que pode ser a 1.ª peça da W7.1;
   cada promoção é janela de manutenção; o rollback exige rede (R-16), mas não cota; toda cerimônia do
   verificador exige re-verificação logo depois (§24).

## §23 Consequências

- (+) O hook deixa de exigir cerimônia por versão; o Owner assina por GERAÇÃO de modelo (eixo 2) e por
  mudança do INSTRUMENTO (ADR-192), não por versão da CLI.
- (+) A decisão criptográfica é tomada por implementação de referência (sigstore) com política de
  identidade exata, sem criptografia à mão, e o vínculo de bytes fica em stdlib.
- (+) Promoção pelos bytes verificados: os irmãos e o lançador passam a ter procedência conferida.
- (+) A rota 2 do corte deixa de executar antes de verificar.
- (+) Cada aceitação vira evidência durável; o mismatch do pin passa a ser evento.
- (−) O verificador depende de `node` + sigstore (declarado no `SBOM.md`; fora do runtime dos hooks).
- (−) Cada adoção baixa ~135 MB (mais o staging do npm), gasta um canário de cota e para o rail por uma
  janela curta.
- (+) O rollback não depende de cota: para sha já registrado ou versão do manifesto, pula o canário (§15).
- (−) O pin anda ~2 dias atrás da `latest`; o rollback exige rede (R-16).
- (−) **Toda cerimônia do INSTRUMENTO revoga a confiança na versão auto-pinada instalada.** Pelo H-07, um
  LAND que muda o verificador, o auxiliar, o `package.json` ou o lockfile (ou a lista do ramo (i)) — cada
  um com campo próprio na linha (§4.1) — faz a linha existente declarar shas que não estão mais no
  manifesto ADR-192 ⇒ sem confiança ⇒ o rail
  BLOQUEIA todas as escritas L3+ logo depois do LAND. Por isso a **re-verificação logo depois do LAND**
  faz parte do material de TODA cerimônia ADR-192 do instrumento (condição 19 do consenso r3): a versão
  instalada é re-verificada pelo verificador NOVO (grava linha nova, que declara os shas novos; sem
  canário quando aquele sha já passou nele, como no rollback), ou a versão do manifesto é reinstalada
  (rota de emergência, §15). Declarado no material assinado.
- (−) O H-07 compara shas DECLARADOS (I8): a defesa contra verificador adulterado é a guarda das fontes
  (W-07..W-09), e o resíduo fica nomeado (R-5, H-14).
- (−) O Gate 4 da fase 6 reprova com o global auto-pinado (por desenho; mensagem nomeia a rota 2).

## §24 Pacotes, `SBOM.md`, manifesto ADR-192 e reversibilidade (MF-R2-W3-7, MF-R2-W3-8)

**Ordem: 1c (se existir) → 1b → 1a → 2, mais o pacote de kernel** (em série com a W1a do PLAN-195; antes
da W3.6). O 1b vem antes do 1a porque o verificador reaproveita funções e constantes do núcleo; a guarda
das FONTES do verificador landa antes do 1.º LAND do 1a (condição 6); o 1b landa ANTES de começar a
derivação do kit da W7 (§18).

**Valores do oráculo `check_canonical_edit.py --is-canonical`, medidos nesta revisão (HEAD `304ec478`):**

| pacote | path | oráculo |
|---|---|---|
| 1c (ou 1b) | `.claude/hooks/check_bash_safety.py` (hospedeiro candidato da guarda de Bash) | 1 |
| 1c (ou 1b) | `.claude/settings.json` (`permissions.deny`) | 1 |
| 1c (ou 1b) | `.claude/hooks/check_harness_config.py` (linha de base da negação) | 1 |
| 1c (ou 1b) | `.claude/hooks/check_canonical_edit.py` (só se as fontes forem por `_CANONICAL_GUARDS`; kernel) | 1 |
| 1c (ou 1b) | `.claude/hooks/tests/test_codex_pin_registry_guard.py` (novo; nome proposto) | 0 |
| 1b | `.claude/adr/ADR-182-AMEND-1-codex-auto-pin-provenance.md` (novo) | 1 |
| 1b | `.claude/hooks/check_pair_rail.py` (kernel) | 1 |
| 1b | `.claude/hooks/tests/test_check_pair_rail_auto_pin.py` (novo) | 0 |
| 1b | `docs/CROSS-LLM-THREAT-MODEL.md` (T-8) | 0 |
| 1b (exceção (4) da regra de WIP) | `.claude/adr/README.md` (índice) e os documentos de contagem que o arquivo de emenda arrasta | 1 (índice) |
| 1a | `.claude/scripts/codex-auto-pin-verify.py` (novo) | 0 |
| 1a | `.claude/scripts/codex-auto-pin/verify-sigstore.js` (novo) | 0 |
| 1a, ramo (ii) | `.claude/scripts/codex-auto-pin/package.json` (novo) | 0 |
| 1a, ramo (ii) | `.claude/scripts/codex-auto-pin/package-lock.json` (novo) | 0 |
| 1a, ramo (i) | `.claude/scripts/codex-auto-pin/npm-sigstore-allowlist.json` (novo; nome proposto) | 0 |
| 1a | `.claude/scripts/tests/test_codex_auto_pin_verify.py` (novo) | 0 |
| 1a | `.claude/scripts/tests/fixtures/codex_auto_pin_sigstore_fixtures.json` (novo; nome proposto) | 0 |
| 1a | `SBOM.md` | 0 |
| 1a | `.claude/governance/gate-scripts-manifest.txt` (ADR-192) | 1 |
| 1a (condição 13) | `.claude/scripts/env-inventory.json` | 0 |
| 2 | `.claude/hooks/_lib/codex_cli_shape.py` | 1 |
| 2 | `.claude/scripts/codex_invoke.py` | 0 |
| 2 | `.claude/scripts/run-promotion-gate.py` | 0 |
| 2 | `.claude/scripts/local/pair-rail-gate.sh` (mensagem do Gate 4 nomeando a rota 2) | 0 |
| 2 | `.claude/scripts/tests/test_codex_callers_verified_path.py` (novo; nome proposto) | 0 |
| kernel | `.claude/hooks/_lib/audit_emit.py` | 1 |
| kernel | `SPEC/v1/audit-log.schema.md` | 1 |
| livre (condição 8; §15) | `.claude/scripts/ceo-boot.py` | 0 |
| livre (§15) | `.claude/scripts/check-substrate-drift.py` | 0 |

Nenhum desses paths é membro do manifesto ADR-192 hoje — nem o próprio `gate-scripts-manifest.txt`, que
não lista a si mesmo [disco: as 9 entradas do arquivo são `verify-counts.sh`, `validate-governance.sh`,
`_release_tag_guard.py`, `check-canonical-doc-freshness.py`, `ownership-nightly-gate.sh`,
`ownership-expected-reds.txt`, `release.sh`, `validate-pair-rail-verdict.py` e `await_release_gate.py`].
Ser canônico (oráculo 1, como o manifesto) e constar do manifesto são propriedades distintas. Os paths do
1a que são fontes do verificador entram no manifesto no próprio 1a.

- **Pacote 1c (guarda; PRIMEIRO da fila se o 1b passar de 8 paths):** a guarda do REGISTRO
  (W-01..W-06) e a guarda das FONTES do verificador (W-07..W-09), no(s) hospedeiro(s) escolhido(s) com as
  regras de série da §10.4 (condição 4), mais o teste da guarda. Conteúdo mínimo: 1 hospedeiro de Edit/Write,
  1 de Bash (ou o mesmo), a negação em `permissions.deny` com a linha de base, e o teste; com o mecanismo
  (a) das fontes, também `check_canonical_edit.py` (kernel).
- **Pacote 1b (núcleo + texto):** AMEND-1, `check_pair_rail.py` (consulta ao registro, H-07 com shas
  DECLARADOS, `_emit_audit()` ligado, sumidouro só em modo de teste, forma do argv da CLI), o teste do hook
  e o T-8 = 4 paths, mais o índice pela exceção (4). Com a guarda dentro, passa de 8 ⇒ a guarda vai ao 1c.
- **Pacote 1a (verificador) — contagem da condição 3:** **8 paths no ramo (ii)** (verificador `.py`,
  auxiliar `.js`, `package.json`, `package-lock.json`, teste do verificador, fixtures, `SBOM.md`,
  `gate-scripts-manifest.txt`) e **7 no ramo (i)** (a lista canônica no lugar do par `package.json` +
  lockfile).
  - **Conflito declarado com a condição 13.** A variável do modo obrigatório entra no inventário de
    ambiente NO MESMO pacote (condição 13, ajuste 17 do consenso r3) ⇒ o `env-inventory.json` é um 9.º path
    no ramo (ii) (8.º no ramo (i)). O scanner não impõe nada além disso: ele inclui o próprio inventário
    (`env-inventory-check.py:61-71` **[disco]**), e a declaração só no inventário dá `clean` (§19.2). **Proposta do CEO (S361), registrada no plano como exceção (5) da «Regra de
    WIP»:** (b) exceção escrita de 9 paths no 1a, que mantém a letra das condições 3 e 13 e do MF-R2-W3-7 — o path
    extra é dado de inventário; ou (a) o `SBOM.md` no 1b — tira o 1a para 8/7, mas sai da letra do
    MF-R2-W3-7 («no MESMO pacote») e precisa do aceite do portador do VETO no rail — descartada. A exceção (b) vale só no ramo (ii) e
    é ratificada junto da decisão 3 (§22); no ramo (i) o 1a fica em 8 paths.
- **Pacote 2:** `codex_cli_shape.py` (eixo 2; depois da W3b), `codex_invoke.py`, `run-promotion-gate.py`,
  `pair-rail-gate.sh` (mensagem do **Gate 4 no pacote 2**, condição 3) e o teste dos chamadores = 5 paths.
- **Pacote de kernel:** `audit_emit.py`, SPEC do audit-log e contagens.
- **Livres:** a evidência em repouso e o cruzamento do boot no `ceo-boot.py`; o detector de deriva.
- **Kit da W7 (não é pacote da W3, é pré-condição da W3.6):** os dois derivadores com a rota 2 invertida
  (§17), que podem landar como a PRIMEIRA peça da W7.1 (§18).
- **Re-verificação logo depois de todo LAND do instrumento (condição 19).** O material da cerimônia
  ADR-192 de TODO LAND que muda o verificador, o auxiliar, o `package.json`, o lockfile ou a lista do
  ramo (i) inclui, logo depois do LAND: re-verificar a versão instalada com o verificador NOVO, ou
  reinstalar a versão do manifesto. Declarado no material assinado (§23).
- **`SBOM.md` no pacote 1a:** declara a dependência de TEMPO DE OPERAÇÃO (`node` + sigstore-js, versão e
  integridade; ramo (ii) pelo lockfile, ramo (i) pela lista canônica) como ferramenta de MANTENEDOR, fora
  do runtime dos hooks; a afirmação «stdlib-only» fica escopada ao runtime dos hooks no MESMO pacote, sem
  afirmação pública falsa. O `CLAUDE.md` §3 só muda no fechamento, dentro da poda (risco 9 do plano).
- **Manifesto ADR-192:** verificador `.py`, auxiliar `.js` e material de empacotamento DENTRO; a linha do
  `gate-scripts-manifest.txt` no mapa de colisões ganha a W3 (pacote 1a), «nunca em paralelo» com W7,
  W7b, W10 e W5c. O plano deixa de chamar o verificador de «livre».
- **Fora:** `codex-cli-pin.txt`, o manifesto do Codex, o validador, o `release.yml`. O oráculo
  `--is-canonical` roda em todos os paths na abertura de cada pacote.
- **Reversibilidade: ALTA** para a extensão de confiança (reverter o hook deixa o registro inerte; apagar
  o registro é a direção segura). **MÉDIA** para o kernel (ações registradas ficam) e para a guarda.

## §25 Alternativas consideradas

| opção | decisão | por quê |
|---|---|---|
| A — conferir procedência dentro do hook | rejeitada | timeout de 210 s ⇒ allow; kernel processando entrada de rede |
| B — re-pin manual por versão (ADR-182 §5) | plano B | ~1 cerimônia/dia |
| C — re-pin do manifesto por script no kit | adiada (follow-up) | não serve o hook |
| D — cache do hash por (caminho, mtime, tamanho) | rejeitada | Unseen 10 da r1 |
| E — registro na árvore git | rejeitada | suja o SIGN; 2.ª fonte versionada |
| F — registro em `state/` | rejeitada | alcance do GC da W2 |
| G — `npm audit signatures` como decisão | **rejeitada pela W0.6** | falso verde em V-T2, V-R1, V-P3, V-N1, V-N3; aceita S-11 |
| H — criptografia Sigstore escrita à mão em stdlib | rejeitada | proibida (MF-W3-3); a stdlib não lê as extensões do Fulcio |
| I — «confiança no registro» | **ESCALATE** | VETO; há mecanismo medido que a dispensa |
| **J — verificador próprio (Python + `node`/sigstore com política) + registro protegido + hook só-consulta + promoção pelos bytes verificados + evento HMAC** | **escolhida** | fecha C1–C8 (r1) e C8–C13 (r2) sem tocar a trilha de release |

## §26 Rastreabilidade — MF-W3-1..11 (rodada 1), atualizada

| MF | endereçado em |
|---|---|
| MF-W3-1 | §3 I2/I5, §4.3, §8, §9 (A, F, P, H-03..H-07), §20 item 1 |
| MF-W3-2 | §3 I3, §4.1, §4.4, §8, H-12 |
| MF-W3-3 | §4.2 V-5 e proibições, §6, §7, A-14, A-15, §9.F |
| MF-W3-4 | §5 item 1, §6, A-07, A-13, A-14, A-17, A-25 |
| MF-W3-5 | §10, §11, §9.C/R, §21 R-5 |
| MF-W3-6 | §3 I6, §12, A-22, §22 decisão 6 |
| MF-W3-7 | §3 I4, §4.2 (V-9 depois de V-8), A-19, A-20, §19.1 |
| MF-W3-8 | §13, §22 decisão 5 |
| MF-W3-9 | §5, A-08..A-11 |
| MF-W3-10 | §14, §21 R-9 |
| MF-W3-11 | §16, §17, §18, §20 (a parte «W3.6 depois da W7» foi refutada pelo disco, consenso r1 §2(c)) |

## §27 Rastreabilidade — MF-R2-W3-1..8 (condição do VETO da rodada 2)

| MF | exigência (resumo) | endereçado em |
|---|---|---|
| MF-R2-W3-1 | V-5 = `sigstore.verify` COM política (SAN exato, emissor exato, ids imutáveis do repositório e do dono); nunca `npm audit signatures`; os DOIS bundles exigidos pelo verificador (A-12); A-14 e A-15 = RECUSA; literais medidos como constantes com teste | §4.2 V-4/V-5, §6 (tabela da política + [a medir na abertura] S-13/S-14), §9.A A-12/A-14/A-15, §0.2, §25 G |
| MF-R2-W3-2 | empacotamento (ii) preferido ou (i) com lista canônica; versão e sha na linha e no evento (`signature_mode`); decisão 3 reescrita; «confiança no registro» ⇒ VETO levantado + ESCALATE | §7 (dois ramos com testes), §4.1, §10.2, §12, §22 decisão 3 |
| MF-R2-W3-3 | sha512 do tarball = digest do `subject` do bundle VERIFICADO (`dist.integrity` só cruzamento); caches npm e TUF NOVOS; 2.º host declarado; tetos medidos | §4.2 V-3/V-6, §6 «Âncora do vínculo», §4.4 (lista fechada, caches, tabela de tetos), A-01, A-03, A-05, A-16, F-08 |
| MF-R2-W3-4 | promoção confere a ÁRVORE inteira contra o manifesto de membros, ou instala dos bytes verificados; P-01 além do `bin/codex`; §2 e R-6 com os irmãos | §4.3 (os dois: bytes verificados sob proxy morto E P-01 da árvore), §9.P, §2, §21 R-6, H-13, §10.2 `members` |
| MF-R2-W3-5 | registro protegido contra escrita do PRÓPRIO agente (Edit, Write, Bash, acréscimo por redirecionamento), com controle positivo; «a conferir» resolvido no pacote | §10.4, §9.W, §3 I8, §24 (1b ou 1c), §21 R-5 |
| MF-R2-W3-6 | rota 2 do kit INVERTIDA (materializar sem executar, ambiente npm do zero, scripts suprimidos, oráculo sem flag, só então executar); R-12 sai; pré-condição da W3.6 com espião | §17, §9.K, §18 item 5, §21 (R-12 retirado) |
| MF-R2-W3-7 | `SBOM.md` declara `node` + sigstore-js; «stdlib-only» escopado ao runtime dos hooks no MESMO pacote | §24 (`SBOM.md` no 1a), §4.1, frontmatter `amends_targets`, §0 (afirmações FALSAS corrigidas) |
| MF-R2-W3-8 | reconciliar plano, AMEND-1 e W0.6 (W3.4 sem «aceita e declarada»; identidade no `subject` verificado e ids imutáveis; paths com ADR-192, lockfile, `SBOM.md`; verificador não «livre»; decisão 3 reescrita) | §6, §7, §9.A, §24, §22; o texto do PLANO é do CEO (ajustes 23–39 do consenso r2) — este rascunho é a fonte que o plano reconcilia |

## §28 Rastreabilidade — lista (b) 1–23 do consenso da rodada 2

| item | conteúdo | endereçado em |
|---|---|---|
| 1 | V-5 = `sigstore.verify` com política (SAN, emissor, OIDs imutáveis), bundles do próprio verificador, constantes com teste, nunca `npm audit signatures` | §4.2 V-5, §6 |
| 2 | os DOIS bundles exigidos; A-12 do verificador | §4.2 V-4, A-12 |
| 3 | A-14 e A-15 = RECUSA | §9.A A-14, A-15 |
| 4 | vínculo ao `subject` VERIFICADO pelos mesmos bytes; `dist.integrity` só cruzamento | §4.2 V-6, §6, A-16 |
| 5 | caches npm e TUF novos com asserção; cache quente vira célula | §4.4, V-0, F-08 |
| 6 | lista FECHADA de hosts (registro + `tuf-repo-cdn.sigstore.dev`); A-03 e §4.4 corrigidos | §4.4, A-03, §21 R-18 |
| 7 | tetos medidos | §4.4 (tabela) |
| 8 | §4.1: Python + `node` como exceção nomeada; `node` absoluto com versão mínima; versões, lockfile, digest TUF na linha e no evento; trocar = «instrumento mudou»; `verifier_sha256` e lockfile no H-07 | §4.1, §10.2, §12, H-07 |
| 9 | empacotamento conforme a decisão 3, ramos (ii) e (i), testes pré-registrados | §7 |
| 10 | células de fronteira, todas recusa: `node` ausente, sigstore ausente/movido/versão, não-JSON, código ≠ 0, tempo, sem política (mutante S-11), cache quente | §9.F F-01..F-09 |
| 11 | duas camadas de teste com lugar pré-registrado; fixture sintética só nas células de forma | §19.1, §19.2 |
| 12 | guarda de rede dos FILHOS com controle positivo | §19.3 |
| 13 | promoção dos bytes verificados + P-01 da árvore inteira; manifesto por membro; §2 e R-6; teste do resíduo | §4.3, §9.P, §10.2, §2, H-13, R-6 |
| 14 | quiesce (`lsof`/`ps` sobre o caminho, nunca `pgrep -f`); janela de manutenção | §4.3, P-03, §22 item 5 |
| 15 | rota 2 INVERTIDA no kit; controle com registro redirecionado e espião; R-12 sai; argv sondado na 0.156.1 | §17, §9.K, §13, §18 |
| 16 | registro protegido contra escrita do agente; controle positivo; «a conferir» resolvido; lacuna da família do log como item próprio | §10.4, §9.W, R-5 |
| 17 | `SBOM.md`; «stdlib-only» escopado; `CLAUDE.md` §3 só no fechamento | §24, §4.1 |
| 18 | manifesto ADR-192 (verificador, auxiliar, lockfile); linha do mapa; pacotes 1a/1b; ordem 1b → 1a; oráculo no auxiliar | §4.1, §24 |
| 19 | Checks da CLI com `--allow-auto-pin` e `pin_source == "registry"`; literal único; W3.1 sem flag | §11, §19.5 |
| 20 | censo das células; arquivo de teste do verificador nomeado; seletores distintos | §19.4 |
| 21 | rollback: R-16 | §15, §21 R-16 |
| 22 | `_emit_audit()` ligado no 1b; sumidouro só em modo de teste; mensagem do Gate 4 nomeando a rota 2; canário com diff sintético; política de nova tentativa | §12, §11, R-04, §4.5, V-10 |
| 23 | decisões 3 a 6 escritas no AMEND-1 assim que saírem | §22 (escritas como «a decidir pelo Owner», com recomendação; o texto da decisão entra aqui quando sair) |

## §29 Rastreabilidade — condições de execução 1–23 do consenso FINAL (rodada 3)

| cond. | conteúdo | pacote | endereçado em |
|---|---|---|---|
| 1 | decisão 3 ESCRITA (ii)/(i); «confiança no registro» ⇒ ESCALATE | Owner | §0, frontmatter `decided_by`, §7, §22.1, §18 item 1 |
| 2 | decisões 4, 5 e 6 escritas antes do pacote de ADR (1b) | Owner/CEO | §22 |
| 3 | plano reconciliado com o AMEND-1 (nomes, 1a 8/7, Gate 4 no pacote 2, 1c primeiro) | texto | §24 (com o conflito da condição 13 declarado); o texto do plano é do CEO |
| 4 | hospedeiro da guarda e linhas no mapa de colisões | texto | §10.4 «Hospedeiros e colisões», §24 |
| 5 | lacuna da família do log com DONO no plano | texto | §10.4, §21 R-5 (o item vive no plano) |
| 6 | guarda das FONTES do verificador, antes do 1.º LAND do 1a | 1c/1b | §9.W W-07..W-09, §10.4, §3 I8, §24 |
| 7 | I8 e H-07 dizem o que o mecanismo prova; teste do resíduo; via nomeada | 1b; texto | §3 I8, §4.1, §8, §9.H H-07/H-14, §21 R-5 |
| 8 | evidência em repouso no boot | livre | §4.1, §15 |
| 9 | CLI afirma `status` e `pin_source`; forma do argv | 1b | §11, §19.5 |
| 10 | S-13/S-14 antes do SIGN do 1a; ordem de fallback honesta | 1a | §6, §19.2, §21 R-21 |
| 11 | guarda de rede do `node` filho com controle positivo VERMELHO | 1a, 1b | §19.3, §18 item 3 |
| 12 | P-04 com opções explícitas, modo offline e controle positivo de cache vazio; o MESMO controle de falha no K-06 (a materialização do kit segue online) | 1a; W7 | §4.3, §9.P, §9.K |
| 13 | camada 2 em MODO OBRIGATÓRIO; inventário de ambiente | 1a | §19.2, §24 (conflito de contagem) |
| 14 | Checks da W3.3/W3.4 por node id de classe; censo × seleção | texto | §19.4 |
| 15 | B-01..B-04, A-26, fronteiras de relógio, constante do F-06 | 1a | §9.A A-26, §9.T, §9.B, §9.F F-06, §19.4 |
| 16 | literais do AMEND-1 nos resumos da W3.4 | texto | §11 «Literal único» |
| 17 | fixtures como instrumento | 1a | §19.2 |
| 18 | rollback sem cota; rota de emergência | 1a; runbook | §15 |
| 19 | re-verificação logo depois de todo LAND do instrumento | material ADR-192 | §23, §24 |
| 20 | modo de execução declarado; morte na Fase 2; quiesce nomeando processos | runbook; 1a | §15, §4.3 |
| 21 | ensaio só-verificação contra a 0.156.1 | runbook | §18 item 9 |
| 22 | ordem com a W7 | W7 × W3 | §18, §24 |
| 23 | validade do Check de sucesso no instante do fechamento | texto | §19.5 |

## Referências

- `.claude/adr/ADR-182-codex-payload-pin-enforcement.md` (§2 `:85-128`, §3 `:130-141`, §4 `:143-164`,
  §5 `:166-184`, §Consequences `:205-224`).
- `.claude/plans/PLAN-194/debate/round-1/consensus.md` e `round-2/consensus.md`; críticas da rodada 2
  (`security-engineer.md`: MF-R2-W3-1..8, NTH 4–8; `qa-architect.md`: must-fix 10–16, NTH 4–5;
  `devops-engineer.md`: must-fix 5–10, NTH 4–6).
- `.claude/plans/PLAN-194/debate/round-3/consensus.md` (FINAL: §2 condições 1–23, §4 itens 18–32, §5
  decisões) e as críticas da rodada 3 (`security-engineer.md`: C-1..C-7, R3-SEC1/R3-SEC2;
  `qa-architect.md`: C-1..C-9; `devops-engineer.md`: condições 1–6, NTH 1–2).
- Rascunho anterior (r3), mantido INTACTO como registro: `.claude/plans/PLAN-194/debate/round-2/ADR-182-AMEND-1-draft.md`.
- `.claude/plans/PLAN-194/LEDGER.md` §W0.6 (resumo) e o relatório completo da W0.6 (fora do repositório).
- Código: `.claude/hooks/check_pair_rail.py`; `.claude/governance/codex-cli-pin-manifest.json`,
  `codex-cli-pin.txt`, `gate-scripts-manifest.txt`; `.claude/scripts/local/pair-rail-gate.sh`;
  `.claude/hooks/_lib/codex_cli_shape.py`; `.github/workflows/release.yml` passo 15;
  `PLAN-192/repass-ga/run-ga-repass.sh` e `PLAN-193/repass-ga/run-ga-repass.sh` (rota 2);
  `.claude/hooks/_lib/runtime_paths.py`; `.claude/hooks/_lib/audit_emit.py`;
  `.claude/hooks/check_canonical_edit.py` (`:115` `_CANONICAL_GUARDS`, `:232` glob de governança);
  `.claude/hooks/check_arbitration_kernel.py:88`; `.claude/scripts/env-inventory-check.py` (`:12-14`,
  `:19-20`, `:61-71`, `:75-79`, `:107`, `:164-169`); `.github/workflows/validate.yml:194-198`; `docs/CROSS-LLM-THREAT-MODEL.md` §T-8; `SBOM.md`.
- ADR-111 §2 (gatilho de 5 pp), ADR-192 (manifesto de gate scripts), ADR-001 (resolvedor de estado),
  ADR-055-AMEND-3 (precedente de breadcrumb — não se aplica), ADR-081 (estimativas em tokens/sessões).
