# Rail (codex) — main não-canônico, rodada 1

**Comando:** `codex exec review --uncommitted </dev/null --output-last-message <SP>/railmain-1.txt`
**Base:** `main` @ `560dad0`, árvore de trabalho suja (S328).
**rc:** 0 · **saída:** 4297 B · **achados:** 7 (5 P1 + 2 P2) · **veredito literal:** ausente
(o formato de saída desta versão do `codex-cli` — 0.147.0 — entrega prosa + lista de comentários,
sem a linha `VERDICT:`. Registrado como tal; a parada exige o literal, então esta rodada NÃO é
parada.)

**Pré-condição cumprida antes de rodar:** a leg H.27 (`test-upgrade-historical-adopter.sh`,
outro agente) fechou com `RESULT: 148 passed, 0 failed`, e o arquivo ficou 3 min sem mudança de
mtime (`1787682609`). Espera total 960 s.

---

## Achados no escopo — 4

### F4 [P1] `check_contamination.py:382-391` — ledger protegido indecodificável era fail-OPEN

**Claim:** um `LEDGER.md` com um único byte UTF-8 inválido é silenciosamente pulado inteiro,
inclusive um handle em outro ponto do arquivo; a exceção deny-wins nova nunca chega a rodar.

**Verificação — REPRODUZIDA.** Sonda (`<SP>/probe-f4.py`): ledger com `\xff` na linha 1 e o
marcador em UTF-8 válido duas linhas abaixo ⇒ `scan()` devolveu `[]`. O `except UnicodeDecodeError:
continue` em `check_contamination.py:388` executa antes de qualquer casamento de padrão.

Real, e da classe exata que a exceção existe para fechar: estes arquivos são anexados pela máquina
mid-sessão e **ninguém os lê antes do commit**, então "o guard não conseguiu parsear" não pode ler
igual a "o guard não achou nada". CLAUDE.md §4: input não-parseável em matcher de segurança é
fail-CLOSED.

**Cura** (`check_contamination.py`): no braço `UnicodeDecodeError`, `if is_never_allowlisted(rel):
violations.append(path)` antes do `continue`. O braço `OSError` acima fica fail-OPEN de propósito —
arquivo ilegível é INFRAESTRUTURA, e a doutrina separa os dois. Docstring do módulo + as duas linhas
de "Allowed zones" do `main()` nomeiam o motivo.

**Testes** (`test_check_contamination_ledger_exception.py`): classe
`TestAnUndecodableProtectedLedgerFailsClosed`, 4 casos que falham por razões diferentes — (1) o
positivo, que é a reprodução; (2) ledger indecodificável SEM marcador também é reportado (a regra é
parseabilidade, não o marcador); (3) irmão `notas.md` no mesmo diretório com os mesmos bytes segue
isento; (4) arquivo não-plan indecodificável segue pulado — este é o que prova que o fail-closed
**não vazou** para fora da classe. Helper `commit_bytes` acrescentado à base (o `write_text` do
`commit` recusaria o byte).

**Controle positivo:** cura neutralizada (1 âncora, `assert count==1`) ⇒ **2 failed, 15 passed** —
exatamente os 2 casos fail-closed, com os 2 controles negativos permanecendo verdes. Restaurado.
`RC=0` / 17 passed, 1 skipped com a cura.

### F5 [P1] `profile-opus-4-7.py:1103-1109` — returncode da referência descartado

**Claim:** falha rápida da referência (import/FS/setup) vira amostra curta e estável, `ref_valid=true`,
envenenando K da fase 2 ou concedendo anistia.

**Verificação — REAL, por leitura.** `_run_ref` chamava `subprocess.run(...)` sem atribuir o
resultado; só `TimeoutExpired` era tratado. A trilha do HOOK, no mesmo arquivo (`:1089`), tem
exatamente esta disciplina desde o pair-rail S265 P2 (`if res.returncode != 0: entry_hook_failed =
True`) — a trilha da referência simplesmente não a recebeu. Direção do dano confirmada na leitura do
desenho: K_e é fixado de `max(hook_p50/ref_p50)`, então um `ref_p50` minúsculo fixa K enorme e compra
anistia ampla depois (o rail acertou o efeito, via fase 2).

**Cura:** `entry_ref_failed` (mesmo idioma `nonlocal` do `entry_hook_failed`), `res.returncode != 0`
⇒ True; parâmetro novo `ref_failed` na função PURA `_classify_entry`, checado PRIMEIRO — forma não é
proveniência: um crash rápido passa em todos os testes de forma (finito, positivo, drift baixo).
`ref_failed` publicado em `stats` e registrado em `_SECOND_KEY_ENTRY_KEYS` (o exit 5 passa a ter
NOME; `ref_valid=false` sozinho não distingue mal-formado de nunca-rodou).

**Testes:** `TestAFailedReferenceIsNotAMeasurement` — unit no classificador + gêmeo anti-vacuidade
(mesmos números, `ref_failed=False` ⇒ `pass`), mais 2 de INTEGRAÇÃO sem sampler (o sampler devolve
float e nunca spawna, logo não exercita a fiação): `_REF_EXEC_SOURCE` trocado por `sys.exit(1)` ⇒
`ref_failed=True`/`ref_valid=False`/contended nas 5 entradas; e o controle de que a referência
SHIPADA sai 0.

**Controle positivo:** removida a checagem de returncode ⇒ **1 failed** (`test_a_real_nonzero_
reference_process_reaches_the_verdict`, em `assertIs(stats["ref_failed"], True)`), 3 passed.
Restaurado.

### F6 [P2] `profile-opus-4-7.py:1341` — um typo armava a fase 2 do run inteiro

**Claim:** K file só com nome desconhecido ⇒ `k_by_entry` não-vazio, todo `K_e=None`, fase 2 armada,
exit 1 da fase 1 podendo agregar para `pass`/exit 0.

**Verificação — REAL.** `any_enforced = bool(k_by_entry)` (`:1341`); `_load_relative_k_source`
(`:641`) valida forma mas não conhece os nomes do corpus. E o docstring do próprio loader declara o
contrato violado: *"Every rejection is NAMED in `warnings` and degrades that entry (or the whole
file) back to PHASE 1 — never to a silently wider gate."*

**Cura:** filtro logo antes de `for entry in corpus:` (primeiro ponto onde os nomes existem):
`set(k_by_entry) - {e["name"] for e in corpus}` ⇒ warning `relative_k_unknown_entry[<nome>]` + `pop`.
Escolhida a rota "rejeitar o nome" das duas que o rail ofereceu: ela também pega o caso de 5 typos
entre 6 nomes, que "exigir ≥1 K aplicado" deixaria passar.

**Testes:** `TestAKFileMayOnlyNameRealEntries` — nome desconhecido é dropado E nomeado; o buraco em
si (`hook=400ms`, K file só com typo ⇒ `phase == "1-advisory"` e `rc == 1`); anti-vacuidade (nome
conhecido + typo ⇒ `2-enforcing`, `K_e` preservado).

**Controle positivo:** filtro removido ⇒ **2 failed, 1 passed** (o anti-vacuidade segue verde, como
deve). Restaurado.

### F7 [P2] `profile-opus-4-7.py:1124-1131` — self-cap podia estourar ~300 s

**Claim:** com `i % _WALL_CHECK_EVERY == 0` e até 30 s por iteração, uma checagem logo abaixo do
self-cap de 378 s podia ser seguida de centenas de segundos sem checagem, deixando o timeout externo
de 420 s matar o processo antes do resultado estruturado — o rc124 que o cap existe para tornar
inalcançável.

**Verificação — REAL, e MEDIDA.** Aritmética confirmada na leitura; o discriminante foi medido no
controle positivo abaixo.

**Cura:** checagem em TODA iteração (o `i % 10` sai) e uma segunda checagem entre a amostra do hook e
a trilha da referência da MESMA iteração — com o hook já pago, é o último lugar onde o estouro ainda
cresce. Pior caso vai de ~300 s para ~10 s. `_wall_blown()` é uma subtração de `perf_counter`; pagá-la
200× em vez de 20× é microssegundos contra um orçamento de 180 ms. `_WALL_CHECK_EVERY` ficou sem uso
e foi REMOVIDA (constante morta é o que a próxima rodada sinaliza), com um comentário no lugar
dizendo por que não há stride.

**Testes:** `TestTheWallIsCheckedEveryIteration` — stub de `perf_counter` normal nas 2 primeiras
chamadas (`t_gate_start` e a checagem por-ENTRADA no topo do laço do corpus; se essas estourassem,
nenhuma entrada seria medida e o teste não provaria nada) e muito além do wall depois. Asserção sobre
`wall_exceeded` sozinha seria VACUOSA — ela já era True antes da cura; o discriminante é a CONTAGEM de
amostras depois do relógio estourar. Mais o controle de relógio saudável (corpus inteiro, `_ITERATIONS`
amostras, `wall_exceeded` False).

**Controle positivo:** stride 10 replantado ⇒ **`AssertionError: 10 != 1`** — o estouro pré-cura era
exatamente o previsto. Restaurado.

---

## Fora de escopo — encaminhar

Os três são do rascunho **PLAN-185 W0** (untracked, pré-existente; a task nomeia esse tree como de
outro dono). NÃO tocados. Todos são da MESMA classe que o CLAUDE.md §5 já registra para esse arquivo
— *fail-open por forma não modelada* — e portanto são **evidência adicional para a 4ª passada
INVERTIDA** já decidida pelo Owner (enumerar as formas PROVADAS seguras; o resto é `indeterminado`),
não itens a curar um a um:

- `[P1] .claude/scripts/data/installer-write-safety-baseline.txt:40` — o checker reporta
  `scripts/upgrade.sh:3727` (`sed-interp`, fingerprint `17e1bdbce06a9384`) e o baseline não o tem, então
  os dois testes de baseline do próprio rascunho estão vermelhos.
- `[P1] .claude/scripts/check-installer-write-safety.py:570` — negação em nível de COMANDO
  (`if ! [ -e "$dst" ]`) não é reconhecida: o texto antes de `-e` termina em `! [`, a condição é lida
  como não-negada e a escrita é classificada inalcançável.
- `[P1] .claude/scripts/check-installer-write-safety.py:827-830` — qualquer comando cujo NOME contenha
  `symlink`/`nofollow`/`lstat`/`deref` é creditado como guard sem inspeção do corpo.

## Encaminhamentos para canônico

Nenhum. As 4 curas desta rodada ficaram todas em arquivos não-canônicos do FILE ASSIGNMENT.
