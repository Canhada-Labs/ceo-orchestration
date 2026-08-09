# PLAN-166 W1 — log da cerimônia (2026-08-06)

Sentinel: `architect/round-1/approved.md`, assinado 2026-08-06 09:19 -03,
chave EDDSA `AE9B236FDAF0462874060C6BCFCFACF00335DC74` (Owner), `gpg
--verify` = Good signature. Anchor-SHA `516e64e671f6e33b7fcf0f0a28a70caf954bd996`.
Round codex pré-assinatura sobre o sentinel: 2 achados (P1 = .asc ausente,
resolvido pela própria assinatura; P2 = tarball "final" stale, regenerado).

## OWNER-DECISIONs resolvidas

1. **Deferred-apply do marcador: Route B** (AskUserQuestion, registrada no
   sentinel). Follow-up livre obrigatório antes do 1º bump do ciclo 1.4.0.
2. **timeout 25 do smoke-install**: ratificado pela assinatura (desvio
   declarado do "~15" do plano; valor medido).

## Simulação pré-assinatura (clone limpo em `516e64e`)

verify-counts EXIT=0 · asserts 52/52 · YAML 3/3 · shellcheck OK · sweep
clean · touched−scope=∅ · F3 e2e 45/45 · bateria 5010 passed/0 failed.

## Step 1 — applies não-kernel (Owner, `OWNER-W1-LAND-step1.sh`)

- 1ª execução: G4 FAIL correto (intent-to-add `git add -N` do review do
  codex aparecia como ` A`); curado com `git reset`, guard re-passou.
- 2ª execução: G1-G4 OK → 14 applies + sweep 188→189 + 29→31 → census
  "sweep clean". Bits executáveis verificados; marcador == VERSION.

## Step 2 — release.yml via rota kernel-override

**Evidência da rota sancionada (bundle compensatório):**

1. systemMessage do hook, testemunhado na scrollback do Owner:
   `ARBITRATION-KERNEL: override granted — reason='PLAN-166-W1-RELEASE-YML-AWAIT-GATE'`
2. Conclusão do one-shot armado (prefixo env, par morto com o processo):
   "Feito. `.github/workflows/release.yml` agora é byte-idêntico ao
   staged (`diff` limpo)".
3. **Controles negativos (2×):** o MESMO comando sem o par, headless
   (probe, sessão `6d29323e`) → BLOCK com a mensagem literal
   ARBITRATION-KERNEL-BLOCKED; Edit in-session sem o par → BLOCK.
   Ambos com evento `veto_triggered reason_code=kernel_edit_blocked` no
   ledger (13:15:52Z e 13:16:12Z).
4. Bytes: `release.yml` vivo == cópia staged pinada no manifesto
   (verificado pelo CEO por diff).
5. Cadeia HMAC: `check-audit-hmac-null.py` = OK.

**⚠️ Achado P1 (follow-up pós-GA, exige cerimônia kernel própria):** os
emits do CAMINHO DE GRANT do `check_arbitration_kernel.py`
(`kernel_extension_landed` e `veto_triggered kernel_override_used`) são
SILENCIOSOS — engolidos por `except Exception: pass` — enquanto os do
caminho de block funcionam (provado 2× hoje). O artefato-prova primário
das notas (§4) não nasce; este bundle compensatório o substitui NESTA
cerimônia por decisão registrada. Suspeito: validação de schema dos
kwargs (`ceremony_sha` recebe PATH, não sha 64-hex).
Corrigir e adicionar teste positivo do emit de grant.

**Nota de higiene:** o par nunca entrou em settings/perfil (greps 0 no
§0.2; o hit de 5 linhas no ~/.zshrc é o bloco de AUTO-CURA S200, que
faz `unset` — o oposto de resíduo). Par usado só em prefixo de processo.

## Rail codex da cerimônia (rounds até APPROVE)

- Round 1 (diff completo pós-apply): 3 achados — P1 rerun do install
  apaga delivery-records; P2 FMS_MODE=copy em target link-mode; P2
  fingerprint cego a symlink adopter-added. TODOS corrigidos na árvore +
  espelhados no staged + controles plantados verdes.
- Round 2: 3 achados — P1 escrita ATRAVÉS de `TARGET/SPEC` symlinkado
  (find -delete fora do target); P2 --skip de descendente ignorado no
  refresh wholesale; P2 cp para marker-como-diretório. TODOS corrigidos
  (guard de ancestral com o helper F11a existente; skip de descendente
  preserva a árvore inteira; guard de destino não-regular).
- Round 3: 2 P2 — backup falho suprimido antes de rm -f (agora aborta,
  preserve+warning); rota de recuperação impossível para SPEC
  não-registrado >v1.2 (agora: takeover por CURRENT-SOURCE match,
  byte-idêntico ao checkout = framework-owned). Controles plantados
  verdes (fingerprint igual/divergente).
- e2e S1-S8 re-rodado após CADA round: 45/45 nas três vezes.
- Round 4 / Round 5: 3 achados cada (r5: continuidade re-baselinizando
  fork editado; snapshot não-verificado antes da instrução de recovery;
  `--skip` invisível a arquivo só-no-target). Aplicados; e2e 45/45.

### Rounds 6-9 (sessão S296, retomada pós-reboot)

- **Round 6 — 1 P2 (ownership perdido em `--mode link`).** O sanitizador
  `_baseline_relpath_unsafe` rejeitava symlink em QUALQUER componente,
  mas o leaf de um registro `LINK  SPEC/v1  <target>` é symlink POR
  CONSTRUÇÃO — todo registro LINK morria na sanitização, e
  `_baseline_has_spec_record` + os dois lookups readlink-vs-registro
  nunca casavam. Todo upgrade em modo link perdia silenciosamente a
  propriedade de `SPEC/v1` e do marcador, caindo no `VERSION` raiz
  obsoleto — exatamente o contrato do ADR-155-AMEND-1.
  **Provado antes de corrigir** (alvo em modo link real: os 2 registros
  LINK sumiam, só o de hash sobrevivia). **Varredura da família achou a
  autoridade:** `doctor.sh` JÁ tinha a cura (`_relpath_unsafe "$rel" link`
  vs `"$rel" file`); o `upgrade.sh` era o irmão atrasado, então a
  semântica foi DERIVADA, não inventada. Fix mais conservador que o do
  doctor.sh: leaf-symlink tolerado só para registros LINK; registros de
  hash mantêm rejeição estrita (`_hash_file` seguiria o link).
  Controles 5/5: 2 positivos (LINK leaf), 2 negativos que seguem
  fechados (HASH com leaf symlinkado; LINK sob PARENT symlinkado), 1 de
  regressão (HASH regular intacto).

- **Round 7 — 3 P2.** (a) `check-framework-updates.sh` respondia
  PROCEDÊNCIA mas nunca INTEGRIDADE: marcador entregue e depois editado
  `1.3.0`→`9.9.9` seguia satisfazendo o registro, e o checker reportava
  up-to-date contra upstream `1.3.0` — SUPRIMINDO um update real. Agora
  verifica os bytes vivos contra o registro (digest portátil com
  fallback; LINK por readlink) e cai para VERSION no que não verificar —
  mesma direção conservadora que o r20 já toma. Live-fire 4/4.
  (b) O skip de `--ceremony user` era o ÚNICO dos 5 callsites irmãos sem
  continuidade de propriedade: reinstalar como `user` preservava a
  árvore e apagava o registro → de volta em maintainer aquela árvore
  v1.3 não casa com fonte nem com fingerprint legado e vira
  ADOPTER-FORK PERMANENTE. Corrigido no skip de SPEC e no análogo de
  `PROTOCOL.md`, com o 3º irmão `_baseline_has_protocol_record`
  (`_baseline_lookup` não serve — resolve só registros de hash).
  (c) `awk '{print $3}'` quebrava o alvo do LINK em espaços: um checkout
  com espaço no caminho fazia entrega INALTERADA ler como redirecionada.
  Delimitador duplo-espaço fixo nos 2 sites.
  *(b) e (c) só ficaram ALCANÇÁVEIS pelo fix do round 6 — antes nenhum
  registro LINK sobrevivia e os lookups morriam vazios antes do defeito.*

- **Round 8 — 1 P1 + 2 P2.** (a) **P1, regressão do próprio fix do round
  5**: `FMS_HASH_ROOT` é interruptor GLOBAL, mas o install RENDERIZA
  templates (`team.md`, skills, `{{X}}` sob `--project`) — um rerun
  passou a gravar o hash da fonte NÃO-renderizada para a árvore inteira,
  que `doctor.sh` lê como drift generalizado e upgrades futuros leem
  como customizado, PARANDO de atualizar esses arquivos. Cura:
  `FMS_HASH_ROOT_PATHS` (override por caminho); o install passa só os
  caminhos cuja continuidade disparou, o upgrade não passa lista e fica
  intocado. Controles 5/5, incluindo `SPEC/v1x/...` NÃO casando o
  prefixo `SPEC/v1`. **Esta é a classe "fixes corretos COMPÕEM errado"
  da S294 — o round 5 estava certo no problema e largo demais no lever.**
  (b) P2 `set -euo pipefail`: `grep | head` sem match retorna 1 e ABORTA
  o upgrade inteiro (no meio, após outras superfícies já atualizadas) em
  vez de cair no ramo warning-and-preserve — um adotante copy-mode que
  trocou `SPEC/v1` por symlink não tem registro LINK por construção.
  PRÉ-EXISTENTE: provado que aborta igual com o `awk` antigo. `|| true`
  nos 2 sites (varredura: são os únicos dessa forma nos 3 scripts).
  (c) P2 `OWNER-W1-LAND-step1.sh` não copiava `_parity_classify.py`,
  embora esteja no escopo assinado e no manifesto — o script documentado
  não reproduzia a árvore validada. Varri a classe: das 3 divergências
  staged-vs-script só essa era real (o ADR é falso-positivo da extração;
  `release.yml` é omitido de propósito, vai pela rota kernel-override).

- **Achado de PROCESSO (não do produto):** o `mirror-fixes.sh` cobria 2
  de 4 canônicos alterados — o checker e o `_framework_manifest_set.sh`
  teriam divergido do staged SEM NENHUM GATE ACUSAR (o `shasum -c` do
  §0.3 valida o staged contra si mesmo, não contra a árvore viva).
  Substituído por tabela path→patch: acrescentar um arquivo é uma linha.

- **Falso-vermelho no runbook §7:** o snippet usa `\s` em `grep -E`/`sed`,
  que NÃO existe no BSD (macOS) — devolvia "tudo fora de escopo". Falha
  na direção segura (STOP), mas travaria a cerimônia. Extração POSIX
  (`[[:space:]]`) usada; corrigir o runbook.

### Follow-ups nomeados (superfície livre, NÃO esta cerimônia)

1. **Cobertura e2e ausente:** o S3 nasce como `--ceremony user`; a
   TRANSIÇÃO maintainer→user (por onde o round 7 (b) passou) não é
   exercitada por nenhum cenário. Adicionar S9.
   > **FECHADO (PLAN-169 W0.7, 2026-08-08):** o ex-"S9" foi absorvido
   > pelo PLAN-167 como célula da tabela — `OWN-0070`
   > (`scripts/tests/ownership_table.tsv:60`, "maintainer install
   > re-run as user: record must NOT be erased", origem r7-F2) — e roda
   > no e2e nightly (GREEN no run Darwin de S297, 62/3). Verificado por
   > grep na tabela-verdade, não por recitação.
2. **Emits do caminho de GRANT do kernel** seguem silenciosos (P1 já
   registrado no Step 2 acima).
3. Matcher de `verify-counts.sh` para as duas frases de contagem de ADR
   em `docs/GUIA-COMPLETO.md` (a NOTE do próprio script pede).
4. Deferred-apply Route B: `_release_bump_sites.py` + `verify-counts.sh`
   ganham o site do marcador ANTES do 1º bump do ciclo 1.4.0.

## §6(b) bateria — satisfeita por composição (registrado, não por silêncio)

O re-run completo na árvore landada foi impedido por kill-waves de
processo (abaixo). Evidência equivalente: (a) bateria COMPLETA verde na
SIMULAÇÃO em clone do conteúdo aplicado (5.010 passed, 0 failed); (b) o
único arquivo python alterado desde `f492545` — onde o verificador dos
residuais rodou o diretório inteiro verde — é
`test_release_workflow_asserts.py`, re-rodado VIVO pós-apply: 52/52;
(c) os fixes do rail tocam só shell (`install.sh`/`upgrade.sh`),
exercitado pelo e2e 45/45, não pela bateria python.

## Incidente operacional: kill-waves de background

Três ondas de kills de tarefas bash/codex em background durante a
cerimônia (bateria 2×, mirror 2×, codex 1×) — padrão consistente com
sleep da máquina. Nenhuma perda: o script de espelhamento é idempotente
e completou antes de cada kill (verificado por cmp + shasum -c toda
vez). Mitigação: `caffeinate -dims` nos relançamentos.

## Observação de substrate (registrar em memória)

`claude -p` headless neste repo demora MINUTOS para responder (boot de
governança completo) — dois operadores concluíram "travou". O guard de
kernel FUNCIONA em `-p` (probe provou); a lentidão é UX, não gate morto.
