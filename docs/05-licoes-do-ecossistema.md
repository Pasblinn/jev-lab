# 📚 Lições do ecossistema

O Jev saiu em early access em 16/09/2026. Em quatro dias: `browser-use/jev-ultrafast` 11k★, `tamaratran/fast-jev-compaction` 4,8k★, 155 projetos catalogados no [`awesome-jev`](https://github.com/cobanov/awesome-jev). Lemos as issues de quem testou antes (20/09/2026):

| Fonte | Achado | Consequência |
| --- | --- | --- |
| jev-router [#35](https://github.com/gargpratyush/jev-router/issues/35) | janela cai de **1M → 200k** sob o modelo custom; schemas de MCP 651 → 18,8k tokens | maior risco aberto para sessão grande |
| jev-router [#17](https://github.com/gargpratyush/jev-router/issues/17) | trocar de modelo no meio descarta o cache; o autor ainda está redesenhando essa lógica | confie na trava de 20k, não a desligue |
| jev-router [#29](https://github.com/gargpratyush/jev-router/issues/29) | com subagentes: 3 prompts → **21 chamadas** ao Jev | filtre mensagens injetadas, não só `tool_result` |
| fast-jev-compaction [#65](https://github.com/tamaratran/fast-jev-compaction/issues/65) | `drop_call` apaga a tool call e deixa a narração → o modelo **fabricou 9 relatórios de trabalho feito** | nunca apague evidência deixando a afirmação |
| fast-jev-compaction [#56](https://github.com/tamaratran/fast-jev-compaction/issues/56) | duas `noul` voltam em escalas diferentes; threshold único de 0,5 trunca o arquivo que o agente ia editar | calibre por pergunta |
| fast-jev-compaction [#70](https://github.com/tamaratran/fast-jev-compaction/issues/70) | "nada a podar" tratado como "Jev falhou" | distinga vazio de erro |
| winnow [#1](https://github.com/GhalebDweikat/winnow/issues/1) | sidecar local sem autenticação: uma página web gasta sua chave | todo serviço em loopback precisa de token |

## Os três padrões

1. **Ranking bom, calibração ruim.** Em todos os relatos o Jev *ordena* certo. O que quebra é comparar a probabilidade com um número fixo.
2. **Falha silenciosa é a regra, não a exceção.** Roteamento desligado, plugin que não carrega, evidência apagada — nenhum gerou erro.
3. **Schema válido ≠ decisão correta.** A própria TypeSafe documenta fraquezas em aritmética, datas, distratores e estado adversarial ([jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13)).
