# rail-record — W7a do PLAN-183, pacote de CÓDIGO (molde sign-min): rodadas do patch e rodada única do texto e dos dados

Rail-Subject: .claude/plans/PLAN-183/w7a/w7a.patch
Rail-Subject-sha256: 84371b9f58b17006c8438bd6f0683ed371603dc4fd477c8f73ee25f41432979e
Rail-Subject-patch-id: 341f0bafd41be57caeabc091a8ee7af3994a0305
Rail-Sentinel: .claude/plans/PLAN-183/w7a-approved.md
Rail-Sentinel-sha256: d778876021af031edc8ad27ca8d3456e00f49a6b9320cb655b42f91519244b5e
Rail-Data: .claude/plans/PLAN-183/w7a/sign.tsv
Rail-Data-sha256: 6c927476564ee9454fa28a8dada3ea0ceedffdf13fe70e34c03464bbbc3e66cd
Rail-Verdict: PENDENTE

Este registro tem duas partes. A primeira é a rodada ÚNICA do molde sign-min sobre o texto do sentinel (com os
quatro campos por preencher), os dados `sign.tsv`, o envoltório `hard-w7a.sh` e o `red-control.txt`, com o
patch acima inalterado; a rodada 1 rodou sobre o texto anterior, o anexo dela muda o texto e o envoltório, e o
veredito acima fica `PENDENTE` até a conferência do anexo terminar (o P0 do SIGN recusa qualquer valor fora de
`APPROVE` e `DECLARED-P2`). A segunda é o histórico das rodadas do patch (r1 a r3
e as conferências r3x e r3y), copiado do registro anterior do pacote: o patch revisado nelas é este, byte a byte
(`git diff --full-index --no-renames 0a953ece 94483a01` da sombra w7a, mesmo sha256 e mesmo patch-id).

## Rodada única do molde (texto, dados, envoltório e registro do controle vermelho)

- Estado: PENDENTE (nenhuma lane rodou sobre os sha256 acima).
- Rodada 1 (materiais de `e539268f`, sentinel de sha256 `84a35d54…`, dados `6c927476…`, patch inalterado):
  Codex 0.160.0 «VERDICT: GO-WITH-CONDITIONS» — P2: conferências de saída de `validate_governance_fast.py`
  («PASS») e `validate-governance.sh` («Errors:   0») julgadas só pelo rc; P2: o envoltório não confinava o
  bytecode dos descendentes e não declarava a retenção do diretório de trabalho em falha; P3: conferências do
  SIGN anterior retiradas sem declaração (registro de worktree, URL do remote, sondas de modo e GID, cruzamento
  verbatim do rail); P3: o `grep` do «{{» tratava rc 2 como ausência. Lanes Claude: código «VERDICT: GO» e
  segurança «VERDICT: GO», só P3 (entre eles, o arquivo do follow-up `PLAN-183-FOLLOWUP-json-census-call-binding`
  ainda não existe). Anexo único: equivalência do rc declarada no sentinel, com as linhas do código;
  `PYTHONDONTWRITEBYTECODE=1` exportado pelo envoltório, com o resíduo do replay e a sonda declarados; retenção
  em falha declarada; seção das conferências aposentadas e do que as substitui; `grep` com rc 0, 1 e outro
  tratados à parte; o follow-up declarado como criado no backlog da v1.4.4. `sign.tsv` e patch inalterados.
- Checklist da rodada: cada frase do sentinel fora do bloco comum é verdadeira no código; o bloco comum é o do
  molde; nenhum comando do SIGN anterior do pacote sumiu (os gates genéricos estão na lista fixa do molde; os
  específicos estão nas linhas `hard` ou, os da passada dirigida, nas duas passadas do molde, todos no
  `testpaths`); o envoltório sai com rc diferente de 0 quando qualquer conferência dele falha; o controle
  vermelho (a), a perna vermelha (b) e o C6 do `red-control.txt` são reproduzidos sobre as pré-imagens.
- Lanes: Codex + 2 refutadores Claude, na mesma rodada; no máximo uma conferência de anexo.

## Rodadas do patch: triagem (copiada do registro anterior)

- r1 (sujeito `0a953ece..5549a6b3`): Codex «NENHUM ACHADO», GO. r-w7a-a (testes, entrega, mutantes,
  condições): GO-WITH-CONDITIONS, dois P3 (o teste da pasta reprovava com um `.DS_Store`; a declaração do
  resíduo do plugin no ADR-158) e as condições do LAND (listagens com `--no-renames`, bateria numa máquina
  descarregada, C8/C9 registrados). r-w7a-b (injeção pelas fixtures, fail-closed, marcador):
  GO-WITH-CONDITIONS, um P2 (`UnicodeDecodeError` e `RecursionError` fora da tupla de exceção viravam
  traceback sem RED nomeado) e dois P3 (chave duplicada e NaN aceitos nas fixtures). Curas em `3ee7ef68`.
- r2 (sujeito `0a953ece..3ee7ef68`, foco `5549a6b3..3ee7ef68`): Codex NO-GO, um P2 (settings e decisão do hook
  sob teste aceitavam NaN/Infinity: falso verde reproduzido). Só a lane Codex está registrada em
  `night/rail/w7a-r2`. Cura em `a4cdc545`.
- r3, FINAL (sujeito `0a953ece..a4cdc545`): Codex NO-GO por AFIRMAÇÃO FALSA reproduzida («NaN/Infinity
  recusados em TODA leitura JSON do gate»: o leitor delegado `check-active-hooks-executable.py` aceitava).
  r3-w7a-a: GO-WITH-CONDITIONS, um P3 (o censo AST deixava passar `getattr(json, "loads")`, `import
  json.decoder` e alias de `JSONDecoder`). r3-w7a-b: GO-WITH-CONDITIONS, um P2 (a decisão lia só a última
  linha do stdout: allow+block e preâmbulo+block saíam verdes) e dois P3 (o censo; o docstring do módulo de
  teste revertido sem declarar). O leitor delegado foi curado num land livre no `main` (`cf785083`); a frase
  ficou restrita ao módulo, e as curas da decisão, do censo e do docstring estão em `d893285d`.
- r3x (exceção do Owner: conferência do anexo `a4cdc545..d893285d` depois de NO-GO por afirmação falsa): Codex
  NO-GO por AFIRMAÇÃO FALSA reproduzida (o `.strip()` da decisão apagava `\x0b`, `\x0c` e NBSP, que o JSON
  proíbe: saída inválida certificada verde). rx-w7a: GO-WITH-CONDITIONS, o mesmo P2 e três P3 (o censo exigia
  só a PRESENÇA de `parse_constant`; a frase sobre o shim; «subgate curado no main», que ainda não estava). Curas
  no micro-anexo `94483a01`.
- r3y («ÚLTIMA CHANCE pré-registrada pelo Owner»: qualquer afirmação falsa reproduzida levaria a W7a à 1.4.4):
  conferência do micro-anexo `d893285d..94483a01`. Codex: «NENHUM ACHADO», GO (o bloco acima, verbatim).
  rx-w7a: GO-WITH-CONDITIONS, cada frase nova medida verdadeira, dois P3 — (1) o censo verifica o guard
  `_refuse_constant` pelo NOME: uma segunda ligação desse nome no módulo passa por ele (condição: follow-up
  nomeado no material do SIGN — `PLAN-183-FOLLOWUP-json-census-call-binding`, declarado no sentinel); (2) a
  mensagem do commit cita o `main` da medição sem data (sem frase falsa; nada no código).
- Disposição das rodadas do patch: P0=0, P1=0, P2=0 na conferência final (r3y); os P3 viram resíduo e
  follow-up declarados no sentinel; o Codex da r3y deu GO. A seção abaixo traz a saída do Codex de cada rodada
  e o VERDICT de cada lane Claude, verbatim; nas saídas das rodadas 3 e r3x, as linhas que começavam com três
  crases tiveram as crases trocadas por três aspas simples (troca declarada aqui).

## Rodadas do patch, verbatim

### Rodada 1 — Codex, sujeito 0a953ece..5549a6b3

```text
NENHUM ACHADO

VERDICT: GO
```

### Rodada 2 — Codex, sujeito 0a953ece..3ee7ef68

```text
**P2 — A cura da classe ainda permite falso verde com decisão inválida.** `.claude/hooks/check_harness_config.py:868`, também em `:221`. Resíduo preexistente, não regressão introduzida nesta rodada.

- **Reprodução:** numa instalação descartável, fiz o hook de Bash imprimir `{"decision":"block","x":NaN}`. Executando o gate com `--replay` e os três controles padrão, obtive **rc 0, zero warnings**. `JSON.parse` rejeita essa saída. `Infinity` e `-Infinity` reproduzem o problema; settings com essas constantes também passam.
- **Causa:** somente as fixtures usam `_refuse_constant`. O parser das decisões aceita constantes fora de JSON e certifica o controle como vivo, contrariando o fail-closed para input inválido. Last-wins para duplicatas não exige essa permissividade.
- **Cura:** acrescentar `parse_constant=_refuse_constant` às leituras de settings e decisões, preservando last-wins, e testar esses falsos verdes.

Os 38 testes passaram em Python 3.9/3.11; env-inventory sem deriva; fixtures entregues e tarball npm com bytes idênticos. O teste original de placeholders expirou em 120 s; a mesma asserção passou com prazo ampliado. C8/C9 completos e ensaio do LAND continuam pendentes conforme declarado.

Checkout intacto; cópias descartáveis apagadas.

VERDICT: NO-GO
```

### Rodada 3 — Codex, sujeito 0a953ece..a4cdc545

```text
**P2 — Condição: corrigir a leitura delegada ou retirar a afirmação universal “NaN/Infinity recusados em TODA leitura JSON do gate”; ela foi refutada.**

Anexo: `.claude/hooks/check_harness_config.py:590` chama o subgate cujo parser, em `.claude/scripts/check-active-hooks-executable.py:53`, continua sem `parse_constant`. O censo em `.claude/hooks/tests/test_check_harness_config.py:348` inspeciona somente o módulo principal.

Reprodução na cópia completa de `a4cdc545`:

1. Acrescentar `"rail_probe":NaN` ao objeto de `.claude/settings.json`, preservando o restante.
2. Executar:

'''bash
python3 .claude/hooks/check_harness_config.py \
  --static --settings templates/settings/settings.base.json
'''

Resultado: **rc 0**, `OK: harness-config gate green (static=yes, replay=no, 0 warning(s))`. Reproduzido também com `Infinity` e `-Infinity`. Selecionar diretamente `.claude/settings.json` retorna rc 2: a cura direta funciona, mas a leitura delegada escapa.

Cura: estender a recusa e a regressão ao leitor delegado. Caso permaneça fora deste pacote, restringir a afirmação do commit e declarar essa exceção.

Verificações adicionais: controle vermelho→verde da r2 confirmado; 39 testes passaram em Python 3.9 e 3.11; env-inventory limpo. O teste de placeholders atingiu timeout de 120 s. C8/C9 e espelhos permanecem pendências declaradas. Checkout intacto; temporários removidos.

O NO-GO decorre da **afirmação falsa reproduzida**, conforme a regra FINAL.

VERDICT: NO-GO
```

### Conferência r3x — Codex, sujeito a4cdc545..d893285d

```text
**[P2 — afirmação falsa reproduzida]** `.claude/hooks/check_harness_config.py:861–867`: a equivalência declarada com o parse do stdout inteiro pelo `json.load` é falsa. `.strip()` remove também caracteres que JSON proíbe.

**Reprodução:** na cópia, substituir `check_bash_safety.py` por:

'''python
import sys
sys.stdout.buffer.write(b'\x0b{"decision":"block"}\n')
'''

Executar o gate com `--replay` retorna **rc 0, verde, zero warnings**. O mesmo stdout produz `JSONDecodeError` em `json.load` e `SyntaxError` em `JSON.parse`. O shim no caminho Claude preserva esses bytes; no caminho Grok, aciona sua recuperação fail-closed. Também reproduzido com `\x0c` e NBSP.

**Cura:** trocar `out = proc.stdout.strip()` por `out = proc.stdout` e adicionar regressões desses prefixos. Testado na cópia: o caso passa a **rc 1, RED nomeado**, mantendo **39/39 testes verdes**. É um defeito residual que torna C-B1 incompleto e contradiz a afirmação deste anexo.

Demais verificações:

- Suíte original: **39/39**, Python 3.9.6; gate completo verde.
- Três hooks reais: um JSON de uma linha cada. Espaços JSON, CRLF e `indent=2` passam; BOM, preâmbulo e dois objetos dão RED.
- Censo: `from json import` dentro de função é barrado. `__import__`, `importlib` e `sys.modules["json"]` escapam; importações dinâmicas já estavam ressalvadas na r3-A.
- Escopo de `_refuse_constant` corrigido; docstring de `3ee7ef68` restaurado.

Cópia descartável apagada; checkout original intacto. O NO-GO decorre da afirmação falsa reproduzida em C-B1.

VERDICT: NO-GO
```

### Conferência r3y — Codex, sujeito d893285d..94483a01

```text
NENHUM ACHADO

VERDICT: GO
```

### Lanes Claude — a linha VERDICT de cada uma, verbatim

```text
r-w7a-a (rodada 1): VERDICT: GO-WITH-CONDITIONS
r-w7a-b (rodada 1): VERDICT: GO-WITH-CONDITIONS
r3-w7a-a (rodada 3): VERDICT: GO-WITH-CONDITIONS
r3-w7a-b (rodada 3): VERDICT: GO-WITH-CONDITIONS
rx-w7a (conferência r3x): VERDICT: GO-WITH-CONDITIONS
rx-w7a (conferência r3y): VERDICT: GO-WITH-CONDITIONS
```
