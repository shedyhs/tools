# Ambiente: sandbox `config-ecc`

Você está num Docker Sandbox descartável, com permissões liberadas
(`bypassPermissions`). O workspace é um **bind mount read-write do host** — o que
você escreve lá persiste na máquina real. O resto do container é efêmero.

## ECC instalado de forma seletiva

Skills, agentes e comandos do ECC estão em `~/.claude/`. A lista curada de skills
vem de `~/.ecc-skills`; o clone do ECC fica em `~/.ecc/ECC` (tag e commit em
`~/.ecc/installed-ref`).

**Os agentes NÃO usam o prefixo `ecc:`** — aqui são agentes de usuário. Use
`planner`, `code-reviewer`, `tdd-guide`, `architect`, `build-error-resolver`,
`database-reviewer`, `doc-updater`, `e2e-runner`, `harness-optimizer`,
`loop-operator`, `python-reviewer`, `refactor-cleaner`.

Os hooks do ECC estão ativos (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`,
`SessionStart`, `SessionEnd`, `Stop`, `PreCompact`), carregados pela camada
`--settings` em `~/.config/claude/ecc.json`. O GateGuard pode exigir fatos antes
de comandos sensíveis — isso é esperado, não é bug. Para desligar, recrie o
sandbox com `--kit-arg gateguard=off` ou `--kit-arg disabled_hooks=<ids>`.

## Git e GitLab

`git` já tem identidade configurada — pode commitar direto.

`glab` está instalado e apontado para o GitLab de trabalho. A variável
`GITLAB_TOKEN` contém um **placeholder**, não o token real: o proxy do sandbox
substitui pelo valor verdadeiro nas requisições. Não tente ler, logar ou copiar
esse valor — ele não serve para nada fora daqui. Operações de git por HTTPS
autenticam pelo credential helper do glab.

## Rede

A saída é restrita a poucos domínios (GitHub, gitlab.com e o GitLab de trabalho).
Se um download falhar por rede, é política do sandbox, não falta de conectividade
— relate em vez de procurar contorno.
