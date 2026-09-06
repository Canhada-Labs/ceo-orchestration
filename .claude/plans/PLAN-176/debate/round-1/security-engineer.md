---
round: 1
archetype: Principal Security Engineer
skill: security-and-auth
agent_persona: (crítico — fronteiras de confiança, autenticação de gates, supply chain)
generated_at: 2026-09-06T04:10:00Z
---

## Verdict

**ADJUST** — 5 itens BLOQUEANTES.

## Summary (≤ 3 bullets)

- O split T/P **não** preserva a cerimônia por construção: a camada T é o
  arquivo sentinel-gated, mas a ordem de precedência publicada a coloca em
  ÚLTIMO lugar (`caller > env > preference > default do schema`). Um env var
  e um arquivo sem sentinel vencem o material Owner-signed.
- O caminho da rede é montado sobre um arquivo que declara, no próprio
  cabeçalho, ser **no-network e Owner-run** — e que **não é canônico**
  (`--is-canonical` = rc 2). O allowlist de hosts que sustenta a garantia de
  egress moraria num arquivo editável sem cerimônia.
- O ADR que o plano declara como autoridade (**ADR-149 Amendment 2**) **já
  existe com outro conteúdo**, landado na S338. O número está tomado.

## Risks

**R-SEC1 — P1 — A precedência inverte o split: a camada sentinel-gated é a
mais fraca das quatro.**
`PLAN-176-model-currency-refresh.md:44-45` fixa
«Precedência: caller > env > preference > default do schema». O schema vive
em `.claude/governance/models-registry.json`, que é o único dos dois arquivos
protegido — confirmado: `.claude/hooks/check_canonical_edit.py:235` guarda
`.claude/governance/*.json`, e a lista está em `_KERNEL_PATHS`
(`check_canonical_edit.py:229-231`), logo estendê-la exige
`CEO_KERNEL_OVERRIDE` além do sentinel. Isso significa que o material com a
proteção mais cara é o *fallback*, e três superfícies sem cerimônia
(argumento do caller, variável de ambiente, PR na camada P) o sobrescrevem.
Isso contradiz `:32-36`, que descreve a camada T como «id concreto
Owner-signed; o sistema AVISA … nunca troca sozinho». As duas seções não
podem estar ambas certas.
*Mitigação:* T não é default, é **teto**. A resolução correta é
`clamp(caller|env|preference, permitido_por_T)`: para papéis VETO/pin, T
vence e as camadas acima só escolhem DENTRO do conjunto que T autoriza;
fora dele = fail-closed nomeado + evento. Escreva a precedência como duas
operações (seleção × validação), não como uma lista linear.

**R-SEC2 — P1 — `env` como camada de override é uma superfície de sequestro
já modelada por este repo, e o plano a promove a design.**
`.claude/hooks/_lib/audit_emit.py:765` já carrega a ação
`env_var_hijack_blocked`, com o comentário explícito de que o NOME da
variável e o VALOR nunca são persistidos porque «the value can be a
path/preload payload or a smuggled secret». O PLAN-176 coloca `env` ACIMA de
`preference` sem nomear uma única variável, sem allowlist e sem evento. Pior:
o «teste-mestre» de `:49-50` («injetar `claude-opus-6` fake no registry»)
exige, na prática, apontar o resolver para um registry alternativo — o que
implica um carrier de PATH por env. Um carrier de path para o arquivo de
confiança é confusão de caminho: quem controla o env controla a camada T sem
tocar em nenhum byte sentinel-gated. É a mesma classe que a S321 fechou com
`WHOLE_DIR_OVERRIDE_CARRIERS` (CLAUDE.md §5, cura `965fb13`).
*Mitigação:* (a) o conjunto de env vars aceitas é FECHADO e derivado do
schema, não aberto; (b) nenhuma env var pode apontar o PATH do registry T —
o teste-mestre roda por injeção de DEPENDÊNCIA no processo de teste (seam de
função), nunca por variável de ambiente; (c) todo override por env emite
evento com classe fechada.

**R-SEC3 — P1 — W1 é construída sobre um arquivo que declara ser no-network e
Owner-run, e que não é canônico.**
`PLAN-176-model-currency-refresh.md:66-69` diz que o plano «APENAS estende
`check-substrate-watch.py` com o probe upstream faltante». Em disco,
`.claude/scripts/check-substrate-watch.py:10-11` diz o oposto: «no-network
under ADR-136-AMEND-1; the doc fetch … is the one network action, so it is
Owner-run by design», reforçado em `:284` («the nightly agent stays
no-network»). O plano converteria um script deliberadamente sem rede e
operado pelo Owner num fetcher automático rodado por rotina cloud. E o
arquivo **não tem cerimônia**: `check-canonical-oracle.py --is-canonical
.claude/scripts/check-substrate-watch.py` retorna **rc 2** e ele não consta
de `.claude/governance/gate-scripts-manifest.txt`. Consequência de segurança
direta: o «allowlist FIXA de hosts/paths HTTPS» (`:70-71`), que é a ÚNICA
coisa que sustenta a garantia de egress, viveria num arquivo que qualquer
agente em sessão edita sem sentinel, sem pair-rail e sem assinatura.
*Mitigação:* separar as duas coisas. A **política** (allowlist de host+path,
limites, timeouts) vira dado sentinel-gated — `.claude/governance/*.json` já
cobre o padrão sem estender a lista KERNEL. O **fetcher** é um arquivo novo,
declarado em `gate-scripts-manifest.txt` no mesmo patch. `check-substrate-watch.py`
mantém seu contrato no-network e apenas CONSOME o ledger produzido.

**R-SEC4 — P1 — O número `ADR-149 Amendment 2` já está ocupado por outra
emenda, landada.**
`PLAN-176-model-currency-refresh.md:30` afirma que a arquitetura foi
«decidida no ADR-149 Amendment 2, não aqui», e `:122-125` manda formalizar o
draft `PLAN-176/adr-149-amendment2-draft.md` (título: «Amendment 2 (DRAFT):
Trust vs Preference») «via cerimônia de ADR no início da execução». Mas
`.claude/adr/ADR-149-model-id-allowlist.md:209` já contém «## Amendment 2
(S338 — Fable 5.1 joins the working set; floor, fallback and pin unchanged)»,
ratificado pelo Owner e landado pela cerimônia `wave-fable51`
(`ADR-149…:211-215`). Duas leituras, ambas ruins: ou a cerimônia sobrescreve
uma emenda assinada, ou o plano cita como AUTORIDADE JÁ DECIDIDA (`:30`) uma
doutrina que em `:122` ele mesmo chama de draft não ratificado. Nenhuma
autoridade para o split T/P existe no HEAD.
*Mitigação:* renumerar para **Amendment 3** e reconciliar `:30` com `:122`
(o §1 passa a dizer «proposta nesta emenda», não «decidida»). O `/debate`
não pode certificar coerência de um plano cuja premissa arquitetural se
declara simultaneamente decidida e pendente.

**R-SEC5 — P1 — Nenhum evento de auditoria para o despacho externo, com a
taxonomia já pronta em disco.**
`audit_emit.py:772` já shipa `egress_destination_detected`, com campos
`egress_class` (enum fechado, re-coerção para `"unknown"` em
`audit_emit.py:6833-6834`) e `destination` restrito a **BARE HOST**, nunca
URL/path/query/credencial (`audit_emit.py:770-771`). O PLAN-176 não cita esse
evento em lugar nenhum; a única «proveniência» que oferece é «digest sha256
da resposta gravado» (`:72`). Digest não é auditoria: ele é computado pelo
próprio processo que buscou, não é encadeado no HMAC, e — como a rotina W1
roda em sessão CLOUD — cai numa família de auditoria por projeto que
`verify_chain()` local nunca lê (a separação por projeto da W1 do PLAN-182,
CLAUDE.md §5). Um fetch que nunca aconteceu e um fetch adulterado produzem o
mesmo artefato: um JSON com um sha256 dentro.
*Mitigação:* AC novo — **todo** despacho externo emite
`egress_destination_detected` com `egress_class` do enum e o host nu; e o
relatório da W1 é inútil como evidência a menos que seus digests sejam
re-verificáveis no repo local. Se a correlação cloud↔local não for viável,
declare-a fora de escopo explicitamente (molde ADR-190), não por silêncio.

**R-SEC6 — P2 — ADR-114 não cobre este egress; citá-lo como revisão é erro de
categoria.**
`ADR-114-codex-egress-redaction-symmetry.md:27-41` decide implementar
`redact_outgoing()` em `_lib/codex_egress_redact.py` e o WIRE em callsites
enumerados: `codex_invoke.py:invoke_codex()` e
`check_pair_rail.py:_invoke_codex_review()`. É um redator de **prompt para
LLM de terceiro**. Um `urllib` GET a um feed de vendor não passa por
nenhum desses callsites, logo o redator não é invocado. `PLAN-176:77-78`
(«Revisão ADR-114 no debate de abertura») trata um ADR de superfície
diferente como se fosse a garantia deste caminho. Além disso a própria
garantia «GET-only, SEM body, NADA do repo sai» (`:73-77`) fala de
«requisições» sem qualificar a wave, enquanto a W2 (`:79-84`) **abre PR** —
um POST autenticado carregando conteúdo do repo. A garantia, como escrita, é
falsa para o plano como um todo.
*Mitigação:* escopar a garantia («requisições de INGESTÃO de feed são
GET-only…») e nomear o egress da W2 como um segundo canal, com seu próprio
controle. ADR-114 entra como precedente de forma, não como cobertura.

**R-SEC7 — P2 — Conteúdo de feed de vendor é ENTRADA NÃO CONFIÁVEL que
termina num PR lido por humano; o plano não o trata como tal.**
`:70-72` valida forma (tamanho, timeout, host, digest) e `:96` cobre drift de
parser — nenhum controle sobre o CONTEÚDO. Um campo de texto num feed (nome
de modelo, nota de release) flui para o relatório e para o corpo do PR que o
Owner revisa. É o padrão «record whose digest is prose»: o sha256 atesta
bytes, não semântica, e o revisor humano é o alvo. O repo já pagou a lição
(CLAUDE.md §5, r22 do PLAN-179: canal instruction-adjacent fecha por
REMOÇÃO, não por enumeração).
*Mitigação:* do feed entram apenas campos de um conjunto FECHADO, cada um
validado contra gramática estrita (`^[a-z0-9][a-z0-9.-]{0,63}$` para ids,
data ISO para timestamps); tudo mais é DESCARTADO, não citado. Nenhuma prosa
do upstream entra no corpo do PR — só contagens e digests.

**R-SEC8 — P2 — O «CI vermelho fail-closed se o PR tocar T/schema» é
auto-referente ao branch que a própria rotina escreve.**
`:82-83` e `:93` colocam o guard no CI. Mas `.github/workflows/*.yml` está
guardado apenas por hook LOCAL (`check_canonical_edit.py:184-185`), e um
guard local não roda contra um branch empurrado por uma rotina cloud. Para
PR de branch do MESMO repo, o workflow executado é o do branch. Um PR que
edite o guard e o arquivo T no mesmo commit desarma a checagem que deveria
pará-lo. O plano não nomeia quem verifica o conjunto de paths tocados.
*Mitigação:* o gate que decide sobre a camada T não pode viver só no
workflow do branch — precisa de um required check independente do conteúdo
do PR (ou de uma regra de proteção de branch) mais um oráculo local
`touched − {paths P} = ∅` na revisão do Owner. Enquanto isso não existir, o
kill criterion de `:93` não pode ficar vermelho por si.

**R-SEC9 — P2 — `.claude/data/` é totalmente desguardado, e já hospeda um
artefato de modelo EXPIRADO que o plano não reconcilia.**
`grep "claude/data" .claude/hooks/check_canonical_edit.py` retorna **zero**:
nenhum padrão cobre o diretório. Isso é intencional para a camada P — mas
`.claude/data/canonical_models.json:10` traz `"valid_until": "2026-09-01"`,
já vencido em 2026-09-06. O plano cita esse arquivo em `:154-155` como «rot»
e nunca decide se `models-preference.json` o SUBSTITUI ou coexiste com ele.
Duas grafias P do mesmo fato é exatamente a forma D1–D4 (CLAUDE.md §5: a
ORIGEM tinha dono, a ROTA não).
*Mitigação:* o W0 declara a rota destino→fonte para os artefatos P no molde
de `scripts/delivery-routes.tsv`, e `canonical_models.json` ou vira leitor de
`models-preference.json` ou é retirado no mesmo patch. Não deixe dois
arquivos P vivos.

**R-SEC10 — P2 — Onde mora `check-model-literals.py` decide se ele é
autenticado, e o plano não diz.**
`:46-48` e `:61-62` nomeiam o lint sem path. A diferença é de segurança, não
de estilo: `.claude/hooks/*.py` é guardado (`check_canonical_edit.py:139`) e
`.claude/hooks/_lib/*.py` também (`:142-144`), mas `.claude/scripts/*.py`
**não** aparece na lista (verificado: o grep por `claude/scripts/*` na lista
de padrões não retorna entrada). Um lint com ratchet+grandfather cujo
LEDGER e cujo código são editáveis sem cerimônia não é ratchet — o próximo
literal se auto-perdoa. O ledger de grandfather é um arquivo a mais que o
plano nunca nomeia.
*Mitigação:* o resolver vai para `.claude/hooks/_lib/model_registry.py`
(guardado por construção); o lint e seu ledger vão para superfície guardada
ou entram em `gate-scripts-manifest.txt` no mesmo patch — decidido ANTES do
W0, porque muda a contagem de paths.

**R-SEC11 — P3 — O W0 não cabe no modelo de operação v2 como está escrito.**
Enumerando o que `:54-62` exige: (1) `models-registry.json`,
(2) `models-preference.json`, (3) `_lib/model_registry.py`,
(4) `check-model-literals.py`, (5) ledger de grandfather, (6) oracle
`replacements ⊆ valid_override_ids`, (7) testes do resolver, (8) testes do
lint, (9) wire no `validate.yml`, (10) `gate-scripts-manifest.txt` (se
R-SEC10 for resolvido para dentro), mais os materiais da cerimônia do ADR.
São ≥ 10 paths contra o teto de 8 do modelo v2, antes de contar o sentinel.
*Mitigação:* dividir — **W0a** = schema T + resolver + testes (sem lint);
**W0b** = lint + ledger + oracle + wire de CI. O split é natural porque W0b
consome o resolver de W0a.

## Must-fix (blocking)

1. **Reescrever a precedência como seleção × validação (R-SEC1)**, com T
   funcionando como teto para papéis VETO/pin e fail-closed nomeado fora
   dele. Sem isso o split não preserva cerimônia alguma.
2. **Fechar o conjunto de env vars e proibir carrier de PATH para o registry
   T (R-SEC2)**; o teste-mestre roda por seam de dependência, não por
   ambiente.
3. **Tirar a rede de `check-substrate-watch.py` (R-SEC3)**: política de
   egress vira dado sentinel-gated em `.claude/governance/`, fetcher vira
   arquivo novo declarado em `gate-scripts-manifest.txt` no mesmo patch.
4. **Renumerar a emenda para Amendment 3 e reconciliar §1 com §3b
   (R-SEC4)** — hoje o plano cita como decidido o que ele mesmo declara
   draft, e o número está ocupado por emenda assinada.
5. **AC de auditoria por despacho externo usando
   `egress_destination_detected` (R-SEC5)**, com a incorrelação cloud↔local
   declarada explicitamente se não for curada.

## Nice-to-have (advisory)

1. Escopar a garantia de egress à ingestão e tratar o PR da W2 como segundo
   canal (R-SEC6).
2. Conjunto FECHADO de campos aceitos do feed; nenhuma prosa upstream no PR
   (R-SEC7).
3. Required check independente do branch para o guard T/P (R-SEC8).
4. Decidir o destino de `canonical_models.json` no mesmo patch (R-SEC9).
5. Fixar o path do lint e do ledger antes do W0 (R-SEC10).
6. Dividir W0 em W0a/W0b (R-SEC11).

## Open questions para o Owner ratificar

- **OQ-S1:** T é teto ou default? (decide R-SEC1 e o desenho do resolver)
- **OQ-S2:** existe alguma env var de modelo? Se sim, qual conjunto fechado —
  e nenhuma delas aponta path, correto?
- **OQ-S3:** a rotina cloud da W1 recebe token com permissão de escrita no
  repo? Em qual escopo, e quem revoga?
- **OQ-S4:** hosts e paths concretos do allowlist — o plano não nomeia nenhum.
- **OQ-S5:** `canonical_models.json` (vencido em 2026-09-01) é substituído ou
  coexiste?
- **OQ-S6:** Amendment 3 (renumerada) ou ADR próprio para o split T/P?

## What I would NOT change

- **Pôr a camada T em `.claude/governance/*.json`.** Verificado: o padrão já
  existe (`check_canonical_edit.py:235`) e a lista é KERNEL — o arquivo nasce
  sentinel-gated sem estender guard algum. É a decisão mais barata e mais
  forte do plano.
- **Camada P sem sentinel, por design.** Governança cara em superfície de
  troca frequente produz bypass; a assimetria está certa — o que falta é o
  teto de R-SEC1, não mais cerimônia.
- **Fail-closed em feed malformado, stale ou parcial (`:72`, `:94-96`)** e o
  **controle de falso-NEGATIVO mensal (`:97-99`)** — um kill criterion que
  testa o DETECTOR, não só o detectado, é a forma certa.
- **Fase 2 (auto-merge) fora, gated em ADR (`:83-84`, `:102`).**
- **Sem fetcher paralelo de CLI (`:66-69`)** — a intenção anti-double-booking
  é correta; só a implementação (R-SEC3) precisa mudar de arquivo.
