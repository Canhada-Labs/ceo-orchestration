# PLAN-156 — bom dia. Está tudo pronto para você assinar e landar.

> Rodei o PLAN-156 inteiro autônomo durante a noite (S269, 2026-07-12→13).
> **Todo o código está escrito, provado em clone limpo, e staged.** Falta
> só a sua parte inegociável por governança: **assinar os sentinels GPG e
> landar** — um único script faz tudo.

## O que fazer (2 passos)

```bash
cd ~/canhada-labs/ceo-orchestration
# 1. rode a cerimônia (assina 6 sentinels com sua chave AE9B, aplica staged,
#    commita, reconcilia counts, roda gates). Revise o script antes se quiser.
!bash .claude/plans/PLAN-156/land-plan156.sh
# 2. se tudo verde:
!git push origin main
```

O script para (`set -e`) em qualquer erro de assinatura/scope/gate — não
landa nada pela metade. Se o GPG reclamar de pinentry:
`export GPG_TTY=$(tty); gpgconf --kill gpg-agent` e rode de novo.

## O que foi construído (Owner directive S266: "ceo funciona no codex e no grok" + investigar GPT-5.6 + "conselho pra audit com codex e grok")

| Wave | Entrega | Prova |
|---|---|---|
| 0 | Caracterização empírica do grok 0.2.93 + codex 0.144.1 (8 lacunas resolvidas) | `artifacts/characterization-grok-codex-S269.md` + wire fixtures |
| 1 | Codex pin → `<0.145.0` (GPT-5.6 Sol/Terra/Luna); deprecações gpt-5.2/5.3-codex/gpt-5/o3 | binário 0.144.1 roda gpt-5.6-luna (provado) |
| 2 | Adapter `grok.py` + chokepoint exit-2/vocabulário no shim | `test_exit2_chokepoint` + live-fire (`artifacts/livefire-grok-S269.md`) |
| 3 | Templates grok + kill-switch guards (single-surface, OQ1 invertido por evidência) | `double-fire-count-S269.md` (count==1) |
| 4 | Audit chain grok (2 actions) + installer `--harness grok` | `test-install-harness-grok.sh` 9/9, hermético |
| 5 | Inverted pair-rail grok (Stop advisory, pre-push é a teeth) | pre-push gate + validate.yml rider |
| 6 | **Conselho cross-vendor** (`/council`) — Claude+Codex+Grok, fail-loud, egress redigido | `test-council-fixture.mjs` 11/11, zero egress |
| 7 | ADR-162 + docs + positive controls | live-fire 4/4 + docs (5 arquivos) |

**Verificação (clone limpo overlay):** ~549 testes targeted verdes cobrindo
TODO caminho de código tocado — exit2 chokepoint 78, gap (filewrite-reroute/
canonical/kernel/adapters/audit) 242, adapter golden+drift+seam, contract +
count guards, installer grok 9/9, council fixture 11/11 — + live-fire
determinístico 4/4, shellcheck 0 issues, contaminação limpa. O padrão
clone-limpo é a lição S266 (`feedback-ci-mirror-needs-clean-clone`).

**Nota sobre a suíte hooks INTEIRA:** ela pendura neste ambiente local (um
teste subprocess-heavy PRÉ-EXISTENTE, NÃO do PLAN-156 — confirmado excluindo
todos os meus testes novos e ainda pendurando; compete com processos de
background). No CI cada arquivo roda isolado, então o Validate deve fechar
verde. Se pintar vermelho, é quase certo um count-guard residual — rode
`check-audit-registry-coverage.py --check` + `check-claude-md-claims.py`.

## 6 bugs REAIS que a execução pegou (a verificação valeu, não foi teatro)

1. **`--force` não chegava ao grok** — install.sh só setava `CODEX_FORCE`.
   Pego pelo `test-install-harness-grok.sh` case 8. Corrigido.
2. **Coherence gate do grok denyava TODO edit legítimo** — eu checava o nome
   normalizado (`search_replace`→`Edit`, na lista Claude-native) em vez do raw
   do wire. Só o **live-fire** pegou (o fixture round-trip passou por cima — a
   lição S254 um nível acima). Corrigido: checa o nome raw.
3-4. **Pair-rail Codex rodada 1 (grok.py + shim)**: block→deny whitespace-
   fragile + precedência de event-source no chokepoint. Corrigidos+testados.
5. **CRÍTICO — pair-rail Codex rodada 2** (`codex review --uncommitted`,
   disparado pelo teu Stop hook): o single-surface `.claude/settings.json` NÃO
   setava `CEO_HOOK_ADAPTER=grok` → sob grok os hooks rodariam com adapter
   claude e misparse do wire camelCase → **enforcement silenciosamente
   quebrado**. Meu live-fire mascarou (eu setava o env na mão). Fix: o shim
   auto-detecta grok via `GROK_HOOK_EVENT` (grok injeta sempre) e seta o
   adapter. Provado SEM env manual: canonical deny funciona, benign passa.
6. **Contaminação**: fixtures grok vazavam `/Users/joaocanhada/.grok/...` —
   scrubbed p/ `/Users/dev` (10 arquivos, round-trip preservado). Também
   adicionei `grok_uninstall` (simetria de lifecycle com codex) e chmod +x no
   pre-push gate emitido (era 0600, git não executava). Todos com regressão.
   **Residual herdado (não corrigi)**: o pre-push gate herda do codex o
   `rev-list --not --all` que retorna vazio em branch novo — não diverjo só no
   grok; CODEOWNERS + branch-protection + CI são os backstops de AMBOS os gates.

## Decisões que precisam da sua ratificação (as OQs)

Já apliquei as recomendações do plano; confirme ou ajuste:

- **OQ1 (superfície de hooks) — INVERTI a recomendação original.** O plano
  recomendava `.grok/hooks/` nativo; a evidência (probe P8) mostrou que
  armar as duas superfícies (nativa + legacy `.claude/settings.json`)
  **double-fira** cada hook no grok 0.2.93, e nenhum kill switch para isso
  em runtime. Então o framework arma **só** a legacy `.claude/settings.json`
  (que já shippa) e guarda `.grok/hooks/**` para nada re-criar a segunda.
- **OQ2 (pin grok):** versão exata `0.2.93` + substrate-watch semanal (não
  range — cadência diária). ✅
- **OQ3 (modelos do council):** grok lane = `grok-4.5` (sua conta não expõe
  `grok-build-0.1`); codex refuters = default da conta (mude via
  `CEO_PAIR_RAIL_CODEX_MODEL`). ✅
- **OQ4 (codex target):** `>=0.128.0,<0.145.0` (widen-upper-only). Os 4 bugs
  0.144.0 triados: #31869 CLOSED upstream; #31873/#31860/#31826 não
  reproduzem no macOS 0.144.1. **Você elege:** rodar o locked-corpus
  catch_rate check na assinatura (precedente S246: rodar). O land script
  NÃO roda por padrão — rode manual se quiser antes de pushar.
- **OQ5 (council = privacidade/egress):** `/council` transmite o escopo
  auditado a **xAI + OpenAI** (redigido via ADR-114, não eliminado). É uma
  decisão de privacidade sua — o council é operator-only, nunca CI. Eu
  **não rodei nenhum council live** esta noite (só testei a lógica contra
  fixtures). O primeiro run live é seu, quando quiser.
- **OQ6 (budget council):** hard-kill default 120k tokens/lane (clamp
  [10k, 400k]). ✅

## Compromisso recorrente que você ratifica ao landar

Um terceiro harness proprietário 0.x com release diário adiciona uma
obrigação **semanal** de substrate-watch + re-fixture que **nenhum CI
automatiza** (não há binário/secret grok em runner). Está no
`substrate-watch.json` (item `grok_cli`, cadência semanal).

## Pré-requisitos que você já tem

- codex-cli **0.144.1** instalado ✅ (o pin bump assume isso)
- grok **0.2.93** logado via sessão ✅ (SuperGrok/X Premium+)
- chave GPG **AE9B236F…** no keyring ✅

## Se algo der errado

- Gate vermelho no land: o script para antes de commitar o closeout; os
  commits de sentinel já feitos ficam — investigue, corrija, e re-rode a
  partir do commit que falhou (ou `git reset --hard` para o anchor pré-land
  e recomece).
- Validate vermelho pós-push: os 3 testes novos são herméticos (zero
  binário grok no runner). Se vermelho, é quase certo um count-guard que eu
  não peguei — rode `check-audit-registry-coverage.py --check` e
  `check-claude-md-claims.py` localmente para o delta.

## Backlog: `/architect graduation` — precisa de você (não executei)

Você pediu "acaba com backlog". O único item estrutural que sobra é o
**`/architect graduation` dos 8 squads importados (cap 32→24)**, deferido
do PLAN-153. **Não executei** porque ele exige **decisões de design suas**
que não posso tomar autônomo: quais dos 37 domains graduam para squad
first-class, e para quanto muda o cap de spawn (32→24?). É um L3 que
precisa do próprio plano + debate. Todos os OUTROS residuais do backlog
daquele bloco já foram fechados (SP-042 landado `080a0c5`, PLAN-154/155
done, HMAC-483 encerrado, Task* matcher triado benigno). Quando quiser
atacar o architect graduation, me fale os critérios e eu drafto o PLAN-157.

Detalhes técnicos completos: o plano em
`.claude/plans/PLAN-156-grok-harness-56-refresh-council.md` + os artifacts.
