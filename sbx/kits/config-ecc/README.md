# config-ecc

Sandbox kit do `sbx` que sobe o Claude Code com um **ECC seletivo** (lista curada
de skills + agentes + comandos), os **hooks do ECC ativos** e o **glab** pronto
para o GitLab da PMMT. Desde a versão 0.2.0, o kit também traz o **roteador de
modelos** (o Jev escolhe modelo e esforço), o **painel `/router`** e as **regras
de escrita técnica** (STE e português técnico simplificado).

## Uso

Os defaults do kit são neutros: identidade git vazia e `gitlab.com` como host.
Os valores da sua máquina entram na invocação — a função de shell abaixo os
busca a cada run:

```bash
sbxecc() {
  local host
  host=$(git config --get remote.origin.url 2>/dev/null \
    | sed -E 's#^[a-z]+://([^/@]*@)?([^/:]+).*#\2#; s#^[^@]+@([^:]+):.*#\1#')
  sbx run /caminho/do/kit \
    --kit-arg git_user_name="$(git config --global user.name)" \
    --kit-arg git_user_email="$(git config --global user.email)" \
    --kit-arg gitlab_host="${host:-gitlab.com}" \
    "$@"
}
```

`gitlab_host` sai do `origin` do repositório onde você está. Sem identidade, o
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
  --value "$(sed -n 's/^TYPESAFE_API_KEY=//p' ~/.config/claude-model-router/env)"
```

Sem esse secret, o sandbox sobe normalmente e o Claude roda sem roteador.

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
| `ecc_ref` | `v2.1.0` | tag `vX.Y.Z` | Tag do repositório ECC clonada |
| `hook_profile` | `standard` | `minimal`, `standard`, `strict` | `ECC_HOOK_PROFILE` |
| `gateguard` | `on` | `on`, `off` | `ECC_GATEGUARD` |
| `glab_version` | `1.117.0` | `X.Y.Z` | Versão do GitLab CLI |
| `gitlab_host` | `gitlab.com` | hostname | GitLab do glab, liberado na rede |
| `git_user_name` | *(vazio)* | texto | `git config --global user.name` |
| `git_user_email` | *(vazio)* | e-mail | `git config --global user.email` |
| `dirty_guard` | `block` | `off`, `warn`, `block` | O que fazer com trabalho não commitado ao encerrar |
| `copy_from_host` | *(vazio)* | lista por vírgula | Arquivos ignorados pelo git a copiar do repo do host (só com `--clone`) |
| `disabled_hooks` | *(vazio)* | IDs minúsculos por vírgula | `ECC_DISABLED_HOOKS` |
| `model_router` | `on` | `on`, `off` | Liga o roteador de modelos (precisa do secret `TYPESAFE_API_KEY`) |
| `router_confidence_min` | `0.5` | número de 0 a 1 | `ROUTER_CONFIDENCE_MIN`: abaixo dela, o roteador usa opus e `high` |

Todo arg interpolado em comando tem `enum` ou `pattern` — a substituição
`${{ kit.args.X }}` é textual e roda antes do parse do YAML, então a restrição é
o que impede injeção de shell no `setup.install`.

## O que o kit entrega

1. **Clone pinado.** `github.com/affaan-m/ECC` na tag do arg, em
   `/home/agent/.ecc/ECC`, com tag + SHA gravados em `installed-ref`. Trocar de
   tag refaz o clone; nada é ignorado em silêncio.
2. **Instalação seletiva.** `install-apply.js --target claude --modules
   hooks-runtime --skills <lista>` popula `~/.claude/{skills,agents,commands,rules,scripts,hooks}`.
3. **Hooks ativados.** O instalador resolve os hooks em
   `~/.claude/hooks/hooks.json` — caminho que o Claude Code **não lê sozinho**.
   O kit transplanta esse bloco para `/home/agent/.config/claude/ecc.json`, que
   entra via `--settings` no `sandbox.command`. Falha alto se o bloco vier vazio.
4. **glab** com SHA256 conferido contra o `checksums.txt` da release.
5. **Identidade git** — sem ela o `git commit` falha, e o sandbox vem sem.
6. **Auth GitLab por HTTPS** via `glab auth git-credential` como credential
   helper.
7. **Roteador de modelos** (`~/.local/bin/claude-model-router`), iniciado pelo
   entrypoint `claude-routed`. Veja [Roteador de modelos](#roteador-de-modelos).
8. **Painel `/router`**, um mod do Claude Code em
   `~/.local/share/claude-router-view`, carregado com `--plugin-dir`.
9. **Escrita técnica:** as skills `asd-ste100` e `portugues-tecnico-simplificado`
   e a seção de escrita do `CLAUDE.md`. O idioma do Claude fica em `pt-BR`
   (`language` no `ecc.json`).

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
roteador de modelos. No fim, ele traz a seção "Technical Writing: ASD-STE100"
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

O kit traz o `claude-model-router` de [`model-router/`](../../../model-router/).
A cada mensagem sua, o Jev (TypeSafe) escolhe o modelo (Haiku, Sonnet ou Opus) e
o esforço (`low` a `max`). Com dúvida ou falha da TypeSafe, o roteador usa opus e
`high`.

```
claude -> claude-model-router (127.0.0.1:8788) -> proxy do sbx -> api.anthropic.com
                       \-> proxy do sbx -> api.typesafe.ai (Jev)
```

O entrypoint do sandbox é `~/.local/bin/claude-routed`, e não o `claude`:

1. Se `model_router=on` e `TYPESAFE_API_KEY` existe, o script sobe o roteador.
2. O script espera até 15 s por `GET /_router/health`.
3. Se o roteador responde, o script define `ANTHROPIC_BASE_URL` e roda o Claude.
4. Se algo falha, o script avisa em stderr e roda o Claude direto. O roteador
   nunca impede a sessão de subir.

Diferenças em relação ao host:

- O sandbox não tem headroom. O Claude fala direto com o roteador.
- O sandbox não tem journald. O roteador grava o log em
  `~/.local/state/claude-model-router/router.log` (`ROUTER_LOG_FILE`), e o
  `--stats` lê esse arquivo. A pasta tem permissão 700 e o arquivo 600, porque o
  log guarda o começo de cada prompt. Erros de inicialização vão para
  `router.err`, na mesma pasta.
- O roteador manda as requisições pelo proxy do sandbox (`HTTPS_PROXY`). O proxy
  troca o placeholder de `TYPESAFE_API_KEY` pela chave real.
- O `setup.install` roda o `--selftest` do roteador. Isso baixa o `aiohttp` do
  PyPI para o cache do `uv`, e por isso `pypi.org` e `files.pythonhosted.org`
  estão liberados na rede. As versões e os hashes vêm do lockfile
  `claude-model-router.lock`, e o `uv run --locked` recusa qualquer diferença.

O script e o lockfile do kit são cópias dos de `model-router/`. Se você mudar o
script, rode `uv lock --script claude-model-router`, copie os dois arquivos para
`files/home/.local/bin/` e confira com `cmp`.

## Painel /router

O mod `router-view` de [`model-router/router-view/`](../../../model-router/router-view/)
fica em `~/.local/share/claude-router-view` e entra pelo `--plugin-dir` no
`sandbox.command`. O comando `/router` abre o painel. Ele mostra os agentes
ativos e as estatísticas do dia, lidas do `claude-model-router --stats-json`.

O Claude Code da imagem (2.1.280) só carrega mods com painel quando
`CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`. O kit define essa variável. O kit leva só
os arquivos que rodam (manifesto, `hooks.json`, `register.tsx` e `view.ts`). Os
testes ficam no repositório.

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

## Rede

```yaml
allow:
  - "github.com:443"           # clone do ECC
  - "gitlab.com:443"           # release do glab
  - "gitlab.example.com:443"  # GitLab de trabalho (arg gitlab_host)
  - "api.typesafe.ai:443"     # Jev (roteador de modelos)
  - "pypi.org:443"            # aiohttp do roteador, no setup.install
  - "files.pythonhosted.org:443"
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

- **Entrypoint próprio para o roteador, não `setup.startup`.** O `startup` não
  segura o entrypoint, então o Claude poderia subir antes do roteador e falhar
  na primeira requisição. O `claude-routed` espera o roteador responder e, se
  ele não responde, roda o Claude sem roteador.

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

Roteador e painel, sandbox criado do zero com `sbx v0.46.0` (Claude Code
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
- `claude --plugin-dir ... -p "/router"` responde `Model router pane opened.`;
- o `policy log` só mostra liberados `api.anthropic.com`, `api.typesafe.ai` e
  `files.pythonhosted.org` para o roteador.

## Limitações

- **Agentes perdem o prefixo `ecc:`.** Instalados como agentes de usuário
  (`~/.claude/agents/`), chamam-se `planner`, `code-reviewer`, `tdd-guide` — não
  `ecc:planner`. Regras que assumem o namespace do plugin não valem aqui.
- **156 skills, não 50.** A baseline do instalador entra junto; cortar mais
  exige `--without`.
- Dependências npm do ECC (`ajv`, `sql.js`, `@iarna/toml`) não são instaladas —
  os hooks só usam módulos nativos do Node. Para `ecc status`/`doctor`/`memory`:
  `cd /home/agent/.ecc/ECC && npm ci --omit=dev` (exige `registry.npmjs.org:443`).
- `setup.install` roda a cada criação e não é cacheado. Para eliminar o custo,
  asse clone + install numa imagem de template (`sbx template`).
- O kit replica só parte da config pessoal do host: a seção de escrita do
  `CLAUDE.md`, as duas skills de escrita e o `language`. Settings, MCP e
  plugins ficam de fora. Para isso existe `~/.claude/sbx-sync-config.sh`, que
  gera `claude-ecc:latest`.
- **Jev com a chave real não foi testado no sandbox.** O teste usou uma chave
  falsa. A troca do placeholder pelo proxy é o mesmo mecanismo do
  `GITLAB_TOKEN`, que foi verificado.
- **O painel não foi visto na tela do sandbox.** O mod carrega e o `/router`
  responde em modo `-p`, mas o desenho do painel só foi visto no host.
- Os mods com painel são early access no Claude Code 2.1.280. Uma versão nova da
  imagem pode mudar a API ou dispensar `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`.

## Referências

- Exemplos oficiais: <https://github.com/docker/sbx-kits-contrib> — vale ler
  `ecc/` (instalação sem hooks), `gitlab/` (limitação do inject duplo) e
  `gitlab-ssh/` (host keys pinados).
