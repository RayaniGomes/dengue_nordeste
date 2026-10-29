"""Gera relatório de resultados, dicionário e notebook a partir da execução real."""
import base64
import csv
import html
import json
from pathlib import Path
import pandas as pd
from coletar import ROOT, agora

def br(x,casas=0):
    if pd.isna(x):return 'Ausente'
    if isinstance(x,str):return x
    return f'{x:,.{casas}f}'.replace(',','@').replace('.',',').replace('@','.')

def gerar():
    data=ROOT/'data/processed/etapa2'; out=ROOT/'outputs/etapa2'
    v=json.loads((ROOT/'data/metadata/validacao_etapa2.json').read_text(encoding='utf-8'))
    e=pd.read_csv(data/'estado_ano_limpo.csv'); n=pd.read_csv(data/'nordeste_ano.csv')
    a=pd.read_csv(data/'auditoria_limpeza.csv'); ranks=pd.read_csv(data/'ranking_municipios_2024.csv')
    saz=pd.read_csv(data/'sazonalidade_estados.csv'); complemento=json.loads((ROOT/'data/metadata/complemento_2026.json').read_text(encoding='utf-8'))
    estrito=n.loc[n.casos_criterio_estrito.idxmax()]
    indef=100*(1-v['casos_criterio_estrito']/v['casos_probaveis_operacionais'])
    sem_descarte=a.loc[a.flag_descartado.eq(0),'ano_arquivo'].astype(str).tolist()
    resumo=[
      ('Evolução temporal',f'O maior volume no recorte selecionado aparece em {v["pico_casos_ano"]}: {br(v["pico_casos"])} casos prováveis operacionais. No cenário estrito, o pico também deve ser verificado separadamente: {int(estrito.ano)}, com {br(estrito.casos_criterio_estrito)} registros. Esses picos descrevem os arquivos publicados e os filtros do projeto, sem demonstrar uma tendência causal ou uma série oficial consolidada.'),
      ('Diferenças entre estados',f'Em 2025, {v["uf_maior_incidencia_2025"]} apresenta a maior incidência operacional entre os nove estados: {br(v["maior_incidencia_2025"],1)} por 100 mil habitantes. O gráfico de volumes e taxas mostra por que o maior número absoluto de casos não determina a maior incidência.'),
      ('Sazonalidade',f'Na média das participações anuais de 2001 a 2024, {br(v["participacao_media_primeiro_semestre_2001_2024_pct"],1)}% dos registros selecionados ocorrem de janeiro a junho. O mês de maior participação regional é {int(v["mes_pico_sazonal"]):02d}. Os perfis estaduais diferem; esse padrão não foi submetido a teste de significância e não demonstra efeito causal de chuva ou temperatura.'),
      ('Valores atípicos',f'Foram sinalizados {v["outliers_estaduais"]} estados-ano acima do limite superior de Tukey no histórico da própria UF. Os outliers municipais comparam taxas dentro da mesma UF e ano. Todos foram mantidos; a classificação indica necessidade de investigação, não erro nem epidemia automaticamente.'),
      ('População e contagem',f'Em municípios observados com população disponível em 2024, a correlação de Spearman entre população e volume de casos é {br(v["spearman_populacao_casos_municipais_2024"],3)}. Ela descreve associação entre tamanho e contagem; não foi calculado teste inferencial e não se conclui que municípios maiores tenham maior incidência.'),
    ]
    limpeza=f'Dos {br(v["registros_entrada"])} registros de entrada, {br(v["casos_probaveis_operacionais"])} passam pela seleção ampla e {br(v["casos_criterio_estrito"])} pelo cenário estrito. A diferença de {br(indef,1)}% entre os cenários evidencia a dependência da definição de caso. Foram mantidos {br(v["casos_atraso_superior60_dias"])} registros selecionados com atraso de notificação superior a 60 dias, sinalizados para revisão.'
    limitacoes=[
      'A classificação 5 não aparece nos arquivos dos anos '+', '.join(sem_descarte)+'. Não se interpreta essa ausência como inexistência de descartes na vigilância; a seleção da publicação pode afetar comparações temporais.',
      'A definição ampla inclui classificações inconclusivas, ignoradas ou ausentes. O cenário estrito permite avaliar parte dessa sensibilidade, sem ser padrão-ouro de diagnóstico.',
      '2023 permanece sem denominador populacional e sem incidência. Não houve interpolação ou cópia automática de outro ano.',
      'As taxas municipais disponíveis descrevem municípios com registros utilizáveis e população. Municípios sem registro não foram transformados em zero; rankings e histogramas não representam todos os municípios.',
      'Censos, estimativas e alterações territoriais têm referências diferentes. As malhas estaduais dos mapas são simplificadas e atuais; não harmonizam retrospectivamente os municípios.',
      'Subnotificação, revisões, mudanças no sistema e duplicidades sem marcação identificável podem permanecer. Não foram ajustados modelos, testadas hipóteses ou estimadas relações causais.',
    ]
    tabelas=[]
    t=e.loc[e.ano.eq(2025),['uf','casos_probaveis_operacionais','casos_criterio_estrito','incidencia_100mil']].sort_values('incidencia_100mil',ascending=False).copy()
    t.columns=['UF','Prováveis operacionais','Cenário estrito','Incidência / 100 mil']
    for c in t.columns[1:]:t[c]=t[c].map(lambda x:br(x,1 if c.startswith('Incidência') else 0))
    tabelas.append(('Comparação estadual em 2025',t))
    t=ranks[['nome_referencia','uf','casos_probaveis_operacionais','populacao','incidencia_100mil']].head(10).copy()
    t.columns=['Município','UF','Casos','População','Incidência / 100 mil']
    for c in ['Casos','População','Incidência / 100 mil']:t[c]=t[c].map(lambda x:br(x,1 if c.startswith('Incidência') else 0))
    tabelas.append(('Maiores incidências municipais observadas em 2024',t))
    t=pd.DataFrame([{'Motivo exclusivo':k,'Registros':br(val)} for k,val in v['exclusoes'].items()])
    tabelas.append(('Fluxo das exclusões',t))
    fontes=[
      ('SINAN/Dengue: dados e definição de casos prováveis','https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue'),
      ('Dicionário SINAN Online, revisão 2015','https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/DIC_DADOS_ONLINE.pdf'),
      ('Ficha SINAN NET, 2006','https://saude.es.gov.br/Media/sesa/LACEN/Fichas_SINAN/ficha_16_sinan_Dengue.pdf'),
      ('IBGE/SIDRA: população','https://sidra.ibge.gov.br/tabela/6579'),
      ('IBGE: malhas geográficas','https://servicodados.ibge.gov.br/api/docs/malhas?versao=3')]
    figuras=json.loads((out/'figuras.json').read_text(encoding='utf-8'))
    def tabela_md(df):
        return '| '+' | '.join(df.columns)+' |\n| '+' | '.join('---' for _ in df.columns)+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in df.itertuples(index=False,name=None))
    titulo='Dengue no Nordeste: resultados da limpeza e EDA (2000–2025)'
    introducao=f'Etapa 2 do projeto IMD1151. Gerado em {agora()}. O estudo descreve casos prováveis operacionais disponíveis no SINAN, com denominadores do IBGE. As conclusões são exploratórias e dependem das limitações de cobertura e classificação.'
    complemento_texto=f'A consulta complementar leu {br(complemento["registros_brasil_2026_lidos"])} registros nacionais de 2026, dos quais {br(complemento["registros_ne_2026_lidos"])} de residentes no Nordeste. Encontrou {br(complemento["registros_recorte"])} registros adicionais com sintomas até 2025. A população e a referência temporal do estudo não foram ampliadas para 2026.'
    md=[f'# {titulo}','',introducao,'','## Limpeza e seleção','',limpeza,'',complemento_texto,'','## Primeiras respostas','']
    h=[f'<h1>{html.escape(titulo)}</h1><p class="sub">{html.escape(introducao)}</p>',
       '<div class="alerta"><strong>Leitura dos resultados:</strong> casos prováveis operacionais não equivalem a casos confirmados; 2023 não possui incidência calculada.</div>',
       '<h2>Limpeza e seleção</h2><p>'+html.escape(limpeza)+'</p><p>'+html.escape(complemento_texto)+'</p><h2>Primeiras respostas</h2>']
    for nome,texto in resumo:
        md += [f'### {nome}','',texto,'']; h += [f'<h3>{html.escape(nome)}</h3><p>{html.escape(texto)}</p>']
    for nome,t in tabelas:
        md += [f'## {nome}','',tabela_md(t),'']; h += [f'<h2>{html.escape(nome)}</h2>',t.to_html(index=False,border=0)]
        if 'municipais' in nome:
            nota='Seleção previamente definida: população de pelo menos 10 mil habitantes e no mínimo 20 casos. Não é ranking de risco individual.'
            md += [nota,'']; h += ['<p class="nota">'+nota+'</p>']
    md += ['## Visualizações','']; h += ['<h2>Visualizações</h2>']
    for nome in figuras:
        md += [f'![{nome}](../outputs/etapa2/{nome})','']
        b64=base64.b64encode((out/nome).read_bytes()).decode()
        h += [f'<figure><img src="data:image/png;base64,{b64}" alt="{html.escape(nome)}"></figure>']
    md += ['## Limitações','']+['- '+s for s in limitacoes]+['','## Fontes','']+ [f'- [{nome}]({url})' for nome,url in fontes]
    h += ['<h2>Limitações</h2><ul>']+['<li>'+html.escape(s)+'</li>' for s in limitacoes]+['</ul><h2>Fontes</h2><ul>']+[f'<li><a href="{html.escape(url)}">{html.escape(nome)}</a></li>' for nome,url in fontes]+['</ul>']
    declaracao='ChatGPT/Codex auxiliou na implementação, documentação, figuras e verificações automatizadas. O grupo deve realizar e registrar a revisão humana e as contribuições individuais antes da entrega final.'
    md += ['','## Uso de IA e revisão do grupo','',declaracao,'']; h += ['<h2>Uso de IA e revisão do grupo</h2><p>'+declaracao+'</p>']
    (ROOT/'docs/resultados_etapa2.md').write_text('\n'.join(md),encoding='utf-8')
    css='body{background:#edf2f7;color:#193047;font:16px/1.65 system-ui,sans-serif;margin:0}main{max-width:1080px;margin:36px auto;background:white;padding:48px;border-radius:12px}h1{font-size:32px;line-height:1.25;color:#126e82}h2{border-bottom:2px solid #e5ecf2;padding-bottom:8px;margin-top:36px}h3{margin-bottom:5px}.sub,.nota{color:#526178}.alerta{border-left:5px solid #df8450;background:#fff6ed;padding:16px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:9px;border-bottom:1px solid #dae3ed}th{background:#eaf3f5}figure{margin:24px 0}img{max-width:100%;height:auto}a{color:#126e82}@media print{main{margin:0;padding:16px}figure,table{break-inside:avoid}}'
    (out/'relatorio_eda.html').write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+titulo+'</title><style>'+css+'</style><main>'+''.join(h)+'</main></html>',encoding='utf-8')
    campos=[
      ('ano','Inteiro','Ano de início dos sintomas; ano_arquivo é ano do recurso de notificação.'),
      ('casos_probaveis_operacionais','Contagem','Seleção ampla: exclui descartado, chikungunya, duplicidade marcada, agravo incompatível e datas/classificações inválidas. Inclui branco/0/8/9.'),
      ('casos_criterio_estrito','Contagem','Subconjunto da seleção ampla com classificação de dengue e critério 1 ou 2.'),
      ('incidencia_100mil','Taxa','Seleção ampla / população do território e ano de sintomas × 100 mil. NA sem população ou sem cobertura municipal.'),
      ('incidencia_criterio_estrito_100mil','Taxa','Cenário estrito / população × 100 mil.'),
      ('registros_com_datas_utilizaveis','Contagem ou NA','Registros com residência e datas utilizáveis, antes de filtrar classificação/agravo. NA não é zero.'),
      ('status_cobertura','Categoria','integrado; sem_populacao; sem_registro_utilizavel. Não mede subnotificação.'),
      ('nome_referencia','Texto','Nome do mesmo ano se disponível; na ausência, nome mais recente apenas para identificação, sem copiar população.'),
      ('variacao_anual_pct','Percentual','Variação do volume selecionado em relação ao ano anterior; não é variação da taxa.'),
      ('outlier_temporal_iqr','Booleano ou NA','Taxa acima de Q3 + 1,5 IQR no histórico da própria UF; sem remoção.'),
      ('outlier_espacial_iqr','Booleano ou NA','Taxa acima de Q3 + 1,5 IQR entre municípios observados da mesma UF e ano; sem remoção.'),
      ('q1_uf / q3_uf / limite_superior_iqr_uf','Taxas','Quartis e limite usados na sinalização temporal estadual.'),
      ('q1_uf_ano / q3_uf_ano / limite_superior_iqr_uf_ano','Taxas','Quartis e limite usados na sinalização espacial municipal.'),
      ('participacao_no_ano_pct','Percentual','Casos do mês / casos do estado-ano × 100.'),
      ('participacao_media_pct','Percentual','Média das participações anuais em 2001–2024, com igual peso por ano.'),
      ('participacao_mediana_pct','Percentual','Mediana das participações anuais em 2001–2024.'),
      ('mes / mes_sintomas','Inteiro','Mês dos primeiros sintomas, de 1 a 12.'),
      ('caso_provavel_operacional / caso_criterio_estrito','Booleanos','Flags individuais que determinam cada cenário de agregação.'),
      ('motivo_exclusao','Categoria','incluido ou primeiro motivo aplicável na ordem de MOTIVOS no script; exclusivo por registro.'),
      ('flag_*','Booleanos','Problemas detectados, podem coexistir; somar flags não fornece o total de excluídos.'),
      ('atraso_notificacao_dias','Dias','Data de notificação menos sintomas. Mais de 60 dias é sinalizado, não removido automaticamente.'),
      ('linha_recorte','Inteiro','Número da linha no CSV de recorte da Etapa 1, incluindo cabeçalho. Não identifica pessoa.'),
      ('nu_ano_divergente_data / ano_notificacao_divergente_arquivo','Booleanos','Divergência de NU_ANO ou ano do ZIP em relação à data real, preservada na auditoria.'),
      ('classificacao_harmonizada','Categoria','Rótulo compatível com o vocabulário histórico; desconhecido é excluído.'),
      ('classificacao_nao_encerrada','Contagem na auditoria','Nome operacional para brancos/0/8/9; inclui inconclusivo (8), que pode estar encerrado. Não significa que todos estejam em aberto.'),
      ('municipio_valido','Booleano','Código de 6 dígitos com UF consistente; existência no IBGE é avaliada na junção.'),
    ]
    with open(ROOT/'docs/dicionario_etapa2.csv','w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['campo','tipo','definicao']); w.writerows(campos)
    cells=[]
    def mdcell(s):cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(True)})
    def code(s):cells.append({'cell_type':'code','metadata':{},'source':s.splitlines(True),'execution_count':None,'outputs':[]})
    mdcell('# Etapa 2 — Limpeza e análise exploratória da dengue no Nordeste\n\nPeríodo dos sintomas: 2000–2025. Fontes: SINAN/MS e IBGE.\n\nA definição principal é operacional e inclui inconclusivos; o cenário estrito demonstra sensibilidade à classificação. Leia `docs/metodologia_etapa2.md`. O notebook usa os produtos disponíveis; ative `REPROCESSAR` para reconstruí-los pelos scripts.\n')
    code('from pathlib import Path\nimport sys, json, os\nimport pandas as pd\nfrom IPython.display import display, Image, Markdown\nbase=Path.cwd().resolve()\ncandidatos=[base,base/"dengue_nordeste",*base.parents]\nROOT=next(p for p in candidatos if (p/"scripts/limpar_analisar.py").exists())\nsys.path.insert(0,str(ROOT/"scripts"))\nos.environ.setdefault("MPLCONFIGDIR",str(ROOT/"tmp/matplotlib"))\nREPROCESSAR=False\nprint("Projeto:",ROOT)\n')
    mdcell('## 1. Preparação e execução\n\nA primeira execução sem produtos faz a coleta/integração necessárias. Os arquivos originais e recortes individuais não são versionados. A reconstrução pode levar vários minutos e exige internet.\n')
    code('from executar_etapa2 import executar_etapa\nexecutar_etapa(reprocessar=REPROCESSAR,documentar=False)\nDATA=ROOT/"data/processed/etapa2"\nmeta=json.loads((ROOT/"data/metadata/validacao_etapa2.json").read_text(encoding="utf-8"))\nprint("Entrada:",meta["registros_entrada"])\nprint("Prováveis operacionais:",meta["casos_probaveis_operacionais"])\nprint("Cenário estrito:",meta["casos_criterio_estrito"])\nprint("Data-limite das notificações:",meta["data_corte_notificacoes"])\n')
    mdcell('## 2. Auditoria dos filtros\n\nOs motivos de exclusão são exclusivos; flags podem se sobrepor. Não há exclusão automática de outliers, remoção de linhas idênticas ou imputação de sintomas/população.\n')
    code('aud=pd.read_csv(DATA/"auditoria_limpeza.csv")\ncols=["ano_arquivo","registros","incluidos","criterio_estrito","nu_ano_divergente_data","incluidos_atraso_superior60"]\ndisplay(aud[cols])\ndisplay(pd.DataFrame(list(meta["exclusoes"].items()),columns=["Motivo exclusivo","Registros"]))\n')
    mdcell('## 3. Verificações das bases\n\nChaves, reconciliação estadual/municipal/mensal, taxas, sazonalidade, ausência de 2023 e hashes são conferidos pelo validador independente. No pacote portátil sem originais, a conferência de hashes exige reconstruir os recortes; as verificações das tabelas continuam disponíveis nas células abaixo.\n')
    code('tipos={"codigo_uf":"string","codigo_municipio_6":"string","codigo_ibge":"string"}\nestados=pd.read_csv(DATA/"estado_ano_limpo.csv",dtype=tipos)\nmunicipios=pd.read_csv(DATA/"municipio_ano_limpo.csv",dtype=tipos)\nmensal=pd.read_csv(DATA/"estado_mes_sintomas.csv",dtype=tipos)\nnordeste=pd.read_csv(DATA/"nordeste_ano.csv")\nassert len(estados)==234\nassert not estados.duplicated(["codigo_uf","ano"]).any()\nassert not municipios.duplicated(["codigo_municipio_6","ano"]).any()\nassert int(estados.casos_probaveis_operacionais.sum())==int(mensal.casos_probaveis_operacionais.sum())==meta["casos_probaveis_operacionais"]\nassert int(municipios.casos_probaveis_operacionais.sum())+meta["casos_sem_municipio_valido"]==meta["casos_probaveis_operacionais"]\nassert estados.loc[estados.ano.eq(2023),"incidencia_100mil"].isna().all()\nprint("Verificações das tabelas concluídas.")\n')
    mdcell('## 4. Estatísticas descritivas e cobertura\n\nA estatística municipal se restringe ao subconjunto com registros e população. As populações combinam censos e estimativas; a taxa de 2023 permanece ausente.\n')
    code('display(estados.groupby("uf")[["casos_probaveis_operacionais","incidencia_100mil"]].describe())\ndisplay(pd.read_csv(DATA/"cobertura_municipal.csv"))\n')
    mdcell('## 5. Evolução, incidência e comparação estadual\n\nSéries por início dos sintomas. O cenário estrito exige classificação de dengue e critério 1/2. A ausência de descartados em certos arquivos pode afetar a comparabilidade.\n')
    code('for nome in ["01_evolucao_temporal.png","02_incidencia_estado_ano.png","03_comparacao_estados_2025.png"]:\n    display(Image(filename=str(ROOT/"outputs/etapa2"/nome)))\ndisplay(estados.loc[estados.ano.eq(2025),["uf","casos_probaveis_operacionais","casos_criterio_estrito","incidencia_100mil"]].sort_values("incidencia_100mil",ascending=False))\n')
    mdcell('## 6. Sazonalidade\n\nCada ano tem peso igual na média de participações mensais. A síntese usa 2001–2024 para reduzir efeitos de borda; não é teste de significância nem evidência causal climática.\n')
    code('display(Image(filename=str(ROOT/"outputs/etapa2/04_sazonalidade.png")))\ndisplay(pd.read_csv(DATA/"sazonalidade_nordeste.csv"))\n')
    mdcell('## 7. Distribuição municipal, correlação e extremos\n\nO ranking de 2024 usa população ≥ 10 mil e pelo menos 20 casos. Outliers permanecem nas bases; Tukey sinaliza extremos, sem distinguir sozinho erro de surto. A correlação refere-se a população versus contagem, não população versus incidência.\n')
    code('for nome in ["05_distribuicoes_municipais.png","06_ranking_municipal.png","07_populacao_casos.png"]:\n    display(Image(filename=str(ROOT/"outputs/etapa2"/nome)))\nprint("Spearman população × contagem em 2024:",meta["spearman_populacao_casos_municipais_2024"])\ndisplay(pd.read_csv(DATA/"outliers_estaduais.csv")[["uf","ano","incidencia_100mil","limite_superior_iqr_uf"]])\n')
    mdcell('## 8. Distribuição espacial e qualidade\n\nOs mapas têm escala comum. As malhas são estaduais, simplificadas e atuais; não harmonizam limites municipais históricos. Zero descartados no arquivo não comprova que não houve descartes na vigilância.\n')
    code('display(Image(filename=str(ROOT/"outputs/etapa2/08_mapas_estaduais.png")))\ndisplay(Image(filename=str(ROOT/"outputs/etapa2/09_qualidade_classificacao.png")))\n')
    mdcell('## 9. Primeiras respostas e limitações\n\n'+'\n\n'.join('**'+nome+'** — '+texto for nome,texto in resumo)+'\n\n'+ '\n'.join('- '+s for s in limitacoes)+'\n\nLeia `docs/resultados_etapa2.md` e `docs/metodologia_etapa2.md` para métodos, fontes e declaração de uso de IA. As conclusões devem ser revisadas pelo grupo antes da entrega.\n')
    for i,c in enumerate(cells):c['id']=f'eda-{i:02d}'
    nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},'language_info':{'name':'python'}},'cells':cells}
    (ROOT/'notebooks/02_limpeza_eda.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')
    print('Relatório HTML/Markdown, dicionário e notebook gerados.',flush=True)

if __name__=='__main__':gerar()
