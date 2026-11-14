# Extração da base tratada a partir do PostgreSQL

Execução concluída em 2026-11-13T22:18:51.708987-03:00, diretamente do banco `dengue-eda`, esquema `public`. Recorte escolhido: residentes do Nordeste e ano de notificação entre 2000 e 2025, conforme a base usada no relatório revisado. Não foi realizada nova coleta nas fontes externas.

## Dados extraídos

Os cinco arquivos CSV compactados estão em `data/raw/postgresql/relatorio_2000_2025/20261113_221719/`:

| Arquivo | Registros | Conteúdo |
|---|---:|---|
| `notificacao_dengue_ne.csv.gz` | 5,474,491 | Todas as notificações tratadas do período, com as 16 colunas originais e flags preservadas |
| `populacao_municipio_ano.csv.gz` | 46,627 | Denominador tratado, incluindo as interpolações previstas nas especificações |
| `populacao_ne.csv.gz` | 43,056 | População consolidada do SIDRA no período e nas nove UFs |
| `municipio_ne.csv.gz` | 1,794 | Cadastro dos municípios do Nordeste |
| `estado_ne.csv.gz` | 9 | Cadastro das nove UFs do Nordeste |

A pasta `raw` identifica a cópia de entrada desta extração. A tabela de notificações de origem já foi tratada no PostgreSQL; esses arquivos não são o SINAN bruto nacional. Os registros individuais permanecem fora do Git, conforme a organização do projeto.

O resumo anual publicável está em `data/processed/postgresql/relatorio_2000_2025/20261113_221719/resumo_anual.csv`, com 26 linhas. Os metadados estão em `data/metadata/postgresql/relatorio_2000_2025/20261113_221719/`:

- `manifesto.json`: consultas SQL, snapshot, período, contagens do banco e dos arquivos, tamanho e SHA-256.
- `dicionario.json`: nomes, tipos e nulabilidade das colunas de origem.

O banco forneceu 4,178,450 casos prováveis e 2,884,120 confirmados no período. A extração inclui todas as notificações; para usar o numerador principal do relatório, selecione `caso_provavel = true`. Possíveis duplicatas foram mantidas e sinalizadas; a extração não redefine caso, idade, sexo, calendário, município ou população. O identificador `id` é a chave local do banco, não um identificador público original do SINAN.

## Verificações

A conexão foi somente de leitura, em isolamento REPEATABLE READ, com um único snapshot para todas as consultas. Cada CSV foi relido com parser independente de COPY. As contagens das cinco tabelas coincidiram com o PostgreSQL. Para as notificações, também coincidiram por ano as contagens de prováveis, confirmados, possíveis duplicatas e ausências de idade, sexo e mês dos sintomas. Foram encontrados 0 casos prováveis sem população correspondente. O parser foi testado com quebras entre aspas, aspas escapadas, ausentes, idade zero e rejeição de ano fora do período.

Não foi executada a EDA nesta extração. Os arquivos anteriores e os dois esquemas do banco foram preservados. A base nova bruta `coleta_20261113` e os dados de 2026 não foram usados nesta execução.

## Repetir a extração nesta pasta

```powershell
.\.venv\Scripts\python.exe -m pip install -r database/requirements-extracao.txt
.\.venv\Scripts\python.exe scripts/extrair_postgresql.py --env CAMINHO_DO_ENV
```

O arquivo privado pode estar fora do repositório e deve conter `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` e `PGPASSWORD`. Use aspas se o caminho tiver espaços. As dependências foram instaladas no `.venv` desta pasta. Cada execução cria uma pasta com data e hora, sem substituir extrações anteriores. O script consulta apenas o esquema `public`, no período 2000–2025. O banco deve estar em execução; o backup `.dump` não é uma conexão ativa. Para outra máquina, restaure o banco conforme `database/README.md`.

Para abrir as notificações com pandas, preservando os códigos como texto e interpretando os booleanos exportados como `t`/`f`:

```python
from pathlib import Path
import pandas as pd
arquivo = Path('data/raw/postgresql/relatorio_2000_2025/20261113_221719/notificacao_dengue_ne.csv.gz')
dados = pd.read_csv(arquivo, dtype={'cod_mun7': 'string', 'cod_mun7_notificacao': 'string'},
                    true_values=['t'], false_values=['f'])
provaveis = dados.loc[dados['caso_provavel']]
```

O pipeline anterior desta raiz tem outras escolhas metodológicas. As saídas desta extração estão em uma subpasta própria e não substituem seus resultados. Nenhum commit ou push foi realizado.
