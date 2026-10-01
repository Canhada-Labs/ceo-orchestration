---
round: 2
archetype: VP Engineering
skill: architecture-decisions
agent_persona: "(nenhuma — perfil sintetizado da linha do skill-map em .claude/team.md:83)"
generated_at: 2026-10-01T03:13:56Z
---

> Regra de divulgação respeitada: formas só em prosa, sem string de comando; matriz privada
> citada só por id. Afirmações sobre código citam `arquivo:linha` conferido nesta rodada
> (HEAD `d572e374`/`96f2f635`). O que não foi sondado está marcado **hipótese**.

## Verdict

ACCEPT

## Summary (≤ 3 bullets)

- O plano revisto absorveu os meus nove must-fix da rodada 1 e os dos outros dois críticos: raiz re-identificada como decisão posicional sobre fatiamento ingênuo, passada única aditiva, reuso por leitura, piso de literais fora da posição do verbo, BLOCK em vez de ASK, divisão W1-ADR→W1a→W1b na mesma vaga, bateria de 9 suítes, prova N de N com classe do motivo, regra de parada do rail e residuais declarados pela forma.
- Do ângulo de arquitetura e sequência — que é o meu — o desenho agora é coerente: um só ponto de evento, um só caminhador, E3/E4 byte-idênticos na W1, orçamento realista (~0,8-1,5 M, coerente com o meu e com o do Critic-B) e colisões mapeadas sem choque novo com PLAN-194/PLAN-183.
- Não reabro nada: não há afirmação falsa nem P0. As minhas reservas restantes (contrato de cwd puxando a parte B para dentro de `main()`; A-8 como lockout de limpeza sancionada) viram recomendações nas respostas, não bloqueios.

## Risks

- **R-VP2.1 — MEDIUM — o contrato de cwd pode inchar a W2 e ampliar o raio de explosão para `main()`.**
  Descrição: a opção de «ler o `cwd` do stdin como o citation-gate lê o `transcript_path`» (plano `:466-468`) muda a assinatura de `decide_command` (`:3818`, hoje só `command`) e acrescenta parsing de stdin em `main()` — a parte B inteira passaria a depender de um campo influenciável pelo chamador. Conferido: `NormalizedEvent` não tem `cwd` (`_lib/contract.py:60-76`) e o citation-gate já lê o stdin cru em `:4167`, então o mecanismo existe, mas custa superfície em `main()`.
  Mitigação: na W2, fechar só o `cd` DENTRO do mesmo comando (a outra opção que o próprio plano oferece) e mandar o `cwd`-entre-chamadas para um FU; se o Owner quiser o `cwd` do stdin, então a divisão W2a/W2b vira obrigatória, não contingente (ver resposta 5).

- **R-VP2.2 — MEDIUM — A-8 pela forma é lockout da limpeza sancionada (lição S358).**
  Descrição: a regra «busca de arquivos com ação de remoção SEM predicado filtrante ≡ remoção recursiva» (OQ-8 opção a) ainda recusa a limpeza confinada que o agente DEVE fazer do próprio clone (memória `feedback-workflow-agents-must-clean-their-clones`), porque a separação segura/insegura é do ALVO (escopo do caminho de busca), não do VERBO — é máquina da parte B, ausente da W1b. Um BLOCK amplo aqui devolve o ENOSPC de ~200 GB.
  Mitigação: OQ-8 = opção (b) com FU nomeado (ver resposta 3).

- **R-VP2.3 — LOW — fail-closed de corpo de shell em grafia nova pode gerar falso-positivo em one-liner legítimo complexo.**
  Descrição: Thesis item 6 estende o fail-closed-cego do E3 (`:2307-2315`) a corpos de SHELL em grafias novas que não tokenizam. É o lado correto do invariante, mas um one-liner de shell legítimo com citação intricada pode ser recusado. Conferido: hoje o E3 já faz isso para o `-c` exato, então não é regressão — é extensão da mesma política à grafia nova.
  Mitigação: já coberta — `TestIndirectLegitAllow` (prova e) + replay offline (OQ-1) medem exatamente esta superfície; se o replay mostrar bloqueio legítimo acima do limite, a sub-forma cai para advisory pela regra da OQ-9. Sem ação nova.

- **R-VP2.4 — LOW — W1a e W1b tocam o mesmo arquivo de teste novo em sequência.**
  Descrição: as duas listam `test_check_bash_safety_indirect_exec.py` como path (`:371`, `:378`); a W1b adiciona linhas ao arquivo que a W1a criou. É legal (mesma vaga, sequencial, nunca em voo juntas), mas o controle N de N da W1b tem de rodar sobre o HEAD que já contém a W1a — o plano já diz isso (`:385-391`), só registro para o executor não medir a W1b contra o HEAD pré-W1a.
  Mitigação: já no plano; sem ação.

## Must-fix (blocking)

(nenhum — os nove da rodada 1 estão refletidos; as reservas acima são advisory)

## Nice-to-have (advisory)

1. Pré-registrar a divisão W2a/W2b como PROVÁVEL, não só contingente ao estouro de 400 linhas: a W2 herda seis responsabilidades (plano `:455-472`) e a de `cwd` sozinha pode cruzar `main()`.
2. FU declarado já na ADR-201: unificar o caminhador do E4 e o novo num caminhador parametrizado por predicado (2.ª ocorrência da forma «dois caminhadores») — com o registro do rail do E4 como baseline do custo.
3. A regra de rebaixamento para advisory (OQ-9) deve ser um FLAG por sub-forma lido do snapshot `trusted_env` (molde do piloto de citação `:991-1001` e do force-push `:660-679`), decidido ANTES do land pelo replay — nunca um interruptor que vira sob carga; e o estado advisory tem de EMITIR (senão a cobertura fica inauditável — ponto do Critic-B).
4. Quando a W1a/W1b e a W7a do PLAN-183 estiverem em voo, o pacote que landar por segundo registra no sentinel que rodou a bateria do outro sobre a árvore composta (já no plano `:416-420`; manter como item explícito do LAND).

## Unseen by the original plan

1. **A assinatura de `decide_command` é parte do contrato de teste.** Se a W2 passar a receber `cwd`, as suítes que chamam `decide_command(command)` diretamente (ex.: `test_check_bash_safety.py`) precisam de um default compatível com Python 3.9 — senão a mudança de assinatura quebra a bateria por fora da classe em teste. Pequeno, mas é a diferença entre W2 caber numa vaga ou estourar na hora do rail.
2. **O estado advisory já tem precedente de mecanismo** (`_env_guard_enforced`, `:3856`): a OQ-9 não inventa um terceiro veredito, reusa um que o hook já sabe emitir — vale dizer isso na ADR-201 para o rail não tratar advisory como contrato novo.

## What I would NOT change

1. A passada única aditiva na cauda de `decide_command`, com o laço legado e `_recheck_whole_command` byte-idênticos (Thesis item 2).
2. Reuso por leitura das tabelas do E4; E3/E4 byte-idênticos na W1 (Thesis item 3).
3. Piso de literais só na W2 (alvo de caminho); regra do verbo computado sem piso na parte A (Thesis item 4).
4. BLOCK com `destructive=True` + `reason_code` próprio por classe; ASK puro rejeitado (Thesis item 7).
5. Divisão W1-ADR (`PROPOSED`) → W1a → W1b na mesma vaga, com a prova N de N por pacote sobre o HEAD de antes DAQUELE pacote.
6. Regra de parada do rail (máx. 4 rodadas/pacote; NO-GO só por P0 ou afirmação falsa; nova grafia de residual já declarado vai ao anexo; P1 da mesma subclasse em duas rodadas ⇒ estreitar a afirmação).
7. Mensagem A3 e argv na W2 (a W1 deixa o E3 byte-idêntico); W2 sempre depois do land da W1b.
8. Bateria de 9 suítes, com `test_check_harness_config.py` e as duas de paridade do gêmeo YAML.
9. Espelhos `dist/`/`npm/` fora do commit, provados por `cmp`; W0 já, fora de janela de SIGN; W3 ortogonal, medir antes de ligar.

## Respostas da rodada 2

**1. Meus must-fix 1-9 da rodada 1 estão refletidos?**
- MF1 (tese de reuso errada — piso no verbo, `_scan_blob` não reutilizável): **atendido** — Thesis itens 3 e 4; alternativas rejeitadas `:208-210`.
- MF2 (escopo × prova de A-8/A-9): **em parte** — A-9 entra na W1b com controle ALLOW; A-8 depende da OQ-8 (fecho na resposta 3). O gap de prova só fecha de verdade quando a OQ-8 for decidida.
- MF3 (uma chamada aditiva na cauda, laço legado byte-idêntico, caminhador sobre o léxico do E3): **atendido** — Thesis item 2; W1a `:357-372`.
- MF4 (bateria com as suítes de paridade): **atendido** — Check da W1 com as 9 suítes `:328`; relação com o gêmeo na ADR-201 `:349`.
- MF5 (BLOCK com `destructive=True`, nunca ASK): **atendido** — Thesis item 7; alternativa ASK rejeitada `:214-217`.
- MF6 (reescrever a promessa como «eleva o custo; residual pela forma»): **atendido** — Goal `:138-144`; Success criteria `:609-613`.
- MF7 (divisão + regra de parada): **atendido** — W1-ADR/W1a/W1b `:327-379`; regra `:422-425`.
- MF8 (rota de limpeza sancionada fixada como ALLOW): **atendido** — W1-ADR `:350-351`; prova (h) `:405`.
- MF9 (costura do E3 — mensagem A3 e argv fora da W1): **atendido** — movidos para a W2 `:427-429`, `:455-465`.
Resumo: 7 atendidos, 1 em parte (MF2, pendente da OQ-8), 0 não atendidos.

**2. Divisão W1-ADR→W1a→W1b, tamanhos, vaga e regra de parada — corretos e exequíveis? Orçamento coerente com o meu?**
Sim. A divisão está certa: a ADR (`PROPOSED`, 1 path) precede o código; W1a e W1b tocam o mesmo hook mas em sequência na MESMA vaga, nunca em voo juntas — não viola «dois pacotes no mesmo arquivo». Cada pacote declara ≤ 3 paths e ≤ 400 linhas (`:355`, `:371-372`, `:378-379`). A regra de parada é exequível e é a correta para instrumento que prevê código por texto (o precedente E4 chegou a r8; 4 rodadas por pacote + a cláusula «P1 da mesma subclasse em duas rodadas ⇒ estreitar a afirmação» impede o loop da S354). Orçamento do frontmatter (`:9-10`): parte A total ~0,8-1,5 M em 3-4 sessões, W1-ADR ~80-150k, W1a ~350-650k, W1b ~300-600k — **coerente com o meu da rodada 1** (~0,8-1,5 M, 3-4 sessões) e com o do Critic-B (~0,7-1,3 M). O `budget_sessions` 5-7 fecha com W0 + replay + parte A + W2 + W3. Uma ressalva de exequibilidade, não de orçamento: se a W2 abraçar o `cwd` do stdin, ela estoura — por isso recomendo a resposta 5.

**3. OQ-8 (A-8): (a) ou (b)?**
**(b)** — tirar A-8 da W1 e de `TestIndirectDestructiveBlocks`, declará-la residual pela forma, com um FU nomeado (`PLAN-195-FOLLOWUP-search-delete-target-scope`) que a trate com a máquina de ESCOPO DE ALVO da parte B (piso de literais sobre a raiz da busca), não com regra de verbo. Por quê: (i) a separação segura/insegura de uma remoção por busca é do ALVO (a raiz e os filtros da busca), não do verbo — é problema da parte B, que não existe na W1b; (ii) a regra «sem predicado filtrante» da opção (a) ainda recusa a limpeza confinada do próprio clone que a lição S358 EXIGE (muitas vezes é uma raiz de busca estreita sem filtro de nome), devolvendo o ENOSPC; (iii) manter A-8 na prova forçaria uma afirmação falsa de «fechado» OU um lockout — removê-la da prova é a resolução honesta e satisfaz o invariante de não-permissividade (a passada não RECONHECE a forma, logo não a torna mais permissiva que forma direta nenhuma). A-9 (sobrescrita de dispositivo) fica na W1b, FP~0.

**4. OQ-9 (K1): aceito a proposta do CEO?**
Sim. Do ângulo de arquitetura: ASK puro não é um canal do hook (`Decision` só tem allow/block/rewrite-ask, `:299-322`; `ask` só sai com `updatedInput`, `:3947-3963`), e o estado advisory (emit + ALLOW) JÁ é um veredito que o hook sabe produzir — precedente `_env_guard_enforced` (`:3856`). Então BLOCK por padrão + `reason_code` próprio + kill-switch próprio + replay offline + rebaixamento PRÉ-REGISTRADO por sub-forma para advisory (nunca ASK) é sólido e não inventa contrato. Duas condições (que já estão como nice-to-have): o rebaixamento é um FLAG por sub-forma lido do snapshot `trusted_env`, decidido antes do land pelo replay, não um interruptor de runtime; e o estado advisory tem de EMITIR, senão a cobertura fica inauditável (ponto do Critic-B). Com isso, aceito — e, do meu lado, não há VETO a retirar (VP Engineering não tem veto, `.claude/team.md:83`).

**5. Colisões: a W2 cabe num pacote? Choque novo com PLAN-194/PLAN-183?**
A W2 herda seis responsabilidades (`:455-472`): mensagem A3, argv, segmento do verbo de busca no E3, contrato de cwd, caminhador/localizador compartilhado e `reason_code` de escrita canônica. Cabe num pacote SE o cwd for bounded ao `cd` intra-comando (hook ~150-250 + testes ~100-150 = ~250-400, no teto). Se o Owner quiser o `cwd` do stdin, isso cruza `main()` e a assinatura de `decide_command`, e aí a divisão **W2a (alvo computado + argv + reason_code) / W2b (mensagem A3 + segmento do verbo de busca)** deixa de ser contingente e passa a ser necessária — recomendo pré-registrá-la como provável agora (nice-to-have 1). Choque novo: **não há**. A W2 não tem vaga reservada e toca só o hook + testes + matriz; PLAN-194 (W1/W3/W2/W5c) e PLAN-183 (W7a/W7b) não tocam `check_bash_safety.py`. A única interseção real é a bateria compartilhada `test_check_harness_config.py` entre a parte A e a W7a do PLAN-183, já resolvida pela regra «quem landar por segundo roda a bateria composta» (`:416-420`). A colisão da W3 no `.claude/settings.json` com W6/W5c do PLAN-194 também já está ordenada (`:515-522`).

**6. Afirmação falsa ou P0 novo?**
Nenhum. Conferi no disco as citações que mudaram na r1: raiz posicional (`:378`, `:433-437`, `:456`); fatiador de quatro operadores (`:275`, `:526-584`); piso `_E4_GLOB_MIN_LITERALS=4` (`:2569`, `:2935`); E3 fail-closed-cego em corpo `-c` que não tokeniza ou passa de 16 KiB (`:2307-2315`); fact-gate só sob `destructive` (`:4166-4180`) e bloqueio canônico sem evento (`:3840`); argv com `break` depois do corpo (`:2335-2345`); varredura do verbo de busca em todos os tokens (`:2431`); `NormalizedEvent` sem `cwd` (`_lib/contract.py:60-76`); citation-gate lendo stdin em `:4167`; crash em matcher fail-open (`:4227-4233`). Todas verdadeiras. O achado C16 (divergência da regra de comentário entre o tokenizador do E3 e o dos pedaços do trio, com o `continue` fail-open de `:597-600`) está descrito pela forma e é consistente com o código. O plano marca como hipótese o que não foi sondado (formas diretas irmãs) — correto. Baseline medido hoje: as três suítes do hook + as duas de paridade = 207 passed, 1 skipped.

## Esforço (ADR-081)

Sem trabalho novo nesta rodada além da crítica (~15-25k tokens, 0 sessão própria). O orçamento da parte A segue o do frontmatter, que confirmei coerente: ~0,8-1,5 M tokens, 3-4 sessões, 2-3 assinaturas GPG do Owner (W1-ADR, W1a, W1b na mesma 2.ª vaga). Se a OQ-8 for (b), a W1b encolhe um pouco (sai A-8) e o FU de escopo de alvo soma ~150-300k numa vaga futura. Se a W2 absorver o `cwd` do stdin, +50-100k e a divisão W2a/W2b.
