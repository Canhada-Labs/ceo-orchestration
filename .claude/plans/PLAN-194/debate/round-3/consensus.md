---
plan: PLAN-194
round: 3
rounds_synthesized: [round-1, round-2, round-3]
final: true
scope: "W3 (a W5c saiu PROCEED na rodada 1 e a W2 na rodada 2); este arquivo fecha o debate único das três ondas"
critics: [Critic-A, Critic-B, Critic-C]
agents_considered: [Critic-A, Critic-B, Critic-C]
verdicts: [ADJUST, ACCEPT, ACCEPT]
vetoes: "Critic-B — W3: RETIRADO, condicionado à decisão 3 do Owner ESCRITA como ramo (ii) ou ramo (i); a retirada vale no instante em que essa decisão escrita existir. Se a decisão 3 for «confiança no registro», o VETO segue LEVANTADO ⇒ ESCALATE-TO-OWNER. (W2: retirado na rodada 2, com condições; W5c: retirado na rodada 1, com condições.)"
wave_verdicts:
  W5c: "PROCEED (rodada 1)"
  W2: "PROCEED (rodada 2)"
  W3: "PROCEED (rodada 3; 3 de 3 críticos)"
round_verdict: PROCEED
design_coherent:
  W5c: true
  W2: true
  W3: true
debate_closed: true
terminal_artifact_note: "DEBATE-SCHEMA §6 pede, na rodada terminal, round-N/approved.md com a ratificação do Owner. Este consensus.md é a síntese ANTERIOR à ratificação; o approved.md nasce quando o Owner escrever as decisões, a 3 acima de todas (ver §8)."
w3_execution_conditions: 23
consensus_adjustments: 32
decisions_revised_in_plan: "pendente — esta síntese NÃO edita o plano nem o AMEND-1; o CEO aplica a lista «Plan adjustments», e o rail (V2) de cada pacote confere. Não há nova rodada."
synthesized_at: 2026-10-02T04:17:00Z
synthesized_by: CEO (síntese delegada, S361)
synthesized_from: "texto anonimizado das três críticas da rodada 3 (cópias fora do repositório, no scratchpad da sessão); consensos das rodadas 1 e 2; ADR-182-AMEND-1 revisado (r3, em round-2/); PLAN-194 no commit 092377af. Limitações declaradas: o mapa de anonimização foi lido só para o estado do VETO, mas também lista os arquétipos; o rascunho e o plano citam achados por arquétipo. Cada decisão abaixo se apoia em fato conferido no disco, não em quem o afirmou."
---

# Consenso FINAL — PLAN-194, debate L3 único, rodada 3 (W3) e fechamento (W2, W3, W5c)

> **O que este veredito certifica.** `design-coherent` (DEBATE-SCHEMA §13.1) certifica só a coerência
> interna do desenho entre perspectivas forçadas do MESMO modelo. Não autoriza publicar. Cada pacote das
> três ondas segue pela cascata V0 → V1 → V2 (rail do Codex, a checagem externa da verdade) → V3 (GPG do
> Owner).
>
> **Repositório público.** Só classes de defeito e ids de lane; nenhum caminho da pasta privada do Owner;
> nenhuma receita de contorno de guarda.

## 0. Verificação das afirmações da rodada 3

Conferido no disco, no HEAD `092377af` (o arquivo do plano é idêntico ao do commit):

| afirmação | onde | resultado |
|---|---|---|
| As fontes do verificador são editáveis pelo agente (oráculo 0) | `check_canonical_edit.py --is-canonical` nos quatro nomes propostos (o `.py`, o `codex-auto-pin/verify-sigstore.js`, o `package.json` e o `package-lock.json`) ⇒ `0` nos quatro | confere |
| Nenhum hook lê o manifesto ADR-192 em execução | `grep gate-scripts-manifest .claude/hooks/` ⇒ nada. Quem o lê são `release.yml`, `npm-publish.yml`, `smoke-install.yml` e `ownership-nightly.yml` | confere: a lista permitida do H-07 só existe a partir do pacote 1b, e ela compara shas DECLARADOS pela linha, não os bytes que a escreveram |
| A CLI toma `argv[0]` como lançador | `check_pair_rail.py:2513` (`launcher = argv[0] if argv else None`) | confere ⇒ a flag precisa vir DEPOIS do caminho; o Check do plano (`:1182`) já a põe depois |
| O plano diverge do AMEND-1 no pacote 1a | plano `:1074-1079` diz «6 paths» (só o lockfile, auxiliar `codex-auto-pin-verify.js`), com a mensagem do Gate 4 no 1b; o AMEND-1 §24 diz 8 paths no ramo (ii): `package.json` + `package-lock.json`, arquivo de fixtures da camada 2, manifesto ADR-192, auxiliar `codex-auto-pin/verify-sigstore.js`, Gate 4 no pacote 2 | confere |
| Os Checks da W3.3 e da W3.4 usam `-k`, e o AMEND-1 §19.4 pede node id de classe | plano `:1119`, `:1148` | confere ⇒ a camada 2 pode passar como SKIP verde |
| Mapa de colisões sem o hospedeiro da guarda do registro | a linha da guarda de Bash (`:263`) diz «nenhuma onda deste plano toca esses arquivos»; a do `.claude/settings.json` (`:243`) não cita a W3 | confere |
| `check_canonical_edit.py` é kernel | `check_arbitration_kernel.py:88` | confere ⇒ pôr as fontes do verificador em `_CANONICAL_GUARDS` (`:115`) é cerimônia de kernel |
| O glob de sentinela é `architect/`, não `debate/` | `check_canonical_edit.py:1005` (`PLAN-*/architect/round-*/approved.md`) | confere ⇒ um `debate/round-3/approved.md` NÃO é sentinela de edição canônica (§8) |

## 1. Veredito FINAL por onda (debate inteiro)

| onda | rodada | veredito | VETO (Critic-B) | condições |
|---|---|---|---|---|
| **W5c** | 1 | **PROCEED** (`design-coherent`) | RETIRADO com condições | MF-W5c-1 e MF-W5c-2 na emenda 4 do ADR-149; must-fix da onda (consenso r1, ajustes 35 a 40) |
| **W2** | 2 | **PROCEED** (`design-coherent`) | RETIRADO com condições | MF-R2-W2-1..4 no ADR-055-AMEND-4 e no plano (aplicados em `092377af`); a W2.0 (cura da condição 67) landa antes do SIGN da W2; lista (a) do consenso r2 |
| **W3** | 3 | **PROCEED** (`design-coherent`), 3 de 3 críticos | **RETIRADO, condicionado à decisão 3 do Owner ESCRITA como ramo (ii) ou ramo (i)** | as condições de execução da §2. «Confiança no registro» ⇒ VETO LEVANTADO ⇒ **ESCALATE-TO-OWNER**. Nenhum P0; nenhuma afirmação FALSA no plano |

**Veredito da rodada e do debate: PROCEED.** O debate único fecha `design-coherent` para as três ondas.
Os pacotes da W3 só começam depois que a decisão 3 estiver ESCRITA, porque é ela que libera o VETO.

A rodada 3 não precisa do Red Team de §12.3: a convergência acontece na rodada N = 3 > 2.

**A divergência que restou, resolvida pela regra** (o portador de VETO prevalece no domínio dele, salvo
disco que o refute): o I8 do rascunho promete mais do que o H-07 entrega.

- O Critic-A a classifica como sobre-afirmação, não P0. O Critic-B, portador do VETO, faz a mesma
  leitura e a põe como condição de execução (C-4 dele).
- O disco confirma o mecanismo da via: as fontes têm oráculo 0, e nenhum hook lê o ADR-192.
- **Decisão:** guarda das fontes do verificador + texto corrigido + resíduo nomeado (condições 6 e 7).
  Não é NO-GO.

## 2. Condições de execução da W3 (consolidadas e deduplicadas)

Cada condição traz o pacote onde entra:

- **1a** — verificador;
- **1b** — núcleo + AMEND-1 + guarda, se couber;
- **1c** — guarda, PRIMEIRO da fila, se o 1b passar de 8 paths (I8);
- **2** — argv, chamadores livres e a mensagem do Gate 4;
- **kernel** — `audit_emit.py`;
- **W7** — kit do corte;
- **runbook** — operação;
- **texto** — plano ou AMEND-1, aplicado pelo CEO.

Uma condição não cumprida reprova o SIGN do pacote correspondente, não o debate. Quem confere é o rail
(V2).

**Antes de qualquer pacote**

1. **[Owner; AMEND-1 §22 e plano] Decisão 3 ESCRITA como ramo (ii) ou ramo (i).** É ELA que retira o
   VETO. «Confiança no registro» ⇒ VETO levantado ⇒ ESCALATE-TO-OWNER. Recusar o `node` devolve o plano
   B (re-pin manual). Fontes: B C-1; A e C concordam.
2. **[Owner/CEO; AMEND-1 §22] Decisões 4, 5 e 6 escritas no AMEND-1 antes do pacote de ADR (1b).** Fonte:
   B C-7.
3. **[texto; CEO, antes de abrir o 1b] Plano reconciliado com o AMEND-1, que prevalece** (A C-5, B C-5,
   C 1):
   - auxiliar `.claude/scripts/codex-auto-pin/verify-sigstore.js`;
   - ramo (ii): `package.json` + `package-lock.json` na mesma pasta;
   - o arquivo único de fixtures da camada 2;
   - o pacote 1a com **8 paths no ramo (ii)** (verificador `.py`, auxiliar `.js`, `package.json`,
     `package-lock.json`, teste do verificador, fixtures, `SBOM.md` e
     `.claude/governance/gate-scripts-manifest.txt`) e **7 no ramo (i)**;
   - a mensagem do Gate 4 no **pacote 2**;
   - o 1c PRIMEIRO da fila se o 1b passar de 8 paths.
4. **[texto; CEO, antes do 1b/1c] Hospedeiro da guarda do registro escolhido, com as linhas no mapa de
   colisões** (C 2):
   - `permissions.deny` do `.claude/settings.json` em série W6 → W5c → W3 (1c) / W3 do PLAN-195;
   - `check_bash_safety.py` em série com as partes A e B do PLAN-195, re-derivado sobre elas. Se a guarda
     de Bash precisar dele, a W3.6 entra no caminho crítico do PLAN-195. Preferência: outro hospedeiro
     enquanto a parte B estiver em voo;
   - `check_canonical_edit.py` (kernel) se as fontes do verificador forem para `_CANONICAL_GUARDS`
     (condição 6);
   - a linha da guarda de Bash (`:263`) deixa de dizer «nenhuma onda deste plano toca esses arquivos»,
     se for o caso.
5. **[texto; CEO, antes do SIGN do 1b] A lacuna de guarda da família do log de auditoria** (log, chave,
   sal e sidecars) ganha item com DONO e posição no plano, com a pergunta respondida no disco: existe
   guarda? com que controle? Não bloqueia a W3; bloqueia ficar sem dono. Domínio do VETO (ADR-052).
   Fonte: B C-6.

**Pacote 1b / 1c (núcleo e guardas)**

6. **[1c, ou 1b se couber] Guarda das FONTES do verificador** (A C-1(a), B C-4):
   - o `.py`, o auxiliar `.js`, o `package.json` e o lockfile ficam protegidos contra Edit, Write e
     escrita direta por Bash do PRÓPRIO agente;
   - o mecanismo é `_CANONICAL_GUARDS` (kernel; a fonte passa a oráculo 1 e a edição pede sentinela de
     cerimônia) ou as células W-01..W-04 estendidas a esses caminhos;
   - controle positivo no formato EXATO do agente ⇒ BLOCK;
   - a guarda landa ANTES do 1º LAND do 1a.
7. **[1b; texto do AMEND-1 I8/H-07/R-5] I8 e H-07 reescritos para dizer o que o mecanismo prova**
   (A C-1(b)(c), B C-4):
   - o hook confia em linhas que **DECLARAM** shas listados no manifesto ADR-192 e não prova quais bytes as
     escreveram;
   - um teste DOCUMENTA o resíduo, no molde do H-13: um verificador sintético editado grava uma linha com
     `verifier_sha256` forjado igual ao do manifesto, e o núcleo concede confiança;
   - a via fica NOMEADA no R-5 («código que calcula o caminho» / «agente que edita o verificador e o
     executa»);
   - se a guarda da condição 6 não couber, esse resíduo vai também ao material assinado. Nunca fica
     silencioso.
8. **[livre — `/ceo-boot`, `ceo-boot.py`, mapa × L2] Evidência em repouso.** O check do boot compara o sha
   EM DISCO do verificador, do auxiliar e do lockfile com o manifesto ADR-192, sem custo no hook. Fonte: A
   C-1(d).
9. **[1b] CLI.** Os Checks de sucesso e da W3.6 afirmam `status == "verified_auto"` **E**
   `pin_source == "registry"`. Um teste fixa a forma do argv: a flag DEPOIS do caminho do lançador,
   porque `_verify_pin_cli` toma `argv[0]` como lançador (`check_pair_rail.py:2513`). Fonte: A C-7.

**Pacote 1a (verificador): medidas na abertura, pré-condição do SIGN do 1a**

10. **[1a] S-13/S-14 medidos na camada 2, na bateria do LAND do 1a, com SKIP = falha, ANTES do SIGN do
    1a** (A C-9, B C-2):
    - com a MESMA política: S-13 (id do repositório errado) e S-14 (id do dono errado) ⇒ REJECTED; S-02 e
      S-10 ⇒ VERIFIED;
    - se `certificateOIDs` falhar, a ordem de fallback é: (a) as extensões `.1.15` e `.1.17` do
      certificado-folha JÁ VERIFICADO, lidas pelo parser X.509 da própria biblioteca sigstore, sem ASN.1 à
      mão; (b) só por último os ids do statement, DECLARADOS no material assinado como proteção REDUZIDA
      («repositório recriado com o mesmo nome passa»);
    - o texto do AMEND-1 §6 é corrigido nesses termos;
    - o resultado vai ao LEDGER, com substrato.
11. **[1a e 1b] Guarda de rede do `node` filho, com controle positivo VERMELHO** (o fetch do filho falha)
    ANTES de qualquer resultado da camada 2 ou de célula «sem rede» contar (A C-9, B C-3):
    - se as variáveis de proxy não prenderem o filho: TUF só de cache sobre a raiz fixada nos testes, ou
      isolamento de rede do processo, com o MESMO controle positivo;
    - resultado e mecanismo no LEDGER.
12. **[1a; e W7 para o K-06] P-04 de produção com as opções EXPLÍCITAS de proxy e o modo offline do npm**
    (W0.6 V-N2/V-N4), não só o ambiente, porque o `env -i` remove as variáveis de proxy. Controle positivo:
    com o cache do staging ESVAZIADO e o proxy morto explícito, a Fase 2 FALHA. Mesmo controle no K-06 do
    kit. Fontes: A C-4, B C-3.
13. **[1a; e Checks do plano] Camada de criptografia em MODO OBRIGATÓRIO** (A C-2, C 6):
    - os testes `crypto_real` FALHAM em vez de pular quando a variável de modo obrigatório estiver ligada;
    - a bateria do LAND, o Check de SUCESSO da W3 e o Check da W3.4 do plano a ligam (SKIP = falha);
    - uma execução de CI sem `node` só pode rodar sem o modo com o SKIP CONTADO e IMPRESSO, declarado;
    - controle positivo: `node` fora do PATH com o modo ligado ⇒ vermelho;
    - a variável nova entra no inventário de ambiente (`env-inventory`) no mesmo pacote.
14. **[texto; Checks do plano] Os Checks da W3.3 e da W3.4 usam node ids de CLASSE** (AMEND-1 §19.4), nunca
    `-k`. Um texto só, o do AMEND-1. O teste-censo também afirma que cada teste mapeado está DENTRO da
    seleção do Check. Fontes: A C-3, C 6.
15. **[1a] Células que faltam no censo** (A C-6):
    - B-01: linha de aceitação sem evento ⇒ ALARME;
    - B-02: evento de quarentena sem linha ⇒ ALARME;
    - B-03: evento sem linha ⇒ informativo;
    - B-04: `--check-installed` com membro alterado ⇒ divergência relatada;
    - A-26: duas execuções concorrentes do verificador ⇒ uma recusa, e a cadeia `seq`/`prev_sha256` fica
      íntegra;
    - fronteiras com relógio INJETADO: 47:59:59 ⇒ não candidata; 48:00:00 ⇒ candidata; nova tentativa do
      canário antes de 10 min ⇒ recusa; 4.ª execução na semana ⇒ recusa;
    - o timeout do auxiliar (F-06) como constante canônica com teste.
16. **[texto] Os resumos da W3.4 no plano usam os literais do AMEND-1** (`verified_auto` nas células do
    registro). Fonte: A C-8.
17. **[1a] Fixtures como instrumento.** Sha e data de captura de cada bundle e da raiz TUF ao lado do
    arquivo de fixtures, e um teste que acusa fixture trocada. Fonte: A NTH 2, adotado.

**Operação (AMEND-1 §15, runbook, material de cerimônia)**

18. **[1a; AMEND-1 §15; runbook] Rollback sem depender de cota** (C 3):
    - rollback para um sha JÁ registrado, ou para a versão do manifesto, re-verifica os bytes (V-0..V-9,
      sonda local incluída) e **PULA o canário**, que já passou para aquele sha. O canário é vivacidade,
      não segurança;
    - o runbook nomeia a rota de EMERGÊNCIA: instalar a versão do MANIFESTO (H-01), sem canário nem cota.
      Instalação crua ⇒ irmãos sem conferência (R-19) até a re-promoção ou o `--check-installed`.
19. **[material de cerimônia ADR-192 de todo LAND do verificador, do auxiliar ou do lockfile] Re-verificação
    logo depois do LAND** (C 4):
    - a versão instalada é re-verificada pelo verificador NOVO, ou a versão do manifesto é reinstalada;
    - isso fica declarado no material assinado. Sem isso, o H-07 tira a confiança da versão auto-pinada e
      o rail bloqueia todas as escritas L3+ depois do LAND.
20. **[runbook do verificador; 1a] Modo de execução declarado** (C 5; C NTH 1):
    - terminal do Owner em primeiro plano, ou segundo plano com timeout EXPLÍCITO ≥ o pior caso
      pré-registrado (downloads + `npm ci` + canário + 1 nova tentativa de ≥ 10 min). Nunca o padrão de
      30 min do CC;
    - morte no meio da Fase 2 ⇒ o hook BLOQUEIA pelo `bin/codex` (P-01) ⇒ rota de emergência da
      condição 18;
    - a recusa do quiesce nomeia o PID e o caminho do executável de cada processo (o daemon `app-server` e
      o app do Codex são os candidatos), e o procedimento lista o que parar.
21. **[runbook; antes do 1º `--promote` real] Ensaio em modo só-verificação contra a 0.156.1 do manifesto**,
    sem gravar linha. Prova a Fase 1 inteira numa versão cujo sha já conhecemos (`0196e89f…`). O canário
    obedece ao freio Q2 ou é pulado nesse modo. A `node` v26.3.0 da W0.6 vai ao LEDGER como linha de base
    da constante de versão mínima. Fontes: A NTH 3, B NTH 4, adotados.

**Sequência com o corte**

22. **[W7 × W3] Ordem** (C NTH 2, adotado):
    - o 1b (pacote de ADR) landa ANTES de começar a derivação do kit da W7, porque nenhum pacote de ADR
      fica em voo durante o kit; senão a W3.6 escorrega para depois do GA;
    - a inversão da rota 2 pode landar como a PRIMEIRA peça da W7.1 (derivadores com oráculo 0, com K-01
      e K-02), para a W3.6 não esperar o kit inteiro.
23. **[texto] O Check de sucesso da W3 vale para o instante do fechamento da W3.** Se uma cerimônia futura
    puser no manifesto a mesma versão instalada, ele volta a dar `manifest`, e isso é esperado. Fonte: A NTH
    4.

## 3. Consensus findings da rodada 3 (2+ críticos)

1. **R3-C1 — A W3 está `design-coherent`.** Os três críticos (PROCEED). Nenhum P0; nenhuma afirmação FALSA
   no plano. As duas afirmações falsas da r2 no rascunho («stdlib-only» e «MESMO host») estão corrigidas e
   sinalizadas.
2. **R3-C2 — O ESCRITOR do registro é editável pelo agente, e o I8 sobre-afirma.** Critic-A (R-QA3-1) e
   Critic-B (R3-SEC1). MEDIUM. → condições 6, 7 e 8.
3. **R3-C3 — A camada 2 passa como SKIP verde nos Checks do plano.** Critic-A (R-QA3-2) e Critic-C
   (R3-DO5). MEDIUM. → condições 13 e 14.
4. **R3-C4 — Plano e AMEND-1 divergem** nos paths, nomes e contagem do 1a, no pacote da mensagem do Gate 4
   e em node id × `-k`. Os três. LOW. → condição 3.
5. **R3-C5 — S-13/S-14 e a guarda de rede do `node` são medidos na abertura**, como pré-condição. Critic-A
   e Critic-B. → condições 10 e 11.
6. **R3-C6 — A prova de «zero busca» da promoção precisa de opção explícita e controle positivo.** Critic-A
   (R-QA3-4) e Critic-B (C-3). → condição 12.
7. **R3-C7 — «Confiança no registro» é rota de ESCALATE, não ramo.** Os três. → condição 1, decisão 3.

**Mantidos de um só crítico:**

- **Critic-B:** a ordem honesta do fallback dos ids (domínio do VETO) e a lacuna da família do log;
- **Critic-C:** o rollback que pula o canário, a re-verificação depois do LAND do verificador, o runbook
  com timeout, o hospedeiro da guarda e a sequência com a W7;
- **Critic-A:** o `status` na CLI e a forma do argv, as células do censo, os literais e as fixtures como
  instrumento.

**Adiados (follow-up):**

- job de CI com `node` rodando a camada 2 (Critic-A NTH 1, Critic-B NTH 1; já citado no AMEND-1 §19.2);
- H-07 aceitando shas HISTÓRICOS do verificador (Critic-B NTH 2): só se o custo operacional aparecer, já
  que hoje «trocar o verificador ⇒ re-verificar» é a direção segura;
- o kit chamando o verificador em modo só-verificação sobre a versão do manifesto (Critic-C NTH 3, fecha o
  R-17);
- o download duplo da Fase 1 (Critic-C NTH 4).

O `-k "probe or canary"` que o Critic-A aceitaria na W3.3 cede ao «um texto só» do AMEND-1 (condição 14).

## 4. Plan adjustments

O CEO aplica estas edições no PLAN-194 e no AMEND-1. Não é nova rodada: o rail de cada pacote confere.

**PLAN-194**

1. *Topo, Approach item 4 e «Cláusula de bloqueio»:* o debate único está FECHADO (W5c na r1, W2 na r2, W3 na r3), e a W3 está liberada do portão do debate. Os pacotes da W3 começam só depois da decisão 3 ESCRITA (o VETO); «confiança no registro» ⇒ ESCALATE.
2. *W3, parágrafo «BLOQUEADA»:* reescrever como «PROCEED na rodada 3, condicionado à decisão 3», remetendo às condições 1 a 23 deste consenso.
3. *W3, «Paths»:* os nomes e a contagem do AMEND-1 (condição 3); o 1c com a guarda do registro e a das fontes do verificador; a mensagem do Gate 4 no pacote 2.
4. *Mapa de colisões:* as linhas dos hospedeiros da guarda (condição 4) e a correção da linha da guarda de Bash (`:263`), se for o caso.
5. *«Paths × oráculo»:* `.claude/scripts/codex-auto-pin/verify-sigstore.js`, `.claude/scripts/codex-auto-pin/package.json` e `.claude/scripts/codex-auto-pin/package-lock.json` (oráculo 0 medido na r3); o arquivo de fixtures (nome a fixar); `check_canonical_edit.py` (1, kernel; condicional à condição 6).
6. *W3.3 e W3.4:* Checks por node id de CLASSE, com a variável de modo obrigatório ligada no da W3.4; os resumos com `verified_auto` (condições 13, 14 e 16).
7. *«Success criteria», braço da W3, e o Check da W3.6:* `status == "verified_auto"` e `pin_source == "registry"`, flag depois do caminho, modo obrigatório da camada 2 e a nota de validade do instante (condições 9, 13 e 23).
8. *W3.6:* novas pré-condições — guarda das fontes landada (6); S-13/S-14 e guarda de rede do `node` medidos e no LEDGER (10 e 11); runbook com timeout e rota de emergência (18 e 20); ensaio só-verificação contra a 0.156.1 (21).
9. *W7:* a sequência da condição 22 e o controle positivo do K-06 (condição 12).
10. *W3, «Declarar no material assinado»:* o resíduo do I8 (shas declarados), a proteção reduzida do fallback (b) se ele for usado, a re-verificação depois de cerimônia do verificador, o rollback sem canário com a rota de emergência e o modo de execução do runbook.
11. *Item novo com dono (transversal):* a lacuna de guarda da família do log de auditoria (condição 5), em «Unidades que ganharam dono» ou na W6, antes do SIGN do 1b.
12. *«Decisões pendentes do Owner»:* a forma final da §6 deste consenso, dizendo que a 3 é a que libera o VETO da W3.
13. *«Riscos»:* risco 4 com o resíduo do I8 e a dependência do instrumento (H-07 revoga a confiança a cada cerimônia do verificador ⇒ condição 19); a dependência de cota no rollback, já resolvida pela condição 18.
14. *«Orçamento»:* as condições cabem nos 1,6–2,8 M já orçados para a W3 (estimativas dos críticos: 50k a 220k); a cerimônia de kernel da condição 6, se for por `_CANONICAL_GUARDS`, é custo marginal sobre o 1b ou o 1c.
15. *LEDGER (seção da W3 ao abrir o 1a):* `node` v26.3.0 como linha de base; resultados de S-13/S-14 e da guarda de rede do `node`.
16. *«Session history»:* S361, rodada 3 — debate fechado; `approved.md` pendente da ratificação do Owner (§8).
17. *Inventário de ambiente:* a variável de modo obrigatório da camada 2 declarada no mesmo pacote (1a).

**ADR-182-AMEND-1 (o rascunho r3 vira o texto do pacote de ADR)**

18. *Frontmatter e §0:* status «`design-coherent` na rodada 3»; `debate_record` com o consenso r3; `decided_by` pendente da decisão 3.
19. *§3 I8 e §4.1 (H-07):* «linhas que DECLARAM shas listados no ADR-192»; resíduo nomeado (condição 7).
20. *§9.W e §10.4:* as células da guarda estendidas às fontes do verificador, com controle positivo; ordem 1c primeiro (condição 6).
21. *§6:* a ordem de fallback dos ids imutáveis e S-13/S-14 como pré-condição do SIGN do 1a (condição 10).
22. *§19.2:* o modo obrigatório; SKIP = falha na bateria e nos Checks do plano; no CI sem `node`, SKIP contado e impresso; controle positivo (condição 13).
23. *§19.3:* controle positivo VERMELHO antes de qualquer resultado contar; mecanismos de troca (condição 11).
24. *§4.3, §9.P e §9.K:* P-04 e K-06 com opções explícitas de proxy, modo offline e controle positivo de cache vazio (condição 12).
25. *§9 e §19.4:* as células B-01..B-04, A-26, as fronteiras de relógio e a constante do F-06; o censo afirma que cada teste está na seleção do Check (condições 14 e 15).
26. *§15:* rollback para sha registrado ou versão do manifesto PULA o canário; rota de emergência; modo de execução e morte no meio da Fase 2 (condições 18 e 20).
27. *§23 e §24:* re-verificação depois de todo LAND do instrumento, como parte do material da cerimônia ADR-192 (19); 1a com 8 paths no ramo (ii) e 7 no ramo (i); Gate 4 no pacote 2; conteúdo do 1c.
28. *§11 e §19.5:* a CLI afirma `status` e `pin_source`; teste da forma do argv (condição 9).
29. *§19.2:* fixtures com sha e data e o teste de fixture trocada (condição 17).
30. *§21:* o R-5 com a via nomeada; a lacuna da família do log como follow-up COM DONO no plano (condição 5).
31. *§22:* as decisões escritas assim que saírem; a decisão 3 como condição da retirada do VETO.
32. *§18:* a ordem com a W7 (condição 22) e o ensaio só-verificação (condição 21).

## 5. Decisões do Owner (forma final)

1. **Vaga da cura da condição 67 (W2.0).** É o único pré-requisito do Owner para o SIGN da W2, que saiu
   PROCEED na rodada 2. **Recomendação:** pacote canônico PRÓPRIO, landado ANTES do SIGN da W2, como 1.º
   pacote na vaga da W2 ou na primeira vaga que abrir antes. A aposentadoria da condição 67 vai no
   `CHANGELOG.md` do corte.
2. **Pré-condição e RECORRÊNCIA da W2.6.** **Recomendação:**
   - trocar «todas as sessões do Claude fechadas» por «todas as sessões DESTE projeto fechadas»;
   - predicado do AMEND-4: PID vivo ⇒ pula a família; mtime < 10 min ⇒ recusa a execução; spool ativo ou
     `.draining.*` com PID vivo ⇒ recusa a execução;
   - aceitar a W2.6 como manutenção recorrente, a cada ~2–4 semanas de uso intenso, quando o `/ceo-boot`
     acusar ≥ 100 mil travas;
   - rodar a 1.ª já.
   Mais de uma W2.6 por mês ⇒ gatilho da T2.
3. **Empacotamento do verificador de assinatura da W3 — É ESTA DECISÃO QUE LIBERA O VETO DA W3.**
   - **(ii)** `sigstore` em versão exata, lockfile de integridade de toda a árvore sob o manifesto ADR-192,
     `npm ci --ignore-scripts` em staging novo: código de terceiro governado pelo repositório.
   - **(i)** o módulo interno do npm, com lista canônica de versões e shas e recusa fora dela: muda num
     upgrade do npm do Homebrew; a falha é fail-closed (perde vivacidade, não segurança).

   **Recomendação: (ii)**, preferida pelo portador do VETO e por outro crítico. A retirada do VETO vale no
   instante em que a decisão estiver ESCRITA. «Confiança no registro» ⇒ VETO segue LEVANTADO ⇒
   ESCALATE-TO-OWNER por múltipla escolha. Recusar o `node` ⇒ plano B (re-pin manual).
4. **Sentinela de qualidade.** **Recomendação:** (ii) a W3 landa SEM sentinela, declarada (R-2). O gatilho
   do ADR-111 §2 fica preservado como NÃO AVALIÁVEL até haver corpus com sha e linha de base. Os três
   críticos aceitam.
5. **Modelo e esforço fixos no argv do rail.** **Recomendação:** `gpt-6-astra` + `xhigh`, condicionado ao
   re-teste da Q11. O par e as flags (`--ignore-user-config` incluída) precisam existir também na 0.156.1,
   que o corte usa. **Adopters:** recomendação de opt-in, mantendo o padrão da conta, porque um id fixo que
   a conta deles não sirva rebaixa o rail a advisory.
6. **Evidência da aceitação automática.** **Recomendação:** evento na cadeia HMAC (§12 do AMEND-1). «Só no
   registro» apenas por decisão ESCRITA, com o resíduo R-3.

**Para ciência, sem decisão:**

- carência de 48 h, então o pin anda ~2 dias atrás da `latest`;
- a W3 tem 1,6–2,8 M tokens em 3–4 sessões (1c/1b, 1a, 2 e kernel), e a W3.6 depende deles e da rota 2
  invertida, que pode ser a 1.ª peça da W7.1;
- cada promoção é janela de manutenção;
- rollback exige rede (R-16), mas não cota (condição 18);
- toda cerimônia do verificador exige re-verificação logo depois (condição 19);
- a W2 e a W5c seguem pela fila.

## 6. Arco das três rodadas (insumo do `approved.md`)

- **Rodada 1:**
  - 21 consensus findings e 48 ajustes;
  - W5c PROCEED; W2 e W3 RUN-ANOTHER-ROUND (VETO levantado nas duas).
  - Fatos que mudaram o plano: `truly_lost` morto; reconciliação sem chamador; condição 67 já assinada;
    rota 2 do re-pass (a W3.6 não precisa esperar o corte); carência de 48 h com a regra de escolha da
    estável elegível.
- **Rodada 2:**
  - 13 consensus findings e 52 ajustes;
  - W2 PROCEED (VETO retirado com condições); W3 RUN-ANOTHER-ROUND.
  - Fatos: a W0.6 (o comando do npm não serve; o sigstore com política serve); a decisão sai só depois do
    `atexit` (medido); a âncora no import nasce tarde nos guards; a rota 2 executava antes de verificar.
- **Rodada 3:**
  - 7 consensus findings e 23 condições de execução;
  - W3 PROCEED 3/3, VETO retirado condicionado à decisão 3.
  - Fatos: o ESCRITOR do registro é editável (I8 sobre-afirmava); a camada 2 podia passar como SKIP; os
    paths do 1a estavam subcontados.

**Lições para o processo de debate** (DEBATE-SCHEMA §6):

1. **Medir antes de debater o mecanismo.** A W0.6 tornou obsoleta metade do rascunho r2. A medição que
   decide o desenho entra ANTES da rodada que o julga.
2. **Divergência plano × rascunho voltou em todas as rodadas** (W2 na r2, W3 na r3). Cure a classe: a regra
   «o rascunho do ADR prevalece; o plano cita, não repete» fica escrita na abertura de todo debate com
   rascunho.
3. **Checks verdes por construção** (`-k` casando o módulo, SKIP verde, marcador literal no `awk`, CLI sem
   flag) apareceram nas três rodadas. Um lint de Checks do plano, com seletor ⊄ nome do módulo, SKIP = falha
   onde a prova conta e afirmação no código de saída, merece item próprio.
4. **Anonimização imperfeita:** o mapa, os rascunhos e o plano expõem arquétipos ao sintetizador. Ou o
   sintetizador recebe só o estado do VETO, ou a limitação continua declarada.
5. **«Autodeclaração do instrumento»** (Critic-B, Unseen 1) é classe transversal: toda identidade de
   instrumento gravada pelo próprio instrumento só vale com o instrumento protegido contra adulteração na
   sessão.

## 7. Round verdict

**PROCEED** — rodada 3 e debate inteiro.

- **W5c:** PROCEED (r1).
- **W2:** PROCEED (r2).
- **W3:** PROCEED (r3), com o VETO retirado sob a condição 1, a decisão 3 ESCRITA (ii)/(i).

Se a decisão 3 for «confiança no registro», a W3 passa a ESCALATE-TO-OWNER, e o PROCEED da W3 deixa de
valer.

Sem nova rodada. As condições de execução são conferidas no rail (V2) de cada pacote e são pré-condição do
SIGN do pacote correspondente.

## 8. Artefato terminal (DEBATE-SCHEMA §6)

O DEBATE-SCHEMA §6 diz que a rodada terminal grava `round-N/approved.md` **no lugar de** `consensus.md`.
O `approved.md` resume o arco, **registra a ratificação do Owner** e aponta as seções ajustadas do plano.
O formato tem `rounds_completed: 3` e `final_verdict`, com as seções «3-round arc summary», «Final plan
deltas» e «Lessons for the debate process itself».

Este arquivo fica como `consensus.md` porque **a ratificação do Owner ainda não existe**. Falta, para o
`approved.md`:

1. **a decisão 3 ESCRITA, ramo (ii) ou (i)** — sem ela, o veredito final da W3 não se firma, porque o VETO
   só sai com ela;
2. as decisões 1, 2, 4, 5 e 6 escritas (ou explicitamente adiadas pelo Owner);
3. a ratificação do Owner do veredito final das três ondas;
4. os ajustes 1–32 aplicados, para que «Final plan deltas» aponte texto que existe.

Depois disso, o CEO grava `.claude/plans/PLAN-194/debate/round-3/approved.md` no formato do §6, usando a
§6 deste arquivo como arco e lições, e mantém este `consensus.md` como registro.

**Cuidado de caminho:** este plano usa o layout legado `debate/`, aceito pelo §3. O glob de sentinela do
guard canônico é `PLAN-*/architect/round-*/approved.md` (`check_canonical_edit.py:1005`). Um
`debate/round-3/approved.md` NÃO é sentinela de edição canônica. Criar o arquivo sob `architect/` o
tornaria sentinela, e não se deve fazer isso por conveniência. A assinatura GPG do `approved.md` (prática
dos planos PLAN-100+) fica a critério do Owner; um `.asc` destacado ao lado é suficiente.
