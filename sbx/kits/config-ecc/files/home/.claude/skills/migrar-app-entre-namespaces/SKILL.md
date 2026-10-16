---
name: migrar-app-entre-namespaces
description: "Use when mover uma aplicação entre namespaces no cluster RKE2 PMMT (repo k8s-manifests, ArgoCD + Kustomize + External Secrets) — cobre overlay, Application, secrets namespaced, bridge de Ingress, NetworkPolicy do destino e ordem do rollout"
metadata:
  origin: auto-extracted
---

# Migrar app entre namespaces (k8s-manifests / RKE2 PMMT)

**Extraído:** 2026-09-16
**Validado em:** `<app>=portal-policial` (front + api), `<ns-origem>=default` →
`<ns-destino>=dev`, `<env>=dev` — MR !185

## Convenção de placeholders

| Placeholder | Significado | Exemplo validado |
|---|---|---|
| `<app>` | nome do app, igual ao diretório em `apps/` | `portal-policial-api` |
| `<env>` | overlay de ambiente | `dev`, `hml` |
| `<ns-origem>` / `<ns-destino>` | namespaces | `default` → `dev` |
| `<svc>` | Service renderizado (com `nameSuffix`) | `portal-policial-api-service-dev` |
| `<ingress-compartilhado>` | Ingress multi-app do `<ns-origem>` | `borda-apis-fronts-parque-50` |
| `<host-publico>` | host com `server` próprio no nginx | `desenvolvimento.pm.mt.gov.br` |
| `<ip-ingress>` | IP onde o ingress controller atende | `172.16.93.50` |
| `<projeto-infisical>` | projeto no Infisical | `portal-policial-f4ew` |

Trocar todos antes de executar. Nada aqui é específico de um ambiente — a mesma
sequência vale para `hml` e para os outros parques.

## Problema

Mudar de namespace no Kubernetes é sempre delete+create, nunca in-place. Quatro
coisas quebram juntas e nenhuma avisa antes:

1. **Ingress não cruza namespace.** Se `<svc>` sai do `<ns-origem>`, toda regra
   do `<ingress-compartilhado>` que o referencia passa a 503.
2. **SecretStore e ExternalSecret são namespaced** — e autenticam por um Secret
   de bootstrap que **não está no GitOps**.
3. **`prune: true`** nas Applications apaga o objeto antigo sozinho no primeiro
   sync. Não existe janela para preparar nada depois do merge.
4. **NetworkPolicy do `<ns-destino>`** pode bloquear o app — ou salvá-lo.

## 1. Reconhecimento (antes de planejar)

```bash
git fetch && git status -sb                      # o clone local costuma estar MUITO atrás
kubectl kustomize apps/<app>/overlays/<env>      # o que REALMENTE renderiza
```

**Não acredite em comentário de overlay.** É comum haver `patches` com
`target: kind: Ingress` que são no-op: se a base só tem Deployment + Service, o
target não casa com nada e o kustomize ignora em silêncio — enquanto o comentário
acima afirma que o patch reescreve a referência. Confirme pelo render, não pelo texto.

NetworkPolicy do destino:

```bash
kubectl get netpol -n <ns-destino> -o yaml
```

- `policyTypes: [Ingress]` apenas → egress do pod segue livre (banco, APIs externas).
- Se houver `Egress` → **o plano muda**: a migração pode trocar um problema por outro.

**AppProject da Application que vai carregar o bridge** — a checagem que falta na
primeira vez e custa a janela inteira:

```bash
kubectl get application <app-da-ponte> -n argocd -o jsonpath='{.spec.project}'
kubectl get appproject <project> -n argocd -o jsonpath='{.spec.namespaceResourceWhitelist}'
```

Projects de ponte costumam ter whitelist **por kind**, não wildcard. Se `Service`
não estiver lá, o sync falha com `resource :Service is not permitted in project
<project>` — e o ArgoCD **aborta a operação inteira**: o Ingress também deixa de
ser aplicado. Combinado com o prune que já removeu os objetos antigos, isso é
rota fora do ar até alguém perceber. Conferir ANTES, junto com a NetworkPolicy.

## 2. As cinco mudanças

| # | Arquivo | Mudança |
|---|---|---|
| 1 | `apps/<app>/overlays/<env>/kustomization.yaml` | `namespace: <ns-destino>` |
| 2 | `infrastructure/argocd-apps/<app>-<env>-app.yaml` | `destination.namespace: <ns-destino>` |
| 3 | `infrastructure/secrets/{<ns-origem> → <ns-destino>}/` | mover SecretStore + ExternalSecret |
| 4 | `infrastructure/borda/.../<app>-bridge-services.yaml` | **novo**: Service ExternalName |
| 5 | `<ingress-compartilhado>` | trocar `backend.service.name` para o bridge |

App gerado por **ApplicationSet** não tem o item 2 — o `destination.namespace` é
fixo no template. Funciona mesmo assim: o kustomize carimba `namespace:` em cada
objeto e o ArgoCD aplica onde o manifesto manda. Confira a lista de `exclude` do
AppSet para saber em qual caso o `<app>` cai; quem está no `exclude` tem
Application dedicada em `infrastructure/argocd-apps/`.

### Secrets: mover, mas cuidado com store compartilhado

Um SecretStore usado por mais de um app deve ser **copiado**, não movido — o grep
cobre o repositório, não o cluster, e há objetos vivos fora do GitOps. Um
SecretStore ocioso não custa nada; remover só depois de confirmar no cluster que
ninguém mais o referencia.

## 3. O bridge ExternalName

```yaml
apiVersion: v1
kind: Service
metadata:
  name: <app>-<env>-bridge        # NOME DIFERENTE de <svc>
  namespace: <ns-origem>          # o ns do Ingress, não o do app
spec:
  type: ExternalName
  externalName: <svc>.<ns-destino>.svc.cluster.local
  ports:
    - port: 80
      targetPort: 80
      protocol: TCP
```

Evita fatiar o `<ingress-compartilhado>` (dezenas de regras) e evita o admission
webhook do ingress-nginx, que bloqueia `host`+`path` duplicado enquanto o Ingress
antigo existir.

**Nome diferente, obrigatoriamente.** Se o bridge tiver o mesmo nome de `<svc>`,
o `prune` da Application do `<app>` deleta o bridge junto — as duas Applications
brigam pelo mesmo objeto.

**Bridge e Ingress na mesma Application**, de propósito: entram no mesmo sync, sem
janela em que a regra aponte para nome inexistente.

## 4. Quantas linhas trocar no Ingress — e por quê

Conte antes e depois:

```bash
grep -c 'name: <svc>' <arquivo-do-ingress>
```

O `<ingress-compartilhado>` pode declarar o mesmo path mais de uma vez, em `rules`
distintas: uma com `host: <host-publico>` e outra **sem host**. Trocar só uma
metade quebra um dos caminhos.

**A regra sem host não é "o acesso por nip.io".** Ela atende qualquer Host que não
tenha `server` próprio no nginx — na prática, o IP puro. Um host como
`<algo>.<ip-ingress>.nip.io` costuma ter bloco dedicado, declarado por **outro**
app, e por isso devolve 404 para rotas que não estejam naquele Ingress. Verifique,
não deduza:

```bash
for h in <host-publico> <ip-ingress> <algo>.<ip-ingress>.nip.io; do
  printf "%-40s " "$h"
  curl -s -o /dev/null -m 8 -w "%{http_code}\n" -H "Host: $h" "http://<ip-ingress><path>"
done
```

## 5. O secret de bootstrap (o passo que ninguém lembra)

Os SecretStores autenticam por um Secret comum no mesmo namespace
(`infisical-universal-auth-<projeto>`). Ele **não tem manifesto** — sem ele o
ExternalSecret não autentica, o pod sobe sem env e cai em CrashLoopBackOff.

Copiar preservando só o essencial. Não use `sed` para limpar o `metadata`: ao
remover a chave da annotation ele deixa o valor órfão e o YAML fica inválido.

```bash
kubectl get secret <nome> -n <ns-origem> -o json | python3 -c "
import json,sys
s=json.load(sys.stdin)
s['metadata']={'name':s['metadata']['name'],'namespace':'<ns-destino>',
  'annotations':{'pm.mt.gov.br/origem':'copia de ns <ns-origem> em <data> (MR !<n>)',
                 'pm.mt.gov.br/fora-do-gitops':'credencial de bootstrap; sem manifesto no k8s-manifests'}}
print(json.dumps(s))" | kubectl apply -n <ns-destino> --dry-run=server -f -
```

Rodar com `--dry-run=server` primeiro; repetir sem a flag para valer. Validar
comparando o hash nos dois namespaces:

```bash
for ns in <ns-origem> <ns-destino>; do
  kubectl get secret <nome> -n $ns -o jsonpath='{.data}' | sha256sum; done
```

Depois do apply, remova a annotation automática que duplica a credencial:

```bash
kubectl annotate secret <nome> -n <ns-destino> kubectl.kubernetes.io/last-applied-configuration-
```

**Sempre carimbe a procedência.** Objeto vivo sem manifesto é mudo: dá para ver
que existe, nunca por quê. Uma NetworkPolicy aplicada à mão, sem autor nem
intenção registrada, já custou ~39h de investigação neste cluster.

## 6. Ordem do rollout

1. Criar o secret de bootstrap no `<ns-destino>`
2. Verificar a NetworkPolicy do `<ns-destino>`
3. Merge na `main`
4. Sincronizar **na mesma janela** as Applications de sync manual (`secrets` e a
   da borda). **Não depois** — sincronizar tarde já custou ~8 min de 503 num
   renome anterior

Haverá indisponibilidade curta entre o prune dos objetos antigos e os pods novos
ficarem Ready. Combine a janela antes.

## Acesso ao cluster

A workstation pode não ter kubeconfig. Pelo nó (credenciais em
`servidor/secrets.txt` — **nunca** cole a senha em mensagem, commit ou MR):

```bash
ssh -p <porta> root@<ip-no>
export KUBECONFIG=/etc/rancher/rke2/rke2.yaml   # sem isso: "connection refused" na 8080
/var/lib/rancher/rke2/bin/kubectl ...           # não está no PATH
```

## Validação antes do push

```bash
for d in <diretórios tocados>; do kubectl kustomize "$d" >/dev/null && echo "OK $d"; done
kubectl kustomize apps/<app>/overlays/<env> | grep -E '^kind:|namespace:'
```

Confirmar: todo objeto do app com `namespace: <ns-destino>`; bridge e Ingress
ainda em `<ns-origem>`; um SecretStore de cada nome por namespace.

## When to Use

- Mover qualquer app entre namespaces neste cluster
- Separar um namespace compartilhado por ambiente ou por domínio
- Sintoma de timeout entre pods de namespaces diferentes: DNS resolve mas
  `connect` estoura → suspeite de NetworkPolicy antes de suspeitar do código
