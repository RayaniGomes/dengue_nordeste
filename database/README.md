# Banco de dados — Dengue no Nordeste

Base PostgreSQL do projeto de análise exploratória da dengue no Nordeste. Reúne notificações do **SINAN/OpenDataSUS**, dados populacionais do **IBGE/SIDRA** e cadastros territoriais do **IBGE/Localidades**, permitindo relacionar notificações, municípios, estados e população ao longo do tempo.

O banco apoia consultas sobre evolução anual, sazonalidade, distribuição territorial e incidência por 100 mil habitantes. O período analítico é **2000–2025**, com foco nos residentes de **MA, PI, CE, RN, PB, PE, AL, SE e BA**. A camada bruta contém notificações de todo o Brasil e inclui **2026, ainda parcial e fora da análise**.

> Este diretório documenta o pipeline PostgreSQL revisado. O pipeline anterior da [raiz do repositório](../README.md) possui outras escolhas metodológicas, inclusive para a população de 2023. Consulte as regras desta versão antes de combinar resultados.

## Sumário

- [Tecnologias](#tecnologias)
- [Organização dos arquivos](#organização-dos-arquivos)
- [Conteúdo e modelo do banco](#conteúdo-e-modelo-do-banco)
- [Pré-requisitos](#pré-requisitos)
- [Como executar](#como-executar)
- [Consultas de exemplo](#consultas-de-exemplo)
- [Validação e rastreabilidade](#validação-e-rastreabilidade)
- [Cuidados na interpretação](#cuidados-na-interpretação)
- [Problemas comuns](#problemas-comuns)

## Tecnologias

| Tecnologia | Uso no projeto |
|---|---|
| PostgreSQL 18 | Armazenamento relacional, SQL, particionamento anual, índices e integridade referencial |
| `psql`, `createdb`, `pg_dump` e `pg_restore` | Acesso, criação, exportação e restauração do banco |
| Python | Automação da coleta e carga; execução de origem com Python 3.14.6 |
| pandas | Organização e transformação dos dados populacionais |
| Requests | Download dos arquivos e consulta às fontes oficiais |
| Psycopg 3 | Conexão e carga de dados no PostgreSQL |
| PyArrow | Leitura e contagem dos CSVs em lotes |
| python-dotenv e tzdata | Configuração local e registro de horários com fuso |
| SHA-256 e JSON | Verificação de integridade, manifestos e relatórios de validação |

As dependências Python estão em [`reproducao/requirements.txt`](reproducao/requirements.txt). Elas são necessárias para uma nova coleta; a restauração do backup exige apenas PostgreSQL e suas ferramentas.

## Organização dos arquivos

```text
 database/
 ├── README.md
 ├── estrutura.sql                 # Estrutura SQL, sem registros
 ├── backups/                      # Backup completo local, fora do Git
 ├── validacao/                    # Comprovantes, contagens e hashes do pacote
 └── reproducao/
     ├── .env.example              # Modelo de configuração da conexão
     ├── requirements.txt
     ├── scripts/executar_coleta_carga.py
     ├── src/                      # Configuração, coleta e carga
     ├── data/                     # Downloads locais, gerados na execução
     ├── reports/validation/       # Resultados das novas execuções
     ├── docs/                     # Registro da coleta
     └── .claude/specs/            # Fontes, dicionário e decisões metodológicas
```

| Arquivo | Finalidade |
|---|---|
| [`estrutura.sql`](estrutura.sql) | Criação dos dois esquemas, tabelas, partições, índices e relações, sem dados |
| [`validacao/coleta_20261113_carga.json`](validacao/coleta_20261113_carga.json) | Contagens anuais reconciliadas entre CSV e PostgreSQL |
| [`validacao/coleta_20261113_manifesto.json`](validacao/coleta_20261113_manifesto.json) | Fontes, datas, tamanhos e SHA-256 dos insumos |
| [`validacao/backup_completo.json`](validacao/backup_completo.json) | Conclusão, tamanho, hash e verificações do backup |
| [`validacao/backup_catalogo.txt`](validacao/backup_catalogo.txt) | Catálogo de objetos do backup |
| `backups/dengue-eda_completo_2026-11-13.dump` | Cópia lógica completa, em formato customizado do PostgreSQL com compressão gzip |

**O backup não acompanha um clone do repositório.** Ele tem aproximadamente **3,37 GB** e fica fora do Git. Para restaurar os dados existentes, obtenha esse arquivo com quem mantém o projeto e coloque-o no caminho indicado. Este pacote ainda não informa um link público para download. Como alternativa, execute a coleta nas fontes oficiais.

## Conteúdo e modelo do banco

O snapshot de **13/11/2026** foi exportado do banco `dengue-eda`, PostgreSQL **18.4**, com aproximadamente **17,36 GB** no ambiente de origem. A exportação é uma cópia lógica; ela não move o serviço PostgreSQL.

### Esquemas disponíveis

| Esquema | Conteúdo e uso |
|---|---|
| `public` | Versão usada pelo relatório revisado: 5.598.410 notificações tratadas, incluindo 2026, e 4.178.450 casos prováveis no período 2000–2025 |
| `coleta_20261113` | Nova coleta: 32.530.748 notificações brutas nacionais de 2000–2026, 44.850 linhas de população bruta do Nordeste, 27 UFs, 5.571 municípios e 48.421 linhas de população tratada |

A nova coleta preserva `public`. A diferença entre as duas versões brutas está em 2026: a coleta nova possui 18.746 registros adicionais. O recorte e a limpeza das notificações do Nordeste são etapas posteriores à carga bruta.

### Tabelas principais

| Tabela | Esquema | Descrição |
|---|---|---|
| `sinan_dengue` | Ambos | Notificações brutas nacionais, particionadas por `ano_arquivo`; campos de origem mantidos como texto |
| `sinan_dengue_carga` | Ambos | Controle por arquivo anual: linhas, bytes nulos removidos e data da carga |
| `estado` | Ambos | Cadastro de UFs, com código, sigla e região |
| `municipio` | Ambos | Cadastro territorial, com códigos IBGE de seis e sete dígitos e UF |
| `populacao_ne` | Ambos | População municipal do Nordeste coletada no SIDRA, com fonte e ano |
| `populacao_municipio_ano` | Ambos | População tratada para as análises, incluindo valores interpolados identificados pela fonte |
| `notificacao_dengue_ne` | Apenas `public` | Notificações tratadas de residentes do Nordeste, com datas, classificação e indicadores de caso provável, confirmado e possível duplicata |

As relações usam `estado.uf_cod` e `municipio.cod_mun7`. A população é identificada por **município e ano**. As notificações tratadas têm município de residência e, quando disponível, município de notificação. Consulte o [dicionário do banco](reproducao/.claude/specs/02_banco.md) para os campos e regras detalhados.

## Pré-requisitos

- PostgreSQL **18**, com servidor instalado e em execução e ferramentas de linha de comando disponíveis.
- Host, porta, usuário e senha de uma instância acessível. O usuário precisa poder criar o banco ou receber um banco vazio já criado; a coleta também exige permissão para criar esquemas e tabelas.
- Espaço para o banco, backup e arquivos temporários. Use os **17,36 GB do banco de origem** como referência, reservando espaço adicional para índices, WAL e processamento. Uma nova coleta também guarda ZIPs e CSVs descompactados.
- Para coletar novamente: Python compatível com as dependências e acesso à internet.

Os exemplos abaixo usam **PowerShell no Windows**. Nos caminhos de restauração e criação da estrutura, execute a partir da **raiz do repositório**. Ajuste o caminho do PostgreSQL, a porta e o usuário à sua instalação. A porta padrão é `5432`; o ambiente de origem usava `55432`.

## Como executar

Escolha um dos caminhos:

| Objetivo | Caminho |
|---|---|
| Consultar a versão completa preservada, incluindo as tabelas tratadas do relatório | A — Restaurar o backup |
| Inspecionar ou desenvolver sobre o modelo vazio | B — Criar apenas a estrutura |
| Buscar os dados oficiais novamente em um esquema separado | C — Executar coleta e carga |

### A — Restaurar o backup completo

**1. Configure a conexão e confira se o servidor responde:**

```powershell
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$pgHostLocal = 'localhost'
$pgPortLocal = 5432
$pgUserLocal = 'postgres'

& "$pgBin\pg_isready.exe" -h $pgHostLocal -p $pgPortLocal
```

O servidor deve indicar que está aceitando conexões. Os comandos seguintes solicitarão a senha quando necessário.

**2. Confira a integridade do arquivo recebido:**

```powershell
Get-FileHash -Algorithm SHA256 'database/backups/dengue-eda_completo_2026-11-13.dump'
Get-Content 'database/validacao/backup_completo.json'
```

Compare o hash calculado com o campo `sha256` do comprovante. Um arquivo `.dump.part` representa uma exportação incompleta: use somente o `.dump` final com o comprovante de conclusão.

**3. Crie um banco novo e restaure:**

```powershell
& "$pgBin\createdb.exe" -h $pgHostLocal -p $pgPortLocal -U $pgUserLocal dengue_restaurada
if ($LASTEXITCODE -ne 0) { throw 'Banco novo não foi criado; interrompa a restauração.' }

& "$pgBin\pg_restore.exe" -h $pgHostLocal -p $pgPortLocal -U $pgUserLocal --dbname dengue_restaurada --no-owner --no-acl --exit-on-error 'database/backups/dengue-eda_completo_2026-11-13.dump'
if ($LASTEXITCODE -ne 0) { throw 'Restauração interrompida por erro; confira a saída.' }
```

O nome `dengue_restaurada` mantém a cópia separada do banco de origem. **Não aplique `estrutura.sql` antes do backup:** o `.dump` já contém estrutura e dados. As opções `--no-owner` e `--no-acl` permitem restaurar sem reproduzir os proprietários e permissões do ambiente original.

**4. Conecte-se e confira os objetos:**

```powershell
& "$pgBin\psql.exe" -X -h $pgHostLocal -p $pgPortLocal -U $pgUserLocal -d dengue_restaurada
```

Dentro do `psql`:

```sql
\dn
\dt public.*
\dt coleta_20261113.*
SELECT current_database(), version();
```

Use `\q` para sair. Também é possível conectar pelo pgAdmin com os mesmos dados de host, porta, usuário e banco.

### B — Criar apenas a estrutura

Este caminho cria tabelas vazias. Use outro banco novo e as variáveis de conexão definidas no caminho A:

```powershell
& "$pgBin\createdb.exe" -h $pgHostLocal -p $pgPortLocal -U $pgUserLocal dengue_estrutura
if ($LASTEXITCODE -ne 0) { throw 'Banco vazio não foi criado; interrompa a execução.' }

& "$pgBin\psql.exe" -X -h $pgHostLocal -p $pgPortLocal -U $pgUserLocal -d dengue_estrutura -v ON_ERROR_STOP=1 -f 'database/estrutura.sql'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao aplicar a estrutura; confira a saída.' }
```

Isso não baixa nem carrega registros. Para uma nova coleta, o caminho C prepara seu próprio esquema e dispensa a aplicação prévia desse SQL.

### C — Executar coleta e carga

**1. Prepare o ambiente Python:**

```powershell
Set-Location database/reproducao
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Se `.env` já existir, edite-o sem sobrescrever suas configurações. Os comandos usam diretamente o Python do ambiente virtual, sem exigir sua ativação.

**2. Preencha o `.env` local**, apontando para um banco PostgreSQL já existente:

```dotenv
PGHOST=localhost
PGPORT=5432
PGDATABASE=dengue_coleta
PGUSER=postgres
PGPASSWORD=sua_senha_local
```

O nome `dengue_coleta` é um exemplo; crie esse banco antes ou informe outro existente. O script cria o esquema, mas **não cria o banco nem inicia o servidor**. Mantenha a senha apenas na configuração local; o `.env` está ignorado pelo Git.

**3. Execute o piloto e, se concluir com sucesso, a carga completa:**

```powershell
.\.venv\Scripts\python.exe -B scripts/executar_coleta_carga.py --env .env --schema coleta_20261114 --piloto
if ($LASTEXITCODE -ne 0) { throw 'Piloto falhou; corrija o erro antes da carga completa.' }

.\.venv\Scripts\python.exe -B scripts/executar_coleta_carga.py --env .env --schema coleta_20261114
if ($LASTEXITCODE -ne 0) { throw 'Coleta ou carga falhou; confira a saída e o manifesto.' }
```

Substitua `coleta_20261114` por um nome exclusivo com prefixo `coleta_`, usando letras minúsculas, números e sublinhados.

O piloto testa o download do SINAN de 2026 e uma consulta do IBGE, **sem carregar tabelas**. A execução completa coleta 2000–2026, carrega o esquema isolado e valida as contagens. A rotina rejeita `public` como destino e verifica se seu resumo foi preservado.

Os arquivos brutos ficam em `reproducao/data/raw/<esquema>/`, acompanhados de `manifesto.json`. Os resultados ficam em `reproducao/reports/validation/<esquema>_carga.json` e `<esquema>_manifesto.json`. O cache só é reutilizado quando URL, tamanho e hash conferem. Em caso de falha, consulte o manifesto e repita o comando com o mesmo esquema para aproveitar os arquivos íntegros.

**Limite desta reprodução:** os scripts incluídos realizam coleta e carga do SINAN/IBGE; não recriam `public.notificacao_dengue_ne` nem todas as análises do relatório. Para consultar essa camada já tratada, restaure o backup. Uma nova coleta pode incorporar revisões das fontes e produzir contagens diferentes do snapshot.

## Consultas de exemplo

Execute no `psql` ou no editor SQL do pgAdmin após restaurar o backup.

### Casos prováveis por ano na versão do relatório

```sql
SELECT ano, count(*) AS casos_provaveis
FROM public.notificacao_dengue_ne
WHERE caso_provavel AND ano BETWEEN 2000 AND 2025
GROUP BY ano
ORDER BY ano;
```

### Municípios com mais casos prováveis em 2025

```sql
SELECT e.sigla AS uf, m.nome AS municipio, count(*) AS casos_provaveis
FROM public.notificacao_dengue_ne AS n
JOIN public.municipio AS m ON m.cod_mun7 = n.cod_mun7
JOIN public.estado AS e ON e.uf_cod = m.uf_cod
WHERE n.caso_provavel AND n.ano = 2025
GROUP BY e.sigla, m.cod_mun7, m.nome
ORDER BY casos_provaveis DESC
LIMIT 10;
```

### Conferir o controle de carga da nova coleta

```sql
SELECT ano_arquivo, linhas, bytes_nulos, carregado_em
FROM coleta_20261113.sinan_dengue_carga
ORDER BY ano_arquivo;
```

Essa última consulta lê o controle da carga. Para recontar os registros efetivamente armazenados, use `SELECT ano_arquivo, count(*) FROM coleta_20261113.sinan_dengue GROUP BY ano_arquivo ORDER BY ano_arquivo;`; a operação percorre milhões de linhas e pode levar mais tempo. Ao usar uma coleta própria, substitua o nome do esquema.

## Validação e rastreabilidade

O pacote registra as URLs de origem, datas de coleta, tamanhos e hashes SHA-256 dos insumos. As contagens anuais dos CSVs foram feitas com parser independente e reconciliadas com o PostgreSQL e a tabela de controle. Nenhum município da população ficou sem correspondência no cadastro na coleta de 13/11/2026.

O backup foi verificado por catálogo (`pg_restore --list`) e leitura/descompressão integral. **Não foi executada uma restauração completa em outra instância nessa preparação**; os comprovantes não representam um teste de restauração de ponta a ponta.

Referências internas:

- [Registro da coleta e armazenamento](reproducao/docs/coleta_armazenamento_2026-11-13.md).
- [Fontes e formas de obtenção](reproducao/.claude/specs/01_fontes.md).
- [Dicionário e modelo do banco](reproducao/.claude/specs/02_banco.md).
- [Decisões metodológicas e pendências](reproducao/.claude/specs/03_decisoes.md).

## Cuidados na interpretação

- **Notificação, caso provável e caso confirmado são medidas distintas.** Use os indicadores documentados da camada tratada e informe a definição adotada. A presença de descartados nos arquivos oficiais varia entre anos.
- O recorte do Nordeste considera o **município de residência**, incluindo residentes notificados fora da região.
- Na série anual tratada, `ano` representa o ano da notificação; `ano_arquivo` identifica o CSV de origem. A sazonalidade usa as datas de sintomas válidas.
- A população tratada deste pipeline interpola **2007 e 2023**, identificando esses valores como `interpolada`. A população bruta preserva as lacunas da fonte.
- A incidência usa casos e população do **mesmo município e ano**, multiplicados por 100.000. Não calcule taxas diretamente sobre as notificações brutas sem aplicar a definição de caso e o recorte.
- Possíveis duplicatas são sinalizadas; os dados públicos não permitem confirmar automaticamente duplicidade individual.
- **2026 é parcial**, e 2025 está sujeito a revisão. Cadastros e limites municipais também podem mudar ao longo do tempo.
- Contagens e hashes validam aspectos técnicos da carga; a interpretação dos resultados exige revisão epidemiológica.

## Problemas comuns

| Situação | O que conferir |
|---|---|
| `psql` ou `pg_restore` não encontrado | Ajuste `$pgBin` para a pasta `bin` do PostgreSQL 18 ou configure o `PATH` |
| Conexão recusada | Verifique se o serviço está ativo e se host e porta correspondem à instância correta |
| Falha de autenticação | Confira usuário, senha e regras de acesso da instância; na coleta, revise o `.env` |
| Banco de destino já existe | Escolha outro nome vazio; os exemplos interrompem a execução se a criação falhar |
| Relações já existem durante a restauração | Use um banco novo e não aplique `estrutura.sql` antes do `.dump` |
| Backup ausente após clonar | Obtenha o arquivo completo com quem mantém o projeto ou faça uma nova coleta |
| Esquema recusado pela coleta | Use um nome exclusivo com prefixo `coleta_`; esquemas preexistentes sem o marcador da rotina são rejeitados |
| Tabela tratada ausente após nova coleta | A coleta não executa a limpeza das notificações; essa camada está preservada no backup |
| Falta de espaço | Considere banco, WAL, backup, ZIPs e CSVs descompactados no planejamento |

Backups e downloads volumosos permanecem fora do versionamento. Publique scripts, estrutura, documentação e metadados; a distribuição do `.dump` deve usar armazenamento externo.

## Extrair os dados do banco em execução

Consulte [extração PostgreSQL](../docs/extracao_postgresql.md) e execute `scripts/extrair_postgresql.py --env CAMINHO_DO_ENV` com o Python do ambiente do repositório. Essa rotina exporta a base tratada de 2000–2025 em modo somente de leitura, separada da coleta bruta nova.
