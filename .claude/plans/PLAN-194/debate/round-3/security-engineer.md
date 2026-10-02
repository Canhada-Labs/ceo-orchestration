---
round: 3
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (Principal, auth/crypto VETO holder — ADR-052; supply chain, tamper-evidence, fail-closed matchers)
generated_at: 2026-10-02T04:30:00Z
served_model_id: claude-opus-5-5
plan: PLAN-194
plan_commit: 092377af
wave_in_scope: W3
final_round: true
inputs:
  - .claude/plans/PLAN-194/debate/round-2/consensus.md (lista (b) 1–23)
  - .claude/plans/PLAN-194/debate/round-2/ADR-182-AMEND-1-draft.md (r3, commit 092377af)
  - .claude/plans/PLAN-194-maintenance-train-v1-4-3.md, seção W3 (commit 092377af; conferido idêntico ao HEAD)
veto:
  W3: "RETIRADO, condicionado a C-1 (decisão 3 do Owner escrita como ramo (ii) ou (i)) e às condições de execução C-2..C-7; «confiança no registro» ⇒ VETO segue LEVANTADO ⇒ ESCALATE-TO-OWNER"
wave_verdict:
  W3: PROCEED
p0_found: false
false_claims_found: "nenhuma que justifique NO-GO; o invariante I8 diz mais do que o mecanismo garante (corrigir o texto, C-4)"
---

# PLAN-194, debate L3 rodada 3 (final): crítica do Security Engineer (só W3)

> **Legenda.** **[disco]**: li nesta rodada no commit `092377af`. **[rascunho]**: linha do `ADR-182-AMEND-1-draft.md` r3. **[W0.6]**: medição de 2026-10-02, citada pelas células.
> **Regra desta rodada:** NO-GO só por P0 ou afirmação FALSA. O resto vai como condição de execução.
> **Repositório público.** Classes de defeito e invariantes; nenhuma receita de contorno de guarda.

## Verdict

**ACCEPT** (posição geral), com condições de execução.

- **W3: PROCEED** (`design-coherent`).
- **VETO RETIRADO, condicionado:**
  - **C-1:** o Owner escreve a decisão 3 como ramo (ii), o recomendado, ou ramo (i). A retirada vale no instante em que essa decisão escrita existir.
  - **C-2 a C-7:** condições de execução, conferidas no rail (V2) de cada pacote. Não pedem nova rodada.
- **Se a decisão 3 for «confiança no registro»:** o VETO segue LEVANTADO, e a W3 vai **ESCALATE-TO-OWNER** por múltipla escolha. Recusar `node` devolve o plano B (re-pin manual).
- **Nenhum P0.** Nenhuma afirmação FALSA no plano. Uma afirmação no rascunho diz mais do que o mecanismo garante: o invariante I8 (`:189-191` [rascunho]). Ela pede texto e uma guarda (C-4), não NO-GO.

## Summary (≤ 3 bullets)

- **O que mudou:** o AMEND-1 r3 trouxe a W0.6 para o desenho:
  - `sigstore.verify` com política exata (SAN, emissor e ids imutáveis);
  - vínculo pelos MESMOS bytes do bundle verificado;
  - lista fechada de hosts e caches novos;
  - promoção pelos bytes verificados, com P-01 da árvore inteira e quiesce;
  - guarda do registro contra escrita do agente;
  - rota 2 do kit INVERTIDA;
  - empacotamento (i)/(ii) com testes pré-registrados;
  - «confiança no registro» = ESCALATE.
- **Pontos fortes:** todos os oito MF-R2-W3 têm seção, célula e teste. As duas afirmações falsas da r2 («stdlib-only» e «MESMO host») estão corrigidas e sinalizadas no próprio texto (`:51-53`). A matriz ganhou as fronteiras F-01..F-09, a promoção P-01..P-05, a guarda W-01..W-06 e o kit K-01..K-06.
- **Pontos fracos (não bloqueantes):**
  - S-13/S-14 (ids imutáveis) ficam para a abertura, e o fallback descrito protege MENOS do que o texto sugere.
  - O verificador fica sob ADR-192, mas não sob guarda de edição: um agente que o edite e o execute concede confiança, e o I8 promete mais do que isso.
  - O plano diverge do AMEND-1 em seis pontos de execução.

## Risks

**R3-SEC1 [W3]. Severidade: MEDIUM.** Um verificador adulterado pelo próprio agente grava linha «válida». O H-07 confia na linha cujo `verifier_sha256`, `helper_sha256` e `sigstore_pkg_digest` sejam IGUAIS aos do manifesto ADR-192 (`:216-221`, `:526` [rascunho]). Esses valores são AUTODECLARADOS pelo processo que escreve a linha. O verificador, o auxiliar e o lockfile ficam sob o manifesto ADR-192 (`:210-215`), que detecta mudança de bytes no CI e no LAND, mas não impede edição na árvore durante uma sessão. A guarda do registro permite, por desenho, a invocação do verificador (W-05) e a escrita feita por ele (W-06; `:542-543`). A sequência é: o agente injetado edita o verificador (forma DIRETA de escrita, sem caminho calculado), o executa e restaura o arquivo. O resultado é uma linha que declara o sha legítimo e um evento HMAC coerente. Quem fica confiável é um binário que não passou pela verificação real. O I8 («só confia em linhas gravadas por um verificador cujos bytes constam do manifesto ADR-192», `:189-191`) promete mais do que o mecanismo entrega: o hook vê o sha DECLARADO, não os bytes que escreveram.
*Mitigação:* C-4.

**R3-SEC2 [W3]. Severidade: MEDIUM.** O fallback dos ids imutáveis protege menos do que o texto sugere. Se a política `certificateOIDs` não funcionar, o rascunho cai para os ids do STATEMENT verificado, «conteúdo assinado pelo mesmo certificado cuja SAN e emissor a política já fixou» (`:363-368`). A frase é verdadeira e ainda assim engana. O statement é AUTORADO pelo workflow que assinou. Num repositório recriado com o mesmo nome, quem roda o workflow obtém um certificado com a MESMA SAN (a SAN é o caminho, não o id) e escreve no statement os ids que quiser. Os ids das extensões OID do certificado, ao contrário, são postos pelo Fulcio a partir das claims do token OIDC, e é isso que barra a recriação.
*Mitigação:* C-2, com a ordem de fallback corrigida.

**R3-SEC3 [W3]. Severidade: LOW-MEDIUM.** Testes «offline» que talvez não sejam offline. O `fetch` nativo do `node` pode ignorar as variáveis de proxy (`:824-826` [rascunho], «[a conferir na abertura]»). Se o filho alcançar a rede, a camada 2 e as células de «sem rede» do TUF passam com dados vivos: são verdes que não provam o que dizem. O rascunho já prevê controle positivo e troca de mecanismo. Aceito na abertura, sob C-3.

**R3-SEC4 [W3]. Severidade: LOW.** O plano diverge do AMEND-1 na execução:
- **ordem da guarda (I8):** o AMEND-1 manda a guarda sair como pacote 1c, PRIMEIRO da fila, se não couber no 1b (`:617-618`, `:953-954`); o plano diz só «se couber; senão, item próprio» (plano `:311`, `:1072`), sem a ordem;
- **nomes:** auxiliar `codex-auto-pin/verify-sigstore.js` (`:200`) × `codex-auto-pin-verify.js` (plano `:313`, `:1075`); lockfile com nome próprio no plano;
- **`package.json` do ramo (ii):** o `npm ci` exige `package.json` e lockfile (`:393-396`), e o plano lista só o lockfile;
- **contagem do 1a:** 8 paths no rascunho (`:960`), 6 no plano (`:1079`), que omite o `package.json` e o arquivo de fixtures da camada 2;
- **mensagem do Gate 4:** no pacote 2 pelo rascunho (`:964`), no 1b pelo plano (`:1073`).
O AMEND-1 se declara a fonte (`:1021`).
*Mitigação:* C-5.

**R3-SEC5 [transversal, W2/W3]. Severidade: LOW-MEDIUM.** A família do log de auditoria pode não ter guarda contra escrita do agente. A rodada 2 achou isso «inconclusivo» (consenso r2 §0) e o rascunho o registra como «item próprio (follow-up nomeado)» (`:619-622`, `:884-885`). Está no domínio do meu VETO (integridade do log, ADR-052) e hoje não tem dono nem posição no plano.
*Mitigação:* C-6.

## Must-fix (blocking)

Nenhum must-fix bloqueante novo de DESENHO. As condições abaixo valem como **condições de execução**. Condição não cumprida reprova o SIGN do pacote correspondente, não o debate.

1. **C-1 [W3; dono: Owner].** Decisão 3 escrita como ramo (ii), o recomendado, ou ramo (i). «Confiança no registro» ⇒ VETO levantado ⇒ ESCALATE-TO-OWNER. A decisão entra no §22 do AMEND-1 antes do pacote de ADR.
2. **C-2 [W3, pacote 1a; dono: builder + Security no rail].** S-13/S-14 medidos na camada 2, na bateria do LAND do 1a, com SKIP = falha, ANTES do SIGN do 1a.
   - Com a MESMA política: S-13 (id do repositório errado) e S-14 (id do dono errado) REJECTED; S-02 e S-10 VERIFIED.
   - Se `certificateOIDs` falhar (ignora a extensão ou rejeita o legítimo), a ordem de fallback é:
     - (a) ler as extensões `.1.15` e `.1.17` do certificado-folha JÁ VERIFICADO, pelo parser X.509 da própria biblioteca sigstore (sem ASN.1 à mão);
     - (b) só então os ids do statement, DECLARADOS no material assinado como proteção REDUZIDA («repositório recriado com o mesmo nome passa»).
   - O texto de `:363-368` é corrigido nesses termos.
3. **C-3 [W3, pacotes 1a e 1b; dono: builder].** A guarda de rede dos filhos tem controle positivo VERMELHO (o fetch do `node` filho falha) ANTES de qualquer resultado da camada 2 ou de célula «sem rede» contar.
   - Se as variáveis de proxy não prenderem o filho: TUF só de cache sobre a raiz fixada nos testes, ou isolamento de rede do processo, com o mesmo controle positivo.
   - Em produção, o P-04 (promoção sem busca) usa as opções EXPLÍCITAS de proxy e o modo offline do npm (W0.6 V-N2/V-N4), não só o ambiente.
4. **C-4 [W3, pacote 1b ou 1c; dono: builder + CEO no texto].** O verificador `.py`, o auxiliar `.js`, o `package.json` e o lockfile ficam protegidos contra edição do PRÓPRIO agente (Edit/Write e Bash direto), pela guarda canônica ou pela mesma guarda W-01..W-04 estendida a esses caminhos, com controle positivo.
   - O I8 e o H-07 são reescritos para dizer o que o mecanismo prova: o hook confia em linhas que DECLARAM shas listados no ADR-192; não prova quais bytes as escreveram.
   - Se a guarda não couber, o resíduo «agente que edita o verificador e o executa concede confiança» entra no R-5 e no material assinado. Não pode ficar silencioso.
5. **C-5 [W3; dono: CEO, na abertura do 1b].** Reconciliar o plano com o AMEND-1, que prevalece:
   - a ordem I8 (1c primeiro);
   - os nomes do auxiliar e do lockfile;
   - o `package.json` no ramo (ii);
   - a contagem e os paths do 1a (fixtures da camada 2 incluídas);
   - o pacote da mensagem do Gate 4.
6. **C-6 [transversal; dono: CEO].** A lacuna de guarda da família do log de auditoria (log, chave, sal e sidecars) ganha item com dono e posição no plano antes do SIGN do 1b, com a pergunta conferida no disco (existe guarda? com que controle?). Não bloqueia a W3; bloqueia ficar sem dono.
7. **C-7 [W3; dono: Owner/CEO].** As decisões 4, 5 e 6 escritas no AMEND-1 antes do pacote de ADR (§22). A 6 segue com a minha recomendação: evento na cadeia. «Só no registro» apenas por decisão escrita (R-3).

## Nice-to-have (advisory)

1. **[W3]** Um job de CI com `node` e o material do ramo escolhido roda a camada 2 (o rascunho já o cita como follow-up, `:815-816`). Sem ele, a camada 2 só roda nas baterias de LAND.
2. **[W3]** O H-07 passa a aceitar também os shas HISTÓRICOS do verificador listados no manifesto ADR-192 de commits assinados anteriores, para não forçar re-verificação a cada troca benigna do instrumento. Só se o custo operacional aparecer; hoje «trocar o verificador ⇒ re-verificar» é a direção segura (`:219-220`).
3. **[W3]** O `/ceo-boot` recomenda o `--check-installed` também depois de um `npm i -g` cru detectado pelo `mtime` do diretório global, porque fecha o R-19 mais cedo (`:721-723`).
4. **[W3]** Registrar no LEDGER, com data e substrato, a versão do `node` usada na W0.6 (v26.3.0) como linha de base da constante de versão mínima (`:204-207`).

## Unseen by the original plan

1. **[W3]** **Autodeclaração do instrumento.** Toda identidade de instrumento gravada pelo próprio instrumento (`verifier_sha256`, `helper_sha256`, `sigstore_pkg_digest`) só vale se o instrumento for à prova de adulteração pelo agente. O ADR-192 detecta no CI; não impede na sessão (R3-SEC1).
2. **[W3]** **Quem põe os ids.** Os ids imutáveis só protegem se vierem do certificado (postos pelo Fulcio), não do statement (autorado pelo workflow assinante) (R3-SEC2).
3. **[transversal]** A família do log de auditoria pode estar sem guarda contra escrita do agente, e esse achado não tem dono (R3-SEC5).

## What I would NOT change

- **A política exata** de `sigstore.verify` (SAN com a tag da versão BASE, emissor exato, ids imutáveis), sobre os bundles que o próprio verificador buscou, e a proibição de `npm audit signatures` como decisão (`:240`, `:252-255`, `:353-360` [rascunho]).
- **O vínculo duplo:** o orquestrador relê o `subject` dos MESMOS bytes e exige igualdade com o que o auxiliar devolveu; o `dist.integrity` fica só como cruzamento (V-6, `:241`; A-16).
- **As fronteiras F-01..F-09**, todas recusa e nunca INFRA, inclusive F-07 (resposta com política efetiva ≠ pedida) e F-08 (cache quente) (`:492-504`).
- **A promoção** pelos bytes verificados, offline e sob proxy morto, com P-01 da árvore inteira e quiesce por CAMINHO, nunca `pgrep -f` (`:257-282`, `:506-514`).
- **A guarda W-01..W-06** com o limite honesto declarado (código que calcula o caminho) (`:534-543`, `:623-625`).
- **A rota 2 invertida** com K-01..K-06 e shim no `path` verificado (`:744-765`); o R-12 fora dos resíduos.
- **«Confiança no registro» = ESCALATE**, com a W0.6 como evidência (`:430-436`).
- **Os novos resíduos honestos:** R-16 (rollback exige rede), R-17 (irmãos na rota 2), R-18 (lista de hosts por configuração), R-19 (`npm i -g` cru de versão registrada) e R-20 (dependência de terceiro) (`:898-907`).

---

## Julgamento dos MF-R2-W3-1..8

| MF | estado | evidência |
|---|---|---|
| **MF-R2-W3-1** — `sigstore.verify` com política; os dois bundles; A-14/A-15 recusa; literais | **atendido**, com S-13/S-14 a medir na abertura (C-2) | política e literais: §6 `:351-382`; V-4 `:239` (os dois bundles, A-12 do verificador); V-5 `:240`; A-12 `:477`, A-14 `:479`, A-15 `:480` (recusa); proibições `:252-255`; alternativa G rejeitada `:989`. A correção do fallback é a C-2 |
| **MF-R2-W3-2** — empacotamento (ii)/(i); `signature_mode`; decisão 3 reescrita; «confiança no registro» ⇒ ESCALATE | **atendido** (a decisão em si é a C-1) | §7 `:384-436` (dois ramos com testes (ii-1..5) e (i-1..5)); identidade do instrumento na linha e no evento `:222-224`, `:591-592`, `:651-655`; §22 `:911-915`; plano `:2011-2013` (decisão 3 reescrita) e `:850` (ESCALATE) |
| **MF-R2-W3-3** — vínculo ao `subject` verificado; caches novos; 2.º host; tetos | **atendido** | V-6 `:241`; «Âncora do vínculo» `:379-382`; A-16 `:481`; §4.4 `:286-312` (lista fechada, caches com asserção, ambiente npm do zero, tabela de tetos com os valores da W0.6); V-0 `:235`; F-08 `:503`; R-18 `:902-903` |
| **MF-R2-W3-4** — promoção da árvore inteira ou dos bytes verificados; escopo honesto | **atendido** (os dois mecanismos) | §4.3 `:257-282`; §9.P `:506-514`; §2 `:136-141`; H-13 `:532` (resíduo documentado por teste); `members` na linha `:588`; R-19 `:904-905` declarado |
| **MF-R2-W3-5** — registro protegido contra escrita do agente, com controle positivo | **parcialmente atendido** | a guarda do REGISTRO está completa: §10.4 `:604-625`, §9.W `:534-543`, I8 `:189-191`, ordem 1b/1c `:617-618`. Faltam a proteção do INSTRUMENTO que escreve no registro e a correção do I8 (C-4), mais a ordem I8 no plano (C-5) |
| **MF-R2-W3-6** — rota 2 invertida, pré-condição da W3.6 | **atendido** | §17 `:744-765`; §9.K `:545-554`; §18 item 5 `:776`; plano W3.6 `:1155` e W7 `:1598`; R-12 retirado `:870-872` |
| **MF-R2-W3-7** — `SBOM.md`; «stdlib-only» escopado | **atendido** | §24 `:967-970`; frontmatter `:27`, `:33`; §4.1 `:197-203`; plano `:253`, `:316`; `CLAUDE.md` §3 só no fechamento, dentro da poda |
| **MF-R2-W3-8** — reconciliar plano, AMEND-1 e W0.6 | **parcialmente atendido** | feitos no plano: W3.4 sem «aceita e declarada» (`:1125`), identidade no `subject` verificado e ids imutáveis (`:1024-1026`), verificador «não livre» sob ADR-192 (`:1077`), linha do manifesto ADR-192 no mapa com a W3 (`:252`), decisão 3 reescrita (`:2011`). Restam as seis divergências de R3-SEC4 (C-5) |

Os MF-W3-1..11 da rodada 1 continuam atendidos pela tabela §26 do rascunho (`:994-1008`). A parte «W3.6 depois da W7» do MF-W3-11 segue refutada pelo disco (consenso r1 §2(c)), e a condição que impus a essa refutação, a rota 2 invertida, está cumprida (MF-R2-W3-6).

## Os dois pontos «a medir na abertura»

**S-13/S-14 (`certificateOIDs` para os ids imutáveis).** **ACEITO medir na abertura, como pré-condição do SIGN do pacote 1a**, nos termos da C-2. Motivos:
1. A ausência não é P0: a SAN exata e o emissor exato já barram atestado de OUTRO repositório e de outro emissor (S-03..S-05, S-12 medidos). Os ids cobrem só a recriação do repositório com o mesmo nome, que exige perder o nome da organização.
2. O pré-registro é bidirecional e por isso seguro de adiar. Se a biblioteca IGNORAR a extensão, o mutante S-13 fica VERIFIED e o teste vermelho; se ela REJEITAR o legítimo, S-02 fica vermelho. Os dois erros aparecem.
3. Exijo só a ordem honesta de fallback: certificado verificado primeiro, statement por último e declarado como proteção reduzida.

**O `node` filho e o proxy morto.** **ACEITO medir na abertura**, como pré-condição de qualquer resultado da camada 2 e das células «sem rede» contar, nos termos da C-3. É questão de HERMETICIDADE de teste, não de segurança de produção. O controle positivo pré-registrado torna a falha visível: se o filho escapar, o controle não fica vermelho e o builder troca o mecanismo. Em produção, o que prova «zero busca» na promoção (P-04) é o npm com opções explícitas de proxy e modo offline, comportamento que a W0.6 já mediu (V-N2, V-N4).

## Os resíduos novos da r3 (R-16..R-20)

| id | julgamento |
|---|---|
| R-16 rollback exige rede | aceito; o cache retido fica como follow-up |
| R-17 irmãos da versão do manifesto na rota 2 | aceito, declarado; o follow-up (kit chamando o verificador em modo só-verificação) é o certo |
| R-18 lista de hosts por configuração | aceito; o TUF é assinado, então um CDN comprometido não forja metadado |
| R-19 `npm i -g` cru de versão já registrada | aceito, com o nice-to-have 3 |
| R-20 dependência de terceiro (`node` + sigstore) | aceito; no ramo (ii) a raiz TUF inicial fica fixada pela integridade do lockfile, e as atualizações seguem a cadeia do TUF (registradas) |

## Esforço adicional (ADR-081)

C-2 a C-6: ~50–150 mil tokens dentro dos pacotes 1a, 1b e 1c, sem sessão extra. C-4 pode exigir a extensão da guarda canônica, que é lista de kernel. O 1b já é cerimônia de kernel (`check_pair_rail.py`), então o custo marginal é o da linha de glob e do teste. external_wait inalterado.

## Estado do VETO e veredito

| onda | veredito | VETO | condição exata |
|---|---|---|---|
| **W3** | **PROCEED** (`design-coherent`) | **RETIRADO, condicionado** | a retirada vale quando a decisão 3 do Owner estiver ESCRITA como ramo (ii) ou (i) (C-1); C-2..C-7 são condições de execução, conferidas no rail de cada pacote e pré-condição do SIGN do pacote correspondente. Decisão 3 = «confiança no registro» ⇒ VETO segue LEVANTADO ⇒ **ESCALATE-TO-OWNER** |

Nenhum conteúdo lido nesta rodada trouxe instrução dirigida a mim. Não houve injeção a relatar.
