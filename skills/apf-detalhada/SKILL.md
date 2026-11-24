---
name: apf-detalhada
description: "Use when the user asks for an APF / Análise de Pontos de Função / contagem de pontos de função detalhada (IFPUG, guia FATTO) of a system from its source code, DER (entity-relationship model) and screens (prints or wireframes), or wants the result as the SIGEPEN-style count spreadsheet (Contagem, Funções, Sumário) with traceability sheets."
metadata:
  version: "1.0.0"
  source: "Guia Prático em APF (Lopes & Braga, 2011 — fattocs.com) + planilhas de referência do usuário"
---

# APF detalhada (guia FATTO / IFPUG)

Conta o tamanho funcional de um sistema e entrega a planilha no formato do modelo de saída
(`assets/modelo-saida.xlsx`), com a rastreabilidade de cada TD, TR e AR até a fonte.

Base metodológica: os 6 passos do guia FATTO, com tabelas IFPUG. Detalhes em
`references/metodo-fatto.md`. Para extrair funções de código, DER e telas, siga
`references/extracao-das-fontes.md`. O formato de entrada do gerador está em
`references/formato-json.md`.

## 0. Entradas obrigatórias: código, DER e telas

A contagem detalhada só é feita com as **três** fontes:

| Fonte | Para quê | Formas aceitas |
|---|---|---|
| Código-fonte | processos elementares, AR lidos e mantidos, campos de entrada e saída, cálculos | repositório local, caminho de pasta |
| DER | ALI/AIE, TD e TR das funções de dados | imagem do diagrama, DDL/migrations/models ORM, banco acessível (MCP `pg`) |
| Telas | o que o usuário reconhece: campos, botões, mensagens, relatórios | prints, wireframes, protótipo, sistema rodando |

Se faltar alguma, **pergunte antes de contar**. Só siga sem ela se o usuário autorizar
explicitamente. Nesse caso, registre a lacuna na aba Revisão e trate como "A apurar" as
funções que dependem dela. Nunca invente TD ou AR para tapar uma lacuna.

Pergunte também, se não estiver claro: tipo de contagem (desenvolvimento, melhoria ou
aplicação), fronteira, órgão, contador, R$/PF (opcional) e deflatores (opcional).

## 1. Tipo de contagem (FATTO 2.2)

- **Desenvolvimento**: tudo que será entregue até a instalação, incluindo as funções de
  conversão (operação `T`). `DFP = (UFP + CFP) × VAF`.
- **Melhoria**: funções incluídas (`I`), alteradas (`A`) e excluídas (`E`). Exige baseline
  ou diff antes/depois. Sem isso, não presuma I/A/E.
- **Aplicação (baseline)**: software instalado, sem conversão.

## 2. Escopo e fronteira (FATTO 2.3)

A fronteira é definida pelo **ponto de vista do usuário**, não pela tecnologia. Frontend,
API e app da mesma aplicação formam uma fronteira só e não geram contagem por canal. Dados
de outros sistemas que são apenas lidos viram AIE. Registre a fronteira em `contagem.escopo`.

## 3a. Funções de dados: ALI e AIE (a partir do DER)

Siga os passos do guia (2.4.4):
1. Monte o modelo lógico a partir do DER.
2. Tabelas reconhecidas pelo negócio viram arquivo lógico: **ALI** se a aplicação mantém
   (existe EE/SE que grava nela), **AIE** se é mantida por outra aplicação e só lida.
3. Tabelas que o negócio não reconhece:
   - se os **campos** são reconhecidos → a tabela vira **TR** de cada arquivo lógico
     relacionado, e os campos somam TD a cada um deles (ex.: tabela associativa com data
     ou hora, especialização);
   - se nem a tabela nem os campos são reconhecidos → descarte.
4. Não são arquivos lógicos: tabelas temporárias, de backup, views, cache, sessão, filas,
   logs técnicos e tabelas de controle de framework (migrations, jobs).
5. **TD** é um campo único, não recursivo e reconhecido pelo usuário. Colunas técnicas (id
   surrogate, timestamps de auditoria técnica, version, flags internas) ficam em
   `colunas_excluidas`, a menos que o usuário as veja e use.
6. **TR**: o próprio arquivo conta 1, mais 1 por subgrupo (especialização, entidade
   dependente, associativa com atributos).

## 3b. Funções de transação: EE, SE e CE (código + telas)

1. Liste os **processos elementares**: a menor atividade completa e com significado para o
   usuário. Cada ação de tela (Salvar, Excluir, Pesquisar, Gerar relatório, Exportar) é
   cruzada com a rota, o controller ou o service correspondente. A mesma lógica em canais
   diferentes conta uma vez só.
2. Classifique pela **intenção principal**:
   - **EE**: mantém ALI (incluir, alterar ou excluir) ou altera o comportamento do sistema.
     Um cadastro que mostra dados ao final continua EE.
   - **SE**: apresenta informação com cálculo, fórmula, dado derivado ou totalização, ou,
     ao apresentar, mantém ALI ou altera comportamento.
   - **CE**: apresenta por recuperação simples, sem cálculo e sem manter ALI.
   - Não são processos: telas de filtro isoladas, preenchimento de campos, menus,
     navegação, health check, paginação e etapas internas de um mesmo processo.
3. **TD da transação**: campos que cruzam a fronteira (entram ou saem) e são reconhecidos
   pelo usuário, contados uma vez cada, mais **1 pela ação** (botão ou comando) e **1 pelas
   mensagens** (erro ou confirmação), quando existirem. Uma coluna repetida em lista conta
   uma vez. Tokens, paginação e campos de transporte vão para `campos_excluidos`.
4. **AR**: arquivos lógicos (ALI/AIE) lidos ou mantidos, cada um contado uma vez. TR não é
   AR, e várias tabelas do mesmo arquivo lógico contam como 1 AR. Leituras de validação
   (ex.: checar se um cliente existe) também contam.

Quando uma função não puder ser classificada, provavelmente ainda não é um processo
elementar: decomponha antes de classificar (guia FATTO 2.5.5).

## 4–6. Complexidade, PF não ajustados, VAF e total

- A complexidade e a contribuição saem das matrizes IFPUG (ver `references/metodo-fatto.md`).
  O script e as fórmulas da planilha já as aplicam; não calcule à mão.
- `UFP` = soma das contribuições de dados e de transações.
- **VAF = 1**: o guia não aplica fator de ajuste (opcional no IFPUG desde 2002). Só use
  outro valor se o usuário pedir.
- Esforço, custo e prazo (guia, cap. 3) só entram com produtividade (h/PF) e custo (R$/PF)
  informados pelo usuário. Nunca use valores de exemplo.

## 7. Gerar a planilha

1. Monte o JSON (`references/formato-json.md`; exemplo completo em
   `examples/locadora-fatto.json`). Cada função precisa de `id`, `fontes` e as listas
   (`td_lista`, `tr_lista` ou `ar_lista`) que justificam os números.
2. Rode, com openpyxl disponível (use um venv se o Python do sistema não tiver):
   ```bash
   python3 <skill>/scripts/gerar_planilha.py contagem.json "Contagem APF - <Sistema>.xlsx" --recalcular
   ```
   O script valida a entrada (erros bloqueiam a geração) e preenche Contagem, Funções e
   Sumário com as fórmulas do modelo. Ele acrescenta as abas **Memória TD**, **Evidências**,
   **Revisão** e **Regras**, imprime o sumário por tipo e complexidade e, com
   `--recalcular`, confere no LibreOffice se as fórmulas dão o mesmo total.
3. Funções com `td` ou `ar_tr` nulo vão para a Revisão como **A apurar**. Elas não recebem
   PF e não aparecem em Funções.
4. Leia os `AVISO:` e corrija ou justifique cada um. Os mais comuns: ALI sem EE que o
   mantenha (talvez seja AIE), AIE nunca lido, CE com cálculo (deveria ser SE) e AR que não
   está declarado como ALI/AIE.

## 8. Entrega

Informe ao usuário:
- o total de PF e a tabela por tipo e complexidade (saída do script);
- quantas funções ficaram **A apurar** e por quê;
- as premissas que mudam o total (agrupamento de arquivos lógicos, login, tabelas de
  domínio, CE × SE);
- o caminho da planilha.

O resultado é uma **proposta técnica** até ser validado pelo responsável funcional. Diga
isso explicitamente e não chame a proposta de contagem aceita.

## Armadilhas

- Uma tabela física não é automaticamente um ALI, e uma coluna física não é
  automaticamente um TD. A visão do negócio manda.
- Uma rota ou um endpoint não é uma função. GET de detalhe usado só para preencher o
  formulário de edição faz parte da EE "Alterar", não é uma CE própria.
- Consultas que diferem só na ordenação ou no layout são o mesmo processo.
- Branches e variações de código são evidência, não somam funções.
- O guia FATTO classifica "Login (com criptografia)" como SE. Mantenha essa classificação,
  mas registre-a na Revisão como premissa a confirmar com o contratante.
