---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer
generated_at: 2026-08-26T20:07:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano acerta os DOIS defeitos e acerta a forma da cura (função compartilhada, validação antes da escrita,
  escrita atômica). Os defeitos são reais: reproduzi a F2 em sandbox — `sed "s/{{OWNER_HANDLE}}/a\/b/g"` sai
  `rc=1` e deixa o destino com **0 bytes**, porque o `>` cria o arquivo antes de o `sed` abortar.
- O ponto forte é a doutrina "curar a classe, não o sítio". O ponto fraco é que o plano **não sabe onde a classe
  mora**: as três âncoras que cita (`install.sh:1466-1472`, `:2139-2159`, `:1508`) estão STALE em `b07be9b`, e a
  que ele chama de "a defesa que já existe" (`:2139-2159`) não contém defesa nenhuma — é `install_protocol_pointer`
  fazendo a sua PRÓPRIA escrita desguardada.
- O achado que muda o desenho: as curas que o plano quer escrever **já existem, no `upgrade.sh`**, em três eixos
  (validação de handle, recusa de hard link, escrita atômica). Escrever versões novas no `install.sh` é literalmente
  a classe "ramo local por omissão" que o próprio plano diz combater.

## Risks

1. **R-SEC1 — CRITICAL.** A W1 cura `install_docs_template` e deixa a classe viva. No `install.sh` vivo há **pelo
   menos cinco** escritores de destino sem guarda de symlink, e só UM é alvo da W1: `install_reference_personas`
   (`:1446` teste `-e`, `:1450` `cp`), `install_docs_template` (`:1514`, `:1520`), o render do CODEOWNERS (`:1626`,
   `:1643`), `install_protocol_pointer` (`:2139`/`:2142`, redirect incondicional) e `portable_sed_inplace`
   (`:2174-2175`). `_assert_no_symlink_parents` (`:863-882`) tem **um único chamador**, `install_one:910`
   (confirmado por `grep`).
   *Mitigação:* o escopo da W1 é o CONJUNTO de escritores, enumerado pelo censo, e o AC-1 exige que os cinco chamem
   a mesma função — prova comportamental (reverter a função deixa os CINCO vermelhos), nunca `grep`.

2. **R-SEC2 — CRITICAL.** O sítio da F2 é ELE PRÓPRIO um sítio da F1, e a W1 não o alcança: o render do CODEOWNERS
   não passa por `install_docs_template`. `:1626` testa `[[ -e "$dst" ]]` (segue o link), `:1642` faz
   `mkdir -p "$TARGET/.github"` sem checar componentes, e `:1643` escreve com `>`. Symlink pendente em
   `$TARGET/.github/CODEOWNERS` — ou um `$TARGET/.github` que seja symlink — escreve FORA do target. A partição
   "W1 cura F1, W2 cura F2" deixa esse vetor aberto entre as duas waves.
   *Mitigação:* tratar F1 e F2 como uma superfície só; `:1626-1645` recebe a guarda de destino antes de qualquer
   decisão de escrita, e a fixture (a) da W2 ganha uma perna com symlink pendente, não só com `/` no handle.

3. **R-SEC3 — HIGH.** O validador de handle que a W2 quer escrever **já existe** em `scripts/upgrade.sh:3699-3701`,
   com um comentário que nomeia ESTE defeito: «no "/" (the sed delimiter that produced the 0-byte CODEOWNERS in
   PLAN-183 §9.2)». O `install.sh` não valida em lugar nenhum (`GITHUB_OWNER` só aparece em `:371`, `:479`, `:1618`,
   `:2829`). Uma segunda implementação recria a assimetria que produziu D1–D4.
   *Mitigação:* extrair a gramática para UM dono compartilhado — o candidato natural é
   `scripts/_framework_manifest_set.sh`, que já hospeda `_wbm_source_confined` e é sourced pelos três scripts — e
   converter `upgrade.sh:3699` em consumidor no MESMO patch.

4. **R-SEC4 — HIGH.** A guarda correta não é um teste `-L` na folha. Quatro vetores irmãos ficam abertos:
   (i) **pai symlink** — `mkdir -p` sobre um pai existente sucede em silêncio e o `cp` escreve através;
   (ii) **hard link** — `-L` não vê, e o `cp` escreve no MESMO inode, alterando o arquivo de fora;
   (iii) **`..` no relpath** — `_assert_no_symlink_parents` caminha componentes mas não recusa `..`, e `$TARGET/..`
   passa por não ser link; (iv) **glob** — `:872` faz `for comp in $parent_rel` sem aspas e sem `set -f`, então um
   componente com `*` sofre expansão de pathname. (i)–(iii) estão dentro de "não escrever fora do diretório que
   recebeu"; (iv) é robustez que a reutilização torna alcançável.
   *Mitigação:* a função compartilhada é um predicado de CONFINAMENTO DE DESTINO espelhando `_wbm_source_confined`
   (`_framework_manifest_set.sh:621-667`): recusa relpath não-confinado (absoluto, com `..`, vazio), caminha os
   componentes com `-L`, e recusa `nlink > 1` na folha. O guard de hard link **também já existe** — `_up_tpl_nlink`
   (`upgrade.sh:3842-3864`). Reusar, não reescrever.

5. **R-SEC5 — HIGH.** A W2 nomeia UM sítio de interpolação; há **três**. `:1643` é a escrita; `:1635` é a MESMA
   `sed` dentro do probe de byte-compare, com `2>/dev/null` — handle inválido aborta o probe em silêncio, o `cmp`
   nunca roda e `_append_delivered_template` nunca é chamado, produzindo drift no manifesto de entrega; `:2193`
   (`_add_sub "OWNER_HANDLE" "$GITHUB_OWNER"`) é outro motor, que escapa `[|&\\]` mas não newline. Além disso
   `:2829` **persiste o handle não validado** no install-state, e `upgrade.sh:4361` o relê por um validador que faz
   `sys.exit(3)` — o upgrade degrada em silêncio para handle vazio (`:4364`).
   *Mitigação:* validar no parse (`:479`) E revalidar no escritor, e validar ANTES de persistir em `:2829`. O AC-2
   ganha uma perna: install com handle inválido não deixa `github_owner` gravado no install-state.

6. **R-SEC6 — MEDIUM.** O padrão de escrita atômica que a W2 propõe existe no repo em duas formas, e **as duas têm
   defeito**. `portable_sed_inplace` (`:2171-2176`) usa nome de temporário PREVISÍVEL — `${file}.ceo-sed-tmp` —
   dentro da árvore do target: um symlink pré-plantado nesse path faz o `>` escrever através, fora do target. E
   `:1634` faz `mktemp "${TMPDIR:-/tmp}/..."`, noutro filesystem: um `mv` a partir dali **não é atômico** (vira
   copy+unlink). Copiar qualquer um regenera a classe dentro da própria cura.
   *Mitigação:* `mktemp` no DIRETÓRIO DE DESTINO (mesmo filesystem, `mv` atômico de verdade), nome imprevisível,
   modo `0644` explícito após o `mktemp` (que cria `0600` — sem o `chmod`, o CODEOWNERS entregue fica ilegível para
   o resto do time), e remoção do temporário em `trap`.

7. **R-SEC7 — MEDIUM.** A regra "0 bytes ⇒ reescreve" muda a superfície de AUTORIZAÇÃO do adotante sem
   consentimento: um CODEOWNERS vazio é forma legítima de DESLIGAR o roteamento de revisão obrigatória, e
   reescrevê-lo re-liga donos num repositório de terceiro.
   *Mitigação:* trocar heurística por evidência — só auto-curar quando o installer pode PROVAR autoria (o
   install-state já registra `github_owner` em `:2829`; há o registro de entrega `_append_delivered_template`). Sem
   prova: `WARNING` nomeado com instrução de remoção manual, e saída não-zero sob `--strict-placeholders`. Nunca
   escrita silenciosa.

8. **R-SEC8 — MEDIUM.** `--github-owner org/team` **é sintaxe válida de CODEOWNERS** (o `@` está no template —
   `templates/.github/CODEOWNERS.template:14` — e o valor completa `@org/team`). O input que dispara a F2 não é um
   erro de digitação: é caso de uso legítimo, e a gramática estreita o REJEITA sem o plano declarar isso.
   *Mitigação:* decisão explícita e documentada. Recomendo manter a gramática estreita (é o que `upgrade.sh:3700`
   já decidiu) e, no texto da falha, dizer que handles de TIME não são suportados por esta flag, apontando a edição
   manual do `.github/CODEOWNERS`. Suportar time exigiria delimitador não-`/` e é wave própria.

9. **R-SEC9 — LOW.** Os dois precedentes de guarda **discordam do veredito**: `_assert_no_symlink_parents` faz
   `exit 1` (aborta a run inteira); `apply_placeholder_substitutions:2293-2304` faz `SKIP` e continua. A função
   compartilhada tem de escolher, e a escolha é de segurança — `SKIP` é fail-open na entrega (o adotante
   silenciosamente não recebe o arquivo).
   *Mitigação:* veredito em dois níveis — recusar a ESCRITA de forma nomeada, acumular, e falhar a RUN no fim com o
   sumário. Nem aborto no meio da entrega, nem silêncio.

## Must-fix (blocking)

1. **Re-derivar as âncoras contra a árvore viva antes de qualquer patch.** As três citadas estão erradas em
   `b07be9b`: F1 está em `:1514`/`:1520` (não `:1466-1472`, que hoje é `_install_src_refuses`); F2 está em `:1643`
   (não `:1508`); e `:2139-2159` **não contém guarda de symlink**. O Scope da cerimônia deriva do patch, e patch
   escrito sobre âncoras stale não é revisável.
2. **Escopo da W1 = o conjunto de escritores, não `install_docs_template`.** Curar os cinco sítios de R-SEC1 pela
   mesma função, com prova comportamental. Censo que sai zero desguardados enquanto quatro seguem desguardados é
   falso-verde — e o AC-3 depende dele.
3. **Incluir o sítio do CODEOWNERS (`:1626-1645`) na guarda de destino** (R-SEC2), com asserção nos BYTES do alvo
   externo na fixture nova.
4. **Reusar, não reescrever, o que o `upgrade.sh` já tem** (R-SEC3, R-SEC4): gramática de handle
   (`upgrade.sh:3699-3701`) e recusa de `nlink > 1` (`upgrade.sh:3842-3864`) viram dono compartilhado, com o
   `upgrade.sh` convertido em consumidor no MESMO patch. Duas cópias divergindo é o mecanismo exato de D1–D4.
5. **A guarda de destino é um predicado de confinamento**, não um `-L` na folha: recusa `..`/absoluto, caminha
   componentes, recusa hard link, e corrige o `for` sem aspas de `:872` (R-SEC4).
6. **Validar no parse E antes de persistir** (R-SEC5): `:479` e `:2829`, além dos três sítios de interpolação.
7. **Escrita atômica correta** (R-SEC6): `mktemp` no diretório de destino, `0644` explícito, `trap` de limpeza.
   Copiar `portable_sed_inplace` ou o `mktemp` em `/tmp` de `:1634` é regenerar a classe dentro da cura.
8. **A auto-cura de 0 byte exige evidência, não heurística** (R-SEC7).
9. **A classe entra em `docs/threat-model.md` e num ADR.** Hoje o arquivo modela symlink/hardlink/`..` só para
   extração de tarball (`:639`); a superfície de ESCRITA DE DESTINO do installer não está no contrato. Aviso
   operacional: o `CLAUDE.md` §5 registra que `check-threat-model-freshness.py` REESCREVE esse arquivo
   (`accepted→stale`) e derruba o P0 do SIGN — planejar o passo, não descobri-lo na cerimônia.

## Nice-to-have (advisory)

1. Alinhar a gramática com a regra real do GitHub: o regex vivo (`upgrade.sh:3700`) aceita hífen final e hífens
   consecutivos, que o GitHub recusa. É nit de correção, **não** de segurança — a propriedade que importa é o
   conjunto fechado `[A-Za-z0-9-]` não conter metacaractere de `sed`. Não verifiquei a doc do GitHub nesta rodada
   (sem rede); se a exatidão importar, é checagem externa a designar, com a fonte citada no resultado.
2. O ramo `DRY_RUN` de `install_docs_template` (`:1506`) tem o mesmo `-e`: o preview mente sobre symlink pendente
   ("would COPY"). Não escreve, mas é o output com que o adotante decide.
3. `portable_sed_inplace` (`:2310`, `:2328`) imprime `SUBSTITUTED` incondicionalmente após a chamada; hoje
   `set -euo pipefail` (`:209`) salva o caso, mas a mensagem está desacoplada do resultado.
4. Estender o censo a `upgrade.sh` e `doctor.sh` no mesmo passo — a assimetria medida aqui é bidirecional.

## Unseen by the original plan

1. **A assimetria install/upgrade é a causa-raiz, e é tripla.** Validação de handle, recusa de hard link e escrita
   atômica existem no `upgrade.sh` e faltam no `install.sh`. F1 e F2 não são dois defeitos com curas pequenas: são
   dois SINTOMAS de "o `upgrade.sh` foi endurecido pelo rail e o `install.sh` não". Isso muda o desenho — extração
   para dono compartilhado, não patch local.
2. **A F2 é disparada por um input LEGÍTIMO** (`@org/team`), não por erro de uso (R-SEC8).
3. **O handle inválido tem consequência a jusante**: persistido sem validação em `:2829`, degrada silenciosamente a
   entrega de CODEOWNERS no upgrade seguinte (R-SEC5). A recuperabilidade do AC-2 é mais ampla que "arquivo de 0
   bytes".
4. **A cura da W2 pode reintroduzir a F1**: `mv` sobre um destino que é symlink SUBSTITUI o link por arquivo
   regular — mais seguro que o `cp`, mas destrói em silêncio um symlink deliberado do adotante. Precisa de guarda,
   não de sorte.
5. **TOCTOU entre a checagem e a escrita** é residual irredutível em shell. Não é motivo para não guardar; é motivo
   para DECLARAR: a guarda reduz a janela, não a fecha, e o alvo compartilhado do §5 é o cenário onde ela importa.
6. **`_assert_no_symlink_parents` aborta com `exit 1` no meio da entrega**, dependendo do trap de rollback. Reusá-la
   em cinco sítios multiplica os pontos de aborto parcial (R-SEC9).

## What I would NOT change

1. **A partição W0 → W1+W2 em UMA cerimônia.** Mesma superfície, mesmo Scope. Duas cerimônias pagariam o custo em
   dobro e abririam a janela do R-SEC2 entre elas.
2. **A doutrina do censo invertido** (enumerar as formas provadas seguras, resto `indeterminado`). É a resposta
   correta a uma classe que regenerou em quatro rodadas de rail, e é o que impede o instrumento de ficar decorativo.
3. **A asserção nos BYTES do alvo externo, não no exit code.** É a diferença entre provar que a escrita não
   aconteceu e provar que o script reclamou. O defeito atual sai `exit 0`; teste de exit code não o pegaria.
4. **A ordem "conteúdo positivo antes da negativa"** na fixture (b) — 1442 bytes, 33 linhas, handle ≥1× e SÓ DEPOIS
   `grep -c == 0`. A negativa sozinha é satisfeita por arquivo vazio, que é o estado do defeito.
5. **A limitação honesta do §5.** "Reproduzido, sem evidência de exploração" está no tom certo: o vetor realista é
   target compartilhado ou repo clonado de terceiro, e isso situa a urgência sem reduzir a gravidade da cura.

---

## Posições diretas às quatro perguntas do CEO

**1. "Recusar qualquer destino symlink" basta?** Não. Cobre a folha e deixa pai symlink, hard link, `..` e glob
(R-SEC4). Em escopo de "não escrever fora do diretório que recebeu" estão pai, hard link e `..`. A guarda mínima que
fecha a CLASSE é o predicado de confinamento de destino espelhando `_wbm_source_confined`, com dono compartilhado, e
`nlink > 1` reusado de `upgrade.sh:3842`. TOCTOU e case-insensitive ficam como residual DECLARADO — o segundo não
atravessa a fronteira do target; o primeiro é irredutível em shell. `cp` seguindo symlink na FONTE já está fechado
por `_install_src_refuses` (`:1470-1481`).

**2. Conjunto de caracteres e onde validar.** Conjunto `^[A-Za-z0-9][A-Za-z0-9-]{0,38}$`, fonte operativa **no
repo**: `scripts/upgrade.sh:3699-3701`, que já decidiu isso citando este mesmo defeito. A propriedade de segurança é
o conjunto fechado não conter `/`, `&`, `\`, `|`, newline nem espaço; a exatidão perante a doc do GitHub é nit
(advisory 1). Validar **nos dois lugares**: no parse (`:479`), único ponto que cobre os três sítios de interpolação
de uma vez; e no escritor, porque `GITHUB_OWNER` é global e o próximo chamador não passa pelo parse. Não é
duplicação — é o mesmo predicado compartilhado invocado em duas fronteiras.

**3. Escrita atômica e recuperação.** O risco do "0 byte ⇒ reescreve" é real e é de autorização, não de dados
(R-SEC7): a cura correta é prova de autoria, não contagem de bytes. O temporário vai no diretório de DESTINO —
`/tmp` quebra a atomicidade do `mv` por cruzar filesystem, e é o padrão que `:1634` usa hoje. Nome imprevisível é
obrigatório: `portable_sed_inplace:2174` demonstra o furo com nome fixo. E sim, `0644` explícito — `mktemp` cria
`0600`, e um CODEOWNERS ilegível para o time é regressão silenciosa.

**4. O que torna o VERDE do censo significativo.** Significativo: controle positivo **por forma** provada segura
(remover aquela guarda ⇒ vermelho NOMEANDO o path); piso não-zero (contagem 0 REPROVA, já no §W0); escopo declarado
e impresso pelo próprio instrumento; baseline rastreado cujo drift falha em vez de auto-atualizar; e execução sobre
a árvore ESTAGIADA depois da última edição (`CLAUDE.md` §4 — gate de corpus roda após o último `git add -A`, nunca
antes). Decorativo: classificar por `grep` de comentário-marcador em vez de derivar comportamentalmente; contar
`indeterminado` como PASS; e rodar só sobre `install.sh` enquanto `upgrade.sh` e `doctor.sh` hospedam a mesma classe.
