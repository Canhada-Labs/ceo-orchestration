# Verificação adversarial — pair-rail parte 6 (rc.1, HEAD 4a1b448)

Verificador: security-engineer (rung 2). Método: leitura linha-a-linha no HEAD, `git show v1.3.0`,
reproduções isoladas em `clone6-1` (git clone --local) com `HOME` e `CLAUDE_PROJECT_DIR` em tmp
próprio — cadeia HMAC viva jamais tocada. Bateria: `test_injection_salt* + test_state_store*` no
clone isolado = **48 passed em 0,72 s**.

Canonicidade (oráculo `--is-canonical`): `state_store.py` 1 · `injection_salt.py` 1 ·
`audit_hmac.py` 1 · `audit_emit.py` 1 · `spool_writer.py` 1 · `ledger_provenance.py` 1 ·
`CHANGELOG.md` 0 · `docs/UPGRADE-PROCEDURE.md` 0 · `PROTOCOL.md` 1 · `README.md` 0.

## §0 Tabela-resumo

| id | conclusão do rail | classificação | regressão vs v1.3.0? | raio de dano (adopter real v1.3→v1.4) | canônico? | envelope / cura antes do GA / doc livre hoje |
|----|----|----|----|----|----|----|
| C1 | cutover do scratchpad sem migração nem aviso | **FALSO na metade «sem aviso»; POR-DESENHO no cutover** (CHANGELOG.md:121-130 + UPGRADE-PROCEDURE.md:63-81 divulgam /resume, handoffs e 2 rotas; migração JÁ é condição assinada da rc.1 — CHANGELOG.md:129) | não (é a cura da mistura, PLAN-182 W1) | continuidade de scratchpad para no upgrade até aplicar uma rota; dados intactos no disco (R1) | sim (state_store) | nada novo: manter a condição de envelope já declarada |
| C2 | first-mint sem exclusividade ⇒ salts divergentes | **PROCEDENTE; PRÉ-EXISTENTE re-exposto** (v1.3 byte-similar; docstring aceita a corrida com justificativa FALSA) | não em código; upgrade re-abre 1 momento de mint POR projeto | prompt_sha256 dos perdedores irreproduzível (R2: 5/5 rodadas, 6/6 salts distintos, 5 órfãos); cadeia HMAC intacta | sim | condição de envelope: mint com O_EXCL + perdedor relê (cerimônia antes do GA); doc livre: 2 linhas de mitigação operacional |
| C3 | `write_text` do marker segue symlink | **FORA-DO-MODELO-DE-AMEAÇA** (same-UID Tier-2, threat-model.md:1745-1761); sítio novo de classe pré-existente (`.salt` idem na v1.3) | sítio novo, classe não | benigno: nulo (nome do framework em dir 0700); atacante same-UID já lê chave/salt por desenho | sim | mesma cerimônia do C2 (O_NOFOLLOW/O_EXCL + os.replace); precedente ratificado PLAN-024 (threat-model.md:1485-1498) |
| C4 | locks em dirs diferentes v1.3×v1.4 no mesmo log | **PROCEDENTE, janela ESTREITA; relocação POR-DESENHO** (family-atomicity cura defeito medido da v1.3) | mudança deliberada; corrida só na janela mista | só com `CEO_AUDIT_LOG_PATH` setado + hooks das 2 versões concorrentes no instante do upgrade ⇒ appends intercalados = falso alarme de `verify_chain` (tamper-EVIDENTE detecta); default: logs distintos, sem corrida | sim | doc livre HOJE (upgrade sem sessão viva); hardening opcional: lock segue a decisão de preservação r9 (fecha a janela por construção) |
| C5 | `project`=path absoluto contradiz contrato | **FALSO como violação/exposição nova; PROCEDENTE como redação** — `project` é campo-base contratual listado NA PRÓPRIA linha 501 e preenchido com o path por TODO emissor nas 2 versões (UserPromptSubmit.py:209) | não | zero exposição além do que toda linha do log já carrega (R5 provou o fato em bytes) | SPEC + docstring canônicos | cura de TEXTO (docstring :227 + frase DENIED do SPEC:501); NÃO adotar o teste pedido pelo rail (contraria o SPEC vigente) |
| C6 | chave de cache omite cwd com candidato absoluto | **PROCEDENTE, P2 correto; PRÉ-EXISTENTE estreitado** (v1.3 key era `(DIR, HOME)` — mais cega) | não | canto: override RELATIVO + processo longo + chdir (R6); hooks são curtos | sim | follow-up pós-GA (5 linhas: cwd quando o input VENCEDOR é relativo) |
| C7 | marker diz «DISCARDED» em postura advisory | **PROCEDENTE, dormente** (zero consumidores fora de testes; docstring do GateVerdict :382-383 declara a intenção violada) | módulo novo | nulo hoje; falsa evidência de disposição para caller futuro (R7) | sim | follow-up pós-GA (cauda condicional à postura) |

## §1 C1 — `state_store.py:126` (cutover do scratchpad)

Código: `_state_root()` em state_store.py:126-133 — `CEO_STATE_ROOT` → `CEO_PROJECT_NAME` →
`_runtime_paths.runtime_state_dir()/"state"`. v1.3.0: default era o LITERAL
`$HOME/.claude/projects/ceo-orchestration/state` (v1.3 state_store.py:125-126).
Reprodução R1 (clone, HOME tmp): perna A grava `resume-anchor` no layout v1.3; perna B (default
HEAD) resolve o slug nativo e `get()` = **None**, com o sqlite legado de 16.384 bytes intacto no
disco. Mecanismo confirmado. PORÉM a conclusão «the release note only warns about the audit
chain» é **falsa no HEAD revisado**: CHANGELOG.md:121-130 («Plan state and scratchpads move too…
/resume and inter-agent handoffs report missing state… Two documented routes…») e
UPGRADE-PROCEDURE.md:63-81 («Upgrading from v1.3.0 with an ACTIVE plan? Read this first») dizem
exatamente o cenário, com o escape hatch `CEO_PROJECT_NAME` e a rota de cópia via
`runtime_paths.py --state-dir`. CHANGELOG.md:129-130: «A migration is a signed condition of
rc.1 (see the release envelope)» — a cura estrutural já está registrada como condição.
Consumidores afetados: check_arbitration_kernel.py, check_precompact_continuity.py,
check_scratchpad_access.py. Classificação: POR-DESENHO (ADR-001 S318; CLAUDE.md §5 «a mistura
ACIDENTAL acabou») + metade documental FALSA. Nada a fazer nos livres hoje — já feito.

## §2 C2 — `injection_salt.py:198` (first-mint sem exclusividade)

Código: `get_instance_salt()` :198-217 — `_read_existing` (None) → `_generate_and_persist`
(:163-164 `path.write_bytes(salt)` — trunca sem O_EXCL) → `:215 _CACHED_SALT = (path_id, salt)`
cacheia o PRÓPRIO valor. A docstring §Thread safety (:42-51) ACEITA a corrida mas afirma «the
winner’s bytes seed the cache for both processes on next call» — **falso**: o cache é hit em :195
e nunca relê o disco. v1.3.0 é byte-similar (:110 write_bytes; :147 cacheia o próprio).
Reprodução R2 (6 processos com barreira spin, HOME tmp fresco por rodada): **5/5 rodadas com 6/6
salts DISTINTOS; 5 de 6 processos terminam com salt órfão** (≠ disco) — cada `prompt_sha256`
deles é irreproduzível a partir do `.salt` persistido. Raio: degradação de correlação forense em
1 instante por projeto (o upgrade re-abre esse instante em CADA projeto; o maintainer roda
sessões paralelas — plausível). Cadeia HMAC, chave e privacidade intactas. Classificação:
PRÉ-EXISTENTE re-exposto pelo cutover; a aceitação documentada tem justificativa refutada.
Cura mínima (≤ 10 linhas, fail-closed): em `_generate_and_persist`, criar com
`os.open(path, O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW, 0o600)`; em `EEXIST`, reler e usar o salt do
vencedor; corrigir a docstring. Controle positivo: a barreira do R2 (hoje 5/5 divergentes ⇒ 0/5).
Bateria: 48 passed hoje (nenhum teste cobre a corrida — o controle é NOVO). Canônico ⇒ cerimônia
assinada; recomendo condição de envelope, não bloqueio da rc.1.

## §3 C3 — `injection_salt.py:246` (symlink no marker)

Código: `_register_mint` :246-249 `marker_path.write_text(...)` + :250-253 `os.chmod` — ambos
seguem symlink. Reprodução R3: symlink pré-plantado em `salt-minted.json` → alvo FORA da árvore
**truncado e substituído pelo JSON do marker, e o mode do alvo rebaixado para 0600** através do
link. Mecanismo confirmado. Alcançabilidade: plantar o link exige escrita no dir 0700 do slug ⇒
mesmo UID. docs/threat-model.md:1745-1761 declara o co-residente same-UID (Tier 2) fora das
defesas do log («Chmod 0o600 protects against other UIDs, not the same UID»); ADR-079 «Honest
limit» idem; CLAUDE.md §5 fixa a fronteira como decisão permanente. O `.salt` (:164) tem a mesma
classe DESDE a v1.3; o marker é apenas o sítio novo. Classificação: FORA-DO-MODELO-DE-AMEAÇA
como ataque; hardening de defesa-em-profundidade recomendável — o próprio repo já ratificou essa
direção no escritor do log (PLAN-024: `O_EXCL` + `test_symlink_race_blocked`,
threat-model.md:1485-1498). Cura: no MESMO patch do C2 — tmp aleatório `O_EXCL|O_NOFOLLOW` +
`os.replace`; recusar marker pré-existente que seja symlink. Não bloqueia rc.1.

## §4 C4 — `audit_hmac.py:226` + `audit_emit.py:2388` + `spool_writer.py:414` (locks divergentes)

Código HEAD: `audit_hmac._audit_dir_from_env` :189-244 — com PATH+DIR divergentes e sidecars
legados sob DIR sem sidecars no destino, a FAMÍLIA (key/last-hmac/chain-length) fica sob DIR
(:226-243, breadcrumb «migracao = cerimonia»); mas `audit_emit._log_family_dir` :2371-2386 e
`spool_writer._log_family_dir` :414-431 põem o LOCK incondicionalmente em `PATH.resolve().parent`.
v1.3.0: lock era `_audit_dir()/audit-log.lock` (DIR, senão o literal — v1.3 audit_emit :2287-2291,
spool :344-349). Cenário do rail confirmado POR LEITURA: com `CEO_AUDIT_LOG_PATH` fixando o mesmo
log nas duas versões, um hook v1.3 ainda em voo trava DIR enquanto um hook v1.4 trava PATH.parent
— dois escritores no mesmo log e nos mesmos sidecars sob locks diferentes ⇒ append intercalado ⇒
fork de elo ou incremento de contador perdido; `verify_chain()` DETECTA (falso alarme de tamper,
não perda silenciosa — o desenho é tamper-EVIDENTE). Alcançabilidade real: exige (a) PATH setado
(operador de teste/multi-log; adopter default NÃO seta — e no default os logs das duas versões
são DIRETÓRIOS DIFERENTES, sem corrida, só a descontinuidade divulgada), (b) upgrade aplicado com
sessão viva no instante em que hooks das duas versões coexistem (janela de segundos, uma vez).
Classificação: relocação POR-DESENHO (cura family-atomicity de defeito MEDIDO na v1.3 — «two
projects with distinct logs serializing on one lock», spool_writer :417-424); janela mista
inerente + intra-v1.4 a família preservada fica deliberadamente em 2 dirs. Cura mínima: (a) HOJE,
livre: parágrafo no UPGRADE-PROCEDURE — upgrade só sem sessão ativa, chamando o caso PATH; (b)
hardening canônico curto: quando a decisão r9 devolve DIR, o lock de audit_emit/spool segue DIR
(v1.3 também trava DIR ⇒ fecha a janela cross-version por construção). Controle positivo: dois
escritores forçados com locks distintos ⇒ `verify_chain` acusa; com a cura ⇒ serializa. Envelope:
condição curta OU residual declarado no material assinado.

## §5 C5 — `injection_salt.py:266-274` + `audit_emit.py:8638` (project = path absoluto)

Fato CONFIRMADO em bytes (R5): a linha `salt_rotation_registered` do log isolado carrega
`project = <path absoluto do clone>` e `slug_sha256 = 80940e91847ff054` — o hash é decorativo
NESTA linha. Porém: `project` é campo-base do envelope de TODO evento registrado
(SPEC:1208 «repo identifier», SPEC:1529 «Standard base field»), está LISTADO na própria linha 501
do SPEC entre os campos do evento, e é preenchido com o path absoluto por todo emissor nas DUAS
versões (UserPromptSubmit.py:209 `project=str(repo_root)` — idêntico na v1.3.0): a linha vizinha
`prompt_submitted` do mesmo log sempre carregou o mesmo valor. O log é local, por projeto, dir
0700. A frase do SPEC:501 «DENIED on the wire: the slug/path TEXT…» lê-se, em contexto, como
proibição de PAYLOAD (o valor de slug_sha256, os bytes do salt, o path DO SALT) — mas é redação
sobre-abrangente; a docstring :226-227 («the path text never reaches the wire») é lida-só FALSA.
O comment de audit_emit :6950-6956 fala de valores «smuggled» (chaves fora da allowlist) e está
correto como escrito. ADR-079 S318 §2 exige mint OBSERVÁVEL e não proíbe o campo `project`; o
rail interno r13 P1-4 ADICIONOU `project` porque o SPEC o REQUER para atribuição (CLAUDE.md §5:
«correct project attribution» é benefício medido da W1). Classificação: FALSO como P1/violação;
PROCEDENTE como inconsistência textual em 2 sítios. Cura: reescrever as 2 frases (cerimônia de
texto; pode viajar no trem do GA). O teste sugerido pelo rail («no absolute path survives this
action») contraria o SPEC vigente — rejeitar sem emenda de SPEC.

## §6 C6 — `spool_writer.py:196` (chave de cache omite cwd)

Código: :196-200 — cwd entra na chave só quando NENHUM candidato é absoluto; a precedência real
de `_project_dir_from_env` (:224-228) faz `CEO_AUDIT_LOG_DIR` RELATIVO vencer mesmo com
`CLAUDE_PROJECT_DIR` absoluto presente. Reprodução R6: `CEO_AUDIT_LOG_DIR=logs` + projeto
absoluto ⇒ chave idêntica após `chdir`, enquanto a resolução efetiva foi de `wd-a/logs` para
`wd-b/logs` — caches dependentes (state-dir SA-K10, journal por-PID do spool) não invalidam.
v1.3.0: chave era `(CEO_AUDIT_LOG_DIR, HOME)` (v1.3 spool :190) — cega a TUDO isso; a W1
estreitou e sobrou este canto. Alcançável só com override relativo + processo LONGO que muda de
cwd (hooks são subprocessos curtos). Classificação: PRÉ-EXISTENTE estreitado; P2 follow-up
correto. Cura (≤ 5 linhas): determinar o input vencedor primeiro; incluir cwd sempre que o
VENCEDOR for relativo. Canônico; pós-GA.

## §7 C7 — `ledger_provenance.py:833` (marker «DISCARDED» em advisory)

Código: `rejection_marker` :840-854 — prefixo de postura correto («ADVISORY (would-reject)») mas
cauda incondicional «body DISCARDED, never redacted-and-kept»; `admit_entry` :902-904 DEVOLVE a
entry quando a postura não vincula (`gate_enforced()` default = False, medido no R7). A própria
docstring do `GateVerdict` (:380-383: «records what enforcement WOULD have done without
pretending it happened») declara a intenção que a cauda viola. Reprodução R7: marker impresso com
a contradição. Consumidores fora de testes: ZERO (grep em hooks/, scripts/, workflows/) —
dormente, como o residual assinado já registra. Classificação: PROCEDENTE, P2/P3, não-bloqueante.
Cura: cauda condicional («body admitted; would be DISCARDED under enforcement») + exigir decisão
de postura antes de qualquer caller de produção. Pós-GA.

## §8 Recomendação ao CEO

Vereditos: o NO-GO do rail NÃO se sustenta como bloqueio mecânico da rc.1 — C1 e C5 caem por
verificação (a divulgação existe; o contrato inclui o campo), C3 está fora do modelo de ameaça,
C4 tem alcançabilidade estreita e mitigação documental gratuita, C2 é pré-existente com cura
barata registrável como condição. Textos propostos:

- Condição E1 (já existe — manter): «Migração/rota guiada dos state stores v1.3→v1.4 entregue
  antes do GA v1.4.0 (CHANGELOG.md:129 “signed condition of rc.1”); até lá, as duas rotas
  documentadas no UPGRADE-PROCEDURE são o caminho suportado.»
- Condição E2 (nova, canônica, 1 cerimônia): «First-mint do salt exclusivo:
  O_CREAT|O_EXCL|O_NOFOLLOW; em EEXIST o perdedor relê e usa o salt do vencedor; marker gravado
  via tmp O_EXCL + os.replace recusando symlink; docstring §Thread safety corrigida. Controle
  positivo: barreira de 6 processos (hoje 5/5 rodadas divergem; pós-cura 0/5).»
- Condição E3 (ou residual declarado): «Quando a preservação r9 mantém a família sob
  CEO_AUDIT_LOG_DIR, o lock de audit_emit/spool_writer segue o MESMO diretório — fecha a janela
  de escritores mistos v1.3×v1.4 sob CEO_AUDIT_LOG_PATH por construção.»
- Texto livre HOJE — UPGRADE-PROCEDURE (§ pré-upgrade): «Não rode `upgrade.sh` com uma sessão
  Claude Code ativa neste repositório. Com `CEO_AUDIT_LOG_PATH` setado, hooks v1.3 e v1.4
  concorrentes travam locks diferentes sobre o MESMO log por alguns segundos — um append
  intercalado nessa janela aparece depois como quebra detectada por `verify_chain()`.»
- Texto livre HOJE — CHANGELOG [1.4.0] (2 linhas, opcional): «Primeira prompt pós-upgrade: rode-a
  numa única sessão por repositório. Sessões paralelas na primeira prompt podem cunhar salts
  concorrentes; os `prompt_sha256` da sessão perdedora ficam sem correlação com o `.salt`
  persistido (corrige-se na condição E2 do envelope).»
- C5: emenda de REDAÇÃO no SPEC:501 (frase DENIED → «…the slug/path TEXT as payload values») e na
  docstring de `_register_mint`; nunca remover `project` do evento.
- C6/C7: abrir follow-ups pós-GA nomeados (chave de cache do vencedor-relativo; cauda do marker
  condicional à postura).

## CLAIM

Verifiquei as 7 conclusões da parte 6 no HEAD 4a1b448 por leitura, diff v1.3.0 e 6 reproduções
isoladas em clone descartável (cadeia viva intocada; bateria 48/48 verde). C1: mecanismo real
(R1), mas POR-DESENHO e JÁ divulgado em CHANGELOG:121-130 + UPGRADE-PROCEDURE:63-81, com migração
JÁ condição assinada da rc.1 — a metade «sem aviso» do rail é FALSA. C2: corrida real e
reproduzida (5/5 rodadas, 5 salts órfãos/6), PRÉ-EXISTENTE da v1.3, re-exposta pelo cutover;
cura O_EXCL barata ⇒ condição E2. C3: symlink seguido confirmado (R3), mas same-UID = Tier-2 fora
do threat model; hardening no mesmo patch. C4: locks divergentes confirmados por leitura; janela
estreita (exige CEO_AUDIT_LOG_PATH + upgrade in-session); doc livre hoje + condição E3 opcional.
C5: fato provado em bytes (R5) porém FALSO como violação — `project` é campo-base contratual nas
duas versões; sobra cura de redação. C6/C7: P2 corretos, pré-existente estreitado e dormente.
Nenhuma conclusão sustenta bloqueio mecânico da rc.1 com E1 mantida e E2/E3 registradas.
