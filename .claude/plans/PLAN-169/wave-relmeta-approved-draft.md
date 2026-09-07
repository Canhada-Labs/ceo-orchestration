# wave-relmeta — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` — land por PATCH.
> O bloco `Scope:` é **DERIVADO** por
> `s349-ceremony-relmeta/finalize-relmeta.sh` a partir de
> `git apply --numstat`, nunca escrito à mão, e o `OWNER-RC1-META-SIGN.sh`
> **regenera e compara byte a byte antes de pedir a assinatura** (a classe
> CM-10 do corpus S348: hoje só o LAND confere, e isso é depois de o Owner
> já ter assinado). O `Anchor-SHA` é preenchido no momento da assinatura; o
> `OWNER-RC1-META-LAND.sh` aborta se o HEAD tiver andado. Reescrever um byte
> deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-169
Wave: wave-relmeta (PLAN-169 — destrava o corte da **v1.4.0-rc.1**)
Patch: .claude/plans/PLAN-169/s349-ceremony-relmeta/RELMETA.patch
Patch-sha256: TO-FILL-BY-FINALIZE
Patch-base: TO-FILL-BY-FINALIZE
Anchor-SHA: TO-FILL-BY-SIGN
Data: TO-FILL-BY-SIGN
Approved-By: TO-FILL-BY-SIGN

## Por que esta wave existe

`release.sh` carrega um bloco `PER-RELEASE` com a versão **hardcoded em
1.3.0**. Com ele, `release.sh preflight --rc 1` morre em
`tag v1.3.0-rc.1 already exists`: o driver não consegue mirar a v1.4.0.
Trocar esse bloco é uma edição de **membro do manifesto ADR-192**
(`.claude/governance/gate-scripts-manifest.txt`), e o manifesto é
**canônico** — o oráculo `check_canonical_edit.py --is-canonical` responde
`1` para ele e `0` para o `release.sh`. As duas metades só são verdadeiras
juntas: um `release.sh` novo com o sha antigo no manifesto derruba os
quatro workflows que conferem o manifesto. Logo: **uma assinatura, três
arquivos.**

## O que entra (dois arquivos, ambas as edições DERIVADAS)

1. **`.claude/scripts/local/release.sh`** (livre pelo oráculo; MEMBRO do
   manifesto ADR-192) — o bloco `PER-RELEASE` inteiro passa a mirar
   `1.4.0`. `RELEASE_SCOPE` é derivado de `git log v1.3.0..HEAD` (os planos
   CITADOS nos assuntos de commit) mais o conjunto de ADRs tocados na mesma
   faixa. Os ADRs entram **listados**, nunca como faixa `primeiro -> último`:
   o conjunto real é esparso e uma faixa afirmaria o que não aconteceu.
2. **`.claude/governance/gate-scripts-manifest.txt`** (CANÔNICO) — a linha
   de `release.sh` é re-pinada com o sha256 do arquivo **depois** da edição
   1. O aplicador computa o sha do texto novo e, após escrever, reconfere
   contra o arquivo em disco.
## O que NÃO entra, e por quê

**`CHANGELOG.md` não é tocado.** A seção `## [1.4.0]` e o rótulo
`as of v1.4.0` do preâmbulo foram landados pelo pacote de docs da release
em `e242544`. Escrever de novo colidiria com o trabalho de outro pacote, e
uma segunda seção `## [1.4.0]` seria ambiguidade, não aprovação. O
aplicador trata o CHANGELOG como **pré-condição conferida**: exige
exatamente uma seção, o rótulo na versão alvo, e as quatro contagens do
preâmbulo batendo `verify-counts.sh --json`. Um CHANGELOG que não chegou
ainda é recusa nomeada, nunca uma escrita silenciosa por cima.

## O que esta wave NÃO faz

- Não corta tag, não commita bump de versão, não empurra nada para o npm.
  Depois deste land o Owner roda `OWNER-RC1-CUT.sh`, que faz o
  `preflight`/`bump`/`tag` pelo driver.
- Não toca em `.claude/governance/codex-cli-pin.txt` nem em
  `codex-cli-pin-manifest.json`. O re-pass roda na versão **pinada** (0.147.0
  via `npx`), sem alterar o `codex` global da máquina, que está em 0.153.4 —
  fora da faixa `>=0.128.0,<0.148.0`.
- Não altera `_release_bump_sites.py`, `_release_tag_guard.py`,
  `validate-pair-rail-verdict.py` nem `release.yml`.

## Recuperação

Se o LAND abortar depois de aplicar o patch, ele reverte os três alvos pelo
`EXPECTED-BASELINE.txt` (hashes PRE-edição gravados pelo `finalize`) e sai
não-zero com o motivo nomeado. Se abortar **depois** do commit local, o
commit fica local e a mensagem é impressa: nada foi empurrado.

Scope:
TO-FILL-BY-FINALIZE
