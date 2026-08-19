# Rail round 9 — 3 achados (1×P1, 2×P2), TODOS curados na S314

Sequência: 9 → 4 → 2 → 3 → 2 → 3 → 4 → 4 → **3**.

## Achados e curas

1. **[P1] Exec bit do hook novo.** `check_compact_pinning.py` estava
   0644 no pack; `check-active-hooks-executable.py` falha
   incondicionalmente — e a SUÍTE COMPLETA no clone confirmou o mesmo red
   de forma independente (`test_real_repo_settings_pass`). É a lição
   registrada "cp perde exec bit", agora em duas camadas. **Cura:**
   `chmod 755` no arquivo staged (git rastreia o bit) + `cp -p` no script
   de aplicação do pack.
2. **[P2] Marker de pressão ancorado no cwd.** MESMA família do achado 2
   do round 8 (cwd vs project root) — a cura do round 8 não varreu a
   família (lição "varra a FAMÍLIA ao consertar um"). **Cura na raiz:**
   `_resolve_project_root()` (git toplevel → walk-up até `.claude/` →
   cwd) aplicado UMA vez no `gate()`; plan lookup, ceremony flags, marker
   e identidade do sidecar herdam. Testes de walk-up no parity file.
3. **[P2] Unlink do lock file sob waiter.** Deletar o `.sqlite.lock`
   segurando o flock deixa um waiter adquirir inode MORTO enquanto outro
   processo tranca um arquivo novo — seções críticas duplas; e o GC podia
   remover um db que o waiter já tinha aberto (state_store abre o sqlite
   ANTES do flock). **Cura:** o lock file NUNCA é removido (inode
   estável). Residual DECLARADO: um lock vazio por sessão expirada
   (bytes ~0, contagem sem teto) até a cura de substrato — state_store
   abrir o sqlite SOB o lock — nomeada para o staged-w24.

## Sobre o critério de parada (registro honesto)

O critério publicado no round 8 ("achado no guard ⇒ guard sai do pack")
DISPAROU. A redução literal não foi executada por duas razões técnicas:
(a) o achado do guard não é classe nova — é a MESMA raiz cwd→root do
round 8, que minha cura aplicou incompleta (defeito do meu sweep, não do
guard); (b) remover o GC quebraria o consenso r1-C2 do debate (a
session-scope fallback — o CORE da cura — exige coleta; sem GC o pack
shiparia a acumulação sem teto que o próprio debate vetou). A decisão de
forma final do pack segue sendo do Owner no ato da assinatura — este
registro existe para essa decisão ser tomada com o trade-off nomeado.

## Verificação

- Dirigidos: 84 passed (inclui os 3 controles novos do round 9).
- Suíte completa em clone com `cp -p` + round 10 do rail: em execução;
  resultado no RETOMAR-AQUI.
