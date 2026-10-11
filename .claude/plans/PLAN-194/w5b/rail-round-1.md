# rail-round-1 — W5b do PLAN-194 (rail oficial, rodada 1 de no máximo 3)

Rail-Round: 1
Rail-Subject: sombra w5b, `git diff 0a953ece..b03934b9` (1 commit; 3 caminhos, +181/−80) — antecessor do w5b.patch
Rail-Subject-patch-id: a1b6d49828967f03c7a2283234357277bd95d2d3
Rail-Reviewer: codex-cli 0.160.0 (pin assinado 4a1eec73), exec --sandbox read-only, modelo gpt-6-astra do config do usuário (sha256 9af51fe781bf86c1…, pelo preflight), reasoning xhigh; refutadores Claude r-w5b-a (DevOps) e r-w5b-b (Security Engineer)
Rail-Prompt: fora do repositório (prompt da rodada na sessão S363, 2026-10-09, scratchpad da sessão d876fa66, night/rail/w5b-r1/rail-prompt.md)
Rail-Date: 2026-10-09 (Codex: preflight 14:02:15Z, saída 14:45Z; lanes Claude registradas 14:13Z (r-w5b-b) e 14:55Z (r-w5b-a) — horários dos arquivos de registro, UTC)
Rail-Reviewer-Verdict: GO-WITH-CONDITIONS
Rail-Verdict: FINDINGS
Rail-Findings: P0=0 P1=0 P2=1

Registro informativo: o SIGN lê só o registro da ÚLTIMA rodada. Esta rodada revisou outros bytes (o sujeito
acima, identificado pelo patch-id estável), não o `w5b.patch`: o 4.º caminho (`docs/deny-baseline.md`) e as
curas entraram depois, em `210baa0b` e `01f94c78`.

## Saída do revisor

```text
**P3 — Offset incorreto na evidência:** [builder-report.md:11](<scratchpad>/night/rail/w5b-r1/builder-report.md:11).

No binário de SHA conferido, a chave começa em **187383022**. Reprodução, com `b` contendo seus bytes: `b.find(b"permission_mode_from_default_fallback", 180000000)` retorna esse valor. Em `187383255` está o trecho `auto mode is now the default`. **Cura:** corrigir o offset no relatório. A conclusão sobre o fallback permanece confirmada.

Sem achados funcionais. Reproduzidos F/G vermelhos no pai e A–H verdes no candidato. Smoke, D3, ownership e censo passaram; 704 entradas preservadas. Checkout limpo; fixtures e HOME descartável apagados.

VERDICT: GO-WITH-CONDITIONS
```

Caminho local do relatório do construtor redigido como `<scratchpad>` (o scratchpad da sessão d876fa66).

## Triagem

- Codex 0.160.0 (read-only): GO-WITH-CONDITIONS — um P3: o offset `187383255` do relatório do construtor não é
  o do nome `permission_mode_from_default_fallback` (que está em `187383022`), mas o do trecho «auto mode is
  now the default». Sem achado funcional; reproduziu F/G vermelhos no pai e A–H verdes no candidato; smoke, D3,
  ownership e censo verdes (704 entradas). Cura: offset corrigido na mensagem de `210baa0b` (o relatório do
  construtor é DADO fora do repositório e não foi editado).
- r-w5b-a (DevOps; instalador, controles e oráculos): GO. P3 doc (o opt-out não menciona o defaultMode) —
  curado em `210baa0b` (`docs/deny-baseline.md`); P3 de desenho (o opt-out da deny-baseline também desliga o
  defaultMode) — declarado no sentinel, decisão do Owner; P3 fora do patch (`test_install_sh_placeholders.py`,
  teto absoluto de 120 s) — a bateria do SIGN o roda serializado.
- r-w5b-b (Security Engineer; postura, verdade das afirmações, resíduos): GO-WITH-CONDITIONS. P2 (o doc do
  opt-out não avisa que o adopter nasce sem `defaultMode` e pode abrir em auto) — curado em `210baa0b`; P3
  (mensagens do caminho pré-existente) — curado em `210baa0b` (`install.sh:2502` e `:2510`); P3 (razão defasada
  em `templates/settings/settings.user.json:67`) — declarado (canônico e derivado; cerimônia própria); P3 (o
  teste não roda no CI) — declarado, com o teste pelo nome na bateria do SIGN e follow-up de ligá-lo ao
  `smoke-install.yml`.
- Disposição: P0=0, P1=0, P2=1 (curado na rodada seguinte) ⇒ FINDINGS; rodada 2 sobre `210baa0b`.

## Saídas das lanes Claude (verbatim; o SIGN não lê esta seção)

### r-w5b-a

```text
RAIL r1 W5b — r-w5b-a (DevOps), 2026-10-09T14:55:09.763Z — texto final verbatim:

Refutador A (instalador/controles/oráculos) — W5b rail r1, sombra b03934b9 (pai 0a953ece). Tudo medido em instalações descartáveis (work/r-w5b-a, apagado ao fim; HOME descartável; /bin/bash 3.2.57; jq 1.7.1; sombra limpa, porcelain 0).

ACHADOS
- P3 docs/deny-baseline.md:119-121 — a seção de opt-out diz que `CEO_INSTALL_SKIP_DENY_BASELINE=1` «skips the injection entirely» e não menciona que agora também pula `permissions.defaultMode`; a linha SKIP do installer diz a verdade, a doc não. Reprodução: `sed -n 119,121p docs/deny-baseline.md`. Cura: uma frase na doc (path livre; pode ir em follow-up, não bloqueia).
- P3 design (resíduo 3 do construtor, decisão do CEO) — scripts/install.sh:2495-2497: a proteção da Q9 fica acoplada ao opt-out da deny-baseline; quem desliga as regras de deny (propósito documentado) perde em silêncio a proteção contra nascer em auto. A mensagem SKIP avisa; se o Owner quiser desacoplar, é um segundo switch (`CEO_INSTALL_SKIP_DEFAULT_MODE`) — não é defeito do patch.
- P3 fora do patch — .claude/scripts/tests/test_install_sh_placeholders.py: orçamento absoluto de 120 s por `install.sh`; nesta máquina um install solo leva 112 s (pai) / 120 s (patch, 1 amostra cada); com 3 instalações em paralelo os 4 testes estouraram; sozinho, 3/4 e depois 4/4 (o que falhou passa isolado nas DUAS árvores). Classe de flake de runner já registrada (3.ª ocorrência na memória), não atribuível à W5b; a bateria do LAND deve rodar esse arquivo serializado.

VERIFICADO (sem achado)
(1) Filtros sondados nas duas rotas com 9 entradas: chave presente é mantida (acceptEdits, plan, null, "", false), ausente ⇒ manual, `permissions` ausente ⇒ criado; jq e python3 concordam em todas menos `{"permissions":null}` (jq grava, python3 AttributeError ⇒ WARNING e arquivo intacto) — classe pré-existente do merge de deny, só alcançável por template, intocada pela W5b. Caminho de escrita inalterado (`$tmp` irmão + `mv`, após `_SETTINGS_DST_REFUSED`/SKIP/DRY_RUN/PRE_EXISTING, install.sh:2492-2512). Perna H: pré-existente byte-idêntico.
(2) Mensagens: SKIP retorna antes das duas escritas (verdade); dry-run e MERGED dizem «if absent» (verdade); 3 WARNINGs citam a chave.
(3) Controle REAL: teste da sombra com `CEO_INSTALL_UNDER_TEST` no install.sh do pai ⇒ `::error::[F/user] … '<absent>'`, `::error::[G] … '<absent>'`, A–E, F/maintainer e H verdes, rc=1; no patch A–H PASS, rc=0. `mktemp -t` ignora TMPDIR (confirmado) ⇒ as instalações do teste caem em /var/folders; o trap apagou tudo (0 restantes).
(4) Ratchet: `check-installer-write-safety.py` rc=0 nas duas árvores; regeneração sobre o patch byte-idêntica ao baseline commitado; 704 entradas, 205 desguardado / 499 indeterminado antes e depois; as impressões trocadas são exatamente a linha jq (33750b69→d5fcb060) e a linha python3 (0576b738→8213a19e), os dois `mv` mantêm as suas; as 7 linhas de install-accelerators.sh diferem só em número de linha e a regeneração do pai produz o mesmo (drift pré-existente); instrumento com sha idêntico nas duas árvores.
(5) Oráculos: test-manifest-delivery-route.sh (D3 S.1) 131/0; check-install-profiles rc 0; gen-settings-user-template --check rc 0; derive-settings-baselines --check MATCH; check_contamination OK; shellcheck 0.11.0: teste 0 avisos, install.sh mesma contagem antes/depois; 12 arquivos pytest que leem ou executam o install.sh (inclui test_install_user_passes_validate_governance, _no_writes_outside_claude, _dispatcher_present, parity_seed_once, check_installer_write_safety): 327 passed, 2 skipped, 4 timeouts (resolvidos acima). smoke-install.sh na perna user só exige validate-governance + nada fora de .claude/; os scripts de paridade não leem defaultMode; nenhum teste em scripts/tests ou .claude/scripts/tests afirma a AUSÊNCIA da chave na instalação user.
(7) Bateria inteira sob /bin/bash 3.2; nada GNU-only no diff (`cmp -s`, `grep -q`, `printf`, jq `has`/`--arg`).
(8) Resíduos conferidos: teste não ligado a workflow/Makefile (0 hits); `_migrate_settings_baseline` (upgrade.sh:3594, 3884-3901) grava quando ausente sem gate de cerimônia — bate com a medição (b) do construtor.

VERDICT: GO
```

### r-w5b-b

```text
RAIL r1 W5b — r-w5b-b (Sec), 2026-10-09T14:12:07.098Z — texto final verbatim:

Refutação W5b — lane B (postura, verdade das afirmações, resíduos) — r1, 2026-10-09. Sujeito b03934b9 (sombra w5b/wt). Binário: ~/.local/bin/claude → versions/2.1.295, sha256 0116ee2e…f047f70, `--version` = 2.1.295; só bytes, nenhuma chamada de modelo. Dir de trabalho r-w5b-b apagado.

VERIFICADO (sem achado):
- (6) `permission_mode_from_default_fallback` existe (nome @187383022; a `describe` citada pelo construtor @187383255): «True when current_permission_mode is auto because no settings source configured a mode and the gated auto default applied». O gate real está em `v_r` @190129550: com NENHUMA fonte dando modo ⇒ `mode="auto", fromAutoFallback=true` se (sem killswitch `ae()`) ∧ (sem `disableAutoMode`) ∧ auto disponível à conta (`ALn()`) ∧ (sessão interativa ∨ IDE ∨ flag `tengu_moss_anchor`) ∧ sem taint HIPAA. Logo o «can start in Claude Code's gated auto default» de `install.sh:2451-2454` é verdadeiro e corretamente condicionado. O CHANGELOG 2.1.284 não está em disco: a frase fica apoiada só pelo binário e pelo plano (:134), como o construtor declarou.
- `manual` é aceito pelo schema: `defaultMode: Yi(oh, U([...fH,...]))` @187864530, `oh` mapeia manual→default — o settings NÃO é descartado (classe S286).
- Precedência: fontes mescladas low→high `userSettings < projectSettings < localSettings < flagSettings < policySettings` (@187508385). Resíduo (5) é verdadeiro.
- `upgrade.sh`: `_migrate_settings_baseline` (:3594) só tem gate `SETTINGS_MIGRATE` + existência do arquivo, sem gate de cerimônia; `perms MISSING ⇒ SET manual` (:3885-3890); `curs=="manual" ⇒ OK already` (:3902). Afirmação (b) verdadeira. `--print-settings-baselines` (:375) é só `printf`+`exit 0`, sem target.
- (2) Sonda própria dos filtros literais (jq e python3): acceptEdits mantido, `null` mantido, ausente ⇒ manual, `permissions` string ⇒ erro nas duas rotas ⇒ WARNING/untouched (classe pré-existente). MERGED/dry-run/WARNING/SKIP dizem a verdade.
- (8) Resíduo (1) verdadeiro: `git grep` em `.github`/Makefile = 0; `smoke-install.yml:16-18` lista 3 scripts por nome, não este. Resíduo (2) verdadeiro. Resíduo (4) agora provado por um segundo verificador (sonda acima).

POSTURA (sua pergunta): o `manual` do projeto sobre o user settings do dev é o DESEJADO e coerente — (a) mesma postura do framework e do maintainer (`settings.base.json:649`, `.claude/settings.json:819`, PLAN-163 T5.3/ADR-183); (b) o próprio CC trata projectSettings como fonte que só RESTRINGE: @190129550+ «only policy/user/flag settings may grant auto mode (projectSettings and localSettings are repo-controllable)» — gravar `manual` ali é o uso previsto pelo substrato; (c) o operador sai por sessão (`--permission-mode`/shift+tab), rota preservada porque não há `disableAutoMode` (`_posture_comment`). Nada declarado quebra. Nota: `.claude/settings.local.json` NÃO serve para um dev conceder `auto` (repo-controllable, ignorado) — a rota é a CLI/teclado. O opt-out: «nasce sem a chave» (resíduo 3) é verdade; «e, sob o gate acima, em auto» está no comentário do código e na linha SKIP, mas NÃO na doc pública (P2 abaixo).

ACHADOS:
- [P2] docs/deny-baseline.md:121 — «skips the injection entirely» descreve um opt-out que agora também omite `permissions.defaultMode`; o adopter que use `CEO_INSTALL_SKIP_DENY_BASELINE=1` para gerir o deny à mão nasce sem bloco `permissions` e, pelo gate medido, em auto, sem a doc avisar. Reprodução: ler :121 contra `install.sh:2496`. Cura: 1 frase em «How an adopter opts out» (+ nota no INSTALL.md); doc, fora dos 3 paths — land livre no mesmo trem ou condição do SIGN.
- [P3] install.sh:2502 e :2510 — mensagens do caminho pré-existente («would NOT touch deny baseline», «SKIP: settings.json pre-existed… add entries manually») não citam o defaultMode; verdade por omissão. Cura: «deny baseline + defaultMode» nas duas.
- [P3] templates/settings/settings.user.json:67 — a razão da exclusão diz «install.sh constroi a deny-baseline do adopter do zero»; agora também grava o defaultMode. Texto defasado (template derivado: rodar `gen-settings-user-template.py --check` ao tocar).
- [P3] Resíduo (1): a única prova mecânica de que a instalação user grava `manual` não roda em CI, e W1a/W1b do PLAN-183 re-derivam sobre este `install.sh`. Cura: nomear `bash scripts/tests/test-install-deny-baseline.sh` na bateria do LAND da W5b e abrir FU de wire no smoke-install.yml.

VERDICT: GO-WITH-CONDITIONS
```
