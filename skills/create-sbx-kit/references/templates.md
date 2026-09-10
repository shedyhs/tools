# Templates customizados

Fonte: <https://docs.docker.com/ai/sandboxes/customize/templates.md>

Sandboxes são customizáveis, mas as mudanças duram só o tempo de vida do sandbox.
Template empacota um ambiente configurado numa imagem reusável.

**Template vs kit:** template customiza o ambiente de um agente existente — não
cria runtime de agente novo. Runtime novo é `kind: sandbox` kit.

Vale construir template quando: um time compartilha o ambiente, o setup é
demorado, ou versões precisam ser pinadas. Para trabalho pontual, a imagem padrão
basta.

## Imagens base

`docker/sandbox-templates:<variante>` — Ubuntu, usuário não-root `agent` com
sudo. Variantes: `claude-code`, `claude-code-minimal`, `codex`, `copilot`,
`cursor-agent`, `devin`, `docker-agent`, Droid, Gemini CLI, Kiro, OpenCode,
`shell`, `shell-docker`.

### Variantes `-docker`

Imagens com sufixo `-docker` (ex.: `claude-code-docker`) rodam um Docker Engine
completo dentro do sandbox e são o **padrão** dos agentes built-in. Usam volume
de bloco dedicado em `/var/lib/docker`, 10 GB sparse por padrão.

```bash
# redimensionar na criação (mínimo 512 MiB; não redimensiona volume existente)
DOCKER_SANDBOXES_DOCKER_SIZE=20g sbx run claude

# variante sem Docker, mais leve e não privilegiada
sbx run claude --template docker.io/docker/sandbox-templates:claude-code
```

## Construir template customizado

Requer Docker Desktop. Dockerfile estendendo a variante base correspondente:

```dockerfile
FROM docker/sandbox-templates:claude-code
USER root
RUN apt-get update && apt-get install -y protobuf-compiler
USER agent
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

Use `root` para `apt-get`, depois **volte para `agent`** — instaladores que
escrevem no home (`rustup`, `nvm`, `pyenv`) senão caem em `/root/`.

```bash
docker build -t my-org/my-template:v1 --push .
```

O daemon do sandbox puxa direto de registries e **não compartilha o image store
do host**.

Docker Hub reusa a sessão do `sbx login`. Para outros registries, guarde as
credenciais antes:

```bash
gh auth token | sbx secret set --registry ghcr.io --password-stdin
```

Para imagem local, pule o registry:

```bash
docker image save my-org/my-template:v1 -o my-template.tar
sbx template load my-template.tar
sbx run --template my-org/my-template:v1 claude
```

Políticas de rede não permissivas podem exigir allow-list:

```bash
sbx policy allow network "*.example.com:443,example.com:443"
```

Rode com o agente correspondente à variante base:

```bash
sbx run --template docker.io/my-org/my-template:v1 claude
```

Estender `codex` significa rodar `codex`; `shell` dá um bash sem agente. Ao
contrário do `docker`, o `sbx` **não resolve `docker.io` automaticamente**.

**Cache:** o primeiro uso puxa do registry; sandboxes posteriores reusam o cache,
que sobrevive à deleção do sandbox e é limpo por `sbx reset`.

## Salvar sandbox como template

Snapshot de um sandbox rodando, em vez de escrever Dockerfile.

> ⚠️ Captura o **filesystem inteiro** — chaves ou tokens adicionados manualmente
> ficam embutidos e são compartilhados. Use `sbx secret set` para o proxy injetar
> credenciais em runtime.

```bash
sbx template save my-sandbox my-template:v1
sbx run -t my-template:v1 claude
sbx template ls
sbx template rm my-template:v1

# export/import entre máquinas
sbx template save my-sandbox my-template:v1 --output my-template.tar
sbx template load my-template.tar
```

**Limitações:** arquivos de config do agente são recriados na criação do
sandbox, então edições em `/home/agent/.claude/settings.json` ou
`/home/agent/.claude.json` **não persistem**.

Agente incompatível gera warning:

```text
⚠ WARNING: template "my-template:v1" was built for the "claude" agent but you are using "codex".
  The sandbox may not work correctly. Consider using: sbx run -t my-template:v1 claude
```
