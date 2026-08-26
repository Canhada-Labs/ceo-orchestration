# Rail (codex) — main não-canônico, rodada 3

**rc:** 0 · **saída:** 9682 B · **achados:** 19 (15 P1 + 4 P2) · **veredito literal:** ausente.
**No meu escopo: 1.** Os 6 achados curados nas rodadas 1 e 2 não reapareceram.

A explosão de 6 → 19 achados NÃO é regressão minha: 18 dos 19 são de outros pacotes, e 11 deles são
o mesmo arquivo do rascunho PLAN-185 sendo lido com mais profundidade a cada passada — o padrão que o
CLAUDE.md §5 já nomeia para esse arquivo.

---

## Achado no escopo — 1

### F10 [P2] `profile-opus-4-7.py:695` — o teto de admissibilidade era inclusivo

**Claim:** quando `K` é exatamente igual a `admissibility_max_K`, o controle positivo de +150 ms cai
na igualdade e `hook_p50 <= K * ref_p50` o aceita; a fase 2 concede anistia ao controle positivo em
vez de detectar a regressão.

**Verificação — REAL, e MEDIDA.** O `admissibility_max_K` codifica UMA garantia: na pior referência
observada, uma regressão de +150 ms ainda FALHA. Detecção exige `hook_p50 > K * ref_p50`, logo K
precisa ficar ESTRITAMENTE abaixo de `(baseline+150)/max_ref` — porque a comparação do classificador
é inclusiva. Sonda com baseline 70 / pior referência 50 / cap 4.4:

    K == cap        -> advisory_slow_runner  (rel_ok True)   <- anistia ao controle positivo
    K = cap*0.999   -> real_regression       (rel_ok False)

O float aponta na mesma direção e piora um pouco: `4.4*50 == 220.00000000000003 > 220.0`, então
mesmo a igualdade "exata" é resolvida a favor da aceitação. Por isso a cura **rejeita a igualdade**
em vez de introduzir tolerância — uma tolerância aqui seria mais um número sem evidência.

Esta é a classe que a memória do repo registra como o forte do pair-rail cross-vendor
(`feedback-pair-rail-finds-range-bugs-debate-misses`): bug de FRONTEIRA que a revisão do mesmo LLM
não pega porque compartilha a premissa.

**Cura:** `if k > cap:` → `if k >= cap:`, mensagem passa a dizer `reaches ... (the cap is exclusive)`,
e o docstring do loader (`:658`) corrigido de "that the K exceeds" para "that the K REACHES".

**Testes:** `TestTheAdmissibilityCapIsExclusive` — a MEDIÇÃO acima como asserção executável (se
`K==cap` detectasse a regressão sozinho, rejeitar a igualdade seria aperto gratuito), a rejeição
nomeada, e o anti-vacuidade de que `K` abaixo do cap segue aceito (o teto tem de continuar fronteira,
não virar rejeição em bloco).

**Controle positivo:** `>=` revertido para `>` ⇒ **1 failed, 2 passed** — cai exatamente o teste de
igualdade, e o teste de medição segue verde (ele descreve o classificador, não o loader).
Restaurado.

---

## Estado dos testes

`test_hook_latency_relative_gate.py` — **59 passed, RC 0** (42 originais + 17 acrescentados nas 3
rodadas).

---

## Fora de escopo — encaminhar

### PLAN-185 W0 (rascunho untracked) — 12 achados, TODOS da mesma classe

O rail leu o `check-installer-write-safety.py` mais fundo e devolveu **11 P1 + 1 P2**, todos
"fail-open por forma não modelada". Vale como EVIDÊNCIA para a 4ª passada INVERTIDA já decidida pelo
Owner, não como lista de correções pontuais — o próprio volume (8 → 7 → 9 → 10 → 12 em passadas
sucessivas) é o argumento de que a arquitetura do matcher é que está errada.

- `:1230-1232` `sed \` com script em linhas seguintes: `logical_line()` retorna cedo (aspas
  balanceadas na 1ª linha) e as continuações não têm o token `sed` — **já esconde substituições cruas
  em `scripts/_grok_harness.sh:112-115`** (é o único destes com sítio vivo nomeado).
- `:999-1000` cap de 10 candidatos de escrita por operando: o 11º (um `cp` incondicional) some e o
  sítio vira `nao-aplicavel`; atingir o cap deveria ser `indeterminado`.
- `:608-611` `[[ -e "$d" ]] && cp "$a" "$d" || cp "$b" "$d"`: para no 1º destino e ignora o `cp` de
  fallback.
- `:785-789` prefixos de comando: `command cp "$src" "$dst"` é lido com `command` como nome.
- `:570` `if ! test -e "$dst"` (a variante `! [` já viera na rodada 1): o texto antes de `-e` termina
  em `! test` e a negação não é vista.
- `:522-524` qualquer `return` aninhado marca `then_jumps=True`, mesmo sob outra condição.
- `:1080-1085` guard creditado sem DOMINAR a escrita (um `[ -L "$dst" ] && return` dentro de um `if`
  anterior credita uma escrita posterior).
- `:827-830` guard creditado por NOME (repetido da rodada 1, agora com exemplo: `_symlink_notice`
  que só avisa e retorna 0).
- `:1196-1202` `_escape_class_covers()` não olha o lado da SUBSTITUIÇÃO: o no-op `sed 's/[|&\\]/&/g'`
  passa por escaping.
- `:1371` só a 1ª substituição define o delimitador: em `sed "s|x|ok|g; s/x/$B/g"`, `$B` é checado
  contra `|`.
- `:1435-1441` definição alcançante escolhida lexicalmente, sem fluxo de controle.
- `[P2] data/installer-write-safety-baseline.txt:40` — **3ª repetição**: falta
  `scripts/upgrade.sh:3727`, então o censo nasce vermelho e não serve de catraca.

### PLAN-179 staged-w24 (pacote D) — 4 achados

- `[P1] .claude/settings.json:353-356` — a registração nova sobe as contagens dogfood/template de
  49/46 para 50/47 e `test_template_dogfood_parity.py` ainda fixa 49/46; o V4 do LAND falha de forma
  determinística.
- `[P1] templates/settings/settings.base.json:214-217` — para adopter EXISTENTE o hook não é ativado:
  `scripts/upgrade.sh:_merge_lifecycle_hooks_into_settings` fixa seis registrações e não tem entrada
  para `check_ledger_checkpoint.py`; o upgrade instala o script e o deixa desligado.
- `[P2] check_ledger_checkpoint.py:399-403` — `--pathspec-from-file=file` é consumido como opção de
  valor comum, `inv.pathspecs` fica vazio e `_committed_paths()` olha o staged inteiro.
- `[P2] _lib/audit_emit.py:7188-7195` — `emit_generic("ledger_entry_rejected", decision="accept",
  reason="ok")` passa pelo scrub: evento assinado cuja ação diz rejeitado e cujos campos dizem aceito.

### `OWNER-S328-MORNING.sh` (pacote da manhã) — 2 achados

- **`[P1] :390-392` — pode DESTRUIR uma edição legítima.** Quando `docs/threat-model.md` é a única
  edição não-staged e ela muda `stale` → `accepted`, o predicado também dá true e o `_tree_check()`
  roda `git checkout --` em cima. O auto-heal deveria ser restrito à direção gerada pelo checker
  (`accepted` → `stale`). Encaminhado com prioridade: é o único achado desta rodada que perde
  trabalho do Owner.
- `[P2] :892-897` — a mensagem promete `Validate` verde depois do pacote B, mas o
  `PLAN-169/s328-ceremony-B/README-B.md:88-97` diz que a fase 1 só publica a métrica relativa e
  preserva os exit codes; se o gate absoluto seguir acima do limiar, a CI continua vermelha e o
  script dá ao Owner a expectativa oposta.

## Encaminhamentos para canônico

Nenhum vindo do meu escopo. (O `upgrade.sh:_merge_lifecycle_hooks_into_settings` do achado
staged-w24 É canônico, mas pertence ao pacote D.)
