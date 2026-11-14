# Primeiro notebook — coleta e integração PostgreSQL

Abra [01_coleta_integracao.ipynb](../notebooks/01_coleta_integracao.ipynb). A versão [HTML com saídas](../outputs/postgresql/01_coleta_integracao.html) pode ser aberta no navegador. O notebook foi executado integralmente em kernel real: seis células de código, sem erros.

## Origem e modo da execução

A base é a tabela tratada `public.notificacao_dengue_ne` e as tabelas de população, municípios e UFs do banco `dengue-eda`, para residentes do Nordeste e anos de notificação 2000–2025. Na execução principal atual, o notebook utilizou o pacote portátil da CP1, derivado do mesmo snapshot PostgreSQL e conferido por SHA-256. Não foi necessária conexão ao banco. A leitura individual em blocos continua disponível quando os CSVs locais existem; consulte [reprodução da CP1](reproducao_portatil.md).

Para extrair novamente, configure `DENGUE_ENV` no ambiente apontando para um `.env` privado, ou configure `.env` na raiz, e altere `REEXTRAIR = True` na célula de configuração. Sem uma extração individual disponível, o modo automático utiliza o pacote CP1 versionado. Uma nova extração é realizada somente quando `REEXTRAIR = True`. O script de extração usa conexão somente de leitura e snapshot REPEATABLE READ. A coleta bruta `coleta_20261113` é outra versão, fora desta etapa.

## Executar nesta pasta

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/executar_notebook_coleta_postgresql.py
```

O executor usa o Python que o iniciou e salva o notebook apenas após sucesso integral.

## Integração e saídas

As notificações são lidas em blocos de 200 mil registros. A integração mantém as flags do banco, a população e as interpolações documentadas, sem aplicar outra limpeza nem excluir possíveis duplicatas. As junções têm chaves e cardinalidades validadas. São mantidos os municípios-ano com população e nenhuma notificação; eventuais notificações sem denominador são preservadas e auditadas. Os painéis estaduais e regionais somam os numeradores e as populações antes de calcular a incidência.

| Painel | Linhas |
|---|---:|
| Município-ano | 46627 |
| UF-ano | 234 |
| Região-ano | 26 |
| Cobertura populacional por UF-ano | 234 |

Os caminhos e hashes estão no [comprovante da integração](../data/metadata/postgresql/relatorio_2000_2025/portatil_20261113/integracoes/20261113_233631.json). Cada execução cria uma subpasta própria em `data/processed/postgresql/relatorio_2000_2025/`, preservando as anteriores. Os registros individuais continuam em `data/raw/postgresql/`, ignorado pelo Git. O notebook e o HTML mostram somente tabelas agregadas e metadados.

## Verificações realizadas

- SHA-256 dos cinco CSVs, resumo anual e dicionário conferido.
- Chaves únicas e junções validadas, sem perda de contagens nem duplicação de população.
- Sete métricas anuais conciliadas com o resumo da extração PostgreSQL.
- Totais preservados: 5.474.491 notificações e 4.178.450 casos prováveis.
- Nenhuma notificação nem caso provável sem população correspondente nesta base.
- Painéis de 234 UFs-ano e 26 anos regionais comparados às tabelas do relatório revisado: população, prováveis e confirmados exatamente iguais; incidências com tolerância relativa 1e-12 e absoluta 1e-10.
- Seis células executadas integralmente em kernel real, nbformat validado e HTML gerado com saídas.
- Notebook anterior preservado e conferido por SHA-256.

O [registro da execução](../database/validacao/notebook01_execucao.json) reúne essas evidências. Isso não substitui revisão pessoal do grupo; decisões pendentes e limitações das fontes continuam abertas. Os métodos de P1–P4 não foram reestimados nesta etapa.

## Arquivo externo do pipeline anterior

O notebook e os scripts anteriores, a antiga etapa 02, seus resultados e o backup completo foram retirados da pasta ativa e preservados externamente. Consulte [organização e recuperação](limpeza_repositorio.md). A etapa ativa contém somente o primeiro notebook PostgreSQL; as etapas seguintes serão desenvolvidas sobre esse fluxo.

Nenhum commit ou push foi realizado.

Após a limpeza, o notebook foi reexecutado em kernel real; os quatro CSVs integrados permaneceram idênticos por SHA-256 aos resultados previamente conferidos.

## Dicionário e modo portátil da CP1

O dicionário semântico completo aparece no notebook e em [dicionario_dados.md](dicionario_dados.md). Os insumos agregados distribuíveis ficam em `data/processed/insumos_portateis/`. Consulte [reproducao_portatil.md](reproducao_portatil.md) para executar sem PostgreSQL e para o teste em ambiente novo.

A reprodução sem banco também foi testada em cópia isolada, com instalação de `requirements.txt` em ambiente virtual novo: seis células sem erros e quatro painéis idênticos por SHA-256. O comprovante está em `database/validacao/reproducao_sem_banco.json`.
