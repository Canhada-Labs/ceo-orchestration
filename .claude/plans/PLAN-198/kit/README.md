# Kit do veredito pair-rail — PLAN-198 (v1.4.4-rc.1 e v1.4.4)

Os mesmos quatro arquivos servem para a versão candidata (rc, de *release candidate*,
`v1.4.4-rc.1`) e para a versão final (GA, de *general availability*, `v1.4.4`). Só muda
o `--tag`. Nenhuma versão está escrita dentro do código.

| Arquivo | Para que serve |
|---|---|
| `run_repass.sh` | O re-pass: duas revisões independentes do mesmo material — Codex (modelo da OpenAI, só leitura) e Claude Code (`claude -p`, só ferramentas de leitura, com o login de assinatura; nunca `--bare`, que exigiria chave de API paga). Grava a evidência em `.claude/plans/PLAN-198/repass-rc1/` (rc) ou `repass-ga/` (GA). |
| `gen_envelope.py` | Gera os campos para você assinar (`verdict-fields-<tag>.md`) e, depois da assinatura, o envelope do veredito (`.claude/governance/pair-rail-verdict-<tag>.md`). Antes de gravar qualquer um dos dois, roda o validador real do passo 15 do `release.yml` sobre o próprio resultado. |
| `test-kit.sh` | Teste descartável do kit: repositório falso numa pasta temporária, chave GPG (programa de assinatura) descartável, revisores simulados. Não toca este repositório nem a rede. |
| `README.md` | Este texto. |

Siglas: CI = integração contínua (os workflows do GitHub); SHA = identificador de um commit;
ADR = registro de decisão de arquitetura; npm = registro público de pacotes; UTC = horário
universal.

## Três regras que valem do início do re-pass da rc até o push da tag do GA

1. **Não atualize o Codex nem o Claude Code.** O re-pass grava a versão e o hash do binário
   do Codex como identidade do instrumento; o GA recusa um Codex diferente do da rc.
2. **Nada entra na main além de arquivos em `.claude/plans/PLAN-198/`.** O GA recusa se a
   main mudou fora dessa pasta depois da tag rc.
3. **Nunca use `MAC_RELEASE_ARGS=--push`.** `make mac-cut-rc` e `make mac-cut-ga` com
   `MAC_RELEASE_ARGS=--push` enviam a main e a tag **automaticamente, sem pedir
   confirmação** — e, se o bump criar um commit, enviam esse commit também. Sem `--push`
   eles só assinam a tag localmente; o envio fica com você.

## Janelas de tempo

- O validador do passo 15 recusa um veredito com mais de **24 h** no momento em que o
  `release.yml` roda. Envie a tag até **~22 h** depois do `generated_at` dos campos (a
  margem cobre a fila da CI). O `generated_at` aparece na saída do `fields`.
- A tag do GA precisa ser criada **pelo menos 24 h depois** da criação da tag rc (o
  `release.yml` compara as datas de criação das duas tags).

## Passo a passo — v1.4.4-rc.1

0. **Antes (o Claude prepara):** o kit e o arquivo de condições estão commitados na main
   e a CI está verde. As condições são o texto que você assina junto com o veredito.
1. **Bump.** Releia `npm/README.md`. Depois:
   `bash .claude/scripts/local/release.sh bump --rc 1 --npm-readme-reviewed`,
   `git push origin main`, e espere a CI verde no commit do bump.
2. **Re-pass** (leva horas; pode rodar em segundo plano):

   ```
   nohup bash .claude/plans/PLAN-198/kit/run_repass.sh --tag v1.4.4-rc.1 \
     --conditions .claude/plans/PLAN-198/CONDITIONS-rc1.md > /dev/null 2>&1 &
   tail -f .claude/worktrees/repass-rc1.log
   ```

   A última linha do log é `runner exit rc=N`:
   `0` = as duas revisões aprovaram todas as partes; `1` = alguma revisão disse NO-GO ou
   não deu veredito legível (não há veredito: chame o Claude para a triagem); `2` = recusa
   antes de qualquer envio (leia a linha `REFUSED:`); `3` = uma revisão morreu (limite da
   conta ou queda): depois do reset rode **o mesmo comando com `--resume`**.
3. **Campos:** `python3 .claude/plans/PLAN-198/kit/gen_envelope.py fields --tag v1.4.4-rc.1`.
   Leia as condições em `.claude/plans/PLAN-198/verdict-fields-v1.4.4-rc.1.md`.
4. **Assinatura** (o pinentry pede a sua senha):

   ```
   gpg --local-user CFCFACF00335DC74 --armor --detach-sign \
     --output .claude/worktrees/fields-v1.4.4-rc.1.asc \
     .claude/plans/PLAN-198/verdict-fields-v1.4.4-rc.1.md
   ```

5. **Envelope:** `python3 .claude/plans/PLAN-198/kit/gen_envelope.py envelope --tag v1.4.4-rc.1 --sig .claude/worktrees/fields-v1.4.4-rc.1.asc`
6. **Commit e conferência** (a lista de arquivos vem do passo 5):

   ```
   git --literal-pathspecs add --pathspec-from-file=.claude/worktrees/commit-list-v1.4.4-rc.1.txt
   git status --short
   git commit -m "governance(PLAN-198): veredito pair-rail v1.4.4-rc.1 assinado + evidência do re-pass"
   python3 .claude/scripts/local/_release_tag_guard.py delta --tag v1.4.4-rc.1
   git push origin main
   ```

   O `git status --short` deve mostrar só os arquivos da lista. Espere a CI verde no commit
   do veredito.
7. **Tag:** `make mac-cut-rc` (sem `--push`). Ele roda o preflight, o bump (que agora não
   deve criar commit — se criar, pare e chame o Claude) e assina a tag localmente.
8. **Push da tag — irreversível:** `git push origin refs/tags/v1.4.4-rc.1`, até ~22 h depois
   do `generated_at`. Cria uma pré-release no GitHub; nada é publicado no npm.
9. **Conferência:** no `release.yml`, a validação do veredito e o passo de delta e
   ancestralidade verdes; no `npm-publish.yml`, "Await release-gate" e
   "RC toolchain proof (no publish)" verdes.

## Passo a passo — v1.4.4 (GA)

1. **Re-pass do GA**, com a main congelada (regra 2). Comece cedo o bastante para que a tag
   do GA possa sair ao mesmo tempo ≥ 24 h depois da tag rc e ≤ ~22 h depois do
   `generated_at` dos campos do GA — por exemplo, ~12 h depois da tag rc. Se houver condições
   do GA, elas são commitadas antes em `.claude/plans/PLAN-198/`:

   ```
   nohup bash .claude/plans/PLAN-198/kit/run_repass.sh --tag v1.4.4 \
     --conditions .claude/plans/PLAN-198/CONDITIONS-ga.md > /dev/null 2>&1 &
   tail -f .claude/worktrees/repass-ga.log
   ```

   A base continua sendo `v1.4.3-rc.1` (o kit a escolhe sozinho: a tag assinada mais nova
   abaixo de 1.4.4). O kit também confere a tag `v1.4.4-rc.1`: assinada, igual no GitHub,
   aceita pelo guarda de tag, e nada fora de `.claude/plans/PLAN-198/` mudou depois dela.
2. **Campos, assinatura, envelope, commit:** os passos 3 a 6 da rc com `--tag v1.4.4`,
   `fields-v1.4.4.asc` e `commit-list-v1.4.4.txt`.
3. **Tag**, pelo menos 24 h depois da tag rc: `make mac-cut-ga` (sem `--push`).
4. **Push da tag — irreversível:** `git push origin refs/tags/v1.4.4`.
5. **Publicação — irreversível:** no run do `npm-publish.yml`, aprove o ambiente
   `production-npm`.
6. **Conferência:** `npm view ceo-orchestration version` mostra `1.4.4`; tire do rascunho o
   GitHub Release (o `release.yml` cria o release do GA como rascunho).

## Se algo der errado

- **NO-GO (rc=1) na rc:** corrija e corte uma rc nova com o `release.sh` direto
  (`bump --rc 2 --npm-readme-reviewed`, depois `tag --rc 2`) — o `make mac-cut-rc` sempre
  corta a rc.1. O re-pass vira `--tag v1.4.4-rc.2` (pasta `repass-rc2/`) e o prazo de 24 h
  do GA recomeça.
- **NO-GO no GA:** mesma coisa: rc.2, novo prazo de 24 h.
- **Os campos passaram de ~22 h e o veredito ainda não foi commitado:** rode `fields` de
  novo e assine de novo; o re-pass não precisa ser refeito se a main não mudou.
  **Se o veredito já foi commitado e venceu, pare e chame o Claude.**
- **`verify`** (`gen_envelope.py verify --tag ... --sig ...`) refaz todas as checagens sem
  gravar nada; só funciona antes do commit do veredito.
- Uma tentativa nunca é apagada pelo kit. Para recomeçar do zero, mova a pasta
  `repass-<rc1|ga>/` para fora do repositório.

## O que o kit verifica

- **Candidato:** a main local é igual à do GitHub, árvore limpa, e a tag pedida bate com
  `VERSION` e com o `TARGET_BASE` do `release.sh`.
- **Base:** tag anotada, assinada por uma chave de `.claude/sentinel-signers.txt`, o mesmo
  objeto no GitHub, ancestral do candidato, aceita pelo guarda de tag atual (prova de que é
  o candidato revisado mais a evidência, nada além), e os campos do veredito dela conferem
  com a assinatura.
- **Partes:** o delta base..candidato é cortado abaixo do limite de entrada do redator
  ADR-114 (o que tira segredos e dados pessoais antes de enviar), passa por ele e é
  conferido (sem truncamento, mesmo número de linhas). Toda mudança fica numa parte ou numa
  classe declarada fora (`scope-<rc1|ga>.txt`).
- **Codex:** o runner só aceita o Codex que o oráculo do pin
  (`check_pair_rail.py --verify-codex-pin`) classifica como `verified` ou `compatible`, e o
  gerador recusa versão abaixo do piso do ADR-182 (`CODEX_VERSION_FLOOR`) **mesmo com o
  hash do manifesto** — o validador sozinho aceitaria. Status `verified` exige versão e hash
  iguais aos do manifesto; `compatible` exige versão mais nova que a do manifesto e hash
  diferente. O hash observado no início é conferido de novo no fim.
- **Gerador:** refaz cada parte a partir da base, do candidato, do kit e das condições e
  exige igualdade byte a byte com a evidência; exige `RUNNER-OVERALL: rc=0`, um veredito
  válido por revisão e parte, e nenhum NO-GO; recusa evidência de revisores simulados;
  recusa campos assinados sem `generated_at` ou com mais de 24 h.

## Limites declarados

- **Fora do re-pass, por classe:** testes; `.claude/plans/`; `docs/research/`; `CLAUDE.md`;
  `.claude/adr/`; dados de oráculo e de teste (`.claude/data/`, `.claude/scripts/data/`,
  `.claude/eval/`); `scripts/local/`; `conftest.py` e `pytest.ini`; `.gitignore`; `dist/`;
  as notas de trabalho da raiz (`RELATORIO-*.md`, `REVIEW.md`, `codex-planos/`); e os
  envelopes de veredito assinados. Fora do re-pass não quer dizer não entregue.
- **Hash do Codex mais novo que o manifesto:** com status `compatible` nenhum manifesto
  atesta os bytes do binário; o hash observado é a única identidade do instrumento, e o GA
  o congela.
- **Nunca rodou de verdade:** as opções da revisão do Claude vieram do `claude --help` da
  versão 2.1.316 (`--restricted`, `--tools`, `--permission-mode dontAsk`,
  `--output-format stream-json`); o teste usa revisores simulados. A primeira execução real
  é a prova. As mensagens de limite de conta do Codex foram medidas só na 0.160.0.
- **Tamanho:** sem prova mecânica de código movido, o delta inteiro desde `v1.4.3-rc.1`
  vai para revisão. Medido em 2026-11-03 sobre `v1.4.3-rc.1..7fad2972` com ~14 KB de
  condições: 281 caminhos em revisão, 32 partes, ou seja 64 revisões (32 do Codex e 32 do
  Claude). O candidato real terá alguns commits a mais. `--jobs N` (padrão 2) controla
  quantas partes rodam ao mesmo tempo; cuidado com a cota das duas contas.
- **Mesmo fornecedor:** parte do delta foi escrita pelo Codex e parte por agentes Claude;
  as duas revisões reduzem, mas não eliminam, o ponto cego de quem revisa o próprio texto.
