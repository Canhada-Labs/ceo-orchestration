---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (Principal, auth/crypto VETO holder — ADR-052; supply chain, tamper-evidence, confinamento de escrita do instalador)
generated_at: 2026-10-02T06:10:00Z
served_model_id: claude-opus-5-5
plan: PLAN-183
plan_commit: 304ec47805e5
waves_in_scope: [W7a, W7b, W8, W9, W10]
inputs:
  - .claude/plans/PLAN-183/debate/w7-round-1/proposal.md
  - .claude/plans/PLAN-183-adopter-fitness.md, seção «Waves S359» (:2036-2903; sem diff entre 092377af e 304ec478 no plano, em hooks/ e em scripts/)
wave_verdict:
  W7a: PROCEED
  W7b: PROCEED
  W8: PROCEED
  W9: PROCEED
  W10: PROCEED
p0_found: false
false_claims_found: "1 — PLAN-183:2130 «nenhuma versão entregou as fixtures» é falsa em geral (o upgrade.sh da v1.1.0 copiava .claude/hooks inteiro até e718cd89); não sustenta o desenho de nenhuma onda (a W7b planta o resíduo, :2473) ⇒ ajuste T-1"
veto:
  W7a: "não levantado"
  W7b: "não levantado; levanta-se no rail da W7b se o predicado morar em arquivo sem guarda canônica E fora do manifesto ADR-192 (MF-SEC-5)"
  W8: "não levantado; levanta-se no rail da W8 se um dos dois destinos novos for escrito sem _wbm_dst_refuses (MF-SEC-8, MF-SEC-10)"
  W9: "não levantado; levanta-se no rail da W9a se o aviso do P4 sair sem evento auditado E sem decisão escrita do Owner aceitando a perda forense (MF-SEC-11)"
  W10: "não levantado"
---

# PLAN-183, debate L3 w7-round-1: crítica do Security Engineer

> **Legenda.** `[disco]` = li no HEAD `304ec47805e5`. `[sonda]` = medido em diretório temporário meu, já apagado. `[não verificado]` = não conferi.
> **Repositório público:** classes e invariantes; nenhuma receita de contorno.

## Verdict

**ADJUST** (posição geral). Todas as ondas **PROCEED** (`design-coherent`), com condições de execução. Nenhum P0. Nenhum must-fix de DESENHO.

- **W7a (prioritária, autônoma): PROCEED, sem VETO.** O move restaura um controle positivo que hoje está MORTO em todo adopter (RED permanente treina a ignorar o canal). Não cria sítio de escrita no instalador: a W7a não toca `scripts/`. O literal destrutivo entregue é aceitável sob MF-SEC-1/2 (Q7a.6).
- **W7b: PROCEED.** O VETO fica pendurado no local do predicado (MF-SEC-5).
- **W8: PROCEED.** O VETO fica pendurado no confinamento dos dois destinos novos (MF-SEC-8, MF-SEC-10).
- **W9: PROCEED, com divisão W9a/W9b recomendada.** O VETO fica pendurado na trilha forense do P4 (MF-SEC-11).
- **W10: PROCEED.**
- **Uma afirmação falsa (L1)**, não estrutural: vira o ajuste T-1, não NO-GO.

## Summary (≤ 3 bullets)

- **O que o plano faz:** entrega por caminho entregue o que um gate entregue lê (W7a); um predicado de repo-fonte (W7b); higiene de arquivos semeados uma vez (W8); P4 a aviso e teto do RISKY DIFF (W9); validador de skills (W10).
- **Pontos fortes:**
  - recodificar o marcador em vez de isentar o caminho;
  - `--no-renames`;
  - ADR-001 e nunca `conftest.py`;
  - troca do `.mcp.json` só por hash exato;
  - `VERSION` sem escrita.
- **Pontos fracos:** os destinos novos da W8 não passam pelo predicado do PLAN-185. A chave nova da W9 pode reproduzir a classe que cura (prévia de 8 KB) e consolidar «revisado» sobre bytes que o Codex não viu. O P4 perde a dimensão forense que o ADR-116-AMEND-1 declara.

## Risks

**R-SEC1 [W9b, pré-existente no arquivo da onda]. HIGH.** Em modo AUTO (opt-in, `CEO_CODEX_USER_REVIEW_AUTO=1`), o conteúdo de arquivos NÃO rastreados vai ao Codex sem redação. O prompt monta o diff cru (`codex_review_user_code.py:125-131`), e o arquivo não chama nenhum redator. Nomes `.env|secret|credential|api[_-]?key` são classificados RISCO (`route.py:34-38`), o que torna esses arquivos MAIS prováveis de seguir. A leitura segue symlink: `os.path.isfile` e `open` (`:99-100`). [sonda] Um symlink não rastreado aparece em `git ls-files --others` e o conteúdo do alvo FORA do repositório é lido.
*Mitigação:* MF-SEC-14 (lstat, na W9b) e MF-SEC-18 (FU com dono para a redação).

**R-SEC2 [W9b]. MEDIUM.** «Revisado» cobre bytes que o Codex não viu. O diff é cortado em `DIFF_CAP` (`:117`). Um CLEAN sobre o diff cortado marca `reviewed` e aprova a assinatura INTEIRA do `review_loop` (`:334`). Com a chave nova de «conjunto completo», o hook passaria a gravar explicitamente como revisado o conjunto todo.
*Mitigação:* MF-SEC-15.

**R-SEC3 [W9b]. MEDIUM.** «Hash por path» calculado sobre o `_file_diff` herda o corte de `PER_FILE_CAP = 8000` (`:51`, `:100`) para não rastreados. Uma mudança depois de 8 KB fica invisível: é a mesma classe dos 16 KB que a W9 diz curar.
*Mitigação:* MF-SEC-14.

**R-SEC4 [W7b]. MEDIUM.** Hoje a decisão de ARMAR o PLAN-119 mora em `validate-governance.sh:1165`, pinado no manifesto ADR-192 (`gate-scripts-manifest.txt:2`). Levá-la para `check-rule-invariants.py` (oráculo 0, FORA do manifesto, medido) permite desarmar o gate sem cerimônia e sem detecção no CI. E renomear o ADR-001 já desarma em silêncio o `check-rule-invariants` hoje (`:242-252`, `ok: True`).
*Mitigação:* MF-SEC-5 e MF-SEC-6.

**R-SEC5 [W8]. MEDIUM.**
- `.mcp.json` em symlink ou hardlink: hash e cópia seguiriam o link, e a escrita cairia fora do alvo (classe F1 do PLAN-185).
- `_dispatch.md`: o gerador resolve a raiz por `CLAUDE_PROJECT_DIR` ANTES do cwd (`generate-dispatch.py:46-48`). Um upgrade rodado de dentro de uma sessão de OUTRO projeto escreveria lá. O `write_text` segue symlink (`:395`) e fica fora do censo bash.

*Mitigação:* MF-SEC-8 e MF-SEC-10.

**R-SEC6 [W9a]. MEDIUM.** O ADR-116-AMEND-1 põe o hook no kernel pela dimensão FORENSE: «Anti-CEO-overhead masking — forensic suppression» (`:224-225`; linha 43 da tabela, `:326`). O aviso do P4 sem evento é a 2.ª ocorrência; a 1.ª é o apply-step, «named follow-up» nunca fechado (`check_anti_ceo_overhead.py:683-693`). O ADR-127 mede «P4 fire count» (`:158`), que cairia a zero em silêncio.
*Mitigação:* MF-SEC-11.

**R-SEC7 [W7b]. LOW-MEDIUM.** Verde-vácuo por cwd. Raiz inexistente é pulada em silêncio (`check-test-audit-isolation.py:600-604`), e o WS-D2 lê `Path(".")` (`:609-610`). A opção (a) da Q7b.3 sozinha deixa o WS-D2 no cwd.
*Mitigação:* MF-SEC-7.

**R-SEC8 [W9b]. LOW-MEDIUM.** Os nomes de arquivo do adopter entram no `additionalContext` (`:301-303`), um canal adjacente a instrução. O teto reduz o volume, mas não fecha o canal (lição do PLAN-179 r22, `CLAUDE.md` §5).
*Mitigação:* MF-SEC-16.

**R-SEC9 [W9a]. LOW.** Prioridade P1>…>P4>P5 (`:499`). Um acerto velho do P4 transformado em aviso num evento Bash SOMBREIA um P5 bloqueante. É a classe S300 r17, já curada só no apply-step (`:698-711`, `skip_p4`).
*Mitigação:* MF-SEC-12.

**R-SEC10 [W7a]. LOW.** Literal destrutivo em adopter, tarball e plugin. No plugin, as fixtures não têm uso: o replay lê `<projeto>/.claude/hooks/...` (`check_harness_config.py:742`, `:783`) [lido, não executado].
*Mitigação:* MF-SEC-1 e MF-SEC-2.

## Must-fix (blocking)

Nenhum must-fix bloqueante de DESENHO. As condições abaixo são de **execução**: condição não cumprida reprova o SIGN do pacote dela, não o debate.

**W7a**
1. **MF-SEC-1 (Q7a.6).** A emenda do ADR-158 declara, pela FORMA, o invariante de consumo da fixture entregue:
   - lida só por parser JSON;
   - entregue por stdin, com argv fixo e sem shell, a um hook escolhido PELO GATE (`REQUIRED_REPLAY_CONTROLS`, `:149-153`; `:783`, `:791-792`);
   - nenhum campo da fixture escolhe programa, argv, env ou cwd (o campo `hook` das fixtures nunca é lido; `run_replay` lê só `expect` e `payload`, `:766`, `:775`);
   - o marcador é trocado em valores já parseados (`:671-678`), nunca no texto.

   `test_check_harness_config.py` (já no pacote) trava isso com controle vermelho: uma fixture com `hook` apontando outro script não muda o hook executado.
2. **MF-SEC-2 (Q7a.4).**
   - (a) Na bateria do LAND: staging npm + `npm pack --dry-run --json`, afirmando a PRESENÇA dos 3 `.json` em `_lib/harness_replay/`, com registro no material.
   - (b) A asserção estrutural do pacote também exige que nenhum segmento de `REPLAY_FIXTURES_REL` seja `tests` ou `fixtures`. São os nomes que `npm-publish.yml:321-322`, `install-npm.sh:120-121` e `build-plugin.py:342-345` descartam; o packlist gate (`:398`) só afirma AUSÊNCIA.
   - (c) Plugin, decidido na abertura:
     - excluir `harness_replay` por commit livre (`build-plugin.py`, oráculo 0, medido), no precedente `build-plugin.py:339-341`, que já tira amostras de ataque do plugin;
     - ou declarar no ADR que o plugin as carrega sem uso.
   - A asserção PERMANENTE de presença no `npm-publish.yml` (oráculo 1) vai a FU nomeado.
3. **MF-SEC-3 (Q7a.3).** O hook aceita SÓ a forma nova do marcador. A forma nova não colide com nenhuma chave de `build_sed_script` (`install.sh:2866-2900`). É defesa em profundidade: o escopo de substituição exclui `.claude/hooks/*` (`:2942-2943`), e o Check `cmp` da W7a já trava isso.
4. **MF-SEC-4 (Q7a.5).** Antes do SIGN da W7a, o FU do censo da classe «componente entregue lê por padrão caminho excluído» (A1-F4/F5, 2.ª ocorrência) existe com dono e posição.

**W7b**

5. **MF-SEC-5 (Q7b.1).** O predicado mora em arquivo à prova de edição na sessão.
   - **Preferido (b):** módulo em `.claude/hooks/_lib/` (oráculo 1), com CLI chamada pelo `.sh`. O `check-rule-invariants.py` importa o módulo.
   - **Aceitável (a):** SÓ se `check-rule-invariants.py` entrar no manifesto ADR-192 no MESMO pacote (o manifesto já é path da W7b).
   - Nos dois casos, erro ao avaliar o predicado ARMA o bloco ou dá FAIL nomeado; nunca pula.
6. **MF-SEC-6 (Q7b.2).**
   - (i) O controle positivo roda sobre o CHECKOUT REAL, nunca sobre um marcador plantado: um teste do repo-fonte afirma o predicado verdadeiro na raiz e o cabeçalho do bloco PLAN-119 na saída do validador completo. Renomear ou apagar o ADR-001 ⇒ CI vermelho, inclusive para o `check-rule-invariants`.
   - (ii) A forma dogfood sem o marcador (`.claude/hooks/tests` presente, ADR-001 ausente) dá WARN nomeado.
   - (iii) O ADR declara o uso MONÓTONO: o predicado só ARMA verificações, e nenhum consumidor pode relaxar uma guarda quando ele é verdadeiro. Senão, um marcador plantado num adopter viraria interruptor de proteção.
7. **MF-SEC-7 (Q7b.3).** Opção (b): o `.py` recebe a raiz explícita, e WS-C e WS-D2 resolvem dela. Zero raiz existente ou zero arquivo varrido ⇒ FAIL. Com o arming pelo marcador, a ausência do checker num repo-fonte vira FAIL (hoje WARN, `validate-governance.sh:1201-1204`), como já é o WS-A (`:1168-1171`).

**W8**

8. **MF-SEC-8 (Q8.4, Q8.1).** Para o `.mcp.json`:
   - `_wbm_dst_refuses "$TARGET" ".mcp.json"` ANTES de tudo; recusa ⇒ PRESERVED nomeado;
   - hash, backup e troca sobre os MESMOS bytes, com re-hash imediatamente antes de uma troca atômica (temporário no mesmo diretório + rename);
   - backup em `$BAK_DIR` (`upgrade.sh:1400`), nunca na raiz;
   - NÃO clonar a checagem local do `_refresh_schema_doc` (`:4379-4455`), que não testa hardlink. Chamar o predicado compartilhado (lição do PLAN-185: cópia local deriva).

   O TOCTOU residual é o já declarado no ADR-196 (`:154-156`).
9. **MF-SEC-9 (Q8.1, L9). Troca INCONDICIONAL à versão do Codex.**
   - Nenhum binário do PATH roda durante o upgrade.
   - Remover uma entrada que o Claude Code auto-executa do PATH REDUZ a superfície, e o template novo é o de toda instalação nova.
   - Aviso e `doctor.sh` imprimem só o nome do servidor e o comando de remoção, NUNCA o conteúdo: `env`/headers de MCP podem levar credencial.
   - O backup é livre de segredo por construção: só bytes com hash conhecido, e o template antigo usa `${OPENAI_API_KEY:-}` (`git show 3c2fb8e9^:templates/.mcp.json`).
10. **MF-SEC-10 (Q8.2, Q8.4).** Para o `_dispatch.md`:
    - roda o gerador da FONTE (`$SOURCE_DIR`), nunca a cópia do alvo (executar código do alvo no upgrade);
    - `CLAUDE_PROJECT_DIR="$TARGET"` explícito;
    - preferido: modo stdout (`generate-dispatch.py:384-388`), e o bash grava sob `_wbm_dst_refuses`, de forma atômica e com backup. O sítio fica no censo do PLAN-185, com o baseline regenerado (regra comum 3);
    - falha do gerador (agente custom malformado) ⇒ WARN nomeado, `_dispatch.md` intocado, upgrade segue.

**W9**

11. **MF-SEC-11 (Q9.1, Q9.3).** Cura da CLASSE (2.ª ocorrência): uma ação auditada de aviso, que cubra o Bash E o apply-step, pela cerimônia do `audit_emit` (oráculo 1, medido; daí a W9a separada). A alternativa é uma decisão ESCRITA do Owner, no material assinado, aceitando a perda forense e aposentando por texto a métrica do `ADR-127:158`. Sem uma das duas ⇒ VETO no rail da W9a. Manter o P4 como aviso permanente; tirar o predicado só junto com esta mesma decisão.
12. **MF-SEC-12 (Q9.1).** O aviso do P4 no Bash reusa a reavaliação `skip_p4`. Controle vermelho: janela com P5 + P4 e evento Bash ⇒ o P5 BLOQUEIA.
13. **MF-SEC-13 (Q9.3).** O dedup do override falha para o lado de EMITIR: estado ilegível ⇒ emite; o 1.º evento sempre sai; `session_id` vazio (`:770`) ⇒ sem dedup; nunca funde sessões. Vale para P1-P3 e P5, que seguem bloqueando.
14. **MF-SEC-14 (Q9.4).**
    - A chave por path é o hash do conteúdo COMPLETO (não rastreado) ou do diff completo do arquivo (rastreado), nunca da prévia de `PER_FILE_CAP`.
    - Symlink não rastreado nunca é seguido: `lstat`, com o alvo do link como conteúdo.
    - Formato do estado: estado antigo, corrompido ou de formato desconhecido ⇒ vazio ⇒ reavisa.
    - Escrita atômica, recusando path de estado em symlink (hoje `json.dump(open(...,'w'))`, `:166`).
15. **MF-SEC-15.** Só vira «revisado» o que entrou INTEIRO no diff enviado. Com truncamento, nada de `_approve_review_loop` para o conjunto.
16. **MF-SEC-16 (Q9.4).**
    - Valor de N: ≤ 10 nomes.
    - Cada nome higienizado (sem C0/C1, comprimento limitado).
    - Total ≤ 2.048 bytes, contagens primeiro.
    - Resíduo «canal de nomes» declarado pela FORMA. Se o rail achar contorno, o fallback é só contagens.
17. **MF-SEC-17 (W9).** A W9 não alarga o egresso: mesmo `DIFF_CAP`, nenhum conteúdo novo no prompt.
18. **MF-SEC-18 [dono: CEO].** Antes do SIGN da W9b, um FU com dono e posição para o egresso do modo AUTO (R-SEC1): redator do ADR-114 (`_lib/codex_egress_redact.py` existe) + `lstat`. Não bloqueia a W9; bloqueia ficar sem dono.

## Nice-to-have (advisory)

1. **[W7a]** O hook (canônico) pina o sha256 das 3 fixtures. Hoje a integridade do payload é só `expect` (`:766-773`), e os `.json` novos têm oráculo 0 (medido).
2. **[W7b]** A perna do purge parte de um alvo com um arquivo da árvore excluída editado à mão, e esse arquivo sobrevive (prova o hash-gate).
3. **[W8]** O NOTE do `VERSION` não ecoa conteúdo que não case semver (sequência de escape de terminal).
4. **[W9b]** Só contagens no contexto, com a lista num arquivo local que o usuário abre (fecha o canal por remoção).

## Unseen by the original plan

1. **[W9b]** Egresso sem redação no modo AUTO, através de symlink, de arquivos com nome de segredo (R-SEC1).
2. **[W9b]** A aprovação do `review_loop` sobre o diff truncado (R-SEC2).
3. **[W9a]** O ADR-116-AMEND-1 fixa a dimensão FORENSE do hook (o plano só procurou ADR que fixasse o bloqueio) (R-SEC6).
4. **[W8]** `CLAUDE_PROJECT_DIR` herdado redireciona a escrita do gerador (R-SEC5).
5. **[W8]** O precedente citado (`_refresh_schema_doc`) não testa hardlink: não serve de molde de escrita.
6. **[W7a]** No layout do plugin o replay não funciona; as fixtures ali são peso morto (R-SEC10).
7. **[W9a]** O P4 como aviso sombreia o P5 em evento Bash (R-SEC9).

## What I would NOT change

- **Recodificar o marcador** em vez de isentar o caminho no teste. A isenção calaria o teste, não o scan do install.
- **A forma do replay:** troca em valores parseados, `sys.executable` + argv em lista, sem shell, env hermético, programa vindo da tabela do gate.
- **O Check `cmp`** das fixtures instaladas. Ele também trava que a substituição textual do instalador nunca reescreva fixture entregue.
- **A W7a sem tocar `scripts/`:** nenhum sítio novo de escrita, nenhum baseline.
- **`--no-renames`** em toda listagem comparada no LAND.
- **ADR-001, nunca `conftest.py`**, como marcador.
- **A troca do `.mcp.json` só por sha256 exato.** São 1.204 bytes, com as gerações derivadas do git por teste; qualquer outro arquivo fica intocado.
- **`VERSION` sem escrita.**
- **P4:** recusa de subir o limiar ou isentar `.claude/**`. O P4 nunca foi barreira de segurança: casa só o token 0 (`:198`).
- **OQ-17:** não usar o manifesto para tirar do escopo o que o framework entregou.

---

## Respostas por pergunta (lente de segurança)

| id | resposta | razão |
|---|---|---|
| Q7a.1 | (a) 8+1, código primeiro | O fail-closed vive no código; o ADR primeiro descreveria uma pasta que ainda não existe. (c) exige exceção nova. |
| Q7a.2 | aditiva: SIM | O comportamento de segurança não reverte: as 4 condições RED ficam (ausente, ilegível, `expect` adulterado, não bloqueia). No adopter, um controle morto volta a funcionar, o que FORTALECE. A emenda declara que SUBSTITUI a pasta do item 1 da Decisão (`ADR-158:57-60`) e inclui o MF-SEC-1. |
| Q7a.3 | o hook aceita só a forma nova (MF-SEC-3) | A 2.ª regex (`test_install_sh_placeholders.py:84`) serve a um teste que exige que placeholders de arquétipo SOBREVIVAM (`:222-224`): não reprova. Não casar nenhuma das duas é critério de QA, não de segurança. |
| Q7a.4 | (i) partida mantida; (ii) sim, npm na bateria; (iii) sim (MF-SEC-2) | A W7a não cria canal novo de escrita no upgrade. |
| Q7a.5 | partida (só `REPLAY_FIXTURES_REL`) + FU com dono (MF-SEC-4) | — |
| Q7a.6 | **aceitável**, sob MF-SEC-1/2 | O hook entregue hoje já carrega 25 ocorrências do mesmo literal (`check_bash_safety.py`, `grep -c`, medido). A fixture é dado inerte, com marcador `_fixture`, e nenhum campo dela dirige execução. Risco residual: falso positivo de scanner de terceiros sobre o tarball [não verificado]. |
| Q7b.1 | (b) preferido; (a) só no manifesto ADR-192 | R-SEC4, MF-SEC-5. |
| Q7b.2 | SIM, desarma em silêncio | O controle de hoje não cobre a remoção futura; MF-SEC-6 (i)-(iii) cobre. |
| Q7b.3 | (b) | R-SEC7, MF-SEC-7. |
| Q7b.4 | sem objeção de segurança ao ADR novo | Ele carrega o uso monótono e o controle sobre o checkout real. |
| Q7b.5 | v1.4.2 + perna do purge | A população v1.1.0 (resíduo `.claude/hooks/tests`) já é coberta pelo resíduo plantado do teste de fronteira (`:2473`); nice-to-have 2. |
| Q8.1 | TROCAR por hash, sem sonda | A troca é função pura de um único fato (sha ∈ gerações derivadas do git), com a forma do hash-gate dos schema docs. Não consulta outra dimensão nem cria ramo local sobre `PROTOCOL.md`/`SPEC`/`.framework-version`: não reabre o `_ownership_verdict()`. Condições MF-SEC-8 e MF-SEC-9. |
| Q8.2 | gerar sim; MF-SEC-10 | Manual: sobrescrito com backup em `$BAK_DIR`. |
| Q8.3 | só aviso | Sem escrita, sem risco de posse. |
| Q8.4 | SIM, os dois pelo predicado | MF-SEC-8 e MF-SEC-10. Backup do arquivo de raiz em `$BAK_DIR/.mcp.json`. |
| Q9.1 | aviso: aceito | O P4 é heurística de delegação, não barreira. Fica como aviso permanente; MF-SEC-11 e MF-SEC-12. |
| Q9.2 | NÃO excluir nesta onda (partida) | Excluir pelo registro esconderia edição posterior em arquivo entregue. |
| Q9.3 | NÃO aceitar a queda silenciosa | MF-SEC-11. O dedup do override vale para P1-P3 e P5 (MF-SEC-13). |
| Q9.4 | MF-SEC-14 a MF-SEC-16 | — |
| Q9.5 | **dividir** | A W9a ganha a cerimônia do `audit_emit`. A W9b concentra o rail no egresso e no escopo do «revisado». |
| Q10.1 | **não fundir** | A W7b muda o armamento de um gate fail-closed; diluir esse rail custa mais que uma assinatura. A W10 roda `test_skill_grandfather_parser.py` e `test_squad_grandfather_cap.py`. |
| Q10.2 | exigir o diretório real (`resolve_skill`) | Aceitar qualquer prefixo é um verde-falso de referência. |
| Q10.3 | modo do parser, com teste | Falha de leitura ⇒ zero isenções, a direção segura de hoje (`validate-governance.sh:135`). O conjunto da política é IGUAL aos 5 do yaml depreciado (conferido): não alarga. A mensagem imprime a fonte («grandfather-cap policy»). |

## Lacunas L1–L12 (lente de segurança)

- **L1 procede: afirmação FALSA.**
  - `PLAN-183:2130` diz que nenhuma versão entregou as fixtures. `resposta-ao-campo-1.4.2.md:59-65,396-399` a estreita: o upgrade da v1.1.0 copiava `.claude/hooks` inteiro até `e718cd89`.
  - Ajuste **T-1**: a linha do A1 passa a dizer o mesmo que a resposta ao campo.
  - Não é estrutural.
- **L2:** resolvida pela Q7a.2 (aditiva).
- **L4 procede.** `check_harness_config.py:56` está no próprio pacote: corrigir junto (**T-2**).
- **L5:** procede só como QA; ver Q7a.3.
- **L6:** procede; respondida (MF-SEC-1/2).
- **L7:** procede e se AGRAVA pelo ADR-116-AMEND-1 (MF-SEC-11).
- **L9:** procede; respondida (MF-SEC-8 a MF-SEC-10).
- **L12:** conferido; nenhum diff entre `092377af` e `304ec478` no plano, em `hooks/` e em `scripts/`.
- **L3, L8, L10, L11:** fora da minha lente; L8 está coberta pela Q10.3.

## Esforço adicional (ADR-081)

| onda | custo | onde |
|---|---|---|
| W7a | ~20–40k tokens | dentro do pacote; o commit livre do plugin, se escolhido, ~5k |
| W7b | ~30–60k tokens | o módulo `_lib/` soma 1 path canônico |
| W8 | ~40–80k tokens | — |
| W9a | +1 sessão e ~100–160k tokens | ação auditada nova (cerimônia do `audit_emit`) |
| W9b | ~40–80k tokens | — |

O FU de egresso (MF-SEC-18) tem orçamento próprio. `external_wait` inalterado.

Nenhum conteúdo lido nesta rodada trouxe instrução dirigida a mim; não houve injeção a relatar.
