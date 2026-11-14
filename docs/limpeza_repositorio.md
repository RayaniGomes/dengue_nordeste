# Organização e recuperação de arquivos

A pasta ativa foi reduzida ao primeiro notebook PostgreSQL, seus scripts, os dados atuais, os painéis integrados e a documentação necessária. O ambiente `.venv`, a pasta `.git`, o registro de IA, as especificações e o kit de reprodução do banco foram mantidos.

## Arquivo externo

Os arquivos retirados estão preservados em:

`D:\Users\Rayani\Downloads\codex\Ciências de Dados\backups_integracao\limpeza_repositorio_20261113_223923`

Foram movidos 304 arquivos (4,295,526,598 bytes), incluindo o pipeline anterior, a antiga etapa 02, dados e resultados anteriores, históricos, temporários e o backup completo. A movimentação ocorreu no mesmo volume, com caminhos verificados e conferência de existência e tamanho de cada arquivo. Não houve exclusão definitiva.

O inventário está em `../database/validacao/limpeza_repositorio.json` e em `manifesto_limpeza.json` no arquivo externo. O subdiretório `estado_antes/` guarda cópias da documentação e configuração do projeto anteriores à organização.

## Recuperar

Localize o caminho original de um item no inventário. O mesmo caminho relativo existe dentro do arquivo externo. Copie somente o item necessário de volta para a pasta do projeto, conferindo antes se já existe uma versão atual. O backup completo está em `database/backups/dengue-eda_completo_2026-11-13.dump` dentro desse arquivo externo.

Não foram alterados o serviço PostgreSQL, os dados do banco nem as outras cópias do projeto. O Git pode mostrar exclusões dos arquivos antigos da pasta ativa; os arquivos permanecem no arquivo externo e nenhum commit ou push foi realizado.

Após a organização, o notebook 01 foi reexecutado sem erros em kernel real. Os quatro painéis agregados são idênticos por SHA-256 aos anteriores. As dependências do fluxo atual foram reunidas em `requirements.txt`.
