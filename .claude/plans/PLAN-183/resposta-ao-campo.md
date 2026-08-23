# Resposta ao relatório de campo — adopter `v1.3.0` (instalado 2026-08-16)

> **Autor:** CEO (`ceo-orchestration`). **Entrega:** do Owner, no canal
> que ele escolher — este documento é o conteúdo, não o envio.
> **Fecha:** `PLAN-183` AC-7 (`[P2]`, não-bloqueante).
> **Data:** 2026-08-23 (S324).
>
> Sete achados foram reportados. **Cinco confirmados, um recusado com
> razão, um reproduzido mas com causa diferente da suposta.** Um oitavo
> defeito, que o relatório não viu, saiu da própria investigação — e ele
> é o mais consequente para quem já instalou.
>
> Todo número aqui vem de comando executado. Onde não foi medido, está
> escrito "não medido".

---

## Antes dos itens: o relatório mudou o diagnóstico do framework

O relatório motivou uma correção de premissa nossa, e vale dizer isso
primeiro. A primeira redação do plano afirmava *"o framework foi
dogfoodado, nunca exercitado como adopter"*. **Isso era falso** — o
instrumento existe, é forte e roda por-PR (`scripts/tests/smoke-install.sh`
+ `.github/workflows/smoke-install.yml`, com install real e paridade
install/upgrade).

A causa-raiz verdadeira é mais estreita e mais útil: **o escopo do
instrumento excluía `.github/`, e ele parava em "o install escreveu os
bytes certos?" sem nunca ATIVAR nem EXECUTAR o CI entregue.** A pergunta
que ninguém fazia é exatamente a que o campo fez. Obrigado — essa é a
classe de evidência que o dogfood não produz.

---

## A1 — ponteiro `PROTOCOL.md` absoluto — **CONFIRMADO, aberto**

Verdadeiro e vivo (`scripts/_framework_manifest_set.sh:673-711`). O
ponteiro é absoluto **por construção**, e a cura anterior estava na
camada errada (no call-site, não no gerador).

**O que isso custa a você:** mover a instalação — outro `$HOME`, outro
username, outra máquina — quebra o ponteiro.

**Estado:** cura desenhada e **não executada**. Ela toca superfície
canônica (`install.sh` + o gerador), logo exige cerimônia de assinatura
do mantenedor. Duas coisas foram decididas no desenho e valem para você:

- o que o ponteiro relativo compra é sobreviver a mover **source e target
  JUNTOS** (a classe real de quebra). Mover o target **sozinho** tem como
  resposta correta um **erro nomeado** que conduz ao reparo — não
  resolução mágica;
- haverá **remediação retroativa**: um upgrade futuro reconhece o
  absoluto legado e re-renderiza, com backup.

**Enquanto isso, a saída existe hoje e não estava documentada:** as flags
`--protocol-source` / `CEO_PROTOCOL_SOURCE` (`install.sh:409,522,663-668`)
já resolvem isso, e o corpo renderizado passará a **nomeá-las** — hoje
ele manda "editar" sem dizer que existe flag para isso.

## A2 — steps de CI que só rodam no repo do framework — **CONFIRMADO, CURADO**

Verdadeiro. Curado em `4f750f0`, com o censo **re-derivado
comportamentalmente no seu tipo de instalação**, não por leitura do
template: `templates/.github/workflows/validate.yml.template` foi de
**14 para 11 steps**.

Foram removidos **três**, não os dois que o desenho previa. O terceiro é
achado novo dessa re-derivação, e é a razão pela qual exigimos
re-derivar: o step *"Skill inventory idempotency"* era estruturalmente
impossível no adopter. Havia ainda dois steps (9 e 10) apontando para
`.claude/{hooks,scripts}/tests` — árvores que o install **nunca embarca**
— o que produzia `Ran 0 tests OK` com `rc=0`: **verde vácuo**, pior que
vermelho.

## A3 — `benchmarks.yml.template` chama script não-entregue — **CONFIRMADO, CURADO**

Verdadeiro (`template:129`; o install não copiava `.github/scripts/`).
Curado no mesmo commit.

## A4 — skills de VETO em `name-only` — **CONFIRMADO, e era pior do que você viu**

Verdadeiro — **e é/era defeito vivo no NOSSO repositório também**, não só
no seu (`.claude/settings.json:872-873`). O mecanismo: a proteção do
gerador tinha **um único eixo**, `tier`, que protege core/frontend. Skills
de VETO em tier `domain` não eram protegidas por deter VETO — a proteção
que as core tinham era **incidental** ao tier delas.

**Curado na autoridade** (`ed4d1cf`): existe agora
`.claude/scripts/veto_skill_map.py`, que **DERIVA** o conjunto de skills
com VETO dos organogramas de autoridade (nenhuma skill enumerada à mão),
mais 22 testes, e o gerador ganhou o **segundo eixo**: `veto_skills`
protege quem detém VETO **em qualquer tier**. Medido: `veto_protected` =
18 entradas, e nenhuma das três antes demovidas
(`financial-correctness-and-math`, `financial-display`,
`trading-execution`) aparece no `skillOverrides` gerado.

**Ressalva honesta:** o **gerador** está curado; o **artefato** do nosso
repo ainda não — a regeneração é passo manual e não foi rodada. No seu
lado, o que importa é que um upgrade futuro entrega o gerador correto.

## A5 — 71 timeouts de hook em 10 dias — **REPRODUZIDO, causa diferente**

Reproduzido com precisão: **71 exatos**, todos breach do teto de 5 s,
todos `hook_cancelled` com `timedOut=true`. A aritmética fechou
(35+25+7+2+2) e não foi preciso abrir arqueologia.

**Mas a atribuição mudou o veredito: 70 dos 71 são do NOSSO repositório**,
não do seu. O que você viu é real como fenômeno e quase todo endereço
nosso. O teto de 5 s e o comportamento sob ele seguem em avaliação
(wave própria, gateada por medição).

## A6 — CODEOWNERS com o handle da organização — **RECUSADO, com a razão**

**Não é defeito, e aqui está o mecanismo** (o AC exige que ele seja
explicado ou declarado não-explicado; ele é explicável).

`install.sh:1493-1515` tem **dois ramos**, e nenhum deles entrega o nosso
handle:

| ramo | condição | destino | conteúdo |
|---|---|---|---|
| A | `--github-owner <handle>` passado | `.github/CODEOWNERS` | `{{OWNER_HANDLE}}` substituído pelo **SEU** handle (11 ocorrências, medido) |
| B | flag ausente | `.github/CODEOWNERS.template` | template cru, com `{{OWNER_HANDLE}}` **não** substituído |

A fonte é sempre `templates/.github/CODEOWNERS.template`. O
`.github/CODEOWNERS` do **nosso** repositório — que de fato carrega
handles reais — **não é a fonte de entrega** e nunca viaja. Medido:
digest da fonte `1955b01a…` (1.442 b) contra o nosso arquivo vivo
`ba6667d9…` (10.259 b); são artefatos distintos.

**Porém — e isto é novo, saiu desta investigação e provavelmente é o que
você viu:** no ramo B os **11 `{{OWNER_HANDLE}}` ficam crus para sempre**,
e `.github/` está **fora dos dois scanners de placeholder** do install
(`explicit_files`, `install.sh:2126-2135`). Nem o gate
`--strict-placeholders` nem o aviso de fim de install olham para lá. Ou
seja: se você instalou **sem** `--github-owner`, tem um arquivo com
placeholder cru e **nada avisou**. Isso é defeito nosso, foi registrado, e
tem cura encaminhada.

**Ação sugerida para você:** rode
`grep -c '{{OWNER_HANDLE}}' .github/CODEOWNERS.template` no seu
repositório. Se der diferente de zero, ou substitua à mão, ou reinstale
passando `--github-owner <seu-handle>`.

## A7 — o guard de contaminação era ele próprio vetor de contaminação — **CONFIRMADO (achado NOVO), CURADO**

Este não estava no seu relatório: saiu do debate sobre ele, e é o mais
irônico. `.claude/scripts/check_contamination.py` **hardcodava a
identidade do mantenedor** e **é entregue ao adopter** — e o próprio
módulo estava em `_ALLOWLIST_EXACT`, isto é, **auto-exento** da própria
verificação. Era exatamente isso que deixava a identidade passar.

Curado em `4f750f0`: o hardcode saiu, a auto-exenção morreu, e existe
guard unitário (`test_check_contamination.py`) mais guard de instalação em
`scripts/tests/smoke-install.sh`. Verificado: o step `Run smoke install`
sai `success` no CI.

---

## O oitavo item — que o relatório não viu, e é o que mais importa para você

**O `upgrade.sh` NUNCA entregou `.github/` nem `docs/`.** Medido:
`grep -c 'github' scripts/upgrade.sh` = **0**; as 3 ocorrências de `docs`
são comentários, zero sítios executáveis.

**Consequência concreta:** você instalou em 2026-08-16. Todo upgrade que
rodar **mantém os templates de CI e a doc de branch-protection daquela
versão, para sempre.** Nenhum upgrade os atualiza. Inclusive as curas de
A2 e A3 acima — elas estão no framework, e **não chegam a você por
upgrade**.

**O que isso significa na prática, hoje:** o `Smoke Install` do nosso CI
está **vermelho de propósito** por causa disso, e o vermelho é o estado
correto até a cura sair. A cura toca três scripts canônicos, exige
cerimônia de assinatura, e está bloqueada numa decisão sobre como migrar
instalações históricas como a sua — porque **nenhuma inspeção de conteúdo
recupera** se um arquivo seu foi entregue por nós ou já estava lá. Errar
esse lado significaria tomar posse de arquivo seu, e o `uninstall.sh`
remove o que o manifesto registra. Preferimos a decisão explícita à
adivinhação.

**Contorno até então:** para pegar as curas de A2/A3, copie à mão de
`templates/.github/` do framework, ou reinstale em vez de dar upgrade.

## Dois defeitos GRAVES do installer, reproduzidos nesta investigação

Não estavam no seu relatório e não afetam quem já instalou — afetam a
**próxima** instalação. Reproduzidos com installs reais, não por leitura:

1. **Escrita fora do diretório de destino.** `install_docs_template`
   guarda o destino com `[[ -e "$dst" ]]`, e esse teste **segue**
   symlink: um link **pendente** faz o teste dar falso e a cópia escreve
   **através** do link, fora da sua árvore. A defesa existe um estágio
   depois no mesmo arquivo, e falta aqui.
2. **`--github-owner` com `/` no valor** aborta o install (`exit 1`) e
   deixa `.github/CODEOWNERS` de **0 bytes** — que passa a ser pulado
   como "já existe" **para sempre**. Nenhum install ou upgrade posterior
   corrige.

Ambos vão para plano próprio de segurança. Se você for reinstalar: não
use `/` no valor de `--github-owner`, e confira que não há symlinks
pendentes em `docs/` no destino.

---

## Resumo

| # | Achado | Veredito | Estado |
|---|---|---|---|
| A1 | ponteiro absoluto | confirmado | **aberto** — precisa de cerimônia |
| A2 | steps de CI impossíveis no adopter | confirmado | **curado** (`4f750f0`) |
| A3 | script não-entregue no benchmarks | confirmado | **curado** (`4f750f0`) |
| A4 | VETO em `name-only` | confirmado, pior que reportado | **curado na autoridade** (`ed4d1cf`) |
| A5 | 71 timeouts de hook | reproduzido | 70/71 são nossos; teto em avaliação |
| A6 | CODEOWNERS com handle da org | **RECUSADO** — mecanismo explicado | mas ver o achado adjacente dos 11 placeholders crus |
| A7 | guard de contaminação contamina | confirmado (novo) | **curado** (`4f750f0`) |
| — | **upgrade nunca entrega `.github/`/`docs/`** | **novo, o mais consequente** | **aberto**, bloqueado em decisão de migração |

**Nada aqui exige ação sua**, exceto os dois `grep` sugeridos (A6) e a
cautela na próxima reinstalação. As curas confirmadas chegam por upgrade
— **menos** as de A2/A3, que dependem do oitavo item.
