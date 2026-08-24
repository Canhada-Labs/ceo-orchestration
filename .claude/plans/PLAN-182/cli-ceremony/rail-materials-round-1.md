# Pair-rail — materiais de cerimônia (árvore viva), rodada 1 (S326, 2026-08-24 15:32–15:52Z)

**Instrumento:** `codex exec review --uncommitted` na árvore VIVA — pedido pelo Stop-hook
("RISKY DIFF" nos scripts de cerimônia). Escopo revisado: `OWNER-S326-SIGN.sh`,
`OWNER-S326-LAND.sh`, `wave-cli-approved.md`, `cli-ceremony/*.md` e — porque também estava
não-commitado — o censo do PLAN-185 W0 escrito pelo agente `sec-185-w0`
(`.claude/scripts/check-installer-write-safety.py`).

**Resumo do revisor (verbatim):** *"The new security census has multiple reproducible
false-negative paths and can bless an empty or partially unreadable corpus. The ceremony land
script also fails to recognize several repository-defined canonical surfaces."*

## Sobre os materiais da cerimônia (este pacote)

| # | Sev | Achado | Verificação | Disposição |
|---|---|---|---|---|
| 1 | P1 | `OWNER-S326-LAND.sh` G0: a lista de prefixos "guardados" é um ESPELHO incompleto de `_CANONICAL_GUARDS` — `.github/CODEOWNERS`, `scripts/install-npm.sh`, `scripts/_hash_lib.sh`, `.claude/team.md` sujos caíam em "toleradas" e o land reportava OK misturando edição canônica não-assinada. | **CONFIRMADO** (o espelho veio do `OWNER-S321-LAND.sh`; o oráculo já existe e o próprio template grok o usa como `--is-canonical -`). | **CURADO:** G0 chama `check_canonical_edit.py --is-canonical <path>` por path sujo e lê `path\t0|1`; resposta diferente de `0|1` ⇒ ABORTA (fail-closed). |

## Sobre o censo do PLAN-185 W0 (fora deste pacote — devolvido ao agente)

Oito achados (6× P1, 2× P2), todos sobre falsos-negativos de um matcher de SEGURANÇA que deve
falhar fechado (AGENTS.md:23): janela predicado→escrita de 25 linhas em vez da função inteira;
tabela-verdade invertida para `[[ ! -e ]]` / ramo `then`; `guard_hit` por mera menção textual de
`-L`/`readlink`; `sed 's/x/'"$V"'/g'` (spans de aspas adjacentes) não parseado; escape upstream
sem o delimitador ativo e sem "última definição alcançável"; arquivo `.sh` ilegível silenciosamente
excluído; `mv` contado como escritor através de link pendente (não é); `--write-baseline` aceita
censo vazio. **Disposição:** encaminhados ao agente `sec-185-w0` como segunda passada obrigatória
antes de qualquer commit do censo; o censo NÃO entra na cerimônia `wave-cli`.
