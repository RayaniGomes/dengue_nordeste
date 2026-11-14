# Coleta e armazenamento em PostgreSQL — 13/11/2026

Execução concluída em 2026-11-13T21:25:09.105851-03:00. Banco `dengue-eda`, PostgreSQL 18.4, esquema `coleta_20261113`. Os arquivos estão na pasta original do projeto `dengue_nordeste`, em D:.

## Fontes e cobertura

- SINAN/OpenDataSUS: 27 ZIPs anuais do Brasil, 2000–2026, pelo endpoint oficial documentado em `.claude/specs/01_fontes.md`. O recorte do Nordeste por residência pertence à limpeza posterior, conforme a decisão do projeto.
- IBGE/SIDRA: tabelas 200 (Censos 2000 e 2010), 4714 (Censo 2022) e 6579 (estimativas), em 27 consultas: três tabelas para cada uma das nove UFs do Nordeste.
- IBGE/Localidades: cadastro nacional de UFs e municípios.

Os ZIPs, CSVs e respostas JSON originais estão em `data/raw/coleta_20261113/`. O manifesto registra URLs, datas de coleta, tamanho, SHA-256 e cabeçalhos de atualização disponíveis. Foram preservadas 84 entradas de arquivos originais e derivados. Os dados de 2026 são parciais; o período analítico continua 2000–2025.

## Tabelas carregadas

| Tabela no esquema `coleta_20261113` | Registros | Conteúdo |
|---|---:|---|
| `sinan_dengue` | 32.530.748 | Notificações brutas do Brasil, particionadas em 27 anos |
| `sinan_dengue_carga` | 27 | Controle por ano, contagens e bytes nulos removidos |
| `populacao_ne` | 44.850 | População municipal consolidada do SIDRA |
| `estado` | 27 | UFs do Brasil |
| `municipio` | 5.571 | Cadastro nacional de municípios |
| `populacao_municipio_ano` | 48.421 | População válida e interpolações já previstas no projeto |

O SINAN foi carregado por COPY, com campos originais como texto e uma transação por ano. A única alteração foi a remoção de 1 byte 0x00, em 2008, registrada no controle. Os arquivos de origem permanecem preservados. O IBGE foi carregado em uma transação única; manteve-se a prioridade dos censos e a interpolação de 2007 e 2023.

Um ANALYZE foi interrompido após o COPY confirmado para ajustar `default_statistics_target=10` nas novas conexões da rotina. Os anos confirmados foram reaproveitados e as estatísticas pendentes foram concluídas. Trata-se da amostragem do otimizador de consultas; as contagens foram verificadas por leitura real das tabelas. O evento está registrado no manifesto.

## Verificações realizadas

- Piloto SINAN 2026 e uma consulta SIDRA aprovado antes da coleta completa.
- Extração integral dos ZIPs, com verificação de integridade do leitor ZIP; arquivos e cache conferidos por SHA-256.
- Contagem independente dos CSVs com PyArrow, respeitando registros com quebras de linha entre aspas.
- Contagem real do PostgreSQL por ano igual ao CSV e ao controle em todos os 27 anos.
- População no banco igual à quantidade de linhas do CSV consolidado.
- 0 linhas de população sem correspondência no cadastro municipal.
- Testes locais do contador com quebras de linha, aspas escapadas e byte nulo; rejeição de manifesto de outro esquema e de `--schema public`.
- Sintaxe da rotina conferida. Não foram reexecutados notebooks de EDA nesta coleta.

Comprovante: [contagens e validação](../reports/validation/coleta_20261113_carga.json). Proveniência: [manifesto de arquivos](../reports/validation/coleta_20261113_manifesto.json). Esses documentos não contêm registros individuais nem credenciais.

## Relação com a versão do relatório

A versão anterior tem 32.512.002 linhas brutas do SINAN. A diferença de contagem de 18.746 registros está em 2026: 470.451 na versão anterior e 489.197 na nova coleta. As contagens anuais de 2000–2025 coincidem; essa comparação de quantidades não constitui comparação de todos os valores dos registros.

As tabelas `public` não foram recarregadas. O resumo verificado antes e depois permaneceu em 5.598.410 notificações tratadas e 4.178.450 casos prováveis de 2000–2025. O relatório continua baseado nessa versão; uma atualização das análises para a nova coleta é uma etapa distinta.

## Reprodução e consulta

Configure um arquivo `.env` privado e use o Python do ambiente do projeto:

```powershell
.\.venv\Scripts\python.exe -B scripts/executar_coleta_carga.py --env CAMINHO_DO_ENV --schema coleta_20261113 --piloto
.\.venv\Scripts\python.exe -B scripts/executar_coleta_carga.py --env CAMINHO_DO_ENV --schema coleta_20261113
```

Repetir o mesmo esquema aproveita arquivos verificados e anos confirmados. Para uma coleta futura, use um novo nome de esquema e pasta. A rotina rejeita `public` e esquemas preexistentes sem seu marcador de execução. Não execute duas instâncias no mesmo esquema/pasta.

```sql
SELECT * FROM coleta_20261113.sinan_dengue_carga ORDER BY ano_arquivo;
SELECT count(*) FROM coleta_20261113.populacao_ne;
SELECT count(*) FROM coleta_20261113.populacao_municipio_ano;
```

Dados brutos, configurações privadas e ambientes permanecem fora do versionamento. Nenhum commit ou push foi realizado.
