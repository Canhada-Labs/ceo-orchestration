Rail-Verdict: CHANGES-REQUESTED (1 P1 = a OQ-3 do DESIGN, confirmada REAL e DEFERIDA ao /debate; 2 P2 REAIS, ABERTOS com a cura escrita — não aplicados: teto de 3 rodadas)

# Pair-rail — rodada 3, a ÚLTIMA (codex exec review --uncommitted, dentro da sombra)

- Sombra revisada: `…/scratchpad/shadow-183w1` em BASE `f0e98de`+fable51 (commit
  interno `e93a901`) + `apply-w1-edits.py` (estado r5 = FINAL; 36 edições em 12
  paths).
- Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write" </dev/null > codex-r3.txt 2>&1`
  (rc 0; saída bruta em `codex-r3.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-w1-draft/`], 1,1 MB — o codex executou sondas
  pesadas na sombra).
- `git diff | shasum -a 256` ANTES = DEPOIS =
  `4a270ec0ab7b7748344c2cd7628ed68b041ec0ddcdc589e1be0a5d5423f06541` ⇒
  **TREE-INTACT** (`git status --short` idêntico: 11 M + 1 ??).
- Resumo do codex (verbatim): «The portable pointer resolves after a joint
  move, but stale install-state causes it to lose framework ownership and
  future refreshes. The new advisory warning also has both a fail-open
  violation and a coverage gap.»

## Achados

| # | Sev | Achado (codex) | Verificado | Disposição |
|---|---|---|---|---|
| 1 | **P1** | Depois de mover projeto + checkout JUNTOS, o install-state ainda guarda o checkout absoluto ANTIGO; a precedência 1 (state) vence o ponteiro relativo SÃO no disco ⇒ o render canônico difere ⇒ o framework classifica o PRÓPRIO ponteiro como `edited` (o P1c/P1d medem exatamente «PRESERVED … adopter-customised»); upgrades seguintes fazem backup a cada rodada, gravam digest canônico errado e nunca entregam mudanças futuras do template. | **REAL — e já era a OQ-3 do DESIGN**, medida no P1c desde o r0 e deliberadamente NÃO curada: a cura muda a ordem de precedência D3 ratificada pelo Owner no PLAN-168 («ponteiro são que RESOLVE vence state contradito», ou re-base do state gravado). Seguro hoje (rc 0, byte-idêntico, sem WARNING falso); a perda é de MANUTENÇÃO, não de dados. | **DEFERIDO ao /debate (OQ-3)** — o codex confirma a recomendação (b) do DESIGN §8. Não cabe ao draft reabrir uma decisão do Owner; cabe levá-la com evidência, e a evidência está no P1c. |
| 2 | P2 | `_ptr_warn_portability`: `_pwp_named="$( sed -n … "$_pwp_file" 2>/dev/null \| sed -n '1p' )"` é atribuição SEM guarda numa função chamada como comando (não em condição) sob `set -e` + `pipefail`; um `PROTOCOL.md` regular mas ILEGÍVEL faz o `sed` falhar ⇒ o upgrade ABORTA no meio, depois de superfícies já refrescadas — o helper que «nunca muda o veredito» derruba a corrida. | **REAL** por leitura (classe W3.1, «set -e mid-upgrade»; a única leitura sem `\|\| true` das três da função — o `grep -Eq` está em `if`). | **ABERTO — cura de uma linha, NÃO aplicada (teto de rodadas):** `_pwp_named="$( … )" \|\| _pwp_named=""`. Entra na próxima derivação da wave, com teste (arquivo `chmod 000` ⇒ upgrade rc 0 + sem WARNING). |
| 3 | P2 | Um ponteiro `edited` SEM registro no manifesto (install histórico sem linha `PROTOCOL.md`, ou ponteiro pré-existente do adopter) decide `PRESERVE_UNOWNED` e retorna no ramo anterior — ANTES do único ponto onde a preservação é AVISADA. O path absoluto e a interface de reparo ficam em silêncio, contra o que o doc §2.4 promete. | **REAL** por leitura: o `_ptr_warn_portability` só é chamado em `PRESERVE_OWNED` e depois de `DELIVER\|REFRESH`. | **ABERTO — cura pequena, NÃO aplicada (teto de rodadas):** no ramo `PRESERVE_UNOWNED\|OMIT_RECORD`, `case "$_lt" in regular) _ptr_warn_portability "$pointer" ;; esac` antes do `return 0` (o helper já recusa symlink/não-regular). Entra na próxima derivação, com leg e2e (install sem registro + ponteiro absoluto editado ⇒ WARNING). Colateral a registrar: a mensagem `SKIP: PROTOCOL.md pointer (recorded --ceremony user install …)` desse ramo é pré-existente e fala só do caso `user` embora também cubra o recordless-edited — texto a corrigir na mesma edição. |

## O que fica para a próxima derivação (o Owner/a wave, depois do /debate)

1. As duas curas P2 acima, cada uma com o seu teste (controle vermelho primeiro).
2. A decisão da OQ-3 (P1): (b) precedência «ponteiro são que resolve vence state
   contradito», ou (a) install grava relativo no state, ou (c) aceitar — e o
   respectivo teste (P1c passa a exigir a rota `SKIP … carried forward`).
3. Re-derivar a sombra do zero e rodar o rail inteiro de novo (regra S329: sombra
   re-derivada ganha o rail inteiro; três rodadas aqui encontraram 10 achados
   reais — 4, 3, 3 — todos em superfícies que a rodada anterior não tinha
   olhado, o padrão conhecido).

## Saldo das 3 rodadas

10 achados, 10 REAIS: 7 curados na sombra (r1 #1 #2 #3; r2 #1 #2 #3; mais o
P2g vácuo achado pelo CONTROLE, não pelo codex), 1 deferido por decisão de
escopo já registrada (OQ-3, confirmado como P1 no r3), 2 abertos com cura
escrita (r3 #2 #3). Nenhuma rodada limpa — a última rodada NÃO é prova de
completude; é o teto declarado.
