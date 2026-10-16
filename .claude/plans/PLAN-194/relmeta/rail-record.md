# rail-record — relmeta-143 (PLAN-194, RM da v1.4.3; molde sign-min): rodada única do patch, do texto e dos dados, conferência do anexo e corte final por remoção

Rail-Subject: .claude/plans/PLAN-194/relmeta/relmeta.patch
Rail-Subject-sha256: 02b7fd110d0d84cbcf3b78cf22cd7574b74daba4ed7593e00f8aacc76f52816b
Rail-Sentinel: .claude/plans/PLAN-194/relmeta-approved.md
Rail-Sentinel-sha256: b853b1ac01812197cba0379532f4e4ff812793e08dbdcfdce58d25bdb202134b
Rail-Data: .claude/plans/PLAN-194/relmeta/sign.tsv
Rail-Data-sha256: 7fd50321fe0dbd4c10815bad13fac5f47c0e0726da099d4313b27294ffded770
Rail-Reviewer: codex-cli 0.160.0 (`exec --sandbox read-only`, config_sha c9249e8213c5a813 no preflight) e três lanes Claude (Opus 5.5) na rodada única; codex-cli 0.160.0 e duas lanes Claude na conferência do anexo
Rail-Date: 2026-10-16 (rodada única: preflight do Codex às 04:07:18Z; conferência do anexo: preflight às 05:02:04Z)
Rail-Reviewer-Verdict: rodada única — Codex NO-GO (3 P2), lane texto NO-GO (1 P1), lane cerimônia GO-WITH-CONDITIONS (2 P2), lane derivador GO-WITH-CONDITIONS (1 P2); conferência do anexo — Codex NO-GO (1 frase falsa), lane texto NO-GO (a mesma frase e 1 P2 de frase universal), lane mecânica GO-WITH-CONDITIONS (1 P2)
Rail-Verdict: DECLARED-P2
Rail-Findings: P0=0; P1 e frases falsas curadas (a última por REMOÇÃO); P2 declarados abaixo

Informativos (o SIGN não os confere):

- Derivador `.claude/plans/PLAN-194/relmeta/apply-relmeta143-edits.py`: sha256 f0a69df4b94395c7805f4a28c9bacfe22b29ca07e362ba6f872dbb4ce115a0a9.
- Envoltório `.claude/plans/PLAN-194/relmeta/hard-relmeta.sh`: sha256 1777724f34602fcc760a92222a99d5e92743190d85f059553026b62772b2cc30.
- Registro do controle vermelho `.claude/plans/PLAN-194/relmeta/red-control.txt`: sha256 c26181e487fa6eb424aafe409750d4a0cf8af2eeee112fb5e6eae2fd71861831.
- Sujeito de cada passo: rodada única = `6524ea8e` (materiais sobre `0f231b76`); conferência do anexo = `63c73de8` (só `CHANGELOG.md`) + `f812b215` (materiais re-derivados); corte final = `6b9904b1` (só `CHANGELOG.md`, pai `0f231b76`) + `fda0f593` (materiais re-derivados, `Derived-From` = `6b9904b1`).
- Saídas verbatim, prompts e logs de cada lane: fora do repositório, na pasta de ferramentas do Owner da S364 (`rm/rail/r1/`, `rm/rail/annex/` e `rm/rail/cut/`), com estes sha256: rodada única — `codex-prompt.md` 7274ab4a…, `codex-last.md` bac19272…, `codex.log` 15b603c3…, `claude-lanes.md` e7d64367…, `claude-lanes-workflow.js` 78169720…; anexo — `codex-prompt.md` ffae6998…, `codex-last.md` 02c9aa98…, `codex.log` b824d17b…, `claude-lanes.md` a98bf385…, `claude-lanes-workflow.js` afe4191d….

## Regra de parada (pré-registrada no esqueleto deste registro)

NO-GO só por condição falsa ou P0; a correção re-deriva e re-commita os materiais, e só então este registro é
preenchido. Rodada única e no máximo uma conferência de anexo (molde sign-min). Frase que recebe NO-GO na
conferência do anexo sai do texto por REMOÇÃO, sem frase nova de resultado no lugar, e o corte não abre outra
rodada.

## Rodada única (sujeito `6524ea8e`)

Lane Codex — última mensagem, verbatim (caminhos absolutos encurtados para `<wt>`):

```text
1. **P2 — `--verify` aceita falha do produtor de contagens.** Em [apply-relmeta143-edits.py:316](<wt>/.claude/plans/PLAN-194/relmeta/apply-relmeta143-edits.py:316), `proc.returncode` não é conferido; na linha 326, `violations` ausente vira lista vazia.
   **Reprodução:** com pós-imagens em memória, simulei o produtor retornando rc 7 e JSON com contagens corretas e `violations: []`. O `verify()` completo retornou 0. Também retornou 0 sem o campo `violations`.
   **Cura:** exigir rc 0 e validar campos obrigatórios e tipos antes de aceitar as contagens. Refuta o fail-closed do item 4.

2. **P2 — promessa de versão futura passa quando muda o major.** Em [apply-relmeta143-edits.py:546](<wt>/.claude/plans/PLAN-194/relmeta/apply-relmeta143-edits.py:546), a comparação considera somente versões do major 1.
   **Reprodução:** acrescentei em memória ao Known-open: `The framework annex cure is planned for v2.0.0.` A pré-condição e o `verify()` aceitaram; a mesma frase com `v1.4.4` foi recusada. O produtor de contagens foi simulado como válido.
   **Cura:** reconhecer versões futuras do framework também quando muda o major, distinguindo explicitamente referências a ferramentas externas. A garantia do sentinel nas linhas 53–56 excede essa implementação.

3. **P2 — conferência do registro de signatários desapareceu sem aposentadoria declarada.** A seção de [relmeta-approved.md:216](<wt>/.claude/plans/PLAN-194/relmeta-approved.md:216) omite essa retirada. O SIGN anterior consultava `is_valid_signer` em `.claude/plans/PLAN-193/relmeta/OWNER-RELMETA142-SIGN.sh:196` e novamente na linha 220. O molde atual seleciona pelo allowlist em `.claude/plans/PLAN-194/sign-min/sign_min.py:1122`; nenhum `hard` substitui a conferência.
   **Reprodução:** em memória, o registro recusou a chave no instante de expiração; a seleção atual aceitou o mesmo fingerprint com resposta GPG simulada.
   **Cura:** restaurar a conferência ou declarar explicitamente sua retirada e o risco residual. Refuta o item 5.

Patch, blobs, hashes, escopo, texto derivado e bloco comum conferem. As seis falhas estáticas do controle vermelho reproduzem os motivos registrados. Não executei as suítes completas nem as sondas que escrevem arquivos; nenhuma alteração foi feita no checkout.

VERDICT: NO-GO
```

Lanes Claude — resumo (o texto inteiro está em `claude-lanes.md`, sha256 acima):

- Texto (NO-GO): P1 reproduzido — uma instalação `--ceremony user`, nova ou atualizada da v1.4.2, seguia
  vermelha no gate do harness (4 RED `deny_baseline`), e o título, a headline e a seção `[1.4.3]` afirmavam
  verde sem ressalva; o CEO reproduziu numa árvore `git archive 0f231b76` (user: `FAIL: 4 RED`; maintainer:
  verde). P3: opt-out do `defaultMode` na headline, siglas, Scope do PLAN-193, commit local citado no
  controle vermelho, exceção `triple_missing` do pin. Frase a frase: o resto SUSTENTADO; Scope-Derived
  SUSTENTADO; contaminação: nenhum achado.
- Cerimônia (GO-WITH-CONDITIONS): P2 «recusa um commit fora do pacote» não pegava `merge -s ours` nem commit
  vazio; P2 a conferência do registro de signatários (`is_valid_signer`) da relmeta-142 sumiu sem declaração;
  P3 descarte do digitado antes do «SIM», pré-condição apoiada em frase histórica, clone do derivador não
  apagado, texto do «SIM» sem dizer que leva ao push.
- Derivador (GO-WITH-CONDITIONS): patch re-derivado idêntico (`f8692e9d…`), idempotente, controle vermelho
  idêntico ao registro, 253 testes de release aprovados; P2 a âncora `cond67` aceitava duas travas separadas;
  P3 tabela de âncoras incompleta, clone do derivador, `--claims-only` fora dos roteiros.

## Anexo (sujeito `63c73de8` + `f812b215`)

Curou: o P1 pelo TEXTO (cerimônia padrão `maintainer` no título, na headline e no `CHANGELOG.md`, commit
`63c73de8` antes da re-derivação); os 3 P2 do Codex (`verify-counts` com rc e campos conferidos; versão futura
em qualquer major; registro de signatários declarado entre as conferências aposentadas); os 2 P2 da cerimônia
(`git rev-list --full-history` fora do pacote e commit vazio recusados); o P2 do derivador (UM MESMO `with`
na âncora `cond67`); os P3 baratos.

Lane Codex da conferência — última mensagem, verbatim (caminhos encurtados):

```text
1. **P2 — a nova afirmação sobre instalações `user` ainda tem uma exceção omitida.** Em [relmeta-approved.md:101](<wt>/.claude/plans/PLAN-194/relmeta-approved.md:101) e `CHANGELOG.md:334`, o vermelho por quatro `deny_baseline` é apresentado sem ressalva.

   **Reprodução:** com `CEO_INSTALL_SKIP_DENY_BASELINE=1`, `scripts/install.sh:2494` retorna antes de criar `permissions`. O template `user` fica sem esse bloco, e `check_harness_config.py:529` retorna **zero achados**, sem exigir as quatro entradas. Executei o gate estático sobre esse template: **rc 0, zero warnings**. A composição normal, com baseline, reproduziu os quatro RED.

   **Cura:** restringir a afirmação à instalação `user` com baseline padrão aplicado ao settings produzido pela instalação; declarar a exceção do opt-out. Isso refuta a afirmação assinada sobre `deny_baseline`; não executei o replay completo.

2. **P3 — o descarte engole um `SIM` digitado depois do texto.** Em [owner-sign-rm.sh:279](<pasta do Owner>/rm/owner-sign-rm.sh:279), o `read -t 1` fica **depois** da tela de confirmação.

   **Reprodução:** executei isoladamente o trecho de entrada, sem assinatura nem escrita. `SIM` enviado 0,2 s após a tela completa foi descartado; o roteiro ficou esperando outra resposta. Enviado após 1,2 s, foi aceito.

   **Cura:** terminar a limpeza da entrada antes de imprimir o pedido de confirmação. Os pins conferem, e o texto agora informa explicitamente que o mesmo `SIM` leva ao push.

As demais curas P2 conferidas funcionam: rc/campos de contagens, `v2.0.0` recusado, npm `11.20.0` aceito, condição 67 com duas travas recusada e aposentadoria do registro declarada. As recusas de merge e commit vazio foram exercitadas com respostas de plumbing simuladas.

Patch, três alvos, blobs, manifesto, bloco comum, Scope, `Derived-From = C` e hashes conferem. O `--verify` passou com pós-imagens em memória; adaptei apenas o transporte dos blocos Python do produtor de contagens para evitar temporários proibidos pelo sandbox. Os seis motivos estáticos do controle vermelho coincidiram integralmente.

A cerimônia desconhecida não impede a entrega do `audit_log.py`: o upgrade atualiza os hooks independentemente dela, e ambos os templates da v1.4.2 já registravam esse hook. Não encontrei falsidade independente nas mensagens de C e M.

Nenhum P0. Pela regra desta conferência, o primeiro achado impede GO por afirmação falsa no texto a assinar. Nenhum arquivo foi alterado.

VERDICT: NO-GO
```

Lanes Claude da conferência — resumo (texto inteiro em `claude-lanes.md` do anexo):

- Texto (NO-GO): a mesma frase do Codex — com `CEO_INSTALL_SKIP_DENY_BASELINE=1`, uma instalação
  `--ceremony user` nova não declara `permissions` e o gate sai verde, então «user, nova ou atualizada, segue
  vermelha» é falso; P2 «uma instalação `maintainer` de release anterior segue vermelha até atualizar» é
  universal e falso (v1.0.0 e v1.0.1 não têm o gate; instalações com cópia da árvore de testes); P3 a frase
  nova sobre o `audit_log.py` «em qualquer cerimônia» tinha exceção; P3 versões de dois números fora do
  mecanismo. Conferidas e verdadeiras: maintainer verde em instalação nova e atualizada (perfil core, perfil
  padrão, `--stack node` e `--stack sandbox`), o defeito do user anterior à v1.4.3, `Derived-From`, as curas do
  `--verify` e a âncora `cond67`.
- Mecânica (GO-WITH-CONDITIONS): toda cura provada com o vermelho reproduzido (produtor de contagens falso
  com rc 7 e campos errados ⇒ rc 2; `v2.0.0`, `1.5.0` e `v1.4.4-rc.1` recusados e `npm 11.20.0` aceito;
  `merge -s ours` e commit vazio ⇒ rc 2; trava partida no `audit_log.py` real ⇒ `cond67` FAIL); derivação
  idempotente com o clone apagado; controle vermelho idêntico; 347 testes aprovados. P2 a frase do sentinel
  sobre versões era mais larga que o mecanismo (só `x.y.z`); P3 citação de outra release só entre colchetes,
  tag da base aposentada (na relmeta-142 era a v1.4.1), «escrita da linha» = qualquer `.write` na trava.

## Corte final por remoção (sujeito `6b9904b1` + `fda0f593`)

A frase com dois NO-GOs saiu por REMOÇÃO, sem frase nova de resultado: o título e a headline dizem o verde
só para a cerimônia padrão e que a instalação `--ceremony user` não é coberta; o `CHANGELOG.md` perdeu as
frases de cor do user e a frase universal «stays red until it upgrades», e o Known-open descreve só o
mecanismo (a checagem `deny_baseline` exige, num settings que declara `permissions`, quatro entradas que a
instalação user não grava), sem afirmar cor; a frase do `audit_log.py` ficou em «os dois templates o
registram e o `upgrade.sh` entrega o arquivo curado». O sentinel declara pela forma o que o mecanismo
confere (versões `x.y.z`; citação entre colchetes; tag da base). O roteiro do Owner descarta o digitado ANTES
de imprimir o texto da tag. O corte não teve rodada de rail própria (regra acima); para conferir que a remoção não trouxe frase
nova falsa, um refutador único Claude (só P0/P1; texto livre) leu o delta `63c73de8..6b9904b1` e
`f812b215..fda0f593` e reproduziu cada frase nova: veredito GO, NENHUM ACHADO P0/P1 (saída inteira em
`rm/rail/cut/delta-refutador.md`, sha256 2c344c00…; prompt em `delta-workflow.js`, sha256 70f6ded9…). Ele
reproduziu, com o `install.sh` do corte, `--profile core --ceremony user`: «MERGED: 20-entry» e o gate com
`FAIL: 4 RED finding(s)` (as 4 de `deny_baseline`); com `CEO_INSTALL_SKIP_DENY_BASELINE=1`, verde — a frase
nova não afirma cor e não contradiz isso; refez o controle vermelho e achou as seções 1 a 3 do
`red-control.txt` idênticas byte a byte. Três P3, declarados abaixo.

## Declarados (P2/P3 que ficam)

- Âncoras são, em maioria, tripwires de presença e de forma; frases só de texto existem em várias linhas da
  tabela do sentinel, que não é exaustiva.
- A pré-condição de versões confere só números `x.y.z`; versões de dois números ficam fora do mecanismo.
- A citação de outra release é reconhecida só entre colchetes.
- Na âncora `cond67`, «a escrita da linha» é qualquer chamada `.write` dentro da trava.
- O SIGN confere o allowlist de signatários, não o registro de validade (`is_valid_signer`); hoje sem efeito
  (a chave do allowlist vale até 2027-05-13 e não está revogada).
- O `--claims-only` antes da rc.1 e antes do GA é passo manual do roteiro do corte, não do SIGN.
- A exceção `triple_missing` do pin (host com codex no PATH e triple não derivável) é anterior a esta release.
- Do refutador do corte (P3): «The upgrade does not cover a `--ceremony user` install», lida isolada, pode
  sugerir que o `upgrade.sh` não atende a instalação user (o referente é o verde do gate); «`upgrade.sh`
  delivers the cured file» tem as exceções normais do upgrader (`--skip`, arquivo customizado pelo adopter em
  conflito, modo só de migração de settings); a checagem de colchetes recusa qualquer `[x.y.z]`, mais estrita
  que «outra release».
