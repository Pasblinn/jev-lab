# 🧪 Como testar gastando pouco

A status line mente por omissão: ela aparece mesmo quando nenhuma decisão foi tomada. **A prova é o transcript.**

## Roteiro (≈ 2 turnos baratos)

```sh
mkdir -p /tmp/jevteste && cd /tmp/jevteste   # pasta vazia: sem CLAUDE.md, sem tools disparando
JEV_DEBUG=1 jev -p "diga apenas: ok"          # esperado: opus -> haiku (jev)
```

Depois, o controle — um prompt que **deve** ficar em cima:

```sh
JEV_DEBUG=1 jev -p "sem usar ferramentas, em uma linha: maior risco de migrar auth para OAuth2 com PKCE sem downtime?"
```

Só o par prova algo. "Foi para Haiku" sozinho pode ser default, não decisão.

## Conferir sem gastar turno

```sh
# quem respondeu de verdade
grep -o '"model":"claude-[^"]*"' "$(ls -t ~/.claude/projects/*/*.jsonl | head -1)" | sort | uniq -c
# o que o Jev decidiu e por quê
python3 -m json.tool "$(ls -t "${TMPDIR}"jev-claude/*.json | head -1)" | grep -E '"(tier|reason|prompt|confidence)"'
```

✅ Funcionando = o **seu** prompt aparece em `prompt` **e** o transcript mostra o modelo do tier decidido.

## Por que pasta vazia

Um `oi` na home, com CLAUDE.md global, memória e skills, custou **91.633 tokens de cache_create** — em Opus. Na pasta vazia: ~13k.

## Interativo sem mãos

```sh
expect -c 'spawn jev; sleep 8; send "oi\r"; sleep 25; send "/exit\r"; sleep 3'
```
