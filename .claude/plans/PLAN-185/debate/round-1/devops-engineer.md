---
round: 1
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps Engineer
generated_at: 2026-08-26T20:05:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- As duas curas atacam defeitos reais e reproduzidos, e a decisão de fazer UMA cerimônia
  para W1+W2 está certa: as duas superfícies se tocam em `install_github_templates`.
- Forte: asserção nos BYTES do alvo externo (não no exit code) e fixtures obrigatoriamente
  VERMELHAS com a cura revertida — a disciplina de controle positivo que este repo pagou.
- Fraco em três eixos operacionais: (i) o **rollback do installer não cobre `docs/` nem
  `.github/`** — as duas árvores que W1/W2 tocam, e é por isso que o 0-byte sobrevive;
  (ii) o Scope da cerimônia está subdimensionado (4 canônicos, não 1) e o wiring de CI que
  o plano promete é ele próprio canônico; (iii) a fixture (b) é **impossível de passar**.

## Risks

1. **R-OPS1 — Severity CRITICAL — o rollback do install não cobre as árvores que W1/W2 tocam.**
   `cleanup_on_failure` (`scripts/install.sh:738-763`) restaura **apenas**
   `$TARGET/.claude` a partir de `$BACKUP_DIR/.claude` (`:753-758`); `docs/` e `.github/`
   nunca entram no snapshot (`:824`). Com `set -euo pipefail` (`:209`), o `sed` que falha
   em `:1643` aborta o script, o trap dispara, `.claude` volta ao estado anterior — e o
   `.github/CODEOWNERS` de 0 bytes **fica**. A permanência do F2 descrita no §1 do plano
   não é só o EXISTS-skip de `:1626`; é o rollback com buraco. Pior: se a guarda da W1
   abortar (`exit 1`, como `_assert_no_symlink_parents:878` já faz) no meio da entrega de
   `docs/`, o target fica MISTO — `.claude` revertido, `docs/` pela metade.
   *Mitigação:* a guarda compartilhada roda como **pré-voo** sobre TODOS os destinos de
   `install_docs_template`/`install_github_templates` antes da primeira escrita, recusando
   ali (zero estado parcial). Se o plano preferir a recusa in-loco, W1 tem de estender o
   snapshot a `docs/`+`.github/`, com item nomeado e teste próprio.

2. **R-OPS2 — Severity HIGH — F1 tem um TERCEIRO sítio, dentro da própria função que a W2 edita.**
   `install_github_templates` escreve `.github/CODEOWNERS` com `mkdir -p` + `>`
   (`install.sh:1642-1643`) guardado só por `[[ -e "$dst" ]]` (`:1626`) — que **segue** o
   symlink. Um link pendente em `$TARGET/.github/CODEOWNERS` faz o `>` escrever ATRAVÉS
   dele, fora do target, exatamente como F1. A W1 (escopada em `install_docs_template`)
   não alcança esse sítio, e a W2 (validação + escrita atômica) só o alcança se a escrita
   atômica também recusar destino-symlink.
   *Mitigação:* o `[P1]` da W1 passa a exigir **três** call-sites da mesma função
   (`:1514`, `:1626` e o pré-voo), e a prova comportamental é reverter a função e ver os
   TRÊS testes vermelhos — não dois.

3. **R-OPS3 — Severity HIGH — a fixture (b) da W2, como escrita, NUNCA passa. Medido.**
   O plano manda assertar «1442 bytes, 33 linhas» (`PLAN-185-installer-write-safety.md:139`).
   Medi: 1442/33 é o tamanho do template **NÃO renderizado**
   (`templates/.github/CODEOWNERS.template`), com 11 ocorrências de `{{OWNER_HANDLE}}` (17
   chars cada). Renderizado dá outro número: `alice`⇒1321, `ceo-test-handle`⇒1431, `a`⇒1277.
   Só um handle de exatos 17 caracteres reproduz 1442 — e aí o `grep -c '{{OWNER_HANDLE}}'
   == 0` da linha seguinte contradiz a asserção de tamanho.
   *Mitigação:* trocar constantes recalled por valores **derivados**: linhas do renderizado
   `==` linhas da fonte; `grep -c "$HANDLE"` `==` `grep -c '{{OWNER_HANDLE}}'` da fonte (11
   hoje, derivado no teste); bytes `> 0`. Fixar 1442 amarra o teste ao template e gera
   vermelho na próxima edição legítima dele.

4. **R-OPS4 — Severity HIGH — a W2 cura UM dos DOIS `sed`, e o que fica decide OWNERSHIP.**
   Existe um segundo `sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g"` em `install.sh:1635`, a
   sonda de byte-compare do ramo EXISTS. Com `/` no handle ela falha, o
   `_append_delivered_template ".github/CODEOWNERS"` de `:1637` não roda, e o veredito de
   posse muda (`FMS_HASH_SOURCE_CODEOWNERS`, `:2701-2714`) — do lado do upgrade isso
   aterrissa em `PRESERVED (unclaimed)` (`scripts/upgrade.sh:4457`). A proposta só nomeia
   o sítio de escrita.
   *Mitigação:* validar o handle **no parsing da flag** (`install.sh:478-479`), que hoje
   aceita qualquer string. Falhar ali torna os dois `sed` seguros por construção e faz a
   fixture (a) assertar recusa **antes** de qualquer `mkdir`.

5. **R-OPS5 — Severity HIGH — o Scope da cerimônia está subdimensionado: são 4 canônicos, não 1.**
   Rodei o oráculo em HEAD `b07be9b`: `scripts/install.sh`=1,
   `.github/workflows/validate.yml`=1, `.github/workflows/smoke-install.yml`=1,
   `scripts/_framework_manifest_set.sh`=1, `scripts/upgrade.sh`=1 — e, do outro lado,
   `scripts/doctor.sh`=0, `scripts/delivery-routes.tsv`=0,
   `.claude/scripts/check-installer-write-safety.py`=0, `scripts/tests/smoke-install.sh`=0.
   O §4 do plano só declara `install.sh`. Como o AC-4 exige `touched − scope = ∅`, um
   Scope de 1 path **aborta o land** no instante em que o patch tocar o `validate.yml`
   (item 3 da proposta) ou o `smoke-install.yml` (R-OPS6).
   *Mitigação:* derivar o Scope do patch, como o AC-4 já manda, mas dimensionar o pedido
   ao Owner **agora** com os 4 canônicos previstos; e decidir explicitamente se a função
   compartilhada vai para `_framework_manifest_set.sh` (canônico, +1 no Scope) ou fica em
   `install.sh` (Scope menor, mas fecha a porta para `upgrade.sh`/`doctor.sh`).

6. **R-OPS6 — Severity HIGH — teste que existe e job que não roda: `smoke-install.yml` é filtrado por `paths:`, em DUAS listas.**
   `scripts/tests/*.sh` só executa em `smoke-install.yml` (o próprio arquivo diz isso em
   `:47-48`) e em `ownership-nightly.yml`. O filtro tem lista de `pull_request` (`:4-…`) e
   lista de `push` (`:105-…`) que o arquivo manda manter idênticas (`:8-9`, `:107-110`).
   Um e2e novo em `scripts/tests/` que não entre nas DUAS listas **e** não ganhe um `run:`
   próprio é um teste que ninguém roda — a classe "red gate nobody runs" que este arquivo
   já documenta cinco vezes.
   *Mitigação:* a cerimônia inclui, no mesmo patch: o e2e nas duas listas de `paths:`, um
   step que o invoca, e um controle negativo (renomear o e2e ⇒ o step falha, não passa calado).

7. **R-OPS7 — Severity MEDIUM — o gate do censo per-PR com `indeterminado` bloqueante cria um deadlock de cerimônia.**
   `validate.yml` roda em todo PR sem filtro `paths:` (`:3-5`) no runner `Ceo` (`:36`,
   `timeout-minutes: 25` em `:43`), então o risco não é custo: o step Python é desprezível.
   É que a 4ª passada INVERTIDA classifica como `indeterminado` toda forma não provada
   segura (hoje 15, contra 12 desguardados). Bloqueando per-PR, qualquer refactor de
   `install.sh` com uma forma nova-mas-segura deixa o repo vermelho até alguém estender a
   allowlist — e destravar isso passa pelos canônicos ao redor, que exigem cerimônia.
   *Mitigação:* per-PR bloqueia apenas **desguardado novo** (delta contra o baseline) e o
   `exit 2` de contagem-zero; `indeterminado` é contado, impresso e vira ratchet no
   `ownership-nightly.yml` (`schedule:` ignora `paths:`). Precedente no repo:
   `scripts/tests/ownership-expected-reds.txt` + `ownership-nightly-gate.sh`.

8. **R-OPS8 — Severity MEDIUM — `mktemp` + `mv` só é atômico com o tmp no MESMO diretório, e muda o MODO do arquivo.**
   O precedente correto já existe: `_up_tpl_write` (`scripts/upgrade.sh`) faz
   `mktemp "$_utw_dir/.ceo-deliver.XXXXXX"` — dentro de `dirname "$dst"` — e `chmod`
   explícito antes do `mv -f`. Já `install.sh:1634` usa
   `mktemp "${TMPDIR:-/tmp}/ceo-codeowners.XXXXXX"`, aceitável só porque aquele tmp nunca é
   movido. Copiar essa forma para a escrita REAL da W2 quebra duas propriedades: `mv` entre
   filesystems degrada para copy+unlink (não-atômico, e sob ENOSPC reintroduz o 0-byte que
   a W2 existe para matar), e o destino herda 0600 do `mktemp` em vez do 0644 que o `>`
   atual produz via umask.
   *Mitigação:* reusar a forma de `_up_tpl_write`, e a fixture (b) assertar **também o
   modo** do `.github/CODEOWNERS` — bytes e linhas não pegam essa regressão.

9. **R-OPS9 — Severity MEDIUM — `upgrade.sh` não consegue recuperar o 0-byte, por construção.**
   O install aborta no `sed` (`:1643`) antes de `_write_install_state` gravar
   `github_owner` (`:2829`). Sem handle registrado, o upgrade cai em
   `PRESERVED (unclaimed)` (`upgrade.sh:4457`) e **nunca** re-renderiza. O AC-2 fala em
   "um install subsequente" e está correto, mas o plano não declara que a rota de upgrade
   é impotente aqui — e é o comando que um adopter roda por reflexo.
   *Mitigação:* AC-2 ganha uma segunda perna (após o install abortado,
   `.claude/.install-state.json` não tem `github_owner`) e declara por escrito que a
   recuperação exige `install.sh --github-owner <handle>`. `scripts/doctor.sh` é
   NÃO-canônico (oráculo=0): uma linha de detecção ali é edição livre.

10. **R-OPS10 — Severity MEDIUM — hard link é o gêmeo de F1 e o upgrade já o trata; o install não.**
    `_up_deliver_template` recusa destino com `nlink>1` (`_up_tpl_multilink_refuses`, rail
    round-7 F3). `install_docs_template` e a escrita do CODEOWNERS não têm nada disso:
    `cp` e `>` escrevem através do segundo nome do inode e nenhum teste de path enxerga.
    O AC-3 afirma que "a CLASSE está fechada" — com hard link aberto, não está.
    *Mitigação:* a guarda compartilhada cobre as TRÊS formas que o upgrade já recusa —
    symlink no leaf, componente de path intermediário symlinkado
    (`_assert_no_symlink_parents:863-882`, que `install_docs_template` **não** chama) e
    `nlink>1` — ou o plano declara hard link fora de escopo, por escrito, no §2.

## Must-fix (blocking)

1. Corrigir a fixture (b) da W2: substituir `1442 bytes / 33 linhas` por asserções
   DERIVADAS (R-OPS3). Como está, ela não pode passar.
2. Estender o `[P1]` da W1 ao sítio do CODEOWNERS (`install.sh:1626`/`:1642-1643`) —
   três call-sites, prova comportamental nos três (R-OPS2).
3. Validar `--github-owner` no parsing (`install.sh:478-479`), cobrindo os DOIS `sed`
   (`:1635` e `:1643`), e assertar recusa antes de qualquer `mkdir` (R-OPS4).
4. Resolver o rollback: pré-voo antes da primeira escrita, ou snapshot estendido a
   `docs/`+`.github/` com teste próprio. Não pode ficar implícito (R-OPS1).
5. Dimensionar o Scope da cerimônia com os canônicos reais (`install.sh`, `validate.yml`,
   `smoke-install.yml`, e `_framework_manifest_set.sh` se a função for para lá) — senão o
   gate `touched − scope = ∅` do AC-4 aborta o land (R-OPS5).
6. Wiring do e2e nas DUAS listas de `paths:` do `smoke-install.yml` + step invocador +
   controle negativo, no mesmo patch (R-OPS6).
7. Re-derivar TODAS as citações contra HEAD antes de implementar: a proposta aponta
   `install.sh:2139-2159` como "a defesa que já existe", e essa região é o render do
   ponteiro `PROTOCOL.md` (`:2137-2144`) mais o cabeçalho do passe de placeholders —
   **não há guarda de symlink ali**. As reais são `install_one` (`:900`, `:913`),
   `_assert_no_symlink_parents` (`:863-882`) e o passe de placeholders (`:2293-2304`).
   Os outros números também moveram: `install_docs_template` em `:1483` (não 1446),
   EXISTS-skip em `:1514` (não 1504), `sed` em `:1643` (não 1508).

## Nice-to-have (advisory)

1. `scripts/delivery-routes.tsv` (não-canônico) repete as linhas velhas no cabeçalho e na
   coluna `note` (`:1446-1474`, `:1488-1523`, "install.sh:1508"). Editá-lo acende o
   `smoke-install.yml` (está no filtro) — desejável.
2. Fixture de segunda execução: rodar o install DUAS vezes com o mesmo `--github-owner` e
   assertar que a segunda registra a entrega pela sonda de `:1635`. É o mesmo furo
   "result-only" que o comentário de `:1562-1569` diz já ter passado verde uma vez.
3. Um caso `--dry-run` por recusa nova: o ramo dry-run de `install_docs_template`
   (`:1505-1512`) usa `-e` puro e hoje mentiria sobre um destino-symlink.

## Unseen by the original plan

1. O rollback não cobrir `docs/`/`.github/` é o mecanismo que torna o F2 permanente — o
   plano atribui a permanência só ao EXISTS-skip (R-OPS1).
2. O segundo `sed` (`:1635`) e o efeito dele sobre o veredito de posse (R-OPS4).
3. `smoke-install.yml`/`validate.yml` canônicos: o wiring de CI é superfície de cerimônia.
4. A impossibilidade aritmética da fixture (b) (R-OPS3).
5. `upgrade.sh` ser incapaz de recuperar o estado corrompido (R-OPS9).
6. Hard link como gêmeo da classe, já reconhecido do lado do upgrade (R-OPS10).
7. O escalonamento de modo 0600 vs 0644 embutido na troca para `mktemp`+`mv` (R-OPS8).

## What I would NOT change

- **Uma cerimônia para W1+W2.** As duas curas convergem em `install_github_templates`
  (`:1603-1668`): dividir pagaria duas assinaturas pelo mesmo Scope e abriria uma janela
  com metade da classe curada.
- **Asserção nos BYTES do alvo externo, não no exit code.** Único critério que enxerga o
  F1, cujo sintoma é `exit 0` com log `COPIED:`.
- **Exigir VERMELHO com a cura revertida em todas as fixtures.** Sem isso o teste mede a
  própria existência.
- **A 4ª passada INVERTIDA do censo.** Três rodadas regenerando a mesma classe é sinal de
  arquitetura errada; enumerar o que é PROVADAMENTE seguro é a inversão certa.
- **Manter F3 fora (§2).** Misturar paridade com escrita reamarraria este plano à fila
  bloqueada do PLAN-183.
