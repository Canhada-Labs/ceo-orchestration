---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: null
generated_at: 2026-08-05T00:00:00Z
---

## Verdict

ADJUST — a tese e as waves estão corretas, mas a direção mecânica proposta
para OQ-1 (F1) é subótima: existe uma terceira opção (reusable workflow via
`workflow_call`) que fecha a mesma lacuna sem os riscos de OIDC/race que (a)
e (b) carregam, e o fix de F2 precisa mudar de camada (idempotência por-site,
não diff-mask pós-hoc) para ser testável sob relógio controlado.

## Summary (≤ 3 bullets)

- O plano corrige 6 findings reais de um NO-GO do codex; verifiquei os 6
  contra o código (`release.yml`, `npm-publish.yml`, `release-v1-2-0.sh`,
  `install.sh`/`upgrade.sh`, `test_install_baseline_manifest.sh:117`) e
  **todos se confirmam** — nenhum é falso-positivo do re-pass.
- Ponto forte: as waves W0/W1/W2 sequenciam corretamente livre→canonical→
  release, e o AC-2 já exige controle positivo (gate red → publish não
  roda) — coerente com a doutrina do repo.
- Ponto fraco: OQ-1 só considera "poll via `gh api`" ou "mover pra dentro
  de `release.yml`" — ambas piores que uma terceira opção (reusable
  workflow) que nenhum dos dois documentos (plano nem verdito) menciona; e
  o fix de F2 proposto na v-atual do driver (`git diff --cached --quiet`)
  já existe mas **não cobre exatamente o caso que F2 descreve** (re-datar
  stamps num dia diferente ainda suja o índice).

## Risks

- **R-DEVOPS1 — CRITICAL.** OQ-1 opção (b) ("mover o publish pra dentro de
  `release.yml` com `needs: release-gate`") muda o **filename** que executa
  o job de publish. `PLAN-158/oidc-failure-playbook.md:18` documenta
  explicitamente: *"the workflow FILENAME must match, not the display
  name"* no registro de Trusted Publisher do npmjs.com. Trocar o arquivo
  sem reconfigurar o npmjs.com PRIMEIRO faz o próximo GA falhar com
  `ENEEDAUTH`/`E403` — falha fechada (não publica), mas custa um ciclo de
  release inteiro (24h de hold reinicia, per ADR-103) exatamente como o
  plano já reconhece em §Riscos. Mitigação: não escolher (b) sem uma
  reconfiguração coordenada e JANELADA no npmjs.com — ou, preferível,
  evitar a opção inteira (ver Unseen).
- **R-DEVOPS2 — HIGH.** OQ-1 opção (a), como literalmente descrita ("step
  pré-publish que verifica conclusão SUCCESS do `release.yml` para o MESMO
  SHA via poll de `gh api`"), tem uma race window real: `release.yml` e
  `npm-publish.yml` disparam do MESMO evento de push, mas o dispatcher do
  GitHub não garante ordem — nos primeiros segundos, `gh run list
  --workflow release.yml --json headSha,conclusion` pode retornar **zero
  runs** simplesmente porque o run de `release.yml` ainda não foi
  registrado, não porque ele falhou. Um poll ingênuo que trata "vazio" como
  "falhou" quebra TODA release; um poll que trata "vazio" como "ok, segue"
  reabre exatamente o buraco que F1 fecha. Mitigação: distinguir três
  estados (`not-yet-created` / `running` / `concluded:{success,failure}`) e
  falhar fechado (não publicar) se o orçamento de tempo estourar em
  qualquer estado que não seja `concluded:success`.
- **R-DEVOPS3 — HIGH.** `npm-publish.yml:68` tem `timeout-minutes: 8`.
  `release.yml`'s `release-gate` (`release.yml:17`) tem `timeout-minutes:
  20` e inclui suíte de hooks+scripts+replay, smoke install, SBOM, GPG
  verify e validação do pair-rail verdict — plausivelmente >8min sozinho.
  Qualquer variante de (a) que espere `release-gate` terminar ANTES de
  publicar precisa aumentar esse timeout (proponho 30-35min) — se isso não
  for feito, o job de publish morre por timeout ANTES do gate concluir, o
  que é fail-closed (bom) mas silenciosamente quebra o fluxo documentado no
  `.github/release-checklist.md` (Owner vendo "NPM Publish" vermelho sem
  entender que é só timeout curto, não falha real).
- **R-DEVOPS4 — MEDIUM.** `.claude/scripts/tests/test_release_workflow_asserts.py`
  é um teste PINADO com invariantes estruturais sobre `release.yml` e
  `npm-publish.yml` — inclusive `test_all_action_uses_are_sha_pinned`
  (linha 230) e `test_workflows_parse_as_yaml` (linha 216), que iteram
  literalmente `("release.yml", "npm-publish.yml")`. Se F1 introduzir um
  NOVO arquivo de workflow (ex.: `_release-gate.yml` reusável), esse novo
  arquivo fica **fora** da varredura de SHA-pin até alguém lembrar de
  adicioná-lo à tupla — exatamente a classe "unwatched surface" que este
  repo já pagou caro em outras rodadas (README.pt-BR/F5 é a MESMA classe).
  Mitigação: qualquer novo arquivo `.github/workflows/*.yml` introduzido
  pelo fix de F1 entra na tupla de `WorkflowHygieneTest` no MESMO commit.
- **R-DEVOPS5 — MEDIUM.** `NpmPublishRcPostureTest.test_rc_exclusion_precedes_publish_command`
  (linha 161) faz um assert de ORDEM textual: a string de exclusão de RC
  precisa aparecer antes de `"npm publish --provenance"` NO MESMO ARQUIVO.
  Se a opção (b) mover o publish para `release.yml`, esse teste (e o
  `test_rc_exclusion_survives_wave_b`/`WaveB5NpmPublishYmlTest`) precisa
  ser reescrito — outro motivo para preferir uma direção que deixe
  `npm-publish.yml` estruturalmente intacto.

## Must-fix (blocking)

1. **OQ-1 — reavaliar a favor de reusable workflow (`workflow_call`).**
   Extrair o job `release-gate` de `release.yml` para um arquivo NOVO
   (`.github/workflows/_release-gate.yml`, `on: workflow_call` apenas,
   sem trigger próprio). `release.yml` chama via
   `gate: uses: ./.github/workflows/_release-gate.yml` +
   `publish-release: needs: gate`. `npm-publish.yml` GANHA um job
   equivalente (`gate: uses: ./.github/workflows/_release-gate.yml`) e o
   job `publish` existente ganha `needs: gate` — mantendo `on: push: tags:
   v*`, `environment: production-npm` e o guard `if:
   !contains(github.ref, '-rc.')` EXATAMENTE como estão hoje. Isso fecha
   F1 com: (i) zero mudança de OIDC — o filename `npm-publish.yml`
   continua sendo quem publica, nenhuma reconfiguração no npmjs.com; (ii)
   zero race window — `needs:` dentro do MESMO workflow run é ordenação
   determinística nativa do GitHub Actions, não polling; (iii) semântica
   de re-run padrão (re-rodar o job `gate` refaz o gate, `publish` some
   até `needs` resolver de novo); (iv) UX do operador melhora
   estritamente: hoje a aprovação manual do `production-npm` acontece
   SEM saber se `release-gate` passou (são workflows independentes); com
   `needs: gate`, o job só fica "Waiting" para aprovação DEPOIS do gate
   verde — o clique do Owner passa a acontecer depois de uma garantia
   mecânica, não de um "confiar que eu chequei a outra aba". Custo aceito:
   o gate roda DUAS VEZES por tag (uma vez por workflow) — CI duplicado
   em paralelo (mesmo wall-clock, ~2x minutos faturados), evento raro
   (poucas releases/mês), custo desprezível frente a poll-loop/merge.
2. **F2 — mover o fix para dentro do laço de substituição, não para um
   diff-mask pós-hoc.** O código atual (`release-v1-2-0.sh:417-433`) já
   trata "nada staged" como no-op (fix do r4), mas os 4 sites
   `last-reviewed:` (`npm/README.md:347-349`, `SBOM.md:360-362`,
   `SECURITY.md:363-364`, `VERSIONING.md:365-366`) substituem a data
   incondicionalmente com `datetime.date.today()` — então, no dia
   seguinte ao RC (exatamente o cenário que o hold de 24h da ADR-103
   GARANTE), a data muda mesmo quando a VERSÃO não muda, o índice fica
   sujo, e o no-op do r4 nunca dispara. Fix correto: dentro do laço
   Python de `SITES`, para os 4 sites de `last-reviewed:`, capturar a
   versão já presente na stamp ANTES de substituir; se já for igual a
   `target`, pular a linha inteira (não tocar nem a data nem a versão).
   Isso é a opção (a) do OQ-2 ("no-op TOTAL"), implementada na MESMA
   função que já é dona de todas as mutações do bump — não uma segunda
   camada que precisa reconstruir "quais hunks do diff são só-data"
   (opção b), que é mais frágil e mais difícil de auditar.
3. **F2 — testabilidade do fix exige extrair a lógica de substituição do
   heredoc.** O bloco `python3 - <<'PY' ... PY` (linhas 330-382) não é
   importável — um teste de regressão "next-day" com relógio mockado
   (exigido pelo AC-1) não consegue monkeypatchar `datetime.date.today()`
   dentro de um subprocesso heredoc sem gambiarra de `PYTHONPATH`/
   `sitecustomize`, e este repo é stdlib-only (sem `freezegun`). Fix:
   mover o corpo da função de substituição para um módulo importável
   (ex.: `.claude/scripts/local/_release_bump_sites.py`) que recebe
   `today` como PARÂMETRO EXPLÍCITO (nunca `datetime.date.today()`
   embutido — mesma lição já registrada na memória deste repo sobre
   parâmetros que mudam o veredito não terem default), chamado tanto
   pelo driver bash (`python3 .claude/scripts/local/_release_bump_sites.py
   --target X --today "$(date -I)"`) quanto por um teste pytest que passa
   datas D e D+1 explícitas sem tocar o relógio real.
4. **F1 — cobertura de teste pinada para a nova superfície.** Qualquer
   direção escolhida para F1 precisa de um teste estrutural NOVO em
   `test_release_workflow_asserts.py` (padrão `assertIn` das classes
   `WaveB5*` já existentes) que falha se a chamada/dependência de gate for
   removida — senão o próprio fix de F1 vira uma "unwatched surface" nova.
   E qualquer arquivo `.yml` novo entra nas tuplas de
   `WorkflowHygieneTest` (R-DEVOPS4).
5. **F6 — duas ocorrências do "SIX sites"/claim falsa de publish que nem o
   plano nem o verdito citam.** Verifiquei o arquivo linha a linha:
   - `release-v1-2-0.sh:19` repete **literalmente a mesma claim falsa**
     que a linha 515 ("git push ... starts `release.yml` (which publishes
     to npm via OIDC)") — o verdito só cita `:515`. Corrigir só `:515` e
     deixar `:19` intocado é reintroduzir a claim falsa no cabeçalho do
     próprio arquivo.
   - `release-v1-2-0.sh:268` (`note "... becomes $TARGET_BASE in the bump
     phase (6 sites)"`) é uma QUARTA ocorrência de "seis sites" além das
     três que o verdito cita (`:3`, `:37`, `:290`) — hoje são >10 sites
     distintos na tabela `SITES` (linhas 339-366). Se o fix de F6 seguir
     só as linhas citadas pelo verdito, essa fica pra trás.

## Nice-to-have (advisory)

1. `permissions:` do novo `_release-gate.yml` reusável: para reusable
   workflows via `workflow_call`, as permissões efetivas são o mínimo
   entre o que o job chamador concede e o que o workflow reusável declara
   — vale um smoke test dedicado (`gh run list` dentro do gate precisa de
   `actions: read`) na primeira execução real, não só leitura de docs do
   GitHub.
2. O nome do arquivo do driver (`release-v1-2-0.sh`) em si já é uma claim
   de versão desatualizada mais visível que qualquer comentário interno —
   fora do escopo de F6 (a verdict não cita o filename), mas vale nomear
   explicitamente no debate: renomear tem custo de ripple (todo
   `.github/release-checklist.md`, `RELEASE.md` e memória referenciam o
   nome atual) — se a decisão for NÃO renomear agora, ao menos um
   comentário de topo dizendo "nome é histórico, não o alvo" evita
   confusão futura sem o custo de rename.
3. `CEO_SOTA_DISABLE` hoje só guarda `release-gate` dentro de
   `release.yml` (`if: vars.CEO_SOTA_DISABLE != '1'`, `release.yml:15`).
   Se F1 adotar o reusable workflow, os DOIS call-sites (`release.yml` e
   `npm-publish.yml`) precisam decidir explicitamente se o kill-switch
   também deve suprimir o gate de publish — não deixar isso implícito só
   porque "copiei o `if:` do job antigo".

## Unseen by the original plan

1. **Terceira opção mecânica pra OQ-1 (reusable workflow) não foi
   considerada** nem pelo plano nem pelo verdito do codex — ambos só
   comparam poll-loop vs. merge-into-release.yml. É estritamente melhor
   nos 5 eixos pedidos (OIDC compat: preservada; race window: zero;
   re-run: semântica nativa do GHA; falha sob outage: nível de job
   normal, sem loop pendurado; UX do operador: aprovação manual passa a
   acontecer DEPOIS do gate verde, fechando um gap que existe HOJE — a
   aprovação de `production-npm` atualmente não tem NENHUMA garantia
   mecânica de que `release-gate` passou, só a expectativa de que o Owner
   olhe as duas abas).
2. **A claim falsa de F1 ("release.yml publica no npm") aparece DUAS
   vezes no arquivo** (`:19` e `:515`), não uma — nenhum dos dois
   documentos de debate cita a duplicata.
3. **F3 e F4 são estruturalmente o MESMO buraco, verificado no código:**
   `install.sh:1300-1307` e `:1312-1322` chamam `install_one "SPEC/v1"` e
   `install_one "VERSION"` como passos 5c-bis/5c-bis-2 **fora** de
   `_framework_manifest_set.sh`; `upgrade.sh` (que SÓ usa
   `_framework_target_entries()` de `_framework_manifest_set.sh:105-107`)
   não tem chamada equivalente a `install_one "SPEC/v1"` nem
   `install_one "VERSION"` em lugar nenhum. Ou seja: os dois sites que F3
   diz que faltam no upgrade são, por construção, **invisíveis** para
   qualquer comparação que passe só por `_framework_target_entries()` —
   inclusive uma reescrita "independente" de F4 que ainda assim delegue
   para essa mesma função ficaria cega para exatamente essa classe de bug.
   Implicação pro fix de F4 (AC-4): a forma mais robusta não é escrever
   DUAS funções de enumeração independentes (que podem compartilhar o
   mesmo ponto cego mental do mesmo autor — a mesma classe de erro que
   gerou F3), e sim **executar install.sh e upgrade.sh de verdade sobre
   fixtures e diffar as árvores resultantes** (a segunda alternativa que
   o próprio verdito já sugere) — e essa execução pode reaproveitar o
   padrão "Smoke install on scratch directory" que `release.yml` já roda
   (linha 341-359), estendido com um smoke-UPGRADE equivalente. Isso fecha
   F3 e F4 com o MESMO mecanismo, em vez de dois patches separados.

## What I would NOT change

- **A ordem das waves (W0 livre → W1 canonical → W2 rc.2/hold/GA)** está
  correta e segue o padrão já provado deste repo (agrupar TODOS os
  patches canônicos numa cerimônia única, per `feedback-ceremony-scripts-
  must-sign-inline` / `feedback-staged-inputs-need-tracked-hash-
  manifest`). Não fragmentaria em mais cerimônias.
- **AC-2 já pede controle positivo explícito** ("gate red → publish não
  roda") — não amoleceria esse critério, e recomendo mantê-lo como
  critério de aceite MESMO se a direção mudar para reusable workflow (o
  controle positivo nesse caso é: gate falha dentro do `_release-gate.yml`
  chamado por `npm-publish.yml` ⇒ job `publish` nunca fica disponível,
  observável no `gh run view` daquela run).
- **A decisão de nunca fazer `npm-publish.yml` disparar em tags `-rc.*`**
  (RC posture, `PLAN-013` anti-goals #3/#16, re-ratificada em
  `PLAN-153`) está fora do escopo de F1 e o plano corretamente não mexe
  nela — qualquer direção de F1 que eu proponha preserva esse guard
  intocado.
- **`--dry-run` restaurando tree+index via trap** no driver — mecanismo já
  correto e testado (lição S273), não tocaria.
