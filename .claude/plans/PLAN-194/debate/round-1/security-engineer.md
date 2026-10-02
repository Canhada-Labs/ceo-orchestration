---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (Principal, auth/crypto VETO holder — ADR-052; supply chain, tamper-evidence, fail-closed matchers)
generated_at: 2026-10-01T23:58:00Z
plan: PLAN-194
waves: [W2, W3, W5c]
veto:
  W2: LEVANTADO
  W3: LEVANTADO
  W5c: RETIRADO (condicionado a MF-W5c-1 e MF-W5c-2 constarem da emenda 4)
---

# PLAN-194, debate L3 rodada 1: crítica do Security Engineer

> **Legenda.** **[disco]**: li no HEAD `6a9abb10` (árvore de trabalho da S361). **[plano]**: o plano ou a proposta afirmam e eu não refiz a medição. **[inferência]**: dedução minha, a conferir na abertura da onda.
> **Repositório público.** Este texto descreve classes de defeito e invariantes. Não traz receita de contorno de guarda.

## Verdict

**ADJUST** (posição geral).

- **W2: ADJUST, VETO LEVANTADO** (ADR-052, integridade do audit-log; `veto_floor` herdado do ADR-055-AMEND-3). Retiro quando MF-W2-1 a MF-W2-6 estiverem no `ADR-055-AMEND-4` e no plano.
- **W3: ADJUST, VETO LEVANTADO** (cadeia de suprimento, T-8 do `docs/CROSS-LLM-THREAT-MODEL.md`). Retiro quando MF-W3-1 a MF-W3-11 estiverem no `ADR-182-AMEND-1` em PROPOSED. Os dois braços que pedem decisão do Owner (MF-W3-3 e MF-W3-6) contam como resolvidos quando a decisão estiver escrita no AMEND-1.
- **W5c: ACCEPT com condições, VETO RETIRADO**, condicionado a MF-W5c-1 e MF-W5c-2 constarem da emenda 4 do ADR-149.
- **Transversal (L-1):** recomendo liberação POR ONDA. Uma onda que volta não segura as outras (MF-T-1).

## Summary (≤ 3 bullets)

- **O que o plano tenta:** tirar a latência do drain forçado da saída dos hooks (W2), aceitar versões novas do Codex por procedência em vez de assinatura humana a cada versão (W3) e registrar o Sonnet 5.5 no ADR-149 (W5c).
- **Pontos fortes:** o núcleo único fail-closed do ADR-182 fica preservado, e o manifesto assinado continua sendo a âncora dos cortes. A limpeza única da W2.6 roda fora do repositório, com as sessões fechadas e simulação por padrão. A W5c segue o formato mínimo da Amendment 2.
- **Pontos fracos:** na W3, dois braços inseguros estão em aberto: «sem rede ou sem atestado» pode cair em INFRA, e o desenho (a) põe rede e download de ~331 MB DENTRO do hook. «Conferir a assinatura» ainda não tem mecanismo viável só com stdlib. Na W2, apagar arquivo de trava dentro do hook quebra a exclusão mútua. A corrida do `audit_log.py` contamina justamente a métrica com que a W2 se prova. E o risco de segurança REAL da W2 (decisão de guard perdida por latência de saída) não tem controle vermelho→verde próprio.

## Risks

Do mais grave ao menos grave.

**R-SEC1 [W3]. Severidade: CRITICAL.** «Sem rede» ou «sem atestado» classificado como INFRA reabre a falha silenciosa que o ADR-182 fechou. No hook, INFRA NÃO executa o binário novo. O efeito é outro: o rail some e a escrita L3+ passa sem revisão. INFRA vira `None` em `_resolve_codex_bin` (`check_pair_rail.py:784-786` **[disco]**). O `None` vira `CodexUnavailable`, que devolve só `systemMessage`, ou seja, allow (`:1512-1520` **[disco]**). A tabela de braços está em `ADR-182-codex-payload-pin-enforcement.md:104-110` **[disco]**. A proposta diz «o binário novo e não verificado roda aberto» (§4.2, W3-5). Para o hook, a frase é imprecisa: ali o efeito é a ausência silenciosa de revisão. Os chamadores manuais é que de fato o executam.
*Mitigação:* todo braço «binário presente, mas não verificado» é SECURITY fail-CLOSED (MF-W3-1).

**R-SEC2 [W3]. Severidade: HIGH.** O desenho (a) («na 1.ª vez que o rail vê uma versão nova, o rail confere sozinho») põe rede, um download de ~331 MB e o parse de tar e JSON vindos da rede dentro de um guard PreToolUse com timeout de 210 s (`.claude/settings.json:285` **[disco]**). Um guard que estoura o timeout deixa a ação passar (lane `CC285-05`, citada pela própria W2 **[plano]**). A classe é a mesma da W2: trabalho longo dentro de guard vira «allow». Além disso, o hook é kernel (`check_arbitration_kernel.py`, lista de `_KERNEL_PATHS` **[disco]**) e passaria a processar entrada não confiável vinda da rede.
*Mitigação:* verificação em processo próprio, fora de qualquer guard. O hook só faz hash e consulta (MF-W3-2).

**R-SEC3 [W3]. Severidade: HIGH.** A «conferência de procedência» do desenho sugerido (W3-2) não verifica assinatura. `subject.sha512` e `dist.integrity` vêm do mesmo registro, então compará-los prova coerência, não autenticidade (L-8). A biblioteca padrão do Python não tem primitiva de assinatura de chave pública: `hashlib` e `hmac` são simétricos, e `ssl` só verifica cadeia dentro do handshake TLS **[inferência; conhecimento da stdlib]**. Implementar à mão a verificação de um bundle Sigstore (cadeia Fulcio, inclusão no Rekor, envelope DSSE) é o lugar clássico de bug de cripto. Pior: sem fixar a IDENTIDADE do construtor, um atestado SLSA válido emitido por OUTRO repositório também «confere».
*Mitigação:* MF-W3-3 (mecanismo ou decisão explícita do Owner) e MF-W3-4 (identidade fixada sempre).

**R-SEC4 [W2]. Severidade: HIGH.** O risco de segurança real da W2 é decisão de guard perdida, não contagem de arquivos. Um guard que já decidiu BLOCK e passa do timeout de 5 s na saída (lock canônico de 2,5 s mais a listagem de ~220 mil nomes; `spool_writer.py:2366`, `:1273` **[disco]**) entrega «sem decisão», e o harness deixa passar (lane `CC285-05` **[plano]**). O crescimento é LIMITADO pelo espaço de PIDs (~3 arquivos por PID; teto ~300 mil, lane `H-02` **[plano]**). Então o disco não é a ameaça; a latência é. Qualquer coisa que atrase a saída (diretório grande, contenção, disco lento) converte decisão em allow. Relocar ou apagar arquivos alivia o sintoma atual. Não cura a classe.
*Mitigação:* prazo na drenagem forçada de saída, derivado do orçamento do hook, com controle de ENTREGA de decisão (MF-W2-3).

**R-SEC5 [W2]. Severidade: HIGH.** Um GC de arquivos `*.lock` dentro do hook, mesmo com «trava obtida sem bloquear», quebra a exclusão mútua escritor × drainer. A sequência: o GC adquire a trava; um processo novo, com o PID reusado, abre o mesmo caminho e espera no MESMO inode; o GC remove o caminho e solta a trava; o processo novo trava o inode já órfão; um drainer abre o caminho, cria um inode NOVO e também «tem» a trava. A renomeação do spool sob a trava por PID (`spool_writer.py:1365-1370` **[disco]**) existe justamente para não roubar um append em voo. Sem exclusão mútua, uma linha em voo pode ir para um arquivo já consumido e apagado. Isso é perda de evento [inferência, mecanismo lido no código]. «PID reusado não basta» (W2.4) reconhece o problema, mas não fecha o caso de quem espera no inode.
*Mitigação:* não apagar travas dentro do hook. Curar na origem (MF-W2-2).

**R-SEC6 [W2, transversal]. Severidade: HIGH.** A corrida do `audit_log.py` contamina a régua da W2. O gravador lê o elo anterior, a chave e o HMAC FORA da trava (`audit_log.py:1262-1276` **[disco]**), contrariando o contrato explícito «MUST be called WITH the audit-log FileLock held» (`_lib/audit_hmac.py:473-483` **[disco]**). A trava só cobre o append (`audit_log.py:1283` **[disco]**), e é o mesmo `audit-log.lock` do drain (`audit_log.py:320-323`, `spool_writer.py:429-434` **[disco]**). Consequências: (a) o invariante W2.5 («`verify_chain()` íntegro» sob estresse) só se prova sem escritores `agent_spawn`, uma propriedade mais fraca do que a afirmada; (b) o gatilho de reversão do AMEND-3, «HMAC chain-break rate > 0.1% over 30 days» (`ADR-055-AMEND-3...md:139-140` **[disco]**), fica inavaliável; (c) a regra operacional «toda quebra num `agent_spawn` é presumida desta classe» (risco 11 **[plano]**) normaliza a quebra de cadeia, e isso desgasta a tamper-evidence. O alarme deixa de ser alarme.
*Mitigação:* MF-W2-1.

**R-SEC7 [W3]. Severidade: HIGH.** O registro automático vira uma 2.ª fonte de verdade. Se o validador do veredito de release, o `gen-envelope-ga.py` ou o kit o lerem, o artefato publicado perde a âncora humana assinada (manifesto da árvore tagueada, `ADR-182:143-164` **[disco]**). O Gate 4 do `pair-rail-gate.sh` reprova qualquer saída ≠ 0 (`.claude/scripts/local/pair-rail-gate.sh:199-219` **[disco]**). Um status novo sem contrato escrito quebra o pré-voo ou o alarga em silêncio.
*Mitigação:* MF-W3-5.

**R-SEC8 [W3]. Severidade: MEDIUM.** A aceitação automática não fica registrada de forma durável. Hoje a assinatura GPG do Owner é a evidência de cada re-pin. O `emit_generic` descarta, com só um breadcrumb, toda ação fora de `_KNOWN_ACTIONS` (`_lib/audit_emit.py:5238-5262` **[disco]**). Até o braço fail-closed atual, `pair_rail_codex_pin_mismatch`, é stderr apenas (`check_pair_rail.py:1201-1236` **[disco]**; `ADR-182:115-116`). Trocar uma assinatura por um breadcrumb é regressão de auditabilidade, e auditabilidade é a proposta de valor declarada do framework (`CLAUDE.md` §1).
*Mitigação:* MF-W3-6.

**R-SEC9 [W3]. Severidade: MEDIUM.** A sonda de subcomandos (W3.3/W3-8) EXECUTA o binário candidato (`codex <sub> --help`). Antes da verificação, isso significa executar um binário não verificado. E uma versão aceita com argv quebrado leva o rail a INFRA, isto é, fail-open: a classe A7, quando a remoção do `mcp-server` quebrou em silêncio **[plano]**.
*Mitigação:* ordem verificar → sondar → aceitar. Sonda reprovada impede a aceitação (MF-W3-7).

**R-SEC10 [W3]. Severidade: MEDIUM.** O `~/.codex/config.toml` global é superfície de ataque do revisor, não só deriva de qualidade. Ele pode trocar provedor e endpoint, ou seja, desviar o conteúdo revisado para outro destino. Pode também ligar servidores MCP e `memories`. Memória persistente é canal de injeção que sobrevive entre rodadas e entre repositórios: o Owner usa o app Codex em outros repositórios (Q2/Q11 **[plano]**). O argv atual omite `--model` (`_lib/codex_cli_shape.py:110`, `:351` **[disco]**) e não isola o config.
*Mitigação:* MF-W3-8.

**R-SEC11 [W3]. Severidade: MEDIUM.** Há chamadores que executam `codex` resolvido pelo PATH sem verificação. Um deles é um hook LIGADO: `codex_review_user_code.py:120-131` roda `codex exec` do PATH (**[disco]**), registrado em `Stop` (`.claude/settings.json:636-645` **[disco]**), com execução automática por opt-in. Ali o braço «decoy no PATH» do T-8 está aberto. O plano o lista entre as «rodadas manuais» (pergunta 6), mas ele é automático quando o opt-in está ligado. O `run-promotion-gate.py:196-212` também EXECUTA o binário, embora só com `--version` (**[disco]**).
*Mitigação:* MF-W3-10.

**R-SEC12 [W2]. Severidade: MEDIUM.** A migração de layout (W2.3) roda com versões misturadas. Um processo com o código velho trava `state/<arquivo>.lock`; um com o código novo trava `state/<subdir>/<arquivo>.lock`. São duas travas para o MESMO recurso, ou seja, nenhuma exclusão. A reconciliação nova pode não ver journals do layout velho (`spool_writer.py:2480` lista o diretório plano **[disco]**). O plano não trata isso (L-4).
*Mitigação:* MF-W2-4.

**R-SEC13 [W3]. Severidade: LOW-MEDIUM.** O artefato de plataforma é publicado como `@openai/codex@<v>-<platform>` (`ADR-182:173-175` **[disco]**). Pela sintaxe semver, isso é PRÉ-RELEASE. Um filtro ingênuo «sem pré-release» rejeita tudo; um filtro ingênuo «sufixo de plataforma» aceita alpha com sufixo.
*Mitigação:* gramática estrita (MF-W3-4).

**R-SEC14 [W5c]. Severidade: LOW.** A adoção pode, por arrasto do script, alargar o piso VETO (Sonnet não é elegível, A1.1 **[disco, via proposta §4.3]**) ou a allowlist customizada de um adopter no `upgrade.sh`.
*Mitigação:* MF-W5c-1 e MF-W5c-2.

## Must-fix (blocking)

Cada item traz a onda e o dono. «Builder» é o agente que o CEO despachar para o pacote da onda; «Security» é este arquétipo, no rail e na rodada 2.

**W2**

1. **MF-W2-1 [W2; dono: CEO (vaga, com o Owner) + builder].** A cura da corrida do `audit_log.py` landa ANTES do SIGN da W2, de preferência em pacote canônico próprio, ou DENTRO do pacote da W2 com controle vermelho próprio. A cura move chave, elo anterior e HMAC para dentro do `with FileLock(...)`, DEPOIS do `rotate_if_needed` (`audit_log.py:1283-1285`). Leva teste de N gravadores `agent_spawn` em paralelo com escritores `audit_emit` (vermelho no código atual) e `verify_chain()` íntegro (verde).
2. **MF-W2-2 [W2; dono: builder; Security revisa].** Nenhum hook apaga arquivo de trava (`*.lock`), a menos que TODOS os adquirentes passem a revalidar o inode depois de adquirir. Isso tocaria `_lib/filelock.py`, que é kernel (`check_arbitration_kernel.py:173` **[disco]**). A cura preferida é na origem: (a) o caminho rápido da W2.2; (b) a compactação remove, sob a própria trava, o journal que ficou vazio, em vez de reescrevê-lo com 0 byte (`spool_writer.py:2286-2297` **[disco]**). A remoção é segura contra descritor guardado porque o flush reabre o journal pelo caminho a cada vez, sob a mesma trava (`:940-971` **[disco]**). (c) As travas saem da listagem do drain (realocação) ou passam a um espaço limitado, sem remoção. O GC de travas fica SÓ na W2.6, com as sessões fechadas.
3. **MF-W2-3 [W2; dono: builder].** A drenagem forçada de saída ganha um prazo derivado do orçamento do hook. Estourar o prazo deixa o spool para a perna 3 (varredura do próximo drainer); isso deixa de ser «anômalo», e essa é exatamente a emenda semântica do AMEND-4. Controle vermelho→verde de ENTREGA DE DECISÃO: um guard que decide BLOCK, com várias saídas concorrentes e o diretório cheio, perde a decisão (vermelho, na W0.5) e passa a entregá-la (verde). O critério de latência atual do plano fica como critério secundário.
4. **MF-W2-4 [W2; dono: CEO (redação do ADR)].** O `ADR-055-AMEND-4` sai em arquivo próprio e precisa conter:
   - o invariante de não-perda reescrito, com as três pernas, dizendo quem cumpre a perna 2 quando o caminho rápido a pula;
   - a regra de versões mistas: LAND com todas as sessões fechadas, declarado no material assinado, MAIS leitura dupla de journals por uma versão; ou dupla trava durante a transição;
   - expressões regulares ANCORADAS para os 3 padrões, com PID só de dígitos;
   - a lista do que NUNCA se apaga: `.draining.*`, `.malformed.*`, `.quarantined.*`, `.test-origin.*`, `.tmp.*`, `*.compact.tmp`, journal com conteúdo, o journal agregado e a trava dele;
   - o caminho de reversão e os gatilhos pré-registrados: `truly_lost_7d ≥ 1`; qualquer quebra de cadeia atribuível à W2 depois de MF-W2-1; qualquer decisão de guard perdida no controle de MF-W2-3.
5. **MF-W2-5 [W2; dono: builder].** O estresse da W2.5 roda com TODOS os gravadores canônicos em paralelo: `agent_spawn` (`audit_log.py`), `audit_emit`, drainers oportunistas e forçados, saídas pelo caminho rápido, kill -9 no meio do drain e reuso de PID. Critério: contagem igual, `verify_chain()` íntegro e reconciliação com `truly_lost = 0`. Um órfão `.draining` deixado por um drainer morto é recuperado pelo drain do próximo `SessionStart`, mesmo com TODAS as saídas no caminho rápido.
6. **MF-W2-6 [W2.6; dono: CEO (script) + Owner (execução)].** O script da limpeza única:
   - resolve o state dir pelo resolvedor (`_lib/runtime_paths.py`), nunca por slug derivado à mão (ADR-001, marcador M4);
   - recusa diretório ou alvo que seja symlink;
   - remove relativo ao descritor do diretório, sem seguir link;
   - reexamina tamanho, tipo, contagem de links e família imediatamente antes de cada remoção;
   - roda em simulação por padrão e recusa rodar com sessão viva;
   - grava a contagem antes e depois no LEDGER, pelo mesmo método do critério de sucesso.

**W3**

7. **MF-W3-1 [W3; dono: CEO (ADR)].** Todo braço «binário presente, mas não verificado» é SECURITY fail-CLOSED: bloqueia as escritas L3+, nunca vira INFRA. Os braços são: sem rede, sem atestado, atestado inválido, identidade divergente, carência não cumprida, sonda reprovada, registro ausente ou corrompido. Registro ausente não é INFRA: significa só «nenhuma confiança extra além do manifesto». O texto da pergunta 5 e o controle W3.4(c) são emendados: «segue na última versão verificada» é inviável, porque o `npm i -g` sobrescreve o payload (L-9). O texto vira «bloqueia até verificar ou reinstalar a versão verificada».
8. **MF-W3-2 [W3; dono: builder].** Rede, download e tarball ficam FORA do hook PreToolUse e de qualquer guard. O hook só faz hash e consulta. O verificador roda em processo próprio, com diretório confinado, piso de `df`, tetos de tamanho (download E descompressão) e limpeza confinada (`CLAUDE.md` §4, regra S358).
9. **MF-W3-3 [W3; dono: builder (medição) + Owner (decisão)].** A W0 mede, com vermelho e verde, o verificador sigstore do PRÓPRIO npm num projeto-rascunho (não global, o que evita o `EAUDITGLOBAL`), com registro fixo e sem `.npmrc` do usuário. Vermelho: tarball adulterado. Verde: o pacote de plataforma íntegro. Se o mecanismo não servir, o Owner decide por escrito aceitar «confiança no registro via TLS» como resíduo nomeado no material assinado. Proibido: criptografia de assinatura escrita à mão, e chamar de «assinatura conferida» a comparação de dois campos da mesma resposta.
10. **MF-W3-4 [W3; dono: builder; Security revisa].**
    - A identidade do construtor fica fixada em constantes canônicas: repositório-fonte, caminho do workflow, ref de tag amarrada à versão, `predicateType` SLSA v1 e `subject` igual ao purl do pacote de PLATAFORMA, com digest igual ao `dist.integrity`.
    - A chave de aceitação é o sha256 do payload LOCAL igual ao sha256 do ÚNICO membro regular no caminho exato do tarball atestado. O membro é lido em fluxo: sem extrair para disco, sem symlink ou hardlink, sem nome duplicado.
    - O metadado local (versão do lançador) é só dica de busca.
    - A gramática de versão é estrita: base estável `X.Y.Z` mais o sufixo exato de plataforma do triple.
11. **MF-W3-5 [W3; dono: CEO (ADR) + builder].**
    - O registro fica no diretório resolvido por `runtime_paths`, FORA de `state/` (alcance do GC da W2), com modos 0700/0600. É só-acréscimo e guarda a evidência completa.
    - Leitores: só o núcleo do hook e a CLI. O validador de release, o `gen-envelope-ga.py` e o kit NUNCA o leem.
    - A CLI `--verify-codex-pin` distingue `verified` (manifesto) de `verified_auto`. O contrato de cada consumidor (hook, Gate 4 do `pair-rail-gate.sh`, release) fica escrito no AMEND-1.
    - O resíduo de mesmo UID é declarado (`CLAUDE.md` §5).
12. **MF-W3-6 [W3; dono: CEO (vaga do kernel) + Owner].** Cada aceitação automática vira evento DURÁVEL na cadeia HMAC, como ação registrada em `_KNOWN_ACTIONS`. Os campos: versão, triple, sha256 do payload, integrity, digest do atestado e identidade. Como o `audit_emit.py` é kernel, o pacote vai em série com a W1a do PLAN-195 (colisão condicional do mapa). O `pair_rail_codex_pin_mismatch` é promovido junto. Uma alternativa (por exemplo, evidência só no registro) exige decisão explícita do Owner, escrita no AMEND-1 como resíduo. O precedente do AMEND-3 (`:124-131`), que preferiu breadcrumb para não tocar o kernel, NÃO se aplica aqui: o evento substitui uma assinatura humana.
13. **MF-W3-7 [W3; dono: builder].** Ordem obrigatória: verificar, depois sondar, depois aceitar. A sonda da W3.3 só executa binário já verificado. Argv obrigatório reprovado (`exec`, `--sandbox`, `-o`, `--output-schema` e `--ignore-user-config`, se adotado) impede a aceitação, e o hook bloqueia. Nunca «aceita e cai em INFRA».
14. **MF-W3-8 [W3; dono: builder; modelo e esforço com QA/FinOps].** O argv do rail fixa modelo e esforço de forma explícita, e inclui `--ignore-user-config` se a sonda confirmar a flag na versão. Uma medição comprova que `memories` não carrega com a flag. O registro de cada rodada leva versão, sha do payload, modelo pedido e modelo servido (se o `session_meta` o expuser) e esforço.
15. **MF-W3-9 [W3; dono: CEO (ADR)].**
    - A carência é de no mínimo 48 h, contada do horário de publicação NO REGISTRO (não do 1.º avistamento local), e fica em constante canônica.
    - A `latest` é condição necessária, nunca prova de estabilidade.
    - Versão `deprecated` é recusada.
    - Nunca se aceita versão abaixo do piso do manifesto assinado.
16. **MF-W3-10 [W3; dono: builder + CEO (material assinado)].** ANTES da W3.6, os chamadores que executam `codex` automaticamente passam pelo núcleo de verificação ou ficam declarados no material assinado, com o estado de opt-in. São eles o hook `Stop` `codex_review_user_code.py` (no modo automático) e o `run-promotion-gate.py`. O daemon `app-server`, o `council-audit.js:325`, o `codex_invoke.py:193` e o `codex exec review` manual ficam declarados.
17. **MF-W3-11 [W3; dono: CEO].** Cortes: na 1.4.3, a W3.6 roda DEPOIS da W7, e a faixa do `codex-cli-pin.txt` fica intocada na W3. O T-8 do `docs/CROSS-LLM-THREAT-MODEL.md` (itens 1 e 5 da mitigação, `:328` em diante **[disco]**) é atualizado no MESMO pacote, porque a âncora de confiança do hook muda de «Owner + kernel» para «registro + Sigstore (ou só registro, por MF-W3-3) + identidade fixada». Precedente: o ADR-182 atualizou o T-8 no próprio pacote.

**W5c**

18. **MF-W5c-1 [W5c; dono: CEO (emenda 4)].** A emenda 4 diz que `claude-sonnet-5-5` NÃO entra no piso VETO, no pin de sessão nem em `.claude/agents/*.md`: a A1.1 é reafirmada. Um controle de igualdade de bytes compara o conjunto elegível a VETO antes e depois do pacote derivado.
19. **MF-W5c-2 [W5c; dono: builder].** A cláusula `superseded` (A2.2, item 5) é repetida, e o array de 8 ids da 1.4.2 entra na lista. O `upgrade.sh` nunca alarga nem estreita em silêncio uma allowlist customizada do adopter.

**Transversal**

20. **MF-T-1 [transversal; dono: CEO].** O `consensus.md` registra veredito e estado do VETO POR ONDA (L-1). Uma onda reprovada não segura as outras, e a W5c pode sair com o próprio PROCEED.

## Nice-to-have (advisory)

1. **[W3]** Rota futura dos cortes, como follow-up do kit da W7, não da W3: o kit re-pina o manifesto e a faixa por script, a partir da evidência do registro. O re-pin viaja na assinatura GPG que o corte JÁ tem e o validador fica intocado. É a «3.ª via» da W3-7: tira a cerimônia por versão sem trocar a âncora humana do artefato publicado.
2. **[W3]** Lista de revogação assinada (versões ou shas negados) em arquivo canônico, mais nova checagem de `deprecated` a cada execução do verificador.
3. **[W3]** Cópia endereçada por conteúdo do último payload verificado, para voltar atrás sem rede. Pede ADR próprio: executar de um armazém gravável pelo mesmo UID só é aceitável com o hash refeito antes de executar, como hoje (`ADR-182:94-99`).
4. **[W3]** Estender o pin automático aos adopters, onde hoje o pin resolve como INFRA, aberto (`CLAUDE.md` §4), em onda própria. Para eles seria ganho líquido de segurança.
5. **[W2]** Se algum breadcrumb novo nascer na W2, ele precisa de taxa limitada. O `audit-log.errors` (25.589 linhas **[plano]**) alimenta os detectores por contagem de linhas (precedente: `ADR-055-AMEND-3:104-122`).
6. **[W2]** A reconciliação de início de sessão também lista o diretório inteiro (`spool_writer.py:2480` **[disco]**; L-10). Pôr nela o mesmo prazo de MF-W2-3.
7. **[W5c, transversal]** O consenso rejeita crítica com VETO cujo modelo SERVIDO esteja fora do piso, porque o CC troca de modelo em silêncio quando a API recusa um (registro da W5c no LEDGER **[plano]**).

## Unseen by the original plan

1. **[W2]** De onde vêm os ~73 mil journals de 0 byte: o journal do PID existe (criado pelo próprio escritor), e a compactação do drainer o reescreve sem os triplos drenados, terminando com 0 byte, sem nunca removê-lo (`spool_writer.py:2262-2297` **[disco]**). A cura dos journals é LOCAL e segura (MF-W2-2 (b)); não precisa de GC externo.
2. **[W2]** O risco de segurança é a decisão perdida (R-SEC4), não o volume de arquivos. Como o crescimento é limitado pelo espaço de PIDs, o critério de sucesso por contagem é higiene. A cura da classe é o prazo na saída, que vale para qualquer causa de lentidão, inclusive uma induzida.
3. **[W2]** Apagar o caminho de uma trava por flock é a corrida clássica de inode (R-SEC5). O predicado «trava obtida sem bloquear» não cobre quem já espera no inode.
4. **[W2, transversal]** A corrida do `audit_log.py` torna inavaliável o gatilho de reversão do AMEND-3 (taxa de quebra de cadeia, `:139-140`). O AMEND-4 não consegue pré-registrar um gatilho de cadeia sobre uma linha de base suja.
5. **[W3, transversal]** Lição comum às duas ondas: trabalho longo dentro de guard vira «allow» pelo timeout do harness. Vale para a listagem de ~220 mil nomes na W2 e para o download de ~331 MB na W3.
6. **[W3]** No hook, INFRA não executa o binário novo: remove a revisão. A proposta descreve o efeito como «roda aberto». O efeito real é mais sutil e mais grave para a governança: a escrita L3+ passa sem par revisor e sem bloqueio (R-SEC1).
7. **[W3]** Armadilha de gramática: a versão do pacote de plataforma é pré-release pela sintaxe semver (R-SEC13).
8. **[W3]** Se o verificador usar a CLI do npm, o `.npmrc` (do usuário ou do projeto) e as variáveis `npm_config_*` podem redirecionar o registro para outra raiz de confiança. Falha de TLS por falta de cadeia de CAs no Python do sistema tem de ficar fail-closed. Desligar a verificação de certificado nunca é a saída.
9. **[W3]** O hook `Stop` `codex_review_user_code.py` é chamador AUTOMÁTICO, não «rodada manual» (R-SEC11).
10. **[W3]** O ADR-182 já previa um cache do hash do payload «via new amendment, not silently» e «fail-closed on any cache doubt» (`:214-218` **[disco]**). O registro do pin automático NÃO pode virar, de carona, um atalho por mtime ou tamanho que dispense o hash a cada invocação.
11. **[W3]** Escopo honesto da ameaça: o pin não protege a MÁQUINA. O Owner roda o app e a CLI do Codex fora do framework, e um binário malicioso já teria executado ali. O valor do pin é a identidade e a integridade do REVISOR cujo veredito o framework registra. O AMEND-1 precisa dizer isso, para não prometer mais do que entrega.

## What I would NOT change

- O núcleo único `verify_codex_payload()`, com hash-then-exec do caminho verificado e fail-CLOSED em entrada de segurança (`check_pair_rail.py:589-747`; `ADR-182:85-128`). O pin automático entra como MAIS UMA fonte de confiança dentro do mesmo núcleo, nunca como bifurcação.
- O manifesto continua canônico, guardado pelo kernel e assinado pelo Owner (`ADR-182:80-83`). Nenhuma automação escreve nele (premissa da W3-1).
- O validador do veredito de release fica intocado (membro do manifesto ADR-192), e os cortes continuam ancorados no manifesto da árvore tagueada.
- A regra operacional W3.1: Codex no 0.156.1, sem `npm update -g`, até o land e até o fim do corte W7.
- A W2.6 continua fora do repositório, com as sessões fechadas, simulação por padrão e journal com conteúdo NUNCA apagado.
- Mudança semântica ganha arquivo de emenda próprio (Q5), tanto `ADR-055-AMEND-4` quanto `ADR-182-AMEND-1`.
- A W5c no formato da Amendment 2: só o working set, com piso, fallback e pin intocados.
- A Q11: app fechado nas janelas de rail, `memories` desligado, e o pré-voo registrando sha do config, modelo e esforço.
- A sentinela que avisa sem travar (decisão do Owner), desde que o aviso seja durável (W3-9 abaixo).

---

## Respostas às perguntas da proposta (posição do Security Engineer)

### W2

- **W2-1 (criar menos, mover ou apagar).** Criar menos e apagar NA ORIGEM sob a própria trava, para journals (MF-W2-2 (b)). Mover, para as travas, com regra de transição (MF-W2-4). Apagar travas dentro do hook: NÃO (R-SEC5). Sozinho, o caminho rápido (W2.2) só resolve a parte da latência ligada aos processos SEM conteúdo próprio. Quantos processos de hook saem sem spool é um número que a W0.5 tem de medir, porque, se a maioria emite, o ganho é pequeno. A peça que basta para a segurança é o prazo de MF-W2-3.
- **W2-2 (quem recupera órfãos).** A condição do caminho rápido usa só o próprio PID, sem listar: spool próprio ausente ou vazio, buffer de journal próprio vazio, e nenhum drain falho registrado em memória neste processo. Os órfãos do diretório ficam com a perna 3: o drain oportunista de quem emite, o forçado de quem tem conteúdo e o forçado do `SessionStart`. O flush do buffer do journal (P1-2, `spool_writer.py:2573-2585`) continua no caminho rápido. O teste fica em MF-W2-5.
- **W2-3 (layout e migração).** Leitura dupla de journals por pelo menos uma versão. Para travas, dupla trava na transição, ou LAND com as sessões fechadas, declarado. O adopter recebe a mudança pelo `upgrade.sh`, possivelmente com sessão aberta: o material assinado declara isso.
- **W2-4 (predicado e executor do GC).** Dentro do hook, só a remoção do journal vazio pela compactação, sob a trava dele. Nenhum GC de travas. Se o debate mantiver algum GC no hook, ele roda fora do lock canônico, com teto de arquivos e prazo por execução, regex ancorada e reexame sob trava. O reuso de PID se trata pela regra «travas não se apagam no hook», não por heurística de PID.
- **W2-5 (absorver a corrida).** Sim, mas como pré-condição: o VETO da W2 fica levantado até a cura landar antes ou dentro do pacote (MF-W2-1). Prefiro pacote próprio antes, pelo raio de explosão menor e pelo rail independente. O estresse da W2 tem de incluir escritores `agent_spawn`.
- **W2-6 (ADR e limiar).** Arquivo próprio: a emenda contradiz a premissa «anômalo» do AMEND-3 (`:19`, `:89`). Para a segurança, o limiar decisivo é: decisão entregue, `truly_lost = 0` e zero quebra de cadeia atribuível. A contagem de arquivos (≤ 1%) fica como critério de higiene, relativo à linha de base do mesmo dia e medido com as sessões paradas. O gatilho de reversão pré-registrado é obrigatório.
- **W2-7 (observabilidade).** Com MF-W2-2 não há GC de travas no hook, logo não há evento novo nem toque no `audit_emit.py`. A W2.6 grava as contagens no LEDGER. Se sobrar GC no hook, a contagem agregada vai por canal forense já registrado, nunca um breadcrumb por arquivo.

### W3

- **W3-1 (onde fica o sha).** No diretório de estado do projeto resolvido por `runtime_paths`, fora de `state/`, só-acréscimo e com a evidência completa (MF-W3-5). Leem o núcleo do hook e a CLI; o passo 15 do release NÃO lê. Vale só para este repositório: adopters seguem em INFRA aberto, declarado (nice-to-have 4). Contra outro processo do mesmo UID não há fronteira, e o resíduo é o mesmo de `CLAUDE.md` §5. A defesa real fica na evidência durável na cadeia (MF-W3-6) e no registro de cada veredito.
- **W3-2 (assinatura só com stdlib).** Não é viável verificar a assinatura do atestado SÓ com a stdlib do Python. Caminho preferido: delegar ao verificador sigstore do npm em projeto-rascunho isolado, medido na W0 (MF-W3-3). Na falta dele, decisão do Owner aceitando a confiança no registro como resíduo nomeado. O download de ~331 MB roda no processo do verificador, nunca no hook (MF-W3-2). O vínculo atestado → tarball → payload sai inteiro da stdlib (`urllib` com TLS verificado, `tarfile` em fluxo, `hashlib`).
- **W3-3 (faixa).** Fica `>=0.128.0,<0.157.0` na W3. O corte da 1.4.3 declara o 0.156.1. Mexer na faixa é edição canônica atrelada ao kit de corte (nice-to-have 1), não à W3.
- **W3-4 (carência).** 48 h no mínimo, contadas do horário de publicação no registro, em constante canônica (MF-W3-9). A dist-tag é necessária e não suficiente, porque quem publica a move. Justificativa de segurança: a carência é a janela para a comunidade detectar uma versão maliciosa com procedência válida, que é o risco 4 do plano.
- **W3-5 (braço da recusa).** SECURITY fail-CLOSED em todos os casos de «binário presente, mas não verificado» (MF-W3-1, R-SEC1). «Seguir na última versão verificada» não existe sem uma cópia retida (L-9). A frase vira «bloqueia até verificar ou reinstalar».
- **W3-6 (manuais e daemon).** Ver MF-W3-10. Ganha prioridade o que executa SOZINHO (hook `Stop` com opt-in, `run-promotion-gate.py`). O resto é declarado.
- **W3-7 (cortes).** Na 1.4.3, W3.6 depois da W7 (MF-W3-11). Para os cortes seguintes, a 3.ª via: re-pin do manifesto dentro do kit, derivado da evidência e coberto pela assinatura que o corte já tem (nice-to-have 1).
- **W3-8 (sonda automática).** Sim, automática, DENTRO do verificador, depois da verificação e antes da aceitação. Reprovar bloqueia a aceitação (MF-W3-7).
- **W3-9 (gatilho do ADR-111 §2).** PRESERVAR, nem revogar nem substituir. O corpus da sentinela é o corpus travado do ADR-111, ou um subconjunto pré-registrado dele, para o gatilho de 5 pp ser avaliável. O resultado vira registro durável e aparece no `/ceo-boot`. Pacote L3+ cujo rail rodou sob versão com sentinela reprovada ou pendente declara isso no material assinado. A sentinela só roda sobre binário verificado e respeita os freios Q1/Q2 de cota.
- **W3-10 (modelo e esforço).** A escolha do id e do esforço não é do meu domínio (QA/FinOps), mas a segurança exige: explícitos no argv, id presente em `_VALID_MODELS` depois da W3b, e `gpt-6-astra` só depois do re-teste (Q11). `--ignore-user-config` entra se a sonda confirmar (R-SEC10). Uma cerimônia por GERAÇÃO de modelo é custo aceitável e até desejável: a identidade do revisor não deve derivar em silêncio. É bem menos frequente que uma cerimônia por versão da CLI, que é o que o Owner quis evitar.

### W5c (só o que toca segurança)

- **W5c-1.** Formato da A2, e só ele (MF-W5c-1). O `_ROUTING_TABLE` fica intocado.
- **W5c-3.** Sem objeção de segurança. O adapter falha ALTO (HTTP 400), o que é seguro, e nenhum código de produção força `tool_choice` fora dos próprios adapters: `git grep` acha `tool_choice` só em `_lib/adapters/live/claude.py` e `claude_batch.py` **[disco]**. Pôr o 5.5 na lista sempre-ligado (`claude.py:135-142` **[disco]**) depende da fonte primária, não de mim.
- **W5c-6.** Sim, repetir as duas cláusulas e incluir o array da 1.4.2 (MF-W5c-2).
- **W5c-2, W5c-4, W5c-5.** Fora do meu domínio. Sem objeção.

## Estado do VETO por onda

| Onda | VETO | Condição de retirada |
|---|---|---|
| W2 | **LEVANTADO** | MF-W2-1..6 no `ADR-055-AMEND-4` (PROPOSED) e no plano; MF-W2-1 landado ou dentro do pacote |
| W3 | **LEVANTADO** | MF-W3-1..11 no `ADR-182-AMEND-1` (PROPOSED); decisões do Owner de MF-W3-3/MF-W3-6, quando houver, escritas no AMEND-1 |
| W5c | **RETIRADO** | MF-W5c-1 e MF-W5c-2 constarem da emenda 4 do ADR-149 |

## Esforço adicional dos must-fix (ADR-081: tokens e sessões)

- **MF-W2-1:** 150–300 mil tokens com rail, 0–1 sessão (pacote canônico próprio; estimativa do plano).
- **MF-W2-3** (prazo na saída e controle de entrega de decisão): mais 100–200 mil tokens dentro da W2, sem sessão extra.
- **MF-W3-2/3/4** (verificador fora do hook e medição na W0): mais 300–600 mil tokens e mais 1 sessão. Cada medição baixa ~331 MB (orçamento de disco da regra S358).
- **MF-W3-6** (ação registrada no kernel): mais 100–200 mil tokens e 1 cerimônia de kernel, em série com a W1a do PLAN-195.
- **Resultado:** a W3 sobe de 0,8–1,5 M para ~1,3–2,5 M tokens, em 2–3 sessões, provavelmente em 2 pacotes ≤ 8 paths (verificador e hook). A W2 sobe ~0,1–0,2 M tokens, sem contar o pacote do MF-W2-1.
- **external_wait:** a carência de 48 h por versão nova, contada no relógio do registro npm.

## Evidência lida no disco (HEAD `6a9abb10`)

- `.claude/hooks/check_pair_rail.py`:
  - `:589-747`: núcleo `verify_codex_payload`. Braços INFRA em `:654`, `:677`, `:725`; mismatch em `:737`.
  - `:749-795` e `:784-786`: INFRA vira `None`.
  - `:1488-1520`: bloqueio do mismatch e allow do `CodexUnavailable`.
  - `:1201-1236`: o pin mismatch é só stderr.
  - `:2502-2524`: contrato de saída 0/1/3 da CLI.
  - `:439-466`: manifesto ancorado em `CLAUDE_PROJECT_DIR`.
- `.claude/governance/codex-cli-pin-manifest.json`: 0.156.1, um único triple. `.claude/governance/codex-cli-pin.txt:147`: faixa.
- `.claude/scripts/local/pair-rail-gate.sh:179-221`: o Gate 4 reprova qualquer saída ≠ 0.
- `.claude/hooks/_lib/codex_cli_shape.py:97-110`, `:339-352`.
- `.claude/hooks/codex_review_user_code.py:120-131`; `.claude/settings.json:285` (timeout de 210 s), `:636-645` (hook `Stop`).
- `.claude/scripts/run-promotion-gate.py:196-212`; `.claude/scripts/codex_invoke.py:193`; `.claude/workflows/council-audit.js:325`.
- `.claude/hooks/_lib/audit_emit.py:5238-5262`: ação desconhecida vira breadcrumb.
- `.claude/hooks/check_arbitration_kernel.py`: `audit_emit.py`, `audit_hmac.py` (`:137`), `filelock.py` (`:173`), `audit_log.py` (`:217`), `check_pair_rail.py` e `settings.json` (`:134`) são kernel.
- `.claude/hooks/audit_log.py`:
  - `:304-330`: a mesma `audit-log.lock` do drain.
  - `:1262-1276`: HMAC fora da trava.
  - `:1283-1285`: trava e rotação.
  - `:1315-1321`: sidecar dentro da trava.
- `.claude/hooks/_lib/audit_hmac.py:473-483`: contrato «MUST be called WITH the audit-log FileLock held».
- `.claude/hooks/_lib/spool_writer.py`:
  - `:265-266`: `state/` é filho do diretório da auditoria.
  - `:429-434`: lock canônico.
  - `:450-472`: nomes por PID.
  - `:940-971`: o flush reabre pelo caminho, sob a trava.
  - `:1259-1380`: varredura, PID vivo e rename sob a trava por PID.
  - `:2248-2297`: a compactação reescreve vazio e não remove.
  - `:2366`, `:2431-2436`: timeout forçado «anômalo».
  - `:2480`: a reconciliação lista o diretório inteiro.
  - `:2573-2585`: atexit.
- `.claude/adr/ADR-055-AMEND-3-opportunistic-drain-nonblocking.md`: `:11` (`veto_floor`), `:19`, `:22-23`, `:89`, `:104-131`, `:139-140`.
- `.claude/adr/ADR-182-codex-payload-pin-enforcement.md`: `:80-83`, `:85-128`, `:143-164`, `:166-184`, `:214-218`.
- `docs/CROSS-LLM-THREAT-MODEL.md`: §T-8 (`:328` em diante).
- `.claude/hooks/_lib/adapters/live/claude.py:91-142`, `:827-828`.
- `.claude/plans/PLAN-194/LEDGER.md:16-18`: estado da cadeia no T0.

Nenhum conteúdo lido trouxe instrução dirigida a mim. Não houve injeção a relatar.
