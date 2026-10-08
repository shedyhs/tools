# Exemplos de antes e depois

## Parte 1: regras do STE, adaptadas ao português

Estes exemplos ilustram regras reais do ASD-STE100, a partir de fontes secundárias públicas (veja `references/regras-de-redacao.md`). São paráfrases adaptadas ao português, não citações da norma. A norma oficial dá exemplos só em inglês.

| Regra | Antes | Depois | Por quê |
|---|---|---|---|
| Um significado por palavra | "Verifique o sistema." / "Confira as conexões." / "Valide o recebimento." | "Verifique o sistema." / "Verifique as conexões." / "Verifique o recebimento." (um só termo, usado de forma consistente) | Três quase sinônimos obrigam o leitor a adivinhar se eles nomeiam a mesma ação. |
| Uma classe gramatical por palavra | "Logue o evento." | "Registre o evento no log." | Se "log" é aprovado só como substantivo, usar a palavra como verbo quebra a garantia de uma palavra para uma função. Além disso, "logar" também quer dizer "entrar no sistema". |
| Significado preciso do verbo | "Libere a porta 8080." | Se o firewall bloqueia a porta: "Abra a porta 8080 no firewall." Se a porta está em uso: "Encerre o processo que usa a porta 8080." | "Liberar a porta" pode ser abrir a porta para o tráfego ou desocupar a porta. O STE escolhe a palavra sem ambiguidade. |
| Só tempos simples | "Temos recebido o relatório técnico da matriz." | "Recebemos o relatório técnico da matriz." | Em português, "temos recebido" indica repetição ("recebemos várias vezes"). Com um relatório só, a frase é um decalque do present perfect, e o pretérito perfeito diz o fato. |
| Verbo, não substantivo | "Realize uma inspeção do filtro." | "Inspecione o filtro." | O substantivo esconde a ação e acrescenta um verbo vazio. |
| Sem locução verbal idiomática (Regra 9.3) | "O job deixou de rodar." | Se o job parou: "O job parou de rodar." Se o job não rodou desta vez: "O job não rodou." | "Deixar de" + infinitivo tem duas leituras. O sentido da locução não vem das partes, e esse é o motivo da Regra 9.3. |
| Sem gíria técnica (Regra 9.3) | "Suba o container e dê um push na branch." | "Inicie o container. Envie a branch ao repositório remoto." | "Subir" tem quatro sentidos: "iniciar", "publicar", "enviar" e "aumentar a versão". "Dar um push" junta um verbo vazio a um termo em inglês. A reescrita também separa as duas instruções. |
| Condição antes da instrução | "Apague o diretório antigo se o backup terminou sem erros." | "Se o backup terminou sem erros, apague o diretório antigo." | Quem age antes de ler o fim da frase apaga o diretório e não vê a condição. |

## Parte 2: regras próprias do português

Estas regras não existem no STE. Elas cobrem fontes de ambiguidade do português e o traduzês que os modelos de linguagem produzem. A tabela mostra só os casos que pedem mais que o exemplo do `SKILL.md`.

| Regra | Antes | Depois | Por quê |
|---|---|---|---|
| "Seu" com dois donos | "O agente enviou ao usuário seu token." | "O agente enviou ao usuário o token do usuário." | "Seu" pode ser do agente, do usuário ou de você. "Dele" também não resolve, porque os dois nomes são masculinos. |
| "Dever" ambíguo | "O job deve terminar em cinco minutos." | Se é ordem: "O job precisa terminar em cinco minutos." Se é estimativa: "O job provavelmente termina em cinco minutos." | Uma frase, duas leituras. Se o contexto não decide, a reescrita também não decide. Ela mantém a frase e sinaliza na linha `Mantido como está:`. |
| Sujeito oculto com troca de sujeito | "O cliente envia o pedido ao servidor, que valida o token. Se o token expirou, rejeita o pedido." | "O cliente envia o pedido ao servidor. O servidor valida o token. Se o token expirou, o servidor rejeita o pedido." | O sujeito oculto de "rejeita" pode ser o cliente (sujeito da frase anterior) ou o servidor. A reescrita nomeia o servidor, porque a fonte atribui ao servidor a frase "valida o token". |
| Tratamento uniforme | "Abre o painel. Remova o filtro. Limpar a tela." | "Abra o painel. Remova o filtro. Limpe a tela." | "Abre" (tu) é também a forma de "ele abre". O leitor não sabe se a frase é uma ordem ou uma descrição. O infinitivo "Limpar" muda de registro no meio do procedimento. |
| "Excluir" com dois sentidos | "Exclua os arquivos temporários do pacote." | Se é apagar: "Apague os arquivos temporários do pacote." Se é deixar de fora: "Não inclua os arquivos temporários no pacote." | "Excluir" quer dizer apagar e também deixar de fora. Com "do pacote", as duas leituras fazem sentido. |
| Decalque: "eventualmente" | "O cache é eventualmente invalidado." | Se o sentido é "eventually": "O cache é invalidado em algum momento." Se o sentido é "às vezes": "O cache é invalidado às vezes." | Em português, "eventualmente" quer dizer "às vezes" ou "por acaso". Quem escreve pensando em "eventually" quer dizer "mais cedo ou mais tarde". A voz passiva fica, porque a fonte não diz quem invalida o cache. |
| Decalque: "uma vez que" | "Uma vez que o deploy terminou, o agente libera o tráfego." | Se é tempo: "Depois que o deploy termina, o agente libera o tráfego." Se é causa: "Como o deploy terminou, o agente libera o tráfego." | Com o indicativo, "uma vez que" indica causa ("já que"). Como decalque de "once", indica tempo. |
| Locução prolixa e verbo-suporte | "O servidor encontra-se indisponível. Favor efetuar uma nova tentativa." | "O servidor está indisponível. Tente de novo." | "Encontra-se" é "está" com mais palavras. "Favor efetuar" junta o infinitivo de cortesia ao verbo-suporte. |

## Parte 3: aplicado à saída de agentes

Estes são exemplos originais, criados para o uso real desta skill. O objetivo é reescrever a saída de agentes de IA. Outro agente, uma camada de tradução ou um leitor estrangeiro precisa interpretar o texto sem ambiguidade. São ilustrações, não citações de um sistema real.

As contagens de palavras abaixo contam os trechos separados por espaço (`text.split()`), e a pontuação não conta à parte. Outro tokenizador vai produzir outro número.

Cada bloco "Antes" fica entre duas diretivas `deve-falhar` do linter, com as regras que ele precisa quebrar. O `--autoteste` verifica se cada bloco ainda falha com essas regras. Os blocos "Depois" passam pelo linter como o resto do arquivo.

### Exemplo A: descrição de ferramenta

**Antes:**

<!-- pts-lint: deve-falhar frase-longa verbo-suporte -->
> Esta ferramenta irá tentar realizar a sincronização do estado entre os diversos backends que foram configurados, e caso um conflito seja detectado ela poderá resolvê-lo automaticamente dependendo da estratégia que tiver sido definida, ou caso contrário irá apresentar o conflito para revisão manual.
<!-- pts-lint: fim -->

**Violações marcadas:**
- Duas instruções numa frase (sincronizar, e depois resolver ou mostrar o conflito).
- Verbo-suporte ("realizar a sincronização").
- Voz passiva nas orações subordinadas ("foram configurados", "seja detectado", "tiver sido definida").
- Futuro ("irá") para descrever o comportamento da ferramenta. A skill descreve o comportamento de um sistema no presente.
- 43 palavras, muito acima do limite de 27 para descrições.

Note o que *não* foi marcado: "tentar" e "poderá resolvê-lo". São ressalvas, não violações. A ferramenta não promete sucesso, e a reescrita também não pode prometer. O "irá" de "irá tentar" é só o tempo futuro. A reescrita troca o futuro pelo presente ("tenta"), e a ressalva continua em "tentar".

**Depois:**
> A ferramenta tenta sincronizar o estado entre os backends configurados. Se encontrar um conflito, a ferramenta lê a estratégia configurada. Se a estratégia permitir resolução automática, a ferramenta pode resolver o conflito automaticamente. Se a ferramenta não resolver o conflito, ela encaminha o conflito para revisão manual.

A última frase depende de a ferramenta resolver ou não o conflito, e não do que a estratégia permite. Esse é o sentido de "ou caso contrário" no original: o caminho alternativo cobre também uma resolução permitida que não aconteceu.

### Exemplo B: mensagem de erro

**Antes:**

<!-- pts-lint: deve-falhar frase-longa -->
> Um erro pode ter ocorrido durante o processamento da sua requisição devido a uma possível incompatibilidade no formato de dados esperado, o que poderia ser causado por uma versão desatualizada do cliente.
<!-- pts-lint: fim -->

**Violações marcadas:**
- Uma frase com três afirmações separadas (um erro, uma incompatibilidade de formato, uma versão de cliente).
- Ação congelada em substantivo ("o processamento da sua requisição").
- 32 palavras, acima do limite de 27 para descrições.

Não marcado: "pode ter ocorrido" e "poderia ser causado por". Quem escreveu a mensagem é um sistema que não sabe o que deu errado. As duas ressalvas relatam essa incerteza com exatidão.

**Depois:**
> Sua requisição pode ter falhado. A causa pode ser um formato de dados diferente do formato que o servidor espera. Uma versão desatualizada do cliente pode causar essa diferença.

**A regra da modalidade existe por causa deste exemplo.** Uma reescrita tentadora troca a primeira frase por "Sua requisição falhou". Ela troca também a terceira por "uma versão desatualizada do cliente **é a causa mais comum**". As duas trocas melhoram a leitura, e as duas estão erradas. A primeira afirma uma falha de que o sistema só suspeita. A segunda inventa uma frequência que não aparece em lugar nenhum da entrada. Uma reescrita que fornece uma causa, uma frequência ou um mecanismo não é mais uma reescrita.

Em inglês, "may have failed" mantém uma forma composta que a regra dos tempos não permitiria. Em português, o conflito não aparece nesta frase. "Pode ter falhado" usa o infinitivo composto depois do verbo modal, e a regra dos tempos trata de outra forma ("tem falhado"). Nas duas línguas vale o mesmo princípio. **Quando a regra dos tempos e a regra da modalidade entram em conflito, a modalidade vence.** Sem o auxiliar, a incerteza some junto com o tempo verbal.

### Exemplo C: instrução entre agentes

**Antes:**

<!-- pts-lint: deve-falhar frase-longa verbo-suporte locucao-prolixa -->
> Uma vez que o job upstream tenha sido concluído e assumindo que nenhum erro tenha sido levantado, o agente downstream deverá proceder ao consumo do artefato de saída, sendo que vale ressaltar que artefatos parciais eventualmente são produzidos em condições de timeout.
<!-- pts-lint: fim -->

**Violações marcadas:**
- Voz passiva e orações subordinadas empilhadas ("tenha sido concluído", "assumindo que...", "sendo que vale ressaltar que...").
- Decalques do inglês: "assumindo que" (assuming) e "eventualmente".
- Verbo-suporte ("proceder ao consumo") e expressão de preenchimento ("vale ressaltar que").
- Uma frase, três fatos separados (condição de término, próxima ação, aviso sobre um caso-limite).
- 42 palavras, acima do limite de 22 para instruções.

**Depois:**
> Espere o job upstream terminar sem erros. Depois, leia o artefato de saída. Atenção: um timeout pode produzir um artefato parcial. Verifique se o artefato está completo antes de usá-lo.

Decisões que vale a pena declarar em vez de esconder:
- "Deverá proceder ao consumo" virou o imperativo "leia". Aqui o contexto decide o sentido de "dever". A frase é uma instrução para o agente que executa a tarefa, então "deverá" é uma ordem, não uma estimativa. O STE permite a troca por um imperativo em instruções. Não faça a mesma troca em texto descritivo.
- "Uma vez que" tem duas leituras. Com o subjuntivo ("tenha sido concluído"), indica tempo ou condição. Com o indicativo, indica causa. A reescrita usa "Espere... terminar" e "Depois", que só têm a leitura de tempo.
- Aqui, "eventualmente" está certo em português ("às vezes"). Mas um leitor que pensa em inglês lê "eventually". A reescrita usa "pode", que tem uma leitura só.
- A última frase é **nova**. O original avisava sobre artefatos parciais, mas não dizia o que fazer. A verificação torna o aviso útil, mas é conteúdo acrescentado. Por isso, este exemplo declara a frase e não a esconde na reescrita. Se o silêncio da fonte era intencional, corte a frase.

### Exemplo D: prosa de README (modo Flexível)

**Antes:**

<!-- pts-lint: deve-falhar frase-longa ponto-e-virgula adjetivo-de-marketing -->
> Nossa camada de cache foi projetada para se encaixar perfeitamente na sua stack existente com o mínimo de atrito e sem vendor lock-in; ela alavanca a similaridade semântica para reduzir drasticamente os cache misses que tradicionalmente atormentam as cargas de trabalho de LLMs.
<!-- pts-lint: fim -->

**Violações marcadas:**
- Adjetivos e afirmações de marketing sem medida ("perfeitamente", "com o mínimo de atrito", "drasticamente").
- Ponto e vírgula entre duas ideias separadas.
- Decalque e jargão ("alavanca", "vendor lock-in").
- Voz passiva ("foi projetada").
- 43 palavras, acima do limite de 27 para descrições.

**Depois:**
> Este cache usa a similaridade semântica entre prompts para reduzir os cache misses, um problema comum em aplicações de grandes modelos de linguagem (LLMs). Ele funciona com a stack que você já usa e não prende você a um fornecedor.

O modo Flexível não impôs um termo fixo por conceito. Ainda assim, ele cortou os adjetivos de marketing, o ponto e vírgula, o decalque e a frase longa. A reescrita não explica como um cache comum funciona, porque a fonte não explica.

## Como ler estes exemplos

A Parte 1 ilustra as regras do STE em que esta skill se baseia. A Parte 2 ilustra as regras que o português acrescenta. A Parte 3 aplica as regras à saída de agentes. A mesma disciplina torna mais seguro de interpretar o texto entre máquinas e entre línguas, não só os manuais de aeronaves. Essa disciplina é: um significado por palavra, voz ativa, tempos simples, uma instrução por frase e condições explícitas em vez de orações subordinadas escondidas.
