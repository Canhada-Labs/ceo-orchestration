# Pair-rail prompt — PLAN-194, cura da corrida no gravador do agent_spawn (Codex, read-only, cold)

Você é o revisor cruzado (V2 da cascata de verificação — `PROTOCOL.md` §Verification cascade).

**Sujeito desta rodada (e só ele):**
1. o patch `.claude/plans/PLAN-194/w-auditrace/auditrace.patch` — JÁ APLICADO nesta árvore: os três
   arquivos que ele toca estão aqui na pós-imagem; a pré-imagem é o `index` de cada arquivo no patch;
2. o texto que o Owner vai assinar, `.claude/plans/PLAN-194/wave-auditrace-approved.md` (os campos
   `TO-FILL-BY-SIGN` são preenchidos pelo script de assinatura; não são achado). As frases dele sobre
   o que o SIGN faz são afirmações sobre `.claude/plans/PLAN-194/w-auditrace/OWNER-AUDITRACE-SIGN.sh`:
   confira-as lá (o resto do script é ensaiado pelo harness `test-ceremony-auditrace.sh`, não pelo rail).

**O caso (condição 67 do envelope assinado da v1.4.0-rc.1, repetida no da v1.4.0):** `append_entry`
(`.claude/hooks/audit_log.py`) lia o elo anterior (`read_prev_hmac()`) e calculava o HMAC FORA do
`FileLock`; a trava cobria só o append e o `write_last_hmac`. Um gravador que anexasse entre a leitura
e a trava deixava a linha `agent_spawn` encadeada num elo velho, e `verify_chain()` acusava
`hmac_mismatch` sem adulteração. Debate do PLAN-194, rodada 1: MF-W2-1 (Security Engineer) e
must-fix 8 (QA Architect) — ver `.claude/plans/PLAN-194/debate/round-1/`.

**Critérios:**
- a chave, o elo anterior, o HMAC, o append e o `write_last_hmac` ficam sob UMA trava, a mesma que
  `_lib/audit_emit._write_event` e a drenagem do spool usam (`audit-log.lock`, mesma derivação de
  caminho), e DEPOIS do `rotate_if_needed`; nenhum caminho do código lê o elo antes da trava e anexa
  depois;
- rotação feita por este gravador: o `chain_reset_marker` (ADR-055-AMEND-2) é a linha 1 do log novo e
  o `agent_spawn` encadeia nele; com a cadeia desligada, nada de marcador; nenhuma trava aninhada no
  mesmo processo (o auxiliar do marcador não toma a trava; importar `_lib.audit_emit` dentro da trava
  não toma a trava);
- fail-open em infraestrutura (o hook nunca sai ≠ 0 nem trava a sessão; estouro da trava descarta a
  linha com breadcrumb, sem mexer em `audit-log.last-hmac`); `hmac_error` segue fora do HMAC;
- nenhum arquivo de trava é apagado ou recriado;
- os testes provam o que dizem: o censo por AST não é vácuo e não aceita forma não modelada que
  deixe a leitura fora da trava num gravador; a janela leitura→anexo é vermelha na pré-imagem; a
  corrida entre processos é vermelha na pré-imagem e não confunde estouro de trava com a corrida;
  nada escreve fora do diretório temporário do teste (`TestEnvContext`; os filhos recusam log fora
  do sandbox); Python ≥ 3.9, stdlib (pytest só no teste);
- latência: o caminho do hook não ganha trabalho novo, só muda de lugar (dentro da trava); o efeito
  disso na frequência do descarte por estouro da trava está medido em `w-auditrace/lockstress-S361.txt`
  e declarado no texto assinável — confira que a declaração diz o que a medição diz;
- `audit_log.py` é KERNEL (`check_arbitration_kernel.py:217`): a seção «Kernel» do texto assinável
  precisa ser verdadeira sobre o hook de kernel (o que ele barra, `_is_kernel_path`,
  `_override_granted`);
- CADA frase do texto assinável é uma afirmação sobre o código: uma afirmação FALSA é motivo de NO-GO;
  o «Residual declarado» precisa ser verdadeiro e completo para o caso.

**Regra desta rodada:** a regra de parada pré-registrada é de no máximo 3 rodadas; a rodada 3 é a
final. NO-GO só por P0 ou por afirmação falsa no texto assinável. Relate todo P1/P2 com
`arquivo:linha` e cura concreta. Não proponha JEV nem capacidade não aprovada do fornecedor. Não
altere arquivos (sandbox read-only).

**Rodada 3 (FINAL).** A rodada 1 (REQUEST-CHANGES: 1 P1 e 2 P2) foi curada como descrito em
`PROPOSED-AUDITRACE.md`, seção «Rodada 1 do rail». A rodada 2 aprovou (Codex `NENHUM ACHADO`; dois
refutadores Claude APPROVE com 17 P2); o que mudou desde ela está em `PROPOSED-AUDITRACE.md`, seção
«Rodada 2 do rail», e no anexo `diff-r2-r3.diff` (diff dos materiais r2→r3, patch incluído). Em resumo:
- no patch, só testes e uma docstring do `audit_log.py` mudaram: `TestReadToAppendWindow` é `serial` e
  conta a janela de 1,0 s a partir do sinal do filho «vou tomar a trava» (antes: 1,5 s do sinal de
  partida, sob `-n auto`); a docstring de `_emit_rotation_marker_under_lock` restringe o motivo ao caso
  da falha do anexo do marcador; o código do caminho do hook é o mesmo da r2;
- no SIGN (fora do patch; sujeito só pelas frases do texto): tolerância zero a falha de teste dos
  arquivos da cura; `Rail-Text-sha256` conferido no P0; evidência citada exigida no git; patch com
  cabeçalho estrutural recusado pelo nome antes de armar o kernel; `APPLIED=1` antes do `git apply`;
  desfazer que reconhece «não chegou a aplicar» e um land já feito; `trap '' INT TERM HUP` no início
  do `on_exit`; `--dry-run` sai ≠ 0 se o desfazer não restaurar a árvore;
- no texto assinável: os residuais declarados novos (censo pela trava de NOME `FileLock` e exclusão
  do `audit_hmac.py` pelo nome do arquivo; linha sem HMAC tolerada como `pre_v29`; estresse só com
  gravadores `append_entry` e a contagem viva de `would-log`; import do `audit_emit` dentro da trava)
  e as imprecisões corrigidas.
Confira as curas e cada frase nova ou alterada do texto assinável; NO-GO só por P0 ou afirmação falsa.

**Anexo da rodada 3 (checagem estreita, só sobre o diff r3→anexo, `diff-r3-anexo.diff`):** o patch é
o mesmo (`c864ff69…`). Confira apenas: (1) a frase reescrita do sentinel sobre os retornos sem marcador
(condicionada à limpeza da rotação; predecessor antigo; `audit-verify-chain.py` com manifesto anterior);
(2) o SIGN assina o `HEAD:<sentinel>` preenchido fora da árvore, aborta se o sentinel vivo mudar durante
a bateria e confere o blob do índice e a assinatura sobre ele (cenários T21 e T22 do harness); (3) os
três P2 de texto/evidência. As seções «Rodada 3 do rail» do `PROPOSED-AUDITRACE.md` descrevem o anexo.

**Registro desta rodada (para o CEO):** `rail-round-3.md` traz `Rail-Subject-sha256` = sha256 do
`auditrace.patch` e `Rail-Text-sha256` = sha256 do `wave-auditrace-approved.md` com os campos
`TO-FILL-BY-SIGN` (o arquivo como está nesta árvore); o P0 do SIGN recusa um registro que não bata
com os dois.

**Saída:** a lista de achados, cada um com severidade `P0 | P1 | P2`, `arquivo:linha` e cura; se não
houver nenhum, escreva exatamente `NENHUM ACHADO`. Termine com UMA linha
`VERDICT: GO | GO-WITH-CONDITIONS | NO-GO`.
