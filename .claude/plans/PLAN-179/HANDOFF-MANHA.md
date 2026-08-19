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

### Round 2: **4 achados, todos novos** (9 → 4, convergindo)

Nenhum repetido: o rail parou de achar o que já foi curado e passou a achar
camadas mais fundas. Todos curados também.

1. **[P1] `audit-registry.golden.txt` estava stale** — o gate
   `check-audit-registry-coverage --check` ficaria VERMELHO no land, e eu
   **nunca tinha rodado esse gate**. Regenerado (324→325) e agora faz parte da
   minha bateria de verificação.
2. **[P2] `project` ausente no evento novo** — o SPEC exige e nem
   `emit_generic` nem `_write_event` sintetizam. Passei a suprir. Já
   `session_id` ficou documentado como **condicional**, com a razão escrita: só
   viaja se vier do input do hook, porque preencher de `CLAUDE_SESSION_ID`
   atribuiria a linha a quem um agente escolher — linha não-atribuída é
   honesta, mal-atribuída não.
3. **[P2] os dois GCs não eram realmente limitados** — `sorted(iterdir())`
   materializa o diretório inteiro antes do cap agir, então o "cleanup
   limitado" era justamente o que podia estourar o budget do hook. Agora o cap
   limita o SCAN.
4. **[P2] um `os.environ[...] =` novo num arquivo ALLOWLISTED** — o achado mais
   sutil da noite: o gate de higiene **não veria** esse site, porque a
   allowlist silencia o arquivo inteiro, inclusive o futuro dele.

### Verificação final (feita por mim, num clone com o pack de 33 paths)

`py_compile` · `settings.json` · `bash -n` + `shellcheck` do `upgrade.sh` ·
**`check-test-env-hygiene`** · manifesto de gate-scripts ·
`validate-governance` · `verify-counts` · `check-claude-md-claims` ·
**`audit-registry --check`** — **10/10 verdes.** Suíte completa de hooks: ver
`rail-round-1/CURAS.md` (a única falha observada é ambiental, provada isolando
o teste: ele exige que o audit log VIVO não mude, e minha própria sessão
escreve nele a cada tool call).

### Round 3: **2 achados, ambos NOVOS** — e um deles é sério

Convergência **9 → 4 → 2**, sem repetição.

**[P1] Eu tinha introduzido um primitivo de ESCRITA ARBITRÁRIA.** A cura que eu
mesmo escrevi no round 2 criava um arquivo temporário com nome **previsível** em
`.claude/state/` e o abria com `open(..., "w")` — que **segue symlink**. Um
agente capaz de escrever nesse diretório podia pré-criar o path como link para
qualquer arquivo e fazer o hook truncá-lo.

Não é teórico. Controle negativo contra o código anterior:

```
VICTIM_SIZE_BEFORE=44 AFTER=3      <-- truncada
CONTEUDO FINAL DA VITIMA: '60\n'   <-- o valor do bucket, escrito dentro dela
```

Curado com `O_EXCL` + `O_NOFOLLOW` + sufixo aleatório + modo na criação. E o
controle positivo é o duro: com o gerador de aleatoriedade fixado — isto é, com
o atacante **sabendo** o nome — o symlink é plantado no path exato e a escrita
**recusa** (vítima 44→44, link intacto). Evidência e ambos os controles em
`PLAN-179/rail-round-3/`.

**[P2] O rail pegou uma afirmação FALSA que eu escrevi.** Eu havia comentado que
o GC "continua de onde a iteração parou" — não continuava, nada persistia
cursor, e um arquivo expirado atrás de um prefixo de arquivos frescos nunca
seria recuperado. Corrigido o mecanismo (offset rotativo) **e** a afirmação
(cobertura probabilística, não garantida).

### Round 4: **3 achados P2, nenhum P1** — e o primeiro é grave

**[P2] O guard de pressão NÃO PODIA disparar em produção.** O PreCompact
documentado entrega apenas `trigger` e `custom_instructions`; o guard lia
contagem de tokens **do evento**, que nunca vem. Com o piso armado, toda
invocação real caía no caminho "sem medição". **E o teste passava** — porque
injetava uma forma que produção nunca envia. O teste alimentava o próprio
sujeito com algo irreal.

Cura: existe fonte real. O `statusline-ceo.py` grava `context_pct` no sidecar
(estava em `84.0` no arquivo vivo enquanto eu investigava). O guard passa a
lê-la. Controle com a **forma de produção**: sem sidecar → 0 eventos e
breadcrumb honesto; com sidecar → 1 evento, `used_bucket=80`, com `project` e
`session_id`.

**[P2] Os dois GCs, terceira tentativa e a primeira certa.** O offset rotativo
que eu tinha posto no round 3 era `% _scan_cap`, então nada além de ~2× o cap
era alcançável — starvation com passos extras. Agora: varredura completa e
preguiçosa (`os.scandir`, sem sort), limitada por **deadline**. Custo limitado
por tempo, correção por cobertura.

**[P2] `env-inventory.json` estava desatualizado** — três variáveis novas
deixavam esse gate vermelho.

### Round 5: **2 achados P2** — e um deles cita a minha própria medição

**[P2] O sidecar do statusline é compartilhado entre projetos.** Eu tinha
acabado de ligar o guard nele — e o rail apontou que o `w0-measurement.md`
**deste plano, escrito por mim ontem**, já registrava que o arquivo é reescrito
com o `project_dir` de outro repositório durante a sessão. Ler `context_pct`
sem conferir identidade atribuiria a pressão de outra sessão a esta e
re-armaria o marker errado. Agora `session_id` e `project_dir` são conferidos,
e campo de identidade **ausente** conta como divergência: o guard degrada para
silêncio, nunca para ficção.

**[P2] O GC, quarta tentativa — e a primeira com cobertura garantida.** As
quatro versões anteriores definiam a fatia do turno por **posição** na
iteração (prefixo, offset, deadline). Toda fatia por posição deixa uma cauda
inalcançável — foi o mesmo defeito apontado três rodadas seguidas. Agora a
fatia vem da **identidade**: `shard = crc32(nome) % 8`. Em 8 turnos todo
arquivo cai na sua fatia exatamente uma vez. Controle: 600 stores, 12
expirados espalhados inclusive na cauda → **12/12 recuperados**, 588 frescos
preservados.

### Um problema de MÉTODO que eu criei e corrigi

Commitar os vereditos do rail no repo fez o revisor **lê-los e ecoá-los** como
se fossem dele — no round 3 isso quase me fez reportar o veredito errado. A
evidência continua no repo (é trilha auditável), mas agora sai do clone de
revisão.

### Bônus: um vermelho no vivo que ninguém tinha visto

A mesma verificação pegou que o land do W3-K deixou um `bare-testcase`
reprovado pelo gate de higiene. Passou porque o `Validate` daquele commit foi
**cancelado** por um push superseder — o gate nunca falou. Curado em `9179ef2`.
