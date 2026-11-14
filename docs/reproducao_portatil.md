# Reprodução da CP1 em outra máquina

A CP1 pede notebook de coleta com duas fontes integradas ou uma fonte complexa via API, e dicionário de dados. O notebook 01 integra o SINAN e o IBGE e apresenta o dicionário semântico. Há dois modos de entrada, com as mesmas regras de tratamento e integração.

## Modo portátil: sem banco e sem credenciais

Obtenha a versão do repositório que inclua `data/processed/insumos_portateis/` e `docs/dicionario_dados.*`. Esses arquivos são parte da entrega; copiar somente o `.ipynb` não é suficiente. Nesta preparação eles foram criados localmente e ainda precisam acompanhar o commit/push que o grupo autorizar.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/executar_notebook_coleta_postgresql.py
```

Sem uma extração individual disponível, o modo `auto` seleciona o pacote agregado. Ele carrega duas fontes de origem: notificações SINAN agregadas por município/ano e população/cadastro IBGE. Não acessa rede nem PostgreSQL durante a execução do notebook; instalar as dependências pode exigir internet. Os arquivos de entrada já foram obtidos de uma extração real e validada do banco, e o manifesto conserva sua proveniência.

Para forçar o modo portátil mesmo com os CSVs individuais presentes, configure `MODO_DADOS = "portatil"` no notebook ou `DENGUE_MODO_DADOS=portatil` no ambiente. O notebook continua gravando painéis e comprovantes em pastas próprias por execução.

## Modo individual PostgreSQL

Configure um `.env` privado, mantenha o banco em execução e use `scripts/extrair_postgresql.py --env CAMINHO_DO_ENV`. O notebook pode consultar novamente o banco com `REEXTRAIR = True`; `MODO_DADOS = "postgresql"` exige uma extração individual disponível. A conexão de extração é somente de leitura.

O kit `database/reproducao/` documenta a coleta e a carga bruta das fontes originais. Ele não deve ser confundido com a restauração completa da camada tratada; para esta, use o backup e as instruções de `database/README.md`. Esse backup não é necessário para reproduzir a CP1 no modo portátil.

## Dicionário de dados

O [dicionário legível](dicionario_dados.md) descreve 61 combinações de tabela/variável: nome, tipo, significado, origem e regras/unidade. A versão CSV é mostrada integralmente no notebook; a versão JSON permite conferência por hash. As descrições cobrem as tabelas individuais de origem, os agregados SINAN, o IBGE e os painéis derivados. As legendas cuja confirmação oficial está pendente continuam identificadas como pendentes.

## Verificar a reprodução

```powershell
.\.venv\Scripts\python.exe scripts/verificar_reproducao_portatil.py --ambiente-limpo
```

O teste cria uma cópia temporária dos arquivos distribuíveis, sem `data/raw`, `.env` ou configuração PostgreSQL. Ele mantém manifestos antigos sem os arquivos individuais, simulando o que ocorre em um clone. Instala `requirements.txt` em um ambiente virtual novo, executa o notebook em kernel real e compara os quatro painéis por SHA-256 com a integração previamente validada.

O resultado é registrado em `database/validacao/reproducao_sem_banco.json`. O teste precisa de um Python base instalado e pode precisar de internet para instalar bibliotecas. O diretório temporário é limpo ao final.

## Limites preservados

O pacote portátil é agregado e suficiente para integração e incidência anual. Não permite novas análises individuais de idade, sexo ou mês. A definição operacional de caso provável, as possíveis duplicatas sinalizadas, as interpolações de população e as decisões pendentes não foram alteradas. O fato de as fontes serem públicas não foi usado como confirmação de licenças ainda pendentes no projeto.

## Resultado da verificação desta preparação

A execução em ambiente virtual novo foi aprovada, com instalação das dependências a partir de `requirements.txt`, sem dados individuais, `.env` ou configuração PostgreSQL. As seis células executaram em kernel real; os quatro painéis foram idênticos por SHA-256 aos resultados previamente validados. O Python base já estava instalado nesta máquina. O dicionário foi conferido contra as colunas de todos os insumos portáteis.

As duas ressalvas da conferência da CP1 foram tratadas nesta cópia local. Para que outra pessoa receba a solução, os novos insumos, scripts e dicionários precisam ser incluídos na publicação que o grupo autorizar. Nenhum commit ou push foi realizado pelo assistente.
