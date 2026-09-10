# Referência do spec.yaml (schema v2)

Fonte: <https://docs.docker.com/ai/sandboxes/customize/kit-reference.md>

## Layout do kit

```text
my-kit/
├── spec.yaml       # obrigatório
└── files/          # opcional
    ├── home/       # → /home/agent/
    └── workspace/  # → workspace primário
```

## Versões de schema

Desde Sandboxes 0.36, `schemaVersion: "1"` e `"2"` carregam, mas o loader ramifica
pelo valor: campo v1 dentro de spec v2 é **erro de decode**.

`mixins` e `sandbox.build` são parseados mas **ainda não ligados**. Spec com
`build` precisa informar `image` também.

### Migração v1 → v2

| v1 | v2 |
|---|---|
| `credentials.sources.<id>` | entrada na lista `credentials:` com `service` |
| `network.allowedDomains` / `deniedDomains` | `permissions.network.allow` / `deny` |
| `network.serviceDomains` / `serviceAuth` | `credentials[].apiKey.inject` |
| portas publicadas | `ports` de topo |
| `oauth:` standalone | `credentials[].oauth` |
| `environment.proxyManaged` | `credentials[].apiKey.proxyManaged` |
| `memory` / `agentContext` | `agentInstructions.content` |
| `kind: agent` | `kind: sandbox` |
| `sandbox.aiFilename` | `agentInstructions.filename` |
| `entrypoint.run` / `args` / `ttyArgs` | `sandbox.entrypoint` / `command.default` / `command.interactive` |
| `tmpfs:` | `volumes:` com `type: tmpfs` |
| `commands:` | `setup:` |

Removidos: `settings:`, `kitDir`, `persistence`. `oauth.skipIfEnv` parseia mas
não faz nada (bindings são autoritativos).

## Campos de topo

```yaml
schemaVersion: "2"
kind: <mixin | sandbox>
name: <nome>
version: <versão>
displayName: <nome>
description: <texto>
sourceURL: <url>
licenses:
  - MIT
locked:
  - sandbox.image
security:
  privileged: false
args:
  channel:
    default: stable
    enum: [stable, beta]
```

Obrigatórios: `schemaVersion`, `kind`, `name` (minúsculas alfanuméricas + hífen,
1–64 chars).

Opcionais: `version`, `displayName`, `description`, `sourceURL`, `licenses`
(SPDX ids), `locked` (caminhos com ponto que filhos não podem sobrescrever),
`security` (`privileged`), `args` (só v2).

## args

```yaml
args:
  version:
    default: latest
    description: Versão da ferramenta
    pattern: '^(latest|[0-9]+\.[0-9]+\.[0-9]+)$'
  channel:
    default: stable
    enum: [stable, beta, nightly]
  target:
    required: true
    description: Build target

environment:
  variables:
    TOOL_VERSION: "${{ kit.args.version }}"
```

- Nome começa com letra ou underscore.
- Cada arg define **exatamente um** entre `default` (string vazia conta) e
  `required: true`.
- `enum` e `pattern` são mutuamente exclusivos. `pattern` é Go RE2, match do
  valor inteiro. `default` declarado precisa passar na própria restrição.
- Todo `${{ kit.args.<nome> }}` precisa de declaração correspondente.
- Substituição roda **antes** do decode YAML — cite valores tipo `"1.20"`.
- Validação acontece antes da criação do sandbox.
- Args são texto plano. Segredo vai em `credentials`.

## kinds

Mixin não pode declarar `sandbox:`, `extends:` nem `mixins:`. Pode fixar base:

```yaml
schemaVersion: "2"
kind: mixin
name: github-tools
requires:
  agent: claude
```

Sandbox kit precisa de bloco `sandbox:`, a menos que herde um:

```yaml
schemaVersion: "2"
kind: sandbox
name: claude-safe
extends: claude
```

`extends:` e `mixins:` são exclusivos de `kind: sandbox`.

## sandbox

```yaml
sandbox:
  image: <image-ref>
  build:
    context: .
    dockerfile: Dockerfile
    args:
      AGENT_VERSION: "1.0.0"
    target: runtime
    platforms:
      - linux/amd64
  entrypoint: [my-agent, "--flag"]
  command:
    default: ["--task-mode"]
    interactive: []
  resources:
    cpu: 2
    memory: 4g
    gpu: "1"
```

- `image` é obrigatório a menos que `extends:` forneça.
- Comando lançado = `entrypoint` + `command.default`; em TTY usa
  `command.interactive` (caindo para `default` se ausente).
- **Com `extends:`, `sandbox.command` substitui a cauda herdada inteira**, não
  concatena. Filho de `claude` que adiciona `--settings` precisa reafirmar
  `--dangerously-skip-permissions`.

Requisitos da imagem: usuário não-root `agent` em UID 1000, sudo sem senha,
`/home/agent/`, variáveis de proxy preservadas através do sudo, binário do agente.
`docker/sandbox-templates:shell-docker` cobre tudo isso.

## agentInstructions

```yaml
agentInstructions:
  filename: CLAUDE.md
  content: |
    Ruff está instalado. Rode `ruff check` antes de commitar.
```

`filename` vale para `kind: sandbox`; em mixin é ignorado com warning. `content`
de mixin é escrito em `<dir-do-arquivo-AI>/kits-memory/<kit-name>.md`, com um
ponteiro `## Kits` adicionado ao arquivo AI base.

## credentials

Kits declaram necessidade e injeção — não descoberta no host. O usuário fornece
valores pelo secret store ou prompt de primeira execução, autorizado por binding.

```yaml
credentials:
  - service: <service-id>
    description: <texto>
    required: <true | false>
    provider: <provider>
    apiKey:
      name: <ENV_VAR>
      proxyManaged: true
      inject:
        - domain: <domínio>
          header: <header>
          format: <format>
        - domain: <domínio>
          scheme: bearer
        - domain: <domínio>
          scheme: basic
          username: <user>
    oauth:
      tokenEndpoint:
        host: <host>
        path: <path>
      sentinels:
        accessToken: <sentinel>
        refreshToken: <sentinel>
      credentialFile:
        path: <path>
        structure:
          <key>:
            accessToken: "{{.AccessToken}}"
            refreshToken: "{{.RefreshToken}}"
            expiresAt: "{{.ExpiresAt}}"
            scopes: "{{.Scopes}}"
```

- `service`: kebab-case minúsculo, casa com o que é guardado via `sbx secret set`.
- `required` default `false`. Credencial obrigatória não atendida gera warning e
  o sandbox sobe sem ela.
- `provider` é reservado e inerte.
- Cada entrada precisa de `apiKey`, `oauth`, ou ambos. Se ambos resolvem, a API
  key vence e OAuth é fallback.

**apiKey**: `name` é a env var. `proxyManaged` (default `false`) faz o `sbx`
setar essa variável com o sentinel `proxy-managed`. Cada `inject[]` precisa de
`domain` (que **também** precisa estar em `permissions.network`) mais `header`
com `format` de um único `%s`, **ou** `scheme` (`bearer`, ou `basic` com
`username`). `format` e `scheme` são mutuamente exclusivos.

**oauth**: `tokenEndpoint.host`/`path` marcam o que interceptar. `sentinels.*` são
os placeholders plantados no container. `credentialFile.path` aceita `~`.
`structure` é JSON declarativo e vence `template` quando ambos aparecem;
`template` é Go template e expõe também `{{.ScopesJSON}}`. `resourceHosts` lista
hosts de API (separados do token endpoint) onde o proxy anexa o token.
`responseFields` renomeia os campos da resposta de token lidos pelo proxy.
`passthrough: true` devolve a resposta intacta em vez de trocar por sentinels.

## permissions.network

```yaml
permissions:
  network:
    allow: [<domínio>, ...]
    deny:  [<domínio>, ...]
```

`deny` vence `allow`, inclusive entre kits compostos.

Aplicados: host exato (`api.example.com`), host com porta
(`api.example.com:8080`), wildcard de um label (`*.example.com`).

Parseados mas **não aplicados ainda**: `**.example.com`, range de portas
(`api.example.com:80-443`), wildcard de porta (`api.example.com:*`), CIDR
(`10.0.0.0/8`).

## ports

```yaml
ports:
  - container: 8080
    name: web
```

`container` 1–65535. `protocol` `tcp` ou `udp`. `name` é label opcional. Portas
de host são efêmeras por padrão.

`protocol` vazio publica só IPv4 (`127.0.0.1`) — adequado a serviço em `0.0.0.0`.
`tcp` também publica `::1`, onde conexões podem ser aceitas e resetadas se nada
escutar em IPv6. Fixar porta de host: `sbx ports --publish <host>:<container>`.

## environment

```yaml
environment:
  variables:
    <NAME>: <valor>
```

Nomes casam `[A-Za-z_][A-Za-z0-9_]*`. Evite prefixos `DASH_`, `SBX_`, `DOCKER_`.
Não sobrescreva `HOME`, `USER`, `SHELL`, `PATH`, `LD_PRELOAD`, `LD_LIBRARY_PATH`,
nem `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`.

## setup

```yaml
setup:
  install:
    - command: <string-shell>
      user: <uid>
      description: <texto>
  startup:
    - command: [<argv>, ...]
      user: <uid>
      background: <true | false>
      description: <texto>
  files:
    - path: <path>
      content: <texto>
      mode: <octal>
      onlyIfMissing: <true | false>
      description: <texto>
```

### Ordem na criação

```text
permissions.network + environment.variables
  → files/home/
  → setup.install
  → setup.files
  → setup.startup   (registrado por start)
  → files/workspace/  (após workspace e --clone prontos)
```

Kits empilhados aplicam por estágio, na ordem dos `--kit`. Logo: install pode ler
de `files/home/`, mas **não** de `files/workspace/` nem de `setup.files`.

`sbx kit add` recria o sandbox e só aceita mixins limitados a
`environment.variables`, `setup.install` e `permissions.network.allow`.

### install

Roda síncrono via `sh -c`. `user` default `"0"` (root). Diretório inicial é o
`WORKDIR` da imagem template (`/home/agent/workspace` nos templates Docker), que
pode não ser o workspace real — use caminhos absolutos.

### startup

Comando em forma de array, sem shell. `user` default `"1000"`. Roda não
interativo, sem terminal — não pode fazer prompt (`aws login` interativo trava).
Não gate o entrypoint: o agente sobe assim que os comandos são despachados, e
`background: false` só serializa o dispatcher.

Replay a cada start e a cada restart de container ⇒ **idempotente**: guard com
checagem de existência, prefira upsert, convirja ao mesmo estado. O que o agente
precisa em disco antes disso vai em `setup.files`.

### files

Escritos no start com substituição em runtime. `path` absoluto. `content` suporta
`${WORKDIR}`. `mode` default `"0644"`. `onlyIfMissing` default `false`. Escritos
como UID 1000 — alvo root (`/etc`) exige `setup.install`.

## Arquivos estáticos

```text
my-kit/files/
├── home/       → /home/agent/
└── workspace/  → caminho do workspace primário
```

Diretórios-pai criados automaticamente, arquivos existentes sobrescritos, e
caminhos absolutos ou traversal `../../` são rejeitados.

## volumes

```yaml
volumes:
  - path: /workspace
    size: 10g
    mode: "0755"
  - path: /tmp/scratch
    type: tmpfs
    size: 512m
    mode: "1777"
```

`path` obrigatório e absoluto. `type` vazio = block-backed; `tmpfs` = RAM.
`size` e `mode` opcionais. **Volumes só valem na criação** — `sbx kit add` não
anexa volume a container rodando.
