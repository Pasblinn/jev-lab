# 🧭 Estudo de caso: o wrapper numa sessão longa

Uma sessão real de trabalho no VS Code, com **~763k tokens em cache**, foi recarregada já sob o wrapper.

| Métrica (45 min) | Valor |
| --- | --- |
| Turnos atendidos pelo proxy | 84 |
| Modelo | `claude-opus-5` em 100% |
| Cache | 763k → 793k, sem quebra, sem compactação |
| Decisões do Jev | 1 |

A única decisão:

```
prompt:      "pronto reautenticado pode seguir"
Jev queria:  haiku 0.61 · opus 0.33 · sonnet 0.06
política:    opus  (downgrade-not-worth-cache-rebuild)
```

## O que isso ensina

> [!CAUTION]
> **O Jev julga o prompt, não o trabalho em andamento.** A frase era trivial; a tarefa por trás dela não. Se a trava de cache não existisse, a sessão teria reconstruído 763k tokens de cache em Haiku e continuado um trabalho pesado no modelo mais fraco.

- Em sessão longa o roteador **não economiza nada**: a trava (corretamente) segura o tier para sempre. Sobra ~1 s de latência por prompt e um proxy como ponto único de falha.
- O ganho está em **sessões novas** e turnos mecânicos.
- Corolário: **abra a conversa com a tarefa real**, não com `oi`. O tier do primeiro turno tende a virar o tier da sessão.

Decisão tomada: sessões longas e críticas rodam fora do wrapper.
