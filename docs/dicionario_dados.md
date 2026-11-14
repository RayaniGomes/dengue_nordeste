# Dicionário de dados — CP1

As tabelas de entrada são apresentadas separadamente. O pacote portátil contém apenas agregados municipais e tabelas públicas do IBGE. A tabela individual é descrita para documentar o modo PostgreSQL; seus registros não são versionados.

Os códigos epidemiológicos mantêm as interpretações operacionais do projeto; a confirmação externa das legendas pendentes não foi presumida.

## notificacao_dengue_ne

| Variável | Tipo | Significado | Origem e regra |
|---|---|---|---|
| id | inteiro | Chave local de uma notificação no banco | PostgreSQL. Identidade gerada; não é um identificador público original do SINAN. |
| cod_mun7 | texto, 7 dígitos | Município de residência | SINAN ID_MN_RESI + IBGE. Chave de integração; primeiros seis dígitos ligados ao cadastro IBGE. |
| cod_mun7_notificacao | texto, 7 dígitos | Município da unidade notificadora | SINAN ID_MUNICIP + IBGE. Pode ser nulo; não define a residência. |
| ano | inteiro | Ano de notificação | SINAN NU_ANO; alternativa ano_arquivo. Análise limitada a 2000–2025; ano inválido usa ano do arquivo. |
| dt_notificacao | data | Data da notificação | SINAN DT_NOTIFIC. Data inválida vira nulo no tratamento de origem. |
| dt_sintomas | data | Data de início dos sintomas | SINAN DT_SIN_PRI. Se a notificação existe, aceita intervalo de até 365 dias antes dela; inconsistências viram nulo. |
| mes_sintomas | inteiro | Mês de início dos sintomas | Derivada de dt_sintomas. 1 a 12; nulo quando a data tratada é ausente. |
| sexo | texto | Sexo registrado | SINAN CS_SEXO. M e F mantidos; I, O e vazio viram nulo. Não representa identidade de gênero. |
| idade_anos | inteiro | Idade em anos completos | SINAN NU_IDADE ou NU_IDADE_N. Anos até 110 mantidos; unidades menores que ano viram 0; inválidos e ignorados viram nulo. |
| classificacao | texto | Código de classificação final harmonizado entre fichas | SINAN CON_CLASSI ou CLASSI_FIN. Código original preservado como texto; confirmação das legendas no dicionário oficial continua pendente. |
| criterio | texto | Código do critério de classificação | SINAN CON_CRITER ou CRITERIO. Código harmonizado entre fichas; legenda oficial ainda requer confirmação. |
| evolucao | texto | Código de evolução do registro | SINAN CON_EVOLUC ou EVOLUCAO. Código harmonizado entre fichas; legenda oficial ainda requer confirmação. |
| caso_provavel | booleano | Flag do numerador principal do projeto | Regra operacional aplicada no banco. Classificação distinta de 5, incluindo nulos e código 0; não equivale a caso confirmado. |
| caso_confirmado | booleano | Flag do cenário de comparação de confirmados | Regra operacional aplicada no banco. Classificação em 1–4 ou 10–12, conforme decisão documentada. |
| possivel_duplicata | booleano | Sinalização de possível repetição de uma notificação | Comparação de campos no banco. Da segunda linha em diante em grupos de ano do arquivo, unidade/município notificador, datas, sexo, idade e residência; não excluída automaticamente. |
| ano_arquivo | inteiro | Ano do CSV anual de origem | SINAN/OpenDataSUS. Pode diferir do ano de notificação; 2026 fica fora da análise. |

## notificacoes_municipio_ano

| Variável | Tipo | Significado | Origem e regra |
|---|---|---|---|
| cod_mun7 | texto | Município de residência | SINAN agregado da base tratada. Chave IBGE de sete dígitos; texto. |
| ano | inteiro | Ano de notificação | SINAN agregado da base tratada. 2000–2025. |
| notificacoes | inteiro | Quantidade de notificações tratadas | Agregação da tabela tratada do SINAN. Inclui prováveis e não prováveis; unidade: registros. |
| casos_provaveis | inteiro | Quantidade com flag caso_provavel verdadeira | Agregação da tabela tratada do SINAN. Numerador principal; inclui possíveis duplicatas sinalizadas. |
| casos_confirmados | inteiro | Quantidade com flag caso_confirmado verdadeira | Agregação da tabela tratada do SINAN. Cenário de comparação; não substitui o numerador principal. |
| possiveis_duplicatas | inteiro | Quantidade com flag possivel_duplicata verdadeira | Agregação da tabela tratada do SINAN. Contagem entre todas as notificações, não apenas casos prováveis. |
| sem_idade | inteiro | Notificações sem idade tratada | Agregação da tabela tratada do SINAN. Contagem entre todas as notificações; idade 0 é válida. |
| sem_sexo | inteiro | Notificações sem sexo tratado | Agregação da tabela tratada do SINAN. Nulo ou vazio; contagem entre todas as notificações. |
| sem_mes_sintomas | inteiro | Notificações sem mês de sintomas tratado | Agregação da tabela tratada do SINAN. Contagem entre todas as notificações. |

## populacao_municipio_ano

| Variável | Tipo | Significado | Origem e regra |
|---|---|---|---|
| cod_mun7 | texto, 7 dígitos | Município do denominador | IBGE/SIDRA e tratamento documentado. Chave de integração, não converter em número. |
| ano | inteiro | Ano de referência da população | IBGE/SIDRA e tratamento documentado. Combinar com o mesmo município e ano do numerador. |
| populacao | inteiro, habitantes | População municipal | IBGE/SIDRA e tratamento documentado. Na tabela consolidada pode ser nula; na tratada é positiva. |
| fonte | texto | Origem do valor populacional | IBGE/SIDRA e tratamento documentado. Censos têm prioridade sobre estimativas; na tratada, interpolada identifica a média dos vizinhos em 2007 e 2023. |

## populacao_ne

| Variável | Tipo | Significado | Origem e regra |
|---|---|---|---|
| cod_mun7 | texto, 7 dígitos | Município do denominador | IBGE/SIDRA e tratamento documentado. Chave de integração, não converter em número. |
| ano | inteiro | Ano de referência da população | IBGE/SIDRA e tratamento documentado. Combinar com o mesmo município e ano do numerador. |
| populacao | inteiro, habitantes | População municipal | IBGE/SIDRA e tratamento documentado. Na tabela consolidada pode ser nula; na tratada é positiva. |
| fonte | texto | Origem do valor populacional | IBGE/SIDRA e tratamento documentado. Censos têm prioridade sobre estimativas; na tratada, interpolada identifica a média dos vizinhos em 2007 e 2023. |
| cod_mun6 | texto, 6 dígitos | Código municipal sem dígito verificador | IBGE/SIDRA. Usado na ligação com o SINAN. |
| uf_cod | inteiro | Código IBGE da UF | IBGE/SIDRA. 21–29 no recorte Nordeste. |
| municipio | texto | Nome do município na fonte consolidada | IBGE/SIDRA. Não é uma chave de integração. |

## municipio_ne

| Variável | Tipo | Significado | Origem e regra |
|---|---|---|---|
| cod_mun7 | texto, 7 dígitos | Código IBGE do município | IBGE/Localidades. Chave primária. |
| cod_mun6 | texto, 6 dígitos | Código municipal sem dígito verificador | IBGE/Localidades. Ligação entre SINAN e IBGE; único no cadastro. |
| nome | texto | Nome do município | IBGE/Localidades. Informação descritiva, não chave. |
| uf_cod | inteiro | Código IBGE da UF | IBGE/Localidades. Ligação ao cadastro de UFs; 21–29 no recorte. |
| microrregiao | texto | Microrregião da divisão anterior | IBGE/Localidades. Pode ser nula para municípios criados após essa divisão. |
| mesorregiao | texto | Mesorregião da divisão anterior | IBGE/Localidades. Pode ser nula. |
| regiao_imediata | texto | Região geográfica imediata | IBGE/Localidades. Divisão regional atual do cadastro. |
| regiao_intermediaria | texto | Região geográfica intermediária | IBGE/Localidades. Divisão regional atual do cadastro. |

## estado_ne

| Variável | Tipo | Significado | Origem e regra |
|---|---|---|---|
| uf_cod | inteiro | Código IBGE da UF | IBGE/Localidades. Chave primária. |
| sigla | texto | Sigla da UF | IBGE/Localidades. MA, PI, CE, RN, PB, PE, AL, SE, BA. |
| nome | texto | Nome da UF | IBGE/Localidades. Descrição da unidade federativa. |
| regiao_sigla | texto | Sigla da grande região | IBGE/Localidades. NE no recorte. |
| regiao | texto | Nome da grande região | IBGE/Localidades. Nordeste no recorte. |

## paineis_integrados

| Variável | Tipo | Significado | Origem e regra |
|---|---|---|---|
| notificacoes | inteiro | Quantidade de notificações tratadas | Soma dos agregados municipais. Inclui prováveis e não prováveis; unidade: registros. |
| casos_provaveis | inteiro | Quantidade com flag caso_provavel verdadeira | Soma dos agregados municipais. Numerador principal; inclui possíveis duplicatas sinalizadas. |
| casos_confirmados | inteiro | Quantidade com flag caso_confirmado verdadeira | Soma dos agregados municipais. Cenário de comparação; não substitui o numerador principal. |
| possiveis_duplicatas | inteiro | Quantidade com flag possivel_duplicata verdadeira | Soma dos agregados municipais. Contagem entre todas as notificações, não apenas casos prováveis. |
| sem_idade | inteiro | Notificações sem idade tratada | Soma dos agregados municipais. Contagem entre todas as notificações; idade 0 é válida. |
| sem_sexo | inteiro | Notificações sem sexo tratado | Soma dos agregados municipais. Nulo ou vazio; contagem entre todas as notificações. |
| sem_mes_sintomas | inteiro | Notificações sem mês de sintomas tratado | Soma dos agregados municipais. Contagem entre todas as notificações. |
| populacao | inteiro, habitantes | Denominador do município, UF ou região no ano | Integração SINAN + IBGE. Somar denominadores antes de calcular a taxa; não representa pessoas distintas ao somar anos. |
| incidencia_provaveis_100mil | número real | Incidência operacional anual por 100 mil habitantes | Integração SINAN + IBGE. casos_provaveis / populacao × 100.000, com população positiva; não é média das taxas municipais. |
| fonte_populacao | texto | Origem do denominador municipal | Integração SINAN + IBGE. Preserva a informação de interpolação do banco. |
| municipios_com_populacao | inteiro | Municípios com população disponível na UF e no ano | Integração SINAN + IBGE. Pode variar por criação de municípios; não presumir cobertura de 26 anos para todos. |
| municipios_interpolados | inteiro | Municípios com população interpolada na UF e no ano | Integração SINAN + IBGE. Contagem de fonte = interpolada. |
