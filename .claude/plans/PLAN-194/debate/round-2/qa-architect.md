---
round: 2
archetype: QA Architect
skill: testing-strategy
agent_persona: Principal QA Architect
served_model: claude-opus-5-5
generated_at: 2026-10-02T01:20:00Z
scope: [W2, W3]
inputs: [round-1/consensus.md, PLAN-194 @ 11c71a42, round-2/ADR-055-AMEND-4-draft.md, round-2/ADR-182-AMEND-1-draft.md, W0.6-medicao.md (2026-10-02T00:53Z–01:15Z)]
---

# PLAN-194 — rodada 2 — crítica do QA Architect (só W2 e W3)

> **Legenda.** **[disco]**: li no HEAD `11c71a42`. **[medido]**: medi eu, só leitura ou num rascunho
> descartável do scratchpad, apagado no fim. **[W0.6]**: tabela de células do relatório da W0.6
> (substrato: macOS 27.0.1, npm 11.16.0, sigstore 4.1.1). **[inferência]**: dedução minha.
> Não rodei gates, suítes do repositório, `codex` nem `grok`.
> Foco do meu domínio: **provas** — o controle vermelho→verde de cada onda, e o que o torna não vácuo.

## Verdict

**ADJUST**

- **W2: PROCEED** (`design-coherent`), com os must-fix 1–9 como pré-requisitos de EXECUÇÃO.
  - O desenho do AMEND-4 fecha os meus oito must-fix da rodada 1: nenhum `unlink` de `*.lock` em hook, journal removido na origem sob a própria trava, INV-NP por conjunto, mutantes, prazo provado com relógio falso e gatilhos com controle positivo.
  - O que resta é de prova e de texto, não de desenho:
    - dois Checks verdes por vácuo;
    - um Check vermelho por construção;
    - a calibração do driver do harness;
    - o N estatístico;
    - o esperado por célula sob a opção T1.
  - O VETO de Segurança e a vaga da W2.0 (decisão pendente 1) não são do meu domínio.
- **W3: RUN-ANOTHER-ROUND.** A W0.6 mediu fatos que mudam a matriz do AMEND-1:
  - a A-15 deixa de ser «não detectável» no ramo sigstore com política;
  - a A-03 («todo download no MESMO host») fica falsa diante do host TUF;
  - a camada de criptografia não se prova com fixture sintética;
  - a guarda de rede do Python não cobre o `node` filho.
  - E o Check de sucesso da W3 fica VERMELHO depois da W3.6 (braço da CLI sem flag).
  - Nada é P0; é a rodada 3 que integra a W0.6.

## Summary (≤ 3 bullets)

- **O que melhorou.**
  - W2: o AMEND-4 trocou um GC incerto por cura na origem com exclusão mútua intacta. Respondeu ao `truly_lost` morto com o INV-NP e o G6. Pré-registrou a W0.5 em 2³ + 4 células.
  - W3: o AMEND-1 tirou rede, download e execução de dentro do hook (I3, H-12), separou a CLI só-manifesto (C-01) e escreveu uma matriz de recusa ampla (A-01..A-24, H-01..H-12).
- **Forte.** As duas emendas citam o disco e enumeram células. O verde por vácuo da rodada 1 virou regra escrita («todo Check vermelho antes e verde depois»).
- **Fraco.** A regra está escrita, mas os COMANDOS dos Checks ainda a violam em seis lugares (tabela da §«Checks»). Na W3, a W0.6 chegou depois do rascunho: os campos «[a medir]» agora têm resposta, e três células escritas contradizem a medição.

## Risks

**R-QA2-1: transversal, HIGH. Checks verdes por vácuo, ou vermelhos por construção, em comandos do plano** (detalhe na §«Checks»).
- O W2.4 usa `-k gc`, que casa o NOME DO MÓDULO `test_spool_state_gc.py` e seleciona TODOS os testes do arquivo **[medido: pytest 7.3.0, arquivo sintético com 3 testes sem «gc» no nome ⇒ 3 coletados]**.
- O W2.0 (`pytest test_two_writer_chain.py`) passa HOJE: são 6 testes sequenciais **[disco]**.
- O braço de timeouts do Check de sucesso da W2 compara o texto `2026…` com o marcador literal `<ISO do LAND…>`. Em ASCII, `'2'` (0x32) < `'<'` (0x3C), então, esquecido o marcador, o `awk` conta 0 e o braço fica verde.
- O braço de contagem aplica o teto de 1.000 às travas. O AMEND-4 §6.3 (H2) diz que isso «reprovaria por construção» sob T1 (~15,8 mil travas por dia).
- O braço `--verify-codex-pin` do Check de sucesso da W3 vai SEM flag. Pela C-01 do AMEND-1, a CLI fica só-manifesto: verde hoje pelo manifesto do 0.156.1 e `mismatch`/1 depois da W3.6.
- Mitigação: must-fix 1, 2, 3 e 14.

**R-QA2-2: W2, HIGH. O controle S1 (entrega de decisão) mede um MODELO do harness.**
- O driver «reproduz a regra do harness: processo que passa do timeout é morto e a decisão é descartada» (AMEND-4 §4.2).
- O próprio AMEND-4 admite que a semântica do substrato não foi medida (§10, opção H).
- Se o harness lê a decisão no stdout antes do kill, o vermelho do HEAD é artefato do driver. Se espera o EOF herdado por filhos, o prazo não basta.
- Mitigação: must-fix 4.

**R-QA2-3: W2, HIGH. Sob T1, o critério pós-cura «razão p95 cheio/vazio ≤ 1,2» é vermelho por construção nas células com spool.**
- As travas ficam (~150 mil depois de um ciclo), e a fase 2 de quem tem conteúdo segue listando o diretório inteiro (`spool_writer.py:1273`) **[disco]**.
- Sem o esperado por célula pré-registrado, o resultado vai convidar a «relaxar» o critério depois. É o anti-padrão da casa (`EXPECTED_*` atualizado conscientemente, nunca relaxado).
- Mitigação: must-fix 5.

**R-QA2-4: W2, MEDIUM. O drain OPORTUNISTA dentro do hook, antes da decisão, não tem prazo.**
- O prazo cobre só a saída. O `audit_emit` drena em linha (`audit_emit.py:2791`) quando o spool próprio passa de 100 ms (`spool_writer.py:1098-1101`). Esse drain lista o diretório e pode esperar até 2,5 s na trava do journal de cada PID drenado (`:2276`) e 0,5 s na do spool (`:1374`) **[disco]**.
- É a MESMA classe («trabalho longo dentro de guard vira allow»), só que antes do stdout.
- Mitigação: must-fix 6.

**R-QA2-5: W2, MEDIUM. Depois da cura, a contenção fica invisível.**
- O braço «0 linhas `drain canonical lock timeout`» é verde por construção depois da cura. O próprio AMEND-4 §8.2 (G2) diz que «NENHUM chamador vivo a produz», e o estouro do prazo sai sem breadcrumb (§4.2 item 5).
- O `exit_deadline_skip` é «não observável diretamente» (§11, item negativo). O G3 só vê órfão com mais de 24 h.
- Um regime de pulo frequente (disco lento, adopter) deixa a perna 3 carregando tudo, sem sinal.
- Mitigação: must-fix 8.

**R-QA2-6: W3, HIGH. A matriz do AMEND-1 contradiz a W0.6 em três células, e falta a fronteira do verificador de assinatura.**
- **A-15:** o rascunho a deixa «não detectável» se a W0.6 não validar o mecanismo. A W0.6 validou: `sigstore.verify` com política recusa toda adulteração (S-06..S-09) e toda identidade divergente (S-03..S-05, S-12).
- **A-03:** «todo download no MESMO host» é incompatível com a busca TUF em `tuf-repo-cdn.sigstore.dev` [W0.6 §6.5].
- **A-12:** precisa ser do verificador. O `npm audit signatures` aceita a REMOÇÃO do atestado (V-P3, exit 0).
- Não há célula para `node` ausente, módulo sigstore movido ou de outra versão, saída malformada, timeout, nem chamada SEM política. Sem política, um atestado de outro repositório passa: S-11 VERIFIED.
- Mitigação: must-fix 10, 11 e 16.

**R-QA2-7: W3, HIGH. As fixtures prometidas não provam a criptografia, e a guarda de rede não vale para o subprocesso.**
- Um atestado sintético não carrega assinatura válida. Com ele, A-14 e A-15 só provam a FIAÇÃO (o Python respeita o veredito de quem verifica), não a verificação.
- A guarda de socket do Python (§17) não intercepta um `node` ou `npm` filho.
- Mitigação: must-fix 12 e 13.

**R-QA2-8: W3, MEDIUM. As células podem sumir em silêncio.**
- Os Checks W3.3 e W3.4 apontam só `test_check_pair_rail_auto_pin.py`, e os dois são o MESMO comando **[disco]**.
- Os testes do verificador (células A-xx e P-xx), «nomes a fixar», não estão em Check nenhum.
- Mitigação: must-fix 15.

## Must-fix (blocking)

### W2 — pré-requisitos de execução (não reabrem o desenho)

1. **[W2; dono: CEO, no texto do plano] Reconciliar plano e AMEND-4, e consertar os seletores.**
   - (a) **R2-2 aceita:** a W2.4 vira condicional, fora do pacote base, e o Check `-k gc` sai. Além disso, renomear o módulo de teste: `test_spool_state_gc.py` contém «gc», e `-k gc` o casa inteiro **[medido]**. O slug do ADR pode ficar (R2-7). Pode-se também usar `arquivo::Classe`.
   - O guarda de seletor confere que cada seletor casa SÓ os testes do próprio item, não apenas «≥ 1».
   - (b) A W2.3 do plano ainda admite «ou pelo dono na saída». O AMEND-4 §4.3 fixou «só a compactação»: um texto só.
   - (c) A célula (c) da W2.2 passa a ser «auxiliar de saída, chamado no atexit E no sinal» (AMEND-4 §4.1), não «no `_atexit_drain`».
   - (d) O Check da W2.4-bis (`test_ceo_boot.py` + `test_ceo_boot_enhanced.py`, 120 testes existentes) é verde HOJE **[disco]**. Ganha um seletor dos testes novos.
2. **[W2; dono: CEO] O Check de sucesso da W2 reescrito para cumprir a própria regra:**
   - (a) o teto de 1.000 conta SÓ journals (AMEND-4 H2). As travas são reportadas à parte (H3), sem limiar;
   - (b) o fluxo H1 com |D| entra AGORA, como script que lê os `pid` e `wall_ns` das linhas canônicas: eles sobrevivem ao drain (50/50 nas últimas linhas do log vivo) **[medido]**. Pré-registrar `|D|_min` (proposta ≥ 200); abaixo dele, reprova;
   - (c) o carimbo do LAND sai do commit do LAND, com formato ISO validado. Marcador literal ⇒ saída ≠ 0;
   - (d) o braço de timeouts passa a se chamar «guarda de regressão» (só pega um chamador forçado sem prazo), nunca prova de contenção;
   - (e) as regex são o texto do AMEND-4 §4.7 (`re.fullmatch` + `re.ASCII`). Hoje é `re.match` com `^…$` e `\d+` **[disco]**, contra o «MESMO texto nos três» do §4.7;
   - (f) o texto do critério promete «sai ≠ 0 com decisão perdida», e o comando não faz isso. Ou entra (a W0.5 grava um veredito lido pelo Check), ou o texto sai.
3. **[W2/W2.0; dono: builder da W2.0] O Check da W2.0 aponta o teste de barreira por node id e o censo AST.**
   - Hoje `pytest test_two_writer_chain.py` é verde ANTES da cura.
   - O LEDGER guarda a execução VERMELHA no HEAD antes do patch: é a obrigação de prova do RED-gate, com o comando e o sha.
4. **[W2; dono: CEO, W0.5] Calibrar o driver contra o harness REAL.**
   - Uma célula, num projeto descartável, com a versão do CC congelada (Q14), e dois braços: um hook PreToolUse sintético que imprime BLOCK e atrasa a SAÍDA além do timeout registrado, e o mesmo hook saindo rápido.
   - Registrar se a ação passou. Custo: 2 chamadas `claude -p`, sob o freio Q1.
   - Sem isso, S1 prova contra o modelo e o material assinado DECLARA essa limitação.
   - A mesma célula responde a opção H do §10.
5. **[W2; dono: CEO, pré-registro da W0.5] Estatística e esperado por célula sob T1.**
   - (a) Medir PRIMEIRO a taxa p̂ de perda de decisão no HEAD. O verde é 0 em N com limite superior de 95% ≈ 3/N ≤ p̂/10.
   - «0 em 30» só limita a perda a ≤ 10%. O p95 com N=30 é o 2.º maior valor: usar N ≥ 100 ou p90.
   - (b) Esperado por célula depois da cura:
     - sem spool: razão p95 cheio/vazio ≤ 1,2;
     - com spool e ~150 mil travas: decisão entregue e prazo respeitado, razão NÃO exigida (R-QA2-3).
   - (c) O critério numérico que dispara a T2, escrito ANTES de rodar.
6. **[W2; dono: CEO, W0.5] Uma célula para o atraso ANTES da decisão.**
   - Medir o drain oportunista dentro do hook, com ~150 mil travas e o diretório cheio: tempo entre a decisão tomada e o stdout escrito, com ≥ 9 concorrentes.
   - Se passar da margem, a mesma regra de prazo vale para o drain oportunista. Mesma classe, mesmo controle.
7. **[W2; dono: builder] Composição da cadeia, não só tamanho (R2-5, N ≥ 1.000).**
   - Mínimo por classe de escritor: ≥ 100 `agent_spawn` e ≥ 100 lotes de drain (linhas com `_drain_epoch`, que sobrevive no canônico) **[disco: `spool_writer.py:1939-1943`; 200/200 no log vivo]**.
   - ≥ 50 transições ADJACENTES entre classes, e ≥ 1 rotação no meio.
   - Mil elos de um escritor só é verde por vácuo para a condição 67.
8. **[W2; dono: CEO] Observabilidade que dispara.**
   - **R2-3: o G6 entra na W2.** Sem ele não existe detector de perda em PRODUÇÃO: o `truly_lost` e a reconciliação estão mortos (AMEND-4 §2.4).
   - **R2-4: sim**, e o check do boot conta spools de PID morto com conteúdo de QUALQUER idade, como taxa, não só acima de 24 h.
   - A W0.5 depois da cura registra a taxa de `exit_deadline_skip` por célula, com teto pré-registrado.
   - O G1 ganha controle positivo para o H1 (log sintético com D PIDs e journals de 0 byte ⇒ F > ε), não só para o H2.
9. **[W2; dono: builder] Guardas mecânicas das regras novas e células do sinalizador (R2-6).**
   - (a) No estresse, o inode de cada caminho `*.lock` fica ESTÁVEL do primeiro ao último uso. Inode trocado = alguém apagou e recriou: guarda viva de «nenhum hook apaga `*.lock`».
   - (b) O censo dos abridores de `audit-pending.*` vira teste. Hoje é um grep do redator (AMEND-4 §4.3).
   - (c) `.draining` próprio consumido por OUTRO drainer (a fase 1 pega `.draining` de PID vivo, `:1277-1317`) ⇒ o sinalizador segue ligado, a saída faz o drain completo, sem erro nem perda.
   - (d) Spool próprio em quarentena (`.malformed`) ⇒ uma tentativa só, sem laço.
   - (e) SIGTERM honra o caminho rápido e o prazo.

### W3 — para a rodada 3

10. **[W3; dono: CEO, no AMEND-1] Integrar a W0.6 ao texto.**
    - V-5 = `sigstore.verify` COM política (`certificateIdentityURI` = SAN da tag `rust-v<X.Y.Z>`, `certificateIssuer` = emissor do GitHub Actions), sobre o bundle que o PRÓPRIO verificador buscou. Nunca `npm audit signatures`: falso verde em V-T2, V-R1, V-P3, V-N1 e V-N3.
    - **A-15 = recusa** no ramo sigstore.
    - **A-12** do verificador, exigindo os DOIS bundles.
    - **A-03** com uma lista FECHADA de hosts (registro + TUF).
    - **A-16** ancorada no `subject` do bundle VERIFICADO, lido dos MESMOS bytes passados ao verificador.
    - Os tetos da §4.4 com os valores medidos [W0.6 §6.7].
    - A identidade da §6 com os literais medidos [W0.6 §4], inclusive os ids imutáveis do repositório e do dono.
11. **[W3; dono: CEO fixa, builder codifica] Células novas da fronteira do verificador de assinatura**, todas com recusa (1) e nunca INFRA:
    - `node` ausente;
    - módulo sigstore ausente, movido ou com versão ≠ a fixada;
    - saída não-JSON;
    - código ≠ 0;
    - tempo excedido;
    - **chamada SEM política** (mutante: o atestado real do `sigstore-js`, S-11, passa a VERIFIED ⇒ o teste fica vermelho);
    - **cache quente**: os caches do npm e do TUF nascem vazios no staging, com asserção no início (V-N1 e V-N3 provam o falso verde do cache quente).
12. **[W3; dono: builder] Duas camadas de teste, com o lugar de cada uma pré-registrado.**
    - **Camada 1 (CI, Python):** stub do subprocesso, que prova a FIAÇÃO fail-closed (REJECTED, crash, timeout e lixo ⇒ recusa).
    - **Camada 2 (criptografia REAL, offline):**
      - os bundles reais da 0.156.1 e da 0.160.0 (~15 KB cada, W0.6 §5) como fixtures, mais a raiz de confiança fixada;
      - os mutantes S-03..S-09, mais S-11 e S-12;
      - VERDE só no íntegro com a política certa.
    - A camada 2 roda no CI com `node` e sigstore em versão fixa, ou na bateria do LAND com **SKIP = falha** no conjunto exato. Um teste de criptografia pulado em silêncio é verde por vácuo.
    - Tarball e atestado sintéticos ficam para as células de forma (A-05, A-16, A-17), não para A-14 e A-15.
13. **[W3; dono: builder] Guarda de rede que vale para os filhos.**
    - Ambiente com `HTTPS_PROXY`/`HTTP_PROXY` apontando para um proxy morto (molde da W0.6, V-N2 e V-N4) e `NO_PROXY` vazio.
    - Controle POSITIVO: um fetch do `node` filho falha sob o ambiente.
    - A guarda de socket do Python continua para o hook (H-12).
14. **[W3; dono: CEO] Os Checks da CLI usam a flag e um literal só.**
    - O braço do Check de sucesso, o da W3.1 e o da W3.6 chamam `--verify-codex-pin --allow-auto-pin` (nome do AMEND-1 C-02) e afirmam `pin_source == "registry"` para uma versão FORA do manifesto.
    - O plano escreve `registro`; o AMEND-1, `registry`. Fica um literal só, o do código.
    - Sem a flag, o braço é verde pelo manifesto antes e vermelho depois da W3.6.
15. **[W3; dono: builder] Censo das células.**
    - Nomear AGORA o arquivo de teste do verificador e pô-lo no Check da W3.4.
    - Um teste-censo liga cada id da §8 a ≥ 1 teste: A-01..A-24, P-01..P-02, H-01..H-12, C-01..C-02, R-01..R-04 e as novas do must-fix 11. Célula removida em silêncio fica vermelha (molde `_EXPECTED_SITES` do `test_verify_counts.py`).
    - W3.3 e W3.4 com seletores DISTINTOS. Cuidado: `pin`, `auto`, `rail`, `pair` e `check` casam o nome do módulo `test_check_pair_rail_auto_pin.py`.
16. **[W3; dono: Owner decide, CEO pré-registra] A decisão pendente 3 mudou de natureza.**
    - Não é mais «aceitar a confiança no registro», e sim aceitar a dependência `node` + sigstore em versão e integridade FIXAS (ou o módulo interno do npm, que muda de lugar num upgrade) [W0.6 §6.6].
    - Pré-registrar os DOIS ramos, com teste por ramo:
      - (i) dependência aceita ⇒ A-14 e A-15 recusam pela camada 2;
      - (ii) recusada ⇒ A-15 aceita e DECLARADA, citando a W0.6 como evidência de que o comando do npm não a detecta.
    - A versão do sigstore entra no registro e no evento: trocar o verificador é «instrumento mudou».

### Transversal

17. **[transversal; dono: CEO] O meu MF-17 da rodada 1 fica PARCIAL.** A regra foi escrita, e os comandos ainda a violam. Itens 1, 2, 3, 14 e 15.

## Nice-to-have (advisory)

1. **[W2, R2-1]** Aceito a âncora no import, com o resíduo declarado. Um censo AST barato limita o resíduo: todo módulo de entrada de hook importa o `audit_emit` no topo, antes do `main`.
2. **[W2]** Teste dourado dos construtores de caminho (`_spool_path`, `_journal_path`, `_spool_flock_path`, `_journal_flock_path` para um PID de amostra), byte a byte contra o HEAD. Prova mecânica do «nenhum caminho muda» do AMEND-4 §4.6.
3. **[W2]** No estresse, afirmar que journals COM conteúdo foram produzidos antes do drain. Assim o H1 não fica verde só porque o journaling quebrou.
4. **[W3]** Teste honesto do resíduo da W0.6 §6.8: um executável secundário do pacote de plataforma (`bin/codex-code-mode-host`) alterado DEPOIS da promoção ⇒ o hook segue `verified_auto`. Documenta por teste o que o pin NÃO cobre.
5. **[W3]** Política de nova tentativa do canário (A-20 «inconclusivo») pré-registrada: número máximo e intervalo. Senão, «re-tentar até ficar verde».
6. **[transversal]** Um lint de seletores: `-k X` em Check do plano não pode ser substring do nome do módulo-alvo.

## Unseen by the original plan

1. `-k gc` seleciona o arquivo inteiro, pelo nome do módulo **[medido]**.
2. O marcador `<ISO do LAND…>` no `awk` faz o braço de timeouts contar 0 (`'2' < '<'`).
3. O Check da W2.0 e o da W2.4-bis passam antes de qualquer patch.
4. Sob T1, o critério de razão é vermelho por construção nas células com spool.
5. O drain oportunista dentro do hook é a mesma classe que o prazo de saída cura, e fica sem prazo.
6. A guarda de socket do Python não cobre os subprocessos `node`/`npm` do verificador.
7. W0.6:
   - o `npm audit signatures` dá falso verde com payload adulterado, com atestado REMOVIDO e sem rede com cache quente;
   - a A-03 do rascunho contradiz o host TUF;
   - o `@openai/codex-darwin-arm64` não existe como pacote: é ALIAS (W0.6 §5).
8. O literal `pin_source` diverge entre o plano (`registro`) e o AMEND-1 (`registry`).
9. Depois da W3.6, o braço da CLI do Check de sucesso fica vermelho com a W3 funcionando.

## What I would NOT change

- **AMEND-4:** nenhum `unlink` de `*.lock` em hook (T1). Remoção do journal na origem, sob a PRÓPRIA trava, com dois mutantes. INV-NP por conjunto e quarentena contada. Mutantes M-a..M-d. Prova do prazo com relógio falso e espião, sem tempo absoluto. Gatilhos G1–G6 com controle positivo. Aposentar o `truly_lost` às claras.
- **AMEND-1:** verificador fora de qualquer guard. Hook só-consulta e sem rede, por construção (H-12). CLI só-manifesto por padrão. Registro fora de `state/`. Evento HMAC antes da linha do registro (I6). Quarentena terminal. «Bloqueia até verificar ou reinstalar» no lugar de «segue na última verificada».
- **W0.6:** o método vira molde de teste: ambiente do npm montado do zero, proxy morto, envenenamento numa CÓPIA do cache e células S-* com mutantes de 1 byte.
- **A decisão pendente 4 (sentinela):** os dois ramos são aceitáveis para QA. O meu MF-12 pedia medir OU declarar, e o AMEND-1 declara NÃO AVALIÁVEL (§18.3, R-2).

## Julgamento dos meus must-fix da rodada 1

| MF | estado | evidência |
|---|---|---|
| 1 — exclusão mútua em `unlink` de trava | **ATENDIDO** | opção (b): nenhum `*.lock` em hook (AMEND-4 §4.4); controle de intercalação da remoção do journal com 2 mutantes (§4.3). Falta a guarda viva (must-fix 9a) |
| 2 — W0.5 pré-registrada | **PARCIAL** | 2³ + 4 células, substrato e vermelho escrito (§6.4; plano W0.5). Faltam a calibração do driver (4), o N estatístico e o esperado por célula sob T1 (5) e a célula pré-decisão (6) |
| 3 — fluxo com denominador; gatilho que dispara | **PARCIAL** | H1/|D| e G1–G6 com controle positivo no AMEND-4 (§6.3, §8.2). O comando do plano não tem H1 nem |D|, aplica o teto às travas e o braço de timeouts é vácuo depois da cura; o G6 só está proposto (2, 8) |
| 4 — invariante por conjunto, ≥ N, mistos, mutantes | **ATENDIDO** | §3.1, §6.1, §6.2. Falta a composição da cadeia (7) |
| 5 — células do caminho rápido | **ATENDIDO** | §4.1 (a)–(f). Faltam as células (c), (d) e (e) do must-fix 9 e o texto do plano (1c) |
| 6 — tabela de predicado | **ATENDIDO** | §5.2, §4.8, §5.3 (manifesto de hash). A W2.4 do plano ainda descreve GC em hook (1a) |
| 7 — convivência da relocação | **ATENDIDO (prejudicado)** | relocação fora; §4.6 |
| 8 — condição 67 | **ATENDIDO no desenho** | §7 (dentro da trava, depois do `rotate`; barreira; censo AST). Check vácuo (3); vaga com o Owner |
| 9 — Check afirma a origem | **PARCIAL** | AMEND-1 §10 e §17 corretos; o braço do plano vai sem flag e com literal divergente (14) |
| 10 — fixtures sem rede e sem binário | **PARCIAL** | §17 completo para a forma. Depois da W0.6: a criptografia pede a camada 2 (12) e a guarda de rede dos filhos (13) |
| 11 — matriz de recusa | **PARCIAL** | §8 cobre e excede a minha tabela (nova + sem rede ⇒ 1; registrada + sem rede ⇒ H-02 offline). Contradições e lacunas da W0.6 (10, 11, 16) |
| 12 — sentinela: medir ou declarar | **ATENDIDO** | declarada NÃO AVALIÁVEL (§18.3, R-2); decisão 4 com o Owner |
| 13 — sonda e argv por stub; ordem | **ATENDIDO** | V-7 → V-8 → V-9; A-19, A-20; §17; registro por rodada (§12) |
| 17 — Checks vermelho→verde | **PARCIAL** | itens 1, 2, 3, 14, 15 |

## Checks: vermelho antes e verde depois? (comandos do plano em `11c71a42`)

| Check | antes | depois | cumpre? |
|---|---|---|---|
| Sucesso W2, braço `pytest -k "…"` | vermelho (módulo novo) | verde | sim |
| Sucesso W2, braço de contagem (teto 1.000 nos 3 padrões) | vermelho | **vermelho por construção sob T1** (as travas crescem) | **não** |
| Sucesso W2, braço `awk` de timeouts | marcador literal ⇒ conta 0 | depois da cura, nenhum chamador vivo produz a linha | **não** (vácuo duplo) |
| W2.0 `pytest test_two_writer_chain.py` | **verde** (6 testes sequenciais) | verde | **não** |
| W2.2 `-k fast_path`, W2.2-bis `-k deadline`, W2.3 `-k origin`, W2.5 `-k invariant` | vermelho | verde | sim, com o guarda «só os do item» |
| W2.4 `-k gc` | vermelho | **verde com qualquer teste no módulo** | **não** |
| W2.4-bis `test_ceo_boot*.py` | **verde** (120 testes existentes) | verde | **não** |
| Sucesso W3, braço `pytest` | vermelho | verde | sim |
| Sucesso W3, W3.1 e W3.6: braço da CLI sem flag | verde (manifesto 0.156.1) | **vermelho** (`mismatch`/1 depois da W3.6) | **não** |
| W3.3 = W3.4 (mesmo comando) | vermelho | verde | não distingue os itens; os testes do verificador ficam fora |

## Respostas às perguntas do AMEND-4 (rodada 2)

- **R2-1:** aceita, com o resíduo declarado; nice-to-have 1.
- **R2-2:** aceita, com a ressalva de seletores do must-fix 1.
- **R2-3:** sim, na W2 (must-fix 8).
- **R2-4:** sim, contagem de qualquer idade e no máximo uma linha por execução do check.
- **R2-5:** os valores estão aceitos como pré-registro, com condições:
  - ε = 0,01 só com `|D|_min` e o vermelho do H1 MEDIDO no HEAD (esperado F ≥ 0,9), não inferido;
  - margem de 1,0 s e prazo de 2,0 s como valores iniciais. Regra pré-registrada: margem ≥ p99 medido (âncora + encerramento depois do atexit) × 1,5. Se não couber, encolhe o PRAZO, nunca a margem. A medição é declarada como da máquina do Owner: a casa já mediu 77 ms local contra 209–435 ms na CI para os mesmos hooks;
  - N ≥ 1.000 elos com a composição do must-fix 7;
  - os 2.000 `stat` estão ok;
  - o teto de 1.000 vale só para journals (e o Check do plano tem de seguir);
  - o Linux de vida longa como gatilho da T2 está ok.
- **R2-6:** a janela do sinalizador cobre os caminhos lidos no disco, com as células do must-fix 9.
- **R2-7:** neutro para QA quanto ao slug do ADR. O nome do MÓDULO de teste precisa mudar (must-fix 1a).

## Esforço (ADR-081)

| Item | Esforço |
|---|---|
| Must-fix 1–3, 14, 17 (texto e Checks) | ~40-80k tokens, no fechamento de emendas do plano, sem sessão extra |
| Must-fix 4 | 2 chamadas `claude -p` + ~30k tokens de harness |
| Must-fix 5–9 | ~150-250k tokens dentro do orçamento da W2 (0,9-1,7 M) |
| W3 para a rodada 3 (10, 11, 15, 16) | ~100-200k tokens de texto do AMEND-1 |
| Camadas de teste e guarda de rede dos filhos (12, 13) | ~200-350k tokens dentro do orçamento da W3 (1,3-2,5 M) |

Nenhuma espera externa nova. Nenhuma estimativa em «semanas» foi recebida para converter.

Nenhum conteúdo lido trouxe instrução dirigida a mim. Não houve injeção a relatar. O rascunho da sonda do `pytest -k` foi criado no scratchpad da sessão e removido com `shutil.rmtree` confinado.
