# Dengue no Nordeste — coleta e integração de dados

Projeto de Ciência de Dados da disciplina **IMD1151, semestre 2026.2**, voltado à organização e integração de dados sobre dengue entre residentes do Nordeste brasileiro, no período de **2000 a 2025**.

O projeto combina notificações do **SINAN/OpenDataSUS**, do Ministério da Saúde, com dados de população e cadastro territorial do **IBGE**. A integração permite acompanhar notificações, casos prováveis e confirmados por município, estado e ano, além de calcular a incidência de casos prováveis por 100 mil habitantes.

O recorte abrange os nove estados: **MA, PI, CE, RN, PB, PE, AL, SE e BA**. A versão ativa entrega o primeiro notebook de coleta e integração, seu dicionário, quatro painéis agregados e verificações de reprodução. As etapas seguintes de análise ainda não fazem parte desta pasta ativa.

> **Para começar:** abra o [notebook principal](notebooks/01_coleta_integracao.ipynb) ou baixe a [versão HTML com as saídas](outputs/postgresql/01_coleta_integracao.html) e abra no navegador. É possível executar o notebook **sem PostgreSQL e sem credenciais**, usando os insumos agregados incluídos neste projeto.

## Sumário

- [Objetivos e fontes](#objetivos-e-fontes)
- [Tecnologias](#tecnologias)
- [Como executar](#como-executar)
- [Usar o PostgreSQL](#usar-o-postgresql)
- [Fluxo de processamento](#fluxo-de-processamento)
- [Resultados e arquivos gerados](#resultados-e-arquivos-gerados)
- [Organização do repositório](#organização-do-repositório)
- [Validação e reprodução](#validação-e-reprodução)
- [Regras e limitações dos dados](#regras-e-limitações-dos-dados)
- [Problemas comuns](#problemas-comuns)
- [Documentação complementar](#documentação-complementar)

## Objetivos e fontes

Esta etapa organiza uma base reproduzível para o estudo da dengue na região. Seus objetivos são integrar notificações e população por município e ano, preservar as definições da base tratada, documentar a origem das variáveis e conferir a consistência dos resultados.

| Fonte de origem | Dados utilizados | Papel na integração |
|---|---|---|
| SINAN/OpenDataSUS — Ministério da Saúde | Notificações de dengue, posteriormente tratadas no PostgreSQL | Numeradores anuais e indicadores de caso |
| IBGE/SIDRA | População municipal, a partir de censos e estimativas | Denominador das taxas |
| IBGE/Localidades | Cadastros de municípios e UFs | Identificação e relacionamento territorial |

A entrada da etapa atual é uma extração da base tratada do banco `dengue-eda`, esquema `public`, ou seu equivalente agregado portátil. O notebook não faz uma nova coleta nas fontes oficiais a cada execução. As fontes e as decisões de tratamento estão descritas na [documentação do banco](database/README.md).

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python | Extração, integração, validação e automação |
| pandas | Leitura dos CSVs, agregações, junções e cálculo das taxas |
| JupyterLab e IPython Kernel | Abertura e execução interativa do notebook |
| nbclient | Execução automatizada do notebook em kernel real |
| PostgreSQL | Armazenamento da base de origem; opcional para executar o pacote portátil |
| Psycopg 3 | Conexão e extração do PostgreSQL |
| python-dotenv | Leitura da configuração privada de conexão |
| CSV, JSON e SHA-256 | Intercâmbio de dados, metadados e verificação de integridade |

As dependências e seus intervalos de versão estão em [`requirements.txt`](requirements.txt). O kit independente de coleta bruta possui suas próprias dependências em `database/reproducao/`.

## Como executar

### 1. Preparar o ambiente

Tenha Python instalado e execute os comandos abaixo na **raiz do repositório**. Os exemplos usam **PowerShell no Windows**:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

A instalação das bibliotecas pode exigir internet. Os comandos usam diretamente o Python do ambiente virtual, sem precisar ativá-lo.

### 2. Executar sem banco de dados

Confira se a cópia do projeto contém `data/processed/insumos_portateis/` e os dicionários em `docs/dicionario_dados.*`. Esses arquivos precisam acompanhar a distribuição do código; somente o arquivo `.ipynb` não é suficiente.

```powershell
$env:DENGUE_MODO_DADOS = 'portatil'
.\.venv\Scripts\python.exe scripts/executar_notebook_coleta_postgresql.py
```

O executor processa o notebook inteiro e salva suas saídas **após a conclusão bem-sucedida de todas as células**. Os painéis e comprovantes são gravados em pastas próprias por execução. Com as dependências instaladas e o pacote presente, esse modo não acessa rede nem PostgreSQL.

### 3. Abrir e explorar o notebook

```powershell
.\.venv\Scripts\python.exe -m jupyterlab
```

Abra `notebooks/01_coleta_integracao.ipynb`, selecione o kernel do ambiente `.venv` e execute as células em ordem. O [dicionário de dados](docs/dicionario_dados.md) também aparece no notebook.

### Modos de entrada

| Modo | Comportamento | Requisitos |
|---|---|---|
| `auto` — padrão | Usa uma extração individual local válida; na ausência dela, seleciona o pacote portátil | Uma das duas entradas disponível |
| `portatil` | Usa os agregados municipais SINAN e as tabelas IBGE da CP1 | `data/processed/insumos_portateis/` e dicionários |
| `postgresql` | Exige os CSVs individuais extraídos do banco | Extração individual válida; conexão ativa apenas para extrair novamente |

O modo pode ser definido por `MODO_DADOS` na configuração do notebook ou pela variável `DENGUE_MODO_DADOS`. Para voltar ao padrão em uma sessão PowerShell onde o modo foi forçado:

```powershell
Remove-Item Env:DENGUE_MODO_DADOS -ErrorAction SilentlyContinue
```

O pacote portátil contém **40.125 linhas de totais municipais do SINAN**, representando as mesmas **5.474.491 notificações**, além de quatro tabelas do IBGE. Ele reproduz os quatro painéis anuais, mas não permite refazer distribuições individuais de idade, sexo ou mês.

## Usar o PostgreSQL

Este caminho é indicado para obter novamente os registros individuais da camada tratada. O servidor precisa estar em execução e conter as tabelas esperadas em `public`. Um arquivo `.dump` precisa ser restaurado antes de servir como banco acessível.

### Configurar a conexão

Copie o modelo para a raiz, caso ainda não exista um `.env` local:

```powershell
Copy-Item database/reproducao/.env.example .env
```

Edite o arquivo com os dados da sua instância:

```dotenv
PGHOST=localhost
PGPORT=5432
PGDATABASE=dengue-eda
PGUSER=seu_usuario
PGPASSWORD=sua_senha_local
```

Ajuste a porta e o nome do banco. O arquivo `.env` e os registros individuais ficam fora do Git. Também é possível manter a configuração fora do repositório e informar seu caminho ao extrator.

### Extrair e executar

```powershell
.\.venv\Scripts\python.exe scripts/extrair_postgresql.py --env '.env'
if ($LASTEXITCODE -ne 0) { throw 'A extração falhou; confira a conexão e a saída do comando.' }

$env:DENGUE_MODO_DADOS = 'postgresql'
.\.venv\Scripts\python.exe scripts/executar_notebook_coleta_postgresql.py
```

A extração usa conexão **somente de leitura**, em isolamento `REPEATABLE READ`, com um único snapshot para as tabelas consultadas. Cada execução cria uma pasta com data e hora, preservando as anteriores.

Outra opção é configurar `REEXTRAIR = True` no notebook, com `.env` na raiz ou `DENGUE_ENV` apontando para o arquivo privado. Selecionar o modo `postgresql` por si só não solicita uma nova extração.

Para instalar a estrutura, restaurar a base completa ou coletar novamente nas fontes oficiais, consulte o [guia do banco](database/README.md). O kit `database/reproducao/` coleta e carrega a camada bruta; ele não recria sozinho a tabela tratada `public.notificacao_dengue_ne` usada nesta etapa. A localização da cópia arquivada do backup está no [guia de recuperação](docs/limpeza_repositorio.md).

## Fluxo de processamento

1. **Selecionar a entrada:** CSVs individuais extraídos do PostgreSQL ou pacote agregado portátil.
2. **Conferir os insumos:** validar hashes, contagens, período e metadados.
3. **Integrar as fontes:** relacionar notificações, população e cadastro territorial, verificando chaves e cardinalidade das junções.
4. **Gerar os painéis:** agregar por município, UF e região, preservando os totais.
5. **Calcular as taxas:** dividir os casos prováveis pela população correspondente e multiplicar por 100.000.
6. **Registrar a execução:** gravar CSVs, auditorias e hashes em diretórios próprios.

Nos painéis estaduais e regionais, numeradores e populações são somados antes do cálculo da incidência. As taxas municipais não são simplesmente somadas ou usadas em média aritmética.

## Resultados e arquivos gerados

A base conferida para **2000–2025** contém **5.474.491 notificações**, **4.178.450 casos prováveis** e **2.884.120 casos confirmados**. Essas categorias não são equivalentes; a medida principal mantém o indicador `caso_provavel` da base tratada.

| Entrega | Conteúdo |
|---|---|
| `painel_municipio_ano.csv` | 46.627 combinações de município e ano, com contagens, população e incidência |
| `painel_uf_ano.csv` | 234 combinações de UF e ano |
| `painel_regiao_ano.csv` | 26 anos da série regional |
| `cobertura_populacao_uf_ano.csv` | 234 combinações de UF e ano para conferir a cobertura populacional |
| Manifestos e comprovantes JSON | Origem dos insumos, verificações, totais e hashes das saídas |

Os CSVs são gravados em subpastas de `data/processed/postgresql/relatorio_2000_2025/`. Os comprovantes ficam em `data/metadata/postgresql/`. Consulte o notebook executado e os manifestos para identificar os caminhos da execução utilizada.

A [versão HTML](outputs/postgresql/01_coleta_integracao.html) permite consultar as saídas já exportadas. O comando de execução do notebook salva o `.ipynb`; ele não atualiza automaticamente esse HTML.

## Organização do repositório

```text
 dengue_nordeste/
 ├── README.md
 ├── requirements.txt
 ├── notebooks/
 │   └── 01_coleta_integracao.ipynb
 ├── scripts/
 │   ├── extrair_postgresql.py
 │   ├── integrar_postgresql.py
 │   ├── preparar_insumos_portateis.py
 │   ├── executar_notebook_coleta_postgresql.py
 │   └── verificar_reproducao_portatil.py
 ├── data/
 │   ├── raw/postgresql/           # Extrações individuais locais, fora do Git
 │   ├── processed/insumos_portateis/            # Insumos agregados para reprodução sem banco
 │   ├── processed/postgresql/     # Painéis e resultados por execução
 │   └── metadata/postgresql/      # Dicionários, manifestos e auditorias
 ├── database/                    # SQL, validações e kit de coleta/carga bruta
 ├── docs/                        # Guias e dicionário semântico
 ├── outputs/postgresql/          # Versão HTML do notebook
 └── .claude/specs/               # Especificações e registro do uso de IA
```

O pipeline anterior, a antiga etapa 02 e o backup completo foram preservados fora da pasta ativa. Consulte [organização e recuperação dos arquivos](docs/limpeza_repositorio.md) antes de buscar resultados antigos.

## Validação e reprodução

As verificações documentadas conferem integridade SHA-256, contagens dos arquivos, unicidade de chaves, cardinalidade das junções e conservação das contagens e da população. Nesta base, não foram encontradas notificações nem casos prováveis sem população correspondente.

O pacote portátil foi testado em uma cópia isolada, sem dados individuais ou credenciais, com instalação das dependências em ambiente virtual novo. As seis células executaram em kernel real, e os quatro painéis foram idênticos por SHA-256 aos resultados previamente validados. Consulte o [comprovante dessa verificação](database/validacao/reproducao_sem_banco.json).

Para repetir a verificação completa:

```powershell
.\.venv\Scripts\python.exe scripts/verificar_reproducao_portatil.py --ambiente-limpo
```

O teste prepara uma cópia temporária e um ambiente virtual novo, podendo precisar de internet para instalar as dependências. Os detalhes estão no [guia de reprodução da CP1](docs/reproducao_portatil.md).

## Regras e limitações dos dados

- **Residência:** o recorte considera residentes do Nordeste, inclusive quando notificados fora da região.
- **Período:** a análise usa o ano da notificação entre 2000 e 2025. Dados de 2026 ficam fora desta etapa; 2025 permanece sujeito a revisão.
- **Definição de caso:** notificações, casos prováveis e confirmados são medidas distintas. A integração mantém as flags da base tratada e não aplica uma nova definição de caso.
- **Duplicidade:** possíveis duplicatas permanecem sinalizadas. A integração não as remove nem confirma automaticamente duplicidade individual.
- **População:** os valores tratados de 2007 e 2023 incluem as interpolações documentadas. Essas escolhas diferem das do pipeline anterior arquivado.
- **Agregação:** o pacote portátil permite reproduzir os painéis anuais; análises individuais de idade, sexo ou mês exigem os dados individuais.
- **Interpretação:** mudanças nas fichas, na presença de descartados, nos cadastros municipais e nas fontes populacionais limitam comparações históricas. As verificações técnicas não substituem revisão epidemiológica.

O [dicionário da CP1](docs/dicionario_dados.md) descreve significado, origem, tipo e regras das variáveis, preservando as indicações de confirmação ainda pendente. A documentação de reprodução também registra pendências relativas às licenças das fontes.

## Problemas comuns

| Situação | Como verificar |
|---|---|
| Python ou bibliotecas não encontrados | Confirme a instalação do Python e execute os comandos com `.venv\Scripts\python.exe` |
| Pacote portátil não localizado | Confira se `data/processed/insumos_portateis/` e os dicionários acompanharam a cópia do projeto |
| Modo PostgreSQL sem arquivos individuais | Execute primeiro o extrator ou use `DENGUE_MODO_DADOS=portatil` |
| Falha de conexão ao banco | Confira serviço ativo, host, porta, banco e credenciais do `.env` |
| Tabela tratada ausente no banco | Use a base completa restaurada; a coleta bruta isolada não produz essa tabela |
| Hash ou contagem divergente | Confira a integridade dos arquivos e seu manifesto antes de reutilizar os dados |
| Saída inesperada ao alternar os modos | Revise `MODO_DADOS`, `DENGUE_MODO_DADOS` e `REEXTRAIR` antes de executar novamente |

## Documentação complementar

| Documento | Assunto |
|---|---|
| [Reprodução da CP1](docs/reproducao_portatil.md) | Execução em outra máquina, pacote portátil e teste isolado |
| [Dicionário de dados](docs/dicionario_dados.md) | Significado e regras das variáveis |
| [Extração PostgreSQL](docs/extracao_postgresql.md) | Consultas de origem, snapshot e conferências da extração |
| [Notebook e integração](docs/notebook01_postgresql.md) | Processamento, painéis e verificações |
| [Banco PostgreSQL](database/README.md) | Modelo, tecnologias, restauração e coleta bruta |
| [Organização e recuperação](docs/limpeza_repositorio.md) | Localização dos arquivos anteriores e do backup |
| [Registro de uso de IA](.claude/specs/99_uso_ia.md) | Uso de ferramentas de IA no desenvolvimento do projeto |
