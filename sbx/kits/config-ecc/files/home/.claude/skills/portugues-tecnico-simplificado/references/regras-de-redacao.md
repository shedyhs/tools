# Regras de redação: resumo, adaptação ao português e fontes

Este arquivo resume a descrição pública e oficial do ASD-STE100 (Simplified Technical English). Ele parafraseia as *categorias* de regras. Ele não reproduz o texto da norma nem o dicionário de cerca de 900 palavras. Para o documento oficial, peça o download gratuito no site oficial. O arquivo descreve também como esta skill adapta cada regra ao português do Brasil e quais referências ela usa.

## O que é o ASD-STE100

O ASD-STE100 é uma linguagem natural controlada. A primeira versão saiu em 1986, como o documento AECMA PSC-85-16598. A organização que publicou a norma hoje se chama ASD (AeroSpace and Defence Industries Association of Europe). As companhias aéreas europeias pediram a norma. Muitas das equipes delas não falavam inglês como língua materna e precisavam de uma documentação de manutenção que ninguém pudesse ler errado. Numa aeronave, uma instrução mal lida pode matar.

O Simplified Technical English Maintenance Group (STEMG) mantém a norma. O download é gratuito desde o Issue 6 (2013). A edição atual é o Issue 9 (janeiro de 2025).

## Estrutura

- **53 regras de redação em 9 seções**: escolha de palavras, gramática, estrutura da frase e estilo.
- **Um dicionário** de cerca de 900 palavras aprovadas, cada uma restrita a um significado e a uma classe gramatical. O dicionário lista também cerca de 1200 palavras a evitar, com substitutas sugeridas.
- **Uma permissão de terminologia**: uma organização pode definir um dicionário próprio de substantivos e verbos técnicos aprovados, além das 900 palavras de base. Esse dicionário próprio cobre o vocabulário de domínio que o dicionário-base não tem.

## Categorias de regras (paráfrase)

**Escolha de palavras**
- Use as palavras aprovadas só no significado e na classe gramatical aprovados.
- Cada palavra corresponde a um só significado. Não dependa do contexto para resolver uma palavra que tem vários sentidos no dicionário.
- Prefira a palavra mais simples, curta e comum a um sinônimo formal ou raro.
- Use um verbo aprovado para uma ação, não um substantivo derivado desse verbo (Regra 3.7).
- Não forme phrasal verbs, isto é, um verbo junto de uma preposição (Regra 9.3). As partes não permitem prever o sentido deles, e tanto leitores não nativos quanto sistemas de tradução erram com eles.

**Formas verbais**
- Formas permitidas: infinitivo, imperativo, presente simples, passado simples, futuro simples e particípio passado usado só como adjetivo.
- Sem present perfect, past perfect nem outras construções compostas ou com auxiliar. "We have received" não é permitido. "We received" é permitido.
- As formas em "-ing" são permitidas só como substantivo técnico ou como parte de um, não como forma verbal.

**Voz**
- A voz ativa é obrigatória em procedimentos e instruções.
- A voz passiva só é permitida em texto descritivo, e só quando quem age é de fato desconhecido ou irrelevante para o leitor.

**Estrutura da frase**
- Uma instrução por frase.
- No máximo cerca de 20 palavras por frase em procedimentos e instruções. No máximo cerca de 25 em texto descritivo.
- Não omita partes da frase (verbo, sujeito, artigo) só para encurtá-la. A norma avisa que essa omissão cria ambiguidade em vez de clareza.
- Grupos nominais (substantivos empilhados como modificadores) têm no máximo 3 palavras.
- O ponto e vírgula não é permitido (Regra 8.1): "You can use all standard English punctuation marks but not the semicolon (;)." Isto é, todos os sinais de pontuação padrão do inglês são permitidos, menos o ponto e vírgula. Escreva frases separadas. Todos os outros sinais continuam permitidos, inclusive o travessão.

**Estrutura do parágrafo e do documento**
- Um tópico por parágrafo.
- No máximo cerca de 6 frases por parágrafo.
- Use listas verticais (numeradas ou com marcadores) para sequências, condições ou enumerações complexas. Não esconda essas sequências na prosa.

**Instruções de segurança**
- Uma instrução crítica para a segurança começa com um comando ou uma condição clara. Ela não fica escondida no meio da frase.

## Adaptação ao português

O STE foi escrito para o inglês. Algumas regras passam direto para o português, outras mudam de forma. A tabela mostra como esta skill trata cada regra do STE.

| Regra do STE | No português | Por quê |
|---|---|---|
| Uma palavra, um significado | Igual. Sem dicionário aprovado, vale só a consistência dentro do documento. Evite também as palavras com dois sentidos no contexto, como "excluir". | Não existe dicionário controlado para o português. "Exclua o arquivo do pacote" pode ser apagar o arquivo ou deixar o arquivo de fora. |
| Verbo, não substantivo (3.7) | Igual, com foco no verbo-suporte: "realizar a análise", "efetuar o pagamento", "proceder à remoção", "fazer uso de". | O verbo-suporte é a forma mais comum de nominalização no português técnico e administrativo. |
| Sem phrasal verbs (9.3) | Vale para as locuções verbais idiomáticas ("deixar de", "acabar com", "dar conta de", "ficar de") e para a gíria técnica ("subir o servidor", "derrubar o serviço", "dar um push", "bater no endpoint"). | O português não tem a partícula do inglês ("take off"). Mas ele tem verbos com preposição ou com objeto fixo cujo sentido não vem das partes. "O job deixou de rodar" pode ser "parou de rodar" ou "não rodou desta vez". |
| Palavra mais simples | Sem locuções prolixas: "a fim de", "tendo em vista que", "no que diz respeito a", "sendo que", "encontra-se". | A locução prolixa usa várias palavras no lugar de uma e não acrescenta sentido. |
| Tempos simples | O pretérito perfeito simples cobre o present perfect. "Tem" + particípio indica repetição, não ação concluída. "Estar" + gerúndio fica nos relatórios de status. Sem gerundismo em ações pontuais. | O pretérito perfeito composto do português tem outro sentido. Traduzir o present perfect por ele muda a afirmação. |
| Formas em "-ing" | Gerúndio em "estar" + gerúndio e em ações simultâneas. Sem gerúndio depois de vírgula para ações em sequência ou para consequências. | A oração reduzida de gerúndio não diz a relação entre as duas ações. |
| Voz ativa | Igual. A regra inclui a passiva sintética ("Apaga-se o arquivo", "Recomenda-se", "Não se recomenda"). | A partícula "se" também esconde quem age. |
| Grupos nominais de até 3 palavras | No máximo dois "de" seguidos. | O português não empilha substantivos. O equivalente é a cadeia de "de": "fuel pump valve" é "a válvula da bomba de combustível". |
| Sem omissões | Igual. O sujeito fica explícito sempre que muda. | O português permite sujeito oculto. Quando o sujeito muda, o leitor não sabe quem age. |
| Sem ponto e vírgula (8.1) | Igual, inclusive nos itens de lista no estilo jurídico. | A regra não depende do idioma. |
| Tamanho da frase | 22 palavras em instruções, no lugar de 20. 27 em descrições, no lugar de 25. | No mesmo texto paralelo (FLORES-200), o português do Brasil usa 6,9% mais palavras que o inglês: artigos, preposições. Os limites acompanham a diferença, arredondados para cima: 20 × 1,07 = 21,4 e 25 × 1,07 = 26,75. As opções `--max-palavras` e `--max-palavras-estrito` ajustam o linter quando um projeto decide outros limites. |
| Instruções de segurança | A condição e o aviso vêm antes da ação, em toda instrução. | Quem age antes de ler o fim da frase não vê a condição. |

As regras sem equivalente no STE estão nas tabelas do `SKILL.md`, cada uma com o motivo.

## Referências de língua

**Acordo Ortográfico e VOLP.** A ortografia segue o Acordo Ortográfico da Língua Portuguesa de 1990, que o Decreto nº 6.583/2008 promulgou no Brasil. Ela segue também o Vocabulário Ortográfico da Língua Portuguesa (VOLP), da Academia Brasileira de Letras. A regra do gênero da norma se apoia nessas duas referências.

**Números: o SI.** A Resolução 10 da 22ª Conferência Geral de Pesos e Medidas (CGPM, 2003) aceita o ponto ou a vírgula como sinal decimal. Ela repete a Resolução 7 da 9ª CGPM (1948): os dígitos podem formar grupos de três para facilitar a leitura. Nenhum ponto e nenhuma vírgula entram entre os grupos. Em português, a vírgula é o sinal decimal ("1,5"), e o espaço separa os grupos ("10 000").

**Datas: a ISO 8601.** A norma define a data no formato AAAA-MM-DD ("2026-10-07"). A ordem vai da unidade maior para a menor, e nenhum leitor confunde o dia com o mês. Quando o ano não importa, esta skill usa o dia e o mês abreviado ("07/Out"). O nome do mês tira a dúvida.

**Manual de Comunicação da Secom do Senado Federal.** Esta skill usa só um verbete deste manual de estilo. O verbete "mesmo" orienta: "Não use *o mesmo*, *a mesma* para substituir nomes e pronomes." A regra de referência sem ambiguidade tem motivo próprio (o leitor precisa procurar o referente) e chega à mesma orientação.

## Linguagem simples: outro leitor

A Lei nº 15.263, de 14 de novembro de 2025, institui a Política Nacional de Linguagem Simples. Ela vale para os textos da administração pública dirigidos ao cidadão. A ABNT NBR ISO 24495-1:2024 é a versão brasileira da norma internacional de linguagem simples (ISO 24495-1:2023).

Esta skill não tira regras dessas normas. O leitor delas é o cidadão, e o leitor desta skill é um leitor técnico ou uma máquina. Uma lei reflete decisões de política pública. Cada regra desta skill precisa de um motivo de leitura: uma ambiguidade que ela tira.

Algumas técnicas do Art. 5º da lei coincidem com regras do STE. Exemplos: ordem direta, frases curtas, uma ideia por parágrafo, voz ativa e verbos no lugar de substantivos. O inciso XI manda "não usar novas formas de flexão de gênero e de número das palavras da língua portuguesa" contrárias às regras gramaticais, ao VOLP e ao Acordo Ortográfico. Ele coincide com a regra do gênero da norma. Nesses pontos, a lei e esta skill chegam à mesma regra por caminhos diferentes. A norma ISO diz que vale também para a redação técnica e para as linguagens controladas, mas dá exemplos só em inglês.

## Por que esta skill usa o STE para a saída de agentes

O STE evita a ambiguidade para um leitor que não pode fazer uma pergunta de volta. Esse leitor é um técnico na pista, com um manual na mão e sem um autor para consultar. Um agente de IA que lê a saída de outro agente, a descrição de uma ferramenta ou uma mensagem de sistema está na mesma posição. Ele não tem um canal de volta para resolver uma dúvida. Por exemplo: esta frase na voz passiva quer dizer que quem chama faz X, ou que quem é chamado faz X? As regras que impedem um mecânico de ler errado uma especificação de torque impedem também um agente de ler errado uma instrução.

## Fontes

**STE**
- [Site oficial do ASD-STE100](https://www.asd-ste100.org/)
- [ASD-STE100: About STE](https://www.asd-ste100.org/about_STE.html)
- [ASD Europe: Simplified Technical English](https://www.asd-europe.org/standards-specifications/simplified-technical-english/)
- [Simplified Technical English na Wikipedia](https://en.wikipedia.org/wiki/Simplified_Technical_English)
- [TechScribe: ASD-STE100 Simplified Technical English](https://www.techscribe.co.uk/techw/asd-simplified-technical-english.htm)
- [SKYbrary: Simplified Technical English (STE)](https://skybrary.aero/articles/simplified-technical-english-ste)

**Tamanho do português**
- [FLORES-200: textos paralelos em 200 línguas](https://github.com/facebookresearch/flores/tree/main/flores200)

**Língua, números e datas**
- [Decreto nº 6.583, de 29 de setembro de 2008 (Acordo Ortográfico)](https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2008/decreto/d6583.htm)
- [Academia Brasileira de Letras (VOLP)](https://www.academia.org.br/)
- [BIPM: Resolução 10 da 22ª CGPM (2003), sinal decimal e grupos de dígitos](https://www.bipm.org/en/-/resolution-cgpm-22-10)
- [ISO 8601: formato de data e hora](https://www.iso.org/iso-8601-date-and-time-format.html)
- [Manual de Comunicação da Secom do Senado Federal: verbete "mesmo"](https://www12.senado.leg.br/manualdecomunicacao/estilos/mesmo)

**Linguagem simples (outro leitor)**
- [Lei nº 15.263, de 14 de novembro de 2025 (Câmara dos Deputados, publicação original)](https://www2.camara.leg.br/legin/fed/lei/2025/lei-15263-14-novembro-2025-798293-publicacaooriginal-177011-pl.html)
- [ISO 24495-1:2023, Plain language, Part 1: Governing principles and guidelines](https://www.iso.org/standard/78907.html)
