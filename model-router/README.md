# claude-model-router

Proxy local que escolhe o modelo e o esforço (effort) de cada turno do Claude Code. A cada nova mensagem do usuário, o roteador pergunta ao Jev (TypeSafe) se o turno precisa de Haiku, Sonnet ou Opus, e qual esforço usar: `low`, `medium`, `high`, `xhigh` ou `max`.

```
Claude Code -> headroom (:8787) -> claude-model-router (:8788) -> api.anthropic.com
```

## Como funciona

- O roteador só muda o modelo do loop principal (requisições com `thinking.type == "adaptive"`). Chamadas auxiliares e pedidos de Haiku passam sem mudança.
- Se o Jev responde com confiança abaixo de `ROUTER_CONFIDENCE_MIN`, o roteador soma as probabilidades do Jev do menor modelo para o maior. Ele usa o primeiro modelo em que a soma chega a `ROUTER_COVERAGE`. Exemplo: com Haiku 0.48, Sonnet 0.44 e Opus 0.08, a soma chega a 0.92 no Sonnet, e o roteador usa o Sonnet. Se a TypeSafe falha ou demora mais de 5 s, o roteador usa Opus.
- O esforço vai em `output_config.effort`. O roteador mantém as outras chaves de `output_config`. Com dúvida no esforço, o roteador usa a mesma regra da soma, de `low` até `max`. Se a TypeSafe falha, o roteador usa `high`.
- As duas perguntas vão na mesma chamada à TypeSafe.
- O modelo e o esforço escolhidos ficam fixos até o fim do turno, porque o cache de prompt é por modelo.
- O Jev recebe a mensagem nova (no máximo 1500 caracteres) e o fim da conversa anterior (no máximo `ROUTER_CONTEXT_CHARS`). Assim uma resposta curta, como "sim", recebe o tamanho do trabalho que ela aprova. O contexto tem o texto digitado pelo usuário e o fim de cada resposta do Claude. Ele não tem chamadas de ferramentas, resultados de ferramentas nem thinking. O roteador mascara chaves e segredos antes de enviar.
- Num comando `/`, o Jev recebe o nome do comando e os argumentos, e não o corpo do comando ou da skill.
- O roteador fica depois do headroom. Na ordem inversa, o headroom não reconhece `claude-haiku-5`, move as system messages para o topo e a Anthropic responde 400.

## Instalação

Requisitos: [uv](https://docs.astral.sh/uv/), systemd de usuário e o headroom rodando como o serviço `headroom-default`.

1. Copie o script e o lockfile, que fixa as versões e os hashes das dependências:
   ```sh
   install -m 755 claude-model-router ~/.local/bin/
   install -m 644 claude-model-router.lock ~/.local/bin/
   ```
2. Crie o arquivo de ambiente e coloque a sua chave da TypeSafe nele:
   ```sh
   install -D -m 600 env.example ~/.config/claude-model-router/env
   ```
3. Copie as units do systemd:
   ```sh
   cp systemd/claude-model-router.service ~/.config/systemd/user/
   mkdir -p ~/.config/systemd/user/headroom-default.service.d
   cp systemd/headroom-default.service.d/model-router.conf ~/.config/systemd/user/headroom-default.service.d/
   ```
4. Ative o serviço e reinicie o headroom:
   ```sh
   systemctl --user daemon-reload
   systemctl --user enable --now claude-model-router
   systemctl --user restart headroom-default
   ```

O `ANTHROPIC_BASE_URL` do Claude Code continua apontando para o headroom (`http://127.0.0.1:8787`).

## Configuração

| Variável | Padrão | Uso |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | (nenhum) | Chave da TypeSafe. Obrigatória: sem ela, o roteador não inicia. |
| `ROUTER_CONFIDENCE_MIN` | `0.5` | Confiança mínima do Jev. Abaixo dela, o roteador usa a regra da soma (`ROUTER_COVERAGE`). |
| `ROUTER_COVERAGE` | `0.8` | Soma de probabilidades que decide o modelo e o esforço quando o Jev está em dúvida. Um valor maior escolhe modelos maiores. |
| `ROUTER_CONTEXT_CHARS` | `3000` | Máximo de caracteres da conversa anterior enviados ao Jev. Use `0` para não enviar contexto. |
| `ROUTER_PORT` | `8788` | Porta local do roteador. |
| `ROUTER_UPSTREAM` | `https://api.anthropic.com` | Destino das requisições. |
| `ROUTER_LOG_FILE` | (nenhum) | Também grava o log neste arquivo, com data e hora. Sem journald, o `--stats` lê daqui. |
| `HTTPS_PROXY` | (nenhum) | Proxy de saída para a Anthropic e a TypeSafe, como o do Docker Sandbox. |

## Comandos

```sh
claude-model-router --selftest            # testa a lógica de roteamento
claude-model-router --stats [since]       # resumo em texto (padrão: today)
claude-model-router --stats-json today    # o mesmo resumo em JSON
journalctl --user -u claude-model-router  # logs, uma linha `route {...}` por turno
curl http://127.0.0.1:8788/_router/health # "ok" se o roteador está de pé (sem chamar a Anthropic)
```

Sem journald (num sandbox, por exemplo), o `--stats` lê o `ROUTER_LOG_FILE` e só
aceita `today` ou uma data `AAAA-MM-DD [HH:MM]`.

## Painel

A pasta [`router-view/`](router-view/) tem um mod do Claude Code. O comando `/router` abre um painel lateral com os turnos por modelo, o esforço, os fallbacks e os agentes ativos.

## No Docker Sandbox

O kit [`sbx/kits/config-ecc`](../sbx/kits/config-ecc/) traz o roteador e o
painel. Veja a seção "Roteador de modelos" do README do kit.

## Desligar

Apague o drop-in `~/.config/systemd/user/headroom-default.service.d/model-router.conf`. Depois rode `systemctl --user daemon-reload` e reinicie o `headroom-default`.
