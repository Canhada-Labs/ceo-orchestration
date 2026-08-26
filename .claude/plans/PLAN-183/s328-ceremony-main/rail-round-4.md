# Rail (codex) — main não-canônico, rodada 4

**rc:** 0 · **saída:** 3080 B · **achados:** 5 (1 P1 + 4 P2) · **veredito literal:** ausente.
**No meu escopo: 1.** Nenhuma cura das rodadas 1-3 reapareceu.

Tendência dos achados: 7 → 6 → 19 → 5; no meu escopo, 4 → 2 → 1 → 1.

---

## Achado no escopo — 1

### F11 [P2] `profile-opus-4-7.py:1280` — `--exec-reference` sozinho publicava um "pass" falso

**Claim:** com `--exec-reference` mas sem `--relative-advisory`, os rótulos são computados e nunca
armazenados, então a agregação vê lista vazia e publica `verdict_label="pass"` mesmo quando toda
entrada estoura o p95 e o MESMO relatório traz `passed=false` e `exit_class=1`.

**Verificação — REPRODUZIDA, e o resultado é cru.** Run com sampler de 400 ms por hook (todas as 5
entradas acima do teto de 180 ms), só `exec_reference=True`:

    passed            = False
    verdict_label     = pass
    exit_class        = 1
    phase             = 1-advisory
    labels por entrada: [None, None, None, None, None]

Um único documento JSON afirmando as duas coisas. Os rótulos por entrada só são gravados sob
`if relative_advisory or relative_k_source:`, e essa combinação de flags é suportada — o CLI expõe
`--exec-reference` de forma independente. Quem lê o rótulo recebe o oposto do exit code.

**Cura:** o fallback de lista vazia deixa de ser o literal `"pass"` e passa a seguir a chave
ABSOLUTA: `("pass" if passed else "real_regression")`. Sem rótulos, a chave absoluta é a única que
rodou — que é exatamente o que "fase 1" significa —, então o rótulo passa a reportar o que ela
decidiu. O override de `wall_exceeded` continua depois e não muda.

**Testes:** `TestTheTopLevelLabelNeverContradictsTheExit` — o modo com os rótulos por entrada
comprovadamente `None` (senão o teste não estaria medindo este modo), mais o INVARIANTE dito
diretamente em duas direções (`_LABEL_EXIT_CLASS[label] == 0` sse `exit_class == 0`), mais o
anti-vacuidade de que um run saudável segue `pass`/0.

**Controle positivo:** fallback revertido para o literal ⇒ **2 failed, 1 passed**, com a falha
nomeando `label 'pass' disagrees with passed=False`; o anti-vacuidade segue verde. Restauração
conferida byte-a-byte (`cmp`).

*(Nota de método: a 1ª tentativa de plant construiu a âncora com `repr()` e produziu aspas simples;
o `assert count == 1` acusou 0 e o teste rodou contra o arquivo CURADO — 3 passed. Aquele verde NÃO
era controle e foi descartado. O plant foi refeito ancorando por FAIXA DE LINHAS a partir do token
abridor, com asserção de unicidade.)*

---

## Estado dos testes

`test_hook_latency_relative_gate.py` — **62 passed, RC 0**.

---

## Fora de escopo — encaminhar

### PRIORITÁRIO — consequência direta de uma cura minha

- **`[P2] PLAN-169/s328-ceremony-B/B.patch:204-208`** — o payload do ADR (CANÔNICO) diz que a
  implementação ainda admite `K == cap` e que a fase 2 fica com uma precondição não atendida. Isso era
  verdade até a rodada 3; **deixou de ser**: o profiler agora rejeita `k >= cap`
  (`.claude/scripts/profile-opus-4-7.py:706`) e testa a fronteira. Landar o pacote B como está
  ASSINA um registro de decisão que contradiz o código que ele governa. O `B.patch` não está no meu
  FILE ASSIGNMENT — encaminhado ao dono do pacote B, que precisa reescrever esse parágrafo antes da
  assinatura do Owner.

### PLAN-185 W0

- `[P1] data/installer-write-safety-baseline.txt:40` — **4ª repetição** (`scripts/upgrade.sh:3727`,
  fingerprint `17e1bdbce06a9384`, ausente do baseline ⇒ checker sai 1 e dois testes de `TestLiveCorpus`
  falham). Aparece em todas as 4 rodadas; é o achado mais estável do conjunto fora de escopo.

### PLAN-179 staged-w24 (pacote D)

- `[P2] check_ledger_checkpoint.py:492-496` — opções de wrapper SEPARADAS: em `stdbuf -o L git commit
  -m x` o laço pula `-o` e trata `L` como o comando, então `parse_git_commit()` devolve
  `is_commit=False`; o commit não gera checkpoint nem evento de skip e some do denominador da
  observação. `env -C /tmp git commit ...` tem o mesmo problema. (Complementa o achado `:470-472` da
  rodada 3: lá eram as opções JUNTAS, aqui as separadas — mesma classe.)
- `[P2] check_ledger_checkpoint.py:984` — `_emit()` só acrescenta `session_id` e
  `audit_emit.emit_generic()` não sintetiza `project`, mas o contrato v2.59 lista `project` para as
  duas ações (`spec-v1-audit-log.schema.md:502`); as linhas emitidas ficam incompletas para consumidor
  que valida ou funde logs por projeto.

## Encaminhamentos para canônico

Nenhum vindo do meu escopo. O `B.patch` acima É canônico e está encaminhado.
