---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (auth/crypto VETO holder)
generated_at: 2026-08-07T21:43:32Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano fecha três dívidas reais e a direção do W2 — opção (b), gerador
  compartilhado — é a correta: fecha a classe, não o sintoma. W1 (recusa de
  HARNESS-SKIP, AC-5 conjunto-de-vermelhos) e W3 ("emendado, não revogado")
  estão bem armados.
- FRACO e central: a premissa do W2 está DESATUALIZADA contra a árvore
  landada. Rodei a sonda de evidência hoje (2026-08-07) contra a árvore viva:
  `probe-INV4-pointer-substitution.sh` → **install=0 E upgrade=0 ocorrências
  literais, "VERDICT: pointer stays substituted"**. O caminho comum
  install→upgrade hoje PRESERVA (OWN-0074), não degrada. O Gate W2 como
  escrito ("a sonda passa a reportar 0") **já passa na árvore sem fix** —
  gate vacuoso, a classe registered-vacuous que este repo já pagou para
  aprender.
- A violação de INV-4 continua real, mas mudou de forma: o canônico do
  upgrade é o corpo LITERAL (upgrade.sh:1568-1571), então o ponteiro que o
  install entregou (substituído) classifica `edited` → "adopter-customised"
  → o framework NUNCA consegue refrescar a própria entrega. E a TSV não tem
  NENHUMA célula REFRESH/DELIVER para `protocol` em `upgrade` — o branch
  executor que escreveria os bytes degradados (upgrade.sh:1630-1651) não é
  alcançável por célula enumerada. O fix precisa mirar ESSE mundo.

## Risks

- **R-SEC1 — HIGH — Gate W2 vacuoso (controle que não pode falhar).**
  Evidência: execução da sonda em 2026-08-07 contra a árvore viva → 0
  literais após upgrade (o verdito da sonda é "pointer stays substituted").
  O gate declarado no plano (§2 W2: "a sonda passa a reportar 0 ocorrências
  literais após o upgrade") passa HOJE, sem fix nenhum. Um gate de
  superfície canônica de installer que não pode falhar não prova nada e
  carimba o pack. Mitigação: o teste do AC-6 deve FORÇAR uma célula de
  escrita (ponteiro ausente ⇒ DELIVER; disco == canônico ⇒ REFRESH) e
  comparar os bytes que o upgrade ESCREVE contra os bytes que o install
  escreve, sob inputs idênticos e pinados — com controle positivo que
  falhe na árvore atual.

- **R-SEC2 — HIGH — Fix (b) sem unificar a camada de RESOLUÇÃO reabre a
  classe um nível acima.** O corpo embute `$SOURCE_DIR`, `$TARGET`,
  `$PROFILE`, `$STACK`. No install a resolução é CLI > env > `$SOURCE_DIR`
  (`--protocol-source` / `CEO_PROTOCOL_SOURCE`, install.sh:404, 517,
  662-663). O upgrade.sh NÃO tem essa flag nem lê o env — sob (b), numa
  célula de escrita, ganha o `$SOURCE_DIR` de QUEM RODA o upgrade. Caminho
  concreto para "ponteiro nomeando um checkout que o adotante não
  pretendia": adotante instala com `--protocol-source ../vendor/ceo`;
  upgrade rodado de um clone scratch/CI em `/tmp/...` numa célula
  DELIVER escreve um caminho efêmero que PARECE válido — pior que o
  placeholder, que é autoevidentemente um placeholder. Mitigação: a função
  compartilhada carrega a REGRA DE RESOLUÇÃO junto com o corpo; upgrade.sh
  ganha `--protocol-source`/env com a mesma precedência; AC-6 pina os
  quatro inputs E a grafia do `$TARGET` (install `.` vs caminho absoluto
  muda os bytes).

- **R-SEC3 — HIGH — Migração dos degradados em campo: indecidida, e a
  direção do over-claim é a proibida.** Após (b), o adotante que já tem
  `{{PROTOCOL_SOURCE}}` literal em disco (upgrades pré-PLAN-167) classifica
  `edited` → PRESERVE_OWNED → **o arquivo quebrado é preservado para sempre
  e rotulado "adopter-customised"** — o fix nunca conserta as próprias
  vítimas que o plano cita. A alternativa (reconhecer degradado ⇒ refresh)
  não pode ser um conjunto finito de hashes: o corpo literal embute o
  `$TARGET`/`$PROFILE`/`$STACK` da invocação ORIGINAL (upgrade.sh:1560),
  que não conhecemos. Mitigação: espelhar a migração legacy do
  ADR-155-AMEND-1 §4 — regenerar corpos-candidatos degradados com os
  valores DESTE run, match por hash EXATO do corpo inteiro (nunca substring
  "contém o marcador" — um PROTOCOL.md autoral do adotante pode conter a
  string, e over-claim é a classe proibida pelo §3), falha na direção
  preserve + WARNING nomeado com instrução manual. Registrar o residual no
  ADR-190: degradado que não casar com candidato fica degradado
  (recuperável à mão; under-claim, direção permitida).

- **R-SEC4 — MEDIUM — Hash canônico vira dependente do run; o
  checkout-móvel produz ponteiro-fóssil "válido".** Sob (b),
  `_REFRESH_PROTOCOL_CANON_HASH` passa a ser função de
  SOURCE_DIR/TARGET/PROFILE/STACK. Adotante move o checkout ⇒
  canônico(novo) ≠ disco(antigo) ⇒ `edited` ⇒ preservado como
  "adopter-customised" ⇒ o ponteiro nomeia um caminho MORTO para sempre,
  parecendo válido. A cura possível — `pristine_prior` (disco ==
  digest registrado no baseline ⇒ refrescável) — AUTORIZA overwrite a
  partir do registro NÃO-ASSINADO: é exatamente o residual aceito do
  ADR-155 ("Tampered H_base==H_dst", Codex R1 P0#1), e só fica dentro da
  classe de confiança aceita com as duas cercas que este caminho JÁ tem
  (backup-always + stderr alto, upgrade.sh:1638-1642). Mitigação: DECIDIR
  (aceitar o residual do fóssil, ou adotar pristine_prior com o argumento
  de classe de confiança escrito no ADR-190) — nunca silenciosamente no
  código; e jamais re-baselinar bytes customizados (C.5).

- **R-SEC5 — MEDIUM — O que quebra no delta de digest: nada na direção
  destrutiva, DESDE QUE o preserve continue registrando o canônico.**
  Verificado consumidor a consumidor: (i) classificação — `_lc` compara
  disco vs canônico DESTE run (upgrade.sh:1579-1580) e
  `_ov_obs_prior_record` greppa só a PRESENÇA do relpath, nunca o digest
  (upgrade.sh:1780-1798) ⇒ o delta de digest não muda verdito; (ii)
  uninstall — só deleta com sha IGUAL ao registro (uninstall.sh:6-7, 193,
  256); registro=canônico nunca iguala bytes customizados ⇒ nenhum corredor
  novo de deleção de arquivo do adotante; a população em transição
  (registro=canônico-literal do upgrade.sh:3142, disco=substituído) dá
  mismatch ⇒ preservado ⇒ resíduo pós-uninstall, não perda; (iii) doctor —
  flag cosmética de drift na população em transição, que o fix cura no
  próximo rewrite C.7. CONDIÇÃO: o fix mantém a semântica
  HASH_CANONICAL_POINTER no preserve (nota da OWN-0074;
  `_framework_manifest_set.sh:361-369`) — agora com canônico=substituído —
  e o teste INV-4 assere registro-digest == hash(saída do gerador).

- **R-SEC6 — LOW — Valores do estado não-assinado fluem para o corpo
  gerado (pré-existente, cercado; a cerca vira contrato).** PROFILE/STACK
  replayados de `.claude/.install-state.json` (upgrade.sh:685-701) entram
  no comando sugerido do corpo (upgrade.sh:1560) — já hoje. A cerca de
  charset (upgrade.sh:672-675: `^[A-Za-z0-9_,.-]{1,200}$` /
  `^[A-Za-z0-9_.-]{1,100}$`, sem espaço/`;`/`$`) impede injeção de shell no
  comando que o adotante copia-cola. Sob (b) isso vira input do gerador
  compartilhado: manter a cerca, nunca alargar o charset, e
  PROTOCOL_SOURCE jamais resolvido de estado/manifesto (só CLI/env).

- **R-SEC7 — LOW — W1: o fetch do tag verifica existência, não conteúdo.**
  `git rev-parse --verify refs/tags/v1.2.0` prova que o ref existe; um tag
  movido no origin muda os inputs do harness. Direção de falha é visível
  (as fingerprints pristine hardcoded em upgrade.sh §4 do AMEND-1 deixam de
  casar ⇒ vermelho), então advisory: assertar o SHA do commit do tag contra
  constante registrada, coerente com a regra de SHA-pinning do repo.

## Must-fix (blocking)

1. **W2 passo 0 — re-verificar a premissa na árvore landada e estabelecer
   alcançabilidade.** Registrar no plano que a sonda hoje dá 0/0 (o §0
   "upgrade=4" é evidência PRÉ-refactor do PLAN-167), e provar com controle
   positivo QUAL combinação alcança o branch `DELIVER|REFRESH` de
   `_refresh_protocol_pointer` (upgrade.sh:1630-1651). A TSV não tem
   nenhuma célula `protocol` com REFRESH, nem DELIVER em `upgrade`
   (verificado por enumeração: OWN-0002 é install_fresh; OWN-0032/33/34,
   0071/0072, 0074 são todas PRESERVE_*); célula ilegal cai no fallback
   preserve (upgrade.sh:1588-1592). Se o branch é morto, o defeito vivo é
   "ponteiro nunca refrescável", não "todo upgrade degrada" — e o fix é
   outro.
2. **Resolver o conflito com o anti-objetivo ANTES de codar.** Se
   (hash, regular, pristine, maintainer, upgrade) é célula ilegal hoje, o
   fix (b) sozinho NÃO devolve a capacidade de refresh — devolver exige
   células novas de escrita para `protocol` em `upgrade` na TSV, o que o
   anti-objetivo do plano proíbe ("não mexer na tabela nem nos vereditos").
   O plano precisa ou escopar uma exceção explícita ratificada pelo Owner,
   ou declarar que o refresh permanece inalcançável e reescrever o AC-6
   para o que sobra testável. Sem essa decisão, AC-6 ("byte-idêntico") é
   vacuamente verdadeiro de novo: nada no lado upgrade escreve.
3. **Substituir o Gate W2 vacuoso** (R-SEC1): teste INV-4 força célula de
   escrita, compara bytes escritos pelos DOIS writers sob inputs pinados
   (incl. grafia do `$TARGET`), assere registro==hash(gerador), e tem
   controle positivo que falha na árvore atual. Cobrir install→upgrade E
   upgrade→upgrade (o plano já pede; manter).
4. **Unificar a camada de resolução junto com o gerador** (R-SEC2):
   upgrade.sh ganha `--protocol-source`/`CEO_PROTOCOL_SOURCE` com a
   precedência do install (CLI > env > SOURCE_DIR); inputs do gerador nunca
   vêm de estado/manifesto não-assinado além dos PROFILE/STACK já cercados
   por charset (a cerca vira asserção de teste).
5. **Decidir e registrar no ADR-190 as duas escolhas de residual**: (a)
   migração dos degradados em campo (R-SEC3 — match por hash exato de
   corpo-candidato regenerado, fail-toward-preserve, over-claim proibido
   por AMEND-1 §3); (b) comportamento no checkout-móvel (R-SEC4 — fóssil
   preservado documentado, OU pristine_prior com o argumento de classe de
   confiança do baseline não-assinado + cercas backup-always/loud
   nomeadas). Nenhuma das duas pode ser decidida silenciosamente no código.

## Nice-to-have (advisory)

1. W1: assertar o SHA do commit de `v1.2.0` contra constante registrada
   após o fetch (R-SEC7).
2. WARNING no DELIVER/REFRESH quando o `$SOURCE_DIR` resolvido está sob
   diretório temporário (`/tmp`, `$TMPDIR`) — o cenário CI-escreve-caminho-
   efêmero de R-SEC2 fica ao menos audível.
3. doctor.sh: nota nomeada para a população em transição
   (registro=canônico-literal antigo ≠ disco) para o drift cosmético não
   virar ticket de adotante.
4. Guardar a saída da re-execução da sonda (0/0) como evidência datada em
   `PLAN-168/evidence/` — o §0 do plano hoje cita como atual um número que
   não é mais.

## Unseen by the original plan

1. **A tabela de evidências do §0 está stale**: "upgrade=4" era verdade
   pré-refactor; a árvore landada (`7c0828a`) preserva no caminho comum
   (execução da sonda em 2026-08-07: 0/0). A regra 3 do próprio plano
   ("verifique cada instrução mecânica") se aplica às premissas dele.
2. **Ausência estrutural de células de escrita para `protocol` em
   `upgrade` na TSV** — o executor `DELIVER|REFRESH` pode ser código morto;
   nenhuma das 62 células o exercita. Isso muda o desenho do fix E do
   teste, e cria o conflito com o anti-objetivo (Must-fix 2).
3. **Duas populações de registro em campo com semânticas diferentes**:
   install grava o hash do DISCO substituído (write_install_manifest,
   install.sh:2720, roda DEPOIS da substituição em 2104; install nunca seta
   FMS_PROTOCOL_HASH) vs upgrade grava o canônico LITERAL
   (upgrade.sh:3142). Uninstall e doctor se comportam diferente por
   população; o plano não menciona a transição.
4. **AC-6 "byte-idêntico" é indefinido sem pinar inputs**: o corpo embute a
   grafia do `$TARGET` como invocado — `install.sh /abs/path` vs
   `upgrade.sh .` produzem bytes diferentes com gerador idêntico.

## What I would NOT change

- **A escolha (b) sobre (a).** Gerador compartilhado é a decisão (i) do
  ADR-155 aplicada ao conteúdo; (a) consertaria um ponteiro e deixaria o
  próximo divergir.
- **A semântica HASH_CANONICAL_POINTER no preserve** (OWN-0074;
  `_framework_manifest_set.sh:361-369`). É a defesa do C.5 — registrar os
  bytes customizados faria o PRÓXIMO upgrade ler H_dst==H_base e clobberar.
  Não "melhorar" para registrar o disco.
- **A recusa do HARNESS-SKIP-exit-0 no W1 e o AC-5** (conjunto de vermelhos
  não pode mudar, nem encolher). É a postura anti-vacuidade correta — e é
  exatamente a régua que o Gate W2 atual não passa (R-SEC1).
- **O guard WS4 de ceremony user** (OWN-0007/0071/0072; install.sh:1941;
  upgrade.sh:1608): install user nunca cria arquivo na raiz do adotante.
  Nada no W2 pode enfraquecê-lo — é a fronteira que fecha o corredor
  uninstall-deleta-arquivo-do-adotante (AMEND-1 r7/r13/r17).
- **W3 como registro, não reescrita.** Confirmei no código a assimetria que
  o ADR-190 vai registrar: SPEC edited+owned ⇒ refresh FORÇADO com backup
  (`_refresh_spec_contract`, branch `DELIVER|REFRESH`, "REFRESHED (forced —
  $_pr/$_lc)"; fork-preserve só na rota legacy sem registro) vs PROTOCOL
  edited+owned ⇒ PRESERVE_OWNED (upgrade.sh:1613-1627). Bate com AMEND-1
  §4 e ADR-155 (iii); registrar isso não contradiz o AMEND-1 — restata. O
  ADR-190 deve também restatar a direção de falha do §3 (over-claim
  proibido), porque as decisões do Must-fix 5 se apoiam nela.

---

### Nota de VETO

Nenhum VETO exercido neste round. Condições que o disparariam na execução
do W2 (escopo: destruição/mis-atribuição de dados de adotante): (1)
migração de degradados por match de SUBSTRING ou qualquer classificação
framework-owned sem hash exato de corpo inteiro (over-claim, AMEND-1 §3);
(2) qualquer rota em que o manifesto/estado não-assinado passe a NOMEAR
conteúdo ou AUTORIZAR overwrite sem as cercas backup-always + stderr alto;
(3) enfraquecimento do guard WS4 (escrita de raiz sob ceremony user).
Condição de lift: ausência dessas três formas no diff staged, verificada
por leitura.
