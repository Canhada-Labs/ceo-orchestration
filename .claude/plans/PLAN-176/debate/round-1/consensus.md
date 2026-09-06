---
plan: PLAN-176
round: 1
rounds_synthesized: [round-1]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "frontmatter — o `id: PLAN-176` fica; o arquivo é `PLAN-176-model-currency-refresh.md` (o path `.claude/plans/PLAN-176.md` do brief NÃO existe em disco); budget_tokens ganha unidade + budget_usd_estimate; depends_on registra a decisão de ADR-136-AMEND-1"
  - "§1 — `Precedência: caller > env > preference > default do schema` (:44-45) reescrita: T é TETO (seleciona × valida), não fallback; a perna `env` vira conjunto FECHADO nomeado, proibida de carregar path para o registry T, com evento por override"
  - "§1 — `fail-closed p/ default` (:43) renomeado: é degradação silenciosa; declarar o evento emitido e quem o lê"
  - "§2 W0 — cortado em W0a (canônico: models-registry.json, _lib/model_registry.py, validate.yml, gate-scripts-manifest.txt) e W0b (livre: models-preference.json, check-model-literals.py, testes); ≤8 paths por pacote, UMA assinatura no W0a"
  - "§2 W0 — `check-model-literals.py` (o lint que sustenta a fronteira T/P) entra no `.claude/governance/gate-scripts-manifest.txt`, precedente `verify-counts.sh`"
  - "§2 W0 — destino de `.claude/data/canonical_models.json` (expirado 2026-09-01) DECIDIDO: absorvido pela camada P e apagado, ou declarado fora de classe com razão"
  - "§2 W1 — o fetcher sai de `check-substrate-watch.py`: módulo próprio, canônico, com a allowlist de hosts DENTRO da superfície cerimonial; consumir o ledger do substrate-watch continua permitido"
  - "§2 W1 — allowlist concreta host+path (o plano nomeia ZERO hosts) e um evento `egress_destination_detected` por despacho (taxonomia já shipada em `_lib/audit_emit.py:772`)"
  - "§2 W1/W2 — a garantia `NADA do repo … sai` (:75-77) reescopada: vale para o fetch do W1; o W2 declara seu PRÓPRIO egress (destino, corpo, redação)"
  - "§2 W1 — a citação ADR-114 sai do lugar de controle de egress (objeto errado) e vira, se ficar, uma nota de simetria"
  - "§2 W2 — o AC troca `check-model-literals` pelo guard que de fato fica vermelho num edit de campo T em JSON (§3 :93), com controle positivo"
  - "§3 — cada kill criterion ganha arquivo de estado rastreado, comando que o lê e dono; limiares re-expressos em CICLOS da rotina, não em dias de calendário"
  - "§3b — ACs viram checkboxes sob heading de wave com linhas `Check:` (hoje: 0 checkbox, 0 `Check:`, dentro da janela §13.4 por created 2026-08-11 + status reviewed) e o W0 ganha ACs próprios (hoje tem ZERO, sendo a dependência dura de W1-W3)"
  - "§3b — o oracle `replacements ⊆ valid_override_ids` nasce VERMELHO em HEAD: ou a cura entra no W0 ou publica-se um conjunto-vermelho exato (precedente `ownership-expected-reds.txt`)"
  - "§3b — o draft `PLAN-176/adr-149-amendment2-draft.md` renumerado (Amendment 2 já está landado e ratificado em `.claude/adr/ADR-149-model-id-allowlist.md:209`) e o §1 deixa de citar como DECIDIDO o que o §3b chama de draft"
  - "§3b — id completo do RemoteTrigger ou AC baseada em configuração (`trig_014Y…` truncado, aparece só no próprio plano)"
synthesized_at: 2026-09-06T05:05:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-176 — consenso do round 1

Três críticos, três `ADJUST`, 18 itens bloqueantes somados (6 + 5 + 7). Nenhum
pediu `REJECT`. Toda claim abaixo foi re-verificada em disco em HEAD antes de
virar ajuste; as que não sobreviveram estão em `## Single-agent insights
rejected / deferred`. **O bloco de críticas chegou TRUNCADO em 24.000 chars** —
a cauda do `summary` do Critic-C não foi lida; os `risks`/`missing` dos três
chegaram completos e foram os insumos desta síntese.

**O que o round CONFIRMA a favor do plano.** A tese central — o split T/P
preserva a cerimônia POR CONSTRUÇÃO — é VERDADEIRA e mecânica, e os três
críticos a verificaram independentemente. Medido aqui com o próprio oráculo
(`python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>`, que
imprime `path<TAB>1|0`):

    .claude/governance/models-registry.json   1   (sentinel-gated)
    .claude/data/models-preference.json       0   (livre, PR auditado)

Zero extensão da guard-list é necessária. É a decisão mais barata e mais forte
do plano e nenhum ajuste abaixo a toca.

## Consensus findings (2+ agents flagged)

### C1 — CRITICAL — `Amendment 2` do ADR-149 já existe, landado e ratificado (Critic-B, Critic-C)

`.claude/adr/ADR-149-model-id-allowlist.md:209` = `## Amendment 2 (S338 — Fable
5.1 joins the working set; floor, fallback and pin unchanged)`; `:61` é o
Amendment 1. O plano cita a doutrina T/P como «decidida no ADR-149 Amendment 2»
(§1, cabeçalho) e o runbook (§3b) manda formalizá-la por cerimônia a partir de
`PLAN-176/adr-149-amendment2-draft.md`. O número está OCUPADO por material
Owner-signed: executar o runbook como escrito cria dois Amendment 2. Corolário
que só o Critic-B nomeou e eu confirmo: **em HEAD não existe autoridade nenhuma
para a doutrina T/P** — o §1 apresenta como herdado e decidido aquilo que o §3b
ainda chama de rascunho.

### C2 — CRITICAL — o W1 injeta rede no instrumento que se declara sem rede (Critic-A, Critic-B, Critic-C)

O §2 W1 diz que o plano «APENAS estende `check-substrate-watch.py` com o probe
upstream faltante». O cabeçalho do próprio arquivo diz o contrário:
`.claude/scripts/check-substrate-watch.py:10-11` — «agents stay no-network under
ADR-136-AMEND-1 … the one network action, so it is Owner-run by design» — e
`:26-32` registra o endurecimento «zero side effects … the argv is hardcoded in
`_PROBE_ARGV` … the ledger can NEVER supply a command (Codex R2 P0)». Medido:
`grep -cE 'urllib|urlopen|http'` sobre o arquivo = **0**. Duas consequências:
(i) a mudança de postura é uma decisão de ADR (ADR-136-AMEND-1), que o plano
não nomeia; (ii) o oráculo dá `.claude/scripts/check-substrate-watch.py 0` —
**não canônico** — então a allowlist fixa de hosts, único lastro da garantia de
egress, moraria num arquivo editável sem sentinel. O fetcher tem de ser módulo
próprio e canônico; consumir os ledgers do substrate-watch segue legítimo.

### C3 — HIGH — ADR-114 é o controle errado, e a garantia de egress está escopada à onda errada (Critic-A, Critic-B, Critic-C)

`.claude/adr/ADR-114-codex-egress-redaction-symmetry.md:18-25` define o objeto:
prompts do framework enviados ao Codex contendo fragmentos de código, citações
de evidência e chaves HMAC. É um redator de prompt de LLM, ligado em call-sites
enumerados. Um `GET` sem body, sem query e sem headers customizados (§2 W1,
:73-78) **não tem o que redigir** — a citação e a garantia não podem ser as duas
load-bearing. Segundo: a frase absoluta «NADA do repo (nem números de versão
locais) sai em requisição alguma» (:75-77) vive no bloco do W1, enquanto o W2
(:82-83) abre um PR autenticado carregando «o relatório+digests como evidência»
— repo-derived data saindo por outra porta. Reescopar, não relaxar.

### C4 — HIGH — o lint que sustenta a fronteira T/P fica FORA da cerimônia que ele protege (Critic-A, Critic-B)

Medido: `.claude/scripts/check-model-literals.py 0` — não canônico (e o
diretório `.claude/scripts/*.py` não casa nenhum padrão da guard-list). O
oráculo também dá `0` para `.claude/scripts/local/verify-counts.sh`, que mesmo
assim é membro de `.claude/governance/gate-scripts-manifest.txt` (9 membros,
linha 1) — ou seja, **a cura já existe no repo e é barata**: entrar no manifesto
põe a edição do gate sob cerimônia sem alargar `_CANONICAL_GUARDS`. O Critic-B
acrescenta, e confirmo, que o plano nunca diz onde o lint e o grandfather-ledger
moram — e é exatamente o path que decide se o ratchet é autenticado.

### C5 — HIGH — `env` entra na cadeia de precedência sem conjunto fechado, validador ou evento (Critic-A, Critic-B)

§1 `:44-45`: «Precedência: caller > env > preference > default do schema».
Nenhuma variável, prefixo, validador ou auditoria é nomeada. O repo já modela
esse vetor como ameaça: `.claude/hooks/_lib/audit_emit.py:765` registra
`env_var_hijack_blocked`, e o CLAUDE.md §5 documenta a classe paga duas vezes
(`BASH_ENV` + `argparse.py` em `sys.path[0]` na S345;
`WHOLE_DIR_OVERRIDE_CARRIERS` neutralizando `CLAUDE_PROJECT_DIR_NATIVE` na
S321/S322). O Critic-B vai além e lê a cadeia inteira como colocando a camada
sentinel-gated em ÚLTIMO lugar, contradizendo o §1 (`:32-36`, «id concreto
Owner-signed … nunca troca sozinho»). Verifiquei o texto: ele é genuinamente
AMBÍGUO — «default do schema» pode ser piso ou teto. A ambiguidade é o defeito;
a cura é dizer no plano que T é TETO (seleciona × valida), não fallback.

### C6 — HIGH — o W0 não cabe no modelo de operação v2 (Critic-A, Critic-B, Critic-C)

Enumeração do §2 W0 classificada pelo oráculo, medida aqui:

    models-registry.json          1    | models-preference.json     0
    _lib/model_registry.py        1    | check-model-literals.py    0
    .github/workflows/validate.yml 1   | (2 arquivos de teste)      0
    ADR-149-model-id-allowlist.md 1
    gate-scripts-manifest.txt     1

≥9 paths, **5 canônicos** — acima do teto de 8 paths e exigindo assinatura GPG.
Os três críticos convergem no corte W0a (canônico) / W0b (livre); os limites que
cada um propôs diferem, o corte fica com o CEO.

### C7 — MEDIUM — uma segunda tabela de modelos, JÁ EXPIRADA, mora no diretório onde o W0 cria a camada P (Critic-A, Critic-B; rot também citada pelo Critic-C)

`.claude/data/canonical_models.json:10` = `"valid_until": "2026-09-01"` —
expirada em 2026-09-06. Medido: `grep -c 'claude/data'
.claude/hooks/check_canonical_edit.py` = **0** (o diretório é livre por design da
camada P, o que está certo). O §4 do plano prevê a rot («`canonical_models.json`
sem gen-5 e expirando 01/09») mas o §2 W0 nunca decide supersede / absorve /
coexiste — duas grafias vivas do mesmo fato.

### C8 — MEDIUM — os kill criteria não têm contador, arquivo de estado nem dono, e usam unidade de calendário contra cadência semanal (Critic-A, Critic-C)

§3 `:88-101`: «>2 falsos-positivos/mês», «3 falhas consecutivas de um vendor»,
«mais velho que 30d», fixture mensal de falso-negativo. Nenhum nomeia arquivo
rastreado nem o comando que o lê — no incidente ninguém sabe dizer se o limiar
foi cruzado. Contraste no repo: `scripts/tests/ownership-nightly-gate.sh` compara
um conjunto EXATO de ids contra arquivo rastreado. O Critic-C acrescenta a perna
de unidade: contra uma rotina semanal, «>2 FP/mês» dispara acima de ~50 % de taxa
de FP e «3 falhas consecutivas» = 3 semanas cego.

## Single-agent insights kept

- **K1 (Critic-A) — o gate §13 do PLAN-SCHEMA está vacuamente verde.**
  `PLAN-SCHEMA.md §13` grandfathera planos criados antes de 2026-06-12; este foi
  criado 2026-08-11 com status `reviewed`, logo está DENTRO da janela. Medido no
  arquivo: `grep -cE '^\s*- \[[ x]\]'` = **0** e `grep -cE 'Check:[[:space:]]*\S'`
  = **0**. Sem checkbox e sem `Check:`, nenhuma AC pode ficar vermelha.
- **K2 (Critic-A) — o oracle do W0 nasce VERMELHO em HEAD.**
  `replacement` em `.claude/scripts/model-deprecations.json` inclui `gpt-5.6-sol`;
  `_VALID_MODELS` em `.claude/hooks/_lib/codex_cli_shape.py:97-105` é
  `(gpt-5.5, gpt-5, gpt-5-mini, gpt-5-codex, o3, o3-mini, o4-mini)` — sem
  `gpt-5.6-sol`. Ou a cura entra no W0 (alargando escopo) ou publica-se o
  conjunto-vermelho exato, no molde `ownership-expected-reds.txt`.
- **K3 (Critic-C) — o W0 não tem AC nenhuma.** §3b lista ACs para W1, W2 e W3;
  o W0, que é a dependência dura das três, não tem nenhuma. «W0 landado» não tem
  definição — e o controle positivo óbvio (T bloqueado / P livre pelo oráculo)
  está de graça.
- **K4 (Critic-C) — a AC do W2 nomeia o guard errado.** §3b manda o
  `check-model-literals` ficar vermelho «se o PR tocar campo T», mas o lint varre
  LITERAIS EM CÓDIGO; quem fica vermelho num edit de campo T em JSON é o gate do
  §3 `:93`. A AC como escrita é um controle positivo que não pode acender.
- **K5 (Critic-C) — a AC do W1 mede a parte que já existe.** «relatório lista os
  3 CLIs com {instalado, pin, upstream}» é o que o substrate-watch já faz: passa
  com ZERO cobertura de feed de modelo, que é a razão de ser da onda. E a lane
  Google não tem preço: medido, `grep -ciE 'gemini|google'
  .claude/scripts/cost-table.yaml` = **0**.
- **K6 (Critic-B) — nenhum evento de auditoria para despacho externo.** A
  taxonomia fechada já shipa `egress_destination_detected`
  (`.claude/hooks/_lib/audit_emit.py:772`). A única proveniência que o plano nomeia
  é um sha256 auto-computado (§2 W1, `:71-72`), fora da cadeia HMAC.
- **K7 (Critic-A) — o path do brief não existe.** `.claude/plans/PLAN-176.md` não
  está em disco; o plano é `.claude/plans/PLAN-176-model-currency-refresh.md`
  (161 linhas). Defeito do brief, não do plano — registrado para que o round 2 e
  a cópia do CEO citem o path certo.
- **K8 (Critic-A/Critic-C) — id do RemoteTrigger truncado.** `trig_014Y…` (§3b
  `:106-107`); medido: `git grep -l 'trig_014Y'` retorna **só o próprio plano**.
  AC ancorada em id irrecuperável.

## Single-agent insights rejected / deferred

- **REJEITADO como bloqueante — «budget_tokens 136× abaixo do custo real»
  (Critic-C, R-FIN1).** Não reproduzi o número: ele vem de
  `ceo-cost-transcripts.py --since 7d --by session` (n=25 sessões, agregado de
  TODA a atividade do repo), e o `budget_tokens` do plano orça as ondas DESTE
  plano. Comparar um agregado de sessão inteira contra um orçamento de onda é
  troca de denominador, não fator de 136×. A metade sólida da crítica SOBREVIVE e
  virou ajuste: a soma do próprio breakdown (150-250k + 100-150k + 100-150k =
  350-550k) não fecha com o teto declarado `300-550k`, e faltam
  `budget_usd_estimate` e `tier_mix_estimate`.
- **REJEITADO como must-fix separado — «T em último lugar na precedência»
  (Critic-B, R-SEC1) na sua forma forte.** Verificado o texto: ele é ambíguo,
  não afirma que P vence T. Absorvido em C5 como desambiguação obrigatória
  (T = teto), que é correção de TEXTO; reescrever o resolver antes de a
  ambiguidade ser resolvida seria trocar o MODELO por causa da redação.
- **DIFERIDO — «o resolver é canônico, logo todo fix custa cerimônia»
  (Critic-C, R-FIN12).** Confirmado: `.claude/hooks/_lib/model_registry.py 1`.
  Mas isso é CONSEQUÊNCIA desejada do desenho (o resolver decide confiança), não
  defeito. Vale uma linha de custo declarado no plano, não um ajuste de arquitetura.
- **DIFERIDO ao round 2 — conteúdo de feed como entrada não confiável terminando
  em corpo de PR (Critic-B, R-SEC7)** e **critério de kill auto-referente ao
  branch que a própria rotina escreve (Critic-B, R-SEC8)**. Ambos verificados como
  lacunas reais do texto, mas ambos vivem no W2, que só abre depois do W0; entram
  no round que preceder o W1/W2, não neste.

## Plan adjustments (must-fix)

1. **Renumerar o draft do ADR** (Amendment 3 ou ADR próprio) e alinhar §1 × §3b:
   nenhum trecho pode citar a doutrina T/P como decidida enquanto o material
   estiver em draft. — §1 cabeçalho, §3b «Draft do ADR-149 Amendment 2». [C1]
2. **Tirar o fetcher do `check-substrate-watch.py`**: módulo novo, canônico, com
   a allowlist de hosts dentro da superfície cerimonial; consumo de ledger
   permanece. — §2 W1. [C2]
3. **Decidir e nomear no plano a mudança de postura ADR-136-AMEND-1** (agente
   noturno no-network / ação de rede Owner-run) — ou desenhar o W1 de modo a não
   tocá-la. — §2 W1, frontmatter `depends_on`. [C2]
4. **Substituir a citação ADR-114** pelo controle de ingress/egress real e
   **reescopar** a garantia absoluta ao W1, com uma linha própria de egress do W2
   (destino, corpo, redação). — §2 W1 `:73-78`, §2 W2 `:79-84`. [C3]
5. **Publicar a allowlist concreta host+path** (o plano nomeia zero hosts) e
   emitir `egress_destination_detected` por despacho. — §2 W1. [C3, K6]
6. **`check-model-literals.py` entra no `gate-scripts-manifest.txt`**, e o plano
   fixa os paths do lint e do grandfather-ledger. — §2 W0, §1 «Fechamento da
   classe». [C4]
7. **Reescrever a precedência**: T como TETO; conjunto FECHADO de env vars,
   proibidas de carregar path para o registry T; evento por override; e trocar
   «fail-closed p/ default» por a semântica real + o evento emitido. — §1
   `:43-45`. [C5]
8. **Cortar o W0 em W0a (canônico, ≤8 paths, UMA assinatura) e W0b (livre)**. —
   §2 W0. [C6]
9. **Decidir o destino de `.claude/data/canonical_models.json`** (absorvido e
   apagado, ou fora de classe com razão). — §2 W0, §4. [C7]
10. **Cada kill criterion com arquivo de estado rastreado, comando de leitura e
    dono; limiares em CICLOS da rotina.** — §3. [C8]
11. **ACs viram checkboxes com linhas `Check:` sob heading de wave, e o W0 ganha
    ACs próprias** (controle positivo T bloqueado / negativo P livre pelo
    oráculo). — §3b. [K1, K3]
12. **Resolver o oracle vermelho** (`gpt-5.6-sol` ausente de `_VALID_MODELS`):
    cura no W0 ou conjunto-vermelho exato publicado. — §1 «Fechamento da classe»,
    §3b. [K2]
13. **Trocar o guard citado na AC do W2** pelo que fica vermelho num edit de
    campo T em JSON. — §3b. [K4]
14. **AC do W1 medindo feeds de modelo** (não os 3 CLIs), e definição de «vendor
    ativo» = membro do working set do ADR-149 **e** com linha em
    `cost-table.yaml`, fail-closed. — §3b, §2 W1. [K5]
15. **Id completo do RemoteTrigger** ou AC baseada em configuração; e corrigir o
    nome do arquivo do plano onde ele for citado. — §3b. [K7, K8]
16. **Fechar a aritmética de budget** (breakdown soma 350-550k contra teto
    300-550k) e acrescentar `budget_usd_estimate` + `tier_mix_estimate`. —
    frontmatter. [rejeitado-parcial R-FIN1]

## Round verdict

**ESCALATE-TO-OWNER.**

18 itens bloqueantes somados e, entre eles, **dois que nenhuma rodada de debate
pode resolver por reescrita de texto** — são decisões do Owner, sobre material
que ele assinou:

- **D1 — o número do Amendment.** `ADR-149:209` é Owner-signed (cerimônia
  `wave-fable51`). Renumerar para Amendment 3 ou abrir ADR dedicado é chamada do
  Owner, e sem ela a doutrina T/P não tem autoridade em HEAD (C1).
- **D2 — a postura no-network.** `check-substrate-watch.py:10-11` declara a
  postura sob ADR-136-AMEND-1. Injetar rede ali, ou construir o fetcher ao lado,
  muda um invariante de contenção (C2).

O rótulo `design-coherent` **NÃO** é registrado: o round termina com itens
bloqueantes abertos. O plano permanece `reviewed`; **o W0 não abre esta noite** —
e não abriria de todo modo, porque o W0a exige assinatura GPG e o Owner está
ausente (regra da noite S347). Recomendação de sequência: o Owner responde D1 e
D2; o CEO absorve os must-fix 1-16 no texto do plano; **round 2** re-verifica o
plano corrigido antes de qualquer pacote canônico. Os itens diferidos (feed como
entrada não confiável no corpo do PR; kill criterion auto-referente ao branch da
própria rotina) entram no round que preceder o W1/W2.
