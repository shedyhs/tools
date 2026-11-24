# Método — Guia Prático em APF (Lopes & Braga, 2011, FATTO)

Fonte: https://www.fattocs.com/wp-content/uploads/2020/04/JhoneySLopes-JoseLBraga-2011.pdf
Resumo em palavras próprias. Tabelas = padrão IFPUG reproduzido no guia.

## Os 6 passos
1. Determinar o tipo de contagem — desenvolvimento, melhoria, aplicação.
2. Identificar escopo da contagem e fronteira da aplicação (visão do usuário).
3. Contar funções: (a) tipo dado — ALI/AIE; (b) tipo transação — EE/SE/CE.
4. Pontos de função não ajustados = Σ contribuições de dados + transações.
5. Fator de ajuste (VAF) — o guia adota VAF = 1 (subjetivo, ±35%, opcional no IFPUG desde 2002).
6. Pontos ajustados. Desenvolvimento: `DFP = (UFP + CFP) × VAF` (CFP = conversão).

"Usuário" em APF = qualquer entidade que interage com o sistema ou lhe impõe ônus
(pessoa, outra aplicação, lei, restrição).

## Tipos de contagem
- Desenvolvimento: tudo até a instalação, inclusive funções de conversão (carga inicial
  de dados vinda de outro sistema, executada uma vez).
- Melhoria: funções novas, alteradas e excluídas; ao final recontar a aplicação.
- Aplicação: software instalado; não conta conversão.

## Funções de dados
- **ALI**: grupo lógico de dados persistentes, mantido dentro da fronteira por processos
  elementares. Ex.: tabelas ou grupos de tabelas mantidos; arquivos de configuração/segurança
  mantidos pela aplicação. Não são: arquivos/tabelas temporários, backup, views.
- **AIE**: grupo lógico mantido por outra aplicação e referenciado pela contada. Dados da
  aplicação contada lidos por outra são ALI aqui (e AIE lá), não AIE.
- Um grupo de tabelas pode ser um único arquivo lógico.
- **TD**: campo único, não recursivo, reconhecido pelo usuário.
- **TR**: subgrupo de dados. Todo arquivo lógico é TR de si mesmo. Tabelas agrupadas no
  arquivo viram TR e seus TD somam ao arquivo (ex.: Funcionário com especializações
  Auxiliar e Dentista → 1 ALI, 3 TR).
- Fluxo prático: modelo lógico → tabelas da visão do negócio = ALI/AIE → demais tabelas:
  campos reconhecidos ⇒ TR + TD em cada arquivo relacionado; nada reconhecido ⇒ descartar.

### Complexidade ALI/AIE
| TR \ TD | 1–19 | 20–50 | 51+ |
|---|---|---|---|
| 1 | Baixa | Baixa | Média |
| 2–5 | Baixa | Média | Alta |
| 6+ | Média | Alta | Alta |

### Contribuição
| Tipo | Baixa | Média | Alta |
|---|---|---|---|
| ALI | 7 | 10 | 15 |
| AIE | 5 | 7 | 10 |

## Funções de transação
Processo elementar = menor unidade de atividade significativa e independente para o
usuário. "Consultar clientes" é uma função; "consultar clientes por nome" e "consultar
clientes em débito" são processos elementares distintos. Consultas que só mudam a
organização/ordenação dos dados não são distintas.

- **EE** — intenção principal: manter um ou mais ALI e/ou alterar o comportamento do
  sistema. Não são EE: telas de filtro, preenchimento de campos, login, relatórios.
- **SE** — apresentar informação com lógica além da simples recuperação (cálculo,
  fórmula); pode manter ALI e alterar comportamento. Ex. do guia: login com criptografia,
  relatórios financeiros calculados, consultas e gráficos com cálculo.
- **CE** — apresentar por recuperação simples de ALI/AIE, sem cálculo, sem alterar
  comportamento. Ex.: consultar clientes por nome; gráfico de recuperação simples.
- A finalidade decide: cadastro que exibe dados ao final continua EE.
- Se não classifica, ainda não é processo elementar — decompor.

- **TD (transação)**: cada campo preenchido ou apresentado, reconhecido pelo usuário;
  o botão de confirmação e a janela de mensagem também contam. Num relatório/gráfico,
  cada informação apresentada (ex.: produto, quantidade, valor = 3 TD).
- **AR**: cada arquivo lógico lido (ALI/AIE) ou mantido (só ALI). TR não é AR. Arquivo
  lido várias vezes conta uma.
- Dica do guia: precisão de TD/AR importa perto das fronteiras de faixa; longe delas, erros
  pequenos não mudam a complexidade.

### Complexidade EE
| AR \ TD | 1–4 | 5–15 | 16+ |
|---|---|---|---|
| 0–1 | Baixa | Baixa | Média |
| 2 | Baixa | Média | Alta |
| 3+ | Média | Alta | Alta |

### Complexidade SE e CE
| AR \ TD | 1–5 | 6–19 | 20+ |
|---|---|---|---|
| 0–1 | Baixa | Baixa | Média |
| 2–3 | Baixa | Média | Alta |
| 4+ | Média | Alta | Alta |

### Contribuição
| Tipo | Baixa | Média | Alta |
|---|---|---|---|
| EE | 3 | 4 | 6 |
| SE | 4 | 5 | 7 |
| CE | 3 | 4 | 6 |

## Derivações (cap. 3) — só com dados do usuário
- Esforço = PF × (h/PF da equipe). Tabelas de edital são referência arriscada.
- Custo = PF × (R$/h × h/PF) — ou PF × R$/PF.
- Prazo = Esforço / recursos (não é linear; usar histórico).

## Exemplo de regressão (locadora)
3 ALI Baixa (21 PF) + 18 transações (57 PF) = **78 PF**; ver `examples/locadora-fatto.json`.
Observação: o guia tem uma inconsistência — "Consulta clientes com carro alugado" aparece com
TD 3 na tab. 2.14 e TD 6 na tab. 2.15; o total de 78 usa TD 6 (Média).
