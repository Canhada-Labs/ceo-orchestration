---
round: 1
plan: PLAN-165
date: 2026-08-02
outcome: REJECT-AS-WRITTEN (approach survives; the plan does not)
lanes: [codex, grok, claude-panel]
---

# Round 1 — consenso cross-vendor sobre PLAN-165

## Como esta rodada correu

Três lanes independentes revisaram o draft `fd372dd` sem se ver:

| Lane | Instrumento | Findings | Veredito |
|---|---|---|---|
| codex | `codex exec --sandbox read-only`, GPT-5.6 | 13 | **REJECT** |
| grok | `grok -p --sandbox council` | 15 (1 P0) | **REJECT** |
| claude-panel | workflow `wf_00bee7e7-a08` — 6 lentes + refutador adversarial por lente | 84 sobreviventes (17 P1 / 41 P2 / 26 P3) | **REJECT** |

Os refutadores do painel Claude fizeram trabalho real, não carimbo: rebaixaram
o P0 do grok para P1 com a correção de que `acceptEdits` **não** anula o deny
nem desarma hooks, e **rejeitaram** um fix proposto por ser repo-ilegal
(allowlist em `FORBIDDEN_KEYS` reentra na carve-out de segurança,
PROTOCOL.md:436).

Cinco alegações factuais foram verificadas pelo CEO contra a árvore viva antes
de qualquer uma ser aceita (disciplina C4 — verificar claims, não relatórios).
Todas as cinco confirmaram.

## Veredito

**REJECT como escrito. A abordagem sobrevive.**

O núcleo — overlay per-machine em `settings.local.json`, semântica de
próxima-sessão, não tocar no arquivo rastreado — continua de pé e nenhum lane
o atacou. O que morre é a camada de afirmações em volta dele: duas são
factualmente falsas, uma colide de propósito com um tripwire existente, e o
nível está errado.

## Os 13 defeitos estruturais

Ordenados por consequência. Nitpicks de redação ficam nos arquivos de lane.

### S1 — Nível errado: L2 → L3 · *codex F10, grok F3, painel ×3*

O plano se auto-classifica L2 para pular debate (l.197-203) enquanto sua
própria T1.4 (l.140-142) chama a superfície de "VETO-relevant per PROTOCOL
§Vetoes". As duas coisas não podem ser verdade. PROTOCOL.md:130 torna debate
obrigatório para domínio VETO-protegido; :402 exige aprovação do Staff
Security. Consequência: exige debate (esta rodada), ADR, revisão com VETO do
Security Engineer, e a cascata V0-V3 inteira — não um V2 advisory.

### S2 — A afirmação de auditoria é falsa · *codex F7, painel ×3*

Linhas 99-101 dizem que o observador L6 `audit_log.py` já encadeia a invocação
forense quando o Owner roda via `!`. **Falso.** `audit_log.py` está registrado
uma única vez, PostToolUse matcher `Agent` (settings.json:352). As únicas
registrações PostToolUse de Bash são `check_bash_canonical_forensic.py` (só
emite quando um operador de escrita referencia caminho CANÔNICO — e
`settings.local.json` não está em `_CANONICAL_GUARDS`) e
`check_output_secrets.py`. O estado interino é **auditoria zero**, não
"observador L6 apenas". O Goal diz "audited"; hoje não seria.

### S3 — `--full` colide com o tripwire de tamper por construção · *codex F8, grok F9, painel P1*

Escrever `bypassPermissions` na camada local é exatamente o cenário que o repo
já classifica como tamper hostil. Verificado por três caminhos:
`effective_config.py:177-181` (`FORBIDDEN_KEYS` → `TAMPER_PERMISSION_BYPASS`),
`_layer_paths()` inclui `settings.local.json` como layer `local` sem isenção,
`ceo-boot.py:1605-1620` emite `settings_tamper_detected` e devolve `red`. E
existe teste que fixa isso: `test_ceo_boot_tamper_tripwires.py:255-261`
constrói literalmente `{"permissions":{"defaultMode":"bypassPermissions"}}` na
camada local e afirma `red`.

Logo `--full` como desenhado ensina o Owner a ignorar um tripwire de segurança
real. E o conserto óbvio está vedado: allowlistar night-mode em
`FORBIDDEN_KEYS` é enfraquecer controle de segurança e reentra na carve-out.
**`--full` precisa ser redesenhado ou cortado.**

### S4 — Escada de escalação no caminho DEFAULT · *grok F1 (P0→P1), codex F1*

O deny tem `Edit(.claude/settings.json)` (settings.json:771) mas **não**
`settings.local.json`. Uma vez em `acceptEdits`, escrever o overlay é
auto-aceito — e o overlay controla a postura. Um agente chega em
`bypassPermissions` sem nunca ver o ack digitado.

Escopo correto (refutador): `acceptEdits` **não** anula o deny nem desarma
hooks — todo PreToolUse (canonical-edit, bash-safety, kernel) continua
disparando. A máquina fica "menos perguntadeira", não ingovernada. Ainda
assim, o alvo de escrita que decide a postura está desprotegido.

### S5 — O ack digitado não é controle de presença humana · *codex F1, grok F12, painel P2*

`NIGHT-MODE-FULL-I-ACCEPT` é um argumento de CLI. Qualquer modelo com Bash
digita. O precedente do repo para "só o Owner" é estado de ambiente do
processo pai, precisamente porque agente não forja
(`check_arbitration_kernel.py:25,38`). Um ack que o autor da escalação
consegue satisfazer não é gate.

### S6 — Modelo de estado não especificado · *codex F5, grok F4/F11, painel ×6*

Sem atomicidade, sem read-back, sem snapshot create-only, sem ordem entre as
duas escritas, sem tratamento de JSON malformado, sem lock (o repo tem
`_lib/filelock.py`). Estados ruins concretos:

- `on` duas vezes → o segundo snapshota o valor que o primeiro escreveu →
  `off` "restaura" para `acceptEdits`. Postura fraca permanente.
- crash entre escrita e fsync → `settings.local.json` truncado → o harness
  pula o arquivo inteiro (classe do hotfix S286).
- marker e settings são duas fontes de verdade sem reconciliação.

### S7 — O banner do boot não é garantia · *codex F6, grok F5, painel ×3*

`/ceo-boot` é manual: `auto_boot.py:91` devolve False a menos que
`CEO_AUTO_BOOT=='1'`, e essa variável só aparece num comentário. As
recomendações são capadas em `recs[:5]` (ceo-boot.py:2671 e :2806) sem slot
reservado. O cache pode retornar antes da renderização (:2390, :3930). E o
banner sai do marker, não da configuração que o harness realmente obedece.
"Impossível esquecer silenciosamente" (l.180-181) não se sustenta — e é
justamente a razão dada em OQ2 para recusar TTL.

### S8 — W0 é um gate sem predicado · *grok F12, painel ×2*

W0 é declarado "kill/pivot decision point" mas só define artefatos de
evidência, nunca uma condição de passa/falha. E faltam as sondas de que o
desenho depende: deny sobrevive sob `acceptEdits`/`bypass`; a camada local
não consegue REMOVER uma chave; o deep-merge de `permissions` preserva
allow/deny. Pior: T0.1 nomeia a saída do `/ceo-info` como evidência, e o
`/ceo-info` nunca lê nem imprime `permissions.defaultMode`.

Nota que muda o desenho: `docs/PERMISSION-MODEL-DESIGN.md:368` marca "Native
deny actually fires" como **PENDING-LIVE**. O repo nunca confirmou que o deny
dispara sob modo nenhum. Não dá para assumir piso de deny.

### S9 — Enumeração de count-drift errada e incompleta · *codex F12, grok F10, painel ×6*

`check-claude-md-claims.py` não tem uma única referência a comando —
contribuição zero para o gate 26→27. São 8 ocorrências com a contagem em 5
arquivos; `docs/COMMAND-SKILL-HOOK-MAP.md` precisa ser regenerado;
`README.pt-BR.md` carrega a contagem e **não** está na lista DOCS do
`verify-counts.sh` → drift silencioso numa superfície publicada.

### S10 — O rider de cerimônia está subdimensionado · *codex F7, grok F13, painel ×3*

R1 está escrito como `_KNOWN_ACTIONS += night_mode_toggled`, uma linha. Não é:
`_lib/audit_emit.py` é caminho de arbitration-kernel **sem escape por
sentinel**, e `test_audit_emit_ghost_action_guard.py:250` impõe partição
branched/reserved/passthrough — um append cru derruba CI.

### S11 — O slug do marker é ambíguo · *grok F6, painel ×3*

`~/.claude/projects/<slug>/` tem convenções incompatíveis vivas na mesma
máquina (o CLAUDE.md define slug como caminho absoluto com `/`→`-`; o
audit-log real usa o slug curto). Se toggle e boot escolherem convenções
diferentes, o banner nunca dispara.

### S12 — A garantia de árvore limpa é falsa para adopters · *codex F9*

`scripts/install.sh` distribui comandos e scripts (:1116, :1265) mas não
instala a regra de `.gitignore` para `settings.local.json`. Num repo adopter
que não a tenha, `/night-mode on` suja a árvore rastreada — contradizendo o
non-goal "adopter behavior unchanged" e a AC "no adopter drift".

### S13 — Lacunas de PLAN-SCHEMA e ACs não verificáveis · *painel ×6*

Faltam `## How to continue` e `## Success metrics`; zero linhas `Check:` (o
enforcer passa vacuamente); `depends_on: []` subestima PLAN-163, de onde a
premissa inteira deriva; a AC "unrelated keys byte-preserved" é insatisfazível
por round-trip JSON.

E uma convergência que vale registrar: a AC de teste (l.172-173) nomeia
`unittest discover -s .claude/scripts/tests`, que **não é como o CI roda**.
É a mesma classe de defeito que hoje produziu um falso-vermelho no
`release-v1-2-0.sh` e barrou o promote do GA. Duas ocorrências independentes
da mesma armadilha no mesmo dia.

## O que o v2 tem de mudar

1. Reclassificar **L3**; registrar ADR; rodar revisão com VETO do Security
   Engineer; cascata V0-V3 completa.
2. Apagar as duas frases falsas (auditoria l.99-101; "tripwires keep
   attesting" l.184-185).
3. Resolver `--full`: cortar, ou desenhar convivência explícita com
   `settings_tamper_detected` — nunca allowlistando.
4. Fechar a escada: negar escrita direta em `.claude/settings.local.json`,
   deixando night-mode como escritor único.
5. Trocar o ack por algo que modelo não forja (tty/env do processo pai).
6. Especificar o contrato de escrita: lock, temp+rename atômico, read-back,
   snapshot create-only, ordem definida e reconciliação.
7. Derivar o banner de `resolve_settings()`, não do marker.
8. Dar predicado de passa/falha ao W0 e adicionar as sondas faltantes.
9. Enumerar os 8 sites de contagem por nome; incluir `README.pt-BR.md`.
10. Reescrever o rider como cerimônia de 4 fontes.
11. Fixar uma convenção de slug e citá-la por nome.
12. Tratar o adopter (recusar mutar settings não-ignorado).
13. Completar o PLAN-SCHEMA; trocar o runner da AC pela invocação do CI.

## Nota de processo

Este debate era obrigatório e o plano dizia que não era. O plano estaria em
execução agora, com duas afirmações falsas de auditoria e segurança dentro
dele, se o Owner não tivesse pedido debate explicitamente. Isso é evidência
sobre o gate de auto-classificação de nível, não sobre este plano: um plano
que se auto-declara L2 nunca encontra o revisor que descobriria que ele é L3.
