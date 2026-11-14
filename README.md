# Dengue no Nordeste — coleta e integração pelo PostgreSQL

Projeto IMD1151, 2026.2. Base tratada de residentes do Nordeste, período 2000–2025, usada no relatório revisado.

Abra [01_coleta_integracao.ipynb](notebooks/01_coleta_integracao.ipynb) ou a [versão HTML](outputs/postgresql/01_coleta_integracao.html). O notebook confere os dados extraídos do PostgreSQL e os integra à população e ao cadastro municipal. A etapa seguinte ainda não faz parte desta pasta ativa.

## Executar

O ambiente `.venv` e a extração local atual foram preservados. Para preparar o ambiente em outra instalação:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para executar o notebook inteiro e salvar as saídas após sucesso:

```powershell
.\.venv\Scripts\python.exe scripts/executar_notebook_coleta_postgresql.py
```

A execução padrão reaproveita a extração local concluída e confere seus hashes. Para extrair novamente do banco em execução, configure um `.env` privado e execute:

```powershell
.\.venv\Scripts\python.exe scripts/extrair_postgresql.py --env CAMINHO_DO_ENV
```

O modelo de configuração está em `database/reproducao/.env.example`. O notebook também permite `REEXTRAIR = True`, usando `.env` na raiz ou a variável `DENGUE_ENV`. A conexão de extração é somente de leitura. Dados individuais e configurações privadas ficam fora do Git.

## Organização atual

- `notebooks/`: primeiro notebook PostgreSQL, executado.
- `scripts/`: extração, integração e execução do notebook.
- `data/raw/postgresql/`: CSVs individuais locais.
- `data/processed/postgresql/`: resumo e painéis agregados.
- `data/metadata/postgresql/`: dicionário, manifestos e verificações da integração.
- `docs/`: instruções da extração, do notebook e da organização dos arquivos.
- `database/`: estrutura SQL, comprovantes e kit independente de reprodução do banco.
- `outputs/postgresql/`: HTML do notebook.
- `.claude/specs/99_uso_ia.md`: registro do uso de IA.

Foram conferidas 5.474.491 notificações e 4.178.450 casos prováveis, integrados em 46.627 municípios-ano, 234 UFs-ano e 26 anos regionais. O numerador principal mantém a flag `caso_provavel`; possíveis duplicatas continuam sinalizadas. A população preserva as interpolações documentadas de 2007 e 2023. Dados de 2026 estão fora desta etapa, e 2025 permanece sujeito a revisão.

Consulte [extração](docs/extracao_postgresql.md), [notebook e integração](docs/notebook01_postgresql.md) e [banco PostgreSQL](database/README.md).

O pipeline anterior e o backup completo foram preservados fora do repositório. Consulte [limpeza e recuperação](docs/limpeza_repositorio.md) para localizá-los. A limpeza não alterou o serviço PostgreSQL nem a base de origem. Não foram realizados commits ou pushes.
