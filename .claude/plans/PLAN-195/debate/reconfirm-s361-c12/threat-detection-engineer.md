---
plan: PLAN-195
ceremony: reconfirmação de VETO por diff — item C12 (resíduo 13), S361
archetype: Threat Detection Engineer
skill: security-and-auth (§Detection-as-Code; SKILL.md sha256=50cd673f…9a80, conferido)
agent_persona: Principal Threat Detection Engineer (VETO de escopo estreito — cobertura, falso-positivo, qualidade do sinal, eventos de auditoria do guarda)
subject_sha256: 93e4b83f4fd4fa848385f1cb0e92b610226588e468fbc7e8f3f3ce13adda5379
base_sha256: e05f5f3f5d11c7910509bcbeb34255bb00295675198b2a6441896d8b0d4067d3
generated_at: 2026-10-02T08:36:17Z
veto: RETIRADO MANTIDO (sha256 93e4b83f…5379), com as condições N1–N3
---

# Reconfirmação do VETO por diff — Threat Detection Engineer (item C12)

## Sujeito (o veredito vale só para ele)

- Arquivo: `.claude/plans/PLAN-195-bash-guard-indirect-execution.md`.
- **Sujeito:** a cópia da worktree destacada (sombra, HEAD `399efbaa`, plano modificado e não
  commitado). sha256 calculado por mim: `93e4b83f4fd4fa848385f1cb0e92b610226588e468fbc7e8f3f3ce13adda5379`.
- **Base:** `git show f829b29a:<arquivo>` (main de hoje) dá `e05f5f3f…67d3`. O mesmo valor sai do
  arquivo na árvore do main e de `git show 399efbaa:<arquivo>`: a sombra parte do mesmo texto.
- **Ponte com a minha retirada anterior** (`reconfirm-s361/threat-detection-engineer.md`, sobre
  `c8cec366…a1ff`, commit `6a9abb10`). Li também o diff `6a9abb10..304ec478` do arquivo: cabeçalho
  `external_wait`, caixa do checklist, «How to continue», histórico e o C11 trocado de PENDENTE
  para REGISTRADA, com as condições incorporadas por remissão. Pelo meu próprio registro, nada
  disso reabre a reconfirmação. Nenhuma linha da Thesis, do Goal, dos escopos ou da Prova mudou
  nesse trecho.
- **Diff integral base → sujeito:** dois blocos, nenhuma linha apagada.
  1. A remissão «→ item C12: resíduo 13.» depois do item 12 da lista de residuais do Goal.
  2. O item C12 no fim do apêndice «Correções pós-debate S360».
- **Código byte-idêntico.** `check_bash_safety.py`, `check_canonical_edit.py` e
  `check_bash_canonical_forensic.py` comparam iguais (`cmp`) entre o main e a sombra.
  `git diff 399efbaa f829b29a` vem vazio para `.claude/hooks`, `SPEC`, `.claude/settings.json`,
  `.claude/scripts/audit-query.py` e os dois docs da W0.

## Âncoras do C12 conferidas no código

- **`check_bash_safety.py:2222-2240` — confere.** O `_is_canonical` do E3 tira só um `./`
  inicial do candidato relativo. Para o absoluto, faz `normpath` de texto e relativiza só se o
  prefixo for byte-igual à raiz. Não dobra caixa. Não colapsa segmentos redundantes no caminho
  relativo. Também não relativiza um absoluto cuja raiz venha em outra grafia.
- **`check_canonical_edit.py:949-985` — confere, com uma imprecisão.**
  - É o casador cru por segmento (`fnmatch.fnmatchcase`), que o E3 importa direto
    (`check_bash_safety.py:2214-2218`) com os padrões sem dobra.
  - Porém a guarda de Edit/Write NÃO casa com caixa. O classificador dela resolve o caminho
    (`_repo_rels`, `:821`) e dobra a caixa nas duas metades, prefixo e glob (`PLAN162_FIX_CASEFOLD`,
    `:866-912`).
  - Logo, «a guarda casa com caixa» vale para o uso que o E3 faz do casador, não para a guarda
    de Edit/Write. Ver N3 (c).
- **`check_bash_safety.py:2531-2534` — confere.** O arquivo recusa resolver no hook um caminho
  fornecido pelo atacante: syscall no orçamento do hook, `RuntimeError` em laço de symlink, TOCTOU.
  O mesmo parágrafo (`:2522-2526`), porém, registra a outra metade do molde, que o C12 não cita:
  um sinal SÓ DE TEXTO na CRIAÇÃO do link que nomeia o caminho protegido (`_E4_LINK_RUNNERS`,
  `:2862`). Ver N2.

## Pergunta 1 — a lacuna tem detecção nula? O forense a vê?

**Não é nula. É nula no bloqueio e parcial no registro pós-fato, e esse registro não tem leitor.**

- **PreToolUse (E3): nula** nas três variantes: caixa, segmentos redundantes em alvo relativo e
  apelido. Lembrete: hoje nem o bloqueio canônico do E3 emite evento (W2 item 6).
- **PostToolUse (forense): parcial, por leitura de código.**
  - O `check_bash_canonical_forensic.py:63-69` classifica com o MESMO classificador da guarda de
    Edit/Write (`check_canonical_edit._is_canonical`, `:937`). Esse classificador resolve o caminho
    (colapsa segmentos redundantes, segue symlink) e dobra a caixa ASCII.
  - Logo, nas QUATRO formas de escrita que a regex do forense extrai (`:44-49`: redirecionamento
    e anexação precedidos de espaço, primeiro operando de `tee`, último token de `sed -i`), um alvo
    literal em outra grafia, ou por symlink, provavelmente GERA `canonical_edit_completed` com
    `sentinel_hint`.
- **O que o forense NÃO vê:**
  - os verbos de cópia, movimento, destruição e `touch` (o E3 os cobre só na grafia da guarda);
  - o apelido por hard link: `resolve()` não o desfaz, e a criação também passa no E3, que checa
    só o destino do `ln`, `:2364-2374`;
  - a raiz de um caminho absoluto em outra caixa (`relative_to` compara bytes);
  - a criação do apelido em si (não há forma de `ln` na regex).
- **Qualidade do sinal: ninguém lê por padrão.**
  - Nenhum teste fixa o comportamento do forense sobre grafia variante: o
    `test_bash_canonical_forensic.py` não o exercita.
  - `canonical_edit_completed` está fora de `_CRITICAL_SECURITY_ACTIONS` (`audit-query.py:2553`) e
    nenhum check de boot ou do nightly o consome. Só sai por consulta ad hoc com `--action`.
  - É detecção que dispara sem leitor. NÃO conta como cobertura.
- **Método.** Não executei nem simulei nenhum comando da classe. Tudo acima vem da leitura do
  código.

## Pergunta 2 — o C12 diz isso com honestidade?

**Sim quanto à lacuna; é omisso quanto à detecção, mas sem prometer nada.**

- O C12 não afirma nenhuma detecção. Declara a subclasse pela forma, cita âncoras verdadeiras e
  deixa o resíduo fora do escopo da W2 com duas razões verificáveis: escopo pré-registrado no
  debate e syscall recusada pelo próprio arquivo.
- As duas imprecisões são de grau P2 e não afrouxam nada:
  - «a guarda casa com caixa» (N3 (c));
  - a omissão do sinal de criação, só de texto, que o mesmo parágrafo citado documenta (N2).
- **Compatibilidade com as minhas condições de `reconfirm-s361`** (todas seguem valendo):
  - o C12 não toca a (k), o K1, o kill-switch, o replay diferencial nem o C4;
  - se a W2 trouxer a metade de grafia, as transições serão ALLOW→BLOCK, nunca BLOCK→ALLOW, e a
    condição 3 segue intacta.

## Pergunta 3 — basta declarar como resíduo, ou precisa de dono com prazo?

**As duas metades são diferentes.**

- **Metade de grafia** (caixa ASCII, segmentos redundantes em alvo relativo, raiz em outra caixa):
  NÃO é incompletude por construção.
  - Há cura só de texto com precedente no próprio repositório: `PLAN162_FIX_CASEFOLD` nos dois
    trilhos de Edit/Write, que o PLAN-162 tratou como P0, e `_E4_TOGGLE_PATHS_FOLDED` no próprio
    `check_bash_safety.py`.
  - Declarar como resíduo sem dono deixaria uma lacuna curável sem responsável.
  - O C12 já aponta o ponto de decisão: a abertura da W2. Falta garantir dono nos dois desfechos.
    Isso é a N1.
- **Metade de apelido:** o USO, por symlink ou hard link, é resíduo por construção, como os
  itens 2 e 3. A declaração basta. A CRIAÇÃO tem sinal literal barato. Isso é a N2, em grau P2.

## Pergunta 4 — a W0 reproduz a lacuna sem prometer detecção?

**Reproduz, sem prometer.** A §6.6 da W0 traz os 13 itens: os 12 do Goal e o 13, com a mesma
forma do C12. O §1.2 e a linha 2 do `docs/threat-model.md` nomeiam a «Class B» e marcam o dono
NONE.

**Mas a W0 afirma uma ausência que o código desmente em parte.** Três trechos:

- a §6.6 diz «Detection: … the `PreToolUse` matcher is the only detection»;
- o §5 diz que o forense «does not observe … the §6.6 class»;
- a linha 2 do threat model diz «PreToolUse is the only detection».

Para a subclasse de grafia nas quatro formas do forense, isso é falso no sentido seguro: o erro
subdeclara. Como o propósito da W0 é a cobertura REAL, isso entra como condição de land da W0 (N3).
A condição não toca o plano.

## Condições novas (somam-se às 8 de `reconfirm-s361/threat-detection-engineer.md`)

**N1 — Abertura da W2: dono da metade de grafia nos dois desfechos.**

- A abertura da W2 registra a decisão sobre a metade de grafia: caixa ASCII, segmentos
  redundantes no alvo relativo e raiz de caminho absoluto em outra caixa.
- **Se ficar fora:** no mesmo ato abre-se um FU nomeado `PLAN-195-FOLLOWUP-<slug>`, com gatilho,
  como os residuais 11 e 12.
- **Se a W2 for congelada ou o plano fechar sem ela:** o FU abre nesse ato.
- **Se entrar:**
  - (a) reusar o classificador dobrado da guarda, com as duas metades dobradas (prefixo e glob).
    Dobrar uma só é a classe do portão morto;
  - (b) a normalização léxica que a W2 aplicar ao alvo vindo de `cd` no mesmo comando vale também
    para o alvo relativo literal sem `cd`, ou a diferença fica declarada;
  - (c) o bloqueio grava EXATAMENTE UM `veto_triggered` com `reason_code` próprio, conforme a (k);
  - (d) as transições ALLOW→BLOCK da dobra (sobreclassificação em sistema de arquivos sensível a
    caixa) entram no replay com contagem e denominador.

**N2 (P2) — Abertura da W2: sinal de criação do apelido.**

- A abertura da W2 registra também, dentro ou fora, o sinal só de texto na criação de link cujo
  operando de ORIGEM seja um caminho canônico literal (molde `_E4_LINK_RUNNERS`,
  `check_bash_safety.py:2522-2526`), ao menos como registro advisory.
- Se ficar fora, o texto do resíduo 13 diz que a criação do apelido não é vista por nenhum dos dois
  hooks e que o hard link tem detecção zero.

**N3 (P2, condição de land da W0; não reabre o plano)** — corrigir os três trechos da Pergunta 4.

- (a) Trocar a negação absoluta por: o forense classifica com o classificador da guarda de
  Edit/Write (resolve o caminho, dobra a caixa ASCII). Por leitura de código, pode registrar depois
  do fato um alvo literal em outra grafia, só nas suas quatro formas. Nenhum teste fixa isso, e o
  evento não tem leitor padrão. NÃO conta como cobertura.
- (b) Manter «NONE» como dono da classe.
- (c) Na §6.6 Class B, dizer que o E3 usa o casador cru por segmento, com caixa. A guarda de
  Edit/Write dobra a caixa (`PLAN162_FIX_CASEFOLD`).
- A mesma precisão de (c) entra no texto do C12 na próxima edição do plano que já reabra a
  reconfirmação, ou como incorporação de condição, que pelo C11 não reabre.

## Observações (pré-existentes, fora do C12; não são condição)

- **O1.** O `_comment` do hook forense em `.claude/settings.json:507` afirma uma forma de
  `git checkout` que `_WRITE_PATTERNS` (`check_bash_canonical_forensic.py:44-49`) não tem. É uma
  afirmação de cobertura sem código, num arquivo canônico. Fica para a próxima cerimônia que tocar
  o `settings.json`, ou vira FU.
- **O2.** `canonical_edit_completed` dispara sem leitor (ver Pergunta 1). É candidato a FU de
  consumo: categoria em `audit-query.py` ou check de boot. Sem isso, o registro pós-fato do forense
  vale só para forense manual.

Divulgação: este registro nomeia a subclasse e as variantes só pela forma. Nenhuma string concreta
de comando ou de caminho variante aparece aqui, e nenhum comando da classe foi executado ou
simulado.

VETO: RETIRADO MANTIDO (sha256 93e4b83f…5379), condições N1–N3 somadas às 8 de `reconfirm-s361`
