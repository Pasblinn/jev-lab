# ⚠️ Riscos conhecidos

| # | Risco | Mitigação hoje |
| --- | --- | --- |
| 1 | **Tier do 1º turno gruda.** Abrir com `oi` fixa Haiku; acima de 20k a trava impede *descer* — se impede *subir* ainda **não foi medido** | abrir com a tarefa real; `/model` pausa o roteador |
| 2 | **Haiku erra mais.** O Jev vê só o texto do prompt, não o repositório | resposta fraca → escolha o modelo manualmente |
| 3 | **Patch em `node_modules`** some em qualquer reinstalação | `./install.sh` é idempotente; acompanhar PRs #36/#37 |
| 4 | **Todo prompt vai para a TypeSafe** (texto do turno + modelo + tamanho do contexto) | nunca colar segredo em prompt |
| 5 | **Proxy é ponto único de falha** no meio da sessão | sessões críticas fora do wrapper |
| 6 | **Queda do Jev no meio da sessão não alerta** | pendente |
| 7 | **Janela 1M → 200k** (jev-router #35) | não reproduzido aqui até 793k; monitorar |
| 8 | **+0,3 a 0,9 s** por turno novo | — |
| 9 | Chamadas auxiliares com o sentinela ainda caem no default `opus` | pequeno, mas custa; pendente |
