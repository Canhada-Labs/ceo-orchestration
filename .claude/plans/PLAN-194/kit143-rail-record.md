# rail-record — kit da v1.4.3-rc.1 (PLAN-194 W7): K-a (texto do plano e do backlog) e K-b (derivador e saídas), três rodadas

Rail-Subject: os commits do kit sobre `9cfeafebcba4` — `97e4951a626c`, `2725143cfd4c`, `849f448695ed`, `f5b7a983d4cc`, `cb75587c6093`, `4381ba7373e6`, `cdb067d41817`, `27c85afe366b`, `20ec3d4eef0c`, `25d26e72542b`, `b978c703079b` (ponta `b978c703079b`)
Rail-Subject-sha256: `.claude/plans/PLAN-194-FOLLOWUP-v1-4-4-backlog.md` fd333ed7d57f3bde086ef6a9a7cbf2cd68a2d796b20d5d53002fa8ca88da8b4d; `.claude/plans/PLAN-194-maintenance-train-v1-4-3.md` 541590469ea0d7522cb4a8a0d33f31c2906fc0a34a06fc74fdae1fbe113d305e; `.claude/plans/PLAN-194/OWNER-RC1-CUT.sh` 752012f90ade8dd564a41de0c9fcdc3d13c11257887e2c49c66ba14d30230b1a; `.claude/plans/PLAN-194/derive-ga-kit-143.py` 2dc3ef71dceb49fe4a1e52b493062dfd4b5d6e367ea2a68c00a5882072e661bb; `.claude/plans/PLAN-194/derive-kit-143.py` caa78427a72867403c3d01d4d4a23c1b86e218dd858d01f91436d75bd0f15902; `.claude/plans/PLAN-194/gen-envelope-rc1.py` 09fd7d386dd4643257b54b1d03ae5f8430785c1eba21058006db939708f99bfb; `.claude/plans/PLAN-194/repass-rc1/.gitignore` 37c4f799869cb0042cdbefa8f35739e2871087b23fe779e8d829ce854cfb8cd0; `.claude/plans/PLAN-194/repass-rc1/CONDITIONS-rc1.md` eebf7191267a85535be53dc9872223a4e7fba89a44778bccac46a46d194a8c51; `.claude/plans/PLAN-194/repass-rc1/README-rc1.md` a7f08cd4272619869a019904065cb30bbed08b50dba0548943d29f729f424441; `.claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py` 1bca3eddabb9105e267dd3491853fe3febca9fef1c799a6ea73929d969208c33; `.claude/plans/PLAN-194/repass-rc1/run-rc1-repass.sh` 7ae00c3ac3f8778d1c603256d6fb45788b80e60e67b8580b938f89116f1665e7; `.claude/plans/PLAN-194/test-rc1-kit.sh` e40c3241cdca10936ff320d570855d7feed591cd6d8f10fd8947c44654173c28
Rail-Reviewer: codex-cli 0.160.0 (`exec --sandbox read-only --skip-git-repo-check`, prompt pela entrada padrão, modelo gpt-6-astra, esforço xhigh, memories e chronicle desligados; config_sha `cdb20042047215ce` no início e no fim das rodadas 1 e 2 e `56eabc9c3db94399` no início e no fim da rodada 3) e lanes Claude (Opus 5.5, Workflow só-leitura) na MESMA rodada: uma lane de texto no K-a; texto, mecânica e derivador no K-b
Rail-Date: 2026-10-17 (K-a r1: preflight do Codex às 13:39:32Z; K-b r1: 14:20:22Z; K-b r2: 16:04:45Z; K-b r3: 21:04:40Z)
Rail-Reviewer-Verdict: K-a r1 — Codex GO, lane texto GO (2 P3); K-b r1 — Codex NO-GO (1 afirmação falsa P2, 1 bug P2), lanes texto e derivador GO-WITH-CONDITIONS, mecânica GO (24 P2/P3); K-b r2 — Codex NO-GO (2 afirmações falsas), as três lanes Claude NO-GO pelas mesmas duas; K-b r3 (FINAL) — Codex NO-GO (2 afirmações falsas P2, num comentário do derivador e no `GA_CARRY`; 1 bug P2; 1 P3), lane texto NO-GO (1 afirmação falsa P2, a frase de forma do §4 e da condição 10; 5 P3), lanes mecânica e derivador GO-WITH-CONDITIONS (1 lacuna P2; 10 P3)
Rail-Verdict: DECLARED-P3
Rail-Findings: P0=0 em todas as rodadas; a classe «o que chega ao adopter» saiu por REMOÇÃO (NO-GO nas rodadas 1, 2 e 3); as afirmações falsas e o P2 da rodada 3 curados sem rodada nova (a frase de forma por REMOÇÃO da cláusula de identidade; as frases universais do derivador trocadas por contagem exata); os P3 sem cura declarados pela forma no item 27 do backlog da 1.4.4

Informativos:

- Regra de parada pré-registrada ANTES da rodada 1: sha256 `9f4f1204…` (texto abaixo). Lane Claude: `claude-lanes.js` sha256 `3b738398…`; lane Codex: `run-codex.sh` sha256 `7209bcd7…`.
- Saídas verbatim, prompts e logs de cada lane: fora do repositório, na pasta de ferramentas do Owner da S365 (`kit143/rail/ka-r1/`, `kb-r1/`, `kb-r2/`, `kb-r3/`), com estes sha256:
  K-a r1 — `codex-prompt.md` b23fdb48…, `codex-last.md` 7d76c1dc…, `codex.log` ce61e63a…, `claude-lane.json` 1d52db5b…, `claude-lanes-workflow.js` bef59c97…;
  K-b r1 — `codex-prompt.md` 5b7f5f18…, `codex-last.md` 872fc2f2…, `codex.log` 7fcc8c21…, `claude-lanes.json` a875a8c9…, `claude-findings.json` 8716f1bd…, `claude-lanes-workflow.js` 4f7d0df2…;
  K-b r2 — `codex-prompt.md` 4548b368…, `codex-last.md` e5896088…, `codex.log` 7718bd7a…, `claude-lanes.json` 455d1c58…, `claude-lanes-workflow.js` c4558231…;
  K-b r3 — `codex-prompt.md` a6b7c95a…, `codex-last.md` 9e49f6ff…, `codex.log` 9c627129…, `claude-lanes.json` 18635ada…, `claude-lanes-workflow.js` a0b4a060….
- Substrato (registro, não achado): a 1.ª tentativa da lane Codex do K-a r1 passou o prompt longo como ARGUMENTO e morreu na hora com rc 137 e log vazio; com o prompt pela entrada padrão (`codex exec … - < prompt`), rodou. O `run-codex.sh` usa a entrada padrão desde então; o runner do re-pass do kit já a usava. O `config.toml` do Codex mudou em 2026-10-16 às 07:02 BRT (sha `cdb20042…`; a base da rodada do RM era `c9249e82…`) e de novo entre a rodada 2 (16:04Z) e a rodada 3 (21:04Z) de 2026-10-17 (sha `56eabc9c…`). Nas duas vezes, modelo, esforço, memories e chronicle ficaram iguais, e dentro de cada rodada o sha não mudou. A origem das mudanças foi perguntada ao Owner.

## Regra de parada (pré-registrada em 2026-10-17, antes da rodada 1)

Sujeito de cada rodada: os commits do kit sobre `9cfeafebcba4` (K-a texto + K-b derivador e saídas),
identificados pelo SHA do commit-ponta E pelo sha256 de cada arquivo tocado (o registro do rail landa
DEPOIS, num commit só de texto que cita esses hashes — lacuna G1: o registro nunca é parte do sujeito).

Lanes por rodada (as DUAS famílias na MESMA rodada; CLAUDE.md §4, S361):
- Codex: `codex exec --sandbox read-only --skip-git-repo-check`, a partir da worktree do sujeito,
  `</dev/null`, `--output-last-message`; pré-voo registra `codex --version`, sha do `~/.codex/config.toml`,
  modelo, esforço e `memories`; se o sha mudar entre o início e o fim, a rodada da lane NÃO conta.
- Claude (Workflow, 3 lanes, só leitura): L-texto (condições, README, GEN_RECORD, CUT_MSG contra o
  CHANGELOG [1.4.3], o texto da tag e o código); L-mecânica (corte, sonda, harness, controles vermelhos,
  heredocs); L-derivador (as saídas saem do derivador byte a byte, `--check`, cascata no kit do GA).

Critério de veredito (regra «rodada final com anexo», Owner 2026-09-10; CLAUDE.md §4):
- NO-GO só por P0 ou por afirmação FALSA reproduzida (condição, README, envelope, mensagem de commit).
- P1 que não seja afirmação falsa: curado se couber sem reabrir arquitetura; senão vai DECLARADO pela
  forma (condição/seção D), nunca enumerando sítios.
- P2/P3: curados sem nova rodada ou declarados.

Parada:
- Rodada 1: completa (Codex + 3 lanes Claude).
- Rodada 2: só se a r1 tiver P0, afirmação falsa ou P1 curado em código; sujeito = o delta da cura.
- Rodada 3 = FINAL. Uma frase com 2 NO-GOs em rodadas diferentes sai por REMOÇÃO, sem nova rodada.
  P0 restante na r3 ⇒ PARAR e levar ao Owner (não há rodada 4).
- Teto indicativo de custo: 3 M tokens de subagentes no rail inteiro.
- Achado só em material não commitado não bloqueia; material curado no vivo é rebaseado/commitado antes
  da rodada seguinte (a sombra revista tem de ser o que landa).

## K-a, rodada 1 (sujeito `9cfeafeb..97e4951a`: plano W7/D-4, backlog da 1.4.4, `CLASS_PENDING` e `CONTENT_PENDING` do kit do GA)

Lane Codex — última mensagem, verbatim:

```text
Não reproduzi achados P0/P1/P2/P3 no diff `9cfeafebcba4..97e4951a626c`.

- SHAs citados existentes e ancestrais do HEAD; referências, versões nas tags e ausência de diff em `SPEC/` conferem.
- Nenhuma contradição encontrada com o CHANGELOG [1.4.3] ou as decisões registradas do Owner.
- `python3 -I .claude/plans/PLAN-194/derive-ga-kit-143.py --check-cures`: **exit 0**.
- Recusa K1: **exit 2**, preservando o prefixo e todos os predicados do K1a. Não encontrei outro consumidor incompatível.
- As quatro saídas curadas do GA permanecem idênticas antes/depois deste diff. As novas pendências correspondem ao código atual.
- L1 está landada; a sonda em memória preservou o drift do Codex junto de `CC_LEDGER_UNREADABLE`.

Li o `test-ga-kit.sh`; não executei o harness completo, que cria arquivos. Medições externas foram confrontadas com registros locais, sem nova consulta ao GitHub ou à máquina do Owner. Nenhum arquivo editado.

VERDICT: GO
```

Lane texto (GO): KA-R1-01 (P3) «o bump da rc da 1.4.4 é o próximo que escreve o sítio» lido ao pé da letra em
2026-10-17; KA-R1-02 (P3) o pin do `tla2tools` mudou três vezes no PR #4, não só em `f465bb50`. Os dois curados
em `2725143c`, sem nova rodada (P3).

## K-b, rodada 1 (sujeito `2725143c..f5b7a983`: o derivador e as 8 saídas)

Lane Codex — última mensagem, verbatim (caminhos absolutos encurtados para `<wt>`):

```text
1. **P2 — afirmação falsa:** [README-rc1.md:68](<wt>/.claude/plans/PLAN-194/repass-rc1/README-rc1.md:68), originada em [derive-kit-143.py:1879](<wt>/.claude/plans/PLAN-194/derive-kit-143.py:1879), justifica excluir `**/tests/**` dizendo que não são entregues. Porém, `.claude/scripts/optimizer/tests/test_codex_phase_gate.py` muda nesta faixa e é entregue pelo upgrade: passa pelo filtro de exclusão e chega à cópia em [upgrade.sh:1818](<wt>/scripts/upgrade.sh:1818).

   Reprodução somente leitura:

   ~~~bash
   bash -c '
   . scripts/_framework_manifest_set.sh
   f=.claude/scripts/optimizer/tests/test_codex_phase_gate.py
   git diff --name-only v1.4.2 HEAD -- "$f"
   _framework_path_excluded "$f"
   printf "exclusion_rc=%s\n" "$?"
   FMS_ROOT=. _framework_manifest_files | rg -Fx "$f"
   '
   ~~~

   Resultado: o caminho aparece no diff e no manifesto; `exclusion_rc=1` significa **não excluído**. Também executei o percurso real `_per_file_classified_update` com a escrita substituída por impressão: ele seleciona esse arquivo para cópia. Corrigir a justificativa no derivador, explicitando essa entrega e o motivo para manter esses testes fora da revisão.

2. **P2 — bug:** [OWNER-RC1-CUT.sh:261](<wt>/.claude/plans/PLAN-194/OWNER-RC1-CUT.sh:261) consulta apenas os últimos **30 runs do repositório**, filtrando o SHA depois. Um run agendado vermelho mais antigo desaparece da conferência. O preflight também tem janela finita, de 40 runs. Portanto, a retomada pode aceitar CI verde sem considerar um vermelho do mesmo candidato.

   Reprodução sem rede nem execução do corte inteiro; extrai somente `wait_ci_green` e aplica seus filtros reais sobre respostas sintéticas:

   ~~~bash
   python3 -I -c '
   import json, re, shlex, subprocess
   from pathlib import Path
   src = Path(".claude/plans/PLAN-194/OWNER-RC1-CUT.sh").read_text()
   fn = re.search(r"(?ms)^wait_ci_green\(\) \{\n.*?^\}", src).group()
   sha = "a" * 40
   green = dict(headSha=sha, status="completed", conclusion="success",
                event="push", headBranch="main", databaseId=1)
   red = dict(green, conclusion="failure", event="schedule", databaseId=41)
   data = "ROWS=" + shlex.quote(json.dumps([green]*40+[red])) + "\n"
   data += "VALIDATE=" + shlex.quote(json.dumps([green])) + "\n"
   data += "JOBS=" + shlex.quote(json.dumps({"jobs":[green]})) + "\n"
   stub = """
   set -eu
   CI_WAIT_MAX_MIN=1
   sleep() { :; }
   die() { echo "$*"; exit 1; }
   gh() {
     case "$*" in
       *"run view"*) echo "$JOBS" ;;
       *"--workflow validate.yml"*) echo "$VALIDATE" ;;
       *) echo "$ROWS" | jq ".[0:30]" ;;
     esac | jq -rc "${!#}"
   }
   """
   subprocess.run(["bash", "-c", data+stub+fn+"\nwait_ci_green "+sha],
                  check=True)
   '
   ~~~

   Resultado: `runs=30 pendentes=0 vermelhos=0`, Validate verde e **rc 0**, apesar do run agendado vermelho. Corrigir com consulta por SHA e paginação, preservando todos os eventos relevantes.

Passaram: derivação das oito saídas, `--check-cures` do GA, sintaxe Python/Bash e as 11 verificações da sonda executáveis sem escrita. O controle da condição 67 passou no HEAD e reprovou na v1.4.2. Não executei o corte, o harness nem sondas que criam arquivos; a árvore permanece limpa.

O NO-GO decorre da afirmação falsa reproduzida no achado 1; não identifiquei P0.

VERDICT: NO-GO
```

Lanes Claude — resumo (o texto inteiro está em `claude-lanes.json` e `claude-findings.json`, sha256 acima):

- Texto (GO-WITH-CONDITIONS): LT-01 (P2) a mesma classe do achado 1 do Codex: o §4 deixou de dizer que o
  `upgrade.sh` entrega `.claude/scripts/local/**` e `.claude/scripts/data/**`; LT-02..07 (P3) texto.
- Mecânica (GO): LM-01..08 (P3).
- Derivador (GO-WITH-CONDITIONS): LD-01..09 (P3); LD-08, as classes G2 e G3 do kit da rc fora do
  `CLASS_PENDING` do kit do GA.

Disposição: o achado 1 do Codex e o LT-01 foram curados pelo TEXTO, com a entrega medida numa instalação
descartável seguida do `upgrade.sh` (C18 na sonda). O achado 2 foi curado no código: o `wait_ci_green`
passou a consultar os runs PELO COMMIT. LD-08 foi curado em `cb75587c`. Os P3 foram curados em `4381ba73`,
exceto os da lista D do construtor (LM-01, o resto do LM-04 e LM-06), que vão para o backlog da 1.4.4.

## K-b, rodada 2 (sujeito `f5b7a983..4381ba73`, o delta das curas)

Lane Codex — última mensagem, verbatim (caminhos absolutos encurtados para `<wt>`):

```text
REJECT. As duas curas ainda estão incompletas: reproduzi duas afirmações falsas. Não encontrei P0.

1. **P1 · afirmação falsa — o limite de 200 ainda esconde runs vermelhos ou pendentes.**  
   [README-rc1.md:179](<wt>/.claude/plans/PLAN-194/repass-rc1/README-rc1.md:179) promete recusar um vermelho “por mais antigo que seja”, mas [OWNER-RC1-CUT.sh:262](<wt>/.claude/plans/PLAN-194/OWNER-RC1-CUT.sh:262) limita a consulta a 200 resultados. Não há filtro de evento: push, schedule e workflow_dispatch podem aparecer, mas somente dentro desse limite.

   Executei a função isolada, com respostas locais e sem executar o corte:

   | Fixture do mesmo SHA | Resultado |
   |---|---|
   | 30 verdes + vermelho agendado | Recusa, código 1 |
   | 200 verdes + vermelho agendado | **Aceita, código 0** |
   | 200 verdes + pendente agendado | **Aceita, código 0** |

   O stub preserva esse truncamento em [test-rc1-kit.sh:2294](<wt>/.claude/plans/PLAN-194/test-rc1-kit.sh:2294); quem mascara a lacuna é a fixture V4, que contém somente 31 runs, na linha 2351.

   Reprodução curta, aplicando a expressão **extraída do corte** à janela:
   ~~~bash
   python3 -I -c '
   import json,pathlib,re,subprocess
   s=pathlib.Path(".claude/plans/PLAN-194/OWNER-RC1-CUT.sh").read_text()
   s=s[s.index("wait_ci_green() {"):]
   limit=int(re.search(r"--limit (\d+)",s)[1])
   q=re.search(r"--jq \"(.*?)\" 2>/dev/null",s,re.S)[1]
   q=q.replace("\\\n","").replace("\\\"",chr(34)).replace("$sha","C")
   g=dict(headSha="C",status="completed",conclusion="success")
   for status,conclusion in [("completed","failure"),("in_progress",None)]:
       rows=[g]*200+[dict(g,status=status,conclusion=conclusion,event="schedule")]
       r=subprocess.run(["jq","-c",f".[:{limit}] | "+q],
           input=json.dumps(rows),text=True,capture_output=True,check=True)
       print(status,conclusion,"=>",r.stdout.strip())
   '
   ~~~
   Ambos retornam `{"n":200,"p":0,"b":0}`. A cura precisa demonstrar completude ou recusar uma consulta truncada; aumentar novamente o teto não sustenta a promessa.

2. **P2 · afirmação falsa — o upgrade não entrega todos os arquivos que §4 lhe atribui.**  
   [README-rc1.md:80](<wt>/.claude/plans/PLAN-194/repass-rc1/README-rc1.md:80), [README-rc1.md:85](<wt>/.claude/plans/PLAN-194/repass-rc1/README-rc1.md:85) e [CONDITIONS-rc1.md:126](<wt>/.claude/plans/PLAN-194/repass-rc1/CONDITIONS-rc1.md:126) atribuem ao upgrade os esquemas, README e exemplos de planos, além do README dos ADRs.

   O instalador entrega esses arquivos. O upgrade só tem entrega/atualização de `PLAN-SCHEMA.md` e `DEBATE-SCHEMA.md`, em [upgrade.sh:4476](<wt>/scripts/upgrade.sh:4476). Ele não entrega `plans/README.md`, `AUDIT-LOG-SCHEMA.md`, `plans/examples/` ou `adr/README.md`. Na C18 esses arquivos já existem porque **o instalador acabou de copiá-los**; sua permanência é contada como entrega pelo upgrade.

   Reprodução por leitura das rotas:
   ~~~bash
   rg -n 'install_one "\.claude/(plans|adr)/' scripts/install.sh
   rg -n '(_refresh_schema_doc "\.claude/plans/|plans/(README|AUDIT-LOG-SCHEMA|examples)|adr/README)' scripts/upgrade.sh
   ~~~
   A segunda busca mostra apenas os dois esquemas. A descrição dos testes de skills e dos testes nos subdiretórios de `.claude/scripts/` está correta; as linhas de planos e ADRs ainda precisam separar entrega de preservação.

3. **P2 · lacuna — C18 não verifica as exclusividades nem a entrega completa da tabela.**  
   Em [probe-conditions-rc1.py:865](<wt>/.claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py:865), o primeiro arquivo idêntico torna a classe inteira verdadeira. Assim, a comparação da linha 915 aceita tanto a ausência dos testes de scripts quanto a entrega indevida de planos numerados e ADRs. Reproduzi ambos em memória; a C18 respondeu OK.

   Este comando reproduz a igualdade com `OUT_DELIVERY` para um alvo virtual contendo **todos os planos e ADRs, mas nenhum teste de scripts**:
   ~~~bash
   python3 -I -c '
   import pathlib,runpy
   from unittest.mock import patch
   m=runpy.run_path(".claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py")
   t=m["Tree"](".","v1.4.2","HEAD")
   original=pathlib.Path.is_file
   prefixes=(".claude/skills/",".claude/plans/",".claude/adr/")
   def measure():
       with patch.object(pathlib.Path,"is_file",
               lambda p: str(p).startswith(prefixes) and original(p)):
           return m["_out_delivered"](t,pathlib.Path("."))
   before=measure()
   prefixes+=(".claude/scripts/local/",".claude/scripts/data/")
   after=measure()
   print({s:(before[s],after[s]) for s in before} == m["OUT_DELIVERY"])
   '
   ~~~
   Resultado: `True`. É necessário comparar conjuntos de arquivos esperados/proibidos e distinguir arquivos preservados dos efetivamente entregues.

4. **P2 · lacuna — a guarda dos `echo`s depende da indentação exata.**  
   [derive-kit-143.py:823](<wt>/.claude/plans/PLAN-194/derive-kit-143.py:823) só inspeciona linhas que casam com quatro espaços, um dígito e `) echo`. Uma linha equivalente com seis espaços escapa; `derive_all()` aceita `$HOME` no texto gerado.

   Reprodução, inteiramente em memória:
   ~~~bash
   python3 -I -c '
   import runpy
   m=runpy.run_path(".claude/plans/PLAN-194/derive-kit-143.py")
   g=m["derive_all"].__globals__
   old="    4) echo "+chr(34)
   new="      4) echo "+chr(34)+"$HOME "
   g["RUNNER_PARTS"]=g["RUNNER_PARTS"].replace(old,new,1)
   out=g["derive_all"]()
   print(next(x for x in out["runner"].splitlines()
       if "4) echo" in x and "$HOME" in x))
   '
   ~~~
   As guardas do veredito, banner e CONTEXT rejeitaram crase, `$(`, barra invertida e variável não permitida nos controles que executei. A lacuna está na cobertura dos `echo`s: linhas não reconhecidas precisam ser recusadas ou analisadas também.

5. **P3 · lacuna — C2 verifica apenas o marcador da condição 15.**  
   [probe-conditions-rc1.py:399](<wt>/.claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py:399) exige somente `15. **`. Substituir toda a condição por uma declaração incompatível continua produzindo `GA: 13 a 15`.

   Reprodução:
   ~~~bash
   python3 -I -c '
   import re,runpy
   m=runpy.run_path(".claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py")
   t=m["Tree"](".","v1.4.2","HEAD")
   original=t.show
   def show(rev,path):
       text=original(rev,path)
       return re.sub(r"(?ms)^15\. \*\*.*",
           "15. **TODOS OS ACHADOS ESTAO CURADOS.**\n",text
       ) if path==m["GA_CONDITIONS"] else text
   t.show=show
   print(m["c2_carried"](t))
   '
   ~~~
   O texto atual da condição 15 está correto; a nova verificação não protege seu conteúdo.

Os dois checks autorizados e `git diff --check` passaram. C0-npm rejeitou o `if:` comentado; C17 rejeitou a marca provisória. Não encontrei outra divergência nas alterações de §1, CONTEXT, mensagem do commit ou nas duas pendências declaradas para o GA. O NO-GO decorre das afirmações falsas dos achados 1 e 2.

VERDICT: NO-GO
```

Lanes Claude — resumo:

- Texto (NO-GO): LT2-01/02 (P2, afirmação falsa) a condição 10 e as linhas de planos e ADRs do §4 atribuem
  ao `upgrade.sh` o que só a instalação nova entrega, reproduzido por código e por comportamento (fonte com
  marcador; arquivos apagados do alvo); LT2-03 (P2) a C18 mede o upgrade sobre o alvo que a instalação
  acabou de encher; LT2-04/05 (P3) texto.
- Derivador (NO-GO): LDR2-01 (P2) a mesma afirmação falsa; LDR2-02 (P2) a C18 vácua; LDR2-03 (P2) o
  `CLASS_PENDING` do kit do GA sem as classes curadas nesta rodada (2.ª ocorrência do LD-08); LDR2-04/05
  (P3); LDR2-06 (P3, afirmação falsa) «por mais antigo que seja» com `--limit 200`.
- Mecânica (NO-GO): LM2-01 (P2, afirmação falsa) a mesma frase do teto de 200; LM2-02 (P2) o mesmo do
  LDR2-03; LM2-03..07 (P3).

Disposição: a classe «o que chega ao adopter» (o §4, a condição 10 e a C18) levou NO-GO na rodada 1 e na
rodada 2, então saiu por REMOÇÃO, sem frase nova de resultado: fica a frase de forma «fora do re-pass não
quer dizer não entregue; o que chega a um adopter é o que o `install.sh` e o `upgrade.sh` do candidato
entregam, e este kit não o afirma classe a classe», e a C18 saiu da sonda. A frase do teto (1.º NO-GO dela)
foi curada no código: as consultas do `wait_ci_green` recusam pelo nome a consulta que volta CHEIA, com
controles vermelhos, e o §10 diz isso. LDR2-03/LM2-02, a 2.ª ocorrência, teve cura ESTRUTURAL: o derivador
da rc exporta `GA_CARRY` e `GA_NA`, e o derivador do GA rende o `CLASS_PENDING` a partir deles, sem lista
mantida à mão. A guarda de heredoc e echo, com 3 ocorrências de cobertura parcial, também teve cura
estrutural: passou a rodar sobre o texto FINAL e a varrer todo heredoc sem aspas e todo echo de texto, com
allowlist dos heredocs de dado. Os P3 foram curados. Sujeito curado: `cdb067d4` (a remoção e o teto), `27c85afe` (a guarda estrutural, os censos, o gêmeo V3s, o `GA_CARRY` e os P3) e `20ec3d4e` (o `CLASS_PENDING` do kit do GA rendido do `GA_CARRY`).

## K-b, rodada 3 — FINAL (sujeito `4381ba73..20ec3d4e`)

Lane Codex — última mensagem, verbatim (caminhos absolutos encurtados para `<wt>`):

```text
Encontrei duas afirmações falsas reproduzidas, suficientes para NO-GO pela regra desta rodada. Nenhum P0 identificado.

1. **P2 — afirmação falsa: a guarda não cobre todo heredoc/echo.**  
   A cobertura universal declarada em [derive-kit-143.py:938](<wt>/.claude/plans/PLAN-194/derive-kit-143.py:938) é refutada pela implementação: a regex de [linha 985](<wt>/.claude/plans/PLAN-194/derive-kit-143.py:985) ignora delimitadores numéricos, e a de [linha 1042](<wt>/.claude/plans/PLAN-194/derive-kit-143.py:1042) ignora `echo -n`. Injetei, em memória, `cat <<123` contendo `$(printf X)` e `echo -n "$(printf X)"`. **Ambos atravessaram `derive_all()` inteiro e passaram no `bash -n`.** A afirmação também está exportada no `GA_CARRY`.

2. **P2 — afirmação falsa: o censo não reconhece atribuição em “QUALQUER forma”.**  
   Em [probe-conditions-rc1.py:410](<wt>/.claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py:410), `printf -v "CODEX_LAUNCHER" "%s" "/tmp/TEST-ONLY-other"` escapa da regex. Inserido depois do oráculo e antes da criação do shim, **`c13_route1()` continua aprovando**, embora essa atribuição altere o executável usado pelo shim. Também reproduzi com `CODEX_LAUNCHER[0]=...`.

3. **P2 — bug: `class_pending()` aceita entradas que o contrato do exportador rejeita.**  
   [derive-ga-kit-143.py:625](<wt>/.claude/plans/PLAN-194/derive-ga-kit-143.py:625) aceita IDs com espaços/maiúsculas e textos com newline. O próprio [check_ga_carry():345](<wt>/.claude/plans/PLAN-194/derive-kit-143.py:345) rejeita essas entradas. Reproduzido também com `check_applied=True`; o consumidor não chama essa validação.

4. **P3 — lacuna: a cura LT-03 do comentário do shim ficou fora da transferência ao GA.**  
   A correção está em [derive-kit-143.py:1065](<wt>/.claude/plans/PLAN-194/derive-kit-143.py:1065). `derive_cured()` ainda conserva o comentário antigo do [runner GA:301](<wt>/.claude/plans/PLAN-193/repass-ga/run-ga-repass.sh:301). Não há entrada correspondente em `GA_CARRY`/`GA_NA`; o comentário listado em [CLASS_PENDING_GA:135](<wt>/.claude/plans/PLAN-194/derive-ga-kit-143.py:135) trata do seam `CODEX_BIN`, outra correção.

Comando único para reproduzir os quatro achados, sem escrever arquivos nem executar o corte:

~~~bash
python3 -I -B -c '
from pathlib import Path
from types import SimpleNamespace
import runpy, subprocess

p = Path(".claude/plans/PLAN-194")
r = runpy.run_path(str(p / "derive-kit-143.py"))
ns = r["derive_all"].__globals__
banner = ns["CUT_BANNER"]
for extra in ("cat <<123\n$(printf X)\n123\n",
              "echo -n \"$(printf X)\"\n"):
    ns["CUT_BANNER"] = banner + extra
    out = r["derive_all"]()
    subprocess.run(["bash", "-n"], input=out["cut"],
                   text=True, check=True)
    print("1 ACEITO:", repr(extra))
ns["CUT_BANNER"] = banner

probe = runpy.run_path(str(p / "repass-rc1/probe-conditions-rc1.py"))
runner = (p / "repass-rc1/run-rc1-repass.sh").read_text()
anchor = "  SHIM_DIR=\"$OUT/.codex-shim\"\n"
injected = "printf -v \"CODEX_LAUNCHER\" \"%s\" \"/tmp/TEST-ONLY-other\"\n"
mutant = runner.replace(anchor, injected + anchor, 1)
print("2:", probe["c13_route1"](
    SimpleNamespace(head="HEAD", show=lambda *_: mutant)))

ga = runpy.run_path(str(p / "derive-ga-kit-143.py"))
out, rc = ga["derive_cured"]()
original = rc.GA_CARRY
for entry in (("ID INVALIDO", "corte", "texto"),
              ("id-valido", "corte", "linha 1\nlinha 2")):
    rc.GA_CARRY = original + (entry,)
    print("3 consumidor ACEITA:",
          repr(ga["class_pending"](rc, check_applied=True)[-1]))
    try:
        rc.check_ga_carry()
    except SystemExit:
        print("3 exportador RECUSA")
rc.GA_CARRY = original

print("4 shim GA:", [x.strip() for x in out["runner"].splitlines()
                     if "# shim do runner" in x])
print("4 carry:", [x for x in rc.GA_CARRY + rc.GA_NA
                   if "LT-03" in str(x) or "shim" in str(x)])
print("4 pendencia especifica:", ga["CLASS_PENDING_GA"])
'
~~~

Os dois checks autorizados passaram. Confirmei a remoção das declarações de entrega classe a classe. Não reproduzi furo do teto: o `wait_ci_green` isolado recusou vermelho antigo, pendentes e consultas cheias nos casos exercitados com JSON bruto e `jq` real. Todos os heredocs de dados da allowlist recusaram texto livre. Não identifiquei regressão adicional fora dos achados acima.

VERDICT: NO-GO
```

Lanes Claude — resumo (o texto inteiro está em `claude-lanes.json`, sha256 acima). As três leram o sujeito
`20ec3d4e`; a cura do Codex (`25d26e72`) veio depois.

- Texto (NO-GO): LT3-01 (P2, afirmação falsa) a frase de forma «o que chega a um adopter é o que o
  `install.sh` e o `upgrade.sh` do candidato entregam» é falsa, porque há uma terceira rota, a instalação
  só pelo plugin (o próprio `CHANGELOG.md` [1.4.3] fala dela); LT3-02 a LT3-06 (P3) textos do
  `GA_CARRY`, do comentário do derivador do GA e da ordem das recusas do `validate.yml`.
- Mecânica (GO-WITH-CONDITIONS): LM3-01 e LM3-04 (P3), formas que escapavam da guarda e do censo, as
  mesmas do Codex; LM3-02 (P3) ramos novos da guarda sem controle vermelho; LM3-03 (P3) a chave `cron`
  entre aspas ou com espaço fora do censo; LM3-05 (P3) contadores do `wait_ci_green` sem validação de
  inteiro.
- Derivador (GO-WITH-CONDITIONS): LDR3-01 (P2, lacuna) a metade SIZE da classe G3 sumiu do
  `CLASS_PENDING` quando ele passou a sair do `GA_CARRY`; LDR3-02 a LDR3-06 (P3) entradas faltando no
  `GA_CARRY`/`GA_NA`, a guarda, os radicais com caixa, controles e o censo do `CODEX_LAUNCHER`.

Disposição, sem rodada 4, pela regra de parada:

- A classe «o que chega ao adopter» levou o 3.º NO-GO (LT3-01). A cláusula de identidade saiu por
  REMOÇÃO, sem frase nova de resultado: fica «Fora do re-pass não quer dizer não entregue; este kit não
  afirma, classe a classe, o que chega a um adopter.» Os radicais proibidos casam sem caixa.
- As duas frases universais do Codex («todo heredoc e todo echo»; a atribuição «em QUALQUER forma») saíram.
  No lugar, a cobertura é medida por contagem exata, não por uma lista de formas. Em cada linha fora de
  comentário e de corpo de heredoc, o número de `<<` (fora de `<<<`) tem de ser igual ao de aberturas
  reconhecidas, e cada linha com a palavra echo é conferida até o fim. Toda linha de código do runner que
  menciona `CODEX_LAUNCHER` tem de ser uma das cinco esperadas. Os reprodutores do Codex são recusados,
  e também `<<\EOF`, `builtin echo` e `export CODEX_LAUNCHER`. Controles G16m, G17m e P34.
- O bug P2: `class_pending()` chama o `check_ga_carry()` do exportador, um contrato só.
- O P2 do derivador e os P3 de `GA_CARRY`/`GA_NA`, textos, ordem das recusas, inteiros e censo dos
  crons: curados.
- Os P3 de controles e de cobertura restantes: declarados (abaixo).

Sujeito curado: `25d26e72` (as curas da lane Codex) e `b978c703` (as das lanes Claude).

## Ensaio em cadeia

Sobre `b978c703`, a ponta do kit (o commit deste registro só acrescenta texto em `.claude/plans/`), num
clone descartável, com a suíte completa: na passada paralela, 16.032 passed e 1 falha; na serial, 683
passed; `test-rc1-kit.sh` com 267 PASS e 0 FAIL; `test-ga-kit.sh` com 57 PASS e 0 FAIL. A falha da passada
paralela é `tests/integration/test_install_smoke.py::test_install_creates_expected_layout`:
`TimeoutExpired` no teto de 90 s de um `install.sh`, com o harness do kit rodando em paralelo na mesma
máquina. Repetida isolada no mesmo clone, passa em 41,7 s. É a classe do item 20 do backlog da 1.4.4
(orçamento absoluto de tempo que mede o ambiente), e o kit não toca o instalador. Em `20ec3d4e`, antes das
curas da rodada 3 (que só tocam o kit), a paralela deu 16.033 passed e a serial 683 passed.

## Para o backlog da 1.4.4 (não curados no kit)

Os P3 sem cura no kit estão no item 27 de `.claude/plans/PLAN-194-FOLLOWUP-v1-4-4-backlog.md`, pela forma: LM-01, o resto do LM-04 e LM-06 (rodada 1); os controles vermelhos dos ramos da guarda e do censo que ainda não têm controle (LM3-02, LDR3-05); as strings de `die` e de `printf`, que ficam fora da guarda (LDR3-03); e o rótulo e o cabeçalho da parte 4 do runner fora das regiões dos radicais (LDR3-04).
