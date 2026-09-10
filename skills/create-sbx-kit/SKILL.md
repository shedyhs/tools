---
name: create-sbx-kit
description: "Use when creating, editing, debugging or publishing a Docker Sandboxes (sbx) kit or custom template — writing spec.yaml, choosing mixin vs sandbox kit vs template, wiring setup.install/startup/files, network permissions, credentials, kit args, or fixing a kit whose tool install or background service fails"
metadata:
  version: "1.0.0"
  source: docker-docs
  verified_against: "sbx v0.42.1"
---

# Criar kits e templates do Docker Sandboxes (sbx)

Kits são **experimentais**: o formato do `spec.yaml` e a CLI podem mudar.
Sempre confirme a versão local antes de assumir sintaxe:

```bash
sbx version
```

## 1. Escolher o artefato certo

Antes de escrever qualquer YAML, decida o tipo. Errar aqui custa retrabalho.

| Objetivo | Artefato | `kind` |
|---|---|---|
| Adicionar capacidade a um agente existente (ferramenta, config, serviço, credencial) | **mixin** | `kind: mixin` |
| Definir um agente novo, ou variar um built-in (entrypoint, settings, política) | **sandbox kit** | `kind: sandbox` |
| Assar ferramentas pesadas/lentas na imagem, com cache entre sandboxes | **template** | Dockerfile, sem kit |

Regras de decisão:

- `setup.install` **não** é cacheado entre sandboxes — roda em toda criação. Se o
  install é lento (compilar, toolchain grande, imagem de ML), vire template.
  Imagens de template são puxadas uma vez e reusadas do cache local.
- Vários mixins empilham num mesmo sandbox; só um sandbox kit por sandbox.
- Template customiza o ambiente de um agente existente — **não** cria runtime de
  agente novo. Runtime novo é sandbox kit.
- Mixin não pode declarar `sandbox:`, `extends:` nem `mixins:`.

Detalhe de templates (imagens base, variantes `-docker`, `sbx template save/load`):
`references/templates.md`.

## 2. Estrutura mínima

```text
my-kit/
├── spec.yaml          # obrigatório
└── files/             # opcional
    ├── home/          # → /home/agent/
    └── workspace/     # → workspace primário
```

Mixin que instala uma ferramenta:

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

Sandbox kit que forka um agente built-in:

```yaml
schemaVersion: "2"
kind: sandbox
name: claude-safe
displayName: Claude Code (com prompts de aprovação)
extends: claude

sandbox:
  entrypoint: [claude, "--permission-mode", "manual"]
```

`name`: minúsculas, alfanumérico e hífen, 1–64 chars. O `schemaVersion` decide o
parser inteiro — campo v1 dentro de spec v2 é **erro de decode**, não aviso.
Migração v1→v2 campo a campo: `references/spec-reference.md`.

## 3. Ordem de execução na criação (crítico)

Muito bug de kit é ordem, não sintaxe:

```text
1. permissions.network + environment.variables
2. files/home/            → /home/agent/
3. setup.install          (root por padrão)
4. setup.files            (substituição em runtime, UID 1000)
5. setup.startup          (registrado; roda a cada start)
6. files/workspace/       (só depois do workspace/--clone pronto)
```

Consequências diretas:

- `setup.install` **pode** ler de `files/home/`.
- `setup.install` **não pode** ler de `files/workspace/` nem de `setup.files`.
- Kits empilhados aplicam por estágio, na ordem dos `--kit`.
- `setup.startup` **não bloqueia** o entrypoint — o agente sobe assim que os
  comandos são disparados. Nada que o agente precise na inicialização pode
  depender de `startup`; use `setup.files` ou `install`.

## 4. Blocos do spec.yaml

Resumo operacional. Referência completa de campos, tipos e defaults em
`references/spec-reference.md`.

### setup.install

```yaml
setup:
  install:
    - command: "apt-get update && apt-get install -y jq"   # string, via sh -c
      user: "0"                                            # default: root
      description: Instalar jq
```

- Roda via `sh`, **não** bash. `source` falha com "not found".
- `user` default `"0"`. Instalador que escreve em `$HOME` precisa de `user: "1000"`,
  senão cai em `/root/`.
- Diretório inicial é o `WORKDIR` da imagem, que pode não ser o workspace real —
  **use caminhos absolutos**.

### setup.startup

```yaml
setup:
  startup:
    - command: ["my-service", "--port", "8080"]   # argv, sem shell
      user: "1000"                                # default: 1000
      background: true
```

- Replay a cada start e a cada restart do container ⇒ **deve ser idempotente**
  (guard de existência, upsert, convergir para o mesmo estado).
- Sem terminal: comando interativo (ex.: `aws login`) trava.
- `background: false` só serializa o dispatcher; não segura o entrypoint.

### setup.files

Só quando o conteúdo depende de valor de runtime (tipicamente o caminho absoluto
do workspace). Conteúdo invariante → `files/` estático.

```yaml
setup:
  files:
    - path: /home/agent/.local/bin/start.sh
      content: |
        exec code-server --bind-addr 0.0.0.0:8080 --auth none "${WORKDIR}"
      mode: "0755"
      onlyIfMissing: false
```

Escritos como UID 1000 — alvo root (`/etc/...`) exige `setup.install`.

### permissions.network

```yaml
permissions:
  network:
    allow: ["api.example.com:443", "*.example.com:443"]
    deny:  ["telemetry.example.com"]
```

`deny` vence `allow`, inclusive entre kits compostos. Sob governança de org, as
regras `allow` do kit são ignoradas e as `deny` continuam valendo.

Padrões **aplicados**: host exato, host com porta, wildcard de um label
(`*.example.com`). Parseados mas **ainda não aplicados**: `**.example.com`,
range de portas, wildcard de porta, CIDR — não confie neles.

### credentials

O segredo real **fica no host**. O container recebe um sentinel; o proxy troca
pelo valor real na saída.

```yaml
credentials:
  - service: my-service          # kebab-case, casa com `sbx secret set`
    required: false
    apiKey:
      name: MY_API_KEY
      proxyManaged: true         # injeta o sentinel "proxy-managed"
      inject:
        - domain: api.example.com
          header: Authorization
          format: "Bearer %s"    # exatamente um %s
```

- O `domain` de `inject` **também** precisa estar em `permissions.network.allow`.
- `header` + `format` e `scheme` (`bearer`/`basic`) são mutuamente exclusivos.
- Nunca coloque segredo em `environment.variables` nem em `args`.
- Fluxo OAuth (sentinels, `credentialFile`, `resourceHosts`): ver referência.

### environment.variables

```yaml
environment:
  variables:
    TOOL_VERSION: "1.2.3"
```

Não sobrescreva `HOME`, `USER`, `SHELL`, `PATH`, `LD_PRELOAD`, `LD_LIBRARY_PATH`,
nem `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` (gerenciados pelo sandbox). Evite os
prefixos `DASH_`, `SBX_`, `DOCKER_`.

### args (só v2)

```yaml
args:
  version:
    default: latest
    pattern: '^(latest|[0-9]+\.[0-9]+\.[0-9]+)$'
environment:
  variables:
    TOOL_VERSION: "${{ kit.args.version }}"
```

Cada arg define **exatamente um** entre `default` e `required: true`. `enum` e
`pattern` são mutuamente exclusivos. Substituição acontece **antes** do decode
YAML — cite valores como `"1.20"`. Args são texto plano: não são para segredos.

Passar: `--kit-arg nome=valor`, escopo `--kit-arg <kit>.nome=valor`, ou
`--kit-args-file`.

### agentInstructions

```yaml
agentInstructions:
  filename: CLAUDE.md      # só para kind: sandbox; ignorado (com warning) em mixin
  content: |
    Ruff está instalado. Rode `ruff check` antes de commitar.
```

Conteúdo de mixin vai para `kits-memory/<kit-name>.md`, indexado por uma seção
`## Kits` no arquivo de memória base.

### Caminhos reservados

Kits de agente built-in são donos de certos caminhos de config — **não escreva
neles**. Ex.: `claude` gerencia `~/.claude.json` e `~/.claude/settings.json`;
`codex` gerencia `~/.codex/config.toml`. Para customizar settings, use a camada
extra do agente (`--settings` do Claude Code, `OPENCODE_CONFIG` do OpenCode) com
arquivo fora dos caminhos gerenciados. Receita em `references/patterns.md` §8.

## 5. Armadilhas recorrentes

| Sintoma | Causa | Correção |
|---|---|---|
| Install "passa" mas a ferramenta não existe | `curl … \| bash` mascara falha: exit status é do bash, que sai `0` com stdin vazio | Baixe primeiro, execute depois: `curl -fsSL … -o /tmp/i.sh && bash /tmp/i.sh` |
| `source: not found` | `setup.install` roda em `sh` | `bash -c '…'` ou pipe explícito para `bash` |
| Ferramenta instalada em `/root/` | `user` default é `"0"` | `user: "1000"` |
| Download 403 com domínio resolvível | política de rede | `sbx policy allow network <host>` ou `permissions.network.allow` |
| nvm não ativa | `NPM_CONFIG_PREFIX` da imagem base | `unset NPM_CONFIG_PREFIX` no init script |
| Shell quebra em comandos não interativos | script de tab-completion em `/etc/sandbox-persistent.sh` | Anexe **só** o init script; o arquivo é sourced antes de todo comando |
| Serviço em background sem output | background não escreve no terminal | Envolva em `sh -c` e redirecione para log; deixe `background: true` fazer o backgrounding, sem `&` |
| Settings do agente não valem na inicialização | `setup.startup` não gate o entrypoint | Arquivo estático + flag no `sandbox.command` |
| Filho de `extends: claude` perde flag | `sandbox.command` **substitui** a cauda herdada, não concatena | Restaure `--dangerously-skip-permissions` explicitamente |
| Downloads corrompidos | domínio de serviço amplo demais coloca o proxy em modo TLS-intercept | Mantenha domínios de credencial estreitos |

Receitas completas (config compartilhada, CA interna, serviço em background,
shipping de skill do Claude Code, fork de agente): `references/patterns.md`.

## 6. Ciclo de trabalho

```bash
sbx kit validate ./my-kit/          # 1. schema
sbx kit inspect ./my-kit/ --json    # 2. o que o kit realmente declara
sbx run claude --kit ./my-kit/      # 3. mixin sobre um agente
sbx run ./my-kit/                   # 3'. sandbox kit (1º argumento posicional)
sbx policy log                      # 4. eventos de proxy / domínios bloqueados
sbx rm <name>                       # 5. recomeçar limpo
```

Output de setup só aparece durante `run`/`create` — para revê-lo, recrie o
sandbox.

`sbx kit add <sandbox> <path>` adiciona mixin a um sandbox **rodando**: reinicia
preservando o estado da VM, mas aceita **apenas** `environment.variables`,
`setup.install` e `permissions.network.allow`. Arquivos estáticos, `setup.startup`,
`setup.files` e `volumes` exigem recriar o sandbox.

Comandos completos, fontes (local/git/OCI), assinatura e `kit.allowedSources`:
`references/cli.md`.

## 7. Antes de publicar

- [ ] `sbx kit validate` passa
- [ ] Testado do zero (`sbx rm` + `sbx run`), não só em sandbox já quente
- [ ] `setup.startup` idempotente — validado com stop/start
- [ ] Nenhum segredo em `environment.variables`, `args` ou `files/`
- [ ] Todo `credentials[].inject[].domain` também está em `permissions.network.allow`
- [ ] Domínios de credencial estreitos (sem wildcard de CDN)
- [ ] Nenhuma escrita em caminho reservado do agente
- [ ] Imagens e pacotes pinados (assinatura cobre `spec.yaml` e `files/`, **não** tags de imagem nem conteúdo baixado)
- [ ] `description` e `displayName` preenchidos

## Referências

- `references/spec-reference.md` — schema v2 completo, campos, defaults, migração v1→v2
- `references/patterns.md` — 9 receitas prontas de kit
- `references/templates.md` — templates customizados, imagens base, save/load
- `references/cli.md` — comandos, fontes de kit, args, assinatura, políticas

Docs oficiais: <https://docs.docker.com/ai/sandboxes/customize/>
Kits de exemplo: <https://github.com/docker/sbx-kits-contrib>
