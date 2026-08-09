# ✅ OWNER-RETURN — o que fazer quando você voltar (S300, 2026-08-09)

> **TL;DR: são 2 comandos hoje e 1 amanhã. Todo o resto já está pronto,
> ensaiado em clone e validado. Você só digita a senha do GPG quando a
> janelinha (pinentry) abrir.**

## HOJE (ao voltar) — corte da rc.2

```
cd ~/canhada-labs/ceo-orchestration
bash .claude/plans/PLAN-166/OWNER-RC2-CUT.sh
```

O que ele faz sozinho (você só confirma e digita a senha ~3x):
1. Assina o pré-registro W5 (pinentry 1).
2. Commita a evidência do re-pass + W5 + docs da sessão.
3. Mostra o verdito que você vai assinar (GO-WITH-CONDITIONS com as
   4 exceções nomeadas V1/V2/V4/V5 — decisão que você já ratificou);
   você dá Enter e assina (pinentry 2).
4. Monta o verdito final, roda o guard local, pusha e ESPERA o CI
   (~15-40 min — pode deixar rodando; ele apita quando precisar de você).
5. `preflight --rc 2` + assina a tag `v1.3.0-rc.2` (pinentry 3).
6. Pergunta "SIM" antes de pushar a tag e criar o pre-release.

Se QUALQUER passo falhar, ele para com mensagem clara — me chame no
Claude e não re-rode a partir do push.

**Depois do corte:** me chame no Claude e diga "roda o E0" — o W5
estará assinado e eu executo o gate-zero (custo ~0) e o fechamento.

⚠️ A partir do corte: **NADA em main até o GA** (nem docs).

## AMANHÃ (>= 24h após o corte) — GA v1.3.0

```
cd ~/canhada-labs/ceo-orchestration
bash .claude/plans/PLAN-166/OWNER-GA-CUT.sh
```

Ele valida o hold, roda o re-pass do codex sobre a tag (~15 min),
você assina o verdito GA + a tag `v1.3.0` (2 pinentries), ele espera
os workflows e te dá o link para aprovar o `production-npm` no browser
(o clique final é seu). NO-GO do codex = ele para e você me chama.

## DEPOIS DO GA (mesma sessão) — pack W3 (cura as 4 exceções)

```
cd ~/canhada-labs/ceo-orchestration/.claude/plans/PLAN-169
cp W3-approved-draft.md W3-approved.md
# edite W3-approved.md: Anchor-SHA = saída de `git rev-parse HEAD`
# e Data = a data de hoje
gpg --armor --detach-sign -u CFCFACF00335DC74 W3-approved.md
bash OWNER-W3-LAND.sh --dry-run     # tudo verde? então:
bash OWNER-W3-LAND.sh
git push origin main
```

## O que EU deixei pronto nesta sessão (para seu registro)

- Verdito rc.2 completo (templates + campos + evidência r2 com
  manifesto reescrito e pins dos payloads raw) — **ensaiado de ponta a
  ponta em clone com chave GPG descartável**: guard delta OK, validador
  server-side OK, e os controles negativos FALHAM como devem.
- **Pack W3 completo e revalidado** (28 arquivos staged): curas
  V1/V2/V4/V5 (+ sonda `test-w3-vcures.sh`: 5 FAIL na árvore atual =
  defeitos comprovados; 8/8 verde pós-pack), release.yml P2 (byte-exato),
  W2.8 (b)-estreito ratificado por sua delegação (+ ADR-192 +
  manifesto `gate-scripts-manifest.txt`), contagens 190→192 ADRs em 10 docs,
  e a bateria plena: **6992/6992 pytest verde na simulação**.
  A simulação pegou 2 quebras que teriam abortado o land real
  (release_steps 31→32 no RELEASE.md; teste-espelho do reviewer F4).
- Trem GA de amanhã pronto (runner do re-pass do hold + templates GA +
  OWNER-GA-CUT.sh).
- Ferramenta E0 escrita e auto-testada; **recusa rodar** antes do W5
  assinado+commitado (AC-6) — como pré-registrado.
- Payloads raw movidos p/ `~/.rc2-backup/repass-r2-raw/` (pins sha256
  na PROVENANCE-r2.md).
- **Pair-rail (codex review) rodou 20 RODADAS sobre TUDO isto antes de
  você voltar: ~45 achados, todos triados (curados, ou refutados com
  evidência reproduzida e registrados). Critério de parada explícito:
  as superfícies do SEU corte de hoje ficaram sem nenhum achado nas 10
  últimas rodadas; o que apareceu no fim era polimento do pack W3 e do
  E0, que re-entram em revisão nas próprias cerimônias.** Destaques —
  na rodada 2: manifesto W2.8 foi a 8 membros
  (validador do verdito + await-gate do npm entram), o GA automático
  passou a exigir `VERDICT: GO` exato (condição nova = triagem antes
  de assinar), e o gate do E0 pina o signatário na SUA chave. Também:
  commit 1 agora é allowlist fechada (não `git add -A`; intruso
  plantado é acusado, controle testado nos 2 sentidos); re-pass GA
  ganhou os helpers executados no escopo (`_release_bump_sites`,
  `await_release_gate`, validador step-15) e virou 2 partes (o diff
  estourava o cap de 250KB do redactor); o GA espera o npm-publish da
  TAG concluir com sucesso (poll amarrado ao SHA + `npm view == 1.3.0`
  assertivo) antes de DECLARAR sucesso — o Release em si é criado pelo
  release.yml (ordem herdada, pré-existente); se o npm falhar, o script
  te dá a mitigação (`gh release edit --draft`) na hora; E0 gateia a evidência no que o
  substrato REALMENTE garante (fail-closed no null-checker + linhas
  malformadas; o estado do `verify_chain` por arquivo é impresso como
  RESSALVA no relatório — a cadeia não é oráculo same-UID, limitação
  HMAC-483/S298 documentada no próprio código), decompõe as fronteiras
  da janela e exige W5 com bytes == HEAD + assinatura verificada DA SUA
  chave antes de rodar.

## ⚠️ Continuam valendo

- NÃO rodar `/set-quality-profile` até o W4.3.
- Nightly saudável = 62 GREEN / 3 RED exatos; all-green = investigar.
- W3-K e W4-C = cerimônias de kernel em sessões próprias (ordem pinada).
