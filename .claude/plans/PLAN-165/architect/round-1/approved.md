# PLAN-165 — Owner Sentinel (round 1)

Autoriza **uma** edição canônica em `main`: a remoção do
`disableAutoMode` do `.claude/settings.json` (`p3-remove-disableautomode.patch`).

O arquivo é canonical-guarded e adicionalmente arbitration-kernel — uma
edição feita **pelo Claude** exigiria também `CEO_KERNEL_OVERRIDE` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` no ambiente de lançamento da sessão.
Esta cerimônia é executada pelo **Owner no próprio terminal**, onde os hooks
do harness não interceptam: o sentinel aqui é o registro assinado da
autorização, não uma trava técnica contornada.

Anchor commit `91e690aa1da0ca2a0eb2446bd764240e892b2035` — HEAD de `main` no
momento da preparação (`fix(release-driver): CI-parity test gate +
stable-aware tag trailer`, pós-GA v1.2.0).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 91e690aa1da0ca2a0eb2446bd764240e892b2035
Plans: PLAN-165
Scope:
  - .claude/settings.json
<!-- END SIGNED SCOPE -->

Authorization: assinatura GPG destacada do Owner em `approved.md.asc`,
fingerprint `AE9B236FDAF0462874060C6BCFCFACF00335DC74`. **O `.asc` é gerado
na EXECUÇÃO, não agora** — este arquivo é commitado como preparação; o Owner
assina na sessão de execução. Reescrever este documento invalida qualquer
assinatura anterior e exige reassinar.

## O patch autorizado

`p3-remove-disableautomode.patch` remove `"disableAutoMode": "disable"` e
reescreve o `_posture_comment` que a descrevia.
`permissions.defaultMode` permanece `"manual"`; o bloco `deny` permanece com
as mesmas 24 entradas.

Verifique a integridade antes de aplicar (lição S274 — entrada staged e
gitignored exige manifesto rastreado e conferência fail-closed):

    cd .claude/plans/PLAN-165/ceremony-staged && shasum -a 256 -c MANIFEST.sha256

Reverte a ratificação do PLAN-163 T5.3/OQ5(c). Decisão do Owner, verbatim:
*"o disableautomode já é escolha do usuário usando o shift+tab, não deveria
nunca ter saído — não é o framework que decide isso."*

O efeito observado da chave excede o documentado: além de impedir escalação
automática, ela **remove `auto` do ciclo shift+tab nativo**. O framework
estava retirando uma afordância do Claude Code do próprio operador.

O default fail-closed não muda: toda sessão continua **começando** em
`manual`. O que volta é sair disso deliberadamente, no teclado, só para
aquela sessão.

Medido em 2026-08-03 com a camada de usuário neutralizada
(`CLAUDE_CONFIG_DIR` apontando para dir vazio), projetos de rascunho:

| overlay local | rodapé | Bash `date` | Edit | Write |
|---|---|---|---|---|
| (nenhum) | `manual mode on` | **pediu** | pediu | pediu |
| `acceptEdits` | `accept edits on` | passou | passou | passou |

Superfície de risco da remoção: nenhum teste afirma que a chave existe,
`check_harness_config.py` não a exige, `effective_config.py` não a consome,
e no template ela aparece só dentro de um comentário para adopters. Não
redenna nada e não muda comportamento de adopter.

## Fora deste sentinel — e por quê

### `p1-deny-overlay.patch` — ADIADO, porque não entrega o que promete

O p1 acrescentaria ao `permissions.deny` as entradas
`Edit/Write` para `.claude/settings.local.json`,
`.claude/state/night-mode.json` e `.claude/scripts/night-mode.py`, alegando
fechar a escada de escalação de postura.

**Não fecha.** Um rascunho anterior deste sentinel afirmava que fechava; o
review cross-model (codex, 2026-08-03) contestou e a verificação contra o
código confirmou o codex:

- As entradas de `deny` são **por ferramenta**: negam Edit e Write.
- `check_bash_safety.py` protege escrita via Bash usando
  `_CANONICAL_GUARDS` como chave.
- Os **três** caminhos estão FORA de `_CANONICAL_GUARDS` (verificado
  programaticamente), e o `check_bash_safety.py` não menciona nenhum deles.

Logo, sob `acceptEdits` — onde Bash roda sem prompt — um redirect
(`echo '{...}' > .claude/settings.local.json`) reescreve o overlay mesmo com
o p1 aplicado. O p1 fecharia a porta deixando a janela aberta, e este
sentinel estaria atestando uma proteção inexistente.

O conserto real exige acrescentar os três caminhos a `_CANONICAL_GUARDS`
(`check_canonical_edit.py` — canônico E kernel), o que é uma cerimônia
maior. Fica para depois, com o p1 corrigido.

Consequência aceita ao landar só o p3: a exposição do overlay **continua
exatamente como já está hoje**. Não é regressão — o `deny` nunca cobriu o
overlay. O que muda é que o operador usará `acceptEdits`/`auto` com mais
frequência, então a janela fica mais alcançável. Isso está registrado como
dívida aberta no plano, não como risco fechado.

### `p2-audit-action.patch` — fora de escopo

Registra `night_mode_toggled` em `_lib/audit_emit.py` (arbitration-kernel).
Só tem efeito quando `night-mode.py` existir em `main`. Merece cerimônia
própria no merge do branch; landar agora registraria uma ação que nada emite.
