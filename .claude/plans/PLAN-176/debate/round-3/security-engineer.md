---
round: 3
archetype: Principal Security Engineer
skill: security-and-auth
agent_persona: (crítico de fronteiras de confiança, autenticação de portões e cadeia de suprimento; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-07T01:20:00Z
---

## Verdict

ADJUST — **4 itens bloqueantes** (S1, S2, S3, S4).

## Summary (≤ 3 bullets)

- **A cura da rodada 2 funcionou onde foi aplicada.** Re-verifiquei os 16
  ajustes: os 13 vereditos do oráculo reproduzem em HEAD (13/13), `ADR-180`
  está livre e sem menção fora deste plano, `gate-scripts-manifest.txt` tem 9
  membros, `owner-decisions-S347.md:21` e `:55` são as linhas citadas,
  `CLAUDE.md:97` contém `97.292`, e os dois allowlists nomeados no §3.1/§3.3
  batem campo a campo com `audit_emit.py:1601-1608` e `:1354-1358`.
- **Onde é forte, do meu ângulo:** o split T/P não alarga a lista de guardas;
  o oráculo de runtime com controle por importação transitiva é a cura certa
  da classe «grep de nomes»; a allowlist de destino re-casada após `302`
  fecha metade real da superfície; `_coerce_egress_destination` está lido
  corretamente (`:8506-8531`, corta em `/ ? #`).
- **Onde é fraco:** a degradação de auditoria foi aplicada a **dois** dos
  **quatro** eventos que o plano usa; o portão do conjunto-vermelho é
  autenticado por um arquivo que qualquer PR edita; o único interruptor do
  módulo com rede não tem camada de aplicação declarada; e o cache de rede
  chega ao contexto do CEO sem cerca e sem `.gitignore`.

## Risks

**S1 — P1 — O portão do conjunto-vermelho é autenticado por um arquivo que
qualquer Pull Request edita; o molde que o plano cita tem a metade que falta.**
`PLAN-176:385-399` cria `.claude/data/model-currency-expected-reds.txt` (oráculo
= 0, medido) «no molde de `scripts/tests/ownership-expected-reds.txt`», e a AC
`expected_reds_exact_set_with_shrinkage_control` promete que «um vermelho que
some sem explicação é motivo para PARAR». Medido: o molde citado é a **linha 6
de `.claude/governance/gate-scripts-manifest.txt`** — ele é membro do manifesto
de portões, e é exatamente isso que impede alguém de silenciar o portão editando
o baseline em vez de consertar a árvore. O análogo deste plano **não entra em
manifesto nenhum**: a única AC de manifesto (W1c, `:694-697`) adiciona só o
lint. Consequência: apagar uma linha do arquivo de vermelhos torna o conjunto
«exato» verde por construção — o controle de encolhimento controla a árvore, não
o baseline. É um portão cuja autoridade é prosa editável.
*Cura:* o arquivo de vermelhos entra no manifesto na W1c, junto com o lint (o
pacote já é canônico e o teto de 8 caminhos não muda), OU o plano declara por
escrito que o portão não resiste a um editor com acesso a PR.

**S2 — P1 — A degradação de auditoria da rodada 2 não alcançou os dois eventos
restantes; os dois falham pela MESMA mecânica que o §3.1 documenta.**
Duas pernas, ambas medidas:
- **`egress_destination_detected` não tem campo `decision`.** `PLAN-176:498` diz
  «o que a cadeia carrega é host + `egress_class` + **a decisão**», e a AC
  `refused_destination_emits_event` (`:532-537`) promete «o host recusado **e a
  decisão**». Medido, `_EGRESS_DESTINATION_DETECTED_ALLOWLIST`
  (`.claude/hooks/_lib/audit_emit.py:8480-8490`) é
  `{action, session_id, project, egress_class, destination, ts, event_schema,
  tokens_*, hmac*}` — **`decision` não existe** e o ramo de scrub (`:6828-6836`)
  descarta chave não-allowlistada. O efeito de segurança é pior que a promessa
  perdida: um despacho RECUSADO e um despacho BEM-SUCEDIDO para o mesmo host
  gravam o **mesmo evento byte a byte** (mesma ação, mesmo host nu, mesmo
  `egress_class`). O caso que a AC existe para cobrir — o `302` do mesmo host
  para outro caminho, que a AC vizinha `:518-524` acabou de nomear como ameaça —
  é **invisível na cadeia HMAC**.
- **`env_var_hijack_blocked` não carrega o nome da variável e coage a classe.**
  `PLAN-176:211-212` promete que valor fora da gramática «emite
  `env_var_hijack_blocked` e é descartado — não degrada para padrão em
  silêncio». Medido: o allowlist (`:8454-8462`) é
  `{action, session_id, project, hijack_class, ts, event_schema, tokens_*,
  hmac*}` com o comentário `:8451-8453` «the var NAME and the assigned VALUE are
  NEVER allowed fields», e `:6817-6818` **coage** qualquer `hijack_class` fora
  do enum fechado `{linker_preload, linker_path, runtime_hook, linker_other,
  parse_failure}` (`:8469-8473`) para `"parse_failure"`. Nenhum valor do enum
  descreve sequestro de preferência de modelo. O evento gravado, portanto, não
  diz que variável foi rejeitada nem por quê — e nenhuma AC assere o que
  sobrevive ao scrub (a AC `:646-649` testa a gramática, não o evento).
*Cura:* aplicar a mesma degradação declarada do §3.1 a estes dois (dizer o que
sobrevive e o que não), com AC de ausência como a `emits_egress_event_without_path`
já faz; e nomear na OQ-2 que a rota cara inclui **enum**, não só allowlist.
Nota conexa (P2): `model_routing_enforced` **não** tem coerção de `decision`
(`:5844-5853` só faz scrub de nomes), então o campo passa — mas o enum
documentado em `:1598-1599` é `enforce_telemetry | advisory | eval_error`, «NO
`block` value». Registrar um valor novo ali é extensão de taxonomia em arquivo
com oráculo = 1, e a OQ-2 hoje só precifica «emendar o allowlist».

**S3 — P1 — O único interruptor do módulo com rede não tem camada de aplicação
declarada, e a AC que o testa é satisfeita por uma implementação que não fecha
nada.** `PLAN-176:453-455` afirma: «sem a bandeira, **nenhum chamador (agente ou
não) abre soquete**» — é a defesa REAL declarada, depois que o portão de
chamador foi rebaixado a convenção (`:442-455`, com a medição honesta de que não
existe marcador de contexto de agente: `grep -rn 'CLAUDE_AGENT\|is_subagent\|
agent_context' .claude/hooks/_lib/*.py` = 0). Mas `:456-458` diz que o
interruptor é **«bandeira de linha de comando»**, e o módulo mora em
`.claude/hooks/_lib/model_feed_fetch.py`, importável por todo hook. Uma bandeira
parseada em `__main__` **não é vista por um importador** — `from _lib import
model_feed_fetch; model_feed_fetch.fetch()` não passa por argv. A AC
`disabled_by_default_opens_no_socket` (`:512-517`) fica VERDE nas duas
arquiteturas: a que fecha (parâmetro da função com padrão desligado) e a que não
fecha (gate só no `__main__`). Uma AC que não separa a implementação segura da
insegura não é catraca.
*Cura:* a AC tem de exigir que o estado desligado seja **parâmetro da função de
biblioteca** (padrão `enabled=False`), com controle positivo que IMPORTA o módulo
e chama a função diretamente, sem argv, e prova que não abre soquete.

**S4 — P1 — O cache de rede chega ao contexto do CEO sem cerca, e nada o mantém
fora do commit.** `PLAN-176:767-774` e `:508-510` definem
`.claude/data/model-currency-upstream-cache.json` como escrito pelo fetcher a
partir de conteúdo **buscado na rede** e lido pelo `/ceo-boot` (W3a). Duas pernas:
- **Sem cerca no consumidor de maior privilégio.** A W2a tem AC própria para
  isso no corpo do Pull Request (`untrusted_feed_is_fenced`, `:741-744`), mas a
  W3a **não tem nenhuma**: as quatro caixas (`:776-800`) cobrem o trio exibido,
  o não-bloqueio, o «lê e nunca busca» e a documentação. O boot imprime conteúdo
  de origem externa **dentro da sessão do CEO** — canal instruction-adjacent
  para o agente de maior privilégio do repositório, que é a classe que
  `CLAUDE.md` §5 (r22) registra como fechável só por remoção/cerca.
- **Não rastreado é afirmação, não mecanismo.** Medido:
  `grep -n 'model-currency\|\.claude/data' .gitignore` ⇒ só
  `.claude/data/federation/peers.yaml` (`:197`). O plano diz que o cache «NÃO é
  rastreado pelo git» (`:770-772`), mas a ordem obrigatória deste repositório é
  `git add -A` → portões → commit (`CLAUDE.md` §4): sem linha de `.gitignore`, o
  primeiro `add -A` **commita conteúdo de rede na árvore**.
*Cura:* AC de cerca+truncamento no leitor da W3a (mesmo molde da `:741-744`,
envenenando a dimensão dona) + AC que assere a linha de `.gitignore`, no pacote
livre da W0b/W3a.

**S5 — P2 — Depois da W1c o lint deixa de ser «livre», e duas seções do plano
continuam dizendo que é.** `PLAN-176:144` publica
`.claude/scripts/check-model-literals.py 0 (lint — Pull Request livre)` e a W1a
o trata como caminho livre (`:561-566`). A W1c o inscreve no manifesto de
portões (`:694-697`). Medido em `CLAUDE.md` §5 (linha S326): «`verify-counts.sh`
é membro do manifesto ADR-192 — o oráculo `--is-canonical` responde 0 para ele,
**mas edição de membro passa pela cerimônia**». Ou seja, a partir da W1c todo
conserto no lint custa uma assinatura, e o plano só declara esse custo para o
resolver (`:1043-1046`, «Custo declarado do resolver ser canônico»).
*Cura:* uma linha no §5 declarando o mesmo custo para o lint, e a correção da
glosa do §2:144 («livre até a W1c»).

**S6 — P3 — «Nada do repositório sai» é verdade só enquanto o cabeçalho for
constante.** `:475-478` fundamenta a garantia de egresso em «`GET`, sem corpo,
sem parâmetro de consulta além do caminho fixo, sem cabeçalho customizado». As
ACs da W0b cobrem allowlist (host+caminho, inclusive redirecionamento),
tempo-limite, certificado, evento e forma da resposta — **nenhuma cobre a
requisição não carregar cabeçalho, cookie ou `User-Agent` derivado do ambiente**.
É a diferença entre uma garantia e uma frase.
*Cura:* estender a AC `allowlist_matches_host_and_path_including_redirect` para
asserir o conjunto EXATO de cabeçalhos enviados (fechado, não «sem customizado»).

## Must-fix (blocking)

1. **S1** — o arquivo de vermelhos entra no manifesto da W1c, ou o plano declara
   por escrito que o portão não resiste a um editor com acesso a PR.
2. **S2** — degradar as promessas de `egress_destination_detected` (sem
   `decision`; recusa e sucesso são indistinguíveis no mesmo host) e de
   `env_var_hijack_blocked` (sem nome de variável; `hijack_class` coagida a
   `parse_failure`) aos campos medidos, com AC de ausência; ampliar a OQ-2 para
   incluir extensão de **enum**.
3. **S3** — a AC do interruptor tem de exigir o estado desligado como parâmetro
   da função de biblioteca, com controle positivo por importação direta sem argv.
4. **S4** — AC de cerca/truncamento do cache no leitor da W3a **e** AC da linha
   de `.gitignore`.

## Nice-to-have (advisory)

- **S5** — declarar no §5 o custo de cerimônia que o lint herda ao entrar no
  manifesto, e ajustar a glosa do §2:144.
- **S6** — fechar o conjunto de cabeçalhos por AC, não por frase.
- A W1c inscreve um caminho no manifesto enquanto o `w4b-ci-matrix` o leva de 9
  a 12; a ordenação está declarada (`:677-682`) e o baseline re-derivado no SIGN
  — do meu ângulo isto está certo, e a AC `baseline_is_rederived_from_live_manifest`
  é a forma correta. Registro como confirmação, não como risco.

## Unseen by the original plan

- A rodada 2 curou a auditoria **por evento citado no §3**, não **por evento
  usado pelo plano**. Os quatro eventos que o texto invoca são
  `model_routing_enforced`, `model_choice_recommended`,
  `egress_destination_detected` e `env_var_hijack_blocked`; a cura alcançou os
  dois primeiros. A regra que fica: quando a cura é «degradar ao que o allowlist
  fechado carrega», o censo é sobre o conjunto de ações que o plano EMITE,
  derivado mecanicamente, nunca sobre as ações que a seção corrigida mencionava.
- O plano importa um molde (`ownership-expected-reds.txt`) sem importar a
  propriedade que o torna um portão (membro de manifesto). Copiar a FORMA de um
  instrumento sem copiar a sua ÂNCORA é a mesma classe de S1 e vale como regra
  independente do resultado desta rodada.

## What I would NOT change

- O split T/P e a decisão de não alargar a lista de guardas: os 13 vereditos
  reproduzem, e é a decisão mais forte do plano.
- A escolha de `.claude/hooks/_lib/model_feed_fetch.py` (oráculo = 1) em vez de
  `check-substrate-watch.py` (oráculo = 0): o cabeçalho daquele arquivo
  (`:8-11`) diz o que o plano cita, e o precedente `otel_emit.py` (11
  ocorrências de `urllib`, oráculo = 1) confere.
- O ponto cego declarado do oráculo de runtime (`:410-417`): declarar o residual
  é a postura certa; não peço portão que não existe substrato para construir.
- As três OQ do §5b permanecem ABERTAS — não as decido, e nenhuma bloqueia.

**BLOCKING: 4.** `status:` permanece `reviewed`; o flip é a decisão 4.10 do
Owner. Esta rodada certifica coerência interna, e ainda não a certifica.
