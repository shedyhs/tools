# Extraindo funções de código, DER e telas

Objetivo: chegar a cada número (TD, TR, AR) com uma fonte apontável — `arquivo:linha`,
tabela do DER ou nome do print. Registre tudo nas listas do JSON; o gerador transforma em
Memória TD / Evidências.

## Ordem recomendada
1. **Inventário** (Evidências): liste telas (prints), rotas/endpoints, tabelas do DER.
   Para repositórios grandes, use subagentes em paralelo por módulo e consolide.
2. **Funções de dados** a partir do DER, confirmando nas telas o que o usuário reconhece.
3. **Transações** a partir das telas (ações do usuário), confirmando no código o que é lido/gravado.
4. **Conciliação**: toda rota relevante ligada a uma função ou marcada como técnica; todo
   ALI com ao menos uma EE que o mantém; todo AIE lido por alguma transação.

## DER → ALI/AIE
- Fontes de DER: imagem do diagrama, `CREATE TABLE`/migrations (Alembic, Flyway, Prisma,
  Django, Laravel, TypeORM…), models ORM, ou o banco via MCP `pg` (`pg_get_ddl`).
- Agrupe por entidade de negócio: entidade forte + dependentes/especializações/associativas
  com atributos = 1 arquivo lógico com vários TR.
- Mantido × lido: procure no código INSERT/UPDATE/DELETE, `save()`, `create()`,
  repositórios. Sem escrita na fronteira e mantido por outro sistema ⇒ AIE.
- Tabelas de domínio (código/descrição): siga o guia FATTO — se não são reconhecidas pelo
  negócio mas o dado é, viram TR/TD de quem as usa. Se o contratante adotar a prática
  NESMA de "tabelas FPA" (um ALI/AIE único de tabelas de código), registre a decisão na
  Revisão e aplique-a de forma consistente.
- TD: atributos de negócio. FK que materializa relação reconhecida conta 1 TD. Excluir:
  id surrogate, created_at/updated_at técnicos, version/lock, soft-delete interno, hash
  de senha só se o usuário não reconhece. Coloque excluídos em `colunas_excluidas`.
- Não contar: cache, sessão, fila, outbox, idempotência, log técnico. Trilha de auditoria
  exigida pelo negócio pode ser ALI — registre a decisão.

## Telas → processos elementares e TD
- Cada botão/ação com efeito próprio candidato a processo: Incluir, Alterar, Excluir,
  Pesquisar/Listar, Detalhar, Imprimir, Exportar, Aprovar/Rejeitar, Importar.
- TD = campos de entrada + campos exibidos que cruzam a fronteira, contados uma vez;
  +1 ação (botão) +1 mensagens, quando existirem. Rótulos fixos, títulos, menus, ícones
  decorativos não contam. Paginação/ordenação não contam.
- Combos/listas de domínio: popular um combo não é processo à parte para fins desta
  skill (o guia exclui "preenchimento de campos"); o campo escolhido conta 1 TD na transação.
- Wireframe sem campos legíveis ⇒ `td: null` e pendência na Revisão.

## Código → classificação, AR e confirmação dos TD
- Localize o handler da ação (rota, controller, service, use-case).
- **AR**: arquivos lógicos tocados — queries, repositórios, joins, validações de existência,
  chamadas a outros sistemas (AIE). Tabelas do mesmo arquivo lógico = 1 AR.
- **SE × CE**: procure cálculo/derivação (somas, médias, percentuais, datas calculadas,
  agregações `GROUP BY`/`SUM`, regras de negócio na montagem). Havendo ⇒ SE; marque
  `"calculo": true`. Recuperação simples ⇒ CE.
- **EE vs. parte de EE**: GET de detalhe usado só pelo formulário de edição pertence à EE.
  Endpoints de upload em partes, refresh token, health check ⇒ técnicos.
- Mesma lógica em web, mobile e API ⇒ uma função; liste as rotas em Evidências.
- Campos de esquema (DTO/serializer/pydantic/zod) ajudam a enumerar TD, mas confirme com
  a tela — esquema aberto/dinâmico ⇒ pendência.

## Quando faltar evidência
Deixe `td` e/ou `ar_tr` como `null`, preencha `pendencia`, e siga. Nunca arredonde para
"Baixa" nem invente quantidades.
