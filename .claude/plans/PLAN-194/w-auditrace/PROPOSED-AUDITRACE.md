# PROPOSED — cura da corrida no gravador do `agent_spawn` (PLAN-194, pacote canônico `w-auditrace`)

Estado: **PROPOSTO** (montado na noite S361→S362; nada assinado). O texto assinável é o sentinel
`.claude/plans/PLAN-194/wave-auditrace-approved.md`; este arquivo é o mapa do pacote para o CEO e o
Owner e não é assinado.

## O pacote

| Caminho | Oráculo | Papel |
|---|---|---|
| `.claude/hooks/audit_log.py` | 1 (canônico) | a cura (`append_entry`) e o auxiliar do marcador de rotação |
| `.claude/hooks/tests/test_two_writer_chain.py` | 0 | censo por AST, janela leitura→anexo, estouro de trava, rotação, corrida entre processos |
| `.claude/hooks/tests/test_audit_log.py` | 0 | o teste de rotação passa a esperar o marcador como linha 1 |

- 3 caminhos, 399 linhas alteradas (+375 −24): dentro do teto da regra de WIP (≤ 400 linhas, ≤ 8 paths).
- Base pinada: os blobs pré-imagem do `index` do patch — os de `main` desde `6a9abb10`, sem mudança até
  `399efbaa` (`--check-base 399efbaa` = OK; `--check-base REV` confere qualquer revisão).
- O conteúdo novo foi escrito em `staged/<caminho original>` (diretório ignorado pelo `.gitignore`,
  regra `staged/`, convenção S238: árvore de staging nunca é commitada; a cópia fica na sombra e no
  checkpoint do builder); `auditrace.patch` é a derivação dela sobre a base
  (`derive-auditrace-patch.sh`, flags pinadas) e é o portador commitado dos bytes, como no molde do
  FN-04. O SIGN confere a pré-imagem do patch contra o HEAD e a pós-imagem depois de aplicar.

## O que muda no código

Dentro de `with FileLock(paths["lock"], timeout=2.5)`, nesta ordem: `rotate_if_needed` (como antes) →
se rotacionou, `_emit_rotation_marker_under_lock` (chama `audit_emit._emit_chain_reset_marker_under_lock`,
o mesmo auxiliar do emissor e do drain) → `get_or_create_key()` → `read_prev_hmac()` →
`compute_entry_hmac` → serializa → append + fsync → chmod 0600 → `write_last_hmac`. Fora da trava fica
só `from _lib import audit_hmac`. No estouro da trava, o breadcrumb serializa a linha sem HMAC. Se o
auxiliar do marcador não grava o marcador (devolve `None` ou levanta), a linha do `agent_spawn` sai SEM
HMAC (`hmac_error` = `chain_reset_marker_missing`) e o `audit-log.last-hmac` fica como o auxiliar o
deixou (no caso em que o anexo do marcador falha, ele já gravou ali o HMAC do marcador e não o restaura).

## Rodada 1 do rail (Codex 0.156.1, REQUEST-CHANGES) — o que mudou

- **P1, marcador que falha no meio:** a frase do sentinel («encadeada no que `audit-log.last-hmac` tiver
  (a gênese)») era falsa. Cura no `audit_log.py`: `_emit_rotation_marker_under_lock` devolve se o marcador
  está no disco, e sem marcador o `append_entry` não assina a sua linha. Teste novo
  `test_marker_append_failure_leaves_this_line_unchained` (falha de E/S injetada no anexo do marcador,
  depois de o auxiliar gravar o sidecar): reprova sobre a pós-imagem da rodada 1 e passa agora. O estado
  que o auxiliar deixa é do `audit_emit.py` (canônico, não tocado): declarado como residual.
- **P2, censo por nome de chamada:** o módulo passa a ser gravador quando NOMEIA uma primitiva de escrita
  de qualquer forma (chamada, atributo, nome, `import`, texto literal); controles sintéticos novos:
  primitivas só por apelido e leitura por `getattr`.
- **P2, intercalação por `session_id`:** a guarda passa a exigir ao menos 2 trocas de TIPO
  (`agent_spawn` ↔ `debate_event`), com controle negativo de blocos segregados; no modo spool, cada
  emissor drena a cada 3 emissões (como um processo de hook ao sair) — 10/10 rodadas verdes.

## Rodada 2 do rail (Codex APPROVE «NENHUM ACHADO»; 2 refutadores Claude APPROVE com 17 P2) — o que mudou

Curado (patch re-derivado; só testes e uma docstring do `audit_log.py` mudaram nos 3 caminhos):
- `TestReadToAppendWindow` passou a `serial`; o filho sinaliza que vai tomar a trava e só então corre a
  janela de 1,0 s (antes: 1,5 s contados do sinal de partida, sob `-n auto`). Segue vermelho sobre o
  código anterior e verde sobre o novo.
- Docstring de `_emit_rotation_marker_under_lock`: o motivo vale para o caso da falha do anexo, não
  para todo retorno sem marcador.

Curado no SIGN e no harness (fora do patch):
- Tolerância ZERO para falha de qualquer id dos arquivos da cura, nas duas passadas, sem rerun (T18).
  A falha instável que o T2 injeta foi para fora dos arquivos da cura.
- O registro do rail traz `Rail-Text-sha256` (sha256 do sentinel com os campos `TO-FILL-BY-SIGN`),
  conferido no P0 contra o sentinel em disco (T6-text).
- O P0 exige commitada a evidência que o sentinel cita (T20) e recusa pelo nome, antes de qualquer
  arme de kernel, um patch com cabeçalho estrutural (T19).
- Desfazer: `APPLIED=1` antes do `git apply`; «patch-nao-chegou-a-aplicar» quando o patch não chegou a
  aplicar; um land já feito (HEAD = Anchor-SHA + 1 com a `.asc`) não é desfeito; `trap '' INT TERM
  HUP` no início do `on_exit`; o `--dry-run` sai ≠ 0 se o desfazer relatar NAO ou SUJOS. Estes três
  últimos caminhos não têm cenário no harness (sinal em janela de milissegundos).
- Derivador: comentário corrigido (o patch é o portador, `staged/` fica fora do git, o SIGN não lê
  `staged/`) e flags de diff pinadas contra a configuração do usuário (`-O/dev/null`,
  `--inter-hunk-context=0`, `--indent-heuristic`, `diff.suppressBlankEmpty=false`) — mesmos bytes.

Declarado no sentinel (residual pela forma): o censo reconhece a trava pelo NOME `FileLock` e exclui o
`audit_hmac.py` pelo nome do arquivo; a linha sem HMAC do ramo marcador-ausente; o estresse do
estouro da trava mede só gravadores `append_entry` (a contagem viva, abaixo); o import do `audit_emit`
dentro da trava na rotação e a drenagem forçada ao sair. Corrigidos: «superconjunto» das suítes (com o
que fica fora), a mensagem de commit (quais testes são vermelhos), a frase do `[Unreleased]`.

## Rodada 3 do rail (FINAL; Codex NO-GO só por uma frase do texto; refutador Claude APPROVE com 5 P2) — anexo

Pela regra da rodada final, as curas vêm num anexo e a checagem é só sobre o diff r3→anexo. O patch não
mudou (sha256 `c864ff69…`).
- Texto: removidas as frases sobre como os verificadores se comportam nos ramos sem marcador (Codex
  NO-GO na r3 e na checagem do anexo, cada vez por uma delas). Fica o mínimo verificável: a linha
  sai sem HMAC com `hmac_error` nomeado, o comportamento dos verificadores é o anterior, e o
  residual em uma linha.
- SIGN, na forma da W1: o texto que se assina é o `HEAD:<sentinel>` (o que o `Rail-Text-sha256`
  nomeia), preenchido numa cópia fora da árvore; o marcador dos campos só nas 4 linhas de campo (P0);
  o sentinel vivo que muda durante a bateria (ou aparece entre os sujos) aborta antes do passo 4, com
  a receita; depois do stage, blob do sentinel no índice = o preenchido e assinatura reverificada
  sobre o conteúdo do índice; o `--dry-run` ignora sinais também no desfazer do caminho de sucesso.
  Harness: T21 (sentinel vivo muda durante a bateria) e T22 (marcador na prosa).
- P2: a lista do que fica fora da bateria do SIGN (pernas de interpretador e de ambiente do CI); o rótulo do blob medido no `lockstress-S361.txt` (`f66cb3d8` da rodada 2; o
  final `4af77462` só muda uma docstring).
- Leitura do veredito do revisor: este SIGN NÃO lê a saída verbatim do revisor nem tem
  `Rail-Reviewer-Verdict`. Lê só os campos `Rail-Verdict` (`APPROVE` | `DECLARED-P2`) e
  `Rail-Findings` que o CEO escreve no registro, cada um exatamente uma vez em início de linha em
  qualquer lugar do arquivo (repetido, inclusive dentro de uma saída colada, é recusado). O defeito
  da W3b.1 (captura que termina em `## ` e aceita `VERDICT:` fora da cerca) não se aplica; o
  residual é que o veredito exigido é o do CEO, sem vínculo mecânico à linha `VERDICT` do revisor.

## Residuais declarados (P2, não curados nesta cerimônia)

- Os abortos por «sentinel virou symlink» (passo 3 e passo 4) não imprimem a receita de restauração.
- O verificador de assinatura e o allowlist são lidos da árvore viva depois da bateria; mudá-los na bateria só gera AVISO.
- Não há conferência pós-commit de `HEAD:<sentinel>` e `HEAD:<sentinel>.asc` contra os blobs do índice.
- A mecânica posterior ao passo 4 (blob do índice, assinatura sobre o índice) não tem cenário negativo no harness.

## Kernel

`audit_log.py` está em `_KERNEL_PATHS` (`check_arbitration_kernel.py:217`). O SIGN segue o molde de
kernel (W3-K do PLAN-169 e 179fu do PLAN-179), adaptado ao molde do FN-04: recusa rodar com
`CEO_KERNEL_OVERRIDE`/`_ACK` já no ambiente; no P0 confere VIVO, pelas funções do próprio hook, que o
caminho é kernel e que o par (reason-SLUG + `I-ACCEPT`) satisfaz `_override_granted()`; arma o
override só em volta de cada `git apply` (aplicar e reverter) e desarma logo depois. O sentinel ganhou
a seção «Kernel» e a nota de sessão dedicada (regra U-3). O harness confere isso no T1/T2 e recusa o
override vindo do ambiente no T17.

## Exigências do debate (rodada 1) e onde estão

- **MF-W2-1 (Security):** chave, elo e HMAC dentro da trava, DEPOIS do `rotate_if_needed` — feito; N
  gravadores `agent_spawn` em paralelo com `audit_emit` (síncrono e spool), vermelho no código atual e
  `verify_chain()` íntegro — `TestParallelWritersChain` (`red-control.txt`: 10/10 rodadas vermelhas no
  código anterior, 10/10 verdes no novo).
- **MF-W2-5 (Security, estresse da W2):** coberto aqui o que cabe sem mudar o escopo — `agent_spawn` +
  `audit_emit` síncrono + `audit_emit` em spool com drenagens oportunistas e forçadas, contagem conferida
  e `verify_chain()` íntegro. DECLARADO para a W2: saídas pelo caminho rápido (não existem ainda), kill
  -9 no meio da drenagem, reuso de PID, `.draining` órfão recuperado pelo `SessionStart` e a
  reconciliação `truly_lost = 0`. **Achado:** o contador `truly_lost` de `JournalReconciliation`
  (`_lib/spool_writer.py:136`) não é incrementado por nenhum caminho do código (só a definição e o
  dicionário de `:2562` o citam): hoje `truly_lost = 0` é vácuo e não pode ser critério da W2 sem antes
  ganhar semântica.
- **QA must-fix 8:** (1) `test_two_writer_chain.py` estendido, docstring da promessa da «rc.2»
  atualizada; controle de barreira (`TestReadToAppendWindow`, envoltório sobre `read_prev_hmac` que
  solta outro gravador e, com ele já na trava, espera 1,0 s; o prazo de trava dele é 2,5 s) vermelho no
  HEAD e verde depois; (2) censo por
  AST (`TestPrevHmacReadCensus`) com módulo sintético como controle positivo e piso anti-vácuo; (3)
  `CHANGELOG.md` tem oráculo 0 ⇒ land LIVRE complementar, DEPOIS do land canônico (diff pronto no
  checkpoint do pacote: `changelog-free-land.diff`, seção `[Unreleased]`, como no precedente do
  PLAN-190 W1; colide com a W7, que converte `[Unreleased]` na entrada da versão); (4) nenhum arquivo
  de trava é apagado ou recriado.

## Evidência

- `red-control.txt` — 7 testes vermelhos no código anterior, com o motivo de cada um; repetições.
- `latency-S361.txt` — subprocess, `append_entry` e contenção, antes × depois; sem regressão acima
  do ruído; a pré-imagem quebrou a cadeia em 12/12 repetições de contenção, a cura em 0/12.
- `lockstress-S361.txt` — frequência do descarte por estouro da trava (pedido do CEO, ADR-055-AMEND-4
  §7; alimenta o G7 da W2): 0 × 0 até 48 gravadores com ≤ 30 anexos; na saturação (32 × 150 anexos
  seguidos) a cura descartou 29/57.600 (0,05%) com a pós-imagem final e 51/48.000 (0,11%) com a da
  rodada 1; a pré-imagem 0, com a cadeia quebrada em 50/50 repetições; a cura íntegra em 50/50. **Decisão pendente:** o `append_entry` descarta no estouro
  (só breadcrumb), o `audit_emit` manda para o fallback (M9); igualar a rota, ou mudar o prazo de 2,5 s,
  fica para a W2 / ADR-055-AMEND-4 (o timeout não foi mudado).
  **Linha de base viva para o G7 da W2** (contagem datada dos `would-log` do `agent_spawn`): o
  `audit-log.errors` deste repositório, lido em 2026-10-02T04:54Z (32.927 linhas), tinha 3 breadcrumbs
  `lock timeout (stale?)  would-log=` de `agent_spawn` — 2026-10-01T23:48:41Z, 2026-10-02T00:44:25Z e
  2026-10-02T00:52:00Z, todos da PRÉ-imagem (o hook vivo) — e 32.721 `drain canonical lock timeout`.
- `rehearsal-S361.txt` — o ensaio do SIGN no harness (clones e chave GPG descartáveis); o final (F,
  materiais do anexo da rodada 3, sobre `f829b29a`) deu 195 PASS / 0 FAIL; o da rodada 3 (E, sobre
  `399efbaa`), 178 PASS / 0 FAIL. A 1.ª passada do E (E1: 29 FAIL de uma
  causa só — a frase nova do sentinel citava o marcador literal dos campos a preencher, que o SIGN
  recusa ver sobrar) foi curada antes do rail.
- `suite-compare-S361.txt` — as suítes do job `hook-tests-python-matrix` (paralela + serial) na base e
  na árvore landada pelo ensaio, por conjunto exato de falhas (patch da rodada 2; a rodada 3 mudou só
  os testes da cura, rodados no ensaio, e uma docstring).

## O que o Owner faz (depois do rail do CEO)

1. O CEO roda o rail (`rail-prompt.md`), commita `rail-round-N.md` (≤ 3 rodadas; o da última com
   `Rail-Subject-sha256` = sha256 do patch e `Rail-Text-sha256` = sha256 do sentinel antes do
   preenchimento, como está commitado) e os materiais num commit livre — por último, antes da assinatura — e refaz o
   ensaio com o registro real.
2. O Owner, num terminal: `bash .claude/plans/PLAN-194/w-auditrace/OWNER-AUDITRACE-SIGN.sh --dry-run`
   (opcional) e depois `bash .claude/plans/PLAN-194/w-auditrace/OWNER-AUDITRACE-SIGN.sh` (um pinentry).
3. `git push origin main` quando quiser. Depois, dois lands livres:
   - o do `CHANGELOG.md` (`changelog-free-land.diff` no checkpoint);
   - o do PLAN-194: o Check da W2.0 aponta node ids que este pacote não cria
     (`TestAgentSpawnBarrier::test_barrier_multiprocess`, `TestReadPrevHmacCensus::test_every_call_inside_filelock`);
     os reais são `.claude/hooks/tests/test_two_writer_chain.py::TestParallelWritersChain::test_parallel_spawn_and_sync_emit_writers_keep_the_chain`,
     `…::TestParallelWritersChain::test_parallel_spawn_and_spool_emit_writers_keep_the_chain`,
     `…::TestPrevHmacReadCensus::test_every_chain_writer_reads_the_predecessor_under_the_lock` e
     `…::TestReadToAppendWindow::test_no_foreign_append_between_prev_read_and_append` — trocar o Check
     por eles (e registrar no LEDGER a execução vermelha sobre o HEAD anterior a este land), antes do SIGN
     da W2.

## Riscos e observações

- **Colisão:** os 3 caminhos não aparecem no mapa de colisões do PLAN-194; `test_two_writer_chain.py`
  e `test_audit_log.py` podem ser tocados por um pacote de compatibilidade de Python (W1) — se um land
  livre tocar um deles antes deste SIGN, o P0 recusa («a base de … mudou») e o pacote é re-derivado
  (`derive-auditrace-patch.sh`) e volta ao rail.
- **Vaga:** pacote canônico; ocupa uma das 3 vagas da regra de WIP até landar.
- **Achado para a W6 (modo `0644` do log vivo, risco 13/«No pacote do `.claude/settings.json`»):**
  `audit_emit._emit_chain_reset_marker_under_lock` cria o log novo com `log.open("a")` (modo do umask);
  numa rotação feita pela drenagem do spool, o `_phase5_append_canonical` abre com `os.open(..., 0o600)`
  um arquivo que já existe e não reaperta — o log fica `0644` até o próximo gravador que faz `chmod`
  (o `audit_emit` síncrono ou o `audit_log.py`). É o candidato natural ao `0600 → 0644` observado na
  S361 depois de uma rotação; não muda neste pacote.
- **Borda analisada (sem mudança, declarada no sentinel):** importar `_lib.audit_emit` dentro da trava
  (só no ramo de rotação) instala os tratadores de saída do spool: o processo passa a fazer uma drenagem
  forçada ao sair, e um SIGTERM recebido exatamente nessa janela tentaria drenar e esperaria a própria
  trava até 2,5 s antes de sair. O custo do import a frio dentro da trava não foi medido.
