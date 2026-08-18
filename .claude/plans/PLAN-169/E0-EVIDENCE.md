# PLAN-169 W5 / AC-6 — evidência do E0 (fração serial S)

> **Procedência: VERIFICADA, não re-gerada.** O relatório da S300 foi
> localizado em `~/.rc2-backup/e0-report-s300.txt`, conferido contra o
> hash pinado no `PLAN-179/LEDGER.md:68` (`d07935b3…`) e copiado
> **byte-a-byte** para dentro do repo. `cmp` = idêntico; nenhuma linha
> foi reescrita, reformatada ou sumarizada. O runner **não** foi
> re-executado nesta sessão (não havia motivo: o artefato autentica).

## 1. Artefato

| campo | valor |
|---|---|
| relatório (no repo) | `.claude/plans/PLAN-169/e0-report-s300.txt` |
| origem | `~/.rc2-backup/e0-report-s300.txt` (fora do repo desde a S300) |
| sha256 | `d07935b3fc67d48dd0101a989b64b1ee04e071c3ac8c2550160baf68672e4f34` |
| prefixo pinado | `d07935b3fc67d48d…` (`PLAN-179/LEDGER.md:68`) — **CONFERE** |
| tamanho / mtime da origem | 4803 bytes · 2026-08-09 19:06 (-03) |
| runner | `.claude/plans/PLAN-169/e0-serial-fraction.py` (rastreado) |

## 2. Linha de comando

```
python3 .claude/plans/PLAN-169/e0-serial-fraction.py --i-confirm-w5-signed
```

executado com o **cwd no root do repo** (`--repo` default `.`) e
`--audit-dir` **no default**. Isso não é suposição de conveniência: a
linha 1 do relatório imprime `copiados de
/Users/joaocanhada/.claude/projects/ceo-orchestration`, que é
literalmente o default de `--audit-dir`
(`e0-serial-fraction.py:369-370`); se a flag tivesse sido passada com
outro valor, o relatório mostraria outro caminho. As **flags** são
portanto derivadas do próprio artefato; o *literal* digitado na S300
não está transcrito em lugar nenhum do repo — o que é reconstruído é a
digitação, não os parâmetros efetivos.

### Prova de ordenação exigida pelo AC-6

`--i-confirm-w5-signed` não é uma afirmação de boa-fé: o runner
**recusa** rodar (`return 3`) sem ela e, com ela, checa
`W5-preregistration.md` + `.asc` (i) presentes, (ii) rastreados
(`git ls-files --error-unmatch`), (iii) **sem divergir do HEAD**
(`git diff HEAD --quiet`) e (iv) com assinatura destacada válida do
keyid **pinado do Owner** (`e0-serial-fraction.py:379-425`; o keyid
literal está em `:408`). Ou seja:
o relatório só pôde existir depois do pré-registro assinado e
commitado.

Datas concordam:

- W5 assinado + commitado: `fcac12d` — `2026-08-09T18:14:30-03:00`
- relatório gravado: `2026-08-09 19:06` (-03) — **~52 min depois**

## 3. INPUTS impressos (a medição lista seus inputs)

- **Amostra PINADA:** planos M = **155..168** (14 planos;
  `PLANS = list(range(155, 169))`, `e0-serial-fraction.py:51`).
- **Constantes de gap:** `GAP_MACHINE_S=120` · `GAP_HUMAN_MAX_S=3600`
  (impressas no relatório, linha 50).
  - máquina = união de `[ts_i, ts_i+120s]` dos eventos de audit;
  - humano = gaps em `(120s, 3600s]`;
  - morto = gaps `> 3600s` (CI/quota/sono).
- **Janela por plano:** `git log --format='%ct %s'`, subject mencionando
  `PLAN-<N>`.
- **Evidência:** 11 arquivos de audit log (snapshot imutável em tmpdir),
  **cada um com sha256 impresso** no relatório — 11/11 passam o gate
  `check-audit-hmac-null.py`.
- **Corte conservador pré-registrado:** máquina conta **100% serial** em
  todos os planos (o grafo de dependência é irrecuperável do log v2) —
  viés **para cima** de S, isto é, **contra** financiar E1/E2.

### Disclosure honesta que o relatório carrega

`verify_chain()` reporta `status=tamper` em **11/11** arquivos — é
DISCLOSURE, **não** gate: (a) HMAC-483, falso mismatch pós-rotação,
reproduzido na S300 inclusive em arquivos saudáveis com >13k entradas
verificadas; (b) decisão S298 — o trust model da cadeia HMAC como
oráculo foi descartado (escritor e verificador correm no mesmo UID:
tamper-*evident* para auditoria externa, não autorização).

## 4. Resultado

Agregado sobre 14/14 planos, união de 3 intervalos disjuntos (sem dupla
contagem — pair-rail S300 r3 P1-4), total **723,0 h** de wall-clock:

| componente | horas | fração |
|---|---|---|
| máquina | 155,4 | ~21% |
| humano | 137,9 | ~19% |
| **tempo-morto** | **429,6** | **~59%** |

- **S (conservador, máquina 100% serial) = 1,000** ← a figura que decide.
- **Figura "otimista" = 0,785** — a fração não-máquina do wall-clock.
  **Atenção:** o próprio relatório a marca como *estatística
  DESCRITIVA que não decide nada*, porque o pré-registro não define
  regra sobre ela; uma regra sobre esse piso seria post-hoc e
  não-assinada (removida no pair-rail S300 r3 P1-5; emenda só via novo
  pré-registro versionado). Ela é o **piso** de S, não um segundo
  veredito.

Em qualquer leitura, **0,785 ≤ S ≤ 1,000** — o resultado é o mesmo lado
da linha nos dois extremos.

## 5. Regra pré-registrada aplicada

Regra assinada no W5 (`PLAN-169`, §W5; `e0-serial-fraction.py:8-12`):

| faixa | decisão pré-definida |
|---|---|
| **S ≥ 0,40** | **E1/E2 NÃO financiados** |
| 0,20 < S < 0,40 | E1 só como piloto (N/2), E2 não financiado |
| S ≤ 0,20 | E1/E2 liberados |

Aplicação: **S = 1,000 ≥ 0,40 ⇒ E1 e E2 são DESFINANCIADOS.** Nenhuma
faixa mensurável ficou para juízo post-hoc; o veredito é mecânico.

### Consequência registrada na S300

- **E1** (audit fan-out read-only vs solo) e **E2** (batch de itens de
  baixo acoplamento): **desfinanciados**.
- Um **PLAN-170** futuro carrega **apenas E3** (paralelismo só na
  verificação) **+ E4** (fidelidade de handoff) — ambos são
  independentes do gate E0 (E4 "roda SEMPRE", E3 é a aposta da
  literatura sobre *review*, não sobre autoria).
- Interpretação registrada no `PLAN-172` §0: teto de Amdahl ≈ 1,27×
  para paralelizar **autoria**; o morto por unidade (~30,7 h) excede o
  trabalho ativo da unidade seguinte (~21 h). *"Não é um problema de
  arquitetura de agentes — é um problema de calendário."*

## 6. O que este documento NÃO fecha

Fecha a **metade E0** do AC-6 (E0 executado, S medido com inputs
impressos, decisão registrada, evidência dentro do repo). A outra
metade do AC-6 — **criar o PLAN-170** com orçamento próprio declarado e
gatilho nomeado (pós-corte v1.4.0-rc.1) — continua **aberta**
(`PLAN-179/LEDGER.md:68-69`).
