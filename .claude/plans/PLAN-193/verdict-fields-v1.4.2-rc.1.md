verdict: GO-WITH-CONDITIONS
generated_at: 2026-09-29T02:44:06Z
ttl_hours: 24
parent_sha: 9b5b1b40078c20e6de4806d89cabd5776a7d33df
release_tag: v1.4.2-rc.1
inputs_hash: 6780022511525efdd2964c3f4b7181d1c4349ef77bf067e2b4c17c0967717409
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
delta_allowlist:
  - .claude/governance/pair-rail-verdict-v1.4.2-rc.1.md
  - .claude/plans/PLAN-193/verdict-fields-v1.4.2-rc.1.md
  - .claude/plans/PLAN-193/repass-rc1/CANDIDATE.sha
  - .claude/plans/PLAN-193/repass-rc1/CONDITIONS-rc1.reviewed.md
  - .claude/plans/PLAN-193/repass-rc1/MANIFEST-rc1.sha256
  - .claude/plans/PLAN-193/repass-rc1/PROVENANCE-rc1.md
  - .claude/plans/PLAN-193/repass-rc1/diff-rc1-1.patch
  - .claude/plans/PLAN-193/repass-rc1/diff-rc1-2.patch
  - .claude/plans/PLAN-193/repass-rc1/diff-rc1-3.patch
  - .claude/plans/PLAN-193/repass-rc1/diff-rc1-4.patch
  - .claude/plans/PLAN-193/repass-rc1/paths-rc1-1.manifest.txt
  - .claude/plans/PLAN-193/repass-rc1/paths-rc1-2.manifest.txt
  - .claude/plans/PLAN-193/repass-rc1/paths-rc1-3.manifest.txt
  - .claude/plans/PLAN-193/repass-rc1/paths-rc1-4.manifest.txt
  - .claude/plans/PLAN-193/repass-rc1/payload-rc1-1.redacted.txt
  - .claude/plans/PLAN-193/repass-rc1/payload-rc1-2.redacted.txt
  - .claude/plans/PLAN-193/repass-rc1/payload-rc1-3.redacted.txt
  - .claude/plans/PLAN-193/repass-rc1/payload-rc1-4.redacted.txt
  - .claude/plans/PLAN-193/repass-rc1/probe-rc1.txt
  - .claude/plans/PLAN-193/repass-rc1/run-rc1-repass.sh
  - .claude/plans/PLAN-193/repass-rc1/transcript-rc1-1.log
  - .claude/plans/PLAN-193/repass-rc1/transcript-rc1-2.log
  - .claude/plans/PLAN-193/repass-rc1/transcript-rc1-3.log
  - .claude/plans/PLAN-193/repass-rc1/transcript-rc1-4.log
  - .claude/plans/PLAN-193/repass-rc1/verdict-rc1-1.txt
  - .claude/plans/PLAN-193/repass-rc1/verdict-rc1-2.txt
  - .claude/plans/PLAN-193/repass-rc1/verdict-rc1-3.txt
  - .claude/plans/PLAN-193/repass-rc1/verdict-rc1-4.txt
delta_manifest: .claude/plans/PLAN-193/repass-rc1/MANIFEST-rc1.sha256
delta_manifest_sha256: ef056636e8fdf6222e20bd75dbf4719972bb4e6cebbe7eca4477ce7a1cbd1182
tool_versions:
  codex_cli: 0.156.1
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 0196e89fe5a7598f816ee54232c3d7c26d75e502ab5cfe2c9240e81d90f7255a
  claude_code: claude-code-cli-2.1.284
  python: 3.9.6
transcript_hash: 702afe84f154da7745ea51924e213731660f79951e86ab9d6946d71fcf14ef25
rail_decisions: [part1=GO-WITH-CONDITIONS, part2=GO-WITH-CONDITIONS, part3=GO-WITH-CONDITIONS, part4=GO-WITH-CONDITIONS]
findings: [rc1-4-partes-por-risco-do-adotante, sonda-das-condicoes-verde, p1-gowithconditions, p2-gowithconditions, p3-gowithconditions, p4-gowithconditions, cobertura-declarada-em-repass-rc1-README-rc1]
conditions:
  - № Condições do envelope — v1.4.2-rc.1 (release expressa: Opus 5.5, Codex 0.156.1, curas do FN-04 e do `relaunch --out`)
  - Este arquivo propõe condições; não é aprovação nem assinatura. O envelope vincula o snapshot
  - bruto e os payloads redigidos das quatro partes; um `NO-GO` exige triagem e novo re-pass.
  - Regra do corte (a que o Owner ratificou para a v1.4.0 e aplicou à v1.4.1): `NO-GO` só por
  - condição declarada FALSA contra o código ou por P0; um P1 não declarado vai ao veredito sob
  - «NEW FINDINGS (annex)» como ANEXO assinado. Este texto não promete versão para a cura de nada
  - que ele declara aberto.
  - Base: a tag assinada `v1.4.1` (o GA). Adopters: quem SOBE da v1.4.1, ou de uma versão
  - anterior, por `upgrade.sh --pin v1.4.2-rc.1`, e quem instala a partir de um checkout da tag pelo
  - `install.sh`; a rc não publica no npm (o `npm-publish.yml` pula as tags `-rc.`).
  - Esta é a rodada 1 do re-pass desta release. Antes do codex, cada afirmação sobre código deste
  - arquivo é conferida contra o candidato por `.claude/plans/PLAN-193/repass-rc1/probe-conditions-rc1.py`,
  - e a saída entra na evidência (`probe-rc1.txt`); com uma afirmação que deixou de valer o runner
  - recusa o re-pass antes do codex (o modo de ensaio REPORT-ONLY do harness segue, e o gerador do
  - envelope recusa a evidência dele).
  - №№ A. Dívida carregada (re-declarada)
  - 1. **O anexo P1 da v1.4.0 segue ABERTO, e nenhuma versão está prometida para a cura dele.** Os
  - itens são as seções «NEW FINDINGS (annex)» dos vereditos em
  - `.claude/plans/PLAN-169/repass-rc1/` e `.claude/plans/PLAN-169/repass-ga/`, mais as condições
  - do envelope assinado `.claude/governance/pair-rail-verdict-v1.4.0.md`. A cura, re-alvejada para
  - a 1.4.2 em 2026-09-18 (PLAN-192 OQ-1), não está nesta release: o Owner decidiu (2026-09-22;
  - PLAN-193 OQ-3) que a 1.4.2 é uma release expressa que re-declara o anexo aberto — o que o
  - envelope assinado do GA v1.4.1 (`.claude/governance/pair-rail-verdict-v1.4.1.md`) já
  - registrou. Esta release não declara curado nenhum daqueles itens. Arquivos citados por aqueles
  - vereditos mudam nesta faixa (`v1.4.1..candidato`); pela forma, estão entre os sítios de
  - versão que o bump reescreve, o texto de release e de documentação, os templates de settings,
  - `scripts/upgrade.sh` e `scripts/install.sh`, o código de hooks (`.claude/hooks/`, fora dos
  - testes), os testes e harnesses de teste (`**/tests/**`, fora deste re-pass) e o contrato
  - deste repositório (`CLAUDE.md`, não entregue). Esta condição não afirma que cada achado siga
  - reproduzível linha a linha: afirma que nenhum é declarado curado.
  - 2. **O que o envelope assinado do GA v1.4.1 declarou aberto segue sem cura declarada, exceto o
  - CASO da condição 23 daquele envelope e a condição 14 dele (condições 3 e 4 abaixo).** Aquele
  - envelope declarou abertos os itens das condições dele — que carregam as da `v1.4.1-rc.1` — e,
  - de todo veredito que ele ou o envelope da `v1.4.1-rc.1` pina — pelo MANIFEST da evidência,
  - cujo sha256 o envelope carrega, ou pelo sha256 escrito numa condição —, os achados sob «NEW
  - FINDINGS (annex)» e os P2. Esta release declara curados só: o caso que a condição 23 daquele
  - envelope descreve — o ledger do hook da tool `Workflow`, que copiava, antes da decisão de
  - permissão, os bytes do arquivo que um `scriptPath` nomeia (condição 3 abaixo) — e a escrita e
  - a limpeza do `relaunch --out` da condição 14 (condição 4 abaixo, que diz o alcance). A CLASSE
  - da condição 23, pela forma — um hook que roda antes da decisão de permissão e persiste os bytes
  - de um caminho que o harness pode negar —, fica DECLARADA, não provada esgotada: a cura cobre só
  - aquele hook, e esta release não afirma que nenhum outro hook seja da classe. Para os demais
  - itens esta condição não afirma que nada mudou na faixa: afirma que esta release não os declara
  - curados.
  - №№ B. O que esta release declara curado
  - 3. **O caso da condição 23 do envelope do GA v1.4.1 está curado: o ledger do hook da tool
  - `Workflow` não copia mais, antes da decisão de permissão, os bytes do arquivo que um
  - `scriptPath` nomeia.** No PreToolUse da tool `Workflow`, `check_workflow_launch.py` (por
  - `_lib/launch_ledger.py`) não grava, no diretório de estado do projeto, byte do arquivo que
  - `tool_input.scriptPath` nomeia: o manifesto registra o caminho, o `sha256` e o tamanho (o
  - `sha256` também na linha do índice), sem snapshot. Esse arquivo ainda é ABERTO e LIDO antes da
  - decisão de permissão, para o hash e o tamanho. O snapshot passa ao PostToolUse da mesma
  - chamada — vinculado por `tool_use_id`, com o id do run rotulado na resposta — e só é gravado
  - quando os bytes relidos têm o `sha256` gravado antes do despacho. A cura landou em cerimônia
  - canônica própria (`.claude/plans/PLAN-193/wave-fn04-approved.md` e a assinatura dele), cujo
  - residual declara, pela forma, que a classe não se esgota neste hook. Esta condição afirma só
  - propriedades do hook da tool `Workflow`.
  - 4. **A escrita e a limpeza do `relaunch --out` (condição 14 do envelope do GA v1.4.1) estão
  - curadas para o NOME do destino.** `ceo-launches.py relaunch --out FILE` escreve os bytes num
  - temporário exclusivo, dentro de um diretório privado (`.ceo-launches-out-<hex>`) que a chamada
  - cria no diretório de FILE; escreve até o último byte, faz `fsync` e só então dá a FILE o nome,
  - por `link`, que nunca substitui uma entrada existente (um FILE que já existe — arquivo, symlink
  - ou diretório — é recusa, sem tocar nele). Nenhum `unlink`, `rmdir`, `rename` ou `replace`
  - recebe o nome de FILE: a limpeza remove, pelo nome, os dois NOMES que a chamada criou (o do
  - temporário e o do diretório privado); sob a confiança declarada no diretório de FILE, o que
  - outro escritor puser sob um desses nomes é removido no lugar. Assim os casos (a), (b) e (c)
  - daquela condição deixam de valer para o nome do destino, e o caso (d) — a segunda leitura do
  - snapshot que falhava e saía rc 0 — sai rc 7, antes do cabeçalho de chamada exata. Os limites
  - estão declarados no item «`relaunch --out` (declared)» de `docs/workflow-recovery.md`; entre
  - eles: nada é afirmado depois de uma queda de energia; o diretório de FILE é confiado como o do ledger; uma interrupção, ou uma remoção que
  - falha, pode deixar o diretório privado — nunca bytes parciais sob o nome FILE.
  - №№ C. O que muda para o adopter
  - 5. **Claude Opus 5.5 é o modelo de sessão fixado; o Opus 5 segue no conjunto de trabalho e como
  - fallback.** O template de settings `base`, o `user` (derivado dele) e o `.claude/settings.json`
  - deste repositório fixam `model: "claude-opus-5-5"`, e nenhum dos três carrega `ultracode`
  - (PLAN-193 OQ-6: o ultracode fica só no override local do Owner). O `base` e o
  - `.claude/settings.json` listam `claude-opus-5-5` e `claude-opus-5` em `availableModels` e
  - mantêm `claude-opus-5` em `fallbackModel`; o `user`, advisory por desenho, não carrega
  - `availableModels` nem `fallbackModel`. O piso VETO (`VETO_FLOOR_ALLOWED` em
  - `.claude/hooks/_lib/agent_frontmatter.py`) admite `claude-opus-5-5`, e nenhum arquivo de
  - agente (`.claude/agents/`) muda nesta faixa.
  - 6. **Esforço: instalação nova em `xhigh`; quem sobe do pin `claude-opus-5` sem esforço definido
  - fica em `high`.** Os templates `base` e `user` e o `.claude/settings.json` deste repositório
  - carregam `effortLevel: "xhigh"` no topo (PLAN-193 OQ-1). Um adopter com os settings que o
  - template `base` da v1.4.1 entregou (pin `claude-opus-5`, a lista `availableModels` entregue,
  - sem `effortLevel`) sai do passo de migração de settings do `scripts/upgrade.sh` com
  - `model: "claude-opus-5-5"` e `effortLevel: "high"`, a profundidade padrão do Opus 5 (OQ-8); o
  - mesmo adopter com `effortLevel: "low"` sai com `"low"`. Nesse passo, `"xhigh"` só é gravado
  - com o opt-in explícito `--adopt-setting effortLevel` (OQ-7), e um `effortLevel` que o adopter
  - já tem fica como está também com ele. Cada saída de falha do passo que deixa o `settings.json`
  - sem migrar — o backup pré-migração impossível, o `python3` ausente, o helper que falha —
  - imprime o comando que re-executa só a migração, montado por uma rotina única
  - (`_t54_rerun_cmd`), com o alvo e as flags do operador que decidem a migração
  - (`--adopt-setting`, `--allow-old-claude-code`, `--pin`, `--dry-run`) (OQ-10).
  - 7. **Claude Code 2.1.280 é o mínimo desta release (PLAN-193 OQ-9).** `scripts/install.sh` e
  - `scripts/upgrade.sh` carregam o mesmo bloco de checagem (`claude-code-floor`, byte a byte
  - igual nos dois), que lê `claude --version` do `claude` do PATH — a versão só da primeira linha
  - que nomeia `(Claude Code)` — e a compara com 2.1.280. Abaixo do piso — e uma versão com
  - qualquer coisa depois dos três números, como `2.1.280-beta.1`, conta como abaixo — uma
  - instalação ou um upgrade saem com código 6 sem escrever nada no alvo, salvo com
  - `--allow-old-claude-code` (aviso nomeado, e seguem); um `--dry-run` nomeia a recusa e segue.
  - Sem `claude` no PATH, ou com uma saída da qual não leem a versão (a sonda para em 10 s),
  - avisam e seguem: nesses casos o piso não é conferido. O motivo (OQ-9): nas versões do Claude
  - Code que a OQ-9 nomeia, um `effortLevel: "xhigh"` num settings pode fazer o CLI descartar o
  - arquivo inteiro, hooks de governança incluídos.
  - 8. **O adapter live classifica os ids por uma lista FECHADA de legados.** Em
  - `.claude/hooks/_lib/adapters/live/claude.py`, só um id dessa lista (os pré-4.6) recebe do
  - `/effort` a forma legada de thinking, com `budget_tokens`; todo id fora dela —
  - `claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5` ou um id que ainda não existe — é
  - adaptive-only, sem entrar em lista nenhuma. A lista nomeia os legados — a geração Claude 3 por
  - prefixo (`claude-3-*`), os demais por id, também nas grafias datada (`-AAAAMMDD`), do Vertex
  - (`@AAAAMMDD`) e do Bedrock —; um id que acrescenta outro segmento a um id da lista é outro id,
  - adaptive-only. Na chamada única (`call()`), um `thinking` de quem chama num id adaptive-only é
  - normalizado antes do envio (a forma `enabled` vira `adaptive`; `budget_tokens` sai); o pedido
  - do batch NATIVO (opt-in, `CEO_NATIVE_BATCH_LIFECYCLE=1`) leva o `thinking` de quem chama como
  - veio.
  - 9. **O pair-rail roda no Codex que o manifesto ADR-182 pina: 0.156.1 nesta release.** Os dois
  - arquivos de pin (`.claude/governance/codex-cli-pin.txt` e `codex-cli-pin-manifest.json`)
  - mudaram sob cerimônia assinada própria (`.claude/plans/PLAN-193/codex-pin-0156/`) e ficam fora
  - deste re-pass (condição 12). O revisor deste re-pass é a versão que o manifesto pina no
  - momento do run; a PROVENANCE a registra, com a rota e o sha256 do payload verificado.
  - 10. **Três CLIs novas, sem hook que as imponha.** `.claude/scripts/re-pin-codex.py`,
  - `.claude/scripts/check-substrate-drift.py` e `.claude/scripts/derive-settings-baselines.py`
  - landaram livres, cada uma com o seu arquivo de teste; os templates de settings, o
  - `.claude/settings.json` e os hooks não as chamam.
  - №№ D. Escopo deste re-pass
  - 11. **Quatro partes, por raio de dano ao adopter, sobre o delta `v1.4.1..candidato`.** Todo
  - caminho que muda nessa faixa está em exatamente uma parte ou numa classe declarada fora
  - (condição 12); a sonda confere isso antes do codex, com as pathspecs do próprio runner, e
  - confere que cada parte cabe no teto do redator com folga de 16 KiB.
  - 12. **Fora do re-pass, pela forma**, com o motivo em
  - `.claude/plans/PLAN-193/repass-rc1/README-rc1.md`: testes, fixtures e harnesses de teste
  - (`**/tests/**` — nesta faixa, entre eles os harnesses shell que nomeiam um instalador e
  - ganham o bloco `harness-claude-stub` da wave-opus55); `.claude/plans/**` e
  - `docs/research/**`; `CLAUDE.md`; `.claude/governance/**` — nesta faixa, só os dois arquivos
  - de pin do Codex (condição 9) e o manifesto ADR-192 dos gates; `.claude/scripts/local/**` —
  - nesta faixa, só o `release.sh`, que muda na relmeta-142, cerimônia assinada própria: o bloco
  - por-release e o probe de assinatura do `preflight`, que passa a chamar o `gpg` com `--yes`
  - (a condição 15 do envelope do GA v1.4.1 declara que o `release.sh` é entregue a adopters, e
  - só pelo `upgrade.sh`, e a divergência instalação × upgrade aberta); `.claude/adr/**`, texto
  - de decisão (a Amendment 3 da ADR-149 muda nesta faixa, na cerimônia da wave-opus55, e a
  - ADR-149 é a fonte das listas de modelos que
  - `generate-available-models.py --check` confere contra os settings); dados de oráculo
  - (`.claude/data/**`, `.claude/scripts/data/**`); `scripts/local/**` — nesta faixa, só o
  - `smoke-install-parity.sh`, que ganha o mesmo bloco `harness-claude-stub`. A camada de
  - isolamento da suíte pytest (`.claude/hooks/_lib/test_isolation.py`, cujo Eixo 4 põe um
  - `claude` FALSO no PATH da suíte) NÃO fica fora: está na parte 2.
