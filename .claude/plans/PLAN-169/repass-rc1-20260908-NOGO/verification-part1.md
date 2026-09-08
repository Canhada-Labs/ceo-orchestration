# Verificação adversarial — pair-rail rc.1 pass-1 sobre scripts/upgrade.sh (HEAD 4a1b448)

Verificador: security-engineer (Fable 5). Método: leitura linha-a-linha no HEAD + reproduções em clone descartável
(clone-1 = git clone --local no scratchpad; targets A/B/C via mktemp; zero codex; zero escrita fora deste arquivo).
**Premissa da task REFUTADA:** o oráculo --is-canonical responde 1 para scripts/upgrade.sh
(controles: README.md=0, PROTOCOL.md=1) — o arquivo é **CANÔNICO**; NENHUMA cura entra como land livre hoje; toda cura é cerimônia assinada.

## §0 Tabela-resumo

| id | classificação | regressão vs v1.3.0? | raio p/ adopter v1.3.0→rc.1 (repos do maintainer) | cura hoje? |
|----|---------------|----------------------|---------------------------------------------------|------------|
| P1-1 | PARCIALMENTE POR-DESENHO (Pacote E ratificado) + defeito de DOC (help :393); «silently» REFUTADO | escopo ampliado (v1.3.0 clobberava 5 hooks W2; resto intocado) | baixo — re-adição nomeada no log, backup, opt-out | n (canônico; cura de mecanismo = arquitetura) |
| P1-2 | VERDADEIRO — superfície NOVA (manifesto nunca cobriu .github na v1.3.0); paridade com install v1.4.0 | não (superfície não existia) | baixo — perda só via uninstall explícito, de arquivo byte-igual ao template público | n (trade-off de desenho; wave própria) |
| P1-3 | POR-DESENHO (replay ADR-155/round-7 F4) + FORA-DO-MODELO no ataque; tensão citável com T-008 | não (braço novo; semântica de replay documentada) | zero — maintainer é o único escritor do install-state | n (mudança de contrato; Owner decide) |
| P1-4 | VERDADEIRO — contradiz CHANGELOG:48 da PRÓPRIA release; inconsistente com as 2 outras formas de poison | não (v1.3.0: mesmo observável — nada entregue, exit 0) | médio — rota futura sem renderer falha silenciosa com «Upgrade complete» | n (canônico) — mas é a ÚNICA cura pequena (~6 linhas, 2 sítios) e testável |
| P2-1 | PARCIAL: divergência produtor/consumidor REAL; «silently changes pointer» REFUTADO em bytes | consumidor mais estrito é novo (W3.1); dano dominante não ocorre | ~zero — WARNING loud + pointer preservado (diff vazio medido) | n (canônico; a cura fica no install.sh, também canônico) |
| P2-2 | VERDADEIRO por leitura; coberto pela doutrina fail-open-infra (CLAUDE.md §4) com fresta menor | não (superfície nova) | ~zero — janela 0600 em docs público; MODE_DIFF detecta; autocura no upgrade seguinte | n; hardening 3 linhas em wave futura |
| P2-3 | VERDADEIRO — classe documentada como defeito conhecido (PLAN-183 §9.3, citada no código :4989) | não (superfície nova; o lado install já tinha a classe) | baixo — par de arquivos; o .template é inerte p/ GitHub | n; a cura do revisor introduz DELETE (direção perigosa) |

## §1 P1-1 — settings-merge re-arma hooks/env removidos (:2885, :2903-2904 vs help :393)
Código: upgrade.sh:2885 anexa só entries AUSENTES do roster ($cur + $blk filtrado por $have — nunca sobrescreve presentes);
:2903-2904 re-adicionam env keys ausentes (with_entries select not-has).
**Reproduzido (target A):** removi o bloco check_canonical_edit.py de PreToolUse e a key env.CEO_QUIET_MODE; upgrade rc=0; ambos
VOLTARAM. Porém o log NOMEIA: «REGISTERED: 2 hook registration(s) ... PreToolUse check_canonical_edit.py / env CEO_QUIET_MODE»,
com backup settings.json.pre-h8-merge e banner «derived from templates/settings/settings.base.json — ceremony=maintainer».
«Silently re-armed» é FALSO no eixo observabilidade; VERDADEIRO no eixo consentimento (remoção deliberada indistinguível de ausência).
Desenho ratificado: CLAUDE.md §5 «Pacote E» — roster derivado da CERIMÔNIA gravada; «o .env do template viaja com os .hooks,
additively, key by key» (r7 P1: hook sem a key chegaria BLOQUEANTE). ADR-197 ACCEPTED (perfil user por subtração declarada).
v1.3.0 (:2324-2381) era PIOR no subset: _reg FILTRAVA e RE-APENDAVA à força os 5 hooks W2 (clobber de customização); fora dos 5 não
tocava — o escopo full-roster é ampliação real da v1.4.0. O help :393 («registers new lifecycle hooks», nomeando 2 exemplos) descreve
o mecanismo antigo — defeito de DOC, exatamente a citação do revisor.
Cura mínima: reescrever o help (≤8 linhas: completa TODO o roster da cerimônia gravada; remoção deliberada exige --no-settings-merge)
+ opcional aviso por adição. Controle positivo: grep do texto novo na saída de --help. A proposta do revisor (baseline por versão
instalada) é a arquitetura do settings-migrate T5.4 estendida a hooks — wave própria. Canônico ⇒ não cabe hoje.

## §2 P1-2 — byte-igualdade registra arquivo adopter no manifesto (:4746-4756)
Código: :4746 compara hash dst = hash src ⇒ :4747 IDENTICAL ⇒ :4755 _up_tpl_register — sem consultar prior record. O próprio arquivo
enuncia o princípio violado (:5234-5241): «Byte-equal means the framework bytes are here only once you already know the framework put
them there» — exigido no braço NÃO-delivery, ignorado no IDENTICAL.
**Reproduzido (target B):** .github/CODEOWNERS.template autoral pré-existente byte-igual; install EXISTS-skip; removi a row do manifesto
(simulando manifesto v1.3.0, que nunca cobriu .github); upgrade ⇒ «IDENTICAL:» + row DE VOLTA no manifesto; uninstall.sh --dry-run ⇒
«would REMOVE .github/CODEOWNERS.template». Cadeia completa confirmada em bytes.
Agravante de paridade: o INSTALL v1.4.0 faz o MESMO (medido no install-B: «EXISTS (skipping)» E row no manifesto pós-install).
v1.3.0: o gerador de manifesto não cobria .github/docs ⇒ o dano (uninstall deleta) era INATINGÍVEL — superfície nova, não regressão.
Mitigantes: o uninstall só deleta com SHA ainda batendo ⇒ o arquivo perdido é byte-igual ao template PÚBLICO (recuperação trivial,
zero informação perdida); o .template é inerte para o GitHub. Raio: baixo, e só sob uninstall explícito.
A cura do revisor (equal sem prior record ⇒ PRESERVED unclaimed, não registrar) tem custo: quebra a paridade install/upgrade e
enfraquece a recuperação-por-evidência do CODEOWNERS 0-byte (T-008 exige delivery record). Trade-off de desenho ⇒ wave própria com Owner.

## §3 P1-3 — handle UNSIGNED do install-state autoriza render de CODEOWNERS (:4903, :5031)
Código: :4902-4908 lê o handle sob REPLAY=1 via _read_install_state_github_owner (:4199-4237: schema + transporte + gramática
_wbm_github_handle_ok — sintaxe, NÃO proveniência); :5031 renderiza via sed com o handle; :4994-5005: CODEOWNERS presente sem handle ⇒
PRESERVED (unclaimed); AUSENTE com handle ⇒ INSTALL do rendered.
**Mecanismo medido (target A):** deletei o CODEOWNERS; o upgrade default reinstalou o rendered com @testowner vindo do install-state,
sem flag alguma. A metade «substituted handle» segue por leitura: o leitor valida apenas gramática.
Classificação: o replay do request gravado é contrato documentado (:44-48, :406, :5474 «replays request.* as DEFAULTS»; round-7 F4
:4886-4898 fixou a semântica; install-state = trust class ADR-155, target-side/UNSIGNED/advisory — decisão ratificada). O ataque como
descrito exige ESCRITA no target (editar install-state + deletar CODEOWNERS) — quem tem isso edita o CODEOWNERS direto; o ganho
residual é laundering de proveniência (o manifesto passa a «assinar» a entrega). docs/threat-model.md T-008 diz que o handle gravado
«proves a REQUEST rather than authorship» — mas esse texto governa a RECUPERAÇÃO de arquivo existente truncado, não o render de arquivo
AUSENTE; tensão real, não contradição direta do texto ratificado. Raio no caso real: zero (o maintainer é o único escritor; o diff do
upgrade é visível no commit). Cura do revisor (flag explícita OU igualdade com o handle do CODEOWNERS framework-owned corrente):
hardening legítimo que muda o contrato de replay ⇒ decisão do Owner, wave própria. Registrar como residual declarado no envelope.

## §4 P1-4 — transform sem renderer ⇒ SKIPPED, exit 0, «Upgrade complete» (:5077-5083, :4977-4980)
Código: :5077-5083 — rc de rota ≠ 0 ou src vazio ⇒ «SKIP (route declares a transform with no renderer, or the row is malformed)» ⇒
_UP_TPL_SKIPPED+1 ⇒ continue — NUNCA seta _UP_DELIVERY_PRECONDITION_FAILED (setters exaustivos: :4864 zero-routes, :4877
rejected-route-row, :5115 unclassified-route). A conservação :5098-5100 conta SKIPPED como verdict válido. Braço CODEOWNERS idem
(:4977-4980, «unsupported transform»).
**Reproduzido (target A):** troquei o transform de docs/rotation-log.md para substitute:{{TYPO}} no clone ⇒ upgrade: «routes
enumerated: 6 of 6», SKIP nomeado, skipped=2, «==> Upgrade complete.», **rc=0**. Contradição direta com CHANGELOG.md:48 desta
release: «A failed delivery exits 3 and persists upgrade_succeeded: false». Inconsistência interna: as DUAS outras formas de poison da
MESMA tabela (row malformada/escapando; zero rotas) ⇒ exit 3; esta ⇒ exit 0.
Não é regressão: v1.3.0 tinha o MESMO observável (nada entregue, exit 0 — era o defeito D1 inteiro). Envenenar a tabela exige escrever
no CHECKOUT do framework (mesma superfície do próprio script) ⇒ fora-do-modelo COMO ATAQUE; o cenário que importa é BENIGNO: rota
futura adicionada sem ensinar o renderer ⇒ adopters não recebem a entrega, silenciosamente, com sucesso persistido — a forma exata da
classe D1..D4 que custou seis sessões de main vermelho (CLAUDE.md §5).
Cura mínima (~6 linhas, sítios :4980 e :5083): setar _UP_DELIVERY_PRECONDITION_FAILED=1 e REASON=unrenderable-transform antes do
continue. Controle positivo: minha repro A com rc esperado 3 (hoje 0 — vermelho sem a cura); preservar o SKIPPED benigno «branch not
taken»; bateria: test-installer-write-safety-e2e.sh + test-ownership-verdict-unit.sh + smoke (contagens de skipped). Canônico ⇒ cerimônia.

## §5 P2-1 — allowlist do PROTOCOL_SOURCE rejeita o que o produtor aceita (:1773, :1802)
Código: :1772-1773 allowlist positivo [A-Za-z0-9._/ espaço til hífen]{1,512} — rejeita cifrão, mais, dois-pontos; o produtor
install.sh:556 aceita RAW e persiste (:2743, :3397). A rejeição é LOUD (:1783-1785, WARNING nomeando a chave). Rota 2 (:1787-1799):
extrai o valor do pointer no disco e o MANTÉM se o re-render reproduz byte a byte; :1802 SOURCE_DIR é último recurso.
**Reproduzido (target C):** install com --protocol-source /opt/ceo+src (aceito, persistido); upgrade ⇒ WARNING da rejeição, e o pointer
seguiu /opt/ceo+src/PROTOCOL.md — REFRESH idempotente, **diff vazio** contra o backup. «If the existing pointer cannot be reconstructed,
line 1802 silently changes it» NÃO ocorre no cenário dominante: pointer são é reconstruído e preservado. O fallback :1802 só assume com
pointer TAMBÉM irreproduzível: degraded (cura→checkout é a rota D3 RATIFICADA, Owner decision D3, :1745-1755) ou edited (o verdict
PRESERVA o arquivo — INV-4; muda apenas o hash canônico gravado). Sobra: adopter com pointer degradado E chave rejeitada perde o valor
da chave — raro e coberto pela rota D3. Cura: validar --protocol-source no PRODUTOR com a MESMA gramática (paridade PLAN-185 W2 do
handle). Hardening; o install.sh também é superfície canônica.

## §6 P2-2 — chmod ignorado; inode 0600 do mktemp entregue e registrado (:4353)
Código: :4351-4354 — modo vazio PULA o chmod; chmod falho é silencioso (2>/dev/null || true); :4355 mv -f sempre. O comment :4327-4329
mede que o cp mantém o 0600 do mktemp. O braço INSTALL (:4716-4730) não chama _up_tpl_normalize_mode depois (REFRESH :4797 e
IDENTICAL :4753 chamam). NÃO reproduzido (exigiria filesystem recusando chmod — fora do orçamento); a leitura confirma a claim.
Enquadramento: falha de chmod/stat é INFRAESTRUTURA — fail-open é doutrina (CLAUDE.md §4; _up_tpl_normalize_mode a cita e emite NOTE
no caso modo-vazio). Fresta real: registrar delivered com modo não aplicado no braço INSTALL. Dano: janela de um ciclo com 0600 em
conteúdo público; o parity classifier acusa MODE_DIFF (a detecção funciona); autocura no upgrade seguinte via IDENTICAL→normalize.
Cura (3 linhas): em _up_tpl_write, se o modo pretendido é conhecido e o chmod falhar ⇒ rm do tmp + return 1 (o caller PRESERVA e
nomeia). Controle positivo: fixture com chmod interceptado. Hardening de wave futura; não bloqueia.

## §7 P2-3 — exclusividade CODEOWNERS/.template não vale através de runs (:5041-5067)
Código: :5041-5044 (handle presente ⇒ template SKIPPED «branch not taken»); :5060-5067 (CODEOWNERS presente ⇒ template SKIPPED);
nenhum braço REMOVE o arquivo do outro lado — a exclusividade decide apenas a ESCRITA do run corrente.
**Reproduzido (target A):** delete do CODEOWNERS ⇒ upgrade --no-replay ⇒ «INSTALLED: .github/CODEOWNERS.template» ⇒ upgrade default ⇒
«INSTALLED: .github/CODEOWNERS» ⇒ ls: **ambos no disco** — o par que nenhum install produz, exatamente a sequência do revisor.
Classe DOCUMENTADA: o comment :4989-4993 cita PLAN-183 §9.3 — as duas branches não são exclusivas NO TEMPO já no lado install; defeito
conhecido que o código deliberadamente não quis ampliar (e reproduz). Dano: higiene — o GitHub lê apenas CODEOWNERS; o .template é
inerte; risco de confusão de operador. A cura do revisor (remover o .template comprovadamente framework-owned antes do render) introduz
um DELETE novo num entregador — direção que exige rail próprio, jamais land noturno. Alternativa mínima: WARNING nomeando o par quando
os dois existem. Não bloqueia.

## §8 Recomendação ao CEO
1. **P1-4 é o único achado que fura o contrato ESCRITO da própria rc.1** (CHANGELOG:48). Duas rotas: (a) micro-cerimônia assinada
   pré-corte com a cura de ~6 linhas + controle positivo (a repro A vira o teste); ou (b) GO-WITH-CONDITIONS com CONDIÇÃO DURA nomeada
   no envelope + emenda do CHANGELOG nomeando a exceção (transform sem renderer = SKIP nomeado, não exit 3) — aí o texto volta a ser
   verdadeiro. Não recomendo cortar a rc.1 com CHANGELOG e binário divergentes sobre delivery-failure.
2. **CONDIÇÕES do envelope (GO-WITH-CONDITIONS):** P1-1 (fix do help :393 na próxima cerimônia canônica), P1-2 (wave própria: claim
   exige prior record OU decisão explícita do Owner mantendo a paridade com o install — registrar residual), P1-3 (residual declarado:
   handle replayed é REQUEST, não proveniência; hardening futuro), P2-1 (validar no produtor), P2-2 e P2-3 (hardening não-bloqueante).
3. **Nenhuma cura é land livre:** upgrade.sh é CANÔNICO pelo oráculo (=1; a premissa da task dizia 0 — controles README=0, PROTOCOL=1).
4. O NO-GO do revisor superestima 3 dos 4 P1 (por-desenho ratificado / fora-do-modelo / superfície nova de raio baixo) e o P1-4 é
   melhor lido como doc-vs-código da própria release. Veredito que eu sustentaria: **NEEDS_CHANGES estreito no P1-4; o resto vira
   condição ou residual declarado.**

## CLAIM
Rodei: clone --local no scratchpad (HEAD 4a1b448); 3 installs reais (targets A/B/C, receita do e2e, CEO_RAG_INSTALL_PROMPT=0);
7 upgrades; 1 uninstall --dry-run. Reproduzidos em bytes: P1-1 (hook e env removidos voltam, log nomeado), P1-2 (cadeia
manifesto-sem-row → IDENTICAL → row → would REMOVE), P1-4 (transform typo → SKIP + rc=0 + «Upgrade complete»), P2-1 (WARNING +
pointer preservado, diff vazio — a metade «silently changes» REFUTADA), P2-3 (par CODEOWNERS + .template no disco), P1-3 (metade
mecânica: reinstalação rendida pós-delete com o handle do install-state). Sem reproduzir: P2-2 (exigiria FS recusando chmod;
classificado por leitura) e o braço degraded-pointer do P2-1. Comparações v1.3.0 via git show (upgrade.sh, install.sh,
_framework_manifest_set.sh). Nenhum arquivo editado fora deste relatório; nada commitado; árvore viva intocada (somente leituras).
Tokens gastos: aproximadamente 105k (entrada + saída desta verificação).
