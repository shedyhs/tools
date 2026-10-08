# Skill Português Técnico Simplificado: o STE100 para a saída de agentes em português

Esta é uma skill do Claude Code que reescreve um português denso e ambíguo. Ela usa as regras do [ASD-STE100 Simplified Technical English](https://www.asd-ste100.org/) (STE), adaptadas ao português do Brasil. O STE é uma norma de linguagem controlada da indústria aeroespacial e de defesa. Ela existe para que ninguém leia errado as instruções de manutenção de aeronaves.

Esta skill usa a mesma disciplina para outro leitor: um **agente de IA**. Esse agente interpreta a saída de outro agente, a descrição de uma ferramenta, uma mensagem de erro ou uma instrução entre agentes. Não há um humano para resolver ambiguidades.

Esta skill é uma adaptação da skill [asd-ste100](https://github.com/danyuchn/asd-ste100-skill), que faz o mesmo trabalho para o inglês.

## Por que o STE, e por que para agentes

O STE existe porque uma instrução mal lida numa aeronave pode matar pessoas. Os leitores da norma muitas vezes não falavam inglês como língua materna e não tinham um autor para pedir esclarecimentos. A solução da norma: um significado por palavra, voz ativa, tempos simples, uma instrução por frase, frases curtas e nenhuma palavra omitida.

Um agente que interpreta a saída de outro agente está numa posição muito parecida. Ele não tem canal de volta nem como perguntar "você quis dizer X ou Y?". As regras que impedem um mecânico de ler errado uma especificação de torque também protegem um agente. Com elas, o agente não lê errado a descrição de uma ferramenta ou uma mensagem entre agentes.

## Por que uma versão em português

Não existe norma de linguagem controlada para o português. O STE é só para o inglês, e uma tradução direta das regras não funciona. O português não tem a partícula dos phrasal verbs ("take off"). Mas ele tem locuções verbais cujo sentido não vem das partes ("deixar de", "acabar com") e uma gíria técnica com o mesmo problema ("subir o servidor", "dar um push"). O pretérito perfeito composto ("tem falhado") tem outro sentido que o present perfect do inglês. O português separa também a essência ("ser") do estado ("estar"), e o inglês não separa.

O português tem ainda fontes de ambiguidade que o inglês não tem. Exemplos: o "dever" (ordem ou estimativa?), o "seu" com dois donos possíveis, o sujeito oculto e o "excluir" (apagar ou deixar de fora?). Os números e as datas também mudam de leitura entre as duas línguas: "1.000" e "07/10".

Há também o traduzês. Os modelos de linguagem aprendem sobretudo com texto em inglês. O português que eles escrevem traz decalques: "eventualmente" no sentido de "por fim", "endereçar o problema", "suportar o formato". Outros sinais do traduzês são o gerundismo e "o mesmo" no lugar de pronome. Esta skill trata esses casos como regras próprias.

O Brasil tem normas de linguagem simples (a Lei nº 15.263/2025 e a ABNT NBR ISO 24495-1). Elas escrevem para o cidadão diante de um texto da administração pública. Esta skill escreve para leitores técnicos e para máquinas e não tira regras dessas normas. A referência de língua é a norma culta: o Acordo Ortográfico e o VOLP.

## Antes e depois

| Antes | Depois |
|---|---|
| "Esta ferramenta irá tentar realizar a sincronização do estado entre os diversos backends que foram configurados, e caso um conflito seja detectado ela poderá resolvê-lo automaticamente dependendo da estratégia que tiver sido definida, ou caso contrário irá apresentar o conflito para revisão manual." | "A ferramenta tenta sincronizar o estado entre os backends configurados. Se encontrar um conflito, a ferramenta lê a estratégia configurada. Se a estratégia permitir resolução automática, a ferramenta pode resolver o conflito automaticamente. Se a ferramenta não resolver o conflito, ela encaminha o conflito para revisão manual." |
| "Um erro pode ter ocorrido durante o processamento da sua requisição devido a uma possível incompatibilidade no formato de dados esperado, o que poderia ser causado por uma versão desatualizada do cliente." | "Sua requisição pode ter falhado. A causa pode ser um formato de dados diferente do formato que o servidor espera. Uma versão desatualizada do cliente pode causar essa diferença." |

Há mais exemplos em [`examples/antes-depois.md`](examples/antes-depois.md), inclusive ilustrações das regras do STE e das regras que só o português tem.

## O que esta skill faz

1. Escolhe um modo. O modo **Estrito** cobre procedimentos, mensagens de erro e descrições de ferramentas. O modo **Flexível** cobre READMEs, descrições de pull request e prosa explicativa. O modo Flexível mantém a disciplina da frase, mas não o vocabulário fixo.
2. Lê o texto de entrada pelo sentido.
3. Marca cada violação, frase por frase. Exemplos: escolha ambígua de palavras, tempo composto, voz passiva com quem age indefinido, várias instruções numa frase, cadeias de "de", palavras omitidas, frases longas. Outros: verbo-suporte, gíria técnica, locuções verbais e prolixas, ponto e vírgula, ressalvas empilhadas, adjetivos de marketing, gerundismo e decalques do inglês. Por fim: "ser" no lugar de "estar", números e datas ambíguos e formas de gênero fora da norma.
4. Reescreve cada frase marcada, sem perder nenhum fato, condição ou limite de escopo do original. Se uma forma mais curta perderia uma precisão necessária, a skill mantém a forma longa e sinaliza a troca. Ela não simplifica em silêncio.
5. Entrega só o texto reescrito: sem preâmbulo, sem anúncio de modo, sem resumo das mudanças. Quando ela deixa algo sem simplificar de propósito, acrescenta uma linha `Mantido como está:`.

Peça o raciocínio ("mostre o diff", "quais regras ele quebrou") e a skill entrega uma tabela de antes e depois que nomeia cada regra.

As regras estruturais que a skill verifica são mecânicas: você aponta a palavra ou o sinal que quebra cada uma. As regras que dependeriam de um dicionário aprovado são só recomendações, porque não existe esse dicionário para o português. As regras que pedem bom gosto ficam com você.

## O linter

`scripts/pts-lint.py` é um linter determinístico que usa só a biblioteca padrão do Python. Ele verifica só padrões estruturais. Ele não compara um texto original com uma reescrita. Ele não verifica se a força de uma exigência continua a mesma e não prova que a reescrita preservou o sentido. Um resultado com zero violações quer dizer que as verificações estruturais configuradas não acharam problemas.

O linter verifica:

- **Achados obrigatórios** reprovam a execução. São eles: ponto e vírgula, frase longa, locução prolixa, verbo-suporte, gíria técnica e adjetivo de marketing. Também: gerundismo com verbo de ação pontual, data no formato dia/mês/ano, número com ponto de milhar e forma de gênero fora da norma. Por fim: a rotação de sinônimos (com as conjugações dos verbos) e a conjunção pendente no fim de item de lista.
- **Achados consultivos** nunca reprovam a execução. São eles: voz passiva, partícula "se", tempo composto, cadeia de "de", "o mesmo" como pronome, gerúndio depois de vírgula, decalque do inglês e travessão. Também: locução verbal idiomática, "excluir", "ser" no lugar de "estar", outros casos de gerundismo e data sem o ano. Por fim: número com três casas depois da vírgula.

O linter nunca marca ressalvas nem modalidade. "Pode ter falhado", "talvez tenha falhado" e "teria falhado" passam limpos, e o autoteste comprova isso. O linter também não verifica a ordem direta, o sujeito oculto, o "seu" ambíguo, o "dever" ambíguo nem a mistura de "tu" e "você". Essas regras precisam de leitura humana ou de um modelo.

O linter lê Markdown por parágrafo. Uma frase quebrada em várias linhas conta como uma frase, e o achado aponta para a primeira palavra dela. O linter ignora blocos de código, blocos de fórmula `$$`, comentários HTML, definições de link e front matter YAML. Código e fórmulas inline contam como uma palavra cada, e os destinos de link não contam. As colunas ficam exatas.

Um trecho entre aspas ("...", “...” ou «...») é uma menção: um exemplo, um rótulo ou uma citação. O linter conta o trecho como uma palavra e não analisa o conteúdo dele. `--ler-citacoes` desliga esse comportamento, por exemplo para analisar as mensagens de erro citadas num README.

Um exemplo que precisa falhar fica entre duas diretivas:

```markdown
<!-- pts-lint: deve-falhar frase-longa ponto-e-virgula -->
> Um texto ruim de propósito; com várias violações.
<!-- pts-lint: fim -->
```

Os achados dentro da região são esperados e saem do relatório. A região falha (`exemplo-sem-falha`) se não tiver um achado obrigatório ou se faltar uma das regras listadas. A lista de regras é opcional. Os blocos "Antes" de `examples/antes-depois.md` usam essas diretivas.

Em arquivos Rust (`*.rs`, ou `--linguagem rust`), o linter lê só a prosa, nunca o código. `--partes` escolhe a prosa (padrão `docs,comentarios`):

- `docs`: `///`, `//!`, `/** */` e `/*! */`, lidos como Markdown.
- `comentarios`: `//` e `/* */`.
- `mensagens`: literais de string dentro de `panic!`, `assert!`, `expect`, `println!` e chamadas parecidas. Mensagens são texto de erro, então usam o limite estrito de 22 palavras (`--max-palavras-estrito`).
- `literais`: todo literal de string com três palavras ou mais.

Outras opções:

- `--max-palavras N` define o limite de palavras por frase (padrão 27).
- `--resumo` imprime uma linha por arquivo, com o pior arquivo primeiro.
- `--ativar historico` acrescenta uma regra opcional que marca frases de changelog ("não mais", "anteriormente", "atualmente") em documentação do estado atual.
- `--linha-de-base N` tolera N violações obrigatórias.
- `--ajuda` mostra o uso completo.
- `--autoteste` roda os testes internos e analisa os documentos desta skill. Os documentos precisam passar, e o arquivo de casos-limite precisa falhar.

Uma opção desconhecida ou um nome de regra desconhecido em `--desativar` ou `--ativar` é erro (código 2). Um nome de opção do ste-lint, como `--baseline`, recebe a indicação do nome em português.

A regra de conjunção pendente lê os marcadores de lista comuns (`-`, `*`, `+`, `1.` e `1)`) com até três espaços antes. Ela não interpreta listas dentro de citações, continuação preguiçosa (lazy continuation) nem a semântica completa de listas aninhadas.

O arquivo `examples/casos-limite-do-linter.md` é inválido de propósito e mostra itens de lista incompletos. Rode `python scripts/pts-lint.py examples/casos-limite-do-linter.md` e veja que o linter informa os dois achados esperados. O arquivo é um caso de teste e não serve de exemplo de prosa conforme.

A skill **não** reproduz o dicionário oficial de cerca de 900 palavras do ASD. A norma é gratuita, mas a redistribuição não é livre. O Issue 9 permite a reprodução só com autorização escrita do ASD ou por oito categorias de organizações. Este projeto não pertence a nenhuma delas. Além disso, o dicionário é de palavras inglesas. Esta skill aplica o *princípio* do dicionário (a palavra mais simples, usada sempre do mesmo jeito), e não uma lista fixa de palavras.

O resumo completo das regras, a adaptação ao português e as citações estão em [`references/regras-de-redacao.md`](references/regras-de-redacao.md).

## Instalação

### Instalação rápida (npx skills)

Rode a [CLI skills](https://skills.sh/) na raiz do projeto:

```bash
npx skills add swfsql/portugues-tecnico-simplificado-skill
```

A CLI baixa a skill do GitHub e instala a skill em `.claude/skills/portugues-tecnico-simplificado`, só para o projeto atual. Com `-g`, a skill fica em `~/.claude/skills/` e vale para todos os projetos. A CLI envia dados anônimos de uso. `DISABLE_TELEMETRY=1` ou `DO_NOT_TRACK=1` desliga o envio. Atualize a skill com `npx skills update`.

### Clone

```bash
git clone https://github.com/swfsql/portugues-tecnico-simplificado-skill ~/.claude/skills/portugues-tecnico-simplificado
```

O clone deixa a skill disponível em todos os projetos do Claude Code. Para um projeto só, clone para `.claude/skills/portugues-tecnico-simplificado` dentro do projeto. Atualize a skill com `git pull`.

## Uso

Peça para simplificar ou esclarecer um texto em português:

```
Desambigue esta descrição de ferramenta
Reescreva esta mensagem de erro para que um agente não interprete errado
Aplique o português técnico simplificado a esta instrução
Tire o traduzês deste texto
```

Ou cole o texto e peça ao Claude para "desambiguar", "simplificar com o STE" ou "reduzir a ambiguidade desta saída".

Você recebe só o texto reescrito. Para ver quais regras a skill aplicou, acrescente "mostre o diff" ou "explique as mudanças" ao pedido.

## Escopo

Feita para: mensagens entre agentes, descrições de ferramentas e funções, mensagens de erro, prompts de sistema e instruções entre agentes. Vale para todo texto em português que uma máquina ou um leitor estrangeiro precisa interpretar sem um humano para consultar.

Não serve para: escrita criativa, textos de marketing ou qualquer texto em que a voz e a nuance são o objetivo. O STE é plano e literal de propósito.

Um limite que vale dizer logo: a skill corrige a forma de um texto, não a substância. Um parágrafo sem nada a dizer sai curto, limpo e ainda vazio.

## Fontes

- [Site oficial do ASD-STE100](https://www.asd-ste100.org/)
- [ASD-STE100: About STE](https://www.asd-ste100.org/about_STE.html)
- [ASD Europe: Simplified Technical English](https://www.asd-europe.org/standards-specifications/simplified-technical-english/)
- [Simplified Technical English na Wikipedia](https://en.wikipedia.org/wiki/Simplified_Technical_English)
- [TechScribe: ASD-STE100 Simplified Technical English](https://www.techscribe.co.uk/techw/asd-simplified-technical-english.htm)

As fontes de língua, números e datas (Acordo Ortográfico, VOLP, SI, ISO 8601) e a relação com as normas de linguagem simples estão em [`references/regras-de-redacao.md`](references/regras-de-redacao.md).

## Licença

MIT. Veja [LICENSE](LICENSE). O texto da licença fica em inglês, porque a licença MIT exige manter o aviso original sem alterações. O aviso de copyright do projeto original fica, e a adaptação acrescenta uma linha própria.
