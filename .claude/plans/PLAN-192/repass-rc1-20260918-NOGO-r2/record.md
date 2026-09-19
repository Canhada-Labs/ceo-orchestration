# Rodada 2 do re-pass da v1.4.1-rc.1 — `GO-WITH-CONDITIONS` / `NO-GO` / `GO-WITH-CONDITIONS` (2026-09-18)

> Registro de triagem. Pela regra de parada pré-registrada (PLAN-192 §Approach, `README-rc1.md` §5) esta
> era a ÚLTIMA rodada por conta do CEO: uma 2.ª `NO-GO` ⇒ parar e levar as duas rodadas ao Owner.

## O que rodou

- Candidato: `3ed81cf657b3d22d012b1e32269671e86f3e4030` (só texto sobre o bump `9e9840b2`), CI verde
  (Validate, Ceremony lint, Translations; sem Smoke Install — nenhum path do filtro mudou).
- Revisor: codex 0.155.0 (binário global, payload conferido), modelo `gpt-6-astra`, 3 partes em
  paralelo, ~10 min. `RUNNER-OVERALL: rc=1`.
- Condições julgadas: `CONDITIONS-rc1.reviewed.md`
  (sha256 `822b4d74699819df313579bb2f9ef6a169d28c008effdb7261adcb330d789f8e`). MANIFEST 19/19.

| veredito | resultado | sha256 |
|---|---|---|
| `verdict-rc1-1.txt` | `GO-WITH-CONDITIONS` | `ec86430e8fa41f919a896ef2ce9d947efb382168edd826a7d0c61cdbd9e36f70` |
| `verdict-rc1-2.txt` | `NO-GO` | `023d8f12495eea0e4dc7811267eef23ba45ead3703d37e598697c92c6dde57af` |
| `verdict-rc1-3.txt` | `GO-WITH-CONDITIONS` | `762f0cf19311247f537a4dde9afd0d1ff2afff25c682212ff225e670a8d7f468` |

## O que convergiu

As três partes confirmaram as condições reescritas: a parte 1 diz que 7, 10 e 12 «now honestly describe
round 1's failures»; a parte 2, que 1–5 e 15–19 se sustentam e que a 15 «now honestly acknowledges
upgrade delivery»; a parte 3, que a 14 revisada «honestly describes the partial-file cases». Nenhum P0.

## A única condição falsa — CONFIRMADA contra o código

Condição 14 (e a mesma frase no `CHANGELOG.md` `### Fixed`): «remove o parcial, só o inode que esta
chamada criou … never a file that is not its own». `ceo-launches.py::_write_new_file` faz `os.lstat(path)`,
compara `(st_dev, st_ino)` e SÓ ENTÃO chama `os.unlink(path)`: dois passos. Um escritor concorrente que
substitua o destino entre os dois perde o arquivo dele, e a mensagem diz «the partial file was removed».
A parte 2 reproduziu a intercalação; a parte 3, olhando o mesmo código, não a viu. A frase vinha do
texto original da W1.1 (`47870320`) — a rodada 1 não a contestou.

É a 2.ª vez que a W1.1 cai (rodada 1: parcial sob Ctrl-C e sob `unlink` que falha; rodada 2: corrida
no `unlink`). Pela regra do repositório (2.ª ocorrência ⇒ cura estrutural), a cura é de ARQUITETURA:
escrever num temporário exclusivo, fechar, publicar com `os.link` (atômico, nunca substitui, nunca segue
symlink no destino) e nunca mais dar `unlink` no destino público.

## Achados novos desta rodada (anexo — não bloqueiam pela regra do corte)

- P1 `approval_gate.py`: chave JSON duplicada (`"findings":[…P0…],"findings":[]`) — `json.load` fica com
  a segunda e o gate APROVA.
- P1 `test_refs.py`: arquivo ilegível no scan vira ausência — uma ambiguidade real passa como prova.
- P1 `mutant_sandbox.py`: timeout mata o filho direto e deixa os descendentes rodando sobre um worktree
  que é removido em seguida.
- P2 `launch_ledger.py`: script INLINE maior que 8 MiB é gravado, mas o leitor do snapshot o recusa
  (`script_snapshot_missing`, inconclusivo).
- P2 `ceo-launches.py`: se a 2.ª leitura do snapshot falha, `relaunch --out` sai rc 0, anuncia «exact
  recorded call» e não cria o arquivo.
- P2 `docs/approval-gate.md:22`: a política «shipped default» é uma fixture de `tests/` que não é
  entregue a adopters.
- P2 (repetido da rodada 1) `INSTALL.md:660`: exemplo `--pin v1.4.1` durante o hold da rc.

## Decisão

Parado, por regra. As opções e o custo de relógio de cada uma foram levadas ao Owner em 2026-09-18
(~20:45 -03): A = 3.ª rodada só de texto (declarar a corrida); B = cura estrutural do `relaunch --out`
(~3 h, porque muda `.claude/hooks/tests/` e dispara o Smoke Install).

**Decisão do Owner (2026-09-18, verbatim):** «beleza faz isso A agora depois que lancar a gente faz o B
salva na memoria e claude pra nao esquecer». A 3.ª rodada roda sobre um candidato só de texto; B é o
primeiro item depois do lançamento. Critério de parada da rodada 3, fixado ANTES de ela rodar: é a
última desta via — outra `NO-GO` ⇒ parar de novo e voltar ao Owner.
