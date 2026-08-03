---
id: PLAN-165
title: Night-mode — Owner-invoked autonomy posture toggle
status: reviewed
created: 2026-08-02
reviewed_at: 2026-08-02
owner: CEO
depends_on: [PLAN-163]
budget_tokens: 90-140k
budget_sessions: 2
context_risk: medium
external_wait: owner-gpg-ceremony
tags: [governance, harness-config, autonomy, commands, security]
---

# PLAN-165 — Night-mode: Owner-invoked autonomy posture toggle

> **v2 (2026-08-02).** v1 foi REJEITADO pelos três lanes de review
> (codex / grok / painel Claude de 6 lentes). O consenso e as evidências
> estão em `PLAN-165/architect/round-1/`. A abordagem sobreviveu intacta;
> a camada de afirmações em volta dela, não. Duas frases do v1 eram
> factualmente falsas e uma feature colidia de propósito com um tripwire
> de segurança existente. Este arquivo é a reescrita.
>
> **Status.** Continua `draft` de propósito: `reviewed` significa "o Owner
> leu e aceitou", e isso ainda não aconteceu. O trabalho de review
> cross-vendor está feito. Para ratificar: `status: reviewed` +
> `reviewed_at: <data>`. Mesmo ratificado, o W1 continua bloqueado pelos
> pré-requisitos de cerimônia P1/P2 abaixo.

## Context

Necessidade do Owner (S288, verbatim): *"apesar do framework desligar o
automode eu preciso de um caminho que eu possa ligar novamente […]
principalmente quando vou dormir e quero que rode autônomo. e está vindo
sempre desligado por padrão pq tá no json do repo."*

A postura fail-closed é ratificada pelo Owner (PLAN-163 T5.3 / OQ5(c)) e
está viva no `.claude/settings.json` rastreado: `permissions.defaultMode:
"manual"` + `disableAutoMode: "disable"`.

Fatos que restringem qualquer caminho de re-habilitação. Cada um cita a
evidência; nenhum é assumido:

1. **`disableAutoMode` não tem valor "enable".** Em CC 2.1.220 é um enum
   de string cujo único valor legal é `"disable"`; qualquer outro faz o
   harness PULAR o arquivo de settings inteiro (hotfix S286 `838527a`).
   Re-habilitar significa REMOVER a chave, e um overlay de merge não
   remove chave da camada de projeto.
2. **Remover `disableAutoMode` sozinho não dá autonomia.** A mesma
   postura fixa `permissions.defaultMode: "manual"`. A alavanca do
   night-mode é o defaultMode, não a chave de escalação.
3. **Por isso o arquivo rastreado é intocável.** `disableAutoMode` bloqueia
   escalação *automática no meio da sessão*. Uma sessão **iniciada já no
   modo alvo** nunca precisa escalar — então night-mode é alcançável sem
   editar o `.claude/settings.json` rastreado, via o
   `.claude/settings.local.json` per-machine e gitignored
   (`.gitignore:78`). A precedência **NÃO é assumida**: é sondada em W0.
4. **O settings.json rastreado é superfície vigiada.** `/ceo-boot` roda
   `settings_tamper_tripwires` + `harness_config_gate`; `check_bash_safety`
   trata corpos de `-c`/`-e` que referenciem `.claude/settings.json` como
   vetor de canonical-edit (confirmado ao vivo em S288 — o guard bloqueou
   uma verificação de leitura durante este próprio review).
5. **Modelo de tempo casa com o caso de uso.** Settings são lidos no início
   da sessão; o toggle vale na PRÓXIMA. "Ligar antes de dormir → sessão
   noturna → desligar de manhã" é exatamente semântica de próxima-sessão.
   A sessão governada corrente nunca muda de postura sob o operador.
6. **O piso de deny nunca foi confirmado ao vivo.**
   `docs/PERMISSION-MODEL-DESIGN.md:368` marca "Native deny actually fires"
   como PENDING-LIVE. Nada neste plano pode assumir que o deny protege algo.

## Goal

O Owner alterna a postura de autonomia per-machine com um comando —
reversível, visível no boot e **auditado** — sem sujar a árvore rastreada,
sem enfraquecer o default publicado, e sem colidir com os tripwires de
segurança existentes.

## Non-goals

- Mudar a postura default publicada (templates e adopters intocados).
- Qualquer escalação de modo no meio da sessão.
- Autonomia em CI ou runner headless (operador/máquina local apenas) —
  **com enforcement**, não só declarado: o script recusa quando `CI` está
  setado (AC-11).
- **`bypassPermissions`.** Cortado em v2 — ver §Decisão D1.

## Decisões de desenho tomadas no review

### D1 — `--full` / `bypassPermissions` foi CORTADO

v1 propunha `--full` gated por ack digitado. Três lanes convergiram que
isso não pode existir como desenhado, e a verificação confirmou:

- `effective_config.py:177-181` mapeia `permissions.defaultMode ==
  bypassPermissions` para `TAMPER_PERMISSION_BYPASS`, **em qualquer
  camada** — `_layer_paths()` inclui `settings.local.json` sem isenção.
- `ceo-boot.py:1605-1620` emite `settings_tamper_detected` e devolve `red`.
- Existe teste que fixa esse comportamento:
  `test_ceo_boot_tamper_tripwires.py:255-261` constrói exatamente
  `{"permissions":{"defaultMode":"bypassPermissions"}}` na camada local e
  afirma `red`.

Ou seja: enviar `--full` faria o produto ensinar o Owner a ignorar um
tripwire de segurança verdadeiro. E o único jeito de silenciá-lo —
allowlistar night-mode em `FORBIDDEN_KEYS` — é enfraquecimento de controle
de segurança e reentra na carve-out (PROTOCOL.md:436), que nenhum feedback
de revisor pode afrouxar.

`acceptEdits` já atende à necessidade declarada. Quem precisar de bypass
real tem o caminho honesto, sem estado persistente e sem colisão:

```bash
claude --permission-mode bypassPermissions     # uma sessão, explícito, efêmero
```

Isso é documentado em W2.2 como a válvula de escape, não implementado aqui.

### D2 — O escritor único precisa da cerimônia ANTES do W1

`.claude/settings.local.json` **não** está no deny (o deny cobre
`Edit(.claude/settings.json)`, settings.json:771, e não o overlay). Sob
`acceptEdits`, escrever o overlay é auto-aceito — e o overlay decide a
postura. Isso é uma escada de escalação real: agente entra em acceptEdits,
reescreve o overlay, e a sessão seguinte nasce em bypass sem ninguém
digitar nada.

Escopo honesto: `acceptEdits` **não** anula o deny nem desarma hooks —
todo PreToolUse (canonical-edit, bash-safety, kernel) continua disparando.
A máquina fica menos perguntadeira, não ingovernada. Mas o alvo de escrita
que controla a postura fica desprotegido, e isso é inaceitável para um
plano cujo produto é justamente escrever ali.

A correção é uma regra de deny nova — o que significa editar
`.claude/settings.json`, arquivo canonical-guarded. **Não cabe na wave
deste plano.** Vira pré-requisito de cerimônia, e W1 fica bloqueado nele.

### D3 — O banner sai do resolver, não do marker

v1 acendia o banner pela presença do marker. Marker e settings são duas
fontes de verdade que dessincronizam (crash entre as escritas, Owner
editando o overlay à mão). O banner passa a derivar de
`_lib/effective_config.resolve_settings()` — o mesmo resolver que o
tripwire usa — e o marker vira decoração (timestamp, hostname, qual modo o
night-mode escreveu).

E o banner deixa de ser vendido como garantia: `/ceo-boot` é manual
(`auto_boot.py:91` exige `CEO_AUTO_BOOT=='1'`, nunca setado), as
recomendações são capadas em `recs[:5]` (ceo-boot.py:2671, :2806) e o cache
pode retornar antes da renderização. É lembrete advisory para quem roda
`/ceo-boot`. A AC reflete isso.

## Pré-requisitos — cerimônia de sentinel (BLOQUEIA W1)

Ambos entram na cerimônia já enfileirada (com RC3-F7 e GA-F3). W1 não
começa antes de landarem.

- **P1 — regra de deny para o overlay.** `Edit(.claude/settings.local.json)`
  e `Write(.claude/settings.local.json)` no bloco `permissions.deny` do
  `.claude/settings.json`, espelhado em `templates/settings/settings.base.json`
  (senão `test_template_dogfood_parity` reddena). Fecha D2.
  Consequência de desenho: `night-mode.py` passa a ser o **único** escritor,
  e escreve como processo, não como Edit/Write de ferramenta.
- **P2 — ação de auditoria.** Registrar `night_mode_toggled`. **Não é uma
  linha.** `_lib/audit_emit.py` é caminho de arbitration-kernel sem escape
  por sentinel, e `test_audit_emit_ghost_action_guard.py:250` impõe a
  partição branched/reserved/passthrough. A mudança tem 4 fontes: entrada
  em `_KNOWN_ACTIONS`, o branch/wrapper tipado com scrub deny-by-default de
  campos, a entrada de schema/versão no SPEC, e os testes de partição +
  cadeia HMAC. Campos permitidos: `mode`, `previous_mode`, `result`,
  `hostname_hash`. Nunca caminho de arquivo, nunca conteúdo.
  `audit_emit.py` está no manifesto de inputs do pair-rail (linha 27), então
  o `inputs_hash` dos verdicts futuros muda — recomputar na cerimônia.

> **Correção do v1.** O v1 afirmava (l.99-101) que o observador L6
> `audit_log.py` já encadeava a invocação forensicamente. **Isso é falso.**
> `audit_log.py` está registrado uma única vez, PostToolUse matcher `Agent`
> (settings.json:352). As únicas registrações PostToolUse de Bash são
> `check_bash_canonical_forensic.py` (só emite para caminho canônico — e o
> overlay não está em `_CANONICAL_GUARDS`) e `check_output_secrets.py`. Sem
> P2 a auditoria é **zero**, não "observador L6 apenas". Por isso P2
> bloqueia em vez de ficar como rider opcional: o Goal diz "auditado".

## Approach

`/night-mode on|off|status`, apoiado por `.claude/scripts/night-mode.py`
(stdlib only, Python ≥3.9, `from __future__ import annotations`).

- **`on`** — merge-write em `.claude/settings.local.json` fixando
  `permissions.defaultMode: "acceptEdits"`. Contrato de escrita abaixo.
- **`off`** — restaura o valor snapshotado (ou remove a chave), remove o
  marker.
- **`status`** — imprime a postura resolvida por camada usando
  `_lib/effective_config.resolve_settings()`, a idade do marker, e se
  marker e configuração resolvida **concordam**.
- **Boot** — `/ceo-boot` renderiza linha advisory quando o resolver mostra
  postura não-ratificada (D3), fail-open, nunca bloqueia o boot.

### Contrato de escrita

Todo item aqui era não-especificado em v1 e gerava estados irrecuperáveis.

1. **Lock** — `_lib/filelock.FileLock` em volta de toda a sequência.
2. **Atômico** — escrever em temp no mesmo diretório, `fsync`, `os.replace`.
   Nunca escrita truncante in-place: um truncamento faz o harness pular o
   arquivo inteiro (classe do S286).
3. **Read-back** — reabrir e re-parsear após o replace; divergência ⇒ sai
   não-zero sem tocar o marker.
4. **Snapshot create-only** — o snapshot é gravado apenas se ainda não
   existir. Sem isso, `on` duas vezes snapshota o valor que o próprio
   night-mode escreveu, e `off` "restaura" para `acceptEdits` — postura
   fraca permanente.
5. **Ordem definida** — settings primeiro, marker depois; `off` na ordem
   inversa. `status` reconcilia e reporta desacordo em vez de escolher um.
6. **Input malformado é fail-CLOSED** — `settings.local.json` que não
   parseia não é reescrito nem "consertado": sai não-zero com diagnóstico.
   (Doutrina do repo: fail-open em infra, fail-closed em input.)
7. **Idempotência** — `on` duas vezes e `off` duas vezes são no-ops que
   saem zero.

## Waves

### W0 — Sondas live-fire (ponto de kill/pivot)

**Predicado de passa/falha** (v1 não tinha nenhum — era um gate sem
condição): W0 PASSA sse T0.1 e T0.2 passam. T0.4 e T0.6 informam o desenho
mas não matam o plano. Falha de T0.1 ⇒ pivot para o fallback.

Evidência de cada sonda em `.claude/plans/PLAN-165/probes/`.

- **T0.1** — `settings.local.json` `permissions.defaultMode` vence o
  `"manual"` do projeto em CC 2.1.2xx. Evidência: transcript de sessão
  **mais** `resolve_settings()` imprimindo a camada efetiva.
  *Não usar `/ceo-info` como evidência: ele nunca lê nem imprime
  `permissions.defaultMode`* (defeito encontrado no review do v1).
- **T0.2** — sessão iniciada em `acceptEdits` com `disableAutoMode:
  "disable"` presente opera sem prompt em ação **não**-allowlistada (fato
  #3). Tem de ser não-allowlistada, senão a sonda é vacuosa: allowlistadas
  já não perguntam em manual.
- **T0.3** — inventário de guard-surface: confirmar que `night-mode.py`,
  `night-mode.md`, `settings.local.json`, o marker **e `ceo-boot.py`**
  (W2.1 edita) batem em ZERO padrões de `_CANONICAL_GUARDS`. Ler a lista;
  não inferir.
- **T0.4** — o deny sobrevive sob `acceptEdits`? Rodar num install de
  rascunho, não na árvore viva. Ligado ao fato #6: se o deny nunca dispara,
  registrar em §Security como classe residual em vez de fingir piso.
- **T0.5** — a camada local consegue REMOVER `disableAutoMode` da camada de
  projeto? v1 afirmava que não, sem sondar. Se conseguir, simplifica.
- **T0.6** — controle de presença do Owner: uma invocação por `!` do
  Claude Code recebe tty? A resposta escolhe o mecanismo em OQ1.
- **T0.7** — fixar a convenção de slug do marker. Há convenções
  incompatíveis vivas na mesma máquina (CLAUDE.md define caminho absoluto
  com `/`→`-`; o audit-log real usa o slug curto). Nomear o resolver que
  night-mode e `/ceo-boot` vão **ambos** usar. Divergência = banner nunca
  dispara.

### W1 — Implementar (bloqueado por W0 **e** pelos pré-requisitos P1/P2)

- **T1.1** `.claude/scripts/night-mode.py` — on/off/status implementando o
  contrato de escrita inteiro. stdlib only.
- **T1.2** `.claude/commands/night-mode.md`.
- **T1.3** Testes em `.claude/scripts/tests/`, todos sob `TestEnvContext`
  **com** `mock.patch.dict`, incluindo o root de estado (o `TestEnvContext`
  isola HOME e o env do audit-log, mas uma constante de caminho de marker
  resolvida em import-time escapa — ancorar o caminho numa função, não num
  literal de módulo). Matriz mínima: merge preserva chaves não-relacionadas;
  round-trip de snapshot; snapshot é create-only (`on`→`on`→`off` volta a
  `manual`, não a `acceptEdits`); duplo-on/duplo-off idempotentes; JSON
  malformado sai não-zero sem escrever; replace atômico deixa o arquivo
  parseável; read-back pega escrita corrompida; ciclo de vida do marker;
  recusa sob `CI` setado.
- **T1.4** Revisão do Security Engineer **com VETO** (não advisory): a
  superfície muda postura de permissão. Cascata V0-V3 completa.
- **T1.5** Pair-rail codex sobre o diff do script.
- **T1.6** ADR para a decisão (exigido em L3): registra D1 (bypass cortado),
  D2 (escritor único via cerimônia) e D3 (banner via resolver).

### W2 — Boot, docs, ratificação

- **T2.1** Linha advisory no `/ceo-boot` derivada de `resolve_settings()`
  (D3). Cuidado: `ceo-boot.py` mantém **duas** listas espelhadas à mão de
  checks/recomendações — editar uma só é drift. Testes.
- **T2.2** Docs. **Contagem 26→27 — sites nomeados, não "superfícies
  derivadas"**, porque `check-claude-md-claims.py` não tem uma única
  referência a comando e contribui zero para este gate:
  - `CLAUDE.md` §1
  - `README.md`
  - `README.pt-BR.md` ← **não está na lista DOCS do `verify-counts.sh`**;
    drift silencioso numa superfície publicada
  - `docs/ARCHITECTURE.md` (duas ocorrências, uma na forma "22 of them",
    que nenhuma regra do verify-counts casa)
  - `npm/README.md`
  - `docs/COMMAND-SKILL-HOOK-MAP.md` — **regenerar**, não editar à mão
  - manifestos de plugin via `scripts/build-plugin.py --write-manifests`

  Mais `docs/CHEAT-SHEET.md` (linha na tabela de operação),
  `docs/TROUBLESHOOTING.md` ("por que meu automode está desligado") e a
  nota de FAQ, incluindo a válvula de escape do D1. Rodar
  `verify-counts.sh` + `build-plugin.py --check` **antes** do push
  (tolerância 0).
- **T2.3** Nota datada na seção OQ do PLAN-163: postura default inalterada;
  override efêmero per-machine adicionado por PLAN-165.
- **T2.4** Tópico de memória + linha de índice.

## Fallback (se T0.1 falhar)

Sem escrita de settings. `/night-mode` vira wrapper documentado de
`claude --permission-mode acceptEdits`, `status` reporta que o toggle
persistente está indisponível nesta versão do harness, e as AC-1/AC-2 são
substituídas pelas ACs do fallback (o v1 mantinha ACs insatisfazíveis sob
o próprio fallback dele). Note que a flag já existe — o fallback é mais
barato que o caminho principal e deve ser reconsiderado como desenho
primário se W0 ficar apertado.

## Acceptance criteria

- [ ] **AC-1** `/night-mode on` + sessão nova ⇒ sessão inicia em
      `acceptEdits` (respaldado por T0.1), e `git status` continua vazio.
      Check: `git status --porcelain` vazio após `on`.
- [ ] **AC-2** `/night-mode off` + sessão nova ⇒ postura de volta a
      `manual` ratificado. Check: `resolve_settings()` reporta `manual`.
- [ ] **AC-3** `on`→`on`→`off` volta a `manual`, não a `acceptEdits`
      (snapshot create-only). Check: teste unitário.
- [ ] **AC-4** `settings.local.json` malformado ⇒ saída não-zero, arquivo
      não modificado. Check: teste compara bytes antes/depois.
- [ ] **AC-5** Crash simulado entre escrita e marker deixa o arquivo
      parseável e `status` reportando o desacordo. Check: teste unitário.
- [ ] **AC-6** `/ceo-boot` mostra a linha advisory sse `resolve_settings()`
      mostra postura não-ratificada — derivada do resolver, não do marker.
- [ ] **AC-7** Após `on` e após `off`, existe linha `night_mode_toggled`
      correspondente em `audit-log.jsonl` e `verify_chain()` continua
      passando. (Depende de P2.)
- [ ] **AC-8** Escrita direta em `.claude/settings.local.json` por Edit/Write
      é negada. (Depende de P1.) Check: probe positivo — a negação é
      observada, não presumida.
- [ ] **AC-9** Suítes verdes na **invocação do CI**:
      `pytest .claude/scripts/tests/ -n auto -m 'not serial'` **e**
      `pytest .claude/scripts/tests/ -m 'serial'`.
      *Não* `unittest discover`: a suíte é pytest-only por construção
      (conftest.py são hooks de coleta; vários módulos isolam env via
      fixture `autouse`). O v1 nomeava `unittest discover` — a mesma classe
      de defeito que produziu um falso-vermelho no `release-v1-2-0.sh` e
      barrou o promote do GA v1.2.0 em 2026-08-02.
- [ ] **AC-10** Aprovação do Security Engineer com VETO registrada;
      pair-rail codex registrado; ADR landado.
- [ ] **AC-11** O script recusa quando `CI` está setado (non-goal com
      enforcement). Check: teste unitário.
- [ ] **AC-12** Templates e defaults publicados byte-idênticos, **exceto** a
      regra de deny do P1, que é deliberada e espelhada em
      `templates/settings/settings.base.json`.
- [ ] **AC-13** `verify-counts.sh` e `build-plugin.py --check` verdes com o
      novo comando em disco, e os sites de contagem atualizados por nome.

## Security notes

- **`bypassPermissions` não é enviado** (D1). O caminho honesto para bypass
  é `claude --permission-mode bypassPermissions` numa sessão explícita —
  efêmero, sem estado persistente e sem colisão com tripwire.
- **`acceptEdits` continua sendo enfraquecimento real** de controle, mesmo
  sendo o modo brando: edições de arquivo passam a ser auto-aceitas. Não
  anula o deny nem desarma hooks — todo PreToolUse continua disparando.
  O que muda é a frequência de prompt, não a governança.
- **A escada de escalação é fechada por P1**, não por convenção. Até P1
  landar, o plano não deve ser executado: enviar o toggle sem a regra de
  deny cria exatamente o caminho de escalação que o toggle deveria tornar
  deliberado.
- **A carve-out de segurança se aplica** (PROTOCOL §Receiving review):
  nenhum feedback de revisor pode afrouxar P1, P2, o predicado de W0 ou o
  fail-closed de input malformado.
- **Classe residual:** se T0.4 mostrar que o deny nativo não dispara (fato
  #6 — nunca confirmado ao vivo), as entradas de Read de credenciais
  (`~/.ssh`, `~/.aws`, `~/.netrc`, família `.env`) são as que não têm gêmeo
  em hook. Registrar aqui em vez de assumir piso.

## Open questions (ratificação do Owner no início da execução)

- **OQ1** controle de presença do Owner para `on`: tty-check (Recomendado
  se T0.6 mostrar que `!` dá tty) vs variável de ambiente do processo pai
  no molde de `check_arbitration_kernel.py` vs nenhum, confiando só em P1.
  *v1 propunha ack digitado; descartado — qualquer modelo com Bash digita o
  token, então não é controle de presença.*
- **OQ2** expiração: só banner (Recomendado) vs TTL duro com auto-off.
  Nota: a justificativa do v1 para recusar TTL era "impossível esquecer
  silenciosamente", o que se mostrou falso (D3) — então TTL merece
  reconsideração honesta e não é mais escolha óbvia.
- **OQ3** nome: `/night-mode` (Recomendado) vs `/automode` (palavra
  original do Owner). Decide nome de arquivo e a contagem nos sites, então
  ratificar **antes** do W1, não durante.

## How to continue

Estado durável entre sessões:

1. Ler `PLAN-165/architect/round-1/consensus.md` — os 13 defeitos
   estruturais e por que o v1 foi rejeitado.
2. Checar se os pré-requisitos P1/P2 landaram (`git log --grep=night_mode`).
   Se não, o plano está bloqueado — não começar o W1.
3. Se landaram: rodar W0 na ordem, gravando evidência em
   `PLAN-165/probes/`. Parar no predicado de W0.
4. Ratificar OQ1-OQ3 com o Owner antes do W1 (OQ3 decide nomes de arquivo).

## Success metrics

- O Owner consegue armar autonomia noturna com um comando e desarmar com
  outro, sem editar JSON à mão e sem sujar a árvore.
- Zero regressão nos tripwires: `/ceo-boot` continua verde com night-mode
  ligado no modo default (é o teste de que D1 estava certo em cortar o
  bypass).
- A postura fica visível: nenhuma sessão começa em modo não-ratificado sem
  que `/ceo-boot` diga.

## Level / debate

**L3.** O v1 se auto-declarava L2 para pular debate, enquanto sua própria
T1.4 chamava a superfície de "VETO-relevant per PROTOCOL §Vetoes" — as duas
não podem ser verdade. PROTOCOL.md:130 torna debate obrigatório para
domínio VETO-protegido; :402 exige aprovação do Staff Security.

Debate rodado em 2026-08-02, três lanes cross-vendor, resultado REJECT do
v1 → esta reescrita. Artefatos em `PLAN-165/architect/round-1/`.

> Nota de processo que vale mais que o plano: o v1 estaria em execução
> agora, com duas afirmações falsas dentro dele, se o Owner não tivesse
> pedido debate explicitamente. Um plano que se auto-declara L2 nunca
> encontra o revisor que descobriria que ele é L3. Isso é evidência sobre o
> gate de auto-classificação, não sobre este plano.
