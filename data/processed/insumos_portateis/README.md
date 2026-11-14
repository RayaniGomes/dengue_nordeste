# Insumos portáteis da CP1

Este diretório deve ser versionado junto com `docs/dicionario_dados.*`, `scripts/` e o notebook 01. Ele permite reproduzir a coleta/integração da CP1 sem banco local nem credenciais.

- `insumos/notificacoes_municipio_ano.csv`: totais municipais do SINAN tratado, sem registros individuais.
- `insumos/populacao_municipio_ano.csv.gz`: denominadores tratados do IBGE, com a fonte e as interpolações previstas.
- `insumos/populacao_ne.csv.gz`: população consolidada do SIDRA no recorte.
- `insumos/municipio_ne.csv.gz` e `estado_ne.csv.gz`: cadastro geográfico do IBGE.
- `resumo_anual.csv`: resumo obtido da extração PostgreSQL, usado na reconciliação.
- `manifesto.json`: consultas de origem referenciadas, snapshot, transformações, contagens, fontes e hashes.

O ano é o da notificação e o município é o de residência; o recorte é 2000–2025. Os totais são 5.474.491 notificações e 4.178.450 casos prováveis, conforme a definição operacional documentada. O pacote congela um snapshot da base tratada; ele não é o SINAN bruto nacional e não contém microdados de idade/sexo/mês.

Para preparar um novo snapshot após uma extração e integração individuais validadas, use `python scripts/preparar_insumos_portateis.py --saida data/processed/insumos_portateis_nova_versao`. O gerador preserva uma saída preexistente. Revise as fontes, o dicionário e os resultados antes de substituir um pacote publicado. O notebook usa `data/processed/insumos_portateis/` como caminho padrão do modo portátil.
