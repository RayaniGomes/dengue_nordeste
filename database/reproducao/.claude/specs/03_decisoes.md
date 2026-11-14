# 03. Decisões de análise

Situação: **decidido** (vale para o projeto), **aplicado** (já implementado no código), **proposto** (em uso, falta o
grupo confirmar), **pendente** (sem escolha). Ao mudar uma decisão, atualize esta tabela, o código e a metodologia do
relatório.

| # | Decisão | Situação | Escolha | Motivo / evidência |
|---|---|---|---|---|
| 1 | Arquitetura | decidido | ELT: bruto no Postgres local, limpeza no banco; só tabelas agregadas sobem para o Neon (dashboard) | Neon tem pouco espaço; bruto do Brasil tem ~8 GB; bruto completo permite expandir para outras regiões |
| 2 | Fonte das notificações | **pendente (grupo)** | na prática, CSV anual (opção B); API (opção A) mantida como alternativa | mesmas notificações; CSV completo em minutos, API incompleta e instável (`01_fontes.md`) |
| 3 | Geografia | aplicado | município de **residência** (`id_mn_resi`) | inclui residentes notificados fora do Nordeste; 99,997% dos códigos têm par no IBGE |
| 4 | Ligação com o IBGE | aplicado | `left(id_mn_resi, 6) = municipio.cod_mun6`, depois tudo por `cod_mun7` | vale para 7 dígitos (até 2006) e 6 dígitos (desde 2007) |
| 5 | "Município ignorado" | aplicado | excluído (167 notificações) | código com UF mas sem município (ex.: `2900000`) |
| 6 | Definição de caso | decidido (29/10/2026) | **caso provável** = classificação ≠ 5 (principal); **confirmado** = 1–4 ou 10–12 (comparação) | 2014, 2015 e 2022–2026 vêm sem descartados: total de notificações não é comparável entre anos; confirmados subestimam epidemias (inconclusivos até 35%) |
| 7 | Possíveis duplicatas | proposto, aplicado | marcar (`possivel_duplicata`), não apagar; mostrar resultado com e sem elas | dados anonimizados não permitem confirmar; `nduplic_n` vazio em 99,7%; 0,7%–3,3% por ano |
| 8 | Regras de limpeza (datas, sexo, idade, fichas) | aplicado | `02_banco.md`, tabela `notificacao_dengue_ne` | validadas coluna a coluna no `05_analise.ipynb`, seção 8 |
| 9 | Data de referência | proposto | `ano` (notificação) para a série anual; `mes_sintomas` para sazonalidade | data dos sintomas é mais próxima do momento da infecção |
| 10 | Denominador | aplicado | `populacao_municipio_ano` do mesmo ano; 2007 e 2023 interpolados | IBGE não tem esses anos |
| 11 | Ano epidêmico | proposto | incidência < 100 baixa, 100–299 média, ≥ 300 por 100 mil alta | classificação usada pelo Ministério da Saúde |
| 12 | Período da análise | proposto | 2000 a 2025; 2026 fora (parcial); 2025 sinalizado como sujeito a revisão | `notificacao_dengue_ne` tem 1 linha de 1999 e 2026 inteiro |
| 13 | Litoral × semiárido (P2) | **pendente (grupo)** | provisório: capital × interior (`08_sazonalidade`) | o banco não tem a lista oficial do semiárido (SUDENE/IBGE); entraria como nova fonte |
| 14 | Município atípico (P3) | proposto | funil com superdispersão aditiva: z = log((O + 0,5)/E) ÷ √(1/E + τ²), τ² por estado; alerta \|z\| > 1,96, atípico \|z\| > 3,09; período 2000–2025 somado | correção de continuidade de 0,5 já presente no código original; estimador operacional com escores winsorizados em 10%/90%; limites nominais, sem calibração de cobertura. A revisão manteve o estimador e explicitou a sensibilidade (17, 46 ou 80 atípicos abaixo com cortes de 0%, 5% ou 10% por cauda) |
| 15 | Ano epidêmico na P4 | proposto | por estado-ano (incidência ≥ 300), não pelo Nordeste todo | as epidemias não são simultâneas entre estados (correlação mediana 0,41, `07_incidencia`) |

## Verificações da revisão de 13/11/2026
- Nenhuma decisão marcada **pendente (grupo)** foi encerrada.
- P2 distingue média circular do mês de máximo; média sem direção resultante é indefinida, não um pico.
- Capital × interior: acrescentado pareamento pelos mesmos anos elegíveis de cada UF, além da comparação histórica não pareada. Não identifica litoral × semiárido.
- Ano da notificação continua principal; ano dos sintomas aparece apenas como sensibilidade e as diferenças de calendário são quantificadas.
- P3 mantém o estimador proposto, com gráfico usando os mesmos E e correção de 0,5 do escore, sem pressupor 26 anos para todo município.
- P4 acrescenta denominadores, ausências e estratos de estado/período. V pequeno na tabela agregada não prova equivalência.
- Saídas, tabelas, versões e hashes estão em `reports/`; detalhes em `docs/revisao_2026-11-13.md`.

## Pendências
- Comunicar ao grupo as decisões 6 e 7 e fechar a 2.
- Confirmar os códigos do SINAN (`02_banco.md`, seção 4) no dicionário oficial.
- Confirmar no painel do Ministério da Saúde o número usado na validação (Bahia 2024), hoje vindo de notícia que cita a Sesab.
- Conferir num boletim do Ministério a definição oficial de "caso provável".
