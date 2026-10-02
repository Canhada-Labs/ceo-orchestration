---
round: 3
archetype: QA Architect
skill: testing-strategy
agent_persona: Principal QA Architect
served_model: claude-opus-5-5
generated_at: 2026-10-02T04:15:00Z
scope: [W3]
inputs: [round-2/consensus.md §3(b), round-2/ADR-182-AMEND-1-draft.md @ 092377af, PLAN-194 §W3 e «Success criteria» @ 092377af, relatório da W0.6]
---

# PLAN-194 — rodada 3 (FINAL) — crítica do QA Architect (só W3)

> **Legenda.** **[disco]**: li no HEAD `092377af`. **[W0.6]**: tabela de células da medição W0.6.
> **[inferência]**: dedução minha. Só leitura: não rodei gates, suítes, `codex` nem `grok`.
> **Regra da rodada final:** NO-GO só por P0 ou afirmação FALSA; o resto vira condição de execução.

## Verdict

**ADJUST**

**W3: PROCEED** (`design-coherent`), com as condições de execução C-1 a C-9 abaixo.

- O AMEND-1 revisado atende cinco dos meus sete must-fix da rodada 2 (10, 11, 13, 14 e 16) e atende em parte os outros dois (12 e 15). O que falta está nos Checks do plano e em células de controle, não no desenho.
- Não achei P0 nem afirmação FALSA no PLANO. Achei UMA sobre-afirmação no RASCUNHO, o I8 («só confia em linhas gravadas por um verificador cujos bytes constam do manifesto ADR-192»). O mecanismo que a sustenta (H-07) compara o sha que a própria linha DECLARA. Um verificador editado pelo agente declararia o sha certo.
- Não a classifico como FALSA nem como P0. A via exige agente sob injeção executando código, que é a classe já declarada no R-5, e o mecanismo da §4.1 está descrito corretamente. Mas a via é mais FÁCIL que a declarada: editar um arquivo livre (oráculo 0) e rodá-lo por um comando permitido (W-05). Vira a condição C-1. Se o portador do VETO de Segurança a julgar P0, a W3 vai ao Owner.

## Summary (≤ 3 bullets)

- **O que melhorou.** A W0.6 foi integrada inteira:
  - `sigstore.verify` com política exata e ids imutáveis;
  - os dois bundles exigidos;
  - A-14 e A-15 como recusa;
  - vínculo pelo `subject` verificado, dos mesmos bytes;
  - lista fechada de hosts e caches novos;
  - tetos medidos e células F-01..F-09 de fronteira;
  - duas camadas de teste, guarda de rede dos filhos e censo por conjunto exato;
  - CLI com `--allow-auto-pin` e literal único `registry`.
- **Forte.** As duas afirmações FALSAS da r2 («stdlib-only» e «MESMO host») foram corrigidas e marcadas (§0). Os literais da W0.6 conferem com o relatório: OIDs `.1.15` = `965415649` e `.1.17` = `14957082`; ordem de publicação 0.160.0 −10 s e 0.156.1 +4,6 min. Nas células que pedem execução, o «[a medir na abertura]» vem com fallback pré-registrado (S-13, S-14, proxy do `node`).
- **Fraco.** Os Checks do plano divergem do AMEND-1:
  - usam `-k`, onde o AMEND-1 manda node id de classe;
  - deixam a camada 2 passar como SKIP verde;
  - o braço da CLI não confere o `status`.
- Os paths do pacote 1a no plano omitem o `package.json` e o arquivo de fixtures da camada 2. E a guarda W protege o REGISTRO, mas não o ESCRITOR dele (o verificador, livre).

## Risks

**R-QA3-1: W3, HIGH. O escritor do registro é editável pelo agente.**
- O verificador, o auxiliar `.js` e o lockfile têm oráculo 0 **[disco: `--is-canonical` = 0 nos três nomes propostos]**.
- O manifesto ADR-192 só é conferido na CI (`smoke-install.yml`, `release.yml`, `npm-publish.yml`, `ownership-nightly.yml`). Nenhum hook o lê em tempo de execução **[disco: grep em `.claude/hooks/`]**.
- O H-07 compara o `verifier_sha256` DECLARADO pela linha com o manifesto ADR-192. Um verificador editado localmente declara o sha esperado e grava confiança para qualquer binário. A W-05 permite invocá-lo, e o agente pode reverter a edição depois.
- O §10.4 põe o agente sob injeção DENTRO do modelo, então o I8 sobre-afirma.
- Mitigação: C-1.

**R-QA3-2: W3, MEDIUM. Os Checks deixam a camada 2 passar como SKIP verde.**
- O AMEND-1 §19.2 exige «SKIP = falha» na bateria do LAND e «SKIP DECLARADO e contado» no CI.
- Os Checks do plano (W3.4 e sucesso) rodam `pytest -q -k "… crypto_real …"`, que sai 0 com testes pulados. Rodado fora da bateria (sem `node` ou sem o sigstore instalado), o Check fica verde sem nenhuma prova criptográfica.
- Mitigação: C-2.

**R-QA3-3: W3, MEDIUM. A seleção por `-k` pode deixar células do hook fora do Check da W3.4.**
- O AMEND-1 §19.4 manda node ids de classe; o plano usa `-k "refusal or boundary or wiring or crypto_real or census or quarantine"` sobre os dois arquivos.
- Os testes H-01..H-13, C-01..C-02 e R-01 do `test_check_pair_rail_auto_pin.py` só entram se o nome ou a classe tiver uma dessas palavras.
- O censo prova que cada id tem ≥ 1 teste, não que esse teste está DENTRO da seleção do Check.
- Os seletores não são substring dos nomes dos módulos nem dos diretórios **[conferi]**, então não há o vácuo do `-k gc`. O risco é de OMISSÃO.
- Mitigação: C-3.

**R-QA3-4: W3, MEDIUM. A prova de «zero busca» na promoção (P-04) não tem controle positivo.**
- O ambiente do npm é montado com `env -i` (§4.4), que remove as variáveis de proxy. Se o proxy morto não for passado EXPLICITAMENTE ao npm, uma busca nova passaria, e a P-04 seria verde por vácuo.
- A W0.6 usou `--https-proxy` explícito (V-N2, V-N3).
- Mitigação: C-4.

**R-QA3-5: W3, LOW. Plano e AMEND-1 divergem nos paths do pacote 1a.**
- O auxiliar é `codex-auto-pin-verify.js` no plano e `codex-auto-pin/verify-sigstore.js` no AMEND-1.
- O plano lista só o lockfile; o `npm ci` exige também o `package.json`.
- O arquivo de fixtures da camada 2 não está no plano. Recontagem do plano: 6 paths; do AMEND-1: 8 no ramo (ii).
- Sem as fixtures no pacote, a camada 2 não roda.
- Mitigação: C-5.

**R-QA3-6: W3, LOW. Células de controle sem teste no censo.**
- O cruzamento do `/ceo-boot` (linha sem evento ⇒ ALARME; evento de quarentena sem linha ⇒ ALARME) e o `--check-installed` (§15) não têm id na §9.
- Faltam também a corrida de duas execuções concorrentes do verificador e as fronteiras do relógio (carência de 48 h; a política de nova tentativa do canário).
- Mitigação: C-6.

## Must-fix (blocking) — condições de execução da W3 (não reabrem o desenho)

1. **C-1 [W3; dono: CEO + portador do VETO; builder] Proteger o ESCRITOR do registro e corrigir o I8.**
   - (a) A guarda do pacote 1b (ou 1c) estende as células W às fontes do verificador: o `.py`, o auxiliar `.js`, o `package.json` e o lockfile. Edit, Write e escrita por Bash ⇒ BLOCK, salvo sob sentinela de cerimônia. Ou essas fontes entram em `_CANONICAL_GUARDS` (cerimônia de kernel). Controle positivo no formato EXATO do agente.
   - (b) O I8 passa a dizer «só confia em linhas que DECLARAM um verificador do manifesto ADR-192».
   - (c) Um teste DOCUMENTA o resíduo, como o H-13: um verificador sintético editado grava uma linha com o `verifier_sha256` forjado igual ao do manifesto, e o núcleo CONCEDE confiança. Isso põe a via no R-5 com nome.
   - (d) O check do `/ceo-boot` compara o sha EM DISCO do verificador, do auxiliar e do lockfile com o manifesto ADR-192 (evidência em repouso, sem custo no hook).
2. **C-2 [W3; dono: builder] A camada 2 obrigatória onde a prova conta.**
   - Os testes `crypto_real` FALHAM em vez de pular quando a variável de modo obrigatório estiver ligada. A bateria do LAND e o Check de sucesso a ligam; o Check da W3.4 no CI pode ficar sem ela, com o SKIP contado e impresso.
   - Controle positivo: `node` fora do PATH com o modo ligado ⇒ vermelho.
3. **C-3 [W3; dono: CEO, no plano] O Check da W3.4 segue o AMEND-1 §19.4.**
   - Node ids das classes dos DOIS arquivos, ou os dois arquivos inteiros.
   - O teste-censo também afirma que cada teste mapeado está na seleção do Check.
   - O W3.3 pode ficar com `-k "probe or canary"`: conferi que nenhum dos dois é substring dos nomes de módulo ou de diretório.
4. **C-4 [W3; dono: builder] Controle positivo da P-04.**
   - Com o cache do staging ESVAZIADO, a Fase 2 sob o proxy morto explícito tem de FALHAR. Se passar, o mecanismo não prende o npm e a «prova de zero busca» não vale.
   - O mesmo controle vale para a K-06 do kit.
5. **C-5 [W3; dono: CEO, no plano] Reconciliar os paths do 1a com o AMEND-1:**
   - o nome do auxiliar;
   - `package.json` + `package-lock.json` no ramo (ii);
   - o arquivo único de fixtures da camada 2 (bundles reais de ~15 KB cada + a raiz TUF fixada, com data);
   - o `gate-scripts-manifest.txt`.
   - Recontagem: 8 paths no ramo (ii), 7 no ramo (i). Onde divergirem, vale o rascunho, como na regra da W2.
6. **C-6 [W3; dono: builder] Células que faltam no censo:**
   - B-01 linha de aceitação sem evento ⇒ ALARME;
   - B-02 evento de quarentena sem linha ⇒ ALARME;
   - B-03 evento sem linha ⇒ só informativo;
   - B-04 `--check-installed` com membro alterado ⇒ divergência relatada;
   - A-26 duas execuções concorrentes do verificador ⇒ uma recusa e a cadeia `seq`/`prev_sha256` fica íntegra;
   - fronteiras com relógio INJETADO: carência 47:59:59 ⇒ não candidata, 48:00:00 ⇒ candidata; nova tentativa do canário antes de 10 min ⇒ recusa; 4.ª execução na semana ⇒ recusa;
   - o timeout do auxiliar (F-06) como constante canônica com teste.
7. **C-7 [W3; dono: CEO, no plano] O braço da CLI do Check de sucesso e do da W3.6 confere `status == "verified_auto"` E `pin_source == "registry"`, não só o segundo.**
   - Um teste fixa a forma EXATA do argv do Check: a flag DEPOIS do caminho do lançador. Hoje `_verify_pin_cli` toma `argv[0]` como lançador (`check_pair_rail.py:2502-2515`) **[disco]**, e a flag não pode virar caminho.
8. **C-8 [W3; dono: CEO, no plano] Os resumos da W3.4 usam os literais do AMEND-1 (`verified_auto` para o registro).**
   - O resumo do plano ainda escreve `verified` em células de registro.
   - É texto. Os testes seguem o AMEND-1 §8 e §11.
9. **C-9 [W3; dono: builder, na abertura] Medições «[a medir na abertura]» com vermelho e verde ANTES de o pacote valer, gravadas no LEDGER com substrato:**
   - S-13 e S-14 (`certificateOIDs`), ou o fallback pelo statement verificado;
   - o controle positivo da guarda de rede do `node` filho (§19.3), com o mecanismo trocado se o `fetch` nativo ignorar o proxy.

## Nice-to-have (advisory)

1. Rodar a camada 2 num job de CI com `node` e o lockfile do ramo escolhido (follow-up já previsto no §19.2). Fecha o SKIP do CI de vez.
2. Ao lado do arquivo de fixtures, gravar sha e data de captura de cada bundle e da raiz TUF, e um teste que acusa fixture trocada. Fixture é instrumento.
3. Antes do 1.º `--promote` real, um ensaio do verificador contra a 0.156.1 do manifesto em modo só-verificação (sem linha). Prova a Fase 1 inteira numa versão cujo sha já conhecemos (L-P1 = `0196e89f…`).
4. O Check de sucesso fica vermelho de novo se uma cerimônia futura puser no manifesto a mesma versão instalada (a fonte vira `manifest`). Dizer no texto que ele vale para o instante do fechamento da W3.

## Unseen by the original plan

1. A guarda W protege o arquivo do registro, mas o único ESCRITOR dele é um script livre que o agente pode editar e rodar (R-QA3-1).
2. O manifesto ADR-192 não tem conferência em tempo de execução: só a CI o lê. A proteção do instrumento vale para o que é PUBLICADO, não para o que roda localmente.
3. `env -i` remove as variáveis de proxy: a prova de «zero busca» depende de passar o proxy morto como opção explícita.
4. O Check com `-k … crypto_real` sai 0 com a camada 2 pulada.

## What I would NOT change

- O verificador fora de qualquer guard; o hook só-consulta, sem rede, por construção (H-12).
- `sigstore.verify` com política exata e ids imutáveis. Os dois bundles exigidos pelo verificador. O vínculo pelo `subject` VERIFICADO, dos mesmos bytes. A lista fechada de hosts. Os caches novos com asserção de vazio.
- As células F-01..F-09 todas como recusa, nunca INFRA. O mutante F-07 (sem política ⇒ S-11 VERIFIED ⇒ vermelho) é o controle não vácuo da identidade.
- As duas camadas de teste e a recusa explícita de provar A-14/A-15 com fixture sintética (§19.1).
- O censo por CONJUNTO EXATO (id removido ou desconhecido ⇒ vermelho).
- A promoção pelos bytes verificados com P-01 da árvore inteira. O H-13 como resíduo DOCUMENTADO por teste. O quiesce por `lsof`/`ps` sobre o caminho.
- A rota 2 invertida, com K-01 (espião de zero execução antes do oráculo) e K-02 (lançador plantado nunca roda).
- «Confiança no registro» como rota de ESCALATE, e não como ramo: a W0.6 é a evidência.

## Julgamento dos meus must-fix da rodada 2 (W3)

| MF r2 | estado | evidência |
|---|---|---|
| 10 — integrar a W0.6 | **ATENDIDO** | §4.2 V-4/V-5/V-6, §4.4 (lista fechada, caches, tetos medidos), §6 (literais da W0.6, ids imutáveis; S-13/S-14 a medir com fallback), §9.A (A-12 do verificador, A-14/A-15 recusa, A-16 ancorada no `subject` verificado, A-25) |
| 11 — células de fronteira | **ATENDIDO** | §9.F F-01..F-09, todas recusa (1): `node`, versão, sigstore, não-JSON, código, tempo, sem política (mutante S-11), cache quente, ambiente herdado. Falta a constante do F-06 (C-6) |
| 12 — duas camadas; SKIP = falha | **PARCIAL** | o AMEND-1 §19.1 e §19.2 estão completos, com o lugar pré-registrado e SKIP = falha na bateria; os Checks do plano saem 0 com a camada 2 pulada (C-2) |
| 13 — guarda de rede dos filhos | **ATENDIDO** | §19.3: proxy morto com controle POSITIVO e troca de mecanismo pré-registrada se o `fetch` nativo ignorar o proxy (C-9 mede); a P-04 de produção precisa do mesmo controle (C-4) |
| 14 — CLI com flag e literal único | **ATENDIDO** | plano: sucesso e W3.6 com `--allow-auto-pin` e `pin_source=="registry"`; W3.1 sem flag, com escopo; AMEND-1 §11 «Literal único». Ajustes: conferir `status` e a forma do argv (C-7) |
| 15 — arquivo nomeado e teste-censo | **PARCIAL** | AMEND-1 §19.4: os dois arquivos nomeados, censo por conjunto exato com W, K, F, P e H-13. O plano usa `-k` onde o AMEND-1 manda node id de classe, e o censo não liga id à seleção do Check (C-3); faltam as células B-01..B-04 e A-26 (C-6) |
| 16 — os dois ramos da decisão 3 | **ATENDIDO** | §7: ramos (ii) e (i) com testes pré-registrados (ii-1..ii-5, i-1..i-5); «confiança no registro» = ESCALATE (decisão do consenso r2 §2(i), que aceito); versão do sigstore como instrumento (§4.1, H-07) |

## Checks da W3: vermelho antes e verde depois? (`092377af`)

| Check | antes | depois | cumpre? |
|---|---|---|---|
| Sucesso, braço `pytest -k …` | vermelho (arquivos não existem) | verde | **sim, com C-2**: sem o modo obrigatório, fica verde com a camada 2 pulada |
| Sucesso, braço da CLI `--allow-auto-pin` + `pin_source=="registry"` | vermelho (0.156.1 dá `manifest`) | verde depois da W3.6 | **sim**, com C-7 (`status`) |
| W3.1 (sem flag, escopo «até o LAND») | verde por desenho (regra operacional) | — | sim; não é controle vermelho→verde e o escopo está escrito |
| W3.3 `-k "probe or canary"` | vermelho | verde | sim (seletores conferidos) |
| W3.4 `-k "refusal or … or quarantine"` | vermelho | verde | **parcial**: pode omitir células do hook (C-3) e passar com a camada 2 pulada (C-2) |
| W3.6 CLI com flag | vermelho | verde | sim, com C-7 |

O meu «verde por vácuo» da rodada 2 na W3 foi curado nos dois braços da CLI. O que resta é SKIP verde e omissão por seletor, os dois como condição de execução.

## Esforço (ADR-081)

| Item | Esforço |
|---|---|
| C-1 a C-8 | ~120-220k tokens dentro do orçamento da W3 (1,6-2,8 M), sem sessão extra |
| C-1(a) | +1 path na guarda do 1b/1c, ou cerimônia de kernel se for por `_CANONICAL_GUARDS` |
| C-9 | medição na abertura do 1a, sem cota paga |

Nenhuma espera externa nova.

Nenhum conteúdo lido trouxe instrução dirigida a mim; não houve injeção a relatar. Não li as críticas da rodada 3 dos outros arquétipos.
