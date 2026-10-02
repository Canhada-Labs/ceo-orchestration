---
id: PLAN-194-FOLLOWUP-repin-generator-hardening
parent: PLAN-194
title: "Gerador do re-pin do Codex: sentinel sem o marcador que o guard recusa, procedência conferida fora do registry e a janela hash→exec registrada"
status: draft
created: 2026-10-02
owner: CEO
depends_on: [PLAN-194]
level: L3
budget_tokens: "200-400k (estimado em 2026-10-02, S362, sem medição): item 1 50-100k (gerador + teste vermelho→verde); item 2 150-300k (depende do verificador da W3); item 3 sem custo (só registro). Reestimar na abertura"
budget_sessions: 1-2
context_risk: medium
external_wait: "item 2: a decisão 3 do PLAN-194 (empacotamento do verificador de assinatura), que não foi tomada; itens 1 e 3: nenhuma"
eta_calendar: "sem data. Posição: depois da 1.4.3, junto da W3 do PLAN-194 ou antes do próximo re-pin manual do Codex — o que vier primeiro"
tags: [codex-pin, re-pin, generator, supply-chain, followup, classe]
---

# PLAN-194-FOLLOWUP-repin-generator-hardening — três achados do gerador do re-pin

> **Lineage (PLAN-SCHEMA §1.4).** O rail do re-pin manual 0.156.1 → 0.160.0 (RP do PLAN-194, rodada 1,
> lente de afirmações, S362) deu P1: o sentinel do pacote `codex-pin-0160` diz que um defeito do gerador
> foi «reportado para cura no gerador», e não havia registro rastreável. Este followup é esse registro.
> Ele NÃO muda o pacote 0160 nem o SIGN dele: o pacote curou o sintoma à mão e declarou isso.

**Vocabulário:** gerador = `.claude/scripts/re-pin-codex.py` (oráculo 0, livre), que gera o pacote do
re-pin a partir do molde; molde = `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh`; sentinel =
o `pin-<etiqueta>-approved.md` que o Owner assina; SLSA = atestado de procedência de build (quem
compilou, de qual fonte).

## Item 1 — o gerador escreve no sentinel o marcador que o próprio guard recusa (cura de CLASSE)

- **Fato (lido no `9a458f19`):** `_inherited_prose_notes` (`re-pin-codex.py:1538-1556`) devolve uma nota
  que cita o marcador de pendência por extenso (`:1548-1549`, via `TODO_MARK`, `:202`).
  `render_sentinel` põe essa nota no sentinel (`:1784`). O guard que o gerador injeta no script de
  assinatura (`_GUARD`, `:924-932`) faz `grep` do mesmo marcador no sentinel INTEIRO e no `.new` do pin
  (`:927`), e o run real morre (`:928`).
- **Consequência:** na gramática de bloco de constantes, todo pacote gerado nasce com um sentinel que
  o SIGN real recusa, mesmo com as duas seções humanas escritas.
- **O que o pacote 0160 fez:** curou só o SINTOMA. Reescreveu à mão o nome do guard na nota e declarou a
  edição no item 4 dos residuais do sentinel.
- **Cura de classe:** o gerador não escreve, em nenhum arquivo que o guard lê, o marcador que o guard
  recusa. A forma da regra fica no gerador, não em cada nota: toda saída destinada ao sentinel ou ao
  `.new` do pin passa por uma checagem que recusa o marcador antes de gravar.
- **Controle vermelho→verde:** teste do gerador com um molde na gramática de bloco de constantes. Hoje
  o sentinel gerado contém o marcador (vermelho); depois da cura, não contém, e o `--dry-run` do script
  gerado não acusa pendência com as seções humanas preenchidas (verde).
- **Paths prováveis:** `.claude/scripts/re-pin-codex.py` e o teste dele (oráculo a rodar na abertura).

## Item 2 — a procedência do pin vem de um único canal (o registry npm)

- **Fato:** o gerador mede o tarball e o sha256 do payload a partir do que o registry npm serve e não
  confere atestado de procedência (`grep -n -i 'attestation\|audit signatures\|/-/npm/v1'` no gerador:
  nada, em 2026-10-02). O registry publica atestados para o artefato de plataforma:
  `https://registry.npmjs.org/-/npm/v1/attestations/@openai%2fcodex@0.160.0-darwin-arm64` respondeu
  HTTP 200 em 2026-10-02, com o atestado de publicação do npm e o `https://slsa.dev/provenance/v1`.
- **Consequência:** todo o pin deriva de um canal só. Um registry comprometido serve um tarball e um
  sha coerentes entre si.
- **Restrição medida (W0.6 do PLAN-194, seção `W0.6` do LEDGER):** `npm audit signatures` NÃO serve.
  Ele fica verde com payload adulterado, sem atestado, com atestado de outro repositório e sem rede com
  cache quente. Baixar o atestado do mesmo endpoint também não basta: é o mesmo canal.
- **Cura:** conferir a assinatura do atestado contra a raiz de confiança do Sigstore, com política de
  identidade (repositório, workflow, ref e emissor do construtor, os literais da W0.6), e o vínculo
  sha512 do tarball = `subject` do atestado. Gravar o resultado (verificado ou recusado, com a
  identidade lida) no sentinel gerado. É o mesmo verificador da W3; o empacotamento dele é a decisão 3
  do PLAN-194, não tomada. Sem a decisão 3, este item espera.
- **Controle vermelho→verde:** os mutantes da W0.6 (payload adulterado, atestado removido, identidade
  divergente) recusam; o íntegro passa.

## Item 3 — janela entre o hash e a execução do payload (registro, sem cura proposta)

- **Fato (molde, herdado pelo pacote gerado):** o script confere o sha256 do payload resolvido
  (`OWNER-PIN-SIGN.sh:466`), cria um link para ele (`:470-472`) e só depois executa o binário pelo gate
  da fase 6 (`:476`). Entre o hash e a execução, um processo do mesmo usuário poderia trocar o arquivo.
- **Mitigação existente:** o Gate 4 do `pair-rail-gate.sh` (`:179-184`) refaz a conferência do pin
  ANTES de qualquer execução do binário.
- **Limite declarado:** sob o mesmo UID, a fronteira não existe (`CLAUDE.md` §5, tamper-evidence entre
  projetos do mesmo `$HOME`). Nenhuma cura proposta; fica registrado para quem revisar o molde.

## Posição e ciclo de vida

- Depois da 1.4.3, junto da W3 do PLAN-194 ou antes do próximo re-pin manual — o que vier primeiro.
- O PLAN-SCHEMA §1.4 não deixa um followup em `executing` antes de o pai estar `done`. Se o próximo
  re-pin vier antes disso, a cura do item 1 entra como land livre dentro do próprio PLAN-194 (é um
  script livre), e este followup registra o land.
- O item 2 segue a decisão 3; o item 3 é só registro.
