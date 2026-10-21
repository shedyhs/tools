# config-ecc

Sandbox kit do `sbx` que sobe o Claude Code com um **ECC seletivo** (lista curada
de skills + agentes + comandos), os **hooks do ECC ativos** e o **glab** pronto
para o GitLab da PMMT. Desde a versão 0.2.0, o kit também traz o **mod
jev-model-router** (o Jev escolhe modelo e esforço) e as **regras
de escrita técnica** (STE e português técnico simplificado). Desde a 0.3.0, o
kit traz os **plugins e mods do host** (ponytail, i-have-adhd, answer-pane,
context-bar, output-diet, skill-diet), fixa o Claude Code na versão do host e usa
o ECC 2.2.3. Desde a 0.4.0, o kit também clona vários repositórios de uma pasta
no mesmo sandbox (veja [Vários repos no mesmo sandbox](#vários-repos-no-mesmo-sandbox)).

## Uso

Os defaults do kit são neutros: identidade git vazia e `gitlab.com` como host.
Os valores da sua máquina entram na invocação. A função abaixo fica no
`~/.zshrc` e busca esses valores a cada run:

```zsh
sbxecc() {
  local kit=/home/shedy/tools/sbx/kits/config-ecc
  local host name repo=. ws pg=~/.config/pg-mcp/connections.json
  local -a rest subrepos paths
  subrepos=( */.git(N/:h) )   # so .git pasta: o script do kit tambem exige -d
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1 && (( $#subrepos )); then
    repo=$subrepos[1]
  fi
  host=$(git -C "$repo" config --get remote.origin.url 2>/dev/null \
    | sed -E 's#^[a-z]+://([^/@]*@)?([^/:]+).*#\2#; s#^[^@]+@([^:]+):.*#\1#')
  rest=()
  while (( $# )); do
    case "$1" in
      --name)   name="$2"; shift 2 ;;
      --name=*) name="${1#--name=}"; shift ;;
      *)        rest+=("$1"); shift ;;
    esac
  done
  : ${name:=ecc-${PWD:t}}
  if [[ $repo != . ]]; then
    ws=~/.local/share/sbxecc/$name
    # --clone exige repo no workspace primario, e o "." vira o mount read-only.
    rest=( ${rest:#--clone} )
    # (b) escapa [ * ? do caminho; a barra final tambem conta como o mesmo caminho.
    rest=( ${${${${rest:#.}:#./}:#${(b)PWD}}:#${(b)PWD}/} )
    paths=( "$ws" "${PWD}:ro" )   # chaves: "$PWD:r" seria modificador do zsh
    rest=( --kit-arg multi_repo_source="$PWD" "${rest[@]}" )
    print -r -- "[sbxecc] multi-repo: ${(j:, :)subrepos} -> $ws"
  fi
  if ! sbx ls 2>/dev/null | awk '{print $1}' | grep -qx "$name"; then
    [[ -n $ws ]] && { mkdir -p "$ws" || return 1; }
    sbx create --name "$name" "$kit" "${paths[@]}" \
      --kit-arg git_user_name="$(git config --global user.name)" \
      --kit-arg git_user_email="$(git config --global user.email)" \
      --kit-arg gitlab_host="${host:-gitlab.com}" \
      "${rest[@]}" || return 1
    if [[ -f $pg ]]; then
      sbx exec "$name" mkdir -p /home/agent/.config/pg-mcp
      sbx cp "$pg" "$name:/home/agent/.config/pg-mcp/connections.json" \
        && print -r -- "[sbxecc] pg-mcp connections.json copiado para $name"
    fi
  fi
  sbx run --name "$name"
}
```

`gitlab_host` sai do `origin` do repositório onde você está. Em uma pasta que
não é repo, mas tem subrepos, ele sai do primeiro subrepo. Sem identidade, o
`setup.install` avisa em stderr que `git commit` vai falhar — e segue, porque
nem todo uso precisa commitar.

Setup uma vez (token fica no host; o container só vê um placeholder):

```bash
sbx secret set-custom --host gitlab.example.com --env GITLAB_TOKEN \
  --value "$(glab config get token --host gitlab.example.com)"
```

Depois, todo sandbox sobe autenticado:

```bash
sbx run ./kits/config-ecc /caminho/do/projeto

sbx run ./kits/config-ecc . --kit-arg ecc_ref=v2.2.1 --kit-arg gateguard=off
```

A credencial da Anthropic não precisa de nada aqui: o login do `sbx` já persiste.

Para ligar o roteador de modelos, guarde a chave da TypeSafe uma vez, como o
token do GitLab. A chave fica no host, e o container só vê um placeholder:

```bash
sbx secret set-custom --host api.typesafe.ai --env TYPESAFE_API_KEY \
  --value "$(jq -r '.pluginConfigs["jev-model-router@skills-dir"].options.typesafeApiKey' ~/.claude/settings.json)"
```

Sem esse secret, o mod sai do sandbox e o Claude roda sem ele.

## Quais skills entram

A lista curada fica em `files/home/.ecc-skills` — um arquivo texto, uma linha,
IDs separados por vírgula. Editar o arquivo é o jeito de mudar o conjunto; o
`setup.install` lê dele.

```
agent-harness-construction,api-design,autonomous-agent-harness,autonomous-loops,backend-patterns,blueprint,coding-standards,configure-ecc,continuous-agent-loop,continuous-learning,continuous-learning-v2,database-migrations,deployment-patterns,django-patterns,django-tdd,django-verification,dmux-workflows,docker-patterns,eval-harness,frontend-patterns,java-coding-standards,jpa-patterns,kubernetes-patterns,orch-add-feature,orch-build-mvp,orch-change-feature,orch-fix-defect,orch-pipeline,orch-refine-code,parallel-execution-optimizer,plan-orchestrate,postgres-patterns,prompt-optimizer,python-patterns,python-testing,react-patterns,react-performance,react-testing,redis-patterns,security-review,security-scan,springboot-patterns,springboot-security,springboot-tdd,springboot-verification,strategic-compact,tdd-workflow,team-agent-orchestration,team-builder,verification-loop
```

**`--skills` não instala só esses.** O instalador do ECC resolve a lista como
módulos `skill-<id>` **em cima de uma baseline** (`rules-core`, `agents-core`,
`commands-core`, `platform-configs`, `framework-language`, `workflow-quality`,
`security`, `skill-unified-memory`). Resultado medido: **156 skills, 67 agentes,
94 comandos** — contra 375 skills do plugin completo. Para cortar mais, use
`--without <component>` no comando do `setup.install` (`ecc catalog` lista os 81
componentes).

Da lista original de 67 IDs: 32 são skills, 12 são **agentes**
(`architect`, `planner`, `code-reviewer`, `tdd-guide`, `build-error-resolver`,
`database-reviewer`, `doc-updater`, `e2e-runner`, `harness-optimizer`,
`loop-operator`, `python-reviewer`, `refactor-cleaner`), 17 são **comandos**
(`plan`, `code-review`, `quality-gate`, `test-coverage`, `update-docs`, …) e 6
são **shims legados** (`tdd`, `eval`, `e2e`, `verify`, `orchestrate`,
`prompt-optimize`). Agentes e comandos não passam por `--skills` — vêm pelos
módulos `agents-core`/`commands-core`, que a baseline já traz.

### Orquestração

Os comandos `/orch-*` são **wrappers** que disparam skills de mesmo nome
("Wrapper that kicks off the orch-add-feature skill"). Os comandos vêm pelo
`commands-core`, mas as skills não vinham — comando presente e skill ausente
dispara para o vazio. Por isso a lista inclui `orch-add-feature`,
`orch-build-mvp`, `orch-change-feature`, `orch-fix-defect`, `orch-refine-code`,
`orch-pipeline`, mais `plan-orchestrate`, `team-agent-orchestration`,
`team-builder`, `parallel-execution-optimizer` e `autonomous-loops`.

O antigo `/orchestrate` é shim legado e **não é instalado** (nenhum módulo traz
`legacy-command-shims/`). Os equivalentes mantidos são `autonomous-agent-harness`
(loop autônomo, memória persistente, agendamento) e `dmux-workflows` (panes tmux,
worktrees, sessões paralelas) — ambos na lista.

## Args

| Arg | Default | Valores | Efeito |
|---|---|---|---|
| `ecc_ref` | `v2.2.3` | tag `vX.Y.Z` | Tag do repositório ECC clonada |
| `claude_version` | `2.1.301` | `X.Y.Z` | Versão do Claude Code (`claude install`). Os mods exigem 2.1.301 ou mais nova |
| `hook_profile` | `standard` | `minimal`, `standard`, `strict` | `ECC_HOOK_PROFILE` |
| `gateguard` | `on` | `on`, `off` | `ECC_GATEGUARD` |
| `glab_version` | `1.117.0` | `X.Y.Z` | Versão do GitLab CLI |
| `gitlab_host` | `gitlab.com` | hostname | GitLab do glab, liberado na rede |
| `git_user_name` | *(vazio)* | texto | `git config --global user.name` |
| `git_user_email` | *(vazio)* | e-mail | `git config --global user.email` |
| `dirty_guard` | `block` | `off`, `warn`, `block` | O que fazer com trabalho não commitado ao encerrar |
| `copy_from_host` | *(vazio)* | lista por vírgula | Arquivos ignorados pelo git a copiar do repo do host (com `--clone` ou `multi_repo_source`) |
| `multi_repo_source` | *(vazio)* | caminho absoluto | Pasta do host com vários repos. O startup clona cada subrepo no workspace (veja [Vários repos no mesmo sandbox](#vários-repos-no-mesmo-sandbox)) |
| `disabled_hooks` | *(vazio)* | IDs minúsculos por vírgula | `ECC_DISABLED_HOOKS` |
| `model_router` | `on` | `on`, `off` | Liga o mod `jev-model-router` (precisa do secret `TYPESAFE_API_KEY`) |

Todo arg interpolado em comando tem `enum` ou `pattern` — a substituição
`${{ kit.args.X }}` é textual e roda antes do parse do YAML, então a restrição é
o que impede injeção de shell no `setup.install`.

## O que o kit entrega

1. **Clone pinado.** `github.com/affaan-m/ECC` na tag do arg, em
   `/home/agent/.ecc/ECC`, com tag + SHA gravados em `installed-ref`. Trocar de
   tag refaz o clone; nada é ignorado em silêncio.
2. **Instalação seletiva.** `install-apply.js --target claude --modules
   hooks-runtime --skills <lista> --enable-hooks` popula
   `~/.claude/{skills,agents,commands,rules,scripts,hooks}`. O ECC 2.2 exige as
   deps npm de produção, então o clone roda `npm ci --omit=dev`.
3. **Hooks ativados.** O ECC 2.2 mescla os hooks no `~/.claude/settings.json`,
   que pertence ao kit `claude`. O kit guarda uma cópia em
   `~/.ecc/settings.ecc.json` e devolve o `settings.json` ao estado anterior.
   Depois, transplanta o bloco para `/home/agent/.config/claude/ecc.json`, que
   entra via `--settings` no `sandbox.command`. Com `ecc_ref` anterior à 2.2, a
   fonte é `~/.claude/hooks/hooks.json`. Falha alto se o bloco vier vazio.
4. **glab** com SHA256 conferido contra o `checksums.txt` da release.
5. **Identidade git** — sem ela o `git commit` falha, e o sandbox vem sem.
6. **Auth GitLab por HTTPS** via `glab auth git-credential` como credential
   helper.
7. **Mod jev-model-router** em `~/.local/share/claude-plugins/jev-model-router`.
   O `jev-config.sh` grava a chave no `ecc.json` na partida, ou remove a pasta
   quando o mod está desligado. Veja [Roteador de modelos](#roteador-de-modelos).
8. **Escrita técnica:** as skills `asd-ste100` e `portugues-tecnico-simplificado`
   e a seção de escrita do `CLAUDE.md`. O idioma do Claude fica em `pt-BR`
   (`language` no `ecc.json`).
9. **Plugins e mods do host** em `~/.local/share/claude-plugins/<nome>`. Um
    segundo `--plugin-dir` aponta para a pasta, e o Claude carrega cada
    subpasta. A cópia sai de `~/.claude/plugins/cache/` sem `.git`, `tests`,
    `benchmarks`, `evals` e `node_modules`. O plugin `ecc` fica de fora, porque o
    kit já instala o ECC (item 2). O `typesafe` também fica de fora, porque está
    desligado no host.
10. **Skills extras do host:** `archify`, `archify-review`,
    `logging-best-practices` e `migrar-app-entre-namespaces`. A
    `create-sbx-kit` fica de fora: o `sbx kit validate` lê `${{ kit.args.<nome> }}`
    na documentação dela como placeholder e rejeita o kit. A `jev-model-router` não
    entra nesta lista: o kit a traz como mod, veja [Roteador de modelos](#roteador-de-modelos).

Para atualizar a partir do host, copie de novo os itens 10 e 11 e o
`statusline-command.sh`, e ajuste `ecc_ref` e `claude_version`. Depois, rode
`sbx kit validate` e recrie um sandbox do zero.

## Rules

O Claude Code carrega `~/.claude/rules/**/*.md` nativamente como memória de
usuário ("private global instructions") — não precisa de import no `CLAUDE.md`.
Verificado no binário 2.1.267 e no comportamento do host.

O kit instala o conjunto completo do ECC: **122 arquivos de rule (279 KB)**,
cobrindo todas as linguagens do repo (arkts, cpp, dart, perl, rust, swift, ruby,
vue, angular, react-native…), não só as do seu stack. Tudo isso entra como
contexto sempre-ligado. É uma escolha consciente: nada é podado.

Se um dia quiser recortar, **não use `--without lang:X`** — testado: excluir
qualquer componente `lang:`/`framework:` derruba o módulo `framework-language`
inteiro, as rules vão a zero e as skills caem de 156 para 70. O caminho viável é
podar `~/.claude/rules/ecc/<lang>` num passo pós-install.

## CLAUDE.md do sandbox

Sem o kit, o sandbox sobe **sem nenhum `CLAUDE.md`** — nem no workspace, nem no
home (verificado). O agente não saberia que o ECC está instalado, que os agentes
perderam o prefixo `ecc:` ou que `GITLAB_TOKEN` é um placeholder.

O kit entrega `files/home/.claude/CLAUDE.md`, que vira `~/.claude/CLAUDE.md`
dentro do container — memória de **usuário**, fora do workspace montado. Cobre:
ECC seletivo e onde estão as coisas, agentes sem prefixo, hooks ativos e como
desligá-los, git/glab prontos, placeholder do token, a rede restrita e o
mod jev-model-router. No fim, ele traz a seção "Technical Writing: ASD-STE100"
copiada do `~/.claude/CLAUDE.md` do host, com a parte de pt-BR.

Editar o conteúdo é editar esse arquivo no kit. Duas coisas a lembrar:

- **Não use `agentInstructions` para isso.** Num `kind: sandbox` ele vira arquivo
  no diretório do AI file, ou seja, dentro do workspace montado — sujaria o
  repositório do host.
- O instalador do ECC também deixa um `~/.claude/AGENTS.md` (172 linhas, conteúdo
  genérico do ECC). Ele descreve o ECC, não este ambiente; se o Claude Code
  carrega AGENTS.md em escopo de usuário, não verifiquei.

## Arquivos ignorados pelo git (.env, certs)

Com `--clone`, o clone só tem o que está versionado — `.env` e afins ficam de
fora. Mas o repo do host fica montado **read-only em `/run/sandbox/source`**
dentro do container, então o kit consegue buscar de lá:

```bash
sbxecc --clone --kit-arg copy_from_host=.env,certs .
```

Default vazio: **nada é copiado sem pedido explícito**. A cópia roda no
`setup.startup`, nunca sobrescreve arquivo já existente no workspace, e avisa no
log o que copiou, o que não achou e o que manteve. Sem `--clone` o mount não
existe e o passo não faz nada (o bind mount já traz tudo).

Como esses arquivos são ignorados pelo git, eles **não voltam** para o host num
`git fetch sandbox-<nome>` — verificado: `git status` limpo depois da cópia.

⚠️ Isso move segredo para dentro de um sandbox onde o agente roda com
`--dangerously-skip-permissions`. Prefira credenciais de dev; para rodar testes,
veja antes se um `.env.test` versionado já resolve.

Ressalva: `setup.startup` não segura o entrypoint — o agente pode subir uma
fração de segundo antes do arquivo aterrissar.

## Vários repos no mesmo sandbox

O `--clone` do sbx clona só o workspace primário, e ele precisa ser um repo git.
Os workspaces extras sempre entram como bind mount, também no `sbxenv.yaml`.
Para uma pasta como `~/git/seamme` (sem `.git`, com `back/`, `front/` e
`external-penha-api/` dentro), o kit faz o clone ele mesmo:

```bash
cd ~/git/seamme && sbxecc --kit-arg copy_from_host=.env .
```

O `sbxecc` detecta o caso: a pasta atual não é repo, mas tem subrepos. Então ele:

1. Usa `~/.local/share/sbxecc/<nome>` como workspace primário (vazio e gravável).
2. Monta a pasta atual como read-only.
3. Passa `--kit-arg multi_repo_source=<pasta>` e remove o `--clone` e o `.`.

No startup, o `clone-multi-repo.sh` faz isto para cada subrepo:

- `git clone` com todas as branches locais do host.
- Os remotes do host, com as refs de tracking e o upstream de cada branch. Só
  entram remotes com nome simples (`A-Z a-z 0-9 . _ -`) e URL `https://`,
  `ssh://` ou `git@host:`. Remote de caminho local fica de fora, como no
  `--clone`.
- Os itens de `copy_from_host` de cada repo (ex, `back/.env`).

O `.git/config` da origem não é confiável, e nada dele é copiado em bloco. O
script lê cada valor com `git config --get` e só grava no clone o que passa
pela allowlist: a URL do remote e o `remote`/`merge` de cada branch. Com isso,
um `core.fsmonitor` ou `core.hooksPath` da origem não chega ao clone. Os comandos
na origem rodam com `safe.directory` só para aquele repo, e com `fsmonitor` e
hooks desligados. O `.gitconfig` não é alterado.

Itens de `copy_from_host` com `..`, caminho absoluto ou symlink que sai do repo
são recusados. Symlinks de topo na pasta de origem são ignorados.

Os itens de topo que não são repo (`docker-compose.yml`, CSVs, `.claude/`) são
copiados por inteiro, inclusive pastas grandes e arquivos sensíveis (`.env`,
`.npmrc`). Nada que já existe no workspace é sobrescrito.

Cada clone é feito em `<repo>.tmp` e renomeado no fim. Um clone interrompido,
por exemplo por um `sbx stop`, é refeito no próximo start. O script recusa
rodar se o workspace ficar dentro da pasta de origem.

⚠️ Não rode git, IDE ou direnv do host em `~/.local/share/sbxecc/<nome>`. O
agente do sandbox escreve nessa pasta, inclusive em `.git/hooks` e
`.git/config`. Use só `git fetch <caminho>` a partir do repo do host, como
mostrado em "Diferenças" abaixo. O fetch não executa hooks nem config do clone.

⚠️ O `setup.startup` não segura o entrypoint. No primeiro start, o agente pode
abrir enquanto os clones ainda rodam, e a pasta aparece vazia por um tempo. Se
um clone falhar, o erro só aparece no log do startup. Os remotes copiados mantêm
a URL do host, inclusive credenciais embutidas (`https://user:token@...`).

Diferenças em relação ao `--clone`:

- Não existe o remote `sandbox-<nome>`. Os clones ficam no host, então o fetch é
  direto: `git -C ~/git/seamme/back fetch ~/.local/share/sbxecc/ecc-seamme/back`.
- Os clones sobrevivem ao `sbx rm`. Um `sbxecc` novo com o mesmo nome reaproveita
  os clones. Para começar do zero, apague `~/.local/share/sbxecc/<nome>`.
- O dirty-guard olha só o diretório atual do agente, que não é repo. Como os
  clones ficam no host, trabalho não commitado não se perde com o sandbox.

## Trabalho não commitado ao encerrar

Num sandbox `--clone`, `git fetch sandbox-<nome>` no host traz **apenas commits**
— arquivo não commitado morre junto com o sandbox. O kit registra um hook `Stop`
próprio (`files/home/.local/bin/dirty-guard.mjs`) que checa o workspace e reage
conforme o arg `dirty_guard`:

| Modo | Comportamento |
|---|---|
| `warn` | `systemMessage` visível, não interrompe |
| `block` (default) | `exit 2` — o Claude Code devolve a mensagem ao agente, que precisa commitar antes de encerrar |
| `off` | desligado |

Detecta duas situações: arquivos não commitados e commits locais à frente do
upstream. Repo limpo não gera ruído. O guard entra **junto** dos hooks do ECC no
mesmo `ecc.json` — o passo de transplante concatena a entrada `stop:dirty-guard`
no array `Stop`.

`block` respeita `stop_hook_active` para não entrar em laço infinito.

O padrão é `block`: o agente é cobrado a commitar já na primeira parada com o
repo sujo. Em trabalho exploratório isso pode incomodar — nesse caso,
`--kit-arg dirty_guard=warn` (só avisa) ou `=off`.

## Roteador de modelos

O kit traz o mod `jev-model-router` (versão 0.4.2, copiada do host). Ele roda
dentro do Claude Code e consulta o Jev, o modelo de decisão da TypeSafe, pela
API `api.typesafe.ai`. A cada mensagem, o Jev escolhe o modelo (Haiku, Sonnet ou
Opus) e o esforço (`low` a `max`). Com dúvida, o mod usa o menor modelo que soma
80% da probabilidade. Se a TypeSafe falhar, o mod deixa a requisição seguir como
o motor a montou.

Por padrão o mod troca o esforço da conversa principal e o modelo de cada
subagente. A troca de modelo da conversa principal fica desligada, porque ela
invalida o cache de prompt. Essas opções são do próprio mod, em `pluginConfigs`.

Como o kit liga o mod:

1. No `setup.files`, a pasta do mod vai para `~/.local/share/claude-plugins/`. A
   pasta é carregada pelo `--plugin-dir` do sbx, como os outros mods.
2. No `setup.startup`, `jev-config.sh` roda a cada partida:
   - Se `model_router=on` e `TYPESAFE_API_KEY` existe, ele grava
     `pluginConfigs["jev-model-router"].options.typesafeApiKey` em
     `~/.config/claude/ecc.json`.
   - Senão, apaga a pasta do mod e remove `pluginConfigs` do `ecc.json`. O
     Claude roda sem o mod.
3. A chave gravada é o placeholder `sbx-cs-…`, não o valor real. O proxy do sbx
   troca o placeholder pela chave real na requisição a `api.typesafe.ai`.

O `ecc.json` não guarda segredo real. Ele é regravado a cada partida.

Diferenças em relação ao host:

- No host, o mod é o `jev-model-router@skills-dir`, lido de
  `~/.claude/skills/jev-model-router/`. No sandbox, a cópia fica em
  `~/.local/share/claude-plugins/` e a chave vem do `ecc.json`.
- No host, o mod é `jev-model-router@skills-dir`. No sandbox, a chave fica em
  `pluginConfigs["jev-model-router"]`, porque o `--plugin-dir` carrega o mod
  com essa chave.
- Não há mais proxy local nem `ANTHROPIC_BASE_URL`. O Claude fala direto com a
  Anthropic, e o mod chama o Jev sozinho.

Teste de 0.5.0, com sandbox descartável (já removido):

- `claude plugin validate` passou. O mod registra `prompt.submit`, `turn.step` e
  `agent.spawn`.
- `claude -p` respondeu `ok` com exit 0.
- O log de rede do `sbx` mostrou uma chamada a `api.typesafe.ai:443`, pelo
  proxy.
- Uma requisição a `api.typesafe.ai/v1/systemone` com o placeholder devolveu
  422 (erro de formato do meu corpo vazio), e não 401. O proxy aceitou a
  autenticação.
- Não confirmei a decisão do Jev dentro de uma sessão interativa. O `claude -p`
  não mostra o log do mod.

## Mods com painel

O Claude Code do sandbox só carrega mods com painel quando
`CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`. A imagem base vem com a 2.1.280, que
rejeita a API de mods do answer-pane, do context-bar e do output-diet. Por isso
o kit instala a versão do arg `claude_version`. O kit define essa variável.

## Autenticação no GitLab

- O token real fica no host; no container `GITLAB_TOKEN` vale um placeholder
  (`sbx-cs-…`) e o proxy troca pelo valor real nas requisições ao host.
- **Cobre os dois usos**: API do `glab` (Bearer/PRIVATE-TOKEN) e git-over-HTTPS
  (Basic, via credential helper).
- **Rotação:** rode o mesmo `set-custom` com o token novo.
- **Armadilha:** não mantenha secret global e `--sandbox` para a mesma env var —
  o sbx recusa com `duplicate custom secret env "GITLAB_TOKEN"`.
- **Não declare `credentials:` no kit para esse host:** o sentinel
  `proxy-managed` colide com o placeholder. E o bloco `credentials` tem
  limitação própria — o kit `gitlab` do `sbx-kits-contrib` documenta que duas
  regras de `inject` no mesmo domínio não funcionam (o proxy não separa Bearer de
  Basic). O custom secret não tem esse problema.

Alternativa com o token dentro do container:
`-e GITLAB_TOKEN="$(glab config get token --host gitlab.example.com)"`.

## Autenticação no GitHub

O `gh` já vem na imagem do `sbx` (2.46). O sandbox define `GH_TOKEN` com um
placeholder (`gho_sbxp…`), e o proxy troca esse valor pelo token real do secret
`github` do `sbx`. Sem o secret, o placeholder não vale nada: o `gh auth status`
responde "token inválido". Guarde o secret uma vez, no host:

```bash
sbx secret set github --command 'gh auth token'
```

O `--command` não copia o token. O `sbx` roda o `gh auth token` no host quando
precisa e guarda o resultado em cache. Um `gh auth refresh` no host vale para os
próximos usos, sem repetir o comando. Para escopo de um sandbox só, acrescente
`--sandbox <nome>`.

O kit configura o resto no `setup.install`:

- `credential.https://github.com.helper` aponta para `gh auth git-credential`,
  então `git clone` e `git push` por HTTPS usam o mesmo token.
- `gh config set git_protocol https` para `github.com`.
- A rede libera `github.com:443` e `api.github.com:443`.

O token do host é um OAuth com os escopos que você deu ao `gh auth login`
(`repo`, `workflow` e outros). O agente roda com `--dangerously-skip-permissions`
e age em seu nome no GitHub. Se quiser menos poder, rode `gh auth login` no host
com um token de escopo menor, ou guarde um PAT fino com
`echo "$PAT" | sbx secret set github`.

## Rede

```yaml
allow:
  - "github.com:443"           # clone do ECC, git do gh
  - "api.github.com:443"       # API do gh
  - "gitlab.com:443"           # release do glab
  - "gitlab.example.com:443"  # GitLab de trabalho (arg gitlab_host)
  - "api.typesafe.ai:443"     # Jev (mod jev-model-router)
```

`github.com:443` basta para o clone (testado sem `codeload` e
`objects.githubusercontent.com`). O GitLab da PMMT responde por HTTPS através do
proxy sem CA interna. As permissões do agente `claude` pai são herdadas.

## Decisões de projeto

- **Instalação seletiva em vez do plugin.** Instalar `ecc@ecc` como plugin traz
  as 375 skills (~34,7k tokens always-on) e não permite recorte. O instalador
  aceita a lista curada e para em 156 skills.
- **Hooks transplantados para a camada `--settings`.** É o que torna a via
  seletiva viável: sem isso, `~/.claude/hooks/hooks.json` fica inerte. O kit
  `ecc` oficial do `sbx-kits-contrib` usa `--profile minimal` e **não instala os
  hooks** — este kit existe justamente para tê-los.
- **`~/.claude/settings.json` não é tocado.** Sem `claude plugin install`, nada
  escreve no caminho reservado do agente; os hooks entram pela camada extra,
  que é a receita sancionada. Blocos `hooks` de camadas diferentes são
  concatenados, não substituídos.
- **Sandbox kit, não mixin:** só `kind: sandbox` altera a cauda do comando
  (`--settings`). Como `sandbox.command` **substitui** a cauda herdada,
  `--dangerously-skip-permissions` é reafirmado explicitamente.
- **Nada é escrito no workspace.** As instruções do agente vão para
  `~/.claude/CLAUDE.md` via `files/home/`, não via `agentInstructions` — que num
  sandbox kit viraria arquivo dentro do workspace montado do host.

- **Mod em vez de proxy.** Até a 0.4.0, o kit subia o `claude-model-router` como
  proxy local, com entrypoint `claude-routed`. Desde a 0.5.0, o mod roda dentro
  do Claude Code, sem processo extra, sem `uv` e sem `pypi.org`. O entrypoint
  voltou ao padrão do agente `claude`.

## Verificado

Sandbox criado do zero, `sbx v0.42.1`:

- **156 skills, 67 agentes, 94 comandos** instalados; as skills da lista
  conferidas uma a uma (`python-patterns`, `springboot-tdd`, `jpa-patterns`,
  `configure-ecc`, `verification-loop`, …);
- `ecc.json` com os 7 eventos: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`,
  `SessionStart`, `SessionEnd`, `Stop`, `PreCompact`;
- **hook executa**: o dispatcher devolveu `permissionDecision: deny` para
  `npm run dev` com `gateguard=on`;
- **nenhum plugin instalado** (`claude plugin list` sem `ecc@ecc`);
- **commit funciona**: `git commit` assinou como a identidade passada por `--kit-arg`;
- **credencial injetada no startup**: sandbox novo sobe com
  `GITLAB_TOKEN=sbx-cs-…`, `glab auth status` loga com o usuario do token e
  `git ls-remote` num repo real da PMMT retorna os refs, sem `-e`. O `push` usa
  o mesmo header Basic (auth verificada na leitura; escrita não testada contra
  produção);
- **`~/.claude/CLAUDE.md` entregue** (1838 bytes) e workspace sem nenhum arquivo
  novo — testado com workspace limpo, sem `CLAUDE.md` prévio;
- workspace montado intacto; SSH agent do host é encaminhado
  (`SSH_AUTH_SOCK=/run/ssh-agent.sock`).

Roteador e painel (até a 0.4.0, com o `claude-model-router`), sandbox criado do zero com `sbx v0.46.0` (Claude Code
2.1.280):

- `sbx kit validate` aprova o kit, e o `--selftest` do roteador passa no
  `setup.install`;
- **sem o secret:** o entrypoint avisa em stderr, e o Claude responde direto;
- **com uma chave falsa:** o roteador sobe, o Claude passa por ele, a TypeSafe
  responde 401 pelo proxy, e o roteador usa opus e `high`. A resposta da
  Anthropic chega pelo proxy;
- `--stats` e `--stats-json` leem o log em arquivo dentro do sandbox;
- **porta ocupada por outro serviço:** o entrypoint espera 15 s, avisa e roda o
  Claude direto;
- uma segunda execução do entrypoint não sobe um segundo roteador;
- o `policy log` só mostra liberados `api.anthropic.com`, `api.typesafe.ai` e
  `files.pythonhosted.org` para o roteador.

### Multi-repo (0.4.0)

- **Script no host**, contra `~/git/seamme`: três repos clonados, com as
  branches, os remotes de URL e o upstream de cada branch batendo com o host.
  Os `.env` de `copy_from_host` foram copiados. Uma segunda execução manteve
  tudo. Uma fonte ausente saiu com 1, e uma fonte vazia saiu com 0.
- **Clone interrompido:** uma pasta `<repo>.tmp` deixada para trás foi refeita
  no start seguinte, e a `.tmp` não ficou no workspace.
- **Workspace dentro da fonte:** recusado com exit 1.
- **Repo hostil** (teste com repo montado à mão): um `merge` com `\n` tentando
  injetar `core.fsmonitor`, remotes de nome `*` e `--upload-pack=...`, URLs
  `ext::`, `../outro` e `foo/bar`, `insteadOf` e `core.fsmonitor` na origem.
  Nada disso chegou ao clone. Depois de `git status` e `git fetch` no clone, o
  arquivo marcador não foi criado. `copy_from_host` recusou `../..`, `/etc/passwd`
  e dois symlinks para fora do repo. Antes dessa correção, o `core.fsmonitor`
  chegava ao clone (reproduzido).
- **Sandbox `shell` descartável** (já removido): o mount `<pasta>:ro` apareceu
  no mesmo caminho do host, com uid 1000. Escrita nele falhou com
  `Read-only file system`. O script rodou dentro do sandbox e clonou os três
  repos, com `git status` batendo com o host.
- **`sbxecc`** com `sbx` falso: o comando gerado é o esperado nos dois modos.
  `--clone`, `.`, `./` e o caminho absoluto são removidos do modo multi-repo.
- **Não testado:** o `sbx run` completo com o kit `config-ecc`, com o agente
  interativo. O primeiro create ainda não foi feito com este kit.

## Limitações

- **Agentes perdem o prefixo `ecc:`.** Instalados como agentes de usuário
  (`~/.claude/agents/`), chamam-se `planner`, `code-reviewer`, `tdd-guide` — não
  `ecc:planner`. Regras que assumem o namespace do plugin não valem aqui.
- **156 skills, não 50.** A baseline do instalador entra junto; cortar mais
  exige `--without`.
- `setup.install` roda a cada criação e não é cacheado. Para eliminar o custo,
  asse clone + install numa imagem de template (`sbx template`).
- O kit replica só parte da config pessoal do host: a seção de escrita do
  `CLAUDE.md`, as skills e os plugins listados, a statusline e o `language`.
  Settings e MCP ficam de fora. Para isso existe `~/.claude/sbx-sync-config.sh`,
  que gera `claude-ecc:latest`.
- Os plugins são uma cópia fixa. Uma atualização no host não chega ao kit até
  você copiar de novo (veja o fim de [O que o kit entrega](#o-que-o-kit-entrega)).
- Os mods com painel são early access no Claude Code. Uma versão nova pode mudar
  a API ou dispensar `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`.
- **O painel dos mods novos não foi visto na tela do sandbox.** O teste da 0.3.0
  confirmou que os 7 plugins carregam (evento `init` do `claude -p`), mas não
  abriu uma sessão interativa autenticada.
- **Multi-repo sem remote nativo.** Os clones do modo multi-repo ficam no host,
  em `~/.local/share/sbxecc/<nome>`. Não há remote `sandbox-<nome>`, então o
  fetch é feito pelo caminho do clone. Veja [Vários repos no mesmo sandbox](#vários-repos-no-mesmo-sandbox).
- **Multi-repo sem trava no startup.** O agente pode abrir antes de os clones
  terminarem. Um erro de clone aparece só no log do startup.
- **Multi-repo sem dirty-guard nos subrepos.** O `dirty-guard` olha só o diretório
  atual do agente, que não é repo. Trabalho não commitado dos subrepos não é
  avisado ao encerrar.

## Referências

- Exemplos oficiais: <https://github.com/docker/sbx-kits-contrib> — vale ler
  `ecc/` (instalação sem hooks), `gitlab/` (limitação do inject duplo) e
  `gitlab-ssh/` (host keys pinados).
