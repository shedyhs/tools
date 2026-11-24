# Formato do JSON de entrada (`scripts/gerar_planilha.py`)

```jsonc
{
  "contagem": {
    "orgao": "Nome do órgão",          // cabeçalho A1 das abas
    "unidade": "Coordenadoria ...",     // cabeçalho A2
    "empresa": "SIGLA", "aplicacao": "Sistema", "projeto": "Projeto",
    "responsavel": "", "contado_por": "", "revisor": "",
    "tipo_contagem": "desenvolvimento", // desenvolvimento | melhoria | aplicacao
    "valor_pf": 0,                      // R$/PF — só se o usuário informar
    "deflatores": {"I": 1, "A": 1, "E": 1, "T": 1},  // opcional
    "data_criacao": "AAAA-MM-DD", "data_revisao": "",
    "proposito": "texto", "escopo": "fronteira e o que ficou fora"
  },
  "funcoes": [
    {
      "id": "CLI-01",                   // único; DAD-xx p/ dados, <MOD>-Txx p/ transações
      "nome": "Cliente",                // ALI/AIE: nome do arquivo lógico; transação: verbo + objeto
      "tipo": "ALI",                    // ALI | AIE | EE | SE | CE
      "operacao": "I",                  // I incluída | A alterada | E excluída | T conversão
      "grupo": "Cliente",               // obrigatório p/ transações → seção "FUNÇÃO CLIENTE"
      "td": 7,                          // inteiro ou null (= A apurar)
      "ar_tr": 2,                       // TR (dados) ou AR (transação); inteiro ou null
      "td_lista":  ["cpf", {"nome": "nome", "fonte": "src/models/cliente.py:12"}],
      "tr_lista":  ["Cliente", "Aluga"],                 // dados
      "ar_lista":  ["Cliente", "Carro"],                 // transações; nomes de ALI/AIE
      "mantem":    ["Cliente"],                          // EE/SE: ALI gravados
      "calculo":   false,                                // true ⇒ não pode ser CE
      "colunas_excluidas": ["id", "created_at"],         // dados: evidência que não soma
      "campos_excluidos":  ["page", "token"],            // transações
      "fontes": ["src/routes/clientes.py:40", "DER: tabela cliente", "print: tela-cliente.png"],
      "observacoes": "",                // vai para a coluna Observações (padrão: lista de AR/TR)
      "pendencia": ""                   // texto quando td/ar_tr = null
    }
  ],
  "evidencias": [
    {"tipo": "rota|tela|tabela|DER", "local": "POST /clientes", "operacao": "create_cliente",
     "funcao": "CLI-T01", "entradas": "cpf; nome", "saidas": "mensagem", "tabelas": "cliente",
     "tratamento": "Processo proposto | Técnica / sem soma isolada", "fonte": "src/...:40"}
  ],
  "revisao": [
    {"referencia": "CLI-T05", "situacao": "Pendente|Premissa|Reagrupada", "item": "...",
     "decisao": "o que precisa ser decidido/evidenciado", "fonte": "..."}
  ],
  "premissas": ["texto livre que vai para a aba Regras"]
}
```

Regras de validação (erros bloqueiam a geração):
- `id`, `nome`, `tipo` obrigatórios; `id` único; transação exige `grupo`.
- `td` ≥ 1, `ar_tr` ≥ 0 (ALI/AIE ≥ 1) ou `null`.
- Se `td_lista` existir, `len(td_lista) == td`; idem `tr_lista`/`ar_lista` com `ar_tr`.

Avisos (revisar e justificar): ALI sem `mantem`, AIE mantido ou nunca lido, CE com
`calculo` ou `mantem`, AR que não corresponde a ALI/AIE declarado, função sem `fontes`.
