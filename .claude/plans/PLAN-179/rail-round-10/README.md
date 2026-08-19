# Rail round 10 — 3 achados (2×P1, 1×P2), TODOS curados na S314

Sequência: 9 → 4 → 2 → 3 → 2 → 3 → 4 → 4 → 3 → **3**.

## Achados e curas (o rail prescreveu; as curas seguem a prescrição)

1. **[P1] GC × conexão SQLite pré-aberta.** O rail escalou o residual
   DECLARADO no round 9: `state_store._ensure_open` roda ANTES do
   FileLock, então o GC (segurando o lock) podia apagar o db por baixo de
   uma conexão já aberta — o commit ia para um inode desvinculado e o
   snapshot sumia. **Cura de raiz:** `state_store.py` entra no pack com
   `_reopen_if_vanished()` como primeira instrução de TODA seção crítica
   (6 sites) — sob o lock a checagem é livre de corrida: se o path some,
   reabre (recria) e a escrita cai no disco. Testes:
   `test_state_store_gc_coordination.py` (controle positivo com conexão
   cacheada + negativo de round-trip intocado).
2. **[P1] Histerese de pressão nunca re-arma.** Produtor PreCompact-only:
   duas compactações no mesmo degrau mantinham previous==current e a
   segunda travessia era suprimida. **Cura:** o PostCompact fecha a
   GERAÇÃO — `audit_emit.clear_context_pressure_marker()` +
   `_clear_pressure_marker(event)` no `gate()` (fail-open, resolve o root
   byte-espelhado do PreCompact). Teste:
   `test_postcompact_rearms_pressure_hysteresis`.
3. **[P2] Starvation por prefixo no sweep.** Ordem de scandir é estável;
   break por deadline caía sempre no mesmo prefixo e a fatia por
   identidade só filtrava o já-alcançado. **Cura:** cursor de RETOMADA
   persistido (`.gc-scan-cursor`, mesmo idioma atômico) — escopos em
   ordem lexicográfica ROTACIONADA a partir do último decidido; teto duro
   anti-DoS no scan. Regressão direta:
   `test_cursor_resumes_past_the_previous_prefix`.

## Suíte completa (clone, pack round-9) — leitura honesta

`SUITE=RED` com 2 fails, ambos explicados e nenhum defeito NOVO do pack:
- `test_committed_doc_in_sync` — drift LEGÍTIMO: o pack registra
  `check_compact_pinning` e o doc derivado não viajava. **Curado:**
  `docs/COMMAND-SKILL-HOOK-MAP.md` regenerado entra no pack (49
  registrations/48 labels).
- `test_diff_size_cap_enforced_with_many_lessons` — **PRÉ-EXISTENTE no
  HEAD vivo** (falha idêntica fora do clone, timeout 30s do subprocess;
  CI Linux do HEAD está success — classe perf local/macOS). Não é do
  pack; não foi tocado.
Os reds do round anterior (exec-bit, demand-resolver) sumiram — o
exec-bit foi confirmação independente do P1 e está curado na fonte
(`chmod 755` no staged + `cp -p` na aplicação).

## Critério de parada FINAL (publicado)

Round 11 com achado novo em GC/pressão ⇒ PARAR: preparar o memo de
redução de escopo para o Owner decidir a forma do pack na assinatura —
sem round 12 autônomo. As curas deste round seguiram a prescrição
explícita do rail (inclusive trazendo `state_store.py` para o pack, a
cura de raiz que os rounds 7/9/10 circulavam).
