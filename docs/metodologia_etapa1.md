# Metodologia — coleta e integração

O estudo adota recorte territorial nos nove estados da Região Nordeste e temporal de 2000 a 2025. Foram obtidos arquivos anuais de dengue do Sistema de Informação de Agravos de Notificação (SINAN), publicados no Portal de Dados Abertos do SUS, e dados populacionais oficiais do IBGE por meio da API de agregados do SIDRA. Os arquivos originais foram preservados para permitir auditoria e reprodução.

No SINAN, a seleção territorial foi realizada pela unidade federativa de residência. O município de residência foi preservado no formato original e normalizado para uma chave de seis dígitos. Nos dados populacionais, os códigos municipais de sete dígitos do IBGE foram preservados e tiveram os seis primeiros dígitos extraídos apenas para a junção. A combinação municipal utilizou essa chave geográfica e o ano; a combinação estadual utilizou o código da UF e o ano. Foram verificadas a unicidade das chaves e a ausência de colisões na normalização.

O ano utilizado nas contagens iniciais corresponde ao ano de notificação (`NU_ANO`). As datas de notificação e início dos sintomas foram conservadas para avaliação posterior. Os registros com ano divergente do arquivo, datas inválidas ou município inconsistente foram quantificados em auditorias. Um registro com UF de residência válida e município inconsistente permanece no total estadual, mas não recebe atribuição municipal arbitrária.

A população foi obtida da tabela 6579 (estimativas anuais), complementada pelas tabelas 202 (censos de 2000 e 2010), 793 (contagem/estimativas de 2007) e 4714 (Censo de 2022). A população municipal e a estadual foram consultadas separadamente. A inexistência de estimativa anual de 2023 na série consultada foi registrada como ausência, sem substituição automática ou interpolação. As diferenças de referência temporal, revisões populacionais e alterações territoriais deverão ser consideradas na interpretação das taxas na etapa analítica.

As contagens desta etapa representam notificações presentes nos arquivos, sem filtragem epidemiológica definitiva. Não se assume equivalência entre notificações, casos prováveis e casos confirmados. Os campos originais de classificação, critério, evolução, agravo e marcação de duplicidade, quando disponíveis, foram preservados para subsidiar a limpeza posterior. Não foram calculadas taxas de incidência antes da definição e harmonização do numerador.

Cada download recebeu metadados contendo origem, URL, identificador do recurso quando disponível, instante de extração em UTC-03:00, atualização informada pela fonte, tamanho e hash SHA-256. Foram produzidos um manifesto consolidado, dicionário dos campos e relatório de validação. As junções preservaram chaves sem correspondência; ausência de registro não foi convertida automaticamente em zero.

## Limitações e decisões ainda necessárias

- Definir casos prováveis/confirmados considerando os layouts históricos e as mudanças de classificação.
- Investigar marcações de duplicidade e agravo antes de interpretar notificações como casos.
- Definir denominador de 2023 de forma explícita e rastreável se esse ano entrar em análises de incidência.
- Verificar a comparabilidade territorial e o impacto das mudanças entre censos e estimativas.
- Investigar pendências de códigos, datas e completude identificadas na execução.
- Não interpretar associações exploratórias como relações causais.

## Fontes

- Ministério da Saúde. SINAN/Dengue: https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue . URLs e datas de extração efetivas no manifesto.
- IBGE. SIDRA: https://sidra.ibge.gov.br/tabela/6579 ; https://sidra.ibge.gov.br/tabela/202 ; https://sidra.ibge.gov.br/tabela/793 ; https://sidra.ibge.gov.br/tabela/4714 . Consultas completas no manifesto.

Este texto documenta a Etapa 1; não constitui o relatório final nem apresenta conclusões epidemiológicas.
