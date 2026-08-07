---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: security-engineer
generated_at: 2026-08-07T00:00:00Z
scope: W2 only (INV-4 — ponteiro PROTOCOL.md install vs upgrade)
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O W2 propõe a cura certa para a CLASSE (gerador compartilhado, opção (b)) e
  a asserção certa (byte-idêntico) — direção correta.
- Mas o plano não tem NENHUM item de trabalho para a MIGRAÇÃO da população
  existente: todo adotante com `{{PROTOCOL_SOURCE}}` literal em disco vai
  classificar como `edited` → `PRESERVE_OWNED` (upgrade.sh:1613-1628) e o
  defeito NUNCA sara — exatamente na população que o fix existe para curar.
- O input decisivo do gerador (qual checkout nomear) não tem contrato: o
  upgrade só conhece o `$SOURCE_DIR` do dia, e o valor que o adotante
  escolheu no install JÁ está gravado (`ph.PROTOCOL_SOURCE`,
  install.sh:2523) e não é lido por ninguém.

## Risks

- **R-SEC1 — Severidade: HIGH.** *Migração ausente ⇒ defeito imortal +
  misattribuição de propriedade.* O hash canônico é computado contra o corpo
  que o framework GERARIA AGORA (upgrade.sh:1568-1584). Quando a substituição
  entrar no caminho do upgrade, o corpo canônico muda; o arquivo literal em
  disco (escrito por upgrades PASSADOS do próprio framework) passa a hashear
  diferente do canônico ⇒ `_lc=edited` ⇒ `PRESERVE_OWNED` "adopter-customised"
  (upgrade.sh:1615-1623). Efeitos em cascata: (1) o ponteiro degradado é
  preservado para sempre — INV-4 não fecha para nenhum adotante existente;
  (2) o manifesto passa a registrar o digest canônico NOVO (FMS_PROTOCOL_HASH,
  upgrade.sh:3138-3142) enquanto os bytes vivos são os antigos ⇒ doctor passa a
  reportar drift/"customização do adotante" num arquivo que o ADOTANTE NUNCA
  EDITOU — o framework o quebrou e agora acusa a vítima; (3) uninstall deleta só com SHA
  batendo e rotula a divergência como "user-modified" (uninstall.sh:6-7,
  :256) — o ponteiro degradado vira resíduo preservado e, como a limpeza
  final do manifesto exige que TUDO bata (uninstall.sh:264-265), um único
  mismatch também deixa a desinstalação incompleta. *Mitigação:* item de migração explícito — reconhecedor por CONTEÚDO
  dos corpos legados que o PRÓPRIO framework escreveu (precedente in-repo: r20
  LEGACY MIGRATION do SPEC/v1, upgrade.sh:1687-1699). O token literal
  `{{PROTOCOL_SOURCE}}` é um artefato que SÓ o heredoc do upgrade produz —
  install.sh nunca deixa o token em disco porque `PH_PROTOCOL_SOURCE` é sempre
  não-vazio (default `$SOURCE_DIR`, install.sh:662-663) e a passada de sed
  cobre `PROTOCOL.md` (install.sh:2060). Corpo contendo o token literal =
  framework-stale ⇒ REFRESH (com o backup-always que já existe,
  upgrade.sh:1638-1642); qualquer outro corpo divergente = adopter-customised
  ⇒ PRESERVE. Testar as DUAS populações: (a) install→upgrade-velho→upgrade-fixo
  (literal em disco) e (b) install→upgrade-fixo direto (corpo substituído do
  install).

- **R-SEC2 — Severidade: MEDIUM.** *Upgrade pode gravar um ponteiro nomeando
  um checkout que o adotante não escolheu.* O install resolve o alvo por
  `--protocol-source` / `CEO_PROTOCOL_SOURCE` / default `$SOURCE_DIR`
  (install.sh:400-404, 517, 662-663). O upgrade não tem esse flag; se o
  gerador compartilhado substituir com o `$SOURCE_DIR` da invocação corrente,
  um upgrade rodado de um clone temporário/segundo checkout/workspace de CI
  regrava o ponteiro apontando para ESSE caminho. O ponteiro é uma folha de
  instruções que o adotante executa por copy-paste (`( cd X && git pull )`;
  `X/scripts/upgrade.sh $TARGET …`) — gravar um caminho não-intencionado ali é
  defeito de integridade numa fronteira de confiança (framework → shell do
  adotante): um caminho efêmero tipo `/tmp/...` pode ser reocupado por outro
  conteúdo antes do próximo copy-paste. *Mitigação:* contrato de input do
  gerador = preferir o `ph.PROTOCOL_SOURCE` REGISTRADO no install-state
  (install.sh:2523) sobre o `$SOURCE_DIR` corrente; WARNING nomeado quando
  divergirem; paridade de flag `--protocol-source` no upgrade para override
  explícito.

- **R-SEC3 — Severidade: MEDIUM.** *AC-6 "byte-idêntico" é inatingível sem
  contrato de inputs — gate vacuoso em potencial.* O corpo embute `$TARGET`,
  `$PROFILE`, `$STACK` e o source resolvido (install.sh:1909-1917;
  upgrade.sh:1552-1560). Se o install rodou com `--protocol-source` override,
  ou com `$TARGET` grafado diferente (relativo vs absoluto), o upgrade NÃO
  consegue reproduzir os bytes do install a partir do `$SOURCE_DIR` sozinho.
  Um teste que só cobre a fixture trivial (mesmos paths, sem override) fica
  verde enquanto instalações reais divergem — a classe "medição sem inputs"
  já registrada em memória. *Mitigação:* o AC-6 nomeia o contrato de inputs
  do gerador (source: install-state > override > SOURCE_DIR; TARGET/PROFILE/
  STACK normalizados) e o teste inclui pelo menos um caso com
  `--protocol-source` override e um com TARGET relativo.

- **R-SEC4 — Severidade: LOW.** *Divergência de digest entre cerimônias.* O
  skip `--ceremony user` carrega adiante o digest canônico ANTIGO do manifesto
  prévio (upgrade.sh:3050-3060). Pós-fix, um upgrade user-ceremony grava
  H_old enquanto um maintainer grava H_new para a mesma árvore — a
  classificação do upgrade seguinte muda conforme QUAL cerimônia rodou antes.
  *Mitigação:* nota no ADR-190/AMEND + caso de teste user→maintainer.

## Must-fix (blocking)

1. **Item de migração explícito no W2** para a população com
   `{{PROTOCOL_SOURCE}}` literal em disco: reconhecedor por conteúdo
   (token literal = corpo que só o framework escreve) ⇒ classifica
   framework-stale ⇒ REFRESH com backup; corpo divergente sem o token
   permanece adopter-customised ⇒ PRESERVE. Sem isso, o fix não cura nenhum
   adotante existente e o doctor passa a misattribuir a degradação como
   customização do adotante (R-SEC1). Seguir o precedente r20 do SPEC/v1.
2. **Contrato de input do gerador compartilhado**: o caminho substituído vem
   do `ph.PROTOCOL_SOURCE` registrado no install-state (já gravado,
   install.sh:2523), com `--protocol-source` como override e `$SOURCE_DIR`
   como último fallback + WARNING quando o fallback divergir do registro
   (R-SEC2).
3. **AC-6 ganha o contrato de inputs** e o teste cobre: (a) install com
   `--protocol-source` override → upgrade; (b) install→upgrade-legado→
   upgrade-fixo (heal da população literal); (c) upgrade→upgrade
   (idempotência, já citado no §6 do plano mas sem item de trabalho)
   (R-SEC3).

## Nice-to-have (advisory)

1. Doctor: quando o corpo vivo contém o token literal, reportar
   "stale framework pointer (upgrade pré-fix)" em vez de "modificado pelo
   adotante" — mesma evidência, atribuição correta.
2. Caso de teste user-ceremony→maintainer-ceremony para o carry-forward de
   digest (R-SEC4).
3. O reconhecedor de legado NÃO deve tentar reconstruir corpos antigos com
   `$PROFILE/$STACK` correntes (o upgrade passado pode ter usado outros
   valores) — é por isso que a chave correta é o token, não o hash do corpo
   reconstruído.
4. Registrar no ADR-190 que o corpo canônico do ponteiro é FUNÇÃO de
   (source, TARGET, PROFILE, STACK) — qualquer futura mudança nesses embeds
   repete esta classe de churn de digest; considerar minimizar o que o corpo
   embute.

## Unseen by the original plan

1. A migração da população existente não tem item de trabalho — o §6 nomeia o
   risco ("placeholder já literal") mas o W2 não contém a decisão de
   classificação nem o mecanismo; "testar upgrade→upgrade" não decide o
   destino do arquivo legado.
2. `ph.PROTOCOL_SOURCE` já é persistido pelo install (install.sh:2523) — o
   input de que o fix precisa existe em disco e nada o lê.
3. O churn do digest canônico registrado (recorded H_old vs novo H_new) e
   seus efeitos em doctor/uninstall — o plano trata INV-4 como problema de
   BYTES, mas o digest gravado é superfície de decisão de 3 consumidores.
4. O precedente r20 (fingerprint de conteúdo legado do SPEC/v1,
   upgrade.sh:1687-1699) é o padrão in-repo exato para o caso — o plano não o
   cita.

## What I would NOT change

- **Opção (b) — gerador compartilhado.** Correta; (a) conserta o sintoma e
  deixa a próxima divergência de conteúdo aberta. É a mesma lição da
  decisão (i) do ADR-155 aplicada a CONTEÚDO.
- **INV-4 como asserção executável (AC-6).** Sem o teste a divergência volta
  silenciosa — nenhuma asserção de propriedade a enxerga.
- **Reuso da sonda existente** como base do teste — ela já reproduz o defeito.
- **A máquina de veredito e o registro do digest CANÔNICO (decisão iii/C.5)
  ficam como estão.** O fix deve entrar COMO UM CASO da máquina (novo
  reconhecimento de conteúdo legado), nunca como bypass dela — o guard-rail
  de `PRESERVE` para corpo genuinamente customizado é o que impede a
  regressão da classe S238.
