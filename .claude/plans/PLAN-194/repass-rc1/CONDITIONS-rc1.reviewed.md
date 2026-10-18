# Condições do envelope — v1.4.3-rc.1 (trem de manutenção: o gate de configuração do harness curado na cerimônia padrão, a condição 67 da v1.4.0-rc.1 aposentada, o re-pin do Codex 0.160.0 e a prova do toolchain do npm na rc)

Este arquivo propõe condições; não é aprovação nem assinatura. O envelope vincula o snapshot
bruto e os payloads redigidos das quatro partes; um `NO-GO` exige triagem e novo re-pass.
Regra do corte (a que o Owner ratificou para a v1.4.0 e aplicou à v1.4.1 e à v1.4.2): `NO-GO` só
por condição declarada FALSA contra o código ou por P0; um P1 não declarado vai ao veredito sob
«NEW FINDINGS (annex)» como ANEXO assinado. Este texto não promete versão para a cura de nada
que ele declara aberto.
Base: a tag assinada `v1.4.2` (o GA). Adopters: quem SOBE da v1.4.2, ou de uma versão
anterior, por `upgrade.sh --pin v1.4.3-rc.1`, e quem instala a partir de um checkout da tag pelo
`install.sh`; a rc não publica no npm (o job do publish do `npm-publish.yml` pula as tags `-rc.`).
Esta é a rodada 1 do re-pass desta release. Antes do codex, cada afirmação sobre código deste
arquivo é conferida contra o candidato por `.claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py`,
e a saída entra na evidência (`probe-rc1.txt`); com uma afirmação que deixou de valer o runner
recusa o re-pass antes do codex (o modo de ensaio REPORT-ONLY do harness segue, e o gerador do
envelope recusa a evidência dele).

## A. Dívida carregada (re-declarada)

1. **O anexo P1 da v1.4.0 segue ABERTO, exceto o CASO da condição 67, e nenhuma versão está
   prometida para a cura do resto.** Os itens são as seções «NEW FINDINGS (annex)» dos vereditos
   em `.claude/plans/PLAN-169/repass-rc1/` e `.claude/plans/PLAN-169/repass-ga/`, mais as
   condições do envelope assinado `.claude/governance/pair-rail-verdict-v1.4.0.md`. O envelope
   assinado do GA v1.4.2 (`.claude/governance/pair-rail-verdict-v1.4.2.md`) já o declarou aberto.
   Esta release declara curado um só daqueles itens — o CASO da condição 67 (a condição 67
   assinada da `v1.4.0-rc.1`, que o envelope `pair-rail-verdict-v1.4.0.md` também numera; condição
   3) — e não declara curado nenhum outro. Arquivos citados por aqueles vereditos mudam nesta
   faixa (`v1.4.2..candidato`); pela forma, estão entre os sítios de versão que o bump reescreve,
   o texto de release e de documentação, os templates de settings, `scripts/upgrade.sh` e
   `scripts/install.sh`, os workflows de CI e de release (`.github/workflows/`), o código de hooks
   (`.claude/hooks/`, fora dos testes), os testes e harnesses de teste (`**/tests/**`, fora deste
   re-pass) e o contrato deste repositório (`CLAUDE.md`). Esta condição não afirma
   que cada achado siga reproduzível linha a linha: afirma que, fora o caso da condição 67, nenhum
   é declarado curado.
2. **O que o envelope assinado do GA v1.4.2 declarou aberto segue sem cura declarada, exceto o
   CASO de um P2 da parte 3 do re-pass daquele GA.** Aquele envelope declarou abertos os itens
   das condições dele — que carregam as da `v1.4.2-rc.1` e, pelas condições 13 a 15 dele, os três
   P1 do anexo assinado da `v1.4.2-rc.1` e os P2 dos quatro vereditos daquela rc — e, de todo
   veredito que ele ou o envelope da `v1.4.2-rc.1` pina pelo MANIFEST da evidência (cujo sha256 o
   envelope carrega), os achados sob «NEW FINDINGS (annex)» e os P2. Esta release declara curado
   um só deles: o P2 da parte 3 do re-pass do GA v1.4.2, em que um ledger de substrato com a forma
   errada substituía o relatório inteiro do `check-substrate-drift.py` (condição 4). Não declara
   curado nenhum outro, entre eles os três P1 do anexo assinado da `v1.4.2-rc.1`. Esta condição
   não afirma que nada mudou na faixa: afirma que, fora esse P2, esta release não os declara
   curados.

## B. O que esta release declara curado (o CASO; a classe fica declarada, não provada esgotada)

3. **O gravador do `agent_spawn` lê o elo anterior, calcula o HMAC, grava a linha e atualiza o
   sidecar sob UMA trava do log: o CASO da condição 67 da `v1.4.0-rc.1`.** Em
   `.claude/hooks/audit_log.py`, `append_entry` faz as quatro coisas dentro de um mesmo
   `with FileLock(paths["lock"], ...)`. O `CHANGELOG.md` [1.4.3] declara a cura e, no Known-open,
   os limites dela, entre eles: as quebras que a corrida já gravou ficam nos logs; gravadores que
   resolvem travas diferentes para o mesmo log seguem sem se excluir; a primeira criação da chave
   HMAC por projeto segue não exclusiva (a condição 68 da `v1.4.0-rc.1`); e, sob saturação da
   trava, a linha pode cair (fail-open). A sonda confere a FORMA do código pela AST (a leitura do
   elo, o cálculo do HMAC e a atualização do sidecar só ocorrem dentro de um bloco dessa trava,
   no mesmo bloco de uma escrita da linha), o texto do CHANGELOG e a condição 67 nos dois
   envelopes da v1.4.0; ela não executa o gravador.
4. **O `check-substrate-drift.py` confere cada componente por si: o CASO do P2 da parte 3 do
   re-pass do GA v1.4.2.** Um ledger de substrato que é JSON válido com a forma errada vira o
   achado nomeado `CC_LEDGER_UNREADABLE`, e uma checagem de componente que levanta exceção vira
   `COMPONENT_CHECK_ERROR`; os dois contam como desconhecido, e com `--strict` a deriva que outro
   componente já achou segue saindo com código 1. O `CHANGELOG.md` [1.4.3] declara a cura e que o
   `/ceo-boot` não roda esta ferramenta. A sonda confere os dois nomes no código e o texto do
   CHANGELOG, e reproduz o cenário do P2 sem rede: um ledger com `last_seen` em texto e um codex
   instalado fora do pin (lido do `package.json` do lançador, sem executá-lo) dão
   `CC_LEDGER_UNREADABLE`, a deriva do Codex e código 1 com `--strict`.

## C. O que muda para o adopter

5. **O pair-rail roda no Codex que o manifesto ADR-182 pina: 0.160.0 nesta release.** Os dois
   arquivos de pin (`.claude/governance/codex-cli-pin.txt` e `codex-cli-pin-manifest.json`)
   mudaram sob cerimônia assinada própria (`.claude/plans/PLAN-194/codex-pin-0160/`) e ficam fora
   deste re-pass (condição 10). O revisor deste re-pass é a versão que o manifesto pina no momento
   do run, e só pela rota 1 do runner (decisão D-4 do PLAN-194): o binário global, depois de o
   oráculo do pair-rail-gate conferir o sha256 do payload nativo contra o manifesto sem
   executá-lo; a rota 2 (`npx` num cache próprio) é recusa nomeada, sem download nem execução.
   A PROVENANCE registra a versão, a rota e o sha256 do payload verificado. Resíduo, da forma que
   o Known-open do `CHANGELOG.md` [1.4.3] declara para o pin (ele não cobre o lançador): o shim do
   runner executa o `codex` global do PATH — no layout do npm, o lançador `codex.js` do pacote —,
   e o oráculo hasheia o payload nativo que resolve a partir desse lançador, não o lançador. É um
   resíduo de mesmo UID, e a cura não é desta release.
6. **A rc prova o toolchain do publish sem publicar.** No `.github/workflows/npm-publish.yml`, o
   job `rc-toolchain-proof` («RC toolchain proof (no publish)») roda só nas tags `-rc.` (`if:
   contains(github.ref, '-rc.')`), com `permissions` só `contents: read` — sem `id-token`, sem
   `environment` e sem `secrets.` — e nenhum passo dele chama `npm publish`; o job do publish
   segue pulando as tags `-rc.`. Os dois jobs leem a linha do Node e a versão exata do npm das
   MESMAS variáveis do workflow (`PUBLISH_NODE_MAJOR` e `PUBLISH_NPM_VERSION`, definidas uma vez,
   no `env` do workflow, e redefinidas por nenhum dos dois), e os dois rodam em `ubuntu-latest`. O
   passo 18 do `OWNER-RC1-CUT.sh` exige `success` nesse job, pelo nome, além do job do gate. O que
   ele NÃO prova: a troca do token OIDC e a escrita no registry, que só acontecem no GA; e a prova
   vale para a imagem do runner em que roda — o GA pode rodar noutra imagem de `ubuntu-latest`.
7. **Durante o hold entre a rc e o GA, o exemplo de upgrade do `INSTALL.md` pina a versão GA que
   o bump escreve, e essa tag ainda não existe.** O `release.sh bump` reescreve o exemplo
   `upgrade.sh … --pin v<versão>` junto do `VERSION`; sem a tag, o `upgrade.sh` sai com
   `ERROR: unknown --pin ref` (código 2). Até o GA, quem sobe usa `--pin v1.4.3-rc.1`. A mesma
   classe apareceu nos re-passes das duas releases anteriores e não é curada aqui.
8. **O adapter Claude da lane live não muda nesta faixa (decisão D-10 do PLAN-194):**
   `.claude/hooks/_lib/adapters/live/claude.py`. Esta release não adota o Sonnet 5.5, e o
   comportamento do adapter com ele (a lane `ANT-02`) não foi medido.

## D. Escopo deste re-pass

9. **Quatro partes, por raio de dano ao adopter, sobre o delta `v1.4.2..candidato`.** Todo
   caminho que muda nessa faixa está em exatamente uma parte ou numa classe declarada fora
   (condição 10); a sonda confere isso antes do codex, com as pathspecs do próprio runner, e
   confere que cada parte cabe no teto do redator com folga de 16 KiB. As demais mudanças que o
   texto de release do candidato descreve (`CHANGELOG.md` [1.4.3], na parte 1), com os limites que
   ele declara, são julgadas como integração nas partes, sem condição própria.
10. **Fora do re-pass, pela forma**, com o motivo em
   `.claude/plans/PLAN-194/repass-rc1/README-rc1.md`: testes, fixtures e harnesses de teste
   (`**/tests/**`); `.claude/plans/**` e `docs/research/**`; `CLAUDE.md`;
   `.claude/governance/**` — nesta faixa, no máximo os dois arquivos de pin do Codex (condição 5),
   o manifesto ADR-192 dos gates e o comentário do publicador confiável do npm
   (`npm-trusted-publisher.txt`, mudado na cerimônia da W4); `.claude/scripts/local/**` — nesta
   faixa, no máximo o `release.sh`; `.claude/adr/**`, texto de decisão; dados de oráculo e de
   teste (`.claude/data/**`, `.claude/scripts/data/**`); `scripts/local/**`, harness de smoke do
   mantenedor; o harness de avaliação `.claude/eval/**`; a configuração de teste da raiz
   (`conftest.py` e `pytest.ini`: o oráculo); e o `.gitignore` da raiz, higiene deste
   repositório. Fora do re-pass não quer dizer não entregue; este kit não afirma, classe a
   classe, o que chega a um adopter.
