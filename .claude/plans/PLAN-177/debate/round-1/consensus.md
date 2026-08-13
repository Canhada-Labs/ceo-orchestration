---
plan: PLAN-177
round: 1
round_verdict: PROCEED
vetoes: 0
critiques: 3 (ADJUST, ADJUST, ADJUST)
consensus_adjustments: 9
created_at: 2026-08-13
---

# Consenso — round 1, PLAN-177

## Consensus findings (2+ críticos)

- **CF-1 [P0] (A,B) — decisão malformada NUNCA sai pelo ramo de INFRA.**
  Empírico (B): `verdict:` vazio ⇒ `{}` no validador / `[]` no guard;
  `.strip()` do plano ⇒ AttributeError ⇒ exit 1 = EXIT_INFRA_ERROR — o
  único código que `CEO_PAIR_RAIL_VERDICT_OPTIONAL` roteia. Cura:
  type-check `isinstance(..., str)` ANTES do compare (precedente
  tool_versions :447-461); não-str/vazio/ausente/lista ⇒
  VERDICT_INVALID(3) / E_DECISION. Casos obrigatórios nos DOIS.
- **CF-2 [P0] (A,C) — a mecânica da allowlist estava descrita ERRADA no
  plano.** A tupla `^\.gitignore$` está em ACCEPTED (não KNOWN_OPEN);
  entry órfã = WARNING, não MANDATORY-FIRE. Estado C (cura landada +
  entry presente) = CI-verde e cego = instância 17. Rota escolhida (b):
  remoção atômica no commit do pack + justificativa trocada para AC-3 +
  nota explícita de que o CI NÃO protege o estado C (verificação humana:
  `git show --stat` prova as duas metades) + controle positivo da
  superfície NOVA = executar o estado D (allowlist removida + entrega
  revertida) em clone scratch e anexar o transcript FATAL (C-M2i).
- **CF-3 [P0] (A,B,C) — assimetria load-bearing.** Sob
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` (release.yml:689
  continue-on-error), o gate do validador é ENGOLIDO; quem barra em
  todos os modos é `_release_tag_guard.py delta` (step delta+ancestry,
  sem continue-on-error, release.yml:786-859). Cura: frase na AC-1 +
  comentário de 3 linhas nos DOIS arquivos (qual é enforcement, qual é
  defesa em profundidade) + assert estrutural de que o step delta segue
  invocando `_release_tag_guard.py delta` (estender a classe W1B* de
  test_release_workflow_asserts) + assert pré-tag no W2 via
  `gh variable list` (OPTIONAL e CEO_SOTA_DISABLE ausentes/0).
- **CF-4 [P0] (A,B,C) — OQ-1 respondido 3/3:** `E_DECISION = 13` NOVO no
  guard (NO-GO é envelope VÁLIDO que diz não; E_VERDICT é forma);
  reusar `EXIT_VERDICT_INVALID = 3` no validador (código novo exigiria
  rotear release.yml = KERNEL) — a assimetria 3×13 é DECISÃO, escrita no
  plano. E o assert de distinção
  (test_release_workflow_asserts.py:1000-1013) JÁ APODRECEU (omite
  E_PARENT_NOT_ANCESTOR=12): derivar a lista de `vars(mod)` com
  contagem mínima — fecha a classe, não a instância.
- **CF-5 [P1] (A,C) — NÃO adicionar `"npm"` cru a SCAN_ROOTS.** O
  bundle espelhado (pytest.ini:68-72) e o staging rsync
  (npm-publish:288-326) fariam o scanner varrer cópias. SCAN_ROOTS já
  aceita arquivos: usar `npm/INTEGRITY.md` e `npm/README.md`
  explícitos. Controle positivo planta o semver NO PRÓPRIO
  INTEGRITY.md (C-U3).
- **CF-6 [P1] (A,B,C) — gate "Where enforced" redesenhado.** Coluna
  `Status` de conjunto FECHADO (`enforced|deferred|operator`);
  parser restrito (workflow em backticks + `step "nome"`); igualdade
  exata com `- name:`; **contagem mínima ≥2** (sem ela o gate é
  vacuoso por construção — classe check_tier_a); fail-closed em Status
  desconhecido; controles: step renomeado ⇒ red E tabela sem matches ⇒
  red na contagem.
- **CF-7 [P0] (A,B + C-M6) — ordem do W2 corrigida.** O guard
  (:369-383 allowlist restrita; :529-542 E_VACUOUS) exige: curas+bump
  landam PRIMEIRO → re-pass revisa ESSE SHA → envelope é a ÚLTIMA
  escrita antes da tag (único arquivo do delta; nenhum path do
  inputs-hash-manifest tocado depois) → push → CI verde POR-JOB
  (success, nunca cancelled/skipped — smoke-install cancela runs por
  concorrência) pinado ao SHA → preflight → tag no MESMO SHA.
- **CF-8 [P1] (B,C + A-U3) — o sweep de honestidade é por ARQUIVO
  INTEIRO + vocabulário.** +3 promessas falsas no INTEGRITY.md fora das
  faixas do plano (rotation-log §NPM inexistente; `.well-known/gpg.asc`
  inexistente; step SOURCE_DATE_EPOCH que validate.yml não tem);
  receita de consumidor REMOVIDA/substituída (não ressalvada);
  `install-npm.sh` é o bloco :178-190 (DUAS claims). Varredura por
  vocabulário em README/npm-README/SECURITY/docs — couber ⇒ agora;
  não ⇒ item NOMEADO do v1.4.0.
- **CF-9 [P1] (A-MF3, B-M4/R-S5) — entrega de .gitignore completa.**
  O gerador é dono dos DOIS blocos marker-guarded do root .gitignore
  (mcp-secrets + posture) e o upgrade entrega ambos (fecha adopter
  pré-v1.2.0). Modo `--ceremony user`: entregar arquivo NOVO
  `.claude/.gitignore` (`/state/` + `/settings.local.json`),
  create-if-missing/nunca sobrescrever, nos DOIS caminhos e TODAS as
  cerimônias — fecha o dano nomeado do verdict-ga-1 sem violar o
  assert "user não escreve fora de .claude/" (smoke:220-232).
  Idempotência por-linha do root mantida (byte-parity) e DOCUMENTADA
  como intencional (re-append pós-remoção deliberada é postura, não
  bug — release notes).

## Single-agent insights KEPT

- (B-M2, P0, reproduzido) chave `verdict:` DUPLICADA é last-wins nos
  dois parsers — rejeitar count(`^verdict:`) != 1; caso NO-GO→GO.
- (B-U2) threat-model: o que prende o envelope é a ASSINATURA do Owner
  sobre a árvore taggeada (inputs_hash cobre gate-scripts, não o
  verdito; gpg_signature é checado por presença) — fixture temporário
  auto-consistente NUNCA é bypass. Frase no plano.
- (B-U4) tupla ACEITA idêntica nos dois arquivos + teste que compara.
- (B-N3) mensagem de erro imprime o conjunto aceito literal.
- (A) caso vermelho com o literal do template (`GO | NO-GO | GO-WITH-CONDITIONS`).
- (B-N4/R-S6) OWNER-GA-CUT.sh:12 header contradiz :387-389 (só GO
  exato) e rc.2/rc.3 voltaram GO-WITH-CONDITIONS ⇒ corrigir o
  COMENTÁRIO (livre) + runbook W2: rail final GO-WITH-CONDITIONS =
  triagem com Owner, by design.
- (C-N1) assert estrutural: todo step de tournament.yml que referencia
  projection.txt carrega working-directory (landa com o pack).
- (C-N3) escopo do sentinel ENUMERA os arquivos livres que landam no
  mesmo commit canônico (senão touched−scope=∅ reprova).
- (C-U1 + lição sonda-morta) testes por subprocesso assertam STRING
  DISTINTIVA do stderr, não só returncode.
- (C-R-B/R-D/U4) riders W2: medir margem do timeout 25min do
  smoke-install antes do corte; cancel-in-progress ⇒ nunca aceitar
  `cancelled`; npm-publish:443 é a última barreira — runbook sabe.
- (C-N4) higiene: tmp_path, env por fixture autouse (xdist), marker
  serial só se registrado (--strict-markers).

## Rejected / deferred

- (A-MF6 rota "bloco fenced machine-readable") — MERGED em CF-6 via
  coluna Status (mesma propriedade, menos partes móveis).
- Varredura de vocabulário FORA de npm/ (CF-8) — pode ser deferida
  NOMEADA se não couber na rc.4.

## Plan adjustments (aplicados na v4)

§W0.1 (CF-1, B-M2, CF-3, CF-4, B-U4, B-N3, A-template, C-U1) ·
§W0.2 (CF-5) · §W0.3 (CF-6, CF-8) · §W0.4 (CF-2) ·
§W1 (CF-9, B-M5, C-N1, C-N3) · §W2 (CF-7, CF-3, B-N4, C riders) ·
§Riders (B-U2) · §AC (todas).

## Round verdict

**PROCEED** — design-coherent. NÃO autoriza ship: a cascata V0-V3
(V2 Codex fail-closed + V3 Owner GPG) segue sendo o único gate.
