# Receitas de kit

Fonte: <https://docs.docker.com/ai/sandboxes/customize/kit-examples.md>

Cada seção é um bloco funcional, não um kit distribuível completo. Versões
completas e carregáveis: <https://github.com/docker/sbx-kits-contrib>

```bash
# mixin do repo contrib
sbx run claude --kit "git+https://github.com/docker/sbx-kits-contrib.git#dir=<kit>"

# sandbox kit do repo contrib (substitui o nome do agente)
sbx run "git+https://github.com/docker/sbx-kits-contrib.git#dir=<kit>"
```

## 1. Distribuir arquivo de config compartilhado

Arquivo estático em `files/workspace/` quando o conteúdo é igual em todo sandbox
e não precisa de substituição em runtime: regras de linter, settings de editor,
`.editorconfig`, dotfiles.

```text
ruff-lint/
├── spec.yaml
└── files/
    └── workspace/
        └── ruff.toml
```

```yaml
schemaVersion: "2"
kind: mixin
name: ruff-lint
displayName: Ruff
description: Python linting com config compartilhada do time

setup:
  install:
    - command: "uv tool install ruff@latest"
      user: "1000"
```

```toml
line-length = 80

[lint]
select = ["E", "F", "I"]
```

## 2. Instalar ferramenta na criação

`setup.install` roda uma vez por sandbox, na criação. **Resultados não são
cacheados entre sandboxes** — kits servem para mudanças pequenas e componíveis;
build pesado vai para template customizado, cujas imagens são reusadas do cache
local.

```yaml
setup:
  install:
    - command: "apt-get update && apt-get install -y jq"
    - command: "curl -fsSL https://example.com/install.sh | sh"
```

- Comandos rodam como root por padrão. `user: "1000"` para o usuário agent (ex.:
  `npm install -g` com escopo de usuário, ou escrita em `/home/agent/`).
- Steps rodam sob `sh`, não bash — `source` falha com "not found". Faça pipe
  explícito para `bash` ou envolva em `bash -c '…'`.
- Downloads obedecem as regras de rede. Domínio resolvível ainda pode ser
  bloqueado (ex.: 403 até `sbx policy allow network get.sdkman.io`). Algumas
  ferramentas precisam de pacotes base antes — SDKMAN! precisa de `zip` e
  `unzip` instalados como root.

> ⚠️ `curl … | bash` **esconde falha de download**: o exit status do pipe é o do
> bash, e bash sai `0` com input vazio. Download bloqueado reporta sucesso.

```yaml
setup:
  install:
    - command: "curl -fsSL https://example.com/install.sh -o /tmp/install.sh && bash /tmp/install.sh"
      user: "1000"
```

## 3. Customizar o ambiente de shell

Gerenciadores de versão (nvm, SDKMAN!) instalam em diretórios versionados e
precisam de um init script sourced. Anexe a linha de source em
`/etc/sandbox-persistent.sh`. Para env vars simples use `environment.variables`
ou `-e`/`--env-file`.

```yaml
schemaVersion: "2"
kind: mixin
name: nvm
displayName: nvm
description: Node version manager disponível em todo shell

setup:
  install:
    - command: "curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash"
      user: "1000"
      description: Instalar nvm
    - command: |
        cat >> /etc/sandbox-persistent.sh <<'INNER'
        export NVM_DIR="$HOME/.nvm"
        unset NPM_CONFIG_PREFIX
        [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
        INNER
      user: "1000"
      description: Sourcear nvm em todo shell
```

- Ambos os steps como `user: "1000"`: o install cai em `/home/agent/` e o usuário
  agent é dono do script persistente. `$HOME` resolve por usuário no momento do
  source.
- **Anexe, nunca sobrescreva** — o sandbox depende do conteúdo existente.
- `NPM_CONFIG_PREFIX` da imagem base bloqueia a ativação do nvm, daí o `unset`.
- Sourcear expõe o comando `nvm` mas não coloca Node no `PATH`; rode
  `nvm install --lts` (envolvido em `bash -c '…'` se for script).
- **Anexe só o init script, nunca scripts de tab-completion** — o arquivo é
  sourced antes de todo comando, e completion quebra os shells não interativos
  de que os agentes dependem.

## 4. Instalar CA interna

Para proxies que inspecionam HTTPS, adicione a CA raiz ao trust store para que
agentes e SDKs confiem nos certificados assinados pelo proxy.

```text
internal-ca/
├── spec.yaml
└── files/
    └── home/
        └── internal-ca.crt
```

Use certificado PEM com extensão `.crt`. `files/home/` mapeia para
`/home/agent/`, então o arquivo vira `/home/agent/internal-ca.crt` — o caminho
que o install lê. Com múltiplos proxies, instale todas as CAs raiz antes de
rodar `update-ca-certificates`.

```yaml
schemaVersion: "2"
kind: mixin
name: internal-ca

setup:
  install:
    - command: "install -m 0644 /home/agent/internal-ca.crt /usr/local/share/ca-certificates/internal-ca.crt && update-ca-certificates"
      user: "0"
      description: Instalar CA interna
```

Como `update-ca-certificates` escreve no bundle do sistema, ferramentas que leem
o bundle não precisam de config extra.

## 5. Rodar serviço em background

`setup.startup` roda a cada start do sandbox. `background: true` para serviços
long-running. Startup faz replay depois de um ciclo stop/start.

```yaml
setup:
  startup:
    - command: ["my-service", "--port", "8080"]
      user: "1000"
      background: true
```

Serviços em background não escrevem no seu terminal. Para capturar output,
envolva em shell e redirecione — deixe `background: true` cuidar do
backgrounding, **sem** anexar `&`:

```yaml
setup:
  startup:
    - command:
        - sh
        - -c
        - my-service --port 8080 > /tmp/my-service.log 2>&1
      user: "1000"
      background: true
```

Log vazio prova que o wrapper rodou; log preenchido explica a falha.

## 6. Escrever valores de runtime em arquivo

Quando o valor de config só é conhecido no start — geralmente o caminho absoluto
do workspace. `${WORKDIR}` expande para o workspace primário no momento da
escrita.

```yaml
setup:
  files:
    - path: /home/agent/.local/bin/start-code-server.sh
      content: |
        exec code-server --bind-addr 0.0.0.0:8080 --auth none "${WORKDIR}"
      mode: "0755"
  startup:
    - command:
        - sh
        - -c
        - nohup /home/agent/.local/bin/start-code-server.sh > /tmp/code-server.log 2>&1 &
      user: "1000"
```

`mode: "0755"` torna o arquivo executável para o startup invocar. Use
`setup.files` **só** quando o conteúdo depende de valor de runtime; caso
contrário, arquivo estático.

## 7. Distribuir uma skill do Claude Code

Claude Code lê skills com escopo de projeto em `.claude/skills/<name>/SKILL.md`.

```text
docker-review/
├── spec.yaml
└── files/
    └── workspace/
        └── .claude/
            └── skills/
                └── docker-review/
                    └── SKILL.md
```

```yaml
schemaVersion: "2"
kind: mixin
name: docker-review
displayName: Dockerfile review skill
description: Distribui uma skill do Claude Code que revisa Dockerfiles
```

Kits miram o **workspace** e não `~/.claude/` porque sandboxes não herdam a
configuração de agente em nível de usuário do host.

## 8. Customizar settings do agente

Quando o agente faz merge de settings de vários arquivos, ponha os settings do
kit em arquivo separado em vez de substituir configuração gerenciada pelo
sandbox.

### Claude Code — `--settings`

```text
claude-sonnet/
├── spec.yaml
└── files/
    └── home/
        └── .config/
            └── claude/
                └── sonnet.json
```

```yaml
schemaVersion: "2"
kind: sandbox
name: claude-sonnet
extends: claude

sandbox:
  command:
    - --dangerously-skip-permissions
    - --settings
    - /home/agent/.config/claude/sonnet.json
```

```json
{"model":"sonnet"}
```

```bash
sbx run ./claude-sonnet
```

Claude Code faz merge com os user settings gerenciados pelo sandbox.
`files/home/` mantém o arquivo dentro do sandbox, fora do workspace montado do
host. No primeiro launch, o `sbx` pede aprovação das credenciais Anthropic
herdadas e registra como credential binding (kit v2 de terceiro).

### OpenCode — `OPENCODE_CONFIG`

```text
opencode-team/
├── spec.yaml
└── files/
    └── home/
        └── .config/
            └── opencode/
                └── team.json
```

```yaml
schemaVersion: "2"
kind: mixin
name: opencode-team
requires:
  agent: opencode

environment:
  variables:
    OPENCODE_CONFIG: /home/agent/.config/opencode/team.json
```

```json
{"$schema":"https://opencode.ai/config.json","autoupdate":false}
```

O mecanismo varia por agente. Sem arquivo de config extra, opção de launch ou
env var, um kit **não consegue** substituir os user settings gerenciados antes do
launch. E `setup.startup` não gate o entrypoint do agente — evite usá-lo para
settings necessários na inicialização.

## 9. Forkar um agente existente

`kind: sandbox` define um agente completo; a variante comum é forkar um built-in
com `extends:`, declarando só os campos alterados.

```yaml
schemaVersion: "2"
kind: sandbox
name: claude-safe
displayName: Claude Code (com prompts de aprovação)
description: Claude Code em modo de permissão manual

extends: claude

sandbox:
  entrypoint: [claude, "--permission-mode", "manual"]
```

O filho herda imagem, credenciais, permissões de rede, volumes persistentes,
settings, config de MCP, instruções de agente, entradas de setup e variáveis de
ambiente. `sandbox.entrypoint` substitui o herdado. Entradas de setup do pai
executam primeiro; em conflito de env var, o filho vence.

```bash
sbx run ./claude-safe
```

## 10. Agente do zero (tutorial Amp)

Fonte: <https://docs.docker.com/ai/sandboxes/customize/build-an-agent.md>
(escrito em schema v1; migre os campos com a tabela em `spec-reference.md`)

Requisitos da imagem base: usuário não-root `agent` em UID 1000, sudo sem senha,
home em `/home/agent/`, forward das env vars de proxy. Opções:
`docker/sandbox-templates:shell`, `:shell-docker`, ou variantes por agente.
Use `shell-docker` quando o agente roda containers; `shell` para ambiente mais
leve e não privilegiado.

Equivalente v2 do spec do Amp:

```yaml
schemaVersion: "2"
kind: sandbox
name: amp
displayName: Amp
description: The frontier coding agent.

sandbox:
  image: "docker/sandbox-templates:shell-docker"
  entrypoint: [amp, --dangerously-allow-all]

agentInstructions:
  filename: AGENTS.md
  content: |
    ## Sandbox environment
    You are running inside a Docker sandbox...

credentials:
  - service: amp
    apiKey:
      name: AMP_API_KEY
      proxyManaged: true
      inject:
        - domain: ampcode.com
          header: Authorization
          format: "Bearer %s"

permissions:
  network:
    allow:
      - "ampcode.com:443"
      - "*.ampcode.com:443"

setup:
  install:
    - command: "curl -fsSL https://ampcode.com/install.sh -o /tmp/amp.sh && bash /tmp/amp.sh"
      user: "1000"
      description: Install Amp
```

Pontos do tutorial:

- `user: "1000"` importa porque install roda como root por padrão, e o instalador
  do Amp escreve no home — como root cairia em `/root/`.
- **Mantenha o domínio de credencial estreito.** Wildcard amplo empurra o proxy
  para modo TLS-intercept, o que **corrompe downloads** de binários de CDN.
- `deny` bloqueia hosts (ex.: telemetria) e tem precedência sobre `allow`.

Quando o agente valida o formato da chave no startup, o sentinel padrão
`proxy-managed` não serve; registre um placeholder com formato próprio:

```bash
sbx secret set-custom \
  --host ampcode.com \
  --env AMP_API_KEY \
  --placeholder "sgamp-{rand}" \
  --value "$AMP_API_KEY"

sbx secret rm --host ampcode.com
```

`{rand}` expande para um sufixo aleatório. (`--host` não aparece no
`sbx secret rm --help`.)
