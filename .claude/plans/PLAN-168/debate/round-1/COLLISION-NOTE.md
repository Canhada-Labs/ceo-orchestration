# Colisão de escrita no round 1 — erro do CEO, registrado

**Dois agentes de security escreveram o MESMO arquivo.** Isso viola a regra
anti-colisão do PROTOCOL (§Spawn Protocol: um agente, um arquivo), e a causa
foi minha.

## O que aconteceu

1. `sec-168` foi despachado e **caiu com erro de API** no meio da resposta.
   Verifiquei o disco: **não havia arquivo**. Conclui que tinha morrido sem
   escrever.
2. Re-despachei como `sec-168b`, apontando para **o mesmo caminho**.
3. `sec-168b` completou e escreveu sua crítica (3 must-fix).
4. `sec-168` **NÃO estava morto** — voltou depois e escreveu por cima
   (5 must-fix, `R-SEC1..R-SEC7`, `generated_at 21:43:32Z`).

O erro não foi re-despachar: foi **re-despachar para o mesmo caminho** sem
tratar o original como possivelmente vivo. "Não escreveu ainda" não é o mesmo
que "morreu".

## Consequência para a auditoria

O arquivo `security-engineer.md` contém **apenas a crítica do `sec-168`**. A do
`sec-168b` foi perdida — não é recuperável do disco.

**Ambas foram aplicadas ao plano.** Os achados do `sec-168b`, preservados aqui
porque o arquivo original não existe mais:

1. **O fix não cura quem já está em campo.** Ponteiro com placeholder literal
   classifica `edited` ⇒ `PRESERVE_OWNED` ⇒ preservado para sempre. Cura
   proposta: reconhecedor de corpo legado ⇒ `REFRESH` com backup, no molde do
   r20 (`_SPEC_PRISTINE_FINGERPRINTS`).
2. **Contrato de input do gerador.** Sob a opção (b), o `SOURCE_DIR` de quem
   roda vence, e o upgrade regravaria o ponteiro nomeando o checkout-do-dia.
   *(Na verificação isto foi AGRAVADO: `request.PROTOCOL_SOURCE` é `None` e a
   chave nem existe — a intenção do adotante **não é persistida em lugar
   nenhum**, então o gerador compartilhado não tem de onde ler.)*
3. **AC-6 só é atingível com inputs normalizados** — o teste tem de cobrir
   override e o caminho de cura, não só install→upgrade.

Os três estão no §W2 do plano (itens 2, 3 e 4) e nos AC-6/6b/6c.

## Regra para a próxima vez

Um agente que falha por erro de API **pode voltar**. Ao re-despachar, aponte o
substituto para um caminho DIFERENTE (`<archetype>-retry.md`) e concilie os
dois na síntese. O custo de dois arquivos é zero; o custo de um clobber é uma
crítica perdida.
