# CLI de kits

Fonte: <https://docs.docker.com/ai/sandboxes/customize/kits.md>
Verificado contra `sbx v0.42.1`.

## Comandos de kit

```bash
sbx kit validate <path>          # valida o artefato
sbx kit inspect <path> [--json]  # detalhes do kit
sbx kit pack <path> -o file.zip  # empacota diretório em artefato
sbx kit push <path> <ref>        # publica em registry OCI
sbx kit pull <ref>               # baixa de registry OCI
sbx kit add <sandbox> <path>     # adiciona mixin a sandbox rodando
sbx kit sign <path>              # assina (sigstore/cosign)
sbx kit verify <path>            # verifica assinatura
sbx kit provenance <ref>         # provenance SLSA
```

## Carregar e rodar

Desde 0.42.0, a referência do **sandbox kit** é o **primeiro argumento
posicional** de `sbx run` / `sbx create`. A forma antiga `--kit` para sandbox kit
está deprecada. Mixins usam `--kit`, repetível.

```bash
# agente built-in
sbx run claude

# sandbox kit local (caminho explícito obrigatório: ./ ou ../)
sbx run ./my-agent/

# sandbox kit OCI
sbx run ghcr.io/foo/my-agent:latest

# mixins sobre um built-in
sbx run claude --kit ./my-mixin/ --kit ./outro-mixin/
```

`--kit` só se aplica na **criação**. Para sandbox já rodando:

```bash
sbx kit add <sandbox> <path>
```

Isso reinicia o sandbox preservando o estado da VM, mas suporta **apenas**
`environment.variables`, `setup.install` e `permissions.network.allow`. Arquivos
estáticos, `setup.startup`, `setup.files` e `volumes` exigem recriar o sandbox.

## Fontes de kit

| Fonte | Forma |
|---|---|
| Local | `./my-kit/`, `../my-kit.zip` (caminho relativo precisa ser explícito) |
| Git | `git+https://host/repo.git#ref=<ref>&dir=<subdir>`, `git+ssh://…` |
| OCI | `ghcr.io/org/kit:tag` — Docker Hub exige o prefixo `docker.io` explícito |

## Argumentos de kit

```bash
sbx run claude --kit ./my-kit/ --kit-arg version=1.2.3
sbx run claude --kit ./my-kit/ --kit-arg my-kit.version=1.2.3   # com escopo
sbx run claude --kit ./my-kit/ --kit-args-file ./args.txt
```

Arquivos de args ignoram linhas em branco e iniciadas por `#`. Arquivos
posteriores e flags explícitas sobrescrevem os anteriores. Validação roda antes
da criação do sandbox.

## Restrição de fontes

Por padrão, só `docker.io/` é permitido.

```bash
sbx settings set kit.allowedSources '["docker.io/","github.com/docker/"]'
```

Prefixos casam em fronteira de segmento de caminho. `["*"]` remove a restrição
(desencorajado). Kits locais são controlados por `kit.allowLocalKits`
(default `true`).

Equivalentes por env var: `DOCKER_SANDBOXES_KIT_ALLOWED_SOURCES`,
`DOCKER_SANDBOXES_KIT_ALLOW_LOCAL`.

## Assinatura

Sigstore/cosign, keyless por padrão.

```bash
sbx kit sign ./my-kit/
sbx kit verify \
  --certificate-identity user@example.com \
  --certificate-oidc-issuer https://accounts.google.com \
  ./my-kit/
```

Assinatura com chave usa par ECDSA P-256 (`--key cosign.key` / `cosign.pub`).
Diretórios ganham um `kit.sig.bundle` ao lado do `spec.yaml`; kits OCI guardam
assinaturas como referrers (`sbx kit push … --sign`). **ZIPs não podem ser
assinados.**

Configuração: `kit.trustedSigners`, `kit.requireSignature`.

> A assinatura cobre `spec.yaml` e `files/`, mas **não** tags de imagem nem
> conteúdo baixado — pine esses por digest.

## Debug

```bash
sbx policy log                        # eventos de proxy, domínios bloqueados
sbx policy allow network <host:port>  # liberar domínio
sbx exec <sandbox> -- <cmd>           # inspecionar estado pós-install
sbx rm <sandbox>                      # recomeçar limpo
```

Output de setup aparece **só** durante `run`/`create` — para revê-lo, recrie o
sandbox.
