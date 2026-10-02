# Pair-rail prompt — PLAN-194, re-pin do Codex 0.156.1 → 0.160.0 (pack `codex-pin-0160`), RODADA 1 (Codex read-only + refutadores Claude)

Você é o revisor cruzado (V2 da cascata de verificação — `PROTOCOL.md` §Verification cascade).

**Instrumento desta série:** o Codex GLOBAL 0.156.1, com `--verify-codex-pin` = `verified` contra o
manifesto vivo, conferido pelo CEO antes de cada rodada. É a última série de rail no 0.156.1: ela
termina INTEIRA antes de a 0.160.0 ser instalada (PLAN-194, plano B, passo 5). O CEO registra, antes de
cada rodada, o sha256 do `~/.codex/config.toml` do Owner, que escolhe o modelo e o esforço servidos
(medido em 2026-10-02: `232b5bede4e1cb36c103046a2aedbb075dac6255c080b789bcb027bcc423a53a`, com
`memories` e `chronicle` ainda ligados — o Lote 0(b) do runbook não foi aplicado).

**Sujeito desta rodada (e só ele):** os seis arquivos do pack em `.claude/plans/PLAN-194/codex-pin-0160/`,
no commit de materiais (o sha256 de cada um vai no registro da rodada):

1. `pin-0160-approved.md` — o texto que o Owner assina. `Anchor-SHA:` e `Data:` são preenchidos pelo
   passo 1 do script (não são achado). As seções escritas à mão são «Ratificação» e «Protocolo,
   consequência e residual», mais UMA edição na nota final do gerador (o nome do guard sem o marcador
   literal de pendência — ver o item 4 do residual). Todo o resto é texto do gerador.
2. `codex-cli-pin.txt.new` e `codex-cli-pin-manifest.json.new` — os bytes que a cerimônia aplica aos
   dois canônicos. O parágrafo novo do `.new` do pin (do «re-pin update (2026-10-02…» até a linha da
   faixa) é texto ASSINÁVEL: vira cabeçalho do canônico.
3. `OWNER-PIN-SIGN.sh` — gerado do molde `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh`
   (sha256 `09ec1cf8f8efc18a9eb47a2e06298af04cfa8e501e786188356b9c8484e098df`). O gerador declara que o
   corpo é o do molde byte a byte fora do cabeçalho, do bloco de constantes e do guard: CONFIRA com
   `diff` contra o molde. A prosa da mensagem de commit (as linhas `printf`) é herdada e precisa ser
   verdadeira para ESTE re-pin.
4. `rehearse-pin-0160.sh` (gerado; só o cabeçalho difere do molde `rehearse-pin-0156.sh`) e `README.md`
   (gerado).

**Contexto que NÃO é sujeito:** o gerador `.claude/scripts/re-pin-codex.py`, o molde 0156 (já assinado),
o texto do PLAN-194 e a sonda FD-02. Um achado sobre a CLASSE no gerador (ver abaixo) vai numa seção
separada e não decide o veredito — salvo se ele tornar falsa uma frase do sujeito.

**Achado já conhecido (para conferir, não para redescobrir):** a nota que o gerador escreve no fim do
sentinel («Texto herdado sem conferência…») citava o marcador de pendência por extenso, e o guard que o
mesmo gerador injeta no script (`grep -n` desse marcador no sentinel INTEIRO e no `.new` do pin) faria o
run real recusar mesmo com as seções humanas escritas. O pack cura o SINTOMA reescrevendo o nome do guard
na nota (declarado no item 4 do residual). Confira: (a) que o grep do guard sobre o sentinel e o `.new`
do pin sai vazio; (b) que a declaração do item 4 é verdadeira; (c) se há OUTRA rota do mesmo marcador
para dentro desses dois arquivos. A cura da classe (o gerador não escrever no sentinel o marcador que o
seu guard recusa, com teste) é do gerador e fica fora deste pack.

**Evidência do ensaio:** `rehearse-pin-0160.sh` rodado em 2026-10-02 sobre estes bytes, com
`REHEARSE_GLOBAL_CODEX` = o prefixo npm descartável da sonda (0.160.0, payload `112fae7a…`) e base
própria; placar e falhas (se houver) no registro da rodada. O ensaio clona o `main` e roda o script de
verdade nos controles negativos e no p2 (run real com chave GPG descartável).

**Critérios:**
- o `.new` do manifesto é o vivo com exatamente 3 valores trocados (`package_version`, `npm_integrity` do
  artefato de PLATAFORMA, `sha256` do payload); o `.new` do pin é o vivo com o prefixo intacto, o
  parágrafo novo só de comentários e a faixa `>=0.128.0,<0.161.0` (só o teto alarga);
- os digests reproduzem do registry pela «Reprodução manual» do sentinel (sha256
  `112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b`, integrity
  `sha512-aefV6cq…`), e os quatro sha256 do bloco «Bytes que esta assinatura cobre» batem com os
  arquivos (`BASE_*` = canônicos vivos no HEAD; `SRC_*` = os dois `.new`);
- o script difere do molde só no cabeçalho, nas constantes e no guard; as constantes batem com o
  sentinel e com o registry; a tag do GA é `v1.4.2`;
- CADA frase do texto assinável — o sentinel inteiro e o parágrafo novo do pin — é uma afirmação sobre o
  código, sobre uma medição ou sobre uma decisão registrada: uma afirmação FALSA é motivo de NO-GO; o
  residual precisa ser verdadeiro e completo e declarar a classe pela FORMA, sem enumerar sítios;
- a nota do pin não carrega caractere de controle nem o marcador de pendência; o guard do script sai
  vazio sobre o sentinel e o `.new` do pin.

**Regra de parada (pré-registrada):** no máximo 3 rodadas; a 3.ª é FINAL, com anexo. NO-GO só por P0 ou
por afirmação falsa no texto assinável. Relate todo P1/P2 com `arquivo:linha` e cura concreta. Os `.new`,
o script, o ensaio e o README são GERADOS: a cura de um achado neles é regenerar o pack (nota nova com
`--pin-note`, num diretório novo), nunca editar à mão. Não proponha JEV nem capacidade não aprovada do
fornecedor. Não altere arquivos (sandbox read-only).

**Saída:** a lista de achados, cada um com severidade `P0 | P1 | P2`, `arquivo:linha` e cura; se não
houver nenhum, escreva exatamente `NENHUM ACHADO`. Termine com UMA linha
`VERDICT: GO | GO-WITH-CONDITIONS | NO-GO`.

**Registro:** o CEO grava `.claude/plans/PLAN-194/codex-pin-0160/rail-round-N.md` no formato de
`.claude/plans/PLAN-194/codex-pin-0160/rail-record-template.md`. Linhas da saída do revisor que comecem
com três crases (mesmo indentadas) têm as crases trocadas por outro marcador, com a troca declarada na
triagem.
