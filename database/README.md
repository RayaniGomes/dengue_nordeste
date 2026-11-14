# Banco PostgreSQL

Banco de origem: `dengue-eda`, PostgreSQL 18.4. O esquema `public` contém a versão tratada usada no relatório; `coleta_20261113` guarda a coleta bruta adicional. O fluxo ativo usa apenas `public`, 2000–2025.

## Arquivos mantidos

- `estrutura.sql`: estrutura dos dois esquemas, sem registros.
- `validacao/`: comprovantes da coleta, do backup, do notebook e da organização dos arquivos.
- `reproducao/`: kit independente com código de coleta/carga, fontes, decisões e dependências para reconstruir o banco quando necessário.

As dependências do fluxo ativo estão em `../requirements.txt`; o kit independente conserva seu próprio arquivo de dependências.

## Backup completo externo

O backup de 3.371.550.780 bytes foi retirado da pasta ativa para manter o repositório leve. Sua localização atual é:

`D:\Users\Rayani\Downloads\codex\Ciências de Dados\backups_integracao\limpeza_repositorio_20261113_223923\database\backups\dengue-eda_completo_2026-11-13.dump`

SHA-256 registrado na geração: `e4d238e064a95dc005b1b044771e7ef87ffbd79d05ab3183e8c76b54d54d3117`. O catálogo e a leitura/descompressão integral foram verificados na criação; uma restauração completa em outra instância não foi executada. O arquivo foi movido no mesmo volume e conferido por tamanho nesta limpeza.

O comprovante `validacao/backup_completo.json` foi atualizado com o caminho relativo atual. Consulte também [organização e recuperação](../docs/limpeza_repositorio.md).

Para restaurar, use PostgreSQL 18 e um banco novo, configurando usuário e porta:

```powershell
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$backup = 'CAMINHO_DO_BACKUP_COMPLETO.dump'
& "$pgBin\createdb.exe" -h localhost -p 55432 -U SEU_USUARIO dengue_restaurada
if ($LASTEXITCODE -ne 0) { throw 'Interrompa: banco novo não foi criado.' }
& "$pgBin\pg_restore.exe" -h localhost -p 55432 -U SEU_USUARIO --dbname dengue_restaurada --no-owner --no-acl --exit-on-error $backup
if ($LASTEXITCODE -ne 0) { throw 'Confira o erro de restauração.' }
```

Não aplique `estrutura.sql` antes de restaurar o backup completo. Para uma instalação somente de estrutura, crie um banco vazio e use `psql` 18 com `-X -v ON_ERROR_STOP=1 -f database/estrutura.sql`.

## Fluxo atual

A [extração PostgreSQL](../docs/extracao_postgresql.md) usa `scripts/extrair_postgresql.py` em modo somente de leitura. O [primeiro notebook](../notebooks/01_coleta_integracao.ipynb) integra os arquivos extraídos e exporta apenas agregados versionáveis. As decisões metodológicas estão em `reproducao/.claude/specs/03_decisoes.md`.
