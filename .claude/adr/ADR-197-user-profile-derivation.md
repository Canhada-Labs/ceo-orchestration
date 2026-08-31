---
adr_id: ADR-197
title: O perfil `user` é DERIVADO de `settings.base.json` por subtração declarada — nunca uma segunda cópia literal, e a lista de exclusão é dado com leitores
status: ACCEPTED
accepted_at: 2026-08-31
proposed_at: 2026-08-30
proposed_by: CEO (S331 — PLAN-169 OQ-E5, wave-s330-F; classificação por mérito em `4f4df3a`, código em `6a51eca`)
decided_by: Owner (ratificado — a assinatura GPG real é o `.asc` commitado sobre `PLAN-169/wave-s330-F-approved.md`, land `303ae55` na S332; este flip textual chegou por cerimônia própria na S334, como ADR-194 e ADR-196 registraram)
risk_tier: B
debate_required: false
debate: "Sem debate formal. A decisão de PRINCÍPIO já tinha precedente ratificado (ADR-194 rota de entrega, ADR-196 confinamento de escrita: o metadado vira DADO com leitores em vez de literal replicado); o que faltava era MEDIÇÃO, e ela existe — classificação por mérito dos 26 hooks só-na-base contra o critério declarado (`4f4df3a`, 43,5 KB, evidência por hook), OQ-E5 ratificada pelo Owner em 2026-08-27, e as quatro decisões de empacotamento ratificadas em 2026-08-30 (FU-F-ACCEL no mesmo patch; OQ-F1 congelada; OQ-F3 incluída; ADR novo em vez de AMEND). A revisão adversarial é o pair-rail cross-vendor sobre a sombra."
numbering_note: "197 era o próximo livre medido no disco na S331 (ADR-000..ADR-196). Alocado NO MOMENTO da escrita, conforme a emenda 8.2 do ADR-195."
related_plans: [PLAN-169, PLAN-183, PLAN-185, PLAN-128]
related_adrs: [ADR-194, ADR-196, ADR-155, ADR-192]
---

# ADR-197 — Derivação do perfil `user`

## Context

`templates/settings/settings.user.json` é o que um adopter que roda
`install.sh --ceremony user` recebe como `.claude/settings.json`. Até esta wave
ele era uma **cópia manual** de `settings.base.json` com hooks apagados à mão,
congelada em `9777a8d` (v1.0.0) e nunca reconciliada.

O que a S330 mediu (`.claude/plans/PLAN-169/s330-ceremony-F/hook-classification-S330.md`):

* **26 basenames** registrados na base e ausentes do template `user`. O
  `_comment` do próprio arquivo afirmava que a remoção era de **"exatamente
  10"**, e nomeava-os.
* Dos 10 nomeados, **só 5 sustentam o critério que o comentário declara**
  («hooks que bloqueiam edição ou exigem GPG/sentinel»), e **2 não pertencem à
  lista por nenhuma leitura** (`check_scratchpad_access.py`,
  `check_skill_reference_read.py`).
* Dos 16 restantes, **13 já faltavam na v1.0.0** — não são defasagem posterior,
  são a cópia tendo nascido incompleta.
* Duas divergências de matcher/registro que o `_comment` afirmava não existir:
  um matcher estreitado à mão (`check_anti_ceo_overhead.py`) e uma segunda
  registração silenciosamente ausente.
* A citação de proveniência do `_comment` — `PLAN-122 WS-4` — **não existe em
  ref git nenhum**: nem o arquivo, nem um commit que o mencione.

E, decisivamente: **nada lia nada disso.** Nenhum ADR decide a composição do
perfil (`ADR-155-AMEND-1` só diz que a instalação `user` pula `install_spec_v1`);
nenhum oráculo compara o template com a base (`test_template_dogfood_parity.py`
verifica `model`/`availableModels`, e os oráculos da wave E verificam que o
*upgrade reproduz o template*, não que o *template esteja certo*).

A composição do perfil `user` era portanto justificada **exclusivamente pelo
comentário do arquivo que ela descreve** — um documento auto-referencial que
aponta para um plano inexistente e cujas duas afirmações verificáveis eram
falsas. Um numeral em prosa JSON não é vigiado por regra alguma; foi assim que
apodreceu. É a forma «instrumento verde cuja pergunta envelheceu», uma camada
acima: aqui não havia sequer instrumento.

## Options considered

1. **Corrigir a cópia à mão** (acrescentar os 16, ajustar os 2 campos).
   Rejeitada: restaura o valor de hoje e reconstrói o mecanismo de apodrecimento
   intacto. A defasagem voltaria no próximo hook adicionado à base — como voltou
   entre `9777a8d` e a S330.
2. **Manter a cópia e acrescentar um teste de paridade literal** (template ==
   base menos uma lista congelada no TESTE). Rejeitada: move a segunda cópia da
   fonte para o oráculo. O bloqueador §4b do DESIGN-F é exatamente essa forma
   materializada — `test_install_user_skips_governance_hooks.py` carregava uma
   **segunda cópia congelada** da lista de 10, e por isso não podia detectar que
   a lista estava errada.
3. **Derivar o template da base por subtração declarada**, com a declaração
   vivendo como DADO legível por máquina e uma paridade byte-a-byte em CI.
   **Escolhida.**
4. Arquivo-irmão `settings.user.derivation.json` para o spec. Rejeitada **por
   medição**: `check-install-profiles.py` exige bijeção entre
   `templates/settings/*.json` e hook stacks, e um arquivo-irmão a quebra
   (reproduzido com controle positivo, DESIGN-F §3.3). O spec vive numa chave
   `_derivation` do próprio template.

## Decision

1. **O perfil `user` é derivado, não copiado.**
   `templates/settings/settings.user.json` é a saída de
   `.claude/scripts/gen-settings-user-template.py` aplicado a
   `templates/settings/settings.base.json` mais o spec de subtração. Editar o
   template à mão é o defeito, não o procedimento: a rota é editar o spec e
   rodar `--write`.

2. **O spec é dado auto-descritivo, embutido no artefato.** Vive na chave
   `_derivation` do próprio template e declara `exclude_hooks` (com `class`,
   `reason` e `evidence` **que resolve** por hook), `env_overrides`,
   `matcher_overrides` e `top_level_exclude`. O gerador lê o spec do arquivo que
   ele mesmo escreve — circular por desenho, com duas saídas explícitas:
   `--spec <path>` para bootstrap e **rc 2 fail-loud** se o arquivo sumir ou
   perder a chave. Nunca um default silencioso.

3. **O critério de exclusão é declarado em três alíneas**, substituindo o
   «bloqueia edição ou exige GPG/sentinel» que 5 dos 10 não satisfaziam. Cada
   exclusão carrega a alínea que a sustenta; uma exclusão sem evidência que
   resolve não passa no oráculo.

4. **`build-plugin.py` deixa de manter lista paralela.** O `hooks.json` do
   plugin é derivado do template e de mais nada. A tabela `ACCEL` era uma
   TERCEIRA cópia das registrações dos quatro aceleradores do PLAN-128, e
   divergente: fixava `review_loop.py` em 60 s e `turbo_sessionstart.py` em
   10 s, enquanto `settings.base.json` **e** o `.claude/settings.json` vivo deste
   repositório rodam 15 s e 5 s. Depois que o roster cresceu, cada um dos quatro
   passava a ser registrado **duas vezes** no plugin. A composição virou função
   pura (`compose_plugin_hooks`), e o marcador de dívida foi **invertido** em
   guard permanente (`PluginHooksHaveNoParallelSource`) que recusa qualquer
   tabela module-level nomeando hook que o template já registra — inclusive uma
   que volte com outro nome.

5. **A paridade é vigiada em CI, não em prosa.** `--check` re-deriva em memória
   e byte-diffa contra o arquivo commitado; roda pela suíte (`.claude/scripts/tests/`
   é coletado) **e** por step dedicado em `validate.yml`, com contrato de saída
   0 in-sync / 1 drift / 2 input inutilizável — fail-closed: um spec que o
   gerador não consegue ler não é um passe.

6. **Pontos cegos ficam declarados, não escondidos:** o keyset da paridade não
   vigia matcher (§0 da classificação); `top_level_*` exige exclude derivado
   (§3); a identidade de um hook nem sempre é o basename `.py` (§3.1); e há
   TOCTOU entre `--check` e um editor concorrente — o gate é de CI e de
   pre-commit, não um lock.

## Consequences

* O roster `user` vai de **20 para 29 registrações** (28 basenames). O próximo
  `upgrade.sh` de um adopter `--ceremony user` **registra 9 registrações novas**
  (8 hooks + a 2ª registração de `check_output_secrets.py`). Isso
  é o ponto da OQ-E5, não efeito colateral; os riscos por hook estão na
  classificação §5. Dois merecem repetição: `check_config_change.py` entra com
  `CEO_CONFIG_CHANGE_GUARD=1` **explícito** (o default vive em código, e uma
  registração é só tão advisory quanto a setting que ela lê), e
  `codex_review_user_code.py` é DETECT-ONLY por default — nunca roda Codex sem
  opt-in.
* **Uma reversão pós-classificação, decidida pelo Owner (2026-08-30,
  rail-round-7 P2-a):** `check_scratchpad_access.py` fica FORA do roster. O
  matcher casa por sufixo — qualquer caminho terminando em `scratchpad.py` —
  e bloquearia o script homônimo do próprio adopter sem rota praticável,
  contra o critério (a) do spec. A exclusão viaja no `_derivation` com classe
  `bloqueia-edicao`; o CLI `scratchpad.py` continua instalado nas duas
  cerimônias pelo `install.sh`, e o plugin deixa de embarcá-lo
  (`copy_guarded_clis` é condicional ao registro — «guard not registered →
  CLI not needed»).
* **+22.001 B** no `settings.json` de todo adopter `--ceremony user` novo, quase
  tudo `reason`/`evidence`. Declarado, não escondido: encurtá-los é rota
  disponível; removê-los não é — são o que torna a subtração auditável.
* `EXPECTED_TEMPLATE_REGISTRATIONS_USER=20`, congelado em
  `PLAN-169/s329-ceremony-E/EXPECTED-BASELINE.txt:182`, fica **defasado por
  decisão** (ratificada em 2026-08-30): é baseline histórica de cerimônia já
  landada e não é consumida por workflow nenhum — re-rodar `finalize-E.sh`
  pós-wave falha por desenho.
* O plugin passa a rodar `review_loop.py` com 15 s e `turbo_sessionstart.py` com
  5 s, alinhado à base e ao repo vivo. É mudança de comportamento real, aqui
  registrada: os valores antigos não tinham fonte que os sustentasse.

## Blast radius

* **Adopters `--ceremony user`** — superfície de hooks muda no próximo upgrade
  (o mecanismo de entrega é o do pacote E, `5930974`, que já deriva o roster do
  template da cerimônia).
* **Consumidores do plugin** — `hooks.json` deixa de ter registrações
  duplicadas; dois timeouts caem para o valor da base.
* **Este repositório** — nenhum. `.claude/settings.json` não é tocado; a base
  não é tocada. O gerador só escreve `templates/settings/settings.user.json`.
* **Não coberto:** o perfil `maintainer`/base não é derivado por este mecanismo
  e continua canônico por edição direta.

## Verification

* `gen-settings-user-template.py --check` → rc 0 no artefato commitado; rc 1 com
  diff unificado sob um único byte alterado (medido); rc 2 com o spec ausente.
* `test_gen_settings_user_template.py` — 7 classes, **controle vermelho** por
  fixture congelada (`fixtures/settings.user.pre-F.json`, o template de
  `1c34eb5`) contra a própria afirmação do `_comment` antigo: 17 registrações
  ausentes e 2 campos divergentes, nomeados.
* `PluginHooksHaveNoParallelSource` — 7 testes; **controle positivo** que
  replanta a tabela `ACCEL` e o extend pré-cura deixa **3 vermelhos** nomeando o
  ofensor (`{'ACCEL': [accel_dispatch.py, codex_review_user_code.py,
  review_loop.py, turbo_sessionstart.py]}`), a duplicata de
  `(evento, matcher, comando)` e a contagem 2 onde deve ser 1.
* `test_install_user_skips_governance_hooks.py` — deriva a lista de hooks de
  governança **do spec** (com guard anti-vacuidade: não-vazio e contendo
  `check_canonical_edit`), verde contra uma instalação real. Antes desta wave
  ele carregava uma segunda cópia congelada da lista de 10 e por isso não podia
  detectar o erro que a wave corrige.
* `validate.yml` — step dedicado `User-template derivation (PLAN-169 F —
  regen+diff)`; `actionlint` limpo.

## References

* `.claude/plans/PLAN-169/s330-ceremony-F/hook-classification-S330.md` —
  classificação por mérito dos 26, §6 (a recomendação de ADR novo em vez de
  AMEND, e por quê).
* `.claude/plans/PLAN-169/s330-ceremony-F/DESIGN-F.md` — desenho, achados §3,
  bloqueador §4b, follow-ups §5, limites §6.
* ADR-194 (resolução de rota de entrega) e ADR-196 (confinamento de escrita) —
  os dois precedentes da mesma forma: metadado vira dado com leitores.
* ADR-155-AMEND-1 — o único registro anterior que menciona `--ceremony user`.
* PLAN-128 — os aceleradores cuja lista paralela este ADR elimina.
