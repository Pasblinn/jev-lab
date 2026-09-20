# 🔬 Os dois bugs e o patch

Base: `jev-router` 0.3.0 · Claude Code 2.1.278 · macOS. Patch: [`patches/jev-router-0.3.0-routing-fixes.patch`](../patches/jev-router-0.3.0-routing-fixes.patch) (38 linhas, só `src/proxy.mjs`).

## Bug 1 — o turno real do usuário não era roteado

**Sintoma.** `oi` numa sessão nova: respondeu `claude-opus-5`, `/jev-explain` disse *"no routing decision has been recorded"*. As únicas decisões gravadas eram de `[SUGGESTION MODE…]` (a chamada interna do Claude Code que sugere o próximo prompt) e de `/model`.

**Instrumentação.** `JEV_DUMP` grava o body de cada `/v1/messages`:

```
dump.…688.json | tools=41 | msgs=2 | last.role=system   ← turno real, ignorado
dump.…313.json | tools=0  | msgs=1 | last.role=user     ← chamada auxiliar
```

**Causa.** `newTurnPrompt` exigia `messages.at(-1).role === "user"`. O Claude Code anexa a saída dos hooks de `SessionStart` como mensagem `role: "system"` **depois** do turno do usuário. Quem tem qualquer hook de SessionStart cai nisso em 100% das sessões. Sem decisão, o código usa `state.tier ?? "opus"`.

Efeito colateral: a chamada de sugestão termina em `user` e tem tools, então era **ela** que o Jev julgava — e o tier decidido para a sugestão vazava para o seu próximo turno.

**Correção.** Andar para trás sobre as mensagens `system` finais, e ignorar prompts que começam com `[SUGGESTION MODE`.

## Bug 2 — toda sessão em projeto real nascia presa em Opus

**Causa.** `decide()` recusa descer de tier quando `contextTokens > 20000`, para proteger o prompt cache. No primeiro turno não existe cache, mas `current` nasce `"opus"` e o `CLAUDE.md` + hooks inflam a primeira mensagem acima de 20k.

**Correção.** `contextTokens: state.tier ? contextTokens : 0` — a trava só vale depois que um tier foi fixado para a conversa.

**A/B** (CLAUDE.md de 145 KB, ctx ~46k, Jev `p=0.99` nos dois braços):

| Braço | Log |
| --- | --- |
| com patch | `opus -> haiku (jev)` |
| sem patch | `opus -> opus (downgrade-not-worth-cache-rebuild/no-change)` |

## Upstream

Os mesmos diagnósticos apareceram de forma independente em [#36](https://github.com/gargpratyush/jev-router/pull/36) e [#37](https://github.com/gargpratyush/jev-router/pull/37) (abertos em 20/09/2026, issues #18 e #28). Diferença: o #36 **não** filtra `[SUGGESTION MODE`. Quando os PRs forem mergeados, prefira a versão oficial e mantenha só esse filtro.

> [!WARNING]
> O patch vive em `node_modules`. Reinstalar ou atualizar o `jev-router` apaga tudo — sem aviso, o roteador volta a mandar tudo para Opus. Rode `./install.sh` de novo.

## Hipóteses descartadas

| Hipótese | Como foi descartada |
| --- | --- |
| Chave errada | mesmo comprimento e valor da chave que responde direto na API |
| Jev fora do ar | `askJev` chamado isolado: typo → haiku `p=1.00` (927 ms); refatorar auth → opus `p=0.95` (696 ms) |
| Instalação quebrada | `[jev] rewrite jev-router -> …` aparecia: o proxy estava vivo, só não decidia |
