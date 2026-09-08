# Condições do envelope — v1.4.0-rc.1 (pré-release; hold mecânico de 24 h antes do GA)

Cada item descreve o que o código FAZ nesta rc, para que a assinatura não afirme
mais do que aconteceu. Fonte: re-pass do candidato (codex 0.147.0 pinado, modelo
gpt-5.6-sol, 6 partes) + verificação adversarial de cada achado contra o código e
os textos de desenho ratificados (registros em `PLAN-169/repass-rc1-20260908-NOGO/`).
Adopters desta rc: os repositórios do próprio maintainer, subindo da v1.3.0 em modo
cópia. «Cura antes do GA» = entra na rc.2 por cerimônia assinada, com controle positivo.

## A. Condições DURAS (o texto da release foi estreitado para dizer isto)

1. **Rota com transform sem renderer sai 0.** `scripts/upgrade.sh` conta uma rota
   cujo transform o binário não sabe renderizar como `SKIP` nomeado e o run termina
   «Upgrade complete», rc 0 — as duas outras formas de tabela envenenada saem 3.
   Inalcançável com a tabela de seis linhas que a rc entrega; o CHANGELOG [1.4.0]
   nomeia a exceção. Cura antes do GA (~6 linhas + controle positivo).
2. **Undemote das 7 skills VETO só em install FRESCO.** Uma instalação v1.3.0 que faz
   upgrade mantém o seu `skillOverrides` (o upgrader preserva settings fora das
   migrações aditivas enumeradas). O CHANGELOG foi estreitado; a migração
   baseline-aware é cura antes do GA.
3. **`uninstall.sh` não desinstala registros `LINK` da v1.3.0.** O parser lê todo
   registro como `<sha> <relpath>`; um registro `LINK <relpath> <target>` (instalação
   `--link`) é RECUSADO com nome (falha fechada — nada é apagado fora do alvo), o
   symlink fica e o manifesto é mantido. Zero efeito em modo cópia (o caso desta rc).
   Cura antes do GA: parser com a forma `LINK` (`PLAN-169-FOLLOWUP-link-uninstall`).

## B. Residuais DECLARADOS por desenho ratificado (não mudam na rc.2 sem decisão do Owner)

4. **Merge de settings é aditivo por roster da cerimônia gravada** (Pacote E, ADR-197):
   uma registração de hook ou chave `.env` removida à mão pelo adopter VOLTA no
   upgrade — com log nomeado («REGISTERED: …») e backup `settings.json.pre-h8-merge`;
   remoção deliberada exige `--no-settings-merge`. O texto do `--help` que descreve o
   mecanismo antigo («registers new lifecycle hooks») será corrigido na próxima
   cerimônia canônica.
5. **Arquivo pré-existente byte-igual ao template entra no manifesto como
   framework-owned** (paridade com o `install.sh` v1.4.0). Efeito só sob `uninstall`
   explícito, e o arquivo perdido é byte-igual ao template público. Decisão de posse
   (prior record vs paridade) = wave própria com o Owner.
6. **O handle do install-state (UNSIGNED, `request.github_owner`) é REPLAY do pedido
   gravado, não proveniência** (ADR-155; round-7 F4): CODEOWNERS ausente + handle
   gravado ⇒ render sem flag. Quem edita o install-state edita o CODEOWNERS
   diretamente; tensão com `docs/threat-model.md` T-008 registrada; hardening (flag
   explícita) = decisão do Owner.
7. **Registros `LINK` herdados da v1.3.0 continuam válidos por igualdade prior-record +
   alvo vivo** (`_framework_manifest_set.sh`); um over-claim de symlink pré-existente
   feito pela v1.3.0 sobrevive ao upgrade. Migração conservadora = cura antes do GA.
8. **Tabela de rotas ausente/corrompida no CHECKOUT do framework**: `install.sh` ainda
   copia `docs/` e `.github/` fixos e reporta sucesso; e `_wbm_route_table` aceita
   symlink no leaf (`-f`). A tabela vive no checkout que executa (mesma superfície do
   próprio script) — fora do modelo de ameaça como ataque; fail-closed = cura antes do GA.
9. **Gramática do handle aceita `owner-` e hífens consecutivos** (GitHub os rejeita);
   apertar no produtor e no consumidor = cura antes do GA.

## C. Hardening não bloqueante (nomeado para não se perder)

10. `--protocol-source` com caracteres fora do allowlist do consumidor é REJEITADO com
    WARNING nomeado e o ponteiro são é PRESERVADO (reproduzido: diff vazio); só um
    ponteiro também irreproduzível cai na rota D3 ratificada. Validar no produtor.
11. `chmod` falho na entrega de template é silencioso (doutrina fail-open em infra); o
    classificador de paridade acusa `MODE_DIFF` e o upgrade seguinte normaliza.
12. `CODEOWNERS` e `.template` podem coexistir através de runs (classe documentada em
    PLAN-183 §9.3; o `.template` é inerte para o GitHub).
13. O comentário de `.claude/settings.json` cita o caminho legado do audit-log
    (`projects/ceo-orchestration/`); o caminho real é o slug nativo por projeto
    (`runtime_paths.py --state-dir`). Canônico; próxima cerimônia.
14. **O manifesto de instalação não é autenticado** (`uninstall.sh` o diz nas próprias
    linhas 89-92): um registro seguro-na-forma é tratado como prova de posse. Escrita
    same-UID no alvo já é game-over pelo modelo de ameaça (§T-05); sidecar autenticado
    = item de v2. O cabeçalho do script deixa de anunciar um `exit 3` de HMAC que não
    existia.
15. **O backup pré-uninstall usa caminho previsível sem criação exclusiva**
    (`.claude.backup-uninstall-<timestamp>.tar.gz` + `.hmac`): um link pré-plantado
    com esse nome faz a escrita seguir para outro inode (reproduzido: 578 bytes fora do
    alvo, same-UID). Mesma classe do ADR-196 num sítio não convertido; cura antes do
    GA: `_wbm_dst_refuses` + criação exclusiva (`PLAN-185-FOLLOWUP-uninstall-backup-confine`).
16. CURADO nesta rc (livres): a recusa/preservação do `uninstall.sh` sai 5/6 em vez de 0
    (dry-run segue 0); o template de CI entregue verifica o SHA-256 do actionlint antes
    de extrair (o vivo já fazia; a v1.3.0 rodava `bash <(curl)` sem pin) e o gate de
    sintaxe YAML instala o parser em CI e FALHA se ele faltar, em vez de pular em verde.
15. **PostCompact reinjeta campos do snapshot em `additionalContext` com sanitização só de
    não-imprimíveis** (`check_postcompact_reinject.py`): um NOME de arquivo `finish-*.sh`
    ou um valor de snapshot adulterado atravessa a fronteira da compaction como texto
    instruction-adjacent (reproduzido byte a byte). O render é pré-existente na v1.3.0; o
    fallback session-scope da v1.4.0 o torna o caminho dominante. Cura antes do GA:
    validação estrutural full-match por campo (cerimônias como contagem/ponteiro fixo).
16. **PreCompact segue symlink em `PLAN-NNN/LEDGER.md`** e copia até 5 headings `## `
    (≤ 160 chars) de um arquivo fora do repo para o BLOB do snapshot (nunca para o
    `additionalContext`); quem cria o symlink já lê o alvo (same-UID). Cura antes do GA:
    `lstat` + `O_NOFOLLOW` (superfície nova da W2 US7).
17. **Orçamento de 2,5 s do PreCompact não chega ao lock de 5 s do `state_store`** (medido
    5,14 s sob holder vivo > 2,4 s): sob contenção rara o harness mata o hook e o snapshot
    e o evento de auditoria se perdem em silêncio; a compaction nunca bloqueia. Cura curta
    na mesma cerimônia (lock_timeout com folga abaixo do timeout do harness).
18. `SessionEnd` varre nomes modificados por dois scanners antes de fixar o desfecho; numa
    cauda rara de 50 ms um `written` real sai como `error`/UNAVAILABLE (contrato assinado
    r6/r7/r22 — instrumento, sem impacto de segurança). O GC do scratchpad NUNCA apaga
    `.sqlite.lock` (declarado em `scratchpad_lib.py`): um inode de 0 bytes por sessão sem
    plano resolvido — a claim de crescimento limitado vale para bytes, não para inodes.
19. **First-mint do salt por projeto não é exclusivo** (`injection_salt.py`): duas sessões
    que enviam o PRIMEIRO prompt depois do upgrade podem cunhar salts diferentes e truncar
    o mesmo arquivo; o `prompt_sha256` das perdedoras fica irreproduzível (reproduzido:
    5/5 rodadas, 6/6 salts distintos); a cadeia HMAC segue íntegra. Pré-existente na
    v1.3.0; o upgrade reabre UM momento de mint por projeto. Mitigação operacional: abra
    a primeira sessão de cada repositório SOZINHA depois do upgrade. Cura antes do GA:
    `O_CREAT|O_EXCL|O_NOFOLLOW` e a perdedora relê; na mesma cerimônia, a escrita do
    marcador `salt-minted.json` deixa de seguir symlink (classe same-UID, fora do modelo
    de ameaça como ataque — `docs/threat-model.md` Tier-2).
20. **Locks em diretórios diferentes entre hooks v1.3.0 e v1.4.0** só ocorrem com
    `CEO_AUDIT_LOG_PATH` definido E as duas gerações de hooks correndo durante o upgrade;
    o efeito é appends intercalados no mesmo log = alarme de `verify_chain` (tamper-
    EVIDENTE, não silencioso). Regra: faça o upgrade sem nenhuma sessão aberta no
    repositório (docs/UPGRADE-PROCEDURE.md).
21. **O campo `project` dos eventos carrega o caminho absoluto do repositório** — campo-base
    contratual (`SPEC/v1/audit-log.schema.md` §501), preenchido assim por TODO emissor nas
    duas versões: não há exposição nova; a frase «slug/path never reaches the wire» no
    docstring de `audit_emit.py` e a redação DENIED do SPEC estão erradas e serão
    corrigidas na próxima cerimônia canônica (texto, não comportamento).
22. Follow-ups pós-GA (P2): chave de cache do `spool_writer` omite `cwd` quando qualquer
    candidato é absoluto (canto: override RELATIVO + processo longo + `chdir`); o marcador
    de rejeição de `ledger_provenance` diz «DISCARDED» num corpo que a postura advisory
    devolve (módulo sem consumidor fora de testes).

## D. O que este re-pass NÃO cobriu

- `.claude/scripts/**` ficou fora por orçamento e permanece coberto apenas pelas
  rodadas por wave (README-rc1.md §4).
- Limite same-UID (cadeias HMAC separadas por diretório e chave, não por privilégio);
  checksums por tarball do npm não automatizados; fence-shadow variante 5 (signatário
  == Owner) fora do modelo de ameaça — residuais herdados do trem, já no CHANGELOG.
