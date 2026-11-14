# Primeiro notebook — coleta e integração PostgreSQL

Abra [01_coleta_integracao.ipynb](../notebooks/01_coleta_integracao.ipynb). A versão [HTML com saídas](../outputs/postgresql/01_coleta_integracao.html) pode ser aberta no navegador. O notebook foi executado integralmente em kernel real: seis células de código, sem erros.

## Origem e modo da execução

A base é a tabela tratada `public.notificacao_dengue_ne` e as tabelas de população, municípios e UFs do banco `dengue-eda`, para residentes do Nordeste e anos de notificação 2000–2025. Nesta execução, o notebook reaproveitou os CSVs extraídos previamente do PostgreSQL, conferindo os hashes de todas as entradas. Não fez uma nova consulta ao banco nessa execução em cache.

Para extrair novamente, configure `DENGUE_ENV` no ambiente apontando para um `.env` privado, ou configure `.env` na raiz, e altere `REEXTRAIR = True` na célula de configuração. Se não existir extração concluída, o notebook tenta executá-la usando essa configuração. O script de extração usa conexão somente de leitura e snapshot REPEATABLE READ. A coleta bruta `coleta_20261113` é outra versão, fora desta etapa.

## Executar nesta pasta

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r database/requirements-extracao.txt
.\.venv\Scripts\python.exe scripts/executar_notebook_coleta_postgresql.py
```

O executor usa o Python que o iniciou e salva o notebook apenas após sucesso integral. `scripts/verificar_notebook.py` também encaminha a execução para esse mesmo executor em kernel real.

## Integração e saídas

As notificações são lidas em blocos de 200 mil registros. A integração mantém as flags do banco, a população e as interpolações documentadas, sem aplicar outra limpeza nem excluir possíveis duplicatas. As junções têm chaves e cardinalidades validadas. São mantidos os municípios-ano com população e nenhuma notificação; eventuais notificações sem denominador são preservadas e auditadas. Os painéis estaduais e regionais somam os numeradores e as populações antes de calcular a incidência.

| Painel | Linhas |
|---|---:|
| Município-ano | 46627 |
| UF-ano | 234 |
| Região-ano | 26 |
| Cobertura populacional por UF-ano | 234 |

Os caminhos e hashes estão no [comprovante da integração](../data/metadata/postgresql/relatorio_2000_2025/20261113_221719/integracoes/20261113_222826.json). Cada execução cria uma subpasta própria em `data/processed/postgresql/relatorio_2000_2025/`, preservando as anteriores. Os registros individuais continuam em `data/raw/postgresql/`, ignorado pelo Git. O notebook e o HTML mostram somente tabelas agregadas e metadados.

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

## Preservação do pipeline anterior

O notebook anterior está em `historico/notebooks/01_coleta_integracao_pipeline_anterior.ipynb`, com hash em `preservacao_01.json`. Os originais de `preparar_documentacao.py` e `verificar_notebook.py` foram preservados em `historico/scripts/`.

O gerador antigo `scripts/preparar_documentacao.py` agora grava seu notebook em `historico/gerados/01_coleta_integracao.ipynb`, sem sobrescrever a versão PostgreSQL nem a cópia histórica. Esse gerador continua pertencendo ao pipeline anterior. O notebook `02_limpeza_eda.ipynb` também permanece nessa versão anterior; ele não foi executado nem adaptado nesta tarefa e não constitui a continuação automática do novo primeiro notebook.

Nenhum commit ou push foi realizado.
