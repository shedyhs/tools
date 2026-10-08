#!/usr/bin/env python3
"""Linter determinístico para as regras estruturais do SKILL.md (português do Brasil).

Verifica só as regras que dispensam dicionário. Por decisão de projeto, nunca
marca ressalvas nem modalidade (pode, poderia, talvez, deve ter, teria): a
skill trata o grau de certeza como conteúdo, e um linter que pressiona contra
ressalvas acaba reescrevendo afirmações.

Uso:
    pts-lint.py ARQUIVO [ARQUIVO ...]
    echo "texto" | pts-lint.py [--json]
    pts-lint.py --linha-de-base 5 ARQUIVO  # passa se houver 5 violações obrigatórias ou menos
    pts-lint.py --desativar voz-passiva,tempo-composto ARQUIVO
    pts-lint.py --ativar historico ARQUIVO # regras opcionais (veja REGRAS_OPCIONAIS)
    pts-lint.py --max-palavras 30 ARQUIVO  # limite de palavras por frase (padrão 27)
    pts-lint.py --resumo ARQUIVO ...       # contagem por arquivo, pior arquivo primeiro
    pts-lint.py --linguagem rust --partes docs,comentarios,mensagens src/lib.rs
    pts-lint.py --ler-citacoes ARQUIVO     # analisa também o texto entre aspas
    pts-lint.py --autoteste                # testes internos e documentos da skill
    pts-lint.py --ajuda

Linguagens de entrada (`--linguagem`, ou pela extensão do arquivo):

- markdown (padrão, também para texto puro e stdin): a prosa é lida por
  parágrafo, então uma frase quebrada em várias linhas conta como uma frase.
  Blocos de código, fórmulas em bloco, comentários HTML, definições de link e
  front matter YAML ficam de fora. Código e fórmulas inline contam como uma
  palavra cada. Destinos de link não contam.

  Um trecho entre aspas ("...", “...” ou «...») é uma menção: um exemplo, um
  rótulo ou uma citação. Ele conta como uma palavra e não é analisado.
  `--ler-citacoes` desliga esse comportamento.

  Um exemplo que precisa falhar fica entre duas diretivas:
    <!-- pts-lint: deve-falhar frase-longa verbo-suporte -->
    ...
    <!-- pts-lint: fim -->
  Os achados dentro da região são esperados e saem do relatório. A região
  falha (exemplo-sem-falha) se não tiver um achado obrigatório ou se faltar
  uma das regras listadas. A lista é opcional.
- rust (`*.rs`): só a prosa é lida, nunca o código. `--partes` escolhe as
  partes (padrão `docs,comentarios`):
    docs         `///`, `//!`, `/** */`, `/*! */` (lidos como Markdown, como no rustdoc)
    comentarios  `//`, `/* */` (linhas que parecem código comentado ficam de fora)
    mensagens    literais de string dentro de panic!/assert!/expect/println!/...
    literais     todo literal de string com três palavras ou mais
  Mensagens são texto de erro, então usam o limite estrito
  (`--max-palavras-estrito`, padrão 22).

Regras obrigatórias: ponto-e-virgula, frase-longa, locucao-prolixa,
verbo-suporte, giria-tecnica, adjetivo-de-marketing, gerundismo (verbo de ação
pontual), data-ambigua (dia/mês/ano), numero-ambiguo, linguagem-neutra,
rotacao-de-sinonimos, conjuncao-pendente, exemplo-sem-falha e
diretiva-invalida.

Regras consultivas: voz-passiva, passiva-sintetica, tempo-composto,
cadeia-de-preposicoes, o-mesmo, gerundio-encadeado, decalque-do-ingles,
locucao-verbal, palavra-ambigua, ser-estar, travessao, gerundismo (outros
verbos), data-ambigua (dia/mês sem ano) e numero-ambiguo (três casas depois
da vírgula). Elas nunca reprovam a execução.

Sai com código 1 quando as violações obrigatórias passam da linha de base
(padrão 0). Sai com código 2 em erro de uso, inclusive numa opção ou regra
desconhecida.
"""
import bisect
import json
import os
import re
import sys

OBRIGATORIA = "obrigatoria"
CONSULTIVA = "consultiva"

# Heurísticas de regex, não um analisador sintático. Sem regra de elipse por
# decisão do projeto original: às vezes a escrita técnica justifica uma.

# Formas flexionadas usadas em várias regras.
FAZER = (r"(?:fa(?:z|zer|zem|zendo|zia|ziam|ço|ça|ças|çam|çamos|remos|rá|rão|ria|riam)"
         r"|fi(?:z|zer|zeram|zemos|zesse)|fez|feit[oa]s?)")
DAR = (r"(?:dar|dá|dão|dê|deem|dou|deu|demos|deram|dava|davam|dará|darão|daria|dariam"
       r"|dando|dado)")
TER = r"(?:ter|tem|têm|tenho|temos|tinha|tinham|teve|tiveram|terá|terão|tenha|tenham|tendo|tido)"
# Verbos-suporte: verbos vazios que carregam um substantivo de ação.
VERBO_SUPORTE = (r"(?:realiz(?:a|am|e|em|ar|ou|aram|ará|arão|aria|ariam|ando|ado|ada|amos|ei)"
                 r"|efetu(?:a|am|e|em|ar|ou|aram|ará|arão|aria|ariam|ando|ado|ada|amos|ei)"
                 r"|promov(?:e|em|a|am|er|eu|eram|erá|erão|eria|endo|ido|emos)"
                 r"|" + FAZER + r")")
# Substantivos com sufixo de ação que, em texto técnico, nomeiam coisas.
NAO_ACAO = (r"(?:(?:funç|aplicaç|vers|seç|sess|opç|informaç|quest|transaç|instruç|condiç|posiç"
            r"|coleç|dimens|extens)(?:ão|ões)|(?:docu|mo|ele|argu|equipa|seg|frag|instru)mentos?)\b")
SUFIXO_DE_ACAO = r"(?:ções|ção|sões|são|mentos|mento|âncias|ância|ências|ência|agens|agem|ises|ise)"
SUBSTANTIVO_DE_ACAO = (r"(?:\w+" + SUFIXO_DE_ACAO + r"|leitura|escrita|abertura|captura|consulta|busca"
                       r"|pesquisa|cópia|coleta|limpeza|cobrança|entrega|troca)")
# Particípios. Palavras com vogal acentuada antes de -ido/-ado são adjetivos
# ("rápido", "válida"), não particípios.
PARTICIPIO = (r"(?![\w]*[áàâãéêíóôõú]\w*(?:ad|id)[oa]s?\b)"
              r"(?:\w+(?:ad|id|íd)[oa]s?|(?:feit|escrit|abert|post|vist|dit|cobert|aceit|pag|gast|ganh"
              r"|impress|eleit|suspens|pres|solt|extint|express|aces)[oa]s?|entregues?)")
NAO_PARTICIPIO = (r"(?!(?:cada|nada|vida|lado|dados|resultados?|estados?|significados?|sentidos?|cuidados?"
                  r"|pedidos?|chamados?|legados?|mercados?|partidos?|ruídos?)\b)")
# Objetos que a gíria técnica costuma acompanhar ("subir o servidor").
OBJETO_TECNICO = (r"(?:servidor(?:es)?|serviços?|containers?|contêiner(?:es)?|ambientes?|aplicaç(?:ão|ões)|apps?"
                  r"|código|branch(?:es)?|prs?|versão|build|pods?|cluster|banco|api|arquivos?|imagens?|imagem"
                  r"|deploy|sistemas?|máquinas?|instâncias?|processos?|jobs?)")
# Verbos de ação pontual: "vou estar enviando" é gerundismo, "vai estar rodando durante a
# janela" é um futuro durativo legítimo.
PONTUAIS = (r"(?:envi|mand|encaminh|transfer|retorn|pass|agend|providenci|cancel|confirm|verific|analis|lig|avis"
            r"|respond|registr|atualiz|resolv|reinici|instal|liber|bloque|desbloque|cadastr|entr|abr|fech|anot"
            r"|repass|devolv|corrig)")
IR_ESTAR = (r"\b(?:vou|vai|vamos|vão|ia|iam|íamos|irei|irá|iremos|irão|iria|iriam|ir)\s+estar\s+"
            r"(?:(?:te|lhe|lhes|o|a|os|as|me|nos|vos|se)\s+)?")
# Adjetivos que quase sempre descrevem um estado atual, que pede "estar". "Vazio" e
# "ativo" ficam de fora: "são vazios por padrão" e "é ativo no plano pago" são essência.
ESTADOS = r"(?:disponíve(?:l|is)|indisponíve(?:l|is)|online|offline|fora do ar)"

LOCUCOES = [
    (r"a fim de", "Locução prolixa. Use 'para'."),
    (r"com (?:o )?(?:objetivo|intuito|propósito) de", "Locução prolixa. Use 'para'."),
    # só antes de infinitivo: "no sentido de 'por fim'" (= com o significado de) é legítimo
    (r"no sentido de\s+\w+(?:ar|er|ir)", "Locução prolixa. Use 'para'."),
    (r"de (?:forma|modo|maneira) a", "Locução prolixa. Use 'para'."),
    (r"tendo em vista", "Locução prolixa. Use 'porque' ou 'por causa de'."),
    (r"(?:devido ao|em virtude do|em razão do|pelo|por conta do) fato de", "Locução prolixa. Use 'porque'."),
    (r"em virtude d[eoa]s?(?!\s+fato\b)", "Locução prolixa. Use 'por' ou 'por causa de'."),
    (r"no que (?:diz respeito|se refere|tange|concerne) (?:a|à|ao|às|aos)", "Locução prolixa. Use 'sobre' ou 'em'."),
    (r"com relação (?:a|à|ao|às|aos)", "Locução prolixa. Use 'sobre'."),
    (r"no decorrer d[eoa]s?", "Locução prolixa. Use 'durante'."),
    (r"para poder(?:em|mos)?", "Locução prolixa. Use só 'para' e o verbo."),
    (r"a nível d[eoa]s?", "'A nível de' é modismo. Use 'em', 'no' ou 'sobre'."),
    (r"encontra(?:m)?-se", "Locução prolixa. Use 'está' ou 'estão'."),
    (r"trata-se d[eoa]s?", "Locução prolixa. Use 'é'."),
    (r"sendo que", "'Sendo que' encadeia ideias sem dizer a relação entre elas. Divida em duas frases "
                   "ou use o conector exato (porque, mas, e)."),
    (r"favor\s+\w+(?:ar|er|ir)", "Use o imperativo ('Verifique'), não 'Favor verificar'."),
    (r"(?:vale|é importante|cabe) (?:ressaltar|destacar|lembrar|mencionar|notar|observar|salientar) que",
     "Expressão de preenchimento. Afirme o fato direto."),
]

SUPORTE_FIXO = [
    # "proceder a" + qualquer substantivo: "proceda ao envio", "proceder ao consumo"
    (r"proced(?:e|em|a|am|er|eu|eram|erá|erão|eria|endo|ido|emos)\s+(?:a|à|ao|às|aos)\s+\w+",
     "Verbo-suporte. Use o verbo da ação ('remova', não 'proceda à remoção')."),
    (DAR + r"\s+início\b", "Verbo-suporte. Use 'iniciar' ou 'começar'."),
    (FAZER + r"\s+uso\b", "Verbo-suporte. Use 'usar'."),
    (r"lev(?:ar|a|am|e|em|ou|aram|ará|arão|ando|ado)\s+em\s+(?:consideração|conta)\b",
     "Verbo-suporte. Use 'considerar'."),
    (r"tom(?:ar|a|am|e|em|ou|aram|ará|arão|ando|ado)\s+(?:a|uma)\s+decisão\b", "Verbo-suporte. Use 'decidir'."),
    (TER + r"\s+conhecimento\b", "Verbo-suporte. Use 'saber' ou 'conhecer'."),
    (DAR + r"\s+uma\s+olhada\b", "Verbo-suporte. Use 'examinar' ou 'ler'."),
    (r"cheg(?:ar|a|am|ou|aram|ará|arão|ando|ue|uem)\s+à\s+conclusão\b", "Verbo-suporte. Use 'concluir'."),
]

DECALQUES = [
    (r"eventualmente", "'Eventualmente' significa 'às vezes' ou 'por acaso', não 'por fim' (eventually). "
                       "Use 'às vezes', 'por fim' ou 'em algum momento', conforme o sentido."),
    (r"uma vez que", "'Uma vez que' significa 'já que' (causa). Se o sentido é de tempo (once), "
                     "use 'depois que' ou 'quando'."),
    (r"assum(?:ir|e|em|o|imos|indo|iu|iram|irá|irão|a|am)\s+que",
     "'Assumir que' é decalque de 'assume that'. Use 'supor que' ou 'considerar que'."),
    (r"endereç\w+\s+(?:o|a|os|as|esse|essa|esses|essas|este|esta|estes|estas)\s+"
     r"(?:problemas?|questão|questões|pontos?|issues?|demandas?|riscos?|preocupaç(?:ão|ões))",
     "'Endereçar um problema' é decalque de 'address an issue'. Use 'tratar' ou 'resolver'."),
    (r"suport(?:a|am|ar|ou|aram|ará|arão|ado|ada|ados|adas|ando|em)",
     "'Suportar' significa 'aguentar'. Se o sentido é compatibilidade (support), use 'aceitar', "
     "'ser compatível com' ou 'oferecer suporte a'."),
    (r"mandatóri[oa]s?", "Decalque de 'mandatory'. Use 'obrigatório'."),
    (r"randômic[oa]s?", "Decalque de 'random'. Use 'aleatório'."),
    (r"requerimentos?", "Se o sentido é 'requirement', use 'requisito'. 'Requerimento' é um pedido formal."),
    (r"performances?", "Use 'desempenho'."),
    (r"delet(?:ar|a|am|e|em|ou|aram|ará|arão|ado|ada|ados|adas|ando)",
     "Use 'apagar' ('excluir' também quer dizer 'deixar de fora'), a menos que 'deletar' seja o termo "
     "fixo da equipe."),
    (r"set(?:ar|ou|aram|ado|ada|ados|adas|ando|am)", "Use 'definir' ou 'configurar'."),
    (r"start(?:ar|a|am|e|em|ou|aram|ado|ada|ando)", "Use 'iniciar'."),
    (r"print(?:ar|a|am|e|em|ou|aram|ado|ada|ando)",
     "Use 'imprimir', 'exibir' ou 'capturar a tela', conforme o sentido."),
    (r"customiz\w*", "Use 'personalizar'."),
    (r"alavanc(?:ar|a|am|ou|aram|ará|arão|ado|ada|ando)|alavanqu(?:e|em)",
     "'Alavancar' no sentido de 'leverage' é jargão. Use 'usar' ou 'aproveitar'."),
    (r"(?:no|ao) final do dia", "Decalque de 'at the end of the day'. Corte, ou use 'no fim das contas'."),
    (r"(?:é|são|está|estão|era|eram) supost[oa]s? a", "Decalque de 'is supposed to'. Use 'deve' ou 'precisa'."),
    (r"em ordem (?:a|de)\s+\w+(?:ar|er|ir)", "Decalque de 'in order to'. Use 'para'."),
    (r"perform(?:ar|a|am|e|em|ou|aram|ará|arão|aria|ando|ado|ada)",
     "Decalque de 'perform'. Use 'ter desempenho', 'funcionar' ou 'executar', conforme o sentido."),
    (r"realiz(?:ar|a|am|o|ei|ou|aram|ando)\s+que", "Decalque de 'realize that'. Use 'perceber que'."),
]

# Gíria técnica: verbos informais com vários sentidos. É o equivalente mais próximo dos
# phrasal verbs informais que o STE proíbe ("spin up", "kick off").
GIRIAS = [
    (r"(?:sub(?:ir|a|am|o|iu|iram|imos|indo|ido|irá|irão|iria)|sobe|sobem)\s+(?:(?:o|a|os|as|um|uma|esse|essa|este"
     r"|esta)\s+)?(?:\w+\s+)?" + OBJETO_TECNICO + r"\b",
     "'Subir' tem vários sentidos: iniciar, publicar, enviar ou aumentar a versão. Use o verbo exato."),
    (r"(?:sub(?:ir|a|am|o|iu|iram|imos|indo|ido|irá|irão|iria)|sobe|sobem)\s+(?:para|pra|em)\s+"
     r"(?:a\s+)?(?:produção|homologação|staging|prod)\b",
     "'Subir para produção' é gíria. Use 'publicar em produção'."),
    (r"derrub(?:ar|a|am|e|em|o|ou|aram|ando|ado|ada|ará|arão)\s+(?:(?:o|a|os|as|um|uma|esse|essa|este|esta)\s+)?"
     r"(?:\w+\s+)?" + OBJETO_TECNICO + r"\b",
     "'Derrubar' pode ser parar de propósito ou causar uma falha. Use 'parar', 'desligar' ou 'causar a falha de'."),
    (DAR + r"\s+(?:um|uma)\s+(?:push|pull|merge|commit|deploy|restart|reboot|refresh|reset|rollback|kill|start|stop"
     r"|ping|fetch|build|upgrade|checada|conferida|geral|tapa)\b",
     "Gíria com 'dar um'. Use o verbo da ação: enviar, mesclar, reiniciar, verificar."),
    (r"bat(?:er|e|em|a|am|eu|eram|endo|ido)\s+(?:n[oa]s?|em)\s+(?:\w+\s+)?"
     r"(?:endpoints?|api|servidor(?:es)?|serviços?|banco|url|rotas?|porta)\b",
     "'Bater em' é gíria. Use 'chamar' ou 'enviar uma requisição a'."),
    (DAR + r"\s+(?:pau|ruim|tilt)\b", "Gíria. Diga o que aconteceu: 'falhou', 'travou' ou 'retornou o erro X'."),
    (r"jog(?:ar|a|am|ue|uem|ou|aram|ando)\s+(?:(?:o|a|os|as|isso|isto|tudo)\s+)?(?:n[oa]s?|para\s+[oa]s?|pr[oa]s?)\s+"
     r"(?:log|logs|lixo|banco|cache|fila|tela)\b",
     "'Jogar em' é gíria. Use 'gravar no log', 'apagar' ou 'enviar à fila', conforme o sentido."),
]

# Locuções verbais idiomáticas: o sentido não vem das partes (Regra 9.3 do STE).
LOCUCOES_VERBAIS = [
    (r"deix(?:ar|a|am|e|em|ou|aram|ará|arão|ando)\s+de\s+\w+(?:ar|er|ir)",
     "'Deixar de' tem duas leituras: parar de ('deixou de rodar') ou não fazer ('deixou de enviar'). "
     "Escreva 'parou de' ou 'não'."),
    (r"acab(?:ar|a|am|e|em|ou|aram|ará|arão|ando)\s+(?:com|por)\b",
     "'Acabar com' e 'acabar por' não dizem a ação (apagar? encerrar? resolver?). Use o verbo exato."),
    (r"(?:d(?:ar|á|ão|eu|eram|ava|ará|ando|ado)|dei)(?:-se)?\s+conta\s+d[eoa]s?\b",
     "'Dar conta de' pode ser conseguir fazer ou perceber. Use 'conseguir' ou 'perceber'."),
    (r"(?:dá|dava|deu|daria)\s+(?:para|pra)\s+\w+(?:ar|er|ir)\b",
     "'Dá para' pode ser possibilidade ou permissão. Use 'é possível' ou 'você pode'."),
    (r"fic(?:ar|a|am|ou|aram|ará|arão)\s+de\s+\w+(?:ar|er|ir)\b",
     "'Ficar de' é uma promessa informal. Diga se a ação aconteceu ou se ela está prevista."),
]

PASSIVA_SE = ("recomenda sugere deve pode utiliza usa verifica observa nota considera espera sabe realiza "
              "efetua executa aplica define calcula gera cria remove exclui adiciona configura acredita "
              "entende admite assume percebe conclui obtém faz tem precisa necessita "
              "recomendam sugerem devem podem utilizam usam verificam observam consideram esperam realizam "
              "efetuam executam aplicam definem calculam geram criam removem excluem adicionam configuram "
              "obtêm fazem").split()

DE = r"(?:de|do|da|dos|das)"
# Quebram a cadeia: coordenação, locuções prepositivas ("cerca de", "antes de"), partitivo ("um dos"),
# números (datas por extenso) e nomes próprios ("Manual de Comunicação da Secom").
LOCUCAO_DE = "cerca antes depois além através dentro fora perto longe partir apesar vez acima abaixo".split()
INICIO_DE = "".join(f"(?<!{word} )" for word in LOCUCAO_DE + ["um", "uma"])
NAO_ELO = r"(?!(?:e|ou|" + "|".join(LOCUCAO_DE) + r")\b|\d|(?-i:[A-ZÀ-Ý]))"
ELO_DE = DE + r"(?:\s+" + NAO_ELO + r"\w+){1,2}\s+"

RULES = [
    ("ponto-e-virgula", OBRIGATORIA,
     re.compile(r";"),
     "O STE proíbe o ponto e vírgula (Regra 8.1). Divida em frases separadas."),
    *[("locucao-prolixa", OBRIGATORIA, re.compile(r"\b" + pattern + r"\b", re.I), message)
      for pattern, message in LOCUCOES],
    ("verbo-suporte", OBRIGATORIA,
     re.compile(r"\b" + VERBO_SUPORTE + r"\s+(?:(?:a|à|ao|às|aos|o|os|as|um|uma)\s+){0,2}(?!" + NAO_ACAO + r")"
                + SUBSTANTIVO_DE_ACAO + r"\b", re.I),
     "Ação congelada em substantivo. Use o verbo pleno (analise, não realize a análise)."),
    *[("verbo-suporte", OBRIGATORIA, re.compile(r"\b" + pattern, re.I), message)
      for pattern, message in SUPORTE_FIXO],
    ("adjetivo-de-marketing", OBRIGATORIA,
     re.compile(r"\b(?:robust(?:o|a|os|as|ez|amente)|poderos[oa]s?|inovador(?:a|es|as)?|revolucionári[oa]s?"
                r"|(?<!não )(?<!pouco )intuitiv[oa]s?|incríve(?:l|is)|ultrarrápid[oa]s?|de ponta(?!\s+a\s+ponta)"
                r"|de última geração|de classe mundial|estado[- ]da[- ]arte|sem esforço|sem complicaç(?:ão|ões)"
                r"|sem atrito|sem fricção|(?:com )?o mínimo de atrito|integração perfeita|divisor de águas|drasticamente"
                r"|perfeitamente(?!\s+(?:possíve(?:l|is)|norma(?:l|is)|válid[oa]s?|aceitáve(?:l|is)|clar[oa]s?"
                r"|compreensíve(?:l|is)|razoáve(?:l|is)))"
                r"|sem precedentes)\b", re.I),
     "Adjetivo de marketing. Corte, ou troque pela medida que justifica a afirmação."),
    ("gerundismo", OBRIGATORIA,
     re.compile(IR_ESTAR + PONTUAIS + r"(?:ando|endo|indo)\b", re.I),
     "Gerundismo. Use o futuro simples (enviaremos) ou 'ir' + infinitivo (vamos enviar)."),
    ("gerundismo", CONSULTIVA,
     re.compile(IR_ESTAR + r"(?!" + PONTUAIS + r"(?:ando|endo|indo)\b)\w+(?:ando|endo|indo)\b", re.I),
     "Possível gerundismo. Se a ação é pontual, use o futuro (enviaremos) ou 'ir' + infinitivo (vamos enviar). "
     "Se a ação dura um período ('vai estar rodando durante a janela'), mantenha."),
    *[("giria-tecnica", OBRIGATORIA, re.compile(r"\b" + pattern, re.I), message) for pattern, message in GIRIAS],
    ("data-ambigua", OBRIGATORIA,
     re.compile(r"(?<![\w/.-])\d{1,2}[/-]\d{1,2}[/-](?:\d{4}|\d{2})(?![\w/-]|[.,]\d)"),
     "Data no formato dia/mês/ano: um leitor pode ler mês/dia. Use AAAA-MM-DD (2026-10-07)."),
    ("data-ambigua", CONSULTIVA,
     re.compile(r"(?<![\w/.,-])(?!24/7\b)(?=\d{2}/\d|\d/\d{2})(?:0?[1-9]|[12]\d|3[01])/(?:0?[1-9]|1[0-2])"
                r"(?![\w/-]|[.,]\d)"),
     "Se isto é uma data, '07/10' pode ser 7 de outubro ou 10 de julho. Use AAAA-MM-DD ou, sem o ano, "
     "o mês abreviado (07/Out)."),
    ("numero-ambiguo", OBRIGATORIA,
     # Um só grupo depois do ponto e nenhuma vírgula decimal: "1.000" pode ser 1,0.
     re.compile(r"(?<![\w.,/])(?<!nº )(?<!n\.º )(?<!n° )\d{1,3}\.\d{3}(?![\w/]|[.,]\d)"),
     "Ponto como separador de milhar: '1.000' pode ser lido como 1,0. Agrupe com espaço (10 000) ou não "
     "agrupe (1000)."),
    ("numero-ambiguo", CONSULTIVA,
     re.compile(r"(?<![\w.,/])\d{1,3},\d{3}(?![\w/]|[.,]\d)"),
     "Vírgula decimal com três casas: '1,500' pode ser lido como 1500. Mude a unidade (1500 ms) ou, se a "
     "precisão não importa, corte os zeros (1,5)."),
    ("linguagem-neutra", OBRIGATORIA,
     re.compile(r"\b(?:todes|elus?|delus?|nelus?|aquelus?|daquelus?|menines|amigues|alunes|usuáries|funcionáries"
                r"|obrigade|querides|bem-vindes|todx|elx|delx|nelx|aquelx|amigx|alunx|meninx|usuárix|funcionárix"
                r"|obrigadx|queridx|bem-vindx|[a-zà-ú]+xs)\b|\b[a-zà-ú]+@s?(?![\w@-]|\.\w)", re.I),
     "Forma de gênero fora da norma (VOLP, Acordo Ortográfico). Use o masculino genérico ('os usuários') ou "
     "um nome sem flexão de gênero ('a equipe', 'quem usa')."),
    ("voz-passiva", CONSULTIVA,
     re.compile(r"\b(?:é|são|foi|foram|era|eram|será|serão|seria|seriam|seja|sejam|fosse|fossem|for|forem"
                r"|sido|sendo|ser)\s+(?:\w+mente\s+)?" + NAO_PARTICIPIO + PARTICIPIO + r"\b", re.I),
     "Possível voz passiva. Nomeie quem age e use o verbo na ativa, a menos que quem age seja "
     "desconhecido ou irrelevante."),
    ("passiva-sintetica", CONSULTIVA,
     re.compile(r"\b(?:" + "|".join(PASSIVA_SE) + r")-se\b"
                r"|\b(?:não|nunca|já|também|ainda|aqui|onde)\s+se\s+(?:" + "|".join(PASSIVA_SE) + r")\b", re.I),
     "A partícula 'se' esconde quem age (passiva sintética ou sujeito indeterminado). Nomeie quem age "
     "ou use o imperativo."),
    ("tempo-composto", CONSULTIVA,
     # "pode ter falhado", "talvez tenha falhado" e "teria falhado" são ressalvas protegidas
     re.compile(r"\b(?:tenho|tem|têm|temos|tinha|tinham|tínhamos|havia|haviam|terá|terão|haverá)\s+"
                r"(?:\w+mente\s+)?" + NAO_PARTICIPIO
                + r"(?![\w]*[áàâãéêíóôõú]\w*(?:ad|id)o\b)(?:\w+(?:ad|id|íd)o|feito|escrito|aberto|posto|visto"
                r"|dito|coberto|aceito|entregue|pago|gasto|ganho|impresso|eleito|suspenso|preso|solto|extinto"
                r"|expresso|aceso|salvo)\b", re.I),
     "Tempo composto. 'Tem falhado' indica repetição até agora. Para um fato único, use o "
     "pretérito perfeito (falhou). Se a repetição é o ponto, mantenha e sinalize."),
    ("cadeia-de-preposicoes", CONSULTIVA,
     re.compile(r"\b" + INICIO_DE + ELO_DE * 2 + DE + r"\s+\w+", re.I),
     "Cadeia de três ou mais 'de' (equivale a um grupo nominal de quatro substantivos). Use um verbo ou divida a "
     "informação."),
    ("o-mesmo", CONSULTIVA,
     re.compile(r"\b(?:(?:d|n|pel)(?:o|a|os|as)|ao|aos|à|às|(?:com|para|sobre|em)\s+(?:o|a|os|as))\s+"
                r"mesm[oa]s?(?=\s*(?:[.,;:!?)]|$))"
                r"|\b(?:o|a|os|as)\s+mesm[oa]s?(?=\s+(?:é|são|está|estão|esteja|estejam|estiver|estiverem|foi"
                r"|foram|será|serão|seja|sejam|for|forem|era|eram|estava|estavam|deve|devem|pode|podem|tem|têm"
                r"|possui|possuem|contém|contêm|fica|ficam|precisa|precisam|encontra|encontram|já|não"
                r"|também)\b)", re.I),
     "'O mesmo' no lugar de um nome. Se retoma um nome, repita o nome ou use 'ele'/'ela'. "
     "Se significa 'a mesma coisa', ignore."),
    ("gerundio-encadeado", CONSULTIVA,
     # "incluindo" e "dependendo de" funcionam como preposição, não como outra ação
     re.compile(r",\s+(?!(?:quando|comando|brando|bando|adendo|dividendo|remendo|tremendo|lindo|infindo"
                r"|contrabando|incluindo|excluindo|dependendo|considerando)\b|sendo\s+que\b|tendo\s+em\s+vista\b)"
                r"\w+(?:ando|endo|indo)\b", re.I),
     "Gerúndio depois de vírgula encadeia outra ação sem dizer a relação (ao mesmo tempo? depois? "
     "por causa?). Use uma frase nova com o verbo conjugado."),
    *[("decalque-do-ingles", CONSULTIVA, re.compile(r"\b(?:" + pattern + r")\b", re.I), message)
      for pattern, message in DECALQUES],
    *[("locucao-verbal", CONSULTIVA, re.compile(r"\b" + pattern, re.I), message)
      for pattern, message in LOCUCOES_VERBAIS],
    ("palavra-ambigua", CONSULTIVA,
     re.compile(r"\bexclu(?:ir|i|is|ímos|em|o|a|as|am|amos|iu|íram|iram|ía|íam|irá|irão|iria|iriam|indo|ído|ída"
                r"|ídos|ídas|isse|issem)\b", re.I),
     "'Excluir' tem dois sentidos: apagar ('exclua o arquivo') e deixar de fora ('exclua o arquivo do "
     "pacote'). Use 'apagar' ou 'não incluir'."),
    ("ser-estar", CONSULTIVA,
     re.compile(r"\b(?:é|são|era|eram|foi|foram|será|serão|seja|sejam)\s+(?:\w+mente\s+)?" + ESTADOS + r"\b", re.I),
     "Um estado atual pede 'estar' ('o servidor está indisponível'). 'Ser' descreve o que a coisa é sempre."),
    ("travessao", CONSULTIVA,
     re.compile(r"(?<=\S)\s*—\s*(?=\S)|(?<=\S)\s+–\s+(?=\S)"),
     "O travessão junta duas ideias (frase encadeada). Considere duas frases, dois-pontos ou parênteses."),
]

# Regras opcionais (`--ativar NOME`). Não são regras do STE: são regras da
# casa que costumam acompanhar reescritas de documentação.
OPTIONAL_RULES = [
    ("historico", OBRIGATORIA,
     re.compile(r"\b(?:não mais|já não|anteriormente|antigamente|atualmente|hoje em dia|originalmente"
                r"|costumavam?|deixou de|deixaram de|passou a|passaram a"
                r"|(?:foi|foram) (?:renomead|substituíd|removid|alterad|adicionad|modificad|excluíd)[oa]s?"
                r"|(?:na|numa|em uma) versão anterior|em versões anteriores)\b", re.I),
     "Histórico de mudanças numa descrição do estado atual. Descreva o que é, não o que mudou."),
]

# Regras calculadas fora da tabela RULES.
DERIVED_RULES = {"frase-longa", "rotacao-de-sinonimos", "conjuncao-pendente", "exemplo-sem-falha",
                 "diretiva-invalida"}
KNOWN_RULES = {rule[0] for rule in RULES} | {rule[0] for rule in OPTIONAL_RULES} | DERIVED_RULES

# Uma palavra, um significado: grupos de verbos que costumam se alternar para
# a mesma ação. Só entram verbos de fato intercambiáveis. Erro, falha e defeito
# são conceitos diferentes e ficam de fora.
SYNONYM_GROUPS = [
    ("verificar", "conferir", "checar", "validar", "confirmar"),
    ("excluir", "remover", "apagar", "deletar", "eliminar"),
    ("iniciar", "começar"),
    ("parar", "interromper"),
    ("encerrar", "finalizar"),
    ("mostrar", "exibir"),
    ("usar", "utilizar", "empregar"),
    ("corrigir", "consertar", "arrumar"),
    ("enviar", "mandar", "transmitir", "remeter"),
    ("obter", "pegar"),
    ("alterar", "modificar", "mudar"),
    ("salvar", "gravar"),
]

# Formas irregulares que o gerador de conjugação não produz.
EXTRA_FORMS = {
    "excluir": {"exclui", "excluis", "excluí", "excluímos", "excluíste", "excluíram", "excluía", "excluías",
                "excluíamos", "excluíam", "excluíra", "excluído", "excluída", "excluídos", "excluídas",
                "excluíssemos"},
    "conferir": {"confiro", "confira", "confiras", "confiramos", "confiram"},
    "pegar": {"pego", "pegos", "pegas"},
}
# Verbos irregulares demais para o gerador: lista completa.
FULL_FORMS = {
    "obter": {"obter", "obtenho", "obténs", "obtém", "obtemos", "obtêm", "obtive", "obtiveste", "obteve",
              "obtivemos", "obtiveram", "obtinha", "obtinhas", "obtínhamos", "obtinham", "obtivera",
              "obterei", "obterá", "obteremos", "obterão", "obteria", "obteriam", "obtenha", "obtenhas",
              "obtenhamos", "obtenham", "obtivesse", "obtivessem", "obtiver", "obtiverem", "obtendo",
              "obtido", "obtida", "obtidos", "obtidas", "obtê"},
}
# Formas que colidem com palavras mais comuns: "para" (preposição), "salvo se"
# (exceto se), "parado" (adjetivo de estado).
EXCLUDED_FORMS = {
    "parar": {"para", "paras", "parado", "parada", "parados", "paradas"},
    "salvar": {"salvo"},
}
# Formas verbais que também são substantivos ("o uso", "o envio").
NOUN_HOMOGRAPHS = {"uso", "usos", "envio", "envios", "começo", "começos", "conserto", "consertos",
                   "emprego", "empregos", "empregado", "empregados", "empregada", "empregadas",
                   "cheque", "cheques", "mostra", "mostras"}

MAX_WORDS = 27  # descrições: 25 do STE × 1,07 do português, para cima. O de instruções é 22, mas o linter não sabe distinguir.
MAX_WORDS_STRICT = 22  # 20 do STE × 1,07, para cima. Mensagens de erro (`mensagens` do rust) são texto do modo Estrito

CODE_FENCE = re.compile(r"^(```|~~~)")
INLINE_CODE = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)")  # N crases fecham N crases (CommonMark)
LIST_ITEM_START = re.compile(
    r"^(?P<indent> {0,3})(?P<marker>[-*+]|[0-9]+[.)])(?P<gap> +)(?P<body>.*)$"
)
CONJUNCTION_END = re.compile(r"\b(?:e|ou)\s*$", re.I)
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")

# Mascaramento: cada trecho mantém o comprimento, então as colunas ficam exatas.
INLINE_MATH = re.compile(r"(?<![\\$\w])\$(?=[^\s$])[^$\n]*?(?<=[^\s\\])\$(?![\d$])")
LINK_TARGET = re.compile(r"\]\([^)\s]*\)")
LINK_REF = re.compile(r"\]\[[^\]]*\]")
HTML_COMMENT_INLINE = re.compile(r"<!--.*?-->")
# Um trecho entre aspas é uma menção (um exemplo, um rótulo, uma citação), não prosa do autor.
QUOTE = re.compile(r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»')
# <!-- pts-lint: deve-falhar [regra ...] --> ... <!-- pts-lint: fim -->
DIRECTIVE = re.compile(r"<!--\s*pts-lint:\s*(\S+)(.*?)-->")
FORMAT_ARG = re.compile(r"\{[^{}\s]*\}")  # {}, {x}, {path:?}, {:>10.6}
LINK_DEF = re.compile(r"^ {0,3}\[[^\]]+\]:\s*\S")
HEADING = re.compile(r"^ {0,3}#{1,6}(?:\s+|$)")
BLOCKQUOTE = re.compile(r"^ {0,3}(?:>\s?)+")
WORD = re.compile(r"\w")
# Uma frase termina em . ! ? ou … (mais aspas, parênteses ou ênfase de
# fechamento), depois espaço, depois algo que pode abrir uma frase.
SENTENCE_END = re.compile(r"[.!?…][\"'”’»)\]*_]*\s+(?=[\"'“‘«(\[*_]*[A-ZÀ-ÖØ-ÞΑ-Ω])")
# "etc." fica de fora: antes de uma maiúscula, ele também fecha a frase.
ABBREVIATIONS = {"ex", "p", "pp", "obs", "pág", "págs", "aprox", "fig", "figs", "cf", "sr", "sra",
                 "srs", "dr", "dra", "prof", "profa", "art", "arts", "inc", "cap", "caps", "vol", "ed",
                 "i.e", "e.g", "vs", "máx", "mín", "núm", "nº", "n", "séc", "tel", "av", "eq", "al",
                 "id", "ib", "op", "cit", "ltda", "cia"}

RUST_PARTS = {"docs", "comentarios", "mensagens", "literais"}
MESSAGE_CALLEES = {
    "panic!", "assert!", "assert_eq!", "assert_ne!", "debug_assert!", "debug_assert_eq!",
    "debug_assert_ne!", "unreachable!", "unimplemented!", "todo!", "expect", "expect_err",
    "println!", "eprintln!", "print!", "eprint!", "format!", "write!", "writeln!",
    "bail!", "anyhow!", "ensure!", "error!", "warn!", "info!",
}
RAW_STRING_START = re.compile(r'(?:b|c)?r(?P<hashes>#*)"')
# Uma linha `//` que termina como código e contém pontuação de código.
COMMENTED_OUT_CODE = re.compile(r"^(?=.*(?:[=(]|::|->)).*[;{}]\s*$")


def _conjugate(infinitive):
    """Formas flexionadas de um verbo regular (sem a 2ª pessoa do plural)."""
    stem, theme = infinitive[:-2], infinitive[-2]
    last = stem[-1]
    if theme == "a":
        soft = stem[:-1] + {"c": "qu", "g": "gu", "ç": "c"}.get(last, last)  # antes de "e"
        endings = [
            (stem, ("o", "as", "a", "amos", "am", "aste", "ou", "aram", "ava", "avas", "ávamos", "avam",
                   "ara", "aras", "áramos", "arei", "arás", "ará", "aremos", "arão", "aria", "arias",
                   "aríamos", "ariam", "asse", "asses", "ássemos", "assem", "ar", "ares", "armos", "arem",
                   "ando", "ado", "ada", "ados", "adas", "á")),
            (soft, ("ei", "e", "es", "emos", "em")),
        ]
    else:
        v = theme  # "e" ou "i"
        accented = "ê" if v == "e" else "í"
        hard = stem[:-1] + {"c": "ç", "g": "j"}.get(last, last)  # antes de "a" e "o"
        endings = [
            (stem, ("es", "e", v + "mos", "em", "i", v + "ste", "eu" if v == "e" else "iu", v + "ram",
                   "ia", "ias", "íamos", "iam", v + "ra", v + "ras", accented + "ramos", v + "rei",
                   v + "rás", v + "rá", v + "remos", v + "rão", v + "ria", v + "rias", v + "ríamos",
                   v + "riam", v + "sse", v + "sses", accented + "ssemos", v + "ssem", v + "r", v + "res",
                   v + "rmos", v + "rem", v + "ndo", "ido", "ida", "idos", "idas",
                   "ê" if v == "e" else "i")),
            (hard, ("o", "a", "as", "amos", "am")),
        ]
    return {s + ending for s, group in endings for ending in group}


def _verb_forms(infinitive):
    forms = FULL_FORMS.get(infinitive) or _conjugate(infinitive)
    forms = (forms | EXTRA_FORMS.get(infinitive, set())) - EXCLUDED_FORMS.get(infinitive, set())
    return forms


def _verb_re(infinitive):
    forms = sorted(_verb_forms(infinitive), key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(map(re.escape, forms)) + r")\b", re.I)


VERB_PATTERNS = {verb: _verb_re(verb) for group in SYNONYM_GROUPS for verb in group}

# A rotação de sinônimos trata de *verbos*. Um determinante antes de um
# homógrafo marca um substantivo ("o uso", "cada envio"), e "de" depois também
# ("uso de memória"). Um hífen antes marca uma palavra composta ("pré-envio").
NOUN_CUE = re.compile(r"\b(?:o|a|os|as|um|uma|uns|umas|este|esta|estes|estas|esse|essa|esses|essas|aquele"
                      r"|aquela|cada|todo|toda|todos|todas|seu|sua|seus|suas|meu|minha|nosso|nossa|do|da|dos"
                      r"|das|no|na|nos|nas|ao|à|aos|às|pelo|pela|pelos|pelas|num|numa|deste|desta|desse|dessa"
                      r"|neste|nesta|nesse|nessa|primeiro|primeira|último|última|mesmo|mesma|outro|outra"
                      r"|nenhum|nenhuma|algum|alguma|qualquer|novo|nova|próprio|própria|único|única|bom|boa"
                      r"|mau|má|cujo|cuja)\s+$", re.I)
NOUN_AFTER = re.compile(r"^(?:\s+d[eoa]s?\b|\s*[:)\]]|\s*$)", re.I)


def _verb_match(pattern, text):
    """Primeira ocorrência de um membro do grupo de sinônimos que se lê como verbo."""
    for m in pattern.finditer(text):
        before = text[:m.start()]
        if before.endswith("-"):
            continue
        if m.group(0).lower() in NOUN_HOMOGRAPHS and (NOUN_CUE.search(before)
                                                      or NOUN_AFTER.match(text[m.end():])):
            continue
        return m
    return None


def _leading_spaces(line):
    return len(line) - len(line.lstrip(" "))


def _is_list_continuation(line, content_indent):
    if not line.strip():
        return True
    if LIST_ITEM_START.match(line):
        return False
    return _leading_spaces(line) >= content_indent


def _split_table_row(line):
    """Devolve as células aparadas de uma linha de tabela e suas colunas de origem (base zero).

    Uma barra vertical precisa separar ao menos duas células. Barras escapadas
    ficam na célula. A função implementa de propósito só a forma comum de
    tabela Markdown. Isso basta para distinguir uma tabela de uma prosa que
    por acaso contém uma barra vertical.
    """
    left = len(line) - len(line.lstrip())
    right = len(line.rstrip())
    content = line[left:right]
    if "|" not in content:
        return None
    if content.startswith("|"):
        content = content[1:]
        left += 1
    if content.endswith("|"):
        content = content[:-1]
    raw_cells = re.split(r"(?<!\\)\|", content)
    if len(raw_cells) < 2:
        return None

    cells = []
    column = left
    for raw_cell in raw_cells:
        leading = len(raw_cell) - len(raw_cell.lstrip())
        cells.append((raw_cell.strip(), column + leading))
        column += len(raw_cell) + 1
    return cells


def _markdown_table_cells(lines):
    """Mapeia as linhas de tabelas Markdown comuns para suas células de prosa.

    A linha separadora ancora a detecção, então uma prosa com barra vertical
    não vira tabela. Os dois estilos (com e sem barra inicial) são aceitos
    quando o cabeçalho e o corpo têm o mesmo número de células.
    """
    table_cells = {}
    index = 1
    while index < len(lines):
        separator = _split_table_row(lines[index])
        header = _split_table_row(lines[index - 1])
        if (not separator or not header or len(separator) != len(header)
                or not all(TABLE_SEPARATOR_CELL.fullmatch(cell)
                           for cell, _ in separator)):
            index += 1
            continue

        table_cells[index - 1] = header
        table_cells[index] = []
        index += 1
        while index < len(lines):
            row = _split_table_row(lines[index])
            if not row or len(row) != len(separator):
                break
            table_cells[index] = row
            index += 1
    return table_cells


def _dangling_conjunction_findings(text, filename):
    lines = text.splitlines()
    findings = []
    in_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if CODE_FENCE.match(stripped):
            in_fence = not in_fence
            index += 1
            continue
        if in_fence:
            index += 1
            continue
        start = LIST_ITEM_START.match(line)
        if not start:
            index += 1
            continue

        content_indent = (len(start.group("indent"))
                          + len(start.group("marker"))
                          + len(start.group("gap")))
        item_lines = [(index, start.group("body"))]
        next_index = index + 1
        item_fence = False
        while next_index < len(lines):
            candidate = lines[next_index]
            candidate_stripped = candidate.strip()
            if CODE_FENCE.match(candidate_stripped):
                # Delimitadores de bloco marcam estado. Não são linhas com conteúdo.
                item_fence = not item_fence
                next_index += 1
                continue
            if item_fence:
                next_index += 1
                continue
            if not _is_list_continuation(candidate, content_indent):
                break
            item_lines.append((next_index, candidate))
            next_index += 1

        meaningful = []
        for line_index, item_line in item_lines:
            # Trechos de código viram operandos neutros, e o conteúdo deles é ignorado.
            cleaned = INLINE_CODE.sub(" CODE ", item_line).strip()
            if cleaned:
                meaningful.append((line_index, cleaned))
        if meaningful:
            end_line_index, end_line = meaningful[-1]
            conjunction = CONJUNCTION_END.search(end_line)
        else:
            end_line_index, end_line, conjunction = None, None, None
        if conjunction:
            if end_line_index == index:
                finding_line = index + 1
                finding_col = start.start("marker") + 1
            else:
                raw_end_line = next(
                    raw for line_index, raw in item_lines
                    if line_index == end_line_index
                )
                masked_end_line = INLINE_CODE.sub(
                    lambda match: " " * len(match.group(0)), raw_end_line
                )
                raw_conjunction = CONJUNCTION_END.search(masked_end_line)
                finding_line = end_line_index + 1
                finding_col = raw_conjunction.start() + 1 if raw_conjunction else 1
            findings.append({
                "arquivo": filename,
                "linha": finding_line,
                "coluna": finding_col,
                "regra": "conjuncao-pendente",
                "nivel": OBRIGATORIA,
                "trecho": end_line,
                "mensagem": "Item de lista termina com conjunção coordenativa. Complete o item ou "
                            "junte-o ao item seguinte.",
            })
        index = next_index
    return findings


# ---------------------------------------------------------------------------
# Extração da prosa. Um bloco é uma lista de linhas de origem
# (lineno, col0, content) de um só tipo. `_paragraphs` corta um bloco em
# parágrafos feitos dessas peças.
# ---------------------------------------------------------------------------

def _mask(text, kind):
    """Neutraliza trechos que não são prosa e mantém o comprimento (e, assim, as colunas)."""
    def placeholder(match):
        return "X" + " " * (len(match.group(0)) - 1)

    def blank(match):
        return " " * len(match.group(0))

    text = INLINE_CODE.sub(placeholder, text)
    text = INLINE_MATH.sub(placeholder, text)
    if kind in ("mensagens", "literais"):
        text = FORMAT_ARG.sub(placeholder, text)
    text = LINK_TARGET.sub(blank, text)
    text = LINK_REF.sub(blank, text)
    text = HTML_COMMENT_INLINE.sub(blank, text)
    return text.replace("[", " ").replace("]", " ")


def _mask_quotes(text):
    """Troca cada menção entre aspas por uma palavra só e mantém as colunas.

    Se a citação termina em . ! ? ou …, esse sinal e a aspa de fechamento ficam,
    então uma frase citada continua a fechar a frase.
    """
    def placeholder(match):
        quoted = match.group(0)
        if len(quoted) > 2 and quoted[-2] in ".!?…":
            return "X" + " " * (len(quoted) - 3) + quoted[-2:]
        return "X" + " " * (len(quoted) - 1)

    return QUOTE.sub(placeholder, text)


def _regions(text):
    """Lê as diretivas `deve-falhar` e `fim`.

    Devolve as regiões ({inicio, fim, coluna, esperadas}) e os problemas
    (linha, coluna, mensagem) das diretivas inválidas.
    """
    regions, problems, current = [], [], None
    fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if CODE_FENCE.match(line.strip()):
            fence = not fence
        if fence:
            continue  # uma diretiva dentro de um bloco de código é só um exemplo
        for m in DIRECTIVE.finditer(line):
            name, args, col = m.group(1), m.group(2).strip(), m.start() + 1
            if name == "deve-falhar":
                if current:
                    problems.append((lineno, col, "Região 'deve-falhar' aberta dentro de outra."))
                    continue
                expected = set(args.replace(",", " ").split())
                if expected - KNOWN_RULES:
                    problems.append((lineno, col, "Regra desconhecida na diretiva: "
                                     + ", ".join(sorted(expected - KNOWN_RULES)) + "."))
                current = {"inicio": lineno, "coluna": col, "esperadas": expected & KNOWN_RULES}
            elif name == "fim":
                if not current:
                    problems.append((lineno, col, "Diretiva 'fim' sem 'deve-falhar' antes."))
                    continue
                current["fim"] = lineno
                regions.append(current)
                current = None
            else:
                problems.append((lineno, col, f"Diretiva desconhecida: {name}. Conhecidas: deve-falhar, fim."))
    if current:
        problems.append((current["inicio"], current["coluna"], "Região 'deve-falhar' sem 'fim'."))
    return regions, problems


def _paragraphs(lines):
    """Corta as linhas de um bloco Markdown em parágrafos de peças (lineno, col0, text).

    Uma linha em branco, um título, o início de um item de lista, uma célula de
    tabela ou uma construção ignorada termina o parágrafo. Linhas quebradas se
    juntam num só parágrafo.
    """
    contents = [content for _, _, content in lines]
    table = _markdown_table_cells(contents)
    paragraphs, current = [], []
    fence = math = html = False
    quoted = False  # o parágrafo atual está dentro de uma citação (>)

    def flush():
        nonlocal quoted
        if current:
            paragraphs.append(list(current))
            current.clear()
        quoted = False

    for index, (lineno, col0, raw) in enumerate(lines):
        stripped = raw.strip()
        if fence:
            fence = not CODE_FENCE.match(stripped)
            continue
        if math:
            math = "$$" not in stripped
            continue
        if html:
            html = "-->" not in stripped
            continue
        if CODE_FENCE.match(stripped):
            flush()
            fence = True
            continue
        if stripped.startswith("$$"):
            flush()
            math = "$$" not in stripped[2:]
            continue
        if stripped.startswith("<!--"):
            flush()
            html = "-->" not in stripped
            continue
        if not stripped:
            flush()
            continue
        if index in table:
            flush()
            for cell, column in table[index]:
                if cell:
                    paragraphs.append([(lineno, col0 + column, cell)])
            continue
        if LINK_DEF.match(raw):
            flush()
            continue
        heading = HEADING.match(raw)
        if heading:
            flush()
            paragraphs.append([(lineno, col0 + heading.end(), raw[heading.end():].rstrip())])
            continue
        quote = BLOCKQUOTE.match(raw)
        if quote:
            # Uma citação interrompe o parágrafo anterior ("**Antes:**" e depois "> texto").
            if current and not quoted:
                flush()
            col0 += quote.end()
            raw = raw[quote.end():]
        item = LIST_ITEM_START.match(raw)
        if item:
            flush()
            current.append((lineno, col0 + item.start("body"), item.group("body").rstrip()))
            quoted = bool(quote)
            continue
        lead = len(raw) - len(raw.lstrip())
        current.append((lineno, col0 + lead, raw.strip()))
        quoted = quoted or bool(quote)
    flush()
    return paragraphs


def _markdown_blocks(text):
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":  # front matter YAML
        for index in range(1, len(lines)):
            if lines[index].strip() in ("---", "..."):
                start = index + 1
                break
    return [{"kind": "markdown",
             "lines": [(n + 1, 0, lines[n]) for n in range(start, len(lines))]}]


def _unescape_rust_string(raw, raw_start, is_raw, pos):
    """Divide o corpo de um literal de string em linhas (lineno, col0, text).

    `\\n` e quebras de linha reais quebram linhas. Uma continuação com barra
    invertida e quebra de linha junta as linhas (e descarta o espaço inicial
    da linha seguinte, como faz o rustc). Os outros escapes viram um só
    caractere, então as colunas depois de um escape são aproximadas.
    """
    out, text, begin = [], [], None
    k = 0

    def end_line():
        if begin is not None or text:
            lineno, col = pos(raw_start + (begin if begin is not None else k))
            out.append((lineno, col, "".join(text)))

    while k < len(raw):
        char = raw[k]
        if begin is None:
            begin = k
        if not is_raw and char == "\\" and k + 1 < len(raw):
            nxt = raw[k + 1]
            if nxt == "\n":
                k += 2
                while k < len(raw) and raw[k] in " \t":
                    k += 1
                continue
            if nxt == "n":
                end_line()
                text, begin = [], None
                k += 2
                continue
            if nxt == "u":
                close = raw.find("}", k)
                text.append("?")
                k = close + 1 if close > 0 else k + 2
                continue
            text.append(" " if nxt == "t" else nxt)
            k += 2
            continue
        if char == "\n":
            end_line()
            text, begin = [], None
            k += 1
            continue
        text.append(char)
        k += 1
    end_line()
    return out


def _rust_blocks(src, parts):
    """Lê código Rust e devolve blocos de prosa: comentários, docs e literais de string."""
    line_starts = [0] + [k + 1 for k, char in enumerate(src) if char == "\n"]

    def pos(index):
        line = bisect.bisect_right(line_starts, index) - 1
        return line + 1, index - line_starts[line]

    blocks, records = [], []
    stack, prev = [], [None, None]  # função chamada por colchete aberto, dois últimos tokens
    i, n = 0, len(src)

    def is_ident_char(char):
        return char.isalnum() or char == "_"

    def add_string(content_start, raw, is_raw):
        callee = stack[-1] if stack else None
        kind = "mensagens" if callee in MESSAGE_CALLEES else "literais"
        words = len([t for t in raw.split() if WORD.search(t)])
        if (kind == "mensagens" and "mensagens" in parts) or ("literais" in parts and words >= 3):
            blocks.append({"kind": kind, "lines": _unescape_rust_string(raw, content_start, is_raw, pos)})

    while i < n:
        char = src[i]
        if src.startswith("//", i):
            end = src.find("\n", i)
            end = n if end < 0 else end
            text = src[i:end]
            lineno, col = pos(i)
            standalone = not src[line_starts[lineno - 1]:i].strip()
            if text.startswith("///") and not text.startswith("////"):
                kind, prefix = "outer", 3
            elif text.startswith("//!"):
                kind, prefix = "inner", 3
            else:
                kind, prefix = "line", 2
            content = text[prefix:]
            if content.startswith(" "):
                content, prefix = content[1:], prefix + 1
            records.append((kind, lineno, col + prefix, content.rstrip(), standalone, col))
            i = end
            continue
        if src.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif src.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            doc = (src.startswith("/*!", i)
                   or (src.startswith("/**", i) and not src.startswith("/***", i)
                       and not src.startswith("/**/", i)))
            body_start = i + (3 if doc else 2)
            lines, k = [], body_start
            for piece in src[body_start:max(body_start, j - 2)].split("\n"):
                lineno, col = pos(k)
                stripped = piece.lstrip()
                lead = len(piece) - len(stripped)
                if stripped.startswith("*"):
                    stripped = stripped[1:]
                    lead += 1
                    if stripped.startswith(" "):
                        stripped, lead = stripped[1:], lead + 1
                lines.append((lineno, col + lead, stripped.rstrip()))
                k += len(piece) + 1
            kind = "docs" if doc else "comentarios"
            if kind in parts:
                blocks.append({"kind": kind, "lines": lines})
            i = j
            continue
        if char in "bcr" and (i == 0 or not is_ident_char(src[i - 1])):
            raw = RAW_STRING_START.match(src, i)
            if raw:
                close = '"' + raw.group("hashes")
                end = src.find(close, raw.end())
                end = n if end < 0 else end
                add_string(raw.end(), src[raw.end():end], True)
                i = end + len(close)
                continue
            if char in "bc" and src.startswith('"', i + 1):
                i += 1
                char = '"'
        if char == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            add_string(i + 1, src[i + 1:j], False)
            i = j + 1
            prev = [prev[1], ("string",)]
            continue
        if char == "'":
            if src.startswith("\\", i + 1):
                close = src.find("'", i + 3)
                i = n if close < 0 else close + 1
            elif i + 2 < n and src[i + 2] == "'":
                i += 3
            else:
                i += 1  # um lifetime ou um rótulo
            continue
        if char.isalpha() or char == "_":
            j = i
            while j < n and is_ident_char(src[j]):
                j += 1
            prev = [prev[1], ("ident", src[i:j])]
            i = j
            continue
        if char in "([{":
            callee = None
            if prev[1] and prev[1][0] == "ident":
                callee = prev[1][1]
            elif prev[1] == ("bang",) and prev[0] and prev[0][0] == "ident":
                callee = prev[0][1] + "!"
            stack.append(callee)
            prev = [prev[1], ("open",)]
        elif char in ")]}":
            if stack:
                stack.pop()
            prev = [prev[1], ("close",)]
        elif char == "!":
            prev = [prev[1], ("bang",)]
        elif not char.isspace():
            prev = [prev[1], ("punct", char)]
        i += 1

    # Linhas de comentário isoladas e consecutivas do mesmo tipo formam um bloco.
    groups = []
    for kind, lineno, col, content, standalone, indent in records:
        last = groups[-1] if groups else None
        if (last and standalone and last["standalone"] and last["kind"] == kind
                and lineno == last["lines"][-1][0] + 1
                and (kind != "line" or indent == last["indent"])):
            last["lines"].append((lineno, col, content))
        else:
            groups.append({"kind": kind, "standalone": standalone, "indent": indent,
                           "lines": [(lineno, col, content)]})
    for group in groups:
        kind = "comentarios" if group["kind"] == "line" else "docs"
        if kind not in parts:
            continue
        lines = group["lines"]
        if kind == "comentarios":
            lines = [(lineno, col, "" if COMMENTED_OUT_CODE.match(content) else content)
                     for lineno, col, content in lines]
        blocks.append({"kind": kind, "lines": lines})
    blocks.sort(key=lambda block: block["lines"][0][:2] if block["lines"] else (0, 0))
    return blocks


def _sentence_spans(text):
    """Devolve (início, fim) de cada frase de um parágrafo, sem cortar em abreviações."""
    start = 0
    for match in SENTENCE_END.finditer(text):
        word = text[:match.start() + 1].split()[-1].lower().strip("(\"'“‘«*_").rstrip(".")
        if word in ABBREVIATIONS:
            continue
        yield start, match.start() + 1
        start = match.end()
    yield start, len(text)


def lint(text, filename="<stdin>", lang=None, parts=None, max_words=MAX_WORDS,
         max_words_strict=MAX_WORDS_STRICT, enabled=(), read_quotes=False):
    """Analisa um documento. Devolve (achados, total_de_palavras)."""
    if lang is None:
        lang = "rust" if filename.endswith(".rs") else "markdown"
    if lang == "rust":
        blocks = _rust_blocks(text, set(parts or ("docs", "comentarios")))
    else:
        blocks = _markdown_blocks(text)
    rules = RULES + [rule for rule in OPTIONAL_RULES if rule[0] in enabled]
    regions, problems = _regions(text)

    def region_of(line):
        return next((r for r in regions if r["inicio"] < line < r["fim"]), None)

    findings = []
    words_total = 0
    # primeira ocorrência de cada membro de grupo de sinônimos: (grupo, verbo) -> (linha, coluna, trecho)
    seen_synonyms = {}

    def finding(line, col, rule, level, match, message, **extra):
        findings.append({"arquivo": filename, "linha": line, "coluna": col, "regra": rule,
                         "nivel": level, "trecho": match, "mensagem": message, **extra})

    for block in blocks:
        kind = block["kind"]
        cap = max_words_strict if kind == "mensagens" else max_words
        for pieces in _paragraphs(block["lines"]):
            raw = " ".join(content for _, _, content in pieces)
            masked = " ".join(_mask(content, kind) for _, _, content in pieces)
            if not read_quotes:
                masked = _mask_quotes(masked)
            starts, offset = [], 0
            for _, _, content in pieces:
                starts.append(offset)
                offset += len(content) + 1

            def at(index):
                piece = bisect.bisect_right(starts, index) - 1
                lineno, col0, _ = pieces[piece]
                return lineno, col0 + index - starts[piece] + 1

            for rule_id, level, pattern, message in rules:
                for m in pattern.finditer(masked):
                    finding(*at(m.start()), rule_id, level, raw[m.start():m.end()].strip(), message)
            for gi, group in enumerate(SYNONYM_GROUPS):
                for verb in group:
                    m = _verb_match(VERB_PATTERNS[verb], masked)
                    # Um exemplo que deve falhar não conta para a escolha de termos do documento.
                    if m and not region_of(at(m.start())[0]):
                        spot = (*at(m.start()), m.group(0))
                        if (gi, verb) not in seen_synonyms or spot < seen_synonyms[(gi, verb)]:
                            seen_synonyms[(gi, verb)] = spot
            for begin, end in _sentence_spans(masked):
                sentence = masked[begin:end]
                n = len([token for token in sentence.split() if WORD.search(token)])
                words_total += n
                if n > cap:
                    original = raw[begin:end]
                    lead = len(original) - len(original.lstrip())
                    excerpt = " ".join(original.split())
                    finding(*at(begin + lead), "frase-longa", OBRIGATORIA, f"{n} palavras",
                            f"A frase tem {n} palavras (limite {cap}). Divida-a.",
                            excerto=excerpt[:80] + ("…" if len(excerpt) > 80 else ""))
        # Blocos de rustdoc e de string são pequenos documentos Markdown.
        virtual = "\n".join(content for _, _, content in block["lines"])
        for f in _dangling_conjunction_findings(virtual, filename):
            lineno, col0, _ = block["lines"][f["linha"] - 1]
            f["linha"], f["coluna"] = lineno, col0 + f["coluna"]
            findings.append(f)
    # rotação de sinônimos: marca cada membro depois do primeiro, na primeira ocorrência dele
    for gi, group in enumerate(SYNONYM_GROUPS):
        present = [(seen_synonyms[(gi, v)], v) for v in group if (gi, v) in seen_synonyms]
        if len(present) > 1:
            present.sort()  # ordem do documento
            first_verb = present[0][1]
            for (lineno, col, match), verb in present[1:]:
                finding(lineno, col, "rotacao-de-sinonimos", OBRIGATORIA, match,
                        f"'{verb}' e '{first_verb}' nomeiam a mesma ação. Escolha um e use-o sempre.")

    # Os achados de uma região 'deve-falhar' são esperados: eles saem do relatório. A região
    # falha se não tiver nenhum achado obrigatório ou se faltar uma das regras esperadas.
    inside = {id(r): [] for r in regions}
    outside = []
    for f in findings:
        region = region_of(f["linha"])
        (inside[id(region)] if region else outside).append(f)
    findings = outside
    for region in regions:
        found = inside[id(region)]
        missing = region["esperadas"] - {f["regra"] for f in found}
        if missing or not any(f["nivel"] == OBRIGATORIA for f in found):
            detail = ("faltam: " + ", ".join(sorted(missing))) if missing else "nenhum achado obrigatório"
            finding(region["inicio"], region["coluna"], "exemplo-sem-falha", OBRIGATORIA, detail,
                    "O exemplo marcado com 'deve-falhar' não falhou como esperado. Corrija o exemplo ou a "
                    "lista de regras da diretiva.")
    for lineno, col, message in problems:
        finding(lineno, col, "diretiva-invalida", OBRIGATORIA, "pts-lint", message)
    findings.sort(key=lambda f: (f["linha"], f["coluna"]))
    return findings, words_total


def report(findings, words_total, as_json, hard_count, baseline):
    rate = round(len(findings) * 100 / words_total, 1) if words_total else 0.0
    if as_json:
        print(json.dumps({"violacoes": findings, "total": len(findings),
                          "obrigatorias": hard_count, "linha_de_base": baseline,
                          "palavras": words_total, "por_100_palavras": rate},
                         indent=2, ensure_ascii=False))
        return
    for f in findings:
        detail = f"{f['trecho']}: {f['excerto']}" if "excerto" in f else f["trecho"]
        print(f"{f['arquivo']}:{f['linha']}:{f['coluna']} {f['regra']}: {f['mensagem']} [{detail}]")
    print(f"\n{len(findings)} violações ({hard_count} obrigatórias, linha de base {baseline}), "
          f"{words_total} palavras, {rate} por 100 palavras")
    print("Ressalvas e modalidade (pode, poderia, talvez, deve ter) nunca são marcadas: "
          "o grau de certeza é conteúdo.")


def report_summary(per_file):
    """Uma linha por arquivo, com o maior número de violações obrigatórias primeiro."""
    rows = sorted(per_file, key=lambda row: (-row[1], -row[2], row[0]))
    print(f"{'obrig':>5} {'cons':>5} {'palavras':>8}  arquivo")
    for path, hard, advisory, words in rows:
        print(f"{hard:>5} {advisory:>5} {words:>8}  {path}")


def _rules_of(text, **options):
    return [f["regra"] for f in lint(text, **options)[0]]


def selftest():
    bad = ("O painel é removido; inicie o job. "
           "Realize uma análise do log robusto. "
           "Vamos estar enviando o relatório. "
           "O build tem falhado desde segunda.")
    findings, _ = lint(bad)
    rules = {f["regra"] for f in findings}
    for expected in ("ponto-e-virgula", "verbo-suporte", "adjetivo-de-marketing",
                     "voz-passiva", "gerundismo", "tempo-composto"):
        assert expected in rules, expected
    # ressalvas nunca são marcadas, inclusive modal + infinitivo composto
    findings, _ = lint("A requisição pode ter falhado. Pode ser um timeout. O disco talvez tenha enchido. "
                       "O servidor deve ter travado. O processo pode estar travando. O job teria falhado.")
    assert findings == [], findings
    # blocos de código ficam de fora
    findings, _ = lint("```\nx = a; y = b\n```")
    assert findings == []
    # todos os marcadores de lista aceitos, variações de caixa e espaço no fim
    findings, _ = lint(
        "- Confirme o alvo e\n"
        "* Registre o resultado OU  \n"
        "+ Feche o painel\n"
        "1. Inicie a tarefa e\n"
        "2) Pare a tarefa OU"
    )
    dangling = [f for f in findings if f["regra"] == "conjuncao-pendente"]
    assert len(dangling) == 4, dangling
    assert [f["linha"] for f in dangling] == [1, 2, 4, 5], dangling
    assert [f["coluna"] for f in dangling] == [1, 1, 1, 1], dangling
    assert all(f["nivel"] == OBRIGATORIA for f in dangling), dangling

    # linhas de continuação válidas e código isolado com quatro espaços são ignorados
    findings, _ = lint("  - Confirme o alvo e\n    registre o resultado.")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("- Confirme o alvo\n  e")
    dangling = [f for f in findings if f["regra"] == "conjuncao-pendente"]
    assert len(dangling) == 1 and dangling[0]["linha"] == 2, dangling
    assert dangling[0]["coluna"] == 3, dangling
    findings, _ = lint("    - código e")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("> - Confirme o alvo e\n> - Registre o resultado ou")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("- Abra isto e\n~~~\ncódigo e\n~~~")
    dangling = [f for f in findings if f["regra"] == "conjuncao-pendente"]
    assert len(dangling) == 1 and dangling[0]["linha"] == 1, dangling
    findings, _ = lint("```text\n- código e\n```")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)

    # marcadores com um e três espaços, e largura de continuação de lista numerada
    findings, _ = lint(" - Inicie a tarefa e\n   registre o resultado.")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("-  Inicie a tarefa e\n   registre o resultado.")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("-\tInicie a tarefa e")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("   - Inicie a tarefa e", filename="fixture.md")
    dangling = [f for f in findings if f["regra"] == "conjuncao-pendente"]
    assert len(dangling) == 1 and dangling[0]["coluna"] == 4, dangling
    assert dangling[0]["arquivo"] == "fixture.md"
    assert dangling[0]["trecho"].endswith("e")
    assert "Complete o item" in dangling[0]["mensagem"]
    findings, _ = lint("100. Inicie a tarefa e\n  texto solto")
    dangling = [f for f in findings if f["regra"] == "conjuncao-pendente"]
    assert len(dangling) == 1, dangling
    findings, _ = lint("- Inicie a tarefa e.\n- Pare a tarefa ou,")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("- Inicie a tarefa e\n\n  registre o resultado.")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("- Item pai e\n  - Item filho ou")
    dangling = [f for f in findings if f["regra"] == "conjuncao-pendente"]
    assert [f["linha"] for f in dangling] == [1, 2], dangling

    # prosa comum, código inline e blocos de código são ignorados
    findings, _ = lint("O processo pode incluir etapas e")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("- Use `e` como rótulo")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint("- Combine `esquerda` e `direita`")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings), findings
    findings, _ = lint("~~~\n- código e\n~~~")
    assert not any(f["regra"] == "conjuncao-pendente" for f in findings)
    findings, _ = lint(("palavra " * 30).strip() + ".")
    assert any(f["regra"] == "frase-longa" for f in findings)
    # A sintaxe de tabela Markdown é leiaute, não prosa. Cada célula continua sendo analisada.
    short_cell = " ".join(f"termo{number}" for number in range(1, 27)) + "."
    for table in (
            "| Rótulo | Detalhe |\n"
            "| --- | --- |\n"
            f"| Claro | {short_cell} |",
            "Rótulo | Detalhe\n"
            "--- | ---\n"
            f"Claro | {short_cell}"):
        findings, words_total = lint(table)
        assert not any(f["regra"] == "frase-longa" for f in findings), findings
        assert words_total == 29, words_total
    long_cell = " ".join(f"termo{number}" for number in range(1, 29)) + "."
    findings, _ = lint(
        "| Rótulo | Detalhe |\n"
        "| --- | --- |\n"
        f"| Claro | {long_cell} |"
    )
    long_sentences = [f for f in findings if f["regra"] == "frase-longa"]
    assert len(long_sentences) == 1, long_sentences
    assert long_sentences[0]["trecho"] == "28 palavras", long_sentences

    # rotação de sinônimos: o segundo membro é marcado, e o primeiro é o que fica
    findings, _ = lint("Verifique o arquivo de configuração. Depois confira a saída. Confira duas vezes.")
    rot = [f for f in findings if f["regra"] == "rotacao-de-sinonimos"]
    assert len(rot) == 1 and "'conferir' e 'verificar'" in rot[0]["mensagem"], rot
    # um termo usado de forma consistente: nada a marcar
    findings, _ = lint("Verifique a configuração. Verifique a saída.")
    assert not any(f["regra"] == "rotacao-de-sinonimos" for f in findings)
    # substantivos, preposições e formas fixas não são rotação de verbos
    findings, _ = lint("Inicie o job. Registre o começo e cada começo. O uso de memória cresce. "
                       "Utilize o cache. Salve o arquivo, salvo se o disco estiver cheio. "
                       "Abra o arquivo para ler.")
    assert not any(f["regra"] == "rotacao-de-sinonimos" for f in findings), findings
    findings, _ = lint("Use o arquivo para testes. Interrompa o job.")
    assert not any(f["regra"] == "rotacao-de-sinonimos" for f in findings), findings
    findings, _ = lint("Pare o job para liberar memória. Interrompa o outro job.")
    assert any(f["regra"] == "rotacao-de-sinonimos" and f["trecho"] == "Interrompa" for f in findings), findings
    findings, _ = lint("Mostre o log. O servidor apresentou o erro 500. Obtenha o token. Recupere o backup.")
    assert not any(f["regra"] == "rotacao-de-sinonimos" for f in findings), findings
    findings, _ = lint("Corrija o bug. Depois consertou o valor. Conserte o erro.")
    assert any(f["regra"] == "rotacao-de-sinonimos" and f["trecho"] == "consertou" for f in findings), findings
    findings, _ = lint("Verifique-o. Depois confira-o.")
    assert any(f["regra"] == "rotacao-de-sinonimos" and f["trecho"] == "confira" for f in findings), findings
    findings, _ = lint("Exclua o arquivo. O arquivo excluído some. Remova o diretório.")
    assert [f["trecho"] for f in findings if f["regra"] == "rotacao-de-sinonimos"] == ["Remova"], findings
    # rótulo por arquivo
    findings, _ = lint("a; b", filename="x.md")
    assert findings[0]["arquivo"] == "x.md"

    # regras próprias do português
    assert "gerundismo" not in _rules_of("O processo pode estar travando.")
    assert "gerundismo" in _rules_of("Vou estar te ajudando agora.")
    assert "locucao-prolixa" in _rules_of("Use o cache a fim de reduzir a latência.")
    assert "locucao-prolixa" in _rules_of("Mude o cache no sentido de reduzir a latência.")
    assert "locucao-prolixa" not in _rules_of("Use 'eventualmente' no sentido de 'às vezes'.")
    rules = _rules_of("O job falhou, sendo que o log está vazio.")
    assert "locucao-prolixa" in rules and "gerundio-encadeado" not in rules, rules
    assert "locucao-prolixa" in _rules_of("Favor verificar o log.")
    assert "locucao-prolixa" in _rules_of("O servidor encontra-se indisponível.")
    assert "verbo-suporte" in _rules_of("Proceda à remoção do arquivo.")
    assert "verbo-suporte" in _rules_of("Faça uso do cache.")
    assert _rules_of("Proceda à remoção do arquivo.").count("verbo-suporte") == 1
    assert "verbo-suporte" in _rules_of("O agente deverá proceder ao consumo do artefato.")
    assert "verbo-suporte" not in _rules_of("Execute a função main. Faça o documento.")
    assert _rules_of("Faça menção ao erro.").count("verbo-suporte") == 1
    assert "passiva-sintetica" in _rules_of("Recomenda-se reiniciar o servidor.")
    assert "passiva-sintetica" not in _rules_of("Certifique-se de que o disco existe. Inscreva-se na lista.")
    assert "tempo-composto" not in _rules_of("O cliente tem chamado aberto. O teste tem resultado vazio.")
    assert "voz-passiva" in _rules_of("O arquivo foi removido pelo agente.")
    assert "voz-passiva" not in _rules_of("Os registros são dados sensíveis. O valor é válido. A rede é rápida.")
    assert "o-mesmo" in _rules_of("Abra o arquivo e edite o conteúdo do mesmo.")
    assert "o-mesmo" in _rules_of("Verifique se o mesmo está parado.")
    assert "o-mesmo" not in _rules_of("Use o mesmo arquivo. O mesmo vale para o cache. O valor é o mesmo.")
    assert "cadeia-de-preposicoes" in _rules_of("Abra a válvula de entrada do conjunto da bomba de combustível.")
    assert "cadeia-de-preposicoes" not in _rules_of("Abra o arquivo de configuração do servidor.")
    assert "cadeia-de-preposicoes" in _rules_of("Abra o arquivo de configuração do servidor de testes.")
    assert "cadeia-de-preposicoes" not in _rules_of(
        "A Lei nº 15.263, de 14 de novembro de 2025. Fora do VOLP e das regras de concordância. "
        "O dicionário de cerca de 900 palavras do ASD. O Manual de Comunicação da Secom do Senado. "
        "Copie para uma das pastas de skills do Claude.")
    assert "gerundio-encadeado" in _rules_of("O agente lê o arquivo, gerando um relatório.")
    assert "gerundio-encadeado" not in _rules_of("Clique em OK, quando terminar.")
    assert "decalque-do-ingles" in _rules_of("O backend eventualmente responde.")
    assert "decalque-do-ingles" in _rules_of("A API suporta JSON.")
    assert "decalque-do-ingles" not in _rules_of("Fale com o suporte. A seta aponta para cima.")
    assert _rules_of("Uma solução robusta e de ponta.").count("adjetivo-de-marketing") == 2
    assert "adjetivo-de-marketing" not in _rules_of("Criptografia de ponta a ponta. O resultado não intuitivo.")
    assert _rules_of("Funciona perfeitamente. É perfeitamente possível.").count("adjetivo-de-marketing") == 1

    # Uma frase quebrada em várias linhas é uma frase, informada onde começa.
    wrapped = ("Introdução.\nUm dois três quatro cinco seis sete\n"
               + "\n".join(["um dois três quatro cinco seis sete"] * 3) + ".\n\nCurta.")
    long_sentences = [f for f in lint(wrapped)[0] if f["regra"] == "frase-longa"]
    assert len(long_sentences) == 1, long_sentences
    assert (long_sentences[0]["linha"], long_sentences[0]["coluna"]) == (2, 1), long_sentences
    assert long_sentences[0]["trecho"] == "28 palavras", long_sentences
    assert long_sentences[0]["excerto"].startswith("Um dois"), long_sentences
    # abreviações não terminam frase, e a maiúscula depois delas não divide a frase
    assert lint("Veja p. ex. Burn para isso. Depois pare.")[1] == 8
    # código e fórmula inline contam como uma palavra, destinos de link não contam
    assert lint("Use `a b c` e $x + y$ aqui.")[1] == 5
    assert lint("Veja [`Layer`](crate::modules::Layer) agora.")[1] == 3
    # `\;` do LaTeX em fórmulas inline e em bloco não é ponto e vírgula
    findings, _ = lint("Inline $a\\;b$ matemática.\n\n$$\nx\\;y\n$$\n\nDepois texto.")
    assert not any(f["regra"] == "ponto-e-virgula" for f in findings), findings
    # front matter YAML, comentários HTML e definições de link ficam de fora
    findings, words = lint("---\nname: x; y\n---\n<!-- a; b -->\n[x]: https://a.b/c;d\nTexto.")
    assert findings == [] and words == 1, (findings, words)
    # um trecho com crase dupla pode conter crase ou ponto e vírgula
    findings, words = lint("O conjunto ``a;`b`` é pequeno.")
    assert findings == [] and words == 5, (findings, words)
    # as colunas ficam exatas depois de trechos mascarados
    findings, _ = lint("O `code` parte; depois mais.")
    semicolon = [f for f in findings if f["regra"] == "ponto-e-virgula"]
    assert semicolon[0]["coluna"] == 15, semicolon
    # o travessão é consultivo, e um traço sozinho numa tabela não é achado
    findings, _ = lint("Uma ideia — e outra.\n\n| a | b |\n| --- | --- |\n| — | x |")
    dashes = [f for f in findings if f["regra"] == "travessao"]
    assert len(dashes) == 1 and dashes[0]["nivel"] == CONSULTIVA, dashes
    # regra opcional de histórico
    text = "Isto já não trava. Atualmente roda uma vez."
    assert not any(f["regra"] == "historico" for f in lint(text)[0])
    assert len([f for f in lint(text, enabled={"historico"})[0] if f["regra"] == "historico"]) == 2

    # Rust: código nunca é prosa. Docs e comentários são lidos como Markdown.
    rust = (
        "//! Doc do módulo; com ponto e vírgula.\n"
        "use a::b; // nota final; aqui\n"
        "/// Doc externa que quebra\n"
        "/// em duas linhas.\n"
        "fn f<'a>(x: &'a str) -> char { let c = ';'; let s = \"não; prosa\"; c }\n"
        "// let comentado = fora(codigo);\n"
        "/* bloco; comentário */\n"
        "fn g() { panic!(\"estado ruim; pare {x:?}\"); }\n"
        "const R: &str = r#\"bruto \"citado\"; texto aqui\"#;\n"
    )
    findings, _ = lint(rust, filename="lib.rs")
    semicolons = sorted((f["linha"], f["coluna"]) for f in findings if f["regra"] == "ponto-e-virgula")
    assert semicolons == [(1, 18), (2, 24), (7, 9)], semicolons
    findings, _ = lint(rust, filename="lib.rs", parts={"mensagens"})
    assert [(f["linha"], f["coluna"]) for f in findings] == [(8, 29)], findings
    findings, _ = lint(rust, filename="lib.rs", parts={"literais"})
    assert sorted(f["linha"] for f in findings) == [8, 9], findings
    # um comentário de documentação é um parágrafo em várias linhas, e mensagens usam o limite estrito
    doc = "/// " + " ".join(["palavra"] * 14) + "\n/// " + " ".join(["palavra"] * 14) + ".\nfn f() {}\n"
    findings, _ = lint(doc, filename="a.rs")
    assert [(f["linha"], f["coluna"], f["trecho"]) for f in findings] == [(1, 5, "28 palavras")], findings
    msg = "fn f() { assert!(x, \"" + " ".join(["palavra"] * 23) + "\"); }\n"
    assert [f["trecho"] for f in lint(msg, filename="a.rs", parts={"mensagens"})[0]] == ["23 palavras"]
    # uma continuação com barra invertida junta as linhas da string
    cont = "fn f() { panic!(\"primeira metade; \\\n    segunda metade\"); }\n"
    findings, _ = lint(cont, filename="a.rs", parts={"mensagens"})
    assert [f["regra"] for f in findings] == ["ponto-e-virgula"], findings

    # Uma menção entre aspas é um exemplo, não prosa: conta como uma palavra e não é analisada.
    findings, words = lint('Não escreva "Realize uma análise; depois robusto." no log.')
    assert findings == [] and words == 5, (findings, words)
    assert "verbo-suporte" in _rules_of('Escreva "Realize uma análise".', read_quotes=True)
    findings, _ = lint("Use “a fim de” e «sendo que» só como exemplo.")
    assert findings == [], findings
    # uma citação que termina em ponto fecha a frase
    long_text = " ".join(["palavra"] * 25)
    assert "frase-longa" not in _rules_of(f'Ele disse "{long_text}." {long_text.capitalize()}.')
    # uma citação em bloco interrompe o parágrafo anterior
    quote = " ".join(["palavra"] * 24) + "."
    assert "frase-longa" not in _rules_of(f"**Antes:** um dois três quatro\n> {quote}")
    # "etc." antes de uma maiúscula fecha a frase
    half = " ".join(["palavra"] * 14)
    assert "frase-longa" not in _rules_of(f"Aceita {half} etc. O passo {half}.")

    # Região 'deve-falhar': os achados esperados somem, e a região sem falha vira um achado.
    findings, _ = lint("<!-- pts-lint: deve-falhar ponto-e-virgula -->\na; b\n<!-- pts-lint: fim -->\nTexto.")
    assert findings == [], findings
    findings, _ = lint("<!-- pts-lint: deve-falhar -->\nTexto conforme.\n<!-- pts-lint: fim -->")
    assert [f["regra"] for f in findings] == ["exemplo-sem-falha"], findings
    findings, _ = lint("<!-- pts-lint: deve-falhar frase-longa -->\na; b\n<!-- pts-lint: fim -->")
    assert [(f["regra"], f["trecho"]) for f in findings] == [("exemplo-sem-falha", "faltam: frase-longa")]
    for broken in ("<!-- pts-lint: deve-falhar -->\na; b", "<!-- pts-lint: fim -->",
                   "<!-- pts-lint: ignorar -->", "<!-- pts-lint: deve-falhar regra-x -->\na; b\n<!-- pts-lint: fim -->"):
        assert "diretiva-invalida" in _rules_of(broken), broken
    # uma diretiva dentro de um bloco de código é só um exemplo de uso
    assert _rules_of("```markdown\n<!-- pts-lint: deve-falhar -->\nTexto.\n<!-- pts-lint: fim -->\n```") == []
    # um sinônimo dentro de um exemplo que deve falhar não entra na rotação do documento
    findings, _ = lint("Verifique o log.\n\n<!-- pts-lint: deve-falhar -->\nConfira o log; agora.\n"
                       "<!-- pts-lint: fim -->")
    assert findings == [], findings

    # gerundismo: obrigatório com verbo pontual, consultivo com verbo de duração
    levels = {f["nivel"] for f in lint("Vamos estar enviando o relatório.")[0] if f["regra"] == "gerundismo"}
    assert levels == {OBRIGATORIA}, levels
    levels = {f["nivel"] for f in lint("O backup vai estar rodando durante a janela.")[0]
              if f["regra"] == "gerundismo"}
    assert levels == {CONSULTIVA}, levels
    assert "gerundio-encadeado" not in _rules_of("Aceita formatos, incluindo JSON, dependendo da versão.")
    # gíria técnica e locuções verbais idiomáticas (Regra 9.3)
    for text in ("Suba o servidor.", "Subiu o novo container.", "Derrube o serviço.", "Dê um push na branch.",
                 "Bata no endpoint de saúde.", "O build deu pau.", "Jogue isso no log.", "Subiu para produção."):
        assert "giria-tecnica" in _rules_of(text), text
    assert "giria-tecnica" not in _rules_of("A temperatura sobe. Suba a escada. Dê um nome ao job.")
    for text in ("O job deixou de rodar.", "Acabe com o processo.", "O agente não deu conta do erro.",
                 "Dá para usar o cache.", "Ele ficou de enviar o log."):
        assert "locucao-verbal" in _rules_of(text), text
    # datas e números
    assert "data-ambigua" in _rules_of("O deploy foi em 07/10/2026.")
    assert [f["nivel"] for f in lint("O deploy é em 07/10.")[0]] == [CONSULTIVA]
    assert _rules_of("O deploy foi em 2026-10-07. O próximo é em 07/Out. O plano cobre 24/48 casos.") == []
    assert _rules_of("Use 1/3 da memória. O suporte é 24/7.") == []
    assert "data-ambigua" in _rules_of("O prazo é 7/10.")
    assert "numero-ambiguo" in _rules_of("O limite é 1.000 requisições.")
    assert [f["nivel"] for f in lint("O tempo é 1,500 s.")[0]] == [CONSULTIVA]
    assert _rules_of("O tempo é 1,5 s. Custa R$ 2,50.") == []
    assert _rules_of("Custa 1.500,00. São 1.000.000 de linhas. Veja a Lei nº 15.263/2025 e a regra 3.7. "
                     "O limite é 10 000.") == []
    # gênero: só as formas da norma
    for text in ("Todes os usuários.", "Bem-vindes ao sistema.", "Olá, todxs.", "Caros alun@s.", "Elu saiu."):
        assert "linguagem-neutra" in _rules_of(text), text
    assert _rules_of("Use o Linux e o fax. Escreva para nome@servidor.com. Abra a sandbox.") == []
    # "excluir", ser e estar, decalques e "se" proclítico
    assert "palavra-ambigua" in _rules_of("Exclua os arquivos temporários do pacote.")
    assert "ser-estar" in _rules_of("O servidor é indisponível.")
    assert "ser-estar" not in _rules_of("O servidor está indisponível. O campo é obrigatório. "
                                        "Os campos são vazios por padrão. O recurso é ativo no plano pago.")
    assert "decalque-do-ingles" in _rules_of("O módulo performa bem.")
    assert "decalque-do-ingles" in _rules_of("Ele realizou que o disco estava cheio.")
    assert "passiva-sintetica" in _rules_of("Não se recomenda reiniciar.")
    assert "passiva-sintetica" not in _rules_of("Verifique se usa o cache.")

    checked = _check_repository()
    print("autoteste OK" + (f" (e {checked} arquivos do repositório)" if checked else ""))


def _check_repository():
    """Quando o linter está no repositório da skill, analisa os documentos dela.

    Os documentos precisam passar sem achados obrigatórios. O arquivo de casos-limite
    precisa falhar com exatamente os dois achados que o README promete.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = ["SKILL.md", "README.md", "references/regras-de-redacao.md", "examples/antes-depois.md"]
    fixture = "examples/casos-limite-do-linter.md"
    paths = [os.path.join(root, name) for name in docs + [fixture]]
    if not all(os.path.exists(path) for path in paths):
        return 0
    failures = []
    for name in docs:
        with open(os.path.join(root, name), encoding="utf-8") as handle:
            findings, _ = lint(handle.read(), filename=name)
        failures += [f"{f['arquivo']}:{f['linha']}:{f['coluna']} {f['regra']} [{f['trecho']}]"
                     for f in findings if f["nivel"] == OBRIGATORIA]
    assert not failures, "Os documentos da skill têm achados obrigatórios:\n" + "\n".join(failures)
    with open(os.path.join(root, fixture), encoding="utf-8") as handle:
        findings, _ = lint(handle.read(), filename=fixture)
    hard = [(f["regra"], f["linha"]) for f in findings if f["nivel"] == OBRIGATORIA]
    assert hard == [("conjuncao-pendente", 7), ("conjuncao-pendente", 8)], hard
    return len(paths)


def _usage_error(message):
    print(f"pts-lint: {message}", file=sys.stderr)
    return 2


FLAGS = {"--json", "--resumo", "--ler-citacoes", "--autoteste", "--ajuda", "--help", "-h"}
# Nomes do ste-lint.py, para que um erro de hábito mostre o nome certo.
STE_LINT_NAMES = {"--baseline": "--linha-de-base", "--disable": "--desativar", "--enable": "--ativar",
                  "--lang": "--linguagem", "--parts": "--partes", "--max-words": "--max-palavras",
                  "--max-words-strict": "--max-palavras-estrito", "--summary": "--resumo",
                  "--selftest": "--autoteste"}


def main(argv):
    if {"--ajuda", "--help", "-h"} & set(argv):
        print(__doc__)
        return 0
    if "--autoteste" in argv:
        selftest()
        return 0
    as_json = "--json" in argv
    summary = "--resumo" in argv
    read_quotes = "--ler-citacoes" in argv
    baseline = 0
    disabled, enabled = set(), set()
    lang, parts = None, None
    max_words, max_words_strict = MAX_WORDS, MAX_WORDS_STRICT
    paths = []
    known = KNOWN_RULES
    i = 0
    try:
        while i < len(argv):
            a = argv[i]
            if a in FLAGS:
                pass
            elif a == "--linha-de-base":
                i += 1
                baseline = int(argv[i])
            elif a == "--desativar":
                i += 1
                disabled = set(argv[i].split(","))
            elif a == "--ativar":
                i += 1
                enabled = set(argv[i].split(","))
            elif a == "--linguagem":
                i += 1
                lang = argv[i]
            elif a == "--partes":
                i += 1
                parts = set(argv[i].split(","))
            elif a == "--max-palavras":
                i += 1
                max_words = int(argv[i])
            elif a == "--max-palavras-estrito":
                i += 1
                max_words_strict = int(argv[i])
            elif a.startswith("-"):
                hint = f" Use {STE_LINT_NAMES[a]}." if a in STE_LINT_NAMES else ""
                return _usage_error(f"opção desconhecida: {a}.{hint} Veja --ajuda.")
            else:
                paths.append(a)
            i += 1
    except (IndexError, ValueError):
        return _usage_error(f"a opção {argv[i - 1] if i else ''} precisa de um valor numérico ou de uma lista")
    unknown = (disabled | enabled) - known
    if unknown:
        return _usage_error(f"regra(s) desconhecida(s): {', '.join(sorted(unknown))}. "
                            f"Conhecidas: {', '.join(sorted(known))}")
    if lang not in (None, "markdown", "rust"):
        return _usage_error(f"--linguagem desconhecida: {lang}. Conhecidas: markdown, rust")
    if parts is not None and parts - RUST_PARTS:
        return _usage_error(f"--partes desconhecida(s): {', '.join(sorted(parts - RUST_PARTS))}. "
                            f"Conhecidas: {', '.join(sorted(RUST_PARTS))}")

    options = dict(lang=lang, parts=parts, max_words=max_words,
                   max_words_strict=max_words_strict, enabled=enabled, read_quotes=read_quotes)
    documents = ([(p, open(p, encoding="utf-8").read()) for p in paths]
                 or [("<stdin>", sys.stdin.read())])
    findings, words_total, per_file = [], 0, []
    for path, text in documents:
        found, words = lint(text, filename=path, **options)
        found = [f for f in found if f["regra"] not in disabled]
        hard = sum(1 for f in found if f["nivel"] == OBRIGATORIA)
        per_file.append((path, hard, len(found) - hard, words))
        findings.extend(found)
        words_total += words

    hard_count = sum(1 for f in findings if f["nivel"] == OBRIGATORIA)
    if summary:
        report_summary(per_file)
    else:
        report(findings, words_total, as_json, hard_count, baseline)
    return 1 if hard_count > baseline else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BrokenPipeError:  # por exemplo, `pts-lint.py … | head`
        sys.exit(1)
