# Pacote E — rail codex rodada 11 (shadow-E curada do r10, 2026-08-27 ~16:40 -03)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E após a cura do r10 (guard de `.env` do template; unit 84/84; e2e 71/0). Modelo `gpt-5.6`, esforço xhigh. Saída bruta: `<scratchpad 02edd09e>/rail-E-round-11.txt`.

## Achados

- **[P1] Provide signed authorization for guarded edits** — sentinel `TO-FILL-AT-SIGN`, sem `.asc`. **Por construção** (estado pré-SIGN); disposto como nas rodadas 2, 3 e 7.
- **[P2] Route the shared-roster tempfile through `_up_tmpbase`** — com `TMPDIR` dentro do `$TARGET`, o `mktemp` da postura SHARED escreveria no adopter (inclusive em `--dry-run`); o helper `_up_tmpbase()` existe exatamente para isso. **REAL.**
- **[P2] Avoid interpolating temp paths into the RETURN trap** — `trap "rm -f '$path'" RETURN` re-parseia o path na execução; apóstrofo no `TMPDIR` aborta sob `set -e`, path forjado injeta. **REAL.**
- **[P2] Reject non-single-document settings before merging** — `settings.json` vazio ou stream de vários objetos passa pelo jq: vazio ⇒ «already present» falso; stream ⇒ `mv` instala arquivo que consumidores JSON comuns não leem. **REAL.**

## Disposição

- **CURADOS na sombra** (DESIGN-E §16): `mktemp "$( _up_tmpbase )/…"`; trap com corpo FIXO (`trap 'rm -f -- "$_UP_SHARED_TPL_TMP"' RETURN`, variável global expandida na execução — semântica do trap `RETURN` sobre globais verificada); guard de documento único sobre `settings.json` antes do report (vazio/stream ⇒ NOTE nomeada com a contagem, PRESERVADO; JSON inválido mantém a mensagem antiga «malformed settings.json»).
- Testes: unidade 84 → 88 (`TestSettingsMustBeExactlyOneDocument`: vazio e stream de 2 recusados e nomeados, intocados; `TestScratchStaysOutsideTheTarget`: com `TMPDIR` dentro do `$TARGET`, o `--dry-run` de cerimônia desconhecida não deixa nada no adopter — usando o `_up_tmpbase` REAL extraído do `upgrade.sh`; e a função chama `_up_tmpbase`, com o trap sem interpolação).
- Próxima rodada: r12 sobre a sombra curada; o SIGN exige que o ÚLTIMO registro seja APPROVE.
