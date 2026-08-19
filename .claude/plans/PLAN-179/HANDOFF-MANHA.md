# Handoff da manhã — 2026-08-19

## O comando

```
! bash ~/canhada-labs/BOM-DIA.sh
```

Ele descobre sozinho em que ponto a cerimônia parou, assina (1 pinentry),
roda o dry-run, landa, pusha e vigia o CI. Se algo divergir, ele **para** e
diz o quê — nenhum gate foi afrouxado para caber na madrugada.

Se o script parar com `PARE:`, me chame com a saída. Não force nada.

## Estado ao dormir

| item | estado |
|---|---|
| `PLAN-169 W3-K` | **LANDADO e pushado** (`c34e8e3`) — cerimônia de kernel, override armado e desarmado dentro do script, `env \| grep CEO_KERNEL` vazio |
| `PLAN-179 staged-w01` | **pronto**, 31 paths, gates G1/G2/G2b verdes |
| `PLAN-179 staged-w24` | implementado, **deliberadamente não montado** (depende do w01 landar) |
| pair-rail | **rodando** — veredito no fim deste arquivo |

## Por que você vai assinar de novo

Você assinou o sentinel do 179 ancorado em `c34e8e3`. Depois disso eu commitei
três correções (o gate `G0` aceitando `YES`, o ponteiro do sentinel, o próprio
`BOM-DIA.sh`), e cada commit move o HEAD — o gate `G3` exige `anchor == HEAD`,
por bons motivos. O `BOM-DIA.sh` detecta isso e regenera o sentinel com o
anchor certo antes de pedir a assinatura. Custo: 1 pinentry, o previsto.

## O que foi consertado para a manhã não custar rodada

1. **`G0` aceita `yes`/`YES`/`y`.** Ontem o land abortou porque você digitou
   `YES` maiúsculo depois de um dry-run verde. O gate existe para impedir um
   enter distraído, não para exigir shift. Controle: `no` continua abortando.
2. **Os scripts de assinatura não recusam mais por causa do próprio output.**
   A pré-condição "árvore limpa" via o `approved.md` que eles mesmos geram e
   travava a segunda tentativa.
3. **`BOM-DIA.sh`** substitui a sequência de scripts por um só, com detecção
   de estado — não há ordem para lembrar.

## Depois do land (comigo, não com você)

- Montar o `staged-w24` (W2+W4) — o `README-COMO-MONTAR.md` lá dentro lista
  o que a cerimônia ainda deve.
- Flip do `PLAN-179` `executing→done` quando as waves fecharem (é seu).

## Veredito do pair-rail — round 1: **REJECT, 9 achados**

Valeu a pena. Evidência completa em `PLAN-179/rail-round-1/`.

O pack tinha passado em **tudo** que eu sei medir sozinho — simulação de land
8/8, suíte completa 7088 passed / 0 failed, teste de integração que nasceu
vermelho e foi curado no código de produção. Os 9 achados sobreviveram a isso.
Três são a classe dominante deste repo, *instrumento que parece ligado e não
pode disparar*:

1. **[P1] `upgrade.sh` nunca registra o hook novo.** Instalação NOVA recebe (o
   template já fora curado pela suíte); **upgrade não**. É o mesmo buraco de
   adopter, uma camada mais funda — quem já tem o framework instalado
   receberia o arquivo e o canal de pinning nasceria morto.
2. **[P2] `gc_orphan_session_stores()` não tem chamador de produção** — e o
   ADR já afirmava que o GC shipava. Arquivos `.sqlite`/WAL/SHM acumulariam
   sem limite.
3. **[P2] `event_source` não-hashável levanta `TypeError`** antes do fail-open,
   quebrando o contrato "emit_generic nunca levanta".

Mais: histerese de pressão global em vez de por sessão; 12 violações do
`check-test-env-hygiene.py` no teste novo (o gate do próprio repo); o guia do
adopter dizendo "staged, não instalado" e descrevendo um guard que HALTA a
compactação (o oposto do que ship); a linha v2.56 do SPEC declarando ausente um
campo que este mesmo patch adicionou; e uma implicação de *throughput* num
comentário, que este repo não faz em lugar nenhum.

**Estado:** as 9 curas estão sendo aplicadas ao pack, com re-verificação
completa depois. Um **round 2** do rail roda em seguida. Se o round 2 voltar
limpo, o `BOM-DIA.sh` landa o pack curado; se voltar com achados novos, eu
curo e o handoff é atualizado — **você não assina nada que o rail não tenha
aprovado.**
