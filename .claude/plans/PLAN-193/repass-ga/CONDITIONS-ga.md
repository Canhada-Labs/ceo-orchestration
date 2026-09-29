# Condições do envelope — v1.4.2 (GA: promoção da v1.4.2-rc.1 após o hold de 24 h)

Este arquivo propõe condições; não é aprovação nem assinatura. O envelope vincula o snapshot
bruto e os payloads redigidos das quatro partes; um `NO-GO` exige triagem e novo re-pass.
Regra do corte (a mesma da rc.1: a que o Owner ratificou para a v1.4.0 e aplicou à v1.4.1):
`NO-GO` só por condição declarada FALSA contra o código ou por P0; um P1 não declarado vai ao
veredito sob «NEW FINDINGS (annex)» como ANEXO assinado — known-open no GA. Este texto não
promete versão para a cura de nada que ele declara aberto.
Base: a tag assinada `v1.4.1` (o GA anterior); o re-pass do GA revisa o delta
`v1.4.1..candidato` nas mesmas quatro partes da rc.1 (condição 11). Adopters do GA: quem SOBE da
v1.4.1, ou de uma versão anterior, por `upgrade.sh --pin v1.4.2`; e quem instala a 1.4.2 do zero
pelo `install.sh` — a partir de um checkout da tag `v1.4.2`, ou pelo `npx ceo-orchestration`,
cujo shim roda o `install.sh` que o pacote empacota. O GA publica esse pacote no npm: o
`npm-publish.yml` publica as tags sem `-rc.`, no ambiente `production-npm` e depois do gate do
`release.yml`, com `npm publish` sem `--tag`, e o npm põe a versão publicada na dist-tag
`latest`, que passa a apontar a 1.4.2.
Esta é a rodada 1 do re-pass do GA. Antes do codex, cada afirmação sobre código deste arquivo é
conferida contra o candidato por `.claude/plans/PLAN-193/repass-ga/probe-conditions-ga.py`, e a
saída entra na evidência (`probe-ga.txt`); com uma afirmação que deixou de valer o runner recusa
o re-pass antes do codex (o modo de ensaio REPORT-ONLY do harness segue, e o gerador do envelope
recusa a evidência dele). Neste texto, «o re-pass» sem outra qualificação é o do GA; o da rc.1 é
sempre nomeado assim.
O candidato da rc.1 (`9b5b1b40`, o commit do bump) teve `GO-WITH-CONDITIONS` nas quatro partes,
na rodada 1 do re-pass da rc.1; o envelope assinado da rc.1
(`.claude/governance/pair-rail-verdict-v1.4.2-rc.1.md`) está em `9a486d29`, o commit da tag
`v1.4.2-rc.1`. Entre aquele candidato e o que o re-pass do GA revisa mudaram só o envelope
assinado da rc.1, `CLAUDE.md` e arquivos de planos numerados (`.claude/plans/PLAN-<N>*`) —
nenhum numa pathspec das quatro partes. O `OWNER-GA-CUT.sh` recusa o corte enquanto o hold de
24 h do pre-release da rc.1 não venceu, e também se, entre o commit da tag `v1.4.2-rc.1` e o
candidato, mudar caminho fora de `CLAUDE.md` e de `.claude/plans/PLAN-<N>*`.
NADA foi curado entre a rc.1 e o GA, e o que a rc.1 declarou curado — as condições 3 e 4 — segue
declarado como ela o declarou. As seções A a D são as condições da rc.1, que seguem verdadeiras
sobre o candidato do GA, com mudanças só de TEXTO: este cabeçalho; na condição 1, o bump nomeado
como o da rc.1 e a re-declaração pelo envelope assinado da rc.1; nas condições 1, 9 e 11 e no
título da seção D, o escopo do re-pass do GA; na condição 12, o envelope assinado da rc.1 entre o
que fica fora, o README do GA como lugar do motivo e o que «entregue a adopters» quer dizer. A
seção E, nova, declara o anexo assinado da rc.1: os três P1 e os P2 dos quatro vereditos dela,
abertos no GA (condições 13 e 14), e o P2 que dependia de a tag do GA não existir (condição 15).
A lista exaustiva são as âncoras de `.claude/plans/PLAN-193/derive-ga-kit-142.py`, que deriva
este arquivo do da rc.1.

## A. Dívida carregada (re-declarada)

1. **O anexo P1 da v1.4.0 segue ABERTO, e nenhuma versão está prometida para a cura dele.** Os
   itens são as seções «NEW FINDINGS (annex)» dos vereditos em
   `.claude/plans/PLAN-169/repass-rc1/` e `.claude/plans/PLAN-169/repass-ga/`, mais as condições
   do envelope assinado `.claude/governance/pair-rail-verdict-v1.4.0.md`. A cura, re-alvejada para
   a 1.4.2 em 2026-09-18 (PLAN-192 OQ-1), não está nesta release: o Owner decidiu (2026-09-22;
   PLAN-193 OQ-3) que a 1.4.2 é uma release expressa que re-declara o anexo aberto — o que o
   envelope assinado do GA v1.4.1 (`.claude/governance/pair-rail-verdict-v1.4.1.md`) já
   registrou, e que a condição 1 do envelope assinado da rc.1
   (`.claude/governance/pair-rail-verdict-v1.4.2-rc.1.md`) re-declarou. Esta release não declara
   curado nenhum daqueles itens. Arquivos citados por aqueles vereditos mudam nesta faixa
   (`v1.4.1..candidato`); pela forma, estão entre os sítios de versão (que o bump da rc.1,
   `9b5b1b40`, o candidato dela, reescreveu para 1.4.2), o texto de release e de documentação, os
   templates de settings, `scripts/upgrade.sh` e `scripts/install.sh`, o código de hooks
   (`.claude/hooks/`, fora dos testes), os testes e harnesses de teste (`**/tests/**`, fora do
   re-pass) e o contrato deste repositório (`CLAUDE.md`, não entregue). Esta condição não afirma
   que cada achado siga reproduzível linha a linha: afirma que nenhum é declarado curado.
2. **O que o envelope assinado do GA v1.4.1 declarou aberto segue sem cura declarada, exceto o
   CASO da condição 23 daquele envelope e a condição 14 dele (condições 3 e 4 abaixo).** Aquele
   envelope declarou abertos os itens das condições dele — que carregam as da `v1.4.1-rc.1` — e,
   de todo veredito que ele ou o envelope da `v1.4.1-rc.1` pina — pelo MANIFEST da evidência,
   cujo sha256 o envelope carrega, ou pelo sha256 escrito numa condição —, os achados sob «NEW
   FINDINGS (annex)» e os P2. Esta release declara curados só: o caso que a condição 23 daquele
   envelope descreve — o ledger do hook da tool `Workflow`, que copiava, antes da decisão de
   permissão, os bytes do arquivo que um `scriptPath` nomeia (condição 3 abaixo) — e a escrita e
   a limpeza do `relaunch --out` da condição 14 (condição 4 abaixo, que diz o alcance). A CLASSE
   da condição 23, pela forma — um hook que roda antes da decisão de permissão e persiste os bytes
   de um caminho que o harness pode negar —, fica DECLARADA, não provada esgotada: a cura cobre só
   aquele hook, e esta release não afirma que nenhum outro hook seja da classe. Para os demais
   itens esta condição não afirma que nada mudou na faixa: afirma que esta release não os declara
   curados.

## B. O que esta release declara curado

3. **O caso da condição 23 do envelope do GA v1.4.1 está curado: o ledger do hook da tool
   `Workflow` não copia mais, antes da decisão de permissão, os bytes do arquivo que um
   `scriptPath` nomeia.** No PreToolUse da tool `Workflow`, `check_workflow_launch.py` (por
   `_lib/launch_ledger.py`) não grava, no diretório de estado do projeto, byte do arquivo que
   `tool_input.scriptPath` nomeia: o manifesto registra o caminho, o `sha256` e o tamanho (o
   `sha256` também na linha do índice), sem snapshot. Esse arquivo ainda é ABERTO e LIDO antes da
   decisão de permissão, para o hash e o tamanho. O snapshot passa ao PostToolUse da mesma
   chamada — vinculado por `tool_use_id`, com o id do run rotulado na resposta — e só é gravado
   quando os bytes relidos têm o `sha256` gravado antes do despacho. A cura landou em cerimônia
   canônica própria (`.claude/plans/PLAN-193/wave-fn04-approved.md` e a assinatura dele), cujo
   residual declara, pela forma, que a classe não se esgota neste hook. Esta condição afirma só
   propriedades do hook da tool `Workflow`.
4. **A escrita e a limpeza do `relaunch --out` (condição 14 do envelope do GA v1.4.1) estão
   curadas para o NOME do destino.** `ceo-launches.py relaunch --out FILE` escreve os bytes num
   temporário exclusivo, dentro de um diretório privado (`.ceo-launches-out-<hex>`) que a chamada
   cria no diretório de FILE; escreve até o último byte, faz `fsync` e só então dá a FILE o nome,
   por `link`, que nunca substitui uma entrada existente (um FILE que já existe — arquivo, symlink
   ou diretório — é recusa, sem tocar nele). Nenhum `unlink`, `rmdir`, `rename` ou `replace`
   recebe o nome de FILE: a limpeza remove, pelo nome, os dois NOMES que a chamada criou (o do
   temporário e o do diretório privado); sob a confiança declarada no diretório de FILE, o que
   outro escritor puser sob um desses nomes é removido no lugar. Assim os casos (a), (b) e (c)
   daquela condição deixam de valer para o nome do destino, e o caso (d) — a segunda leitura do
   snapshot que falhava e saía rc 0 — sai rc 7, antes do cabeçalho de chamada exata. Os limites
   estão declarados no item «`relaunch --out` (declared)» de `docs/workflow-recovery.md`; entre
   eles: nada é afirmado depois de uma queda de energia; o diretório de FILE é confiado como o do ledger; uma interrupção, ou uma remoção que
   falha, pode deixar o diretório privado — nunca bytes parciais sob o nome FILE.

## C. O que muda para o adopter

5. **Claude Opus 5.5 é o modelo de sessão fixado; o Opus 5 segue no conjunto de trabalho e como
   fallback.** O template de settings `base`, o `user` (derivado dele) e o `.claude/settings.json`
   deste repositório fixam `model: "claude-opus-5-5"`, e nenhum dos três carrega `ultracode`
   (PLAN-193 OQ-6: o ultracode fica só no override local do Owner). O `base` e o
   `.claude/settings.json` listam `claude-opus-5-5` e `claude-opus-5` em `availableModels` e
   mantêm `claude-opus-5` em `fallbackModel`; o `user`, advisory por desenho, não carrega
   `availableModels` nem `fallbackModel`. O piso VETO (`VETO_FLOOR_ALLOWED` em
   `.claude/hooks/_lib/agent_frontmatter.py`) admite `claude-opus-5-5`, e nenhum arquivo de
   agente (`.claude/agents/`) muda nesta faixa.
6. **Esforço: instalação nova em `xhigh`; quem sobe do pin `claude-opus-5` sem esforço definido
   fica em `high`.** Os templates `base` e `user` e o `.claude/settings.json` deste repositório
   carregam `effortLevel: "xhigh"` no topo (PLAN-193 OQ-1). Um adopter com os settings que o
   template `base` da v1.4.1 entregou (pin `claude-opus-5`, a lista `availableModels` entregue,
   sem `effortLevel`) sai do passo de migração de settings do `scripts/upgrade.sh` com
   `model: "claude-opus-5-5"` e `effortLevel: "high"`, a profundidade padrão do Opus 5 (OQ-8); o
   mesmo adopter com `effortLevel: "low"` sai com `"low"`. Nesse passo, `"xhigh"` só é gravado
   com o opt-in explícito `--adopt-setting effortLevel` (OQ-7), e um `effortLevel` que o adopter
   já tem fica como está também com ele. Cada saída de falha do passo que deixa o `settings.json`
   sem migrar — o backup pré-migração impossível, o `python3` ausente, o helper que falha —
   imprime o comando que re-executa só a migração, montado por uma rotina única
   (`_t54_rerun_cmd`), com o alvo e as flags do operador que decidem a migração
   (`--adopt-setting`, `--allow-old-claude-code`, `--pin`, `--dry-run`) (OQ-10).
7. **Claude Code 2.1.280 é o mínimo desta release (PLAN-193 OQ-9).** `scripts/install.sh` e
   `scripts/upgrade.sh` carregam o mesmo bloco de checagem (`claude-code-floor`, byte a byte
   igual nos dois), que lê `claude --version` do `claude` do PATH — a versão só da primeira linha
   que nomeia `(Claude Code)` — e a compara com 2.1.280. Abaixo do piso — e uma versão com
   qualquer coisa depois dos três números, como `2.1.280-beta.1`, conta como abaixo — uma
   instalação ou um upgrade saem com código 6 sem escrever nada no alvo, salvo com
   `--allow-old-claude-code` (aviso nomeado, e seguem); um `--dry-run` nomeia a recusa e segue.
   Sem `claude` no PATH, ou com uma saída da qual não leem a versão (a sonda para em 10 s),
   avisam e seguem: nesses casos o piso não é conferido. O motivo (OQ-9): nas versões do Claude
   Code que a OQ-9 nomeia, um `effortLevel: "xhigh"` num settings pode fazer o CLI descartar o
   arquivo inteiro, hooks de governança incluídos.
8. **O adapter live classifica os ids por uma lista FECHADA de legados.** Em
   `.claude/hooks/_lib/adapters/live/claude.py`, só um id dessa lista (os pré-4.6) recebe do
   `/effort` a forma legada de thinking, com `budget_tokens`; todo id fora dela —
   `claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5` ou um id que ainda não existe — é
   adaptive-only, sem entrar em lista nenhuma. A lista nomeia os legados — a geração Claude 3 por
   prefixo (`claude-3-*`), os demais por id, também nas grafias datada (`-AAAAMMDD`), do Vertex
   (`@AAAAMMDD`) e do Bedrock —; um id que acrescenta outro segmento a um id da lista é outro id,
   adaptive-only. Na chamada única (`call()`), um `thinking` de quem chama num id adaptive-only é
   normalizado antes do envio (a forma `enabled` vira `adaptive`; `budget_tokens` sai); o pedido
   do batch NATIVO (opt-in, `CEO_NATIVE_BATCH_LIFECYCLE=1`) leva o `thinking` de quem chama como
   veio.
9. **O pair-rail roda no Codex que o manifesto ADR-182 pina: 0.156.1 nesta release.** Os dois
   arquivos de pin (`.claude/governance/codex-cli-pin.txt` e `codex-cli-pin-manifest.json`)
   mudaram sob cerimônia assinada própria (`.claude/plans/PLAN-193/codex-pin-0156/`) e ficam fora
   do re-pass (condição 12), como ficaram fora do da rc.1. O revisor do re-pass do GA é a versão
   que o manifesto pina no momento do run; a PROVENANCE a registra, com a rota e o sha256 do
   payload verificado.
10. **Três CLIs novas, sem hook que as imponha.** `.claude/scripts/re-pin-codex.py`,
    `.claude/scripts/check-substrate-drift.py` e `.claude/scripts/derive-settings-baselines.py`
    landaram livres, cada uma com o seu arquivo de teste; os templates de settings, o
    `.claude/settings.json` e os hooks não as chamam.

## D. Escopo do re-pass do GA (as quatro partes da rc.1)

11. **Quatro partes, por raio de dano ao adopter, sobre o delta `v1.4.1..candidato`.** Todo
    caminho que muda nessa faixa está em exatamente uma parte ou numa classe declarada fora
    (condição 12); a sonda confere isso antes do codex, com as pathspecs do próprio runner, e
    confere que cada parte cabe no teto do redator com folga de 16 KiB. No GA, as quatro partes
    têm as pathspecs do runner da rc.1, e a sonda confere também, antes do codex, que são as mesmas
    e que nenhum arquivo delas mudou entre o candidato da rc.1 (`9b5b1b40`) e o do GA.
12. **Fora do re-pass, pela forma**, com o motivo em
    `.claude/plans/PLAN-193/repass-ga/README-ga.md` (§4; o que o GA acrescenta, na §0): testes,
    fixtures e harnesses de teste
    (`**/tests/**` — nesta faixa, entre eles os harnesses shell que nomeiam um instalador e
    ganham o bloco `harness-claude-stub` da wave-opus55); `.claude/plans/**` e
    `docs/research/**`; `CLAUDE.md`; `.claude/governance/**` — nesta faixa, só os dois arquivos
    de pin do Codex (condição 9), o manifesto ADR-192 dos gates e, no GA, o envelope assinado da
    rc.1 (`.claude/governance/pair-rail-verdict-v1.4.2-rc.1.md`), material de release;
    `.claude/scripts/local/**` —
    nesta faixa, só o `release.sh`, que muda na relmeta-142, cerimônia assinada própria: o bloco
    por-release e o probe de assinatura do `preflight`, que passa a chamar o `gpg` com `--yes`
    (a condição 15 do envelope do GA v1.4.1 declara que o `release.sh` é entregue a adopters, e
    só pelo `upgrade.sh`, e a divergência instalação × upgrade aberta); `.claude/adr/**`, texto
    de decisão (a Amendment 3 da ADR-149 muda nesta faixa, na cerimônia da wave-opus55, e a
    ADR-149 é a fonte das listas de modelos que
    `generate-available-models.py --check` confere contra os settings); dados de oráculo
    (`.claude/data/**`, `.claude/scripts/data/**`); `scripts/local/**` — nesta faixa, só o
    `smoke-install-parity.sh`, que ganha o mesmo bloco `harness-claude-stub`. A camada de
    isolamento da suíte pytest (`.claude/hooks/_lib/test_isolation.py`, cujo Eixo 4 põe um
    `claude` FALSO no PATH da suíte) NÃO fica fora: está na parte 2.
    Neste texto, «entregue a adopters» quer dizer copiado para a árvore do adopter pelo
    `install.sh` ou pelo `upgrade.sh`, e nenhum dos dois copia `.claude/governance/` para o alvo.
    O pacote npm, que o GA publica, empacota `.claude/` com as exclusões do passo «Stage bundle»
    do `npm-publish.yml`, que não excluem `.claude/governance/`: o envelope da rc.1 vai no pacote,
    e o `install.sh` que o shim roda não o copia para o alvo.

## E. O anexo assinado da rc.1, aberto no GA

13. **Os três P1 do anexo assinado da rc.1 seguem ABERTOS no GA, e nenhuma versão está prometida
    para a cura deles.** O envelope assinado da rc.1 pina, pelo MANIFEST da evidência cujo sha256
    ele carrega (`.claude/plans/PLAN-193/repass-rc1/MANIFEST-rc1.sha256`), os quatro vereditos da
    rodada 1 do re-pass da rc.1 (`.claude/plans/PLAN-193/repass-rc1/verdict-rc1-{1,2,3,4}.txt`),
    todos `GO-WITH-CONDITIONS`. Sob «NEW FINDINGS (annex)», o veredito da parte 3 traz dois P1 e o
    da parte 4, um; os das partes 1 e 2 não trazem achado novo. Os três, pela forma:
    (a) uma CLI de inspeção que recebe o caminho de outro checkout importa um módulo Python da
    árvore desse checkout — o código de importação dele roda com os privilégios de quem a chamou,
    antes das comparações e também sem `--fetch`;
    (b) um comando que uma CLI imprime para o operador copiar leva um caminho sem aspas de shell:
    um nome de diretório com uma substituição de comando a executa quando o comando é colado num
    shell, antes de a cerimônia começar;
    (c) o modelo com que o gerador do pack de re-pin do Codex decide onde o extrator do npm
    instala cada membro do tarball não normaliza os nomes como o extrator (o node-tar remove um
    prefixo de drive depois de `strip: 1`, e o modelo não): dois membros podem cair no mesmo
    destino sem recusa, e o pack então pina os bytes de um membro que não é o que o extrator deixa
    ali.
    (a) e (b) estão em `check-substrate-drift.py` e (c) em `re-pin-codex.py`, duas das CLIs da
    condição 10: nenhum hook, template de settings ou o `.claude/settings.json` as chama, e os
    defeitos só agem quando alguém as roda; o `install.sh` as copia para a árvore do adopter, como
    a todo `.claude/scripts/*.py` de primeiro nível. Esta condição não afirma que a classe de cada
    um se esgote nesses sítios. Nenhum arquivo das pathspecs das quatro partes mudou entre o
    candidato da rc.1 e o do GA (condição 11), e a entrada `[1.4.2]` do `CHANGELOG.md` — texto do
    candidato da rc.1, datado de 2026-09-25, que o GA não muda — não os nomeia no «Known-open».
    O P1 que o revisor da parte 1 citou como já declarado, não novo — a migração de settings do
    `upgrade.sh` ignora a cerimônia de instalação, a condição 55 do envelope da v1.4.0 — segue sob
    a condição 1.
14. **Os P2 dos quatro vereditos da rc.1 seguem ABERTOS no GA, sem versão prometida para a cura,
    fora o da condição 15.** Pela forma: o comentário (`_comment`) da registração do hook da tool
    `Workflow` nos templates de settings e no `.claude/settings.json` segue dizendo que o
    snapshot do script é gravado antes do despacho, o que, para um `scriptPath`, deixou de valer
    com a cura da condição 3 (o residual assinado da cerimônia do FN-04 e o «Known-open» da
    entrada `[1.4.2]` já o declaram); `check-substrate-drift.py` só declara o catálogo parcial
    quando faltam os dois blocos que ele compara, e, faltando um só, a comparação dele some sem
    aviso; `re-pin-codex.py`, com um molde da gramática de bloco de constantes (a do molde mais
    novo), escreve o marcador `TODO(owner)` também em prosa explicativa do sentinel do pack, e o
    guard do script de cerimônia, que recusa a execução real enquanto o marcador está no
    sentinel, segue recusando depois de preenchidas as seções humanas; e o mesmo gerador segue um
    diretório-pai do destino que é um symlink para fora do checkout e cria o pack lá.
15. **O P2 da parte 1 dependia de a tag `v1.4.2` não existir, e perde o objeto quando ela existe.**
    O exemplo de upgrade do `INSTALL.md` roda `upgrade.sh --pin v1.4.2`. O `upgrade.sh` resolve a
    ref do `--pin` com `git rev-parse --verify` no checkout-fonte de onde roda e, sem ela, sai com
    `unknown --pin ref` (código 2) — o caso da parte 1, durante o hold da rc.1. Este corte cria a
    tag assinada `v1.4.2` e a empurra ao remoto; num checkout-fonte que tem a tag, o exemplo
    resolve o `--pin`. Antes do push dela, ou num checkout-fonte que não a buscou, ele segue
    falhando como a parte 1 descreveu.
