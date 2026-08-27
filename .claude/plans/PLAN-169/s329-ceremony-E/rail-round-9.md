# Pacote E — rail codex rodada 9 (shadow-E curada do r8, 2026-08-27 ~15:20 -03)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E após a cura do r8 (postura SHARED; unit 80/80; e2e 69/0). Modelo `gpt-5.6`, esforço xhigh. Saída bruta: `<scratchpad 02edd09e>/rail-E-round-9.txt`.

## Achados (todos sobre a postura SHARED introduzida no r8)

- **[P1] Withhold profile-dependent hooks from the shared roster** — hooks e env intersectados em separado: `check_config_protection.py` (nos dois templates) entrava no shared sem o seu interruptor advisory (user-only) ⇒ adopter `user` legado receberia o hook BLOQUEANTE. **REAL** — a dependência hook→setting vive no código do hook, invisível a qualquer interseção de JSON.
- **[P1] Keep unknown-ceremony dry runs read-only** — o branch shared criava `$BAK_DIR/.claude` e escrevia o roster derivado antes do `return` do `--dry-run`. **REAL.**
- **[P2] Validate both templates before deriving** — os guards de documento único/forma só corriam sobre o arquivo derivado; fonte em stream era coerçida via `$b[0]`. **REAL.**

## Disposição

- **Arquitetura trocada** (DESIGN-E §14): cerimônia desconhecida ⇒ NENHUM hook; só as settings que os dois perfis declaram com o MESMO valor; `WITHHELD:` quantificado + `PARTIAL (ceremony unknown)` no sumário (nunca a frase de completude) + opt-in; derivação em `mktemp` com trap `RETURN` (dry-run intocado); artefato de auditoria só no caminho que escreve; as duas fontes validadas antes de derivar.
- Testes: unidade 80 → 82 (`TestUnknownCeremonyRegistersNoHooks`, 11 casos, substitui a classe do r8); e2e 69 → 71 (E.15b invertido; E.15h; E.15i dry-run no-write).
- Próxima rodada: r10 sobre a sombra curada; o SIGN exige que o ÚLTIMO registro seja APPROVE.
