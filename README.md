# Dengue no Nordeste — coleta, limpeza e análise exploratória

## Etapa 2 pronta: limpeza e EDA

Abra [o notebook de limpeza e EDA](notebooks/02_limpeza_eda.ipynb), [os resultados](docs/resultados_etapa2.md) e [a metodologia](docs/metodologia_etapa2.md). O relatório visual completo está em `outputs/etapa2/relatorio_eda.html`; baixe e abra no navegador. Ele contém as imagens incorporadas e funciona offline.

A Etapa 2 entrega tabelas anuais por estado/município, série mensal por início dos sintomas, incidência operacional por 100 mil habitantes, estatísticas descritivas, sazonalidade, correlação descritiva, sinalização de outliers, nove figuras e auditoria dos filtros. Os outliers foram mantidos. Não há modelagem preditiva ou conclusão causal.

**Atenção ao numerador:** casos prováveis operacionais não são casos confirmados. A definição ampla exclui descartados e outros problemas documentados, mas inclui inconclusivos/ignorados; o cenário estrito requer classificação de dengue e critério 1/2. A composição dos arquivos publicados varia entre anos, inclusive quanto à presença de descartados. **2023 continua sem taxa**, porque não foi imputada população.

Para reconstruir a Etapa 2 nesta pasta, após instalar as dependências:

```powershell
.\.venv\Scripts\python.exe scripts/executar_etapa2.py --reprocessar
.\.venv\Scripts\python.exe scripts/testar_regras_etapa2.py
.\.venv\Scripts\python.exe scripts/validar_etapa2.py
.\.venv\Scripts\python.exe scripts/executar_notebook_etapa2.py
```

Sem `--reprocessar`, o ponto de entrada reutiliza as tabelas existentes e gera a documentação. A geração da documentação recria o notebook; execute novamente o último comando para salvar suas saídas em kernel real. Sem os recortes individuais da Etapa 1, a reconstrução também faz a coleta e a integração necessárias. A consulta complementar de 2026 serve exclusivamente para buscar sintomas até 2025 e não amplia o período de estudo. Seu resultado, inclusive se vazio, é auditado.

| Entrega da Etapa 2 | Local |
|---|---|
| Notebook executado | `notebooks/02_limpeza_eda.ipynb` |
| Relatório visual independente | `outputs/etapa2/relatorio_eda.html` |
| Texto com resultados e limitações | `docs/resultados_etapa2.md` |
| Métodos e fontes primárias | `docs/metodologia_etapa2.md` |
| Dicionário adicional | `docs/dicionario_etapa2.csv` |
| Tabelas para análise | `data/processed/etapa2/` |
| Auditoria e hashes | `data/metadata/validacao_etapa2.json` e manifestos de referências/complemento |
| Recortes com flags e motivos | `data/interim/etapa2/` (não versionados) |

Os testes das regras cobrem descarte, códigos históricos, inconclusivos, duplicidade marcada, outra doença, cronologia, ausência de sintomas, ano, notificações tardias e atribuição municipal. O validador independente confere chaves, reconciliação de contagens, taxas, sazonalidade, ausência de 2023 e hashes dos insumos. Essas verificações não substituem a revisão epidemiológica do grupo.

---

## Etapa 1: coleta e integração

Projeto IMD1151, 2026.2. Recorte: 2000–2025; residentes em MA, PI, CE, RN, PB, PE, AL, SE e BA.

Esta etapa entrega dados efetivamente baixados, scripts reproduzíveis, notebook de acompanhamento, bases integradas, dicionário e rastreabilidade. A limpeza epidemiológica e a escolha da definição de caso pertencem à etapa seguinte.

## Comece aqui

Abra `notebooks/01_coleta_integracao.ipynb`. Com os arquivos já coletados, o notebook usa o cache e apresenta a cobertura e as validações. Para repetir toda a preparação:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/coletar.py
.\.venv\Scripts\python.exe scripts/integrar.py
.\.venv\Scripts\python.exe -m jupyterlab
```

Execute os comandos nesta pasta. Os scripts também funcionam chamados por caminho absoluto a partir de outra pasta. Uma primeira execução exige acesso à internet, aproximadamente 1 GB para arquivos brutos e espaço adicional para os recortes; o processamento pode levar vários minutos. O SINAN é lido em blocos, sem carregar toda a série na memória.

`coletar.py --inicio 2024 --fim 2025` permite recorte menor; use os mesmos argumentos em `integrar.py`. Os CSVs processados são substituídos pelo recorte escolhido. O padrão é sempre 2000–2025. `--atualizar` refaz downloads; sem essa opção, o cache somente é aceito se URL e SHA-256 conferirem. Falhas de download são registradas e fazem o comando terminar com erro; execute novamente para retomar usando os arquivos íntegros.

## Fontes oficiais

- SINAN/Dengue, Ministério da Saúde: https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue . Arquivos nacionais anuais CSV/ZIP, encontrados no catálogo, e PDF do dicionário oficial.
- IBGE/SIDRA, API de agregados: https://servicodados.ibge.gov.br/api/docs/agregados . Seleção territorial `N6[N3[21,22,23,24,25,26,27,28,29]]` para municípios e `N3[...]` para estados.
- Tabela 6579, variável 9324: estimativas anuais nos anos disponíveis.
- Tabela 202, variável 93, sexo e situação do domicílio = Total: censos de 2000 e 2010, resultados do universo.
- Tabela 793, variável 93: contagem/estimativas de 2007.
- Tabela 4714, variável 93: Censo de 2022.

Os JSONs brutos e os metadados das tabelas foram preservados. URLs completas, atualização na fonte, instante de extração com UTC-03:00, tamanho e SHA-256 constam dos arquivos `.meta.json` e de `data/metadata/manifesto_extracao.json`. Uma nova execução que reutiliza cache preserva a data da extração original.

## Decisões que afetam a interpretação

1. **Residência:** o recorte usa `SG_UF`, a UF de residência, e `ID_MN_RESI`, município de residência. Não usa o município notificador como residência. Registros com UF de residência fora das nove selecionadas não entram no recorte, mesmo se notificados no Nordeste.
2. **Código municipal:** preservamos o valor original. Códigos de sete dígitos são reduzidos aos seis primeiros; códigos de seis dígitos são mantidos. O cruzamento recupera o código IBGE de sete dígitos da população do mesmo ano. Asserções impedem colisão de códigos e relações muitos-para-muitos. Código sem correspondência não recebe nome ou população por aproximação.
3. **Ano:** nesta etapa, `ano` é `NU_ANO` (ano de notificação), e não o ano dos sintomas. Registros cujo ano diverge do arquivo ficam no recorte individual e na auditoria, mas fora dos totais integrados. Datas de notificação e sintomas são preservadas para limpeza e sazonalidade na Etapa 2.
4. **Notificações:** as contagens são de registros presentes nos arquivos oficiais, antes de filtrar classificação, agravo, duplicidade ou confirmação. Não são uma estimativa de casos confirmados/prováveis e não devem ser apresentadas como incidência de dengue. A classificação original é preservada, inclusive a transição de `CON_CLASSI` para `CLASSI_FIN`. O dicionário atual não deve ser aplicado automaticamente a todo o período histórico.
5. **2023:** a série 6579 não oferece estimativa anual para esse ano. As notificações de 2023 estão presentes; a população fica ausente. Não copiamos a população censitária de 2022, não interpolamos e não chamamos uma população de referência de 2022 de estimativa de 2023. Para calcular incidência em 2023, a Etapa 2 deverá adotar e documentar um denominador alternativo, por exemplo a série de estimativas municipais utilizada pelo Ministério da Saúde, ou uma interpolação explicitamente identificada como cálculo do grupo.
6. **Ausência e zero:** linhas de população sem registros correspondentes ficam com `notificacoes` ausente e status `sem_registro_sinan`. Isso não comprova que não houve casos. A base municipal contém a união das chaves observadas nas duas fontes; não é uma grade fixa de todos os municípios em todos os anos.
   Valores especiais do IBGE, como `...`, são mantidos nos originais e convertidos em população ausente nos produtos. Havendo notificações para essa chave, o status é `sem_populacao_valida`.
7. **Cobertura municipal:** as malhas e códigos podem mudar. Não harmonizamos retrospectivamente limites territoriais nesta etapa. Comparações longitudinais municipais e diferenças entre censos/estimativas exigem discussão na Etapa 2.
8. **Totais estaduais:** usam diretamente os registros com UF de residência válida, inclusive quando o município está ausente/inconsistente. A diferença em relação à soma municipal é conciliada na auditoria. A população estadual vem diretamente do IBGE; não é estimada pela soma apenas dos municípios com notificações.

## Arquivos entregues

| Local | Conteúdo |
|---|---|
| `notebooks/01_coleta_integracao.ipynb` | Notebook principal da etapa |
| `scripts/coletar.py` | Coleta, cache, metadados e retomada |
| `scripts/integrar.py` | Recorte, normalização, integração e validações |
| `data/raw/sinan/` | ZIPs nacionais originais e dicionário oficial |
| `data/raw/ibge/` | Respostas JSON municipais/estaduais e metadados |
| `data/interim/sinan_ne_AAAA.csv.gz` | Recorte individual dos residentes no Nordeste |
| `data/processed/dengue_municipio_ano.csv` | Integração municipal por código de seis dígitos e ano |
| `data/processed/dengue_estado_ano.csv` | Integração estadual por código da UF e ano |
| `data/processed/dengue_estado_mes_notificacao.csv` | Contagens mensais com data/ano consistentes; somente grupos observados |
| `data/processed/classificacao_estado_ano.csv` | Frequências dos códigos originais de classificação por estado e ano |
| `data/processed/populacao_nordeste.csv` | Populações de ambos os níveis territoriais e sua origem |
| `data/processed/pendencias_integracao.csv` | Chaves municipais sem correspondência completa |
| `data/processed/cobertura_anual.csv` | Cobertura anual da integração estadual |
| `data/metadata/` | Manifesto, status de coleta, auditorias e validação |
| `docs/dicionario_dados.csv` | Dicionário dos campos entregues |
| `docs/metodologia_etapa1.md` | Texto adaptável ao relatório técnico |
| `docs/resumo_execucao.md` | Resumo da execução e pendências reais |

## Validação

O processamento verifica unicidade das chaves populacionais e municipais, população positiva, ausência de colisões ao reduzir códigos, nove UFs em cada ano, junções um-para-um e conservação das contagens entre recorte, totais estaduais, municípios e classificação. Problemas de datas, anos, códigos e ausências são quantificados, sem apagar silenciosamente os registros originais. A extração não contém uma chave individual confiável para decidir duplicidade por igualdade de atributos; por isso, não elimina linhas idênticas automaticamente.

Execute `python scripts/validar.py --hashes` para conferir também todos os arquivos originais contra o manifesto. `python scripts/verificar_notebook.py` executa as células Python em sequência, sem servidor Jupyter, e salva as saídas reais no notebook.

## Versionamento e uso de IA

O `.gitignore` exclui bases brutas e recortes individuais volumosos. Versione scripts, notebook, documentação, CSVs agregados e metadados; disponibilize os dados brutos por suas URLs e os scripts de obtenção. Nenhum repositório remoto foi criado nem houve publicação dos dados.

Texto inicial da declaração, a ser atualizado pelo grupo: “Foi utilizado o ChatGPT/Codex na organização da coleta, implementação de scripts, documentação e verificações automatizadas. O grupo deverá revisar as definições epidemiológicas, conferir os resultados nas fontes e registrar as verificações humanas realizadas.” Esse texto não afirma que o grupo já realizou verificações ainda pendentes.
