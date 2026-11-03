# Kit do veredito pair-rail — PLAN-198 (v1.4.4-rc.1 e v1.4.4)

Os mesmos quatro arquivos servem para a versão candidata (rc, de *release candidate*,
`v1.4.4-rc.1`) e para a versão final (GA, de *general availability*, `v1.4.4`). Só muda
o `--tag`. Nenhuma versão está escrita dentro do código.

| Arquivo | Para que serve |
|---|---|
| `run_repass.sh` | O re-pass: duas revisões separadas do mesmo material — Codex (modelo da OpenAI, só leitura, sem a configuração pessoal do Codex) e Claude Code (`claude -p`, só ferramentas de leitura, sem CLAUDE.md, skills, hooks nem servidores MCP, com o login de assinatura; nunca `--bare`, que exigiria chave de API paga). Grava a evidência em `.claude/plans/PLAN-198/repass-rc1/` (rc) ou `repass-ga/` (GA). |
| `gen_envelope.py` | Gera os campos para você assinar (`verdict-fields-<tag>.md`) e, depois da assinatura, o envelope do veredito (`.claude/governance/pair-rail-verdict-<tag>.md`). Antes de gravar qualquer um dos dois, roda o validador real do passo 15 do `release.yml` sobre o próprio resultado. Também tem as checagens de antes do corte (`precut`) e o gerador das condições do GA (`carry-conditions`). |
| `test-kit.sh` | Teste descartável do kit: repositório falso numa pasta temporária, chave GPG (programa de assinatura) descartável, revisores simulados. Não toca este repositório nem a rede. |
| `README.md` | Este texto. |

Siglas e termos: CI = integração contínua (os workflows do GitHub); SHA = identificador de
um commit; ADR = registro de decisão de arquitetura; npm = registro público de pacotes;
UTC = horário universal; API = interface de programação (aqui: acesso pago por chave, fora da
assinatura); hash = impressão digital de um arquivo (muda se um byte mudar); pin = versão
fixada de uma ferramenta; bump = troca do número da versão nos arquivos; preflight =
checagens antes do corte; delta = o que mudou entre dois commits; pinentry = a janela que
pede a senha da sua chave GPG; re-pass = a revisão do delta inteiro antes de cada tag.

## Quatro regras que valem da derivação dos metadados da release até o push da tag do GA

1. **Não atualize o Codex nem o Claude Code.** O re-pass grava a versão e o hash do binário
   do Codex e a versão do Claude Code como identidade dos revisores; o GA recusa um Codex
   diferente do da rc, e uma troca durante o re-pass faz ele parar com `rc=3`.
2. **A main fica congelada.** Só entram: os commits da própria cerimônia relmeta-144 (os
   materiais e o land assinado); o commit do bump; o commit do veredito de cada tag; e
   `CONDITIONS-ga.md`, só entre o push da tag rc e o início do re-pass do GA. Durante um
   re-pass (do início até o push da tag dele) só entra o commit do veredito dessa tag —
   qualquer outro commit invalida o re-pass inteiro. A VM do Codex não faz merge nessa janela.
   Todo commit cita no assunto só planos que estão no `RELEASE_SCOPE` do `release.sh`; o kit
   recusa se a faixa desde a v1.4.2 citar outro plano ou tocar um ADR fora dele (a linha
   `Scope:` da tag assinada ficaria falsa).
3. **Nunca use `MAC_RELEASE_ARGS=--push`.** `make mac-cut-rc` e `make mac-cut-ga` com
   `MAC_RELEASE_ARGS=--push` enviam a main e a tag **automaticamente, sem pedir
   confirmação** — e, se o bump criar um commit, enviam esse commit também. Sem `--push`
   eles só assinam a tag localmente; o envio fica com você.
4. **Nunca apague nem edite `.claude/worktrees/repass-attempts.log`.** É o registro de todas
   as tentativas de re-pass (encadeado por hash); os campos que você assina listam as
   tentativas da tag, e um NO-GO registrado bloqueia aquele commit para sempre, com qualquer tag
   (uma rc.2 sobre o mesmo commit também é recusada).

## Janelas de tempo

- O validador do passo 15 recusa um veredito com mais de **24 h** no momento em que o
  `release.yml` roda. Envie a tag até **~22 h** depois do `generated_at` dos campos (a
  margem cobre a fila da CI). O `generated_at` aparece na saída do `fields`.
- A tag do GA precisa ser criada **pelo menos 24 h depois** da criação da tag rc (o
  `release.yml` compara as datas de criação das duas tags).
- Workflows agendados também rodam sobre o commit congelado: todo dia Ownership Nightly
  (06:43 UTC), Coverage (07:00), Validate (07:37, com pernas que o push não roda, como o
  Python 3.14) e mcp-smoke (11:00); outros às segundas e no dia 1.º. O `precut` lista todos.

## Passo a passo — v1.4.4-rc.1

0. **Decisões e preparação (o Claude prepara, você decide):**
   1. Os seus dois commits de correção (Caminho 1+) já estão no main, assinados, abaixo das
      notas, do plano e deste kit: o filtro de segredos, e a lista do kernel com o timeout do
      Coverage.
   2. As decisões OQ-1 a OQ-7 do `PLAN-198-release-v1-4-4.md` ficam registradas no plano.
   3. O Claude escreve `.claude/plans/PLAN-198/CONDITIONS-rc1.md` (o texto que você assina
      junto com o veredito) e o commita com um assunto que cita só o PLAN-198.
   4. **Cerimônia relmeta-144 (você assina):** `release.sh` com `TARGET_BASE="1.4.4"` e
      `RELEASE_TITLE`, `RELEASE_SCOPE` e `RELEASE_HEADLINE` derivados de `v1.4.2..HEAD`; a
      linha do `release.sh` no manifesto de gate-scripts e o `test_release_bump_sites.py`
      fixados de novo. Os materiais são o último land antes do SIGN. SIGN → land → push (leva
      também os commits acima, se nenhum foi enviado antes) → CI verde. **O congelamento
      (regra 2) começa na derivação.** Sem essa cerimônia o bump não faz nada e o re-pass
      recusa.
   5. Espere um ciclo diário do Validate no commit do land e confira:
      `python3 .claude/plans/PLAN-198/kit/gen_envelope.py precut --tag v1.4.4-rc.1 --ci-only --require-schedule`
1. **Bump.** Releia `npm/README.md`. Depois:
   `bash .claude/scripts/local/release.sh bump --rc 1 --npm-readme-reviewed`,
   `git push origin main`, e espere a CI verde no commit do bump.
2. **Re-pass** (leva horas; pode rodar em segundo plano):

   ```
   nohup bash .claude/plans/PLAN-198/kit/run_repass.sh --tag v1.4.4-rc.1 \
     --conditions .claude/plans/PLAN-198/CONDITIONS-rc1.md > /dev/null 2>&1 &
   tail -f .claude/worktrees/repass-rc1.log
   ```

   A última linha do log é sempre `runner exit rc=N` (com um `--tag` ilegível o log é
   `.claude/worktrees/repass-unknown.log`):
   `0` = as duas revisões aprovaram todas as partes; `1` = alguma revisão disse NO-GO ou
   não deu veredito legível (não há veredito: chame o Claude para a triagem); `2` = recusa
   antes de qualquer envio (leia a linha `REFUSED:` logo acima); `3` = uma revisão morreu
   (limite da conta, queda, tempo esgotado, sinal) ou o fechamento recusou: depois do reset
   rode **o mesmo comando com `--resume`**. Para parar no meio: `kill <pid do runner>` — ele
   encerra os revisores antes de sair (`rc=3`; depois `--resume`).
3. **Campos:** `python3 .claude/plans/PLAN-198/kit/gen_envelope.py fields --tag v1.4.4-rc.1`.
   Leia em `.claude/plans/PLAN-198/verdict-fields-v1.4.4-rc.1.md` as `conditions`, as
   `lane_notes` (o que cada revisão disse além do veredito: condições e achados P0/P1) e as
   `attempts` (todas as tentativas desta tag).
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
7. **Tag:** primeiro
   `python3 .claude/plans/PLAN-198/kit/gen_envelope.py precut --tag v1.4.4-rc.1` (confere o
   `RELEASE_SCOPE` e que **todos** os workflows sobre o HEAD, agendados inclusive, terminaram
   verdes); depois `make mac-cut-rc` (sem `--push`). Ele roda o preflight, o bump (que agora
   não deve criar commit — se criar, pare e chame o Claude) e assina a tag localmente.
8. **Push da tag — irreversível:** `git push origin refs/tags/v1.4.4-rc.1`, até ~22 h depois
   do `generated_at`. Cria uma pré-release no GitHub; nada é publicado no npm.
9. **Conferência:** no `release.yml`, a validação do veredito e o passo de delta e
   ancestralidade verdes; no `npm-publish.yml`, "Await release-gate" e
   "RC toolchain proof (no publish)" verdes.

## Passo a passo — v1.4.4 (GA)

1. **Condições do GA (o Claude faz, obrigatório):** depois do push da tag rc e antes do
   re-pass do GA,
   `python3 .claude/plans/PLAN-198/kit/gen_envelope.py carry-conditions --tag v1.4.4`
   escreve `.claude/plans/PLAN-198/CONDITIONS-ga.md` com todas as condições e `lane_notes`
   que você assinou na rc; o Claude acrescenta as do GA no fim, commita (assunto cita só o
   PLAN-198), faz push e espera a CI verde. O runner recusa o GA se faltar alguma linha
   assinada na rc.
2. **Re-pass do GA**, com a main congelada (regra 2). Comece cedo o bastante para que a tag
   do GA possa sair ao mesmo tempo ≥ 24 h depois da tag rc e ≤ ~22 h depois do
   `generated_at` dos campos do GA — por exemplo, ~12 h depois da tag rc:

   ```
   nohup bash .claude/plans/PLAN-198/kit/run_repass.sh --tag v1.4.4 \
     --conditions .claude/plans/PLAN-198/CONDITIONS-ga.md > /dev/null 2>&1 &
   tail -f .claude/worktrees/repass-ga.log
   ```

   A base continua sendo `v1.4.3-rc.1` (o kit a escolhe sozinho: a tag assinada mais nova
   abaixo de 1.4.4). O kit também confere a tag `v1.4.4-rc.1`: assinada, igual no GitHub,
   aceita pelo guarda de tag, e nada fora de `.claude/plans/PLAN-198/` mudou depois dela.
3. **Campos, assinatura, envelope, commit:** os passos 3 a 6 da rc com `--tag v1.4.4`,
   `fields-v1.4.4.asc` e `commit-list-v1.4.4.txt`.
4. **Tag**, pelo menos 24 h depois da tag rc:
   `python3 .claude/plans/PLAN-198/kit/gen_envelope.py precut --tag v1.4.4`, depois
   `make mac-cut-ga` (sem `--push`).
5. **Push da tag — irreversível:** `git push origin refs/tags/v1.4.4`.
6. **Publicação — irreversível:** no run do `npm-publish.yml`, aprove o ambiente
   `production-npm`.
7. **Conferência:** `npm view ceo-orchestration version` mostra `1.4.4`; tire do rascunho o
   GitHub Release (o `release.yml` cria o release do GA como rascunho).

## Se algo der errado

- **`precut` recusa por um workflow vermelho ou cancelado no HEAD:** `gh run rerun <id> --failed`
  e rode o `precut` de novo. **Nunca commite uma correção** — ela quebra o delta do veredito.
  Um vermelho que se repete é uma rc nova (abaixo).
- **NO-GO (rc=1) na rc** — nessa ordem:
  1. mova `.claude/plans/PLAN-198/repass-rc1/` para uma pasta fora do repositório; nunca
     rode `git add -A` com ela lá. O registro de tentativas
     guarda o NO-GO, e o kit recusa para sempre o mesmo commit;
  2. corrija, commit (assunto com planos do `RELEASE_SCOPE`, senão a relmeta é refeita),
     push, CI verde;
  3. `bash .claude/scripts/local/release.sh bump --rc 2 --npm-readme-reviewed` (se criar
     commit: push e CI verde);
  4. re-pass com `--tag v1.4.4-rc.2` (pasta `repass-rc2/`), depois campos, assinatura,
     envelope, commit, push e CI verde;
  5. `bash .claude/scripts/local/release.sh preflight --rc 2` (a única checagem de CI do
     `release.sh`; a fase `tag` não tem) e `gen_envelope.py precut --tag v1.4.4-rc.2`;
  6. `bash .claude/scripts/local/release.sh tag --rc 2` (o `make mac-cut-rc` sempre corta a
     rc.1), push da tag. O prazo de 24 h do GA recomeça.
- **NO-GO no GA:** mesma coisa: rc.2, novo prazo de 24 h.
- **`rc=3` com "finalize refused":** o `.header` e os registros das revisões voltam para a
  pasta; corrija a causa (a linha `REFUSED:`) e rode o mesmo comando com `--resume` — nenhuma
  revisão concluída roda de novo.
- **Os campos passaram de ~22 h e o veredito ainda não foi commitado:** rode `fields` de
  novo e assine de novo; o re-pass não precisa ser refeito se a main não mudou.
  **Se o veredito já foi commitado e venceu, pare e chame o Claude.**
- **`verify`** (`gen_envelope.py verify --tag ... --sig ...`) refaz todas as checagens sem
  gravar nada; só funciona antes do commit do veredito.
- Uma tentativa nunca é apagada pelo kit. Para recomeçar do zero depois de uma queda, mova a
  pasta `repass-<rc1|ga>/` para fora do repositório; a tentativa continua no registro.
- **O registro de tentativas recusa ("not an unbroken chain"):** pare e chame o Claude.

## O que o kit verifica

- **Candidato:** a main local é igual à do GitHub, árvore limpa, e a tag pedida bate com
  `VERSION` e com o `TARGET_BASE` do `release.sh`.
- **Escopo assinado:** todo `PLAN-NNN` citado nos assuntos de commit desde a última tag GA
  (v1.4.2) e todo ADR tocado estão no `RELEASE_SCOPE` (no `prepare`, nos campos, no
  envelope, no `verify` e no `precut`).
- **Base:** tag anotada, assinada por uma chave de `.claude/sentinel-signers.txt`, o mesmo
  objeto no GitHub, ancestral do candidato, aceita pelo guarda de tag atual (prova de que é
  o candidato revisado mais a evidência, nada além), e os campos do veredito dela conferem
  com a assinatura.
- **Partes:** o delta base..candidato é cortado abaixo do limite de entrada do redator
  ADR-114 (o que tira segredos e dados pessoais antes de enviar), passa por ele e é
  conferido (sem truncamento, mesmo número de linhas e de blocos). O redator recebe o texto
  original — o cabeçalho com as condições e o diff. Só depois, na saída dele, os caracteres que a
  normalização Unicode NFKC muda (reticências, "№") são mostrados como `<U+XXXX>`, para leitura,
  e o resultado tem de ser estável sob NFKC. Antes de redigir, o kit confere que o redator do
  candidato tira inteira uma chave de teste escrita depois de um caractere que o NFKC muda (a
  correção do seu commit do filtro de segredos, abaixo deste kit); se sobrar qualquer pedaço,
  recusa. Toda mudança fica numa parte ou numa classe declarada fora (`scope-<rc1|ga>.txt`).
- **Revisores:** cada um num grupo de processos próprio, com limite de 2 h, a partir de uma
  cópia do candidato **fora do repositório** e sem os arquivos `CLAUDE.md`/`AGENTS.md`
  (que os programas leriam como instrução). Codex com `--ignore-user-config --ephemeral
  --ignore-rules` e apps, plugins, hooks, navegador e memórias desligados; Claude Code com
  `--restricted --safe-mode --strict-mcp-config`, o binário da versão (não o atalho que se
  atualiza sozinho) e a atualização automática desligada. A versão do Claude Code e o hash
  do Codex são conferidos de novo no fim; quando o Claude Code relata o modelo (no evento
  de início do `stream-json`), o nome relatado tem de começar pelo nome pedido.
- **Codex:** o runner só aceita o Codex que o oráculo do pin
  (`check_pair_rail.py --verify-codex-pin`) classifica como `verified` ou `compatible`, e o
  gerador recusa versão abaixo do piso do ADR-182 (`CODEX_VERSION_FLOOR`) **mesmo com o
  hash do manifesto** — o validador sozinho aceitaria. Status `verified` exige versão e hash
  iguais aos do manifesto; `compatible` exige versão mais nova que a do manifesto e hash
  diferente.
- **Limite de conta:** as mensagens do Codex (`ERROR:` no fim do log) e as do Claude Code
  ("You've hit your limit", de sessão, semanal ou de gasto, também no campo `errors`) param
  o envio de partes novas e gravam `.quota`.
- **Gerador:** refaz cada parte a partir da base, do candidato, do kit e das condições e
  exige igualdade byte a byte com a evidência; exige `RUNNER-OVERALL: rc=0`, um veredito
  válido por revisão e parte, e nenhum NO-GO — nem desta tentativa nem de tentativa anterior
  do mesmo commit no registro, com qualquer tag; recusa evidência de revisores simulados; recusa campos
  assinados sem `generated_at`, com mais de 24 h ou no futuro; no GA, exige que as condições
  carreguem todas as linhas assinadas na rc.

## Limites declarados

- **Fora do re-pass, por classe:** testes; `.claude/plans/`; `docs/research/`; `CLAUDE.md`;
  `.claude/adr/`; dados de oráculo e de teste (`.claude/data/`, `.claude/scripts/data/`,
  `.claude/eval/`); `scripts/local/`; `conftest.py` e `pytest.ini`; `.gitignore`; `dist/`;
  as notas de trabalho da raiz (`RELATORIO-*.md`, `REVIEW.md`, `codex-planos/`); e os
  envelopes de veredito assinados. Fora do re-pass não quer dizer não entregue.
- **Revisões separadas, não isoladas:** nenhuma acha a resposta da outra subindo pastas a
  partir da cópia, mas o modo só leitura do Codex lê qualquer arquivo do seu usuário; nada
  impede um revisor de abrir a pasta da evidência pelo caminho completo.
- **Opções lidas, nunca rodadas de verdade:** as do Claude Code vêm do `claude --help` da
  2.1.316 (`--restricted`, `--safe-mode`, `--tools`, `--permission-mode dontAsk`,
  `--output-format stream-json`); as do Codex, do `codex exec --help` da 0.166.0
  (`--ignore-user-config`, `--ephemeral`, `--ignore-rules`; a 0.160.0 do manifesto pode não
  tê-las — o runner confere e recusa antes de enviar). O `--safe-mode` não cita a memória
  automática; a cópia numa pasta nova faz a memória deste projeto não casar, mas não há
  prova de que memória nenhuma carrega. As mensagens de limite foram medidas no Codex 0.160.0
  e em transcrições interativas do Claude Code, não no `claude -p`. O teste usa revisores
  simulados; a primeira execução real é a prova.
- **`kill -9` no runner** não deixa ele encerrar os revisores; eles terminam sozinhos ou pelo
  limite de 2 h.
- **Registro de tentativas:** encadeado por hash, então editar uma linha é detectado; apagar
  o arquivo inteiro não é (mesmo usuário). Por isso a regra 4.
- **Redator ADR-114:** o desvio de posição depois de caracteres que o NFKC muda foi corrigido
  na biblioteca (`_lib/secret_patterns.py`) mais cedo neste trem, no seu commit de correção do
  filtro de segredos, que fica abaixo deste kit. O kit redige o texto original e só depois
  aplica o `<U+XXXX>` (`nfkc_safe()`, só exibição); confere a correção com uma chave de teste
  antes de redigir. O `test-kit.sh` usa cópias reais do redator corrigido e tem um controle
  negativo: um segredo depois de um `=` de largura total (U+FF1D) não chega ao payload.
- **Hash do Codex mais novo que o manifesto:** com status `compatible` nenhum manifesto
  atesta os bytes do binário; o hash observado é a única identidade do instrumento, e o GA
  o congela.
- **Tamanho:** sem prova mecânica de código movido, o delta inteiro desde `v1.4.3-rc.1`
  vai para revisão. Medido em 2026-11-03 sobre `v1.4.3-rc.1..7fad2972` com ~14 KB de
  condições: 281 caminhos em revisão, 32 partes, ou seja 64 revisões (32 do Codex e 32 do
  Claude) — antes do `<U+XXXX>`, que aumenta um pouco o tamanho. O candidato real terá
  alguns commits a mais. `--jobs N` (padrão 2) controla quantas partes rodam ao mesmo tempo;
  cuidado com a cota das duas contas.
- **Mesmo fornecedor:** parte do delta foi escrita pelo Codex e parte por agentes Claude;
  as duas revisões reduzem, mas não eliminam, o ponto cego de quem revisa o próprio texto.
