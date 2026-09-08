# Verificação adversarial — Parte 3 do candidato v1.4.0-rc.1 (HEAD 4a1b448)

Sujeito: `scripts/uninstall.sh` (U1–U4) + `templates/.github/workflows/validate.yml.template` (T1, T2).
Método: leitura linha-a-linha no HEAD + `git show v1.3.0` + reprodução em clone `--local` descartável
(`repass-triage/clone3-1`, targets sintéticos sob `repass-triage/t1|t2|wsp2`). Zero codex, zero escrita fora deste arquivo.

## Tabela de canonicidade (STDOUT do oráculo; exit sempre 0)

| path | is-canonical |
|---|---|
| scripts/uninstall.sh | 0 (livre) |
| scripts/doctor.sh | 0 (livre) |
| templates/.github/workflows/validate.yml.template | 0 (livre) |
| .github/workflows/validate.yml | 1 (canônico) |
| scripts/_framework_manifest_set.sh | 1 (canônico) |
| PROTOCOL.md | 1 (controle ⇒ 1 OK) |
| README.md | 0 (controle ⇒ 0 OK) |
| scripts/tests/test-installer-write-safety-e2e.sh | 0 |
| .claude/scripts/tests/test_validate_template_frozen_subset.py | 0 |

Os DOIS arquivos-sujeito são LIVRES — cura pode landar esta noite sem assinatura do Owner.

## §0 — Resumo

| id | classificação | regressão vs v1.3.0? | raio de dano | arquivo livre? | cura cabe hoje? |
|---|---|---|---|---|---|
| U1 | PRÉ-EXISTENTE (falha-FECHADO: registro LINK é RECUSADO) | não (awk idêntico; link-mode já existia) | só `--link`; copy-mode = ZERO; sem traversal | sim | **não** (reescrita do parser) |
| U2 | PRÉ-EXISTENTE + fail-open no REPORT (exit 0 em incompleto; exit 3/5 mortos) | parcial (refusal-path é novo) | automação confia em `$?` e registra sucesso falso | sim | **sim** |
| U3 | POR-DESENHO + FORA-DO-MODELO (escrita same-UID em `.claude/`) | não | precisa injetar manifesto = já é game-over (§T-05) | sim | **não** (sidecar autenticado = v2/ADR) |
| U4 | PRÉ-EXISTENTE + mesma classe do ADR-196 (sítio não convertido) | não (path previsível idêntico em v1.3.0) | write-through same-UID via symlink pré-plantado | sim | sim (marginal, ~15 l) |
| T1 | POR-DESENHO (skip deliberado em `4f750f0`) — questionável | não (era `import yaml` duro; skip é novo, deliberado) | CI do adopter aceita catálogo YAML malformado em verde | sim | **sim** |
| T2 | melhoria-INCOMPLETA (mais fraca que o workflow VIVO) | não (v1.3.0 era `bash <(curl)` UNPINNED — pior) | CI do adopter baixa+EXECUTA binário não verificado | sim | **sim** (copiar 2 linhas do vivo) |

Recomendação: curar **T2 + U2** esta noite (as duas mais limpas, em arquivo livre, com teste). **T1** é a terceira
opção (decisão do CEO sobre o skip deliberado). **U1, U3, U4** viram CONDIÇÕES do envelope. Detalhe abaixo.

## §1 — U1: registro LINK mal-parseado (`uninstall.sh:364,370,373,376`)

Código no HEAD (o parser trata TODO registro como `<sha>  <relpath>`):
```
recorded_sha="${line%% *}"                       # 370
rel="${line#* }"; rel="${rel#* }"                # 371-372
rel="$(printf '%s' "$line" | awk '{ $1=""; sub(/^ +/, ""); print }')"   # 373
if _rel_unsafe "$rel"; then ... continue; fi     # 376
```
Escritor (`_framework_manifest_set.sh:1278`, gramática §309): `LINK␣␣<relpath>␣␣<target>`.

Alcançável? **Sim, mas falha FECHADO.** Repro (`t1`, manifesto com uma linha LINK real):
`recorded_sha=[LINK]`, `rel=[docs/linked.md /outside/src/linked.md]` — relpath + target juntados por espaço.
`_rel_unsafe` rejeita pelo espaço ⇒ `REFUSED (unsafe manifest path)`, o symlink `docs/linked.md` fica INTOCADO,
exit 0. Nada fora do target é seguido. Logo NÃO é traversal — é INCOMPLETUDE: um adopter `--link` não consegue
desinstalar as entregas link (símbolos permanecem, manifesto KEPT). Somado a U2, o report diz "incomplete" mas
sai 0.

Classe: **PRÉ-EXISTENTE** (o awk é idêntico em `v1.3.0:uninstall.sh:209`; link-mode já existia — `install.sh`
tem 5 sítios `--mode` em v1.3.0). Raio: copy-mode (o caso real dos outros repos do maintainer) = **zero**;
`--link` = incompletude não-destrutiva. Cura mínima = parsear LINK e hash separadamente pela gramática comum e
só desligar o symlink quando o alvo corrente bate o alvo registrado — é reescrita do laço (>15 l) + teste de
integração v1.3-link→rc.1→uninstall. **Não é land limpo desta noite.** → CONDIÇÃO.

## §2 — U2: recusa de segurança sai 0 (`uninstall.sh:436,454`)

Código no HEAD:
```
if [ "$unsafe_count" -gt 0 ] || { [ "$mismatch_count" -gt 0 ] && [ "$FORCE" -eq 0 ]; }; then
  ... _log "==> Uninstall summary (incomplete):" ...
  exit 0                                          # 454  <-- fail-open
fi
```
`grep -n 'exit'` em HEAD: só 0,1,2,4 são emitidos. **Exit 3 (HMAC) e exit 5 (--force ausente) do cabeçalho estão
MORTOS** — cabeçalho `uninstall.sh:21-27` documenta 5 códigos, o corpo usa 4 e nunca os dois de falha
não-sucesso. Repro (`t1`): registro recusado ⇒ `EXIT_CODE=0`.

Alcançável? **Sim, provado.** Automação que faz `uninstall.sh … && echo ok` registra sucesso após um caminho de
travessia recusado, um ancestral symlink, ou qualquer registro LINK de §1. É fail-open na FRONTEIRA DO PROCESSO
e contradiz o próprio cabeçalho.

Classe: **PRÉ-EXISTENTE no núcleo** (v1.3.0:252-261 já sai 0 no incompleto-por-mismatch; exit 5 já morto lá) +
**regressão parcial** (o ramo `unsafe_count` é novo em HEAD e nasceu saindo 0). Raio: qualquer chamador que
confia em `$?` (CI, `doctor`, orquestrador). Cura mínima (≤ 6 l, direção fail-closed) em arquivo LIVRE — patch em §7.
Controle positivo: registro recusado deve dar `$? != 0` (hoje dá 0). Bateria: `test-installer-write-safety-e2e.sh`
seção U + `smoke-install.sh` §9.8 (já exercitam uninstall; adicionar asserção de status). **Cabe hoje.**

## §3 — U3: manifesto sem integridade tratado como prova de posse (`uninstall.sh:89,369,403`)

Código no HEAD (o próprio cabeçalho admite): `# The manifest … is NOT integrity-checked before the walk`
(89-92). O laço remove qualquer arquivo cujo sha CORRENTE bata o registrado (403-408), sem `--force`.

Alcançável? **Sim, provado** (`t1`): `adopter-notes.md`, arquivo do adopter, com seu sha corrente injetado no
manifesto ⇒ `REMOVED` sem `--force`. MAS: quem escreve `.claude/.install-manifest.sha256` tem escrita same-UID no
target. `docs/threat-model.md` §T-05 residual: "deliberate removal (rm -rf .claude/) is not defended"; seção
same-UID (linhas 1745+): "A local process running as the same UID … can rewrite selected lines". Um atacante que
injeta um registro já pode `rm` o arquivo diretamente — a injeção NÃO concede nada novo.

Classe: **POR-DESENHO** (documentado 89-92) + **FORA-DO-MODELO-DE-AMEAÇA** (escrita same-UID em `.claude/`). Raio
real adicional sobre o baseline same-UID: **nenhum**. Cura proposta pelo revisor (sidecar autenticado verificado
antes de qualquer remoção) é mudança de `install.sh`+`upgrade.sh`+`uninstall.sh` com ADR — **v2, não rc.1**. →
CONDIÇÃO declarada / out-of-scope explícito no envelope.

## §4 — U4: backup previsível sem criação exclusiva (`uninstall.sh:318,340,350`)

Código no HEAD:
```
timestamp="$(date -u +%Y%m%d-%H%M%SZ)"                          # 318
backup="$TARGET/.claude.backup-uninstall-$timestamp.tar.gz"     # 319
( cd "$TARGET" && tar czf "$backup" -T "$backup_list" ... )     # 340
printf '%s  %s\n' "$backup_hmac" "$backup" > "$backup.hmac"     # 350
```
Sem `O_EXCL`, sem recusa de destino linkado, resolução em SEGUNDOS (previsível).

Alcançável? **Sim, provado** (`t2`): symlink pré-plantado em `.claude.backup-uninstall-<ts>.tar.gz` apontando para
fora ⇒ `tar czf` ESCREVEU ATRAVÉS do link — **578 bytes** aterrissaram em `repass-triage/exfil/` (fora do target),
e o run reportou sucesso normal (exit 0). O mesmo vale para `$backup.hmac`.

Classe: **PRÉ-EXISTENTE** (v1.3.0:176-188 tem path previsível idêntico + `tar czf` sem O_EXCL) + **mesma classe do
ADR-196/T-008** (sítio de escrita não convertido ao predicado `_wbm_dst_refuses`; ADR-196 já lista `doctor.sh` e
outros como não convertidos). Para plantar o symlink é preciso escrita same-UID no diretório-pai. Raio: clobber/
write-through de um inode fora do target, para atacante que já é same-UID. Cura factível hoje (~15 l: recusar se
`$backup`/`$backup.hmac` existe ou é symlink; criar via `mktemp` em `$TARGET/.claude` e `mv`). Marginal para land
livre — recomendo alinhar ao predicado do ADR-196 num follow-up. → CONDIÇÃO (ou cura noturna cuidadosa com teste
negativo próprio).

## §5 — T1: validação YAML pula sem PyYAML e deixa CI verde (`template:119,128`)

Código no HEAD (template):
```
if python3 -c 'import yaml' 2>/dev/null; then
  python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1])); ..." "$y"
else
  echo "NOTE: PyYAML absent — skipped YAML syntax check for $y"   # 127  <-- fail-open
fi
```
Alcançável? **Sim, provado** (`wsp2` + python3 sem yaml via `PYTHONNOUSERSITE=1`): catálogo QUEBRADO ⇒ o laço
imprime `NOTE: PyYAML absent — skipped` e sai **0**. Controle positivo (python3 COM yaml, mesmo arquivo) ⇒
`ParserError`, exit **1**. Runner slim ou alterado aceita catálogo de governança malformado em verde.

O workflow VIVO NÃO tem esse buraco: instala PyYAML incondicional (`validate.yml:462-465`) e valida duro
(`295-296`, sem skip). O template é materialmente mais fraco.

Classe: **POR-DESENHO** (skip introduzido deliberadamente em `4f750f0` com comentário "so a slim runner never
false-reds") — mas desenho QUESTIONÁVEL: um guard de validação que falha-aberto em infra ausente derrota o
próprio propósito (o "fail-open on infrastructure" do CLAUDE.md §4 é para HOOKS de sessão, não para um gate de CI
sobre o próprio input). Raio: CI do adopter valida catálogos em falso-verde. Cura fail-closed em arquivo LIVRE
(instalar validador PINADO e validar duro — preserva stdlib-only no RUNTIME, fecha o CI) em §7. Controle
positivo: catálogo quebrado deve ficar VERMELHO. **Cabe hoje** — decisão do CEO se o skip deliberado é aceitável.

## §6 — T2: actionlint baixado sem checksum (`template:187,191,193`)

Código no HEAD (template):
```
VERSION="1.7.7"
ASSET="actionlint_${VERSION}_linux_amd64.tar.gz"
curl -sSLO "https://github.com/rhysd/actionlint/releases/download/v${VERSION}/${ASSET}"   # 191
tar -xzf "$ASSET" actionlint; chmod +x actionlint                                          # 192-193
```
Nenhum SHA-256, nenhuma assinatura antes de EXECUTAR. O workflow VIVO (`validate.yml:892-899`) fixa
`EXPECTED_SHA256="023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757"` (mesmo asset linux_amd64) e
roda `sha256sum -c -` ANTES do `tar`. O template é provadamente mais fraco que sua própria fonte.

Alcançável? **Sim, por leitura.** O adopter baixa e executa um binário de release não verificado; troca do asset
(comprometimento de conta, CDN, MITM abaixo do TLS) ⇒ execução de código do atacante no CI do adopter.

Classe: **melhoria-INCOMPLETA** — v1.3.0 usava `bash <(curl … download-actionlint.bash)` (script remoto UNPINNED,
PIOR); HEAD melhorou para URL pinada mas parou antes do checksum. Não é regressão vs v1.3.0; é hardening pela
metade. Raio: supply-chain no CI de todo adopter. Cura mínima = copiar 2 linhas do workflow vivo (§7). Preserva
`VERSION="1.7.7"` e o nome de step "actionlint" ⇒ `test_validate_template_frozen_subset.py` continua verde.
Controle positivo: asset corrompido ⇒ `sha256sum -c` falha e o job fica VERMELHO antes de extrair. **Cabe hoje — a
mais limpa das seis.**

## §7 — Recomendação ao CEO

**Curar esta noite (arquivo livre, cura pequena, teste presente):**

T2 — `templates/.github/workflows/validate.yml.template`, dentro do step "actionlint":
```diff
           VERSION="1.7.7"
+          EXPECTED_SHA256="023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757"
           ASSET="actionlint_${VERSION}_linux_amd64.tar.gz"
-          curl -sSLO "https://github.com/rhysd/actionlint/releases/download/v${VERSION}/${ASSET}"
+          curl -fsSLO "https://github.com/rhysd/actionlint/releases/download/v${VERSION}/${ASSET}"
+          echo "${EXPECTED_SHA256}  ${ASSET}" | sha256sum -c -
           tar -xzf "$ASSET" actionlint
```
Controle vermelho-sem-cura: baixar asset adulterado ⇒ job passa hoje, falha com o patch. Bateria:
`test_validate_template_frozen_subset.py` (VERSION/step preservados) + `smoke-install.sh` executa o step em Linux.

U2 — `scripts/uninstall.sh`, ramo incompleto (linha 454), fail-closed:
```diff
-  _log "    Preserved files were NOT touched."
-  exit 0
+  _log "    Preserved files were NOT touched."
+  if [ "$unsafe_count" -gt 0 ]; then exit 5; fi          # refusal = never a success
+  exit 5                                                 # mismatch-without-force (documented)
+fi
```
(Alinhar o cabeçalho: exit 5 = "uninstall incompleto — recusa e/ou mismatch sem --force"; remover os mortos 3.)
Controle vermelho-sem-cura: registro recusado deve dar `$? != 0` (hoje 0). Bateria: `test-installer-write-safety-e2e.sh`
seção U + `smoke-install.sh` §9.8 (adicionar asserção de status junto ao texto).

**Terceira opção (decisão do CEO sobre o skip deliberado) — T1** dentro do step "Validate settings.json and YAML":
```diff
+          # CI é dev-time: instalar o validador PINADO fecha o fail-open sem
+          # violar o stdlib-only do RUNTIME (espelha validate.yml:462-465).
+          python3 -m pip install --quiet --no-cache-dir "PyYAML>=6.0" >/dev/null
           for y in .claude/pitfalls-catalog.yaml .claude/task-chains.yaml; do
             [ -f "$y" ] || continue
-            if python3 -c 'import yaml' 2>/dev/null; then
-              python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1])); ..." "$y"
-            else
-              echo "NOTE: PyYAML absent — skipped YAML syntax check for $y"
-            fi
+            python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1])); print('ok '+sys.argv[1])" "$y"
           done
```
Controle vermelho-sem-cura: catálogo quebrado passa hoje, falha com o patch.

**Condições do envelope (não bloquear rc.1; documentar como residual conhecido):**
- U1 — registros LINK não desinstaláveis por copy-vs-link no parser; falha FECHADO; abre `PLAN-169-FOLLOWUP-link-uninstall`.
- U3 — manifesto sem autenticação; POR-DESENHO + same-UID out-of-scope (§T-05); sidecar autenticado = item de v2.
- U4 — backup previsível write-through same-UID; mesma classe do ADR-196; converter ao predicado `_wbm_dst_refuses`
  em `PLAN-185-FOLLOWUP-uninstall-backup-confine` (FU-7 já cobre `doctor.sh`).

Se o CEO quiser um único land, **T2 sozinho** é o de maior valor/risco-mínimo (copia código já verificado do
próprio repo). U2 é o segundo. T1 depende de aceitar o `pip install` no template.

## CLAIM
Rodei: oráculo de canonicidade (7+2 paths), leitura integral de `uninstall.sh` (486 l) e do template (242 l),
`git show v1.3.0` dos dois, e 4 reproduções em clone `--local`: U1 (LINK ⇒ REFUSED, fecha), U3 (arquivo do
adopter removido por sha injetado), U4 (578 bytes write-through de symlink pré-plantado, exit 0), T1 (catálogo
quebrado ⇒ skip verde sem yaml; vermelho com yaml — controle positivo). U2 e T2 verifiquei por leitura + `grep`
de exits + diff contra o workflow vivo (SHA-256 do actionlint presente no vivo, ausente no template). NÃO reproduzi
end-to-end um install `--link` v1.3.0→rc.1→uninstall (U1 confirmado no nível do parser, não no ciclo completo) nem
executei `smoke-install.sh` (precisa Linux/`CEO_SMOKE_EXECUTE_CI`). Tokens: ~115k.
