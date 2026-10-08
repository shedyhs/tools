# router-view

Mod do Claude Code que mostra o `claude-model-router` em um painel lateral. Abra o painel com `/router`. Ele também abre sozinho no início da sessão, se o terminal tem pelo menos 144 colunas.

O painel atualiza a cada 5 s e tem duas seções. Clique no título para abrir ou fechar cada uma.

- **Agentes ativos:** a árvore de subagentes da sessão, com o estado de cada um (`●` rodando, `◐` esperando, `○` pendente, `◌` ocioso) e o modelo entre colchetes.
- **Jev hoje:** os turnos do dia por modelo, o que o Jev pediu, o esforço usado, os fallbacks para Opus (dúvida, falha e 400), a latência e as dúvidas recentes.

Os dados vêm de `claude-model-router --stats-json today`. O comando precisa estar no `PATH`. Veja [o roteador](../README.md).

## Instalação

Inicie o Claude Code com a pasta do mod:

```sh
claude --plugin-dir /caminho/para/tools/model-router/router-view
```

## Desenvolvimento

```sh
claude plugin validate .   # valida o manifesto e o módulo
claude plugin test .       # roda os testes de view.test.ts
```

O modelo de cada agente vem do evento `agent.spawn`. Depois de um reload do mod, um agente que já existia aparece com `[?]`. As seções começam fechadas depois de cada reload.
