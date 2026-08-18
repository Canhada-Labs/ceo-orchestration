# Security Engineer — PLAN-181 round 1

## Verdict

ADJUST — a tese ("adotar com wrapper, nunca cru") está certa, mas os 7 gaps
são um conjunto INCOMPLETO e três dos moldes citados não alcançam o
substrato do `/loop`; o piloto W0 num freeze real é a decisão que eu
bloquearia como está escrita.

## Summary

Li o plano contra o disco. O que sustenta: `/loop` é de fato Tier-C nato
pelo critério 1 do ADR-125 ("spends tokens autonomously without per-action
user prompt", `ADR-125-risk-tiered-defaulting-doctrine.md:211-216`), e o
próprio guia já declara que ele **não** é governado pelas 6 camadas de
swarm (`docs/AUTONOMOUS-LOOP-GUIDE.md:169-172`). O molde de opt-in
(`night-mode.py`) é genuinamente bom: fail-closed on input, REFUSE em CI
por PRESENÇA da var (`.claude/scripts/night-mode.py:454-464`), registro
duplo, enum real do harness (`:257`), rota de recuperação não-restauradora
(`:281-287`), e recusa até de invocação por alias (`:785-813`).

O que NÃO sustenta, e é o núcleo desta crítica: **três dos sete gaps citam
moldes que são inalcançáveis a partir de um tick de `/loop`.** Budget
(W2.2), pausa Owner-absent (W2.5) e o audit por tick (W2.4) vivem todos no
substrato `CEO_SWARM` — `swarm/loop_runner.py` + um matcher Bash que exige
assinatura de coordinator. Um tick de `/loop` é um wakeup do harness: não
passa por `loop_runner.step()`, não emite `swarm_started`, não roda um
comando Bash de coordinator. Reusar o nome do molde sem reusar o ponto de
interceptação é exatamente a classe "instrumento verde cuja PERGUNTA
envelheceu".

E falta um oitavo gap, que é o pior de todos: composição com `night-mode`.

## Risks

**P0-1 — 8º gap ausente: `/loop` sob `night-mode` herda autonomia de
ESCRITA por tick.** `night-mode on` merge-escreve
`permissions.defaultMode: "acceptEdits"` no `settings.local.json`
gitignored (`.claude/scripts/night-mode.py:5-7`, `:244`). Esse é estado de
SESSÃO: todo tick do `/loop` que rodar naquela sessão tem Edit/Write
auto-aprovado, sem prompt. Duas capacidades individualmente opt-in
(posture noturna + recorrência) compõem uma terceira que ninguém aprovou —
mutação recorrente e não-supervisionada do repo. Nem o `night-mode` sabe
que existe um loop, nem o `/loop` sabe qual posture está armada. Pela
resposta direta à OQ-2: **não, os 7 gaps não são o conjunto certo.**

**P0-2 — a LINHA DURA do W0 é PROMETIDA, não garantida** (proposal.md:29,
plano `:41-42`). Não existe guard on-disk que impeça um tick de cortar tag
ou landar: `check_bash_safety.py` guarda `rm -rf`, `git reset --hard` e
`git push --force`/`-f` (`:427-442`, `:581`) — e nada mais. Não há matcher
para `git tag`, `git push` simples, nem para o freeze rota-SEQUÊNCIA. A
lição da S303 é literalmente esta: o freeze foi violado sem instrumento
avisar, porque um gate só fala quando EXECUTADO — e um tick não executa o
gate, ele executa o comando. Somando com P0-1 (se a sessão estiver sob
`acceptEdits`, nem o prompt de permissão existe), o piloto coloca um MODELO
com toolset completo dentro da janela em que o repo está congelado. "Owner
presente" não é controle: presente ≠ olhando cada tick de uma hora.

**P0-3 — W2.5 mede a coisa errada, e o detector é no-op estrutural para
`/loop`.** O plano diz "auto-PAUSE >12h sem Read do Owner" (plano `:69`).
O molde não mede Read: `_OWNER_READ_ACTIONS = frozenset({"session_start"})`
(`.claude/hooks/_lib/swarm_circuit_breaker.py:51`) — o nome da constante
mente sobre o conteúdo dela. Consequências:
  (a) `session_start` é emitido por QUALQUER boot de sessão, incluindo
      headless e subagente. Um loop que dispare qualquer sessão filha
      FABRICA sua própria evidência de "Owner presente". Isso não é
      spoofing sofisticado — é o funcionamento normal do proxy. Não há
      atribuição a um humano em lugar nenhum da cadeia.
  (b) `should_pause_weekend_burn` só considera loops abertos por
      `swarm_started` (`:162`) e fechados pelos `swarm_halted_*` (`:165`).
      Um `/loop` do harness não emite nenhum desses ⇒ `active_swarms` fica
      vazio ⇒ o detector retorna False para sempre. Herdar este molde sem
      um produtor equivalente é herdar um verde vazio.
  (c) O wiring real vive em `.claude/scripts/swarm/loop_runner.py:186-240`,
      atrás de `CEO_SWARM=1` — substrato que o `/loop` não atravessa. O
      histórico é agravante: este módulo já teve fase de "zero production
      callers" e já referenciou ações-fantasma que nunca existiram no
      `_KNOWN_ACTIONS` (`swarm_circuit_breaker.py:44-50`).

**P1-4 — W2.2 não tem caminho de enforcement hoje.** O comentário de
registro é explícito: o `check_cost_envelope.py` "Activates ONLY when BOTH
CEO_SWARM=1 AND command body matches a real swarm coordinator signature"
(`.claude/settings.json:313`). Tick de `/loop` falha nas duas condições.
Resposta à OQ-3: budget e teto são ENFORCEMENT e uma SKILL não os entrega —
skill é advisory por construção. O único ponto de interceptação que existe
para um tick é a família de hooks (SessionStart / PreToolUse / PostToolUse).

**P1-5 — injeção acumulada: W2.7 MOVE a superfície, não a remove.** Trocar
transcript por "estado durável em disco" (plano `:71`) significa que
conteúdo hostil lido no tick N é PERSISTIDO e relido como contexto no tick
N+1. A única defesa no caminho de re-leitura é `check_read_injection.py`,
que por contrato "Always allows the read" (`:4`, `:32-35`) e só bloqueia
sob `CEO_UNICODE_HARDBLOCK=1`. Advisory pressupõe um humano lendo o
`systemMessage` — precisamente o que um loop não tem. Sem hardening, o
wrapper aumenta a exposição em relação ao transcript (que ao menos era
volátil e visível).

**P1-6 — W1 pode vazar e/ou derrubar eventos.** `session_crons` existe
mesmo no schema (`.claude/plans/PLAN-163/probes/hook-schema-2.1.220.json:88`,
Stop e SubagentStop), mas o SHAPE de `CronSummary` não está registrado em
lugar nenhum do disco — só o nome do tipo. Logar o objeto cru arrisca dois
danos conhecidos deste repo: (a) o prompt do cron é texto arbitrário e pode
carregar segredo/PII para dentro de um log DURÁVEL e HMAC-chained, que as
skills `audit-tokens` e `skill-health` depois renderizam como untrusted
data; (b) um campo float num evento coberto por HMAC descarta o evento
inteiro. Bump de SPEC antes de conhecer o shape é bump às cegas.

**P1-7 — `CLAUDE_CODE_DISABLE_CRON` é claim de documentação, não fato
verificado.** Aparece apenas em `docs/AUTONOMOUS-LOOP-GUIDE.md:169-172` e
no próprio plano; não há um único teste, sonda ou controle on-disk. É o
kill-switch ÚNICO da capacidade inteira e ninguém neste repo jamais o viu
funcionar. Um kill-switch não testado não conta como camada.

**P2-8 — Stop é o hook errado para parar qualquer coisa.** No schema do
harness, um Stop que devolve `{"decision":"block"}` força o modelo a
CONTINUAR. W1 sendo advisory está correto; o risco é W2 herdar o ponto de
montagem "porque W1 já estava lá".

**P2-9 — `CEO_SOTA_DISABLE=1` desarma a família de gates** (rota de
recuperação documentada em `CLAUDE.md` §4). Um loop cuja sessão nasça com
essa var no ambiente roda com o wrapper inteiro em modo advisory, e nada
avisa.

## Must-fix

1. **Adicionar o 8º gap (W2.8): interação com a posture de permissão.** O
   tick 0 do wrapper LÊ a posture efetiva e RECUSA se for `acceptEdits`,
   `bypassPermissions`, `dontAsk` ou `auto` — fail-closed, com a mesma
   disciplina de enum exato do `night-mode.py:257` (conjunto derivado da
   autoridade, nunca escrito de memória). Simetricamente: `night-mode on`
   deve recusar quando houver cron/loop vivo na sessão. Sem isso, os outros
   sete gaps protegem o custo e deixam a ESCRITA aberta.
2. **W0 não roda num hold real.** Ensaio em clone com tag falsa (doutrina
   S293/S301), ou não roda. Se o Owner mantiver o hold real como alvo, então
   a linha dura precisa de mecanismo, não de prosa: um matcher PreToolUse
   fail-closed que bloqueie `git tag`, `git push`, `gh release` e o
   `OWNER-GA-CUT.sh` enquanto a var de freeze estiver armada — com controle
   positivo provando a RECUSA (lição t10, já citada no próprio plano `:58-59`).
3. **Reescrever W2.5 sobre um sinal que exista para `/loop`.** Nomear
   honestamente o que o proxy mede (boot de sessão, não Read do Owner),
   declarar explicitamente que ele é auto-fabricável por sessões filhas e,
   se a pausa Owner-absent for para ficar, exigir um sinal com atribuição
   humana (evento Owner-físico dedicado, ou ancoragem no ciclo GPG). Enquanto
   isso não existir: declarar W2.5 como NÃO-ENTREGUE em vez de herdar o
   molde vazio.
4. **Trocar "acionar o molde" por "declarar o ponto de interceptação".**
   Para cada um dos 8 gaps, o AC deve nomear o EVENTO de hook que executa a
   checagem e o que acontece na recusa. Gap sem evento é gap não fechado.
   `cost_envelope` e o circuit-breaker só valem se um hook novo os chamar
   fora do gate `CEO_SWARM=1`.
5. **Controle positivo do kill-switch, antes de qualquer outro AC.** Loop de
   brinquedo em sessão descartável, `CLAUDE_CODE_DISABLE_CRON` armado, provar
   que o tick seguinte NÃO dispara, e medir a latência até a parada. Se o
   kill-switch não for demonstrável, o plano inteiro perde a premissa e vira
   "não adotar".
6. **W1: sondar o shape de `CronSummary` ANTES do bump de SPEC**, e logar
   apenas campos derivados — contagem, intervalo, `sha256` do prompt. Nunca
   o corpo do prompt. Allowlist explícita, ints com unidade no nome.
7. **W2.7: estado inter-tick estruturado com allowlist de campos**, nunca
   prosa livre; `CEO_UNICODE_HARDBLOCK=1` obrigatório durante loop; e o
   arquivo de estado tratado como untrusted na releitura (a mesma postura
   que o spawn protocol já impõe a retorno inter-agente: fenced + capped).
8. **W2.6: citar o guard que já existe e medir o delta.** A proibição de
   tocar governança não deve nascer como prosa de skill — parte dela já é
   `check_canonical_edit.py`, fail-closed com sentinel. O AC deve enumerar,
   por controle positivo, quais paths o guard cobre hoje, e o trabalho novo é
   SÓ o complemento. Como está (`plano :70`), é teatro — a classe que o
   próprio plano diz querer evitar.

## Nice-to-have

- Registrar `loop_id` em todo evento de tick: sem ele não há como atribuir
  custo nem correlacionar uma recusa ao opt-in que a autorizou (OQ-5).
- Ordenar PLAN-179 antes do 181-W2, não em paralelo: se governança decai
  30-59% sob compactação, um loop longo é o pior caso possível, e a primeira
  restrição esquecida tende a ser justamente a de W2.6.
- Checar `CEO_SOTA_DISABLE` no tick 0 e recusar — mesma família do item 1.

## Unseen

- **Fronteira de identidade.** O loop roda com a identidade e as credenciais
  do Owner (git, `gh`, GPG-agent com socket vivo). Nenhum dos 7 gaps trata
  disso. Um tick com GPG-agent destravado pode ASSINAR — o que colapsa a
  cerimônia inteira, que é justamente o mecanismo em que este repo apoia
  autoridade. Merece um gap próprio ou uma exclusão explícita.
- **Composição, não capacidade.** P0-1 é uma instância de uma classe: duas
  autonomias aprovadas separadamente produzem uma terceira que ninguém
  revisou. O plano deveria declarar a MATRIZ (loop × night-mode × swarm ×
  Workflow) e dizer quais combinações são proibidas.
- **OQ-1, do meu ângulo:** o `Monitor` é estritamente superior em segurança —
  processo externo, um comando, sem contexto de modelo, sem ferramenta de
  escrita. O `/loop` só se paga onde é preciso JULGAMENTO recorrente. Vigiar
  hold não é isso. Se W0 existir, que seja para exercitar a recorrência num
  ensaio, nunca para vigiar um freeze.
- **OQ-4:** o inventário de W1 não é sonda órfã do meu ponto de vista — é
  pré-requisito de detecção (não se governa o que não se enumera). Mas só
  vale com o item 6 acima; um inventário que vaza prompt é passivo.

## What I would NOT change

- "Adotar com wrapper, nunca cru" — correto, e a leitura do `/loop` como
  Tier-C nato está ancorada no critério certo (`ADR-125:211-216`).
- `night-mode.py` como molde de opt-in: é o melhor exemplar de fail-closed
  deste repo, e a escolha está certa (fica só o alerta do P0-1, que é sobre
  a INTERAÇÃO com ele, não sobre a qualidade dele).
- A honestidade já declarada sobre HMAC RESERVED (proposal.md:54-55): não
  reivindicar tamper-evidence entre iterações está exatamente certo. Idem a
  citação da lição t10 — o plano já sabe qual é o teste dele.
- W3 exigindo sentinel GPG para a SKILL.md nova e §Cost do ADR-125 como
  condição de ship.

DONE_WITH_CONCERNS
