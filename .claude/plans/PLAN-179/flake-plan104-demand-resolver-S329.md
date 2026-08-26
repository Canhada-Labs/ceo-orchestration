# Flake `test_waive_scoped_to_changed_paths` — mecanismo, classificação e cura (S329)

**Status:** CURADO no lado livre (`.claude/scripts/persona_demand_scan.py`).
**Classificação:** SCANNER — e o defeito é de PRODUTO, não só de teste.
**Segundo sítio da mesma classe, medido e NÃO curado (fora do meu FILE ASSIGNMENT):**
`.claude/scripts/persona_demand_resolver.py:525` — diff proposto na §6.

---

## 1. O que estava vermelho, exatamente

CI: run **33005244561**, workflow `Validate CEO Orchestration governance`,
headSha `f787cf22d66d702cffa87251f0f557547dfc0626`, `conclusion=failure`,
criado 2026-08-26T19:27:28Z.

- Job: **`Governance, health, contamination, shellcheck`**
- Step **26**: **`Run v1.0.1 test roots (PLAN-152 tests-01)`**

Linha do log (`gh run view --job 98297187716 --log-failed`):

```
Governance, health, contamination, shellcheck	Run v1.0.1 test roots (PLAN-152 tests-01)	2026-08-26T19:47:27.3699660Z FAILED .claude/hooks/_lib/tests/test_plan104_demand_resolver.py::TestWaiveTimingSemantics::test_waive_scoped_to_changed_paths - AssertionError: 0 != 1
```

O mesmo job traz uma **segunda** falha independente — `opus-4-7-profiler-smoke`,
step 5 `Run profile-opus-4-7.py --hook-latency (p95/p99 gate)`. Essa é a classe
de runner-drift já descrita no `CLAUDE.md` §5 (pacote B), **não** é este flake.

---

## 2. Mecanismo

`_scan_commit_files` montava o horizonte como `f"--since={hours}h"` com
`hours=168`. O parser de *approxidate* do git só reconhece uma palavra de
unidade a partir de quatro caracteres (`"hour"`), então **`168h` não é uma
duração para o git**: o `h` não casa com nada e os dígitos caem em
`pending_number()`, que só guarda um número quando ele cabe num campo de data
(`<32` → dia-do-mês, `<13` → mês, 1970..2099 → ano). **168 não cabe em nenhum,
é DESCARTADO, nenhum campo é tocado — e o corte fica em *agora*.**

`git log` então sai com **rc=0 e stdout vazio**. Não há como o chamador
distinguir isso de uma semana genuinamente parada; `_git()` engolir stderr é
irrelevante aqui, porque **o git teve sucesso**.

Por que o teste FLAKAVA em vez de falhar sempre: ele faz os dois commits e o
scan dentro do mesmo segundo de relógio, e `--since` é **inclusivo**. Se o
`git log` cai no mesmo segundo dos commits, eles sobrevivem ao corte e o teste
passa; se o scan atravessa para o segundo seguinte, os commits ficam antes do
corte e somem — `0 != 1`. O teste nunca pediu nada **mais velho que agora**,
por isso jamais poderia falhar de forma determinística.

### 2.1 Reprodução determinística do parser

Comando: `python3 <scratch>/probe_since.py` — um repo com commits em
now, −1min, −5min, −30min, −61min, −5h, −24h, −7d, −10d:

```
--since='168h'           rc=0 n=1  ['m-0']
--since='168.hours.ago'  rc=0 n=8  ['m-0','m-1','m-5','m-30','m-61','m-300','m-1440','m-10080']
--since='7.days.ago'     rc=0 n=8  [idem]
--since='168 hours ago'  rc=0 n=8  [idem]
--since='24h'            rc=0 n=7  [...'m-1440']
--since='2h'             rc=0 n=9  [TUDO, inclusive m-14400 = 10 dias]
--since=(none)           rc=0 n=9

--- 12 amostras de --since=168h ao longo de ~6 s ---
t=17:04:46.033  n=0  []      (… todas as 12 amostras n=0)
```

Leitura: `2h` vira **dia-do-mês 2** (admite um commit de 10 dias);
`168h` vira **agora** (admite quase nada). Nenhum dos dois erra em voz alta.
`24h` parece certo por coincidência do dia corrente — hoje é dia 26, então
"dia 24" ≈ 2 dias atrás; um commit de 30 h passaria por uma janela que se lê
como "24 horas".

### 2.2 Identificação exata do corte + inclusividade

Comando: `python3 <scratch>/probe_boundary.py` — commits em now−300 s,
−60 s, −5 s, −2 s, −1 s e now:

```
base(now, truncado ao segundo) = 2026-08-26T20:06:30+00:00
--since=168h            survivors: ['s+0|2026-08-26T20:06:30Z']
--since=168.hours.ago   survivors: ['s+0','s-1','s-2','s-5','s-60','s-300']
--since=<ts exato de s-1> survivors: ['s+0','s-1']   (inclusive? True)
```

**O corte é o segundo corrente.** Um commit de UM segundo de idade já é
excluído. E `--since` admite o commit que está exatamente no corte — é essa
inclusividade que deixava o teste canônico passar 90 % das vezes.

---

## 3. Impacto de produto (o achado maior que o flake)

Mesma execução, Parte 2, sobre o repositório VIVO:

```
BEFORE (--since=168h)      total=1   by_type={'branch_ahead': 1}
AFTER  (168.hours.ago)     total=35  by_type={'branch_ahead': 1, 'auth_edit': 28, 'test_edit': 6}
```

A superfície de demanda por edição de arquivo (`auth_edit`, `test_edit`,
`detect_edit`) estava **morta em produção**: 0 de 34. O único evento que o
scanner ainda produzia vinha de `_scan_branch_ahead`, que não usa `--since`.

> ⚠ **Consequência que o CEO precisa decidir:** com a cura, um `/ceo-boot`
> passa a abrir ~34 `persona_demand_opened` reais. Se ficarem sem
> correspondência dentro da janela de 24 h, o 19º check vira **red**. Isso é o
> comportamento pretendido do PLAN-104 finalmente funcionando — mas não é
> inerte, e não era o estado de ontem.

---

## 4. Cura (lado livre)

`.claude/scripts/persona_demand_scan.py` — 23 inserções, 2 remoções:

- novo `_since_arg(hours)` que devolve um **instante ISO-8601 UTC absoluto**,
  tirando o parser de approxidate do caminho (mesma forma que
  `session-graph-build.py:294` já usava — prior art no próprio repo);
- call-site `f"--since={hours}h"` → `_since_arg(hours)`;
- docstring do módulo, que documentava a forma quebrada, corrigida.

A escolha de arquitetura é deliberada: não patchar o ramo (`168h` → `168.hours.ago`)
e sim **remover a classe do sítio** — sem expressão relativa não há
mis-parse possível, nem dependência de locale/TZ.

---

## 5. Antes / depois (todos os números são de comandos executados)

| medida | comando | antes | depois |
|---|---|---|---|
| classe canônica isolada | `pytest ".../test_plan104_demand_resolver.py::TestWaiveTimingSemantics" -p no:cacheprovider -q` ×20 | 2/20 falhas | — |
| idem, 2ª batelada (código revertido p/ HEAD) | idem ×20 | 1/20 falhas | — |
| **idem, pós-cura** | idem ×40 | — | **0/40** |
| arquivo canônico inteiro `-m serial` | `pytest ".../test_plan104_demand_resolver.py" -m serial -p no:cacheprovider -q` ×10 | (CEO mediu 3/10) | **0/10** |
| driver standalone (sem pytest) | `python3 <scratch>/driver.py` | 3 anomalias em 16 rodadas | — |
| novo arquivo de regressão | `pytest .claude/scripts/tests/test_persona_demand_scan_window.py -q` | **6 failed, 5 passed** | **11 passed** (rc=0) |
| suíte dos consumidores do scanner | 5 arquivos, ver §5.1 | — | **57 passed** (rc=0) |
| env-hygiene | `python3 .claude/scripts/check-test-env-hygiene.py` | — | **rc=0**, "test-env hygiene clean" |

Baseline agregado do flake antes da cura: **3 falhas em 40 execuções (~7,5 %)**.

O `--since` revertido para medir o "antes" foi restaurado no mesmo comando
atômico e verificado por hash:
`CURED_SHA=3a833855130096af81ef07751f1c2ef3bdd2a2b3a058cbefda8063566d3035df`,
`RESTORED_SHA` idêntico → `RESTORE: OK (byte-identical)`.

### 5.1 Consumidores exercitados

`test_plan104_demand_scan.py`, `test_plan104_demand_resolver.py`,
`test_plan104_microbench.py`, `test_plan132_codex_review_observe.py`,
`test_persona_demand_scan_window.py` — 57 passed, rc=0 (medido sem pipe).

CLI ainda funciona: `python3 .claude/scripts/persona_demand_scan.py --repo . --no-emit --json`
→ rc=0, 35 linhas.

---

## 6. Segundo sítio da MESMA classe — medido, NÃO curado

Censo mecânico de `--since=` na árvore viva (excluídos `plans/`, `npm/`, `dist/`):

| sítio | forma | veredito |
|---|---|---|
| `persona_demand_scan.py:208` | `f"--since={hours}h"` | **QUEBRADO** → curado nesta wave |
| `persona_demand_resolver.py:525` | `f"--since={TREND_WINDOW_HOURS}h"` (=168) | **QUEBRADO** — fora do meu escopo |
| `ceo-boot.py:348` | `"--since=24 hours ago"` | OK (palavra completa) |
| `session-graph-build.py:294` | `strftime("%Y-%m-%dT%H:%M:%SZ")` | OK (absoluto) |
| `memory-prioritize.py:203` | `f"{since_days}.days.ago"` | OK |

Prova do segundo sítio (`python3 <scratch>/probe_resolver.py`), repo com
`src/auth.py` de 3 dias e um trailer `Persona-Waive:` de 2 dias:

```
TREND_WINDOW_HOURS = 168
scanned auth demands (cured scanner): 1
emit_waives_for_scanned -> n = 0        (esperado >=1 se a janela funcionasse)
  resolver git log --since=168h            -> rc=0 subjects=[]
  resolver git log --since=168.hours.ago   -> rc=0 subjects=['docs: readme', 'feat: add auth']
```

O varredor de trailers de waive está igualmente morto. Diff proposto
(**não aplicado** — arquivo fora do FILE ASSIGNMENT):

```diff
--- a/.claude/scripts/persona_demand_resolver.py
+++ b/.claude/scripts/persona_demand_resolver.py
@@
-            ["git", "log", f"--since={TREND_WINDOW_HOURS}h",
+            ["git", "log",
+             "--since=" + (
+                 datetime.now(timezone.utc)
+                 - timedelta(hours=TREND_WINDOW_HOURS)
+             ).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "--pretty=format:__SHA__%H%n%B%n__END_COMMIT__"],
```

Verificado: a linha 30 do módulo é `from datetime import datetime, timezone` —
**falta `timedelta`**, então o diff acima precisa também de:

```diff
-from datetime import datetime, timezone
+from datetime import datetime, timedelta, timezone
```

A alternativa mínima de um caractere seria `f"--since={TREND_WINDOW_HOURS}.hours.ago"`,
que corrige o comportamento mas deixa a classe viva no sítio.

---

## 7. Achado de teste (canônico — só relato, não editei)

`test_plan104_demand_resolver.py:484` e `:526`:

```python
n = self.resolver.emit_waives_for_scanned(scanned, log, repo)
self.assertGreaterEqual(n, 0)
```

`n` é uma contagem não-negativa por construção: **a asserção não pode falhar**.
E como o §6 mostra que `n` é estruturalmente 0, a metade "waive" de
`TestWaiveTimingSemantics` — que é o que o nome da classe promete — nunca foi
verificada. Depois de curar o §6, a asserção deveria virar `assertEqual(n, 1)`
para o caso `test_waive_scoped_to_changed_paths`. **Isso exige cerimônia
assinada pelo Owner** (arquivo canônico); não é pré-requisito para o flake,
que já está curado pelo lado do scanner.

Nenhuma edição do teste canônico é necessária para fechar o vermelho do main.

---

## 8. Novo arquivo de regressão

`.claude/scripts/tests/test_persona_demand_scan_window.py` (333 linhas,
`TestEnvContext`, `.claude/scripts/tests/` já está em `testpaths`).

Todo cenário **data os commits no PASSADO** — é o que torna o vermelho
determinístico em vez de 1-em-10:

- `TestApproxidateMechanism` — fixa o comportamento do **git**, não o nosso:
  `168h` colapsa a janela, `2h` vira dia-do-mês, `--since` é inclusivo. Se um
  git futuro aprender a ler `168h`, a asserção falha e a razão de existir do
  `_since_arg()` é re-declarada em vez de sumir em silêncio.
- `TestSinceArgIsAbsolute` — contrato do instante ISO-8601 + guarda anti-rot
  que lê o arquivo **em disco** procurando approxidate de unidade nua.
- `TestScannerSeesAgedCommits` — ponta a ponta; inclui a **borda distante**
  (commit de 8 dias continua FORA: a cura não é "varrer tudo") e um
  **controle positivo** que replanta o defeito reescrevendo só o token
  `--since=` a caminho do git, reproduzindo o MECANISMO e não um retorno
  stubado.
- `TestLiveRepoHorizon` — read-only: 168 h sobre o repo real precisam abranger
  mais de um commit.

Prova do vermelho no código antigo (scanner revertido para HEAD):
**6 failed, 5 passed**. Os 5 que passam são os 3 de `TestApproxidateMechanism`
(asserções sobre o git, independentes da nossa versão), a borda distante
(passa vacuamente quando nada é detectado) e o caso de mesmo-segundo, que é
justamente o flake.

---

## 9. Risco residual

1. **Comportamento novo, não inerte.** ~34 demandas reais passam a abrir. Ver
   o aviso da §3. Se o CEO quiser aterrissar sem acender o 19º check, a opção
   é landar a cura junto com um despacho das personas ou com a kill-switch
   `CEO_PERSONA_DEMAND_LEDGER_DISABLED=1` — decisão do Owner, não minha.
2. **O segundo sítio (§6) continua vivo.** Enquanto não for curado,
   `emit_waives_for_scanned` devolve 0 sempre e nenhum `Persona-Waive:`
   funciona.
3. **`24h` no `ceo-boot.py` está correto por forma** (`"24 hours ago"`), mas
   qualquer novo sítio que escreva `{N}h` reintroduz a classe. A guarda
   anti-rot da §8 cobre **apenas** `persona_demand_scan.py`. Um censo com
   guarda de repositório inteiro é uma unidade separada.
4. **`_git()` continua engolindo stderr.** Não foi a causa aqui (o git saiu 0),
   mas continua sendo uma superfície onde uma falha real vira janela vazia
   silenciosa. Não toquei — está fora do mínimo desta cura.
5. **Medição local, macOS, git 2.50.1 (Apple Git-155).** O parser de
   approxidate é do `date.c` do git e não é específico de plataforma; o CI
   (ubuntu) reproduziu o mesmo `0 != 1`, o que é consistente.
