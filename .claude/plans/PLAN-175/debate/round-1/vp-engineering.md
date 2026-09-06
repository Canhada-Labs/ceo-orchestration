---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-06T07:40:00Z
---

> **Nota de setup (DADO, não achado do plano).** O prompt desta rodada nomeia a
> proposta como `<ROOT>/.claude/plans/PLAN-175.md`. Esse arquivo **não existe em
> HEAD**; o plano vive em `<ROOT>/.claude/plans/PLAN-175-skills-pruning-discovery.md`
> (171 linhas, `status: reviewed`). Critiquei o arquivo real. Toda referência
> abaixo é a ele.

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano acerta a ORDEM (descoberta antes de poda), a forma da regra (determinística, arquivar-não-deletar) e é honesto ao registrar em §3.1 que o mecanismo do P1 estava morto. A §3.1 é o melhor pedaço do documento: mede, publica o controle e declara o N.
- **Onde é forte:** a recusa de fechar o P1 no baseline (§3:76-78), a rota única do sweep de atualidade (§1:50-51, «sem rota dupla»), e o reconhecimento de que a contagem pinada é o incentivo estrutural anti-poda (§1:55-58).
- **Onde é fraco:** as duas janelas de 90 dias que sustentam os passos 1 e 2 **não existem em HEAD** — a família de auditoria por projeto nasceu em 2026-08-21 (16 dias). E a regra de poda, ao contrário do passo 1, não tem guarda de denominador: com telemetria vazia ela não recusa, ela **arquiva tudo**. É a forma «instrumento verde cuja pergunta envelheceu», agora com efeito destrutivo.

## Risks

**R-VP1 — P1 — A janela de 90 dias não existe: a família de auditoria deste projeto tem 16 dias.**
§1:36 fixa «janela = 90d de audit log, N mínimo = 100 spawns» e §1:38-39 define a poda por «0 invocações em ≥90d». Medido em `<PK>`: o arquivo rotacionado mais antigo é `audit-log-2026-08.jsonl`, cujo primeiro evento é `ts=2026-08-21T12:13:43Z`; o `.salt` do diretório é de 21/08. A causa é conhecida e correta — a W1 do PLAN-182 separou a cadeia HMAC por projeto (`CLAUDE.md` §5) — mas a consequência não está no plano: **90 dias de histórico só existem por volta de 2026-11-19**. O `external_wait` do frontmatter (linha 13) nomeia «pós-GA v1.3.0; W1c do PLAN-171» e **não** nomeia essa data.
*Mitigação:* o `external_wait` passa a citar a data de acúmulo e o COMANDO que a verifica (primeiro `ts` da família); enquanto ela não chega, os passos 1 e 2 estão fechados por calendário, não por decisão.

**R-VP2 — P1 — A regra de poda falha ABERTO: sem denominador mínimo, telemetria vazia arquiva tudo.**
O passo 1 tem guarda explícita de amostra (`N mínimo = 100 spawns`, §1:36). O passo 2 (§1:38-41) **não tem nenhuma**: é `0 invocações em ≥90d E ausente do SKILL MAP`. Com a família de 16 dias do R-VP1, e com o próprio plano registrando que o detector vivo reporta `0 general-purpose, 0 test-pollution` (§3.1:150-152), a lista derivada é *toda skill core fora do SKILL MAP*. O AC do P2 (§3:79-81) exige que a lista seja «DERIVADA pela regra determinística (nunca curada à mão)» — ou seja, **o Check não pode ficar vermelho**: derivação sobre denominador zero satisfaz o AC e arquiva em massa. Um instrumento sem sinal deve RECUSAR, não concluir.
*Mitigação:* dois parâmetros pré-registrados na própria regra — `min_window_coverage_days` (a janela precisa estar coberta pelo log) e `min_observed_spawns` — e a regra emite `REFUSE: insufficient telemetry` em vez de uma lista. O AC do P2 ganha um controle positivo: com log truncado a regra sai vermelha.

**R-VP3 — P1 — §3.1 declara «não há sinal» a partir do leitor ERRADO; duas seções discordam sobre qual instrumento define a janela.**
O bloco de bloqueio (§3.1:147-156) argumenta a inexecutabilidade do N≥30 citando o `skill_unknown_ratio` do `/ceo-boot`. Esse detector lê **só o arquivo vivo, 24 h**: `<ROOT>/.claude/scripts/ceo-boot.py:661` chama `_iter_audit_events_since(24)`, e a função (`ceo-boot.py:448-472`) abre apenas `AUDIT_LOG_DEFAULT`, sem nenhuma descoberta de rotacionados. O arquivo vivo foi rotacionado em `2026-09-06T01:58:33Z` (manifesto de rotação em `<PK>`) e guarda 11 498 linhas ≈ 5,5 h. O instrumento que o PLANO precisa é outro: `<ROOT>/.claude/scripts/skill-health.py` **descobre rotacionados** (`:207-209`, docstring `:44`) e parseia janela (`:268`). Logo o «zero» citado é uma propriedade de um detector de 24 h, não a ausência de sinal em 90 d.
*Mitigação:* nomear o LEITOR em cada AC («janela X medida por `skill-health.py --since 90d` com rotacionados incluídos») e re-derivar o bloco §3.1:147-156 com esse leitor. A conclusão pode sobreviver (R-VP1 a sustenta por retenção), mas hoje ela está provada pelo instrumento errado.

**R-VP4 — P1 — `archive/` dentro de `.claude/skills/` não tira uma skill de contagem nenhuma nem de gate nenhum.**
§1:40-41 promete «rollback = `archive/` restaurável» e §1:47-48 promete que «CI/soak param de vigiar prosa de domínio». Mas a derivação de contagem é recursiva e cega a tier: `<ROOT>/.claude/scripts/local/verify-counts.sh:192` faz `find "$REPO_ROOT/.claude/skills" -name SKILL.md`. Uma skill movida para qualquer `archive/` **sob `.claude/skills/`** continua contada no total (e, se sob `core/`, no 42). O plano **nunca nomeia o path de destino** do arquivamento. Sem isso o passo 2 entrega risco de perda de catálogo sem entregar nenhum dos dois benefícios declarados.
*Mitigação:* nomear o destino FORA de `.claude/skills/` (ou ensinar `verify-counts.sh` a excluí-lo **no mesmo patch**, com controle positivo: arquivar 1 skill ⇒ total cai de 166 para 165).

**R-VP5 — P1 — O passo 3 depende de uma wave que não começou, e seu AC-mestre testa o caminho que não regride.**
A ferramenta existe — verifiquei `<ROOT>/.claude/scripts/{squad-export.py,squad-import.py,validate-squad-contract.py}` e o comando `<ROOT>/.claude/commands/squad-install.md:46`, que invoca `squad-import.py`; ADR-039 está `ACCEPTED (2026-04-14)`. O problema é o CONTRATO de instalação: `<ROOT>/scripts/install.sh:12-15` documenta `--profile core,fintech` e `:1288-1297` instala a partir da árvore. Tirar 116 skills da árvore muda o que um perfil de domínio consegue resolver. O AC-mestre do P3 (§3:83-84) só exige que «install/upgrade de adopter **SEM packs** funcione» — justamente o caminho que não regride. Some-se a dependência declarada em §1:49 e §3:88-89: `PLAN-171` W1c é `contract-only` (`<ROOT>/.claude/plans/PLAN-171-governance-imports-provenance.md:165`) num plano `status: executing` que está no lote 1/6 do W0 — W1c não começou.
*Mitigação:* o AC-mestre vira DOIS — sem packs (verde) e **com** `--profile core,<domínio>` após a mudança (o que hoje ninguém testa); e o passo 3 não abre antes de W1c estar entregue, não apenas planejada.

**R-VP6 — P2 — Despinar o «166» troca uma superfície vigiada por uma invisível, e o AC do P5 não consegue ficar vermelho.**
§1:55-58 quer prosa derivada («N core + M frontend + packs opt-in»). Mas `verify-counts.sh:584-616` casa as claims por REGEX literal sobre a prosa (`(\d+) reusable skills`, `\((\d+) core `, `# (\d+) skills across`, …) e compara exato. **Prosa que deixa de casar não vira derivada — vira não-vigiada**, que é a classe já registrada como `feedback-adr-count-drift-unwatched-docs`. O AC do P5 (§3:84-86) — «`check-claude-md-claims` verde com tolerance=0» — não detecta isso: `<ROOT>/.claude/scripts/check-claude-md-claims.py:68` define tolerance como absoluta com default 0, mas uma claim REMOVIDA simplesmente não é checada, e o gate sai verde por vácuo.
*Mitigação:* o AC do P5 assere o número de SÍTIOS casados, não só a cor do gate: contagem de claim-sites antes e depois, com a diferença justificada linha a linha; qualquer sítio que deixe de casar é falha até ser re-declarado num padrão novo do `verify-counts.sh`, no mesmo patch.

**R-VP7 — P2 — Três das quatro figuras de consolidação não têm fonte, e uma está fora do escopo do passo.**
§1:42-44 lista «lgpd×4 → 1; accessibility duplicada; 2 pares de basename duplicado». Derivado em HEAD: basenames duplicados = **exatamente 2** (`frontend-data-layer`, `frontend-patterns`) — essa figura se sustenta. **Accessibility duplicada não está no core**: os sítios são `<ROOT>/.claude/skills/frontend/accessibility-and-wcag/`, `<ROOT>/.claude/skills/frontend/frontend-accessibility/` e `<ROOT>/.claude/skills/domains/government/skills/accessibility-section-508/` — o passo 2 está escopado a «podar o **core**» (§1:38), então esse item pertence a outro passo ou o escopo precisa mudar. «lgpd×4» é defensável por tema (`compliance-lgpd`, `dpo-reporting`, `consent-lifecycle`, `pii-data-flow`), mas **9** SKILL.md de core mencionam LGPD — o «×4» não imprime sua derivação.
*Mitigação:* modelo de operação v2 — essas quatro figuras são GERADAS por instrumento no momento da execução, nunca digitadas; e o item de accessibility migra para o passo cujo escopo o contém.

**R-VP8 — P2 — A decisão (b) do gap de idioma não tem dono, nem check, nem critério de morte — e nenhum AC a menciona.**
§3.1:135-140 enumera três saídas (indexar PT / normalizar a query / declarar a limitação) e **não escolhe**; §3.1:145 exige N≥30 antes de decidir. Nenhum AC de §3 fala em idioma: o AC do P1 (§3:73-78) pede mecanismo vivo + baseline + re-medição aos 30 d + aplicação da regra de Fase 2. Resultado: o P1 pode fechar VERDE sem nunca decidir (b), enquanto a própria medição do plano diz que «ligar a sugestão por tf-idf em sessão PT é uma regressão medida» (§3.1:138-140). É um AC que não pode ficar vermelho exatamente no risco que a seção identificou.
*Mitigação:* (b) vira AC próprio do P1 com as três opções como conjunto fechado, um dono, e critério de morte pré-registrado («se recall@5 PT < recall@5 do static-fallback com N≥30, a sugestão fica DESLIGADA em sessão PT»).

**R-VP9 — P2 — O plano não tem decomposição em waves e não cabe no modelo de operação v2.**
O documento é uma lista de 5 passos (§1) sem rótulos de wave, e o `budget_sessions: 2-4` (frontmatter linha 11) é anterior ao modelo v2. O passo 3 move 116 skills — centenas de paths num movimento só, contra o teto de ≤ 400 linhas alteradas **ou** ≤ 8 paths por pacote. Sem cortar, nenhum passo pode abrir como pacote livre.
*Mitigação:* cada passo vira W-N com pacotes nomeados, cada pacote com sua regra de parada pré-registrada no topo do registro; o passo 3 é dividido por domínio (ou por lote de ≤ 8 paths com um derivador que gera o tarball).

**R-VP10 — P3 — O censo de §3.1 não reproduz mais em HEAD.**
§3.1:105-109 afirma que `grep -rln skill-index-build` sobre `.claude/hooks/`, `.github/workflows/` e `scripts/` «devolve apenas o próprio build, o retrieve e os testes». Re-executado em HEAD, o comando devolve `<ROOT>/.claude/hooks/_lib/frontmatter.py` (linha 22 — uma referência em docstring). A CONCLUSÃO sobrevive (docstring não é rota de bootstrap), mas a figura como escrita é falsa.
*Mitigação:* reescrever como «nenhuma referência EXECUTÁVEL» e pinar a saída do comando com a data.

**R-VP11 — P3 — O denominador da semente (164) discorda do título (166).**
Semente §:21-22 cita «157/164 skills com zero invocações (96%)»; o título e §1:55 falam em «166». HEAD deriva 166 = 42 core + 8 frontend + 116 domain, batendo com `verify-counts.sh:31-34`. Os 96% são internamente consistentes para 164, mas são citados ao lado de um catálogo de 166.
*Mitigação:* re-derivar a semente no momento da execução, com o comando impresso.

**R-VP12 — P3 — A linha de debate do §3 pode ser lida como duas autorizações.**
§3:94-95 diz «Codex r1→r3 (GO no r3); `/debate start PLAN-175` no início da execução». Esta rodada é um debate Claude de coerência de desenho — um gate DIFERENTE do pair-rail Codex, e que não autoriza nada por si. Sem uma frase que diga qual artefato satisfaz a linha do runbook, uma sessão futura pode tratar qualquer um dos dois como autorização.
*Mitigação:* nomear no §3 o artefato que satisfaz a linha (`.claude/plans/PLAN-175/debate/round-1/`), e repetir que ele certifica coerência interna, nunca verdade externa.

## Must-fix (blocking)

1. **Escrever no `external_wait` a data de acúmulo de telemetria e o comando que a verifica (R-VP1).** Hoje o plano promete uma janela de 90 d sobre uma família de auditoria de 16 dias.
2. **Dar guarda de denominador à regra de poda (R-VP2):** `min_window_coverage_days` + `min_observed_spawns`, com `REFUSE` como saída e controle positivo no AC do P2. Uma regra determinística sem guarda não é conservadora — é destrutiva por omissão.
3. **Nomear o LEITOR em cada AC de telemetria e re-derivar §3.1:147-156 com `skill-health.py` (R-VP3).** O bloqueio hoje é provado por um detector de 24 h que não lê rotacionados.
4. **Nomear o path de destino do arquivamento fora de `.claude/skills/` — ou excluí-lo em `verify-counts.sh:192` no mesmo patch (R-VP4),** com controle positivo 166 → 165.
5. **Desdobrar o AC-mestre do P3 e travar o passo 3 em W1c ENTREGUE (R-VP5):** um AC para install sem packs, outro para `--profile core,<domínio>` depois da mudança.
6. **Cortar o plano em waves que caibam no modelo v2 (R-VP9)**, com regra de parada por pacote; o passo 3 não pode existir como um movimento único.

## Nice-to-have (advisory)

1. AC do P5 assere a contagem de claim-sites casados, não a cor do gate (R-VP6).
2. Gerar as quatro figuras de consolidação por instrumento e mover o item de accessibility para o passo cujo escopo o contém (R-VP7).
3. Promover a decisão (b) do gap de idioma a AC com critério de morte (R-VP8).
4. Reescrever o censo de §3.1 como «referência executável» e pinar a saída (R-VP10).
5. Re-derivar a semente 157/164 no momento da execução (R-VP11).
6. Registrar num ADR a escolha de arquivar-em-vez-de-deletar e o limite de retenção da família por projeto — é o fato que governa todo o passo 2.

## Unseen by the original plan

1. **A retenção real da cadeia por projeto.** A cura correta da S319/S321 zerou o histórico em 21/08; nenhum passo deste plano considera que a própria separação por projeto redefiniu o que «90 dias de log» significa.
2. **Os dois leitores de audit log com janelas diferentes** (`ceo-boot.py:448` live-only/24 h × `skill-health.py:207` rotated-aware/janela parametrizada). O plano cita um e precisa do outro.
3. **`verify-counts.sh:192` é recursivo e cego a tier** — o `archive/` planejado não reduz contagem nenhuma se ficar sob `.claude/skills/`.
4. **A assimetria de guardas entre o passo 1 (N≥100) e o passo 2 (nenhuma).** O passo destrutivo é o menos protegido dos dois.
5. **`install.sh --profile core,<domínio>` é o caminho que o passo 3 quebra**, e é exatamente o que o AC-mestre não testa.
6. **Despinar uma contagem casada por regex a remove do gate.** «Derivada» e «não vigiada» são indistinguíveis para `verify-counts.sh` se a prosa deixar de casar.
7. **A duplicação de accessibility não está no core** — o item está no passo errado.

## What I would NOT change

- **A ordem: descoberta antes de poda.** Está certa e a §3.1 a reforça: sem discovery viva, a telemetria de poda mede o injetor, não o catálogo.
- **A regra determinística com lista derivada, nunca curada à mão.** O defeito é a falta de guarda, não a determinística — não substituir por curadoria.
- **ARQUIVAR, não deletar.** Continua sendo a escolha certa; só falta dizer PARA ONDE.
- **A rota única do sweep de atualidade no W-IM/172 (§1:50-51).** «Sem rota dupla» é a lição D1-D4 aplicada corretamente.
- **A honestidade da §3.1.** Registrar que o mecanismo do próprio P1 estava morto, publicar o controle (`static-fallback` 4/8) e declarar N=8 como insuficiente para magnitude é exatamente o comportamento que se quer preservar. Não «reconciliar» a tabela para melhorar a narrativa.
- **A escala de honestidade sobre velocidade.** §:23-25 diz que isto não é gargalo de velocidade; nada nos passos deve ser reescrito como se fosse.
