# PLAN-194 — LEDGER (diário de identificadores e medições)

Registro datado de comandos, identificadores e resultados das medições e dos lands do PLAN-194
(trem de manutenção até a v1.4.3). Uma entrada por fato; o que é medição diz o comando, a data e o
substrato. Este arquivo é LIVRE (oráculo de canonicidade = 0).

## T0 do trabalho longo — 2026-10-01 (S361)

- Owner aceitou em bloco as decisões Q1–Q14 (ver `PLAN-194-maintenance-train-v1-4-3.md`, seção
  «Decisões do Owner — S361»). Primeiro commit do trabalho longo: `6a9abb10` (emendas de texto).
- Substrato no T0: macOS 27.0.1; Claude Code 2.1.287 (auto-atualizado de 2.1.286 às
  2026-10-01T18:21:01Z, segundo `~/.claude/.last-update-result.json`); Codex CLI 0.156.1 pinado
  (`check_pair_rail.py --verify-codex-pin` = `verified`); Codex 0.160.0 publicado no npm em
  2026-10-01T20:26:19Z (não instalado; o Owner decidiu em 2026-10-01 atualizar pela W3, sem re-pin
  manual).
- Cadeia de auditoria no T0: `audit-log-2026-10.jsonl` com 1.ª quebra na linha 7726 (mesma da linha
  de base S360) e `audit-log.jsonl` vivo íntegro (372 elos) antes do primeiro spawn paralelo; as
  quebras posteriores em `agent_spawn` são a corrida no produtor descrita no risco 11.
- Backup da cadeia (W6.1, primeiro): `~/.ceo-backups/<slug>/ceo-backup-2026-10-01T195004Z.tar.gz`,
  30.111.116 bytes, sha256 `2217cafb1554e640183d087c182d20e4b8dd9399429d2fbce2ec06cd4f3ffe78`
  (15 arquivos `.jsonl` + `audit-log.errors` + `memory/`; sem `audit-key`, `.salt`,
  `audit-log.rotation-manifest.json`, `audit-log.last-hmac` e `audit-log.chain-length`).

## W0.2 — manifesto do setup-python (controle vermelho da W1)

- 2026-10-01 (S361): no `versions-manifest.json` do ramo `main` de `actions/python-versions`, o
  Python 3.9 NÃO tem nenhum build linux para Ubuntu 26.04 (só até 24.04); 3.10 e 3.14 têm.

## W0.1 — Docker `ubuntu:26.04` (parcial)

- 2026-10-01T20:41Z–20:42Z (S361), colima 4 CPU / 6 GB nesta máquina:
  `docker pull ubuntu:26.04` ⇒ imagem `sha256:da6fc2be547864451aa253836dd926da33623312df4a9a243e35dc877c378a78`
  (criada em 2026-09-12T10:26:00Z); `/etc/os-release` = «Ubuntu 26.04.1 LTS (Resolute Raccoon)»;
  depois de `apt-get update`, `apt-cache policy python3` ⇒ candidato `3.14.3-0ubuntu2`, nada
  instalado; `apt-cache search --names-only '^python3\.[0-9]+$'` ⇒ só `python3.14`.
- Itens (a)–(d) da W0.1 (template ativado, passos de governança com o `python3` do sistema, suíte de
  hooks em 3.14, censo dos workflows): em medição pelo builder da W1; resultado a acrescentar aqui.

## W3b.3 — verificação em fonte primária (ids da OpenAI)

- 2026-10-02 ~00:30Z (S361), fonte: página oficial de deprecações da OpenAI
  (`https://platform.openai.com/docs/deprecations`, que redireciona com 301 para
  `https://developers.openai.com/api/docs/deprecations`), lida por WebFetch (extração por modelo
  auxiliar; as linhas abaixo foram pedidas verbatim):
  - seção «2026-06-11: GPT-5 and o3 model deprecations»: desligamento em **Dec 11, 2026** de
    `gpt-5-2025-08-07`, `gpt-5-mini-2025-08-07`, `gpt-5-nano-2025-08-07`, `gpt-5-pro-2025-10-06`,
    `o3-2025-04-16` e `o3-pro-2025-06-10` (substitutos `gpt-5.6-sol`/`-terra`/`-luna`);
  - seção «2026-04-22: Legacy GPT model snapshots (July 2026 shutdown)»: desligamento em
    **July 23, 2026** (já passado) de `gpt-5-codex`, `gpt-5-chat-latest`, `gpt-5.1-codex`,
    `gpt-5.1-codex-max`, `gpt-5.1-codex-mini`, `gpt-5.2-codex`, `gpt-5.1-chat-latest` e
    `o3-deep-research-2025-06-26`;
  - **`gpt-5.5` NÃO aparece na página** ⇒ a aposentadoria em 2026-10-14 NÃO se confirma; pelo texto
    da W3b.3 o item fecha sem a linha no `model-deprecations.json` (Check: none, resultado aqui).
  - `o3-mini`: uma primeira extração resumida citou «October 23, 2026», mas a extração verbatim não
    trouxe linha de `o3-mini` ⇒ NÃO confirmado; re-conferir à mão antes da W3b.1.
- Consequência para a W3b (achado do builder da W3b.0 + esta leitura): com a cura do detector, uma
  variante só casa se o ledger a listar; `gpt-5-codex` (desligado em 2026-07-23) e os demais ids da
  seção de julho precisam entrar no `model-deprecations.json` para não ficarem escondidos (hoje o
  `gpt-5-codex` aparece em `codex_invoke.py` e `codex_phase_gate.py`). Entra no refresh do ledger
  junto da W3b.3 (mesmo arquivo; a regra INERT do `check-model-currency.py:64`, opção A do builder,
  vai no mesmo land).
