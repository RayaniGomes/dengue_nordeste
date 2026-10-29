# Etapa 2 — Limpeza e análise exploratória

## Perguntas

1. Como o volume e a incidência operacional variaram entre 2000 e 2025?
2. Quais diferenças aparecem entre os nove estados e entre seus municípios?
3. Quais meses concentram maior participação dos registros selecionados?
4. Quais estados-ano e municípios-ano apresentam incidências extremas?
5. Quanto as definições de caso e a qualidade dos arquivos afetam a interpretação?

## Numerador e classificações

A análise principal utiliza **casos prováveis operacionais presentes nos arquivos publicados**. O Portal de Dados Abertos do SUS define prováveis como suspeitos notificados, excluídos os descartados. Neste projeto, aplicamos essa definição de forma auditável: retiramos classificação 5, classificação 13 (chikungunya), agravos incompatíveis/ausentes quando há campo CID, duplicidade marcada em `NDUPLIC_N=2`, classificações desconhecidas e datas clinicamente inconsistentes. Não é uma reprodução certificada do painel oficial.

Brancos e códigos 0, 8 e 9 permanecem na definição ampla. **Código 8 é inconclusivo e não é tratado como confirmação de dengue.** O cenário de sensibilidade usa somente classificações compatíveis com dengue e critério de confirmação 1 ou 2. As diferenças entre os cenários são apresentadas nos resultados; a definição ampla pode incluir suspeitas sem conclusão específica de dengue.

| Vocabulário | Códigos compatíveis com dengue | Descartado | Outra doença |
|---|---|---|---|
| Legado: `CON_CLASSI`/`CLASSI_FIN` até 2013 | 1, 2, 3, 4 | 5 | 13 é excluído se presente |
| Novo: arquivos a partir de 2014 | 10, 11, 12 | 5 | 13 (chikungunya) |
| Arquivo de 2016, que contém os dois vocabulários | 1, 2, 3, 4, 10, 11, 12 | 5 | 13 |

O código 2 no vocabulário legado é dengue com complicações, conforme as fichas históricas. Não aplicamos a tabela “1 confirmado / 2 descartado” encontrada no dicionário genérico distribuído pelo catálogo aos layouts históricos observados. Foram consultados o dicionário SINAN Online de 2015 e as fichas de 2006 e 2001, cujas cópias e datas de obtenção estão registradas no manifesto da Etapa 2.

Nos arquivos anteriores a 2007, `ID_DG_NOT` é diagnóstico e não é usado como se fosse o CID do agravo. A origem no recurso específico de dengue é preservada; nos layouts que possuem `ID_AGRAVO`, aceitamos A90/A91 após retirar o ponto da grafia. CID ausente ou diferente permanece sinalizado e fora do numerador principal.

## Datas e notificações tardias

O eixo temporal principal é o **início dos sintomas**. As datas são convertidas de AAAA-MM-DD; não se substitui data de sintomas ausente pela data de notificação. São excluídos do numerador os sintomas anteriores a 2000, posteriores a 2025, inválidos ou posteriores à notificação. O ano obtido da data é utilizado em vez de um `NU_ANO` inconsistente, e a divergência fica registrada.

Para avaliar o limite de 2025, também foi consultado o arquivo de notificações de 2026, aceitando no complemento somente sintomas de 2000–2025. A consulta e seu eventual resultado vazio são registrados em `data/metadata/complemento_2026.json`. Não se presume que o ano do nome do ZIP seja sempre igual ao ano dos sintomas ou da data de notificação. Os arquivos originais de 2025 já contêm algumas notificações datadas de 2026; elas podem entrar se atenderem aos demais critérios.

As notificações são aceitas até a data de extração do complemento, preservada nos metadados, sem incluir sintomas de 2026. Atrasos acima de 60 dias são quantificados, mas não são automaticamente excluídos: atraso não equivale a erro. A série pode sofrer revisões e ainda ter efeitos de borda, mesmo com esse complemento.

## Duplicidade e rastreabilidade

Excluímos somente registros explicitamente marcados como duplicidade em `NDUPLIC_N=2`. A categoria 1 significa “não listar” na rotina de duplicidades, e não determina a exclusão da incidência. Flags antigas, inclusive `NDUPLIC=S`, não recebem significado presumido. Não eliminamos linhas idênticas por atributos reduzidos, pois não há chave individual pública confiável para distinguir duas pessoas com as mesmas características. Essa limitação permanece no estudo.

Os arquivos `data/interim/etapa2/sinan_ne_AAAA_classificado.csv.gz` conservam todas as linhas, inclusive as excluídas, seus campos originais, flags de problemas, motivo exclusivo de exclusão e identificador da linha no recorte de origem. As flags podem se sobrepor; os motivos exclusivos seguem a ordem documentada em `scripts/limpar_analisar.py` e somam exatamente o total excluído. `linha_recorte` não identifica uma pessoa.

## Integração e incidência

A residência é preservada como referência territorial. Município inválido ou com prefixo divergente da UF não recebe atribuição arbitrária: o registro pode compor o total estadual, mas fica fora da soma municipal. As contagens e as diferenças são conciliadas em testes.

A incidência operacional é calculada como casos selecionados divididos pela população do território e **ano de sintomas**, vezes 100 mil. A taxa do Nordeste usa soma de casos dividida pela soma das populações estaduais; não usa a média simples das taxas. Os denominadores seguem as fontes e limitações da Etapa 1. **2023 permanece sem incidência**, pois não foi adotado um denominador substituto ou interpolado. As mudanças entre censos, estimativas e malhas históricas devem ser consideradas nas comparações.

Município-ano sem registro utilizável permanece ausente. Zero de casos é atribuído somente quando há notificações com datas/residência utilizáveis naquela chave, mas nenhuma passa pelos filtros de caso. Portanto, estatísticas municipais descrevem o subconjunto observado; não estimam a distribuição entre todos os municípios do Nordeste. A base mensal completa o calendário dos estados-ano com registros; zero significa zero registros selecionados disponíveis na célula, e não comprovação de ausência de transmissão.

## Estatísticas e visualizações

- Estatísticas descritivas por UF: média, desvio-padrão, quartis, mediana, mínimo e máximo dos volumes e das taxas disponíveis.
- Séries anuais e mapa de calor de incidência; comparação de volumes e taxas em 2025.
- Sazonalidade: para cada estado-ano, proporção de casos em cada mês; depois média dessas proporções entre **2001 e 2024**, dando igual peso aos anos. A série regional também normaliza cada ano antes de calcular a média. Excluímos os dois extremos temporais dessa síntese para reduzir efeitos de borda. Não foram realizados testes de sazonalidade nem de significância.
- Histogramas, boxplots e gráfico de dispersão municipal para 2024, escolhido previamente como último ano completo anterior ao limite de 2025.
- Correlação de Spearman entre população e volume municipal de casos em 2024: Pearson dos postos médios, sem teste inferencial. Essa associação de tamanho populacional e contagem não equivale a associação entre população e incidência e não demonstra causalidade.
- Outliers temporais: taxa acima de Q3 + 1,5 × IQR no histórico da própria UF. Outliers espaciais: mesma regra entre municípios da mesma UF e ano. As flags são descritivas, não classificam automaticamente epidemias nem erros e **não removem extremos**. Não são testes ajustados para dependência temporal/espacial ou múltiplas comparações.
- Ranking municipal: incidência em 2024, apenas população de pelo menos 10 mil e ao menos 20 casos, critérios definidos antes da ordenação para reduzir instabilidade em contagens pequenas. O arquivo completo dos outliers não tem esse filtro.
- Mapas estaduais: anos 2002, 2016, 2024 e 2025, com a mesma escala de cores; malhas simplificadas atuais do IBGE em coordenadas geográficas. Não constituem harmonização retrospectiva dos limites municipais.

## Limitações essenciais

A ausência de descartados em determinados arquivos não prova ausência de descartes na vigilância e pode refletir a seleção da publicação. As comparações anuais são exploratórias e dependem da cobertura, da classificação e da atualização da base. Não há correção de subnotificação, teste de hipóteses ou estimação causal. Picos e rankings se referem aos dados disponíveis e às regras do projeto, e não a um ranking definitivo de risco epidemiológico.

## Referências primárias

- [SINAN/Dengue: dados e notas](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue).
- [Dicionário SINAN Online, revisão de 21/10/2015](https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/DIC_DADOS_ONLINE.pdf).
- [Ficha SINAN NET de 25/09/2006, Ministério da Saúde, hospedada na SESA/ES](https://saude.es.gov.br/Media/sesa/LACEN/Fichas_SINAN/ficha_16_sinan_Dengue.pdf).
- [Guia de Vigilância Epidemiológica, ficha histórica CENEPI de 30/05/2001](https://bvsms.saude.gov.br/bvs/publicacoes/Guia_Vig_Epid_novo2.pdf).
- [IBGE/SIDRA: estimativas populacionais](https://sidra.ibge.gov.br/tabela/6579), complementadas pelas tabelas 202, 793 e 4714, conforme manifesto da Etapa 1.
- [IBGE: documentação da API de malhas](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3).

## Uso de IA

ChatGPT/Codex foi usado na implementação, consulta à documentação, geração das figuras, verificações automatizadas e redação inicial. Os testes executados e as versões constam nos metadados; não são uma revisão humana independente. O grupo deve revisar a seleção epidemiológica, conferir as conclusões nas tabelas e registrar as contribuições individuais e as verificações humanas efetivamente realizadas.
