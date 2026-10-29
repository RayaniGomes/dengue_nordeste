"""Figuras estáticas da EDA; geradas a partir das tabelas auditadas da Etapa 2."""
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
from coletar import ROOT, RAW, UFS, ler_json

OUT=ROOT/'outputs/etapa2'
DATA=ROOT/'data/processed/etapa2'
MESES=['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
def numero(x,pos=None):return f'{x:,.0f}'.replace(',','.')

def gerar():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':14,
       'axes.labelsize':10,'axes.spines.top':False,'axes.spines.right':False,
       'figure.facecolor':'#f7f9fc','axes.facecolor':'#ffffff','savefig.facecolor':'#f7f9fc',
       'axes.titleweight':'bold','grid.alpha':.22,'axes.axisbelow':True})
    e=pd.read_csv(DATA/'estado_ano_limpo.csv',dtype={'codigo_uf':'string'})
    m=pd.read_csv(DATA/'municipio_ano_limpo.csv',dtype={'codigo_municipio_6':'string'})
    n=pd.read_csv(DATA/'nordeste_ano.csv'); saz=pd.read_csv(DATA/'sazonalidade_estados.csv')
    a=pd.read_csv(DATA/'auditoria_limpeza.csv'); cores=plt.colormaps['tab10']
    arquivos=[]
    def salvar(fig,nome,nota='Fonte: SINAN/MS + IBGE. Cálculos do projeto; extração em 28/10/2026.'):
        fig.text(.02,.018,nota,fontsize=8,color='#526178',ha='left')
        fig.savefig(OUT/f'{nome}.png',dpi=165,bbox_inches='tight')
        plt.close(fig); arquivos.append(nome+'.png')
    fig,ax=plt.subplots(figsize=(11,5.8))
    ax.plot(n.ano,n.casos_probaveis_operacionais,label='Prováveis operacionais',color='#126e82',lw=2.5,marker='o',ms=4)
    ax.plot(n.ano,n.casos_criterio_estrito,label='Classificação de dengue + critério 1/2',color='#df8450',lw=1.8,ls='--')
    ax.axvline(2014,color='#8693a6',ls=':',lw=1)
    ax.text(2014.2,ax.get_ylim()[1]*.92,'Mudança de classificação',fontsize=8,color='#59677c')
    ax.set(title='Dengue no Nordeste: evolução dos registros selecionados',xlabel='Ano de início dos sintomas',ylabel='Casos presentes nos arquivos')
    ax.yaxis.set_major_formatter(FuncFormatter(numero)); ax.grid(axis='y'); ax.legend(frameon=False,loc='upper left')
    fig.subplots_adjust(bottom=.15,top=.88)
    salvar(fig,'01_evolucao_temporal','SINAN/MS. Definições operacionais; não representa série oficial consolidada. 2025 pode ter atraso de notificação.')
    fig,ax=plt.subplots(figsize=(12,5.3))
    pivot=e.pivot(index='uf',columns='ano',values='incidencia_100mil').reindex(list(UFS.values()))
    cmap=plt.colormaps['YlOrRd'].copy(); cmap.set_bad('#c8cfd8')
    im=ax.imshow(np.ma.masked_invalid(pivot.to_numpy(dtype=float)),aspect='auto',cmap=cmap)
    ax.set_xticks(range(26),pivot.columns,rotation=65); ax.set_yticks(range(9),pivot.index)
    ax.set(title='Incidência operacional por estado e ano',xlabel='Ano de início dos sintomas')
    cb=fig.colorbar(im,ax=ax,pad=.015); cb.set_label('Casos por 100 mil habitantes')
    fig.subplots_adjust(bottom=.20)
    salvar(fig,'02_incidencia_estado_ano','SINAN/MS + IBGE. Cinza = sem denominador (2023); censos e estimativas não são uma série populacional harmonizada.')
    fig,axs=plt.subplots(1,2,figsize=(11,5.8))
    ultimo=e.loc[e.ano.eq(2025)].sort_values('incidencia_100mil')
    for ax,col,titulo in [(axs[0],'casos_probaveis_operacionais','Volume de registros selecionados'),(axs[1],'incidencia_100mil','Incidência operacional por 100 mil')]:
        ax.barh(ultimo.uf,ultimo[col],color=['#df8450' if x==ultimo.iloc[-1].uf else '#126e82' for x in ultimo.uf])
        ax.set_title(titulo,fontsize=12); ax.grid(axis='x'); ax.xaxis.set_major_formatter(FuncFormatter(numero))
    fig.suptitle('Comparação dos estados em 2025',fontweight='bold',fontsize=15)
    fig.subplots_adjust(bottom=.15,wspace=.3)
    salvar(fig,'03_comparacao_estados_2025','SINAN/MS + IBGE. Ordem definida pela incidência; volume e taxa respondem a perguntas diferentes. Dados sujeitos a revisão.')
    fig,ax=plt.subplots(figsize=(10.6,5.8))
    for i,uf in enumerate(UFS.values()):
        s=saz.loc[saz.uf.eq(uf)].sort_values('mes')
        ax.plot(s.mes,s.participacao_media_pct,label=uf,lw=1.7,color=cores(i),marker='o',ms=3)
    ax.axhline(100/12,color='#8a96a8',lw=1,ls='--',label='Distribuição uniforme')
    ax.set_xticks(range(1,13),MESES); ax.set(title='Sazonalidade: perfis mensais dos estados',xlabel='Mês de início dos sintomas',ylabel='Participação média no total anual (%)')
    ax.legend(ncol=5,frameon=False,loc='upper center',bbox_to_anchor=(.5,-.14)); ax.grid(axis='y')
    fig.subplots_adjust(bottom=.24)
    salvar(fig,'04_sazonalidade','SINAN/MS. Média das participações anuais, com igual peso por ano, de 2001 a 2024; 2025 excluído para reduzir efeito de borda.')
    fig,axs=plt.subplots(1,2,figsize=(11,5.7))
    d=m.loc[m.ano.eq(2024)&m.incidencia_100mil.notna()]
    axs[0].hist(d.incidencia_100mil,bins=45,color='#126e82',edgecolor='white')
    axs[0].set(title='Distribuição municipal em 2024',xlabel='Incidência operacional por 100 mil',ylabel='Municípios com registros e população')
    grupos=[d.loc[d.uf.eq(uf),'incidencia_100mil'] for uf in UFS.values()]
    axs[1].boxplot(grupos,tick_labels=list(UFS.values()),showfliers=True,
       flierprops={'marker':'.','markersize':3,'alpha':.4},medianprops={'color':'#df8450','linewidth':2})
    axs[1].set(title='Dispersão dentro de cada estado',ylabel='Incidência operacional por 100 mil')
    for ax in axs:ax.grid(axis='y'); ax.yaxis.set_major_formatter(FuncFormatter(numero))
    fig.subplots_adjust(bottom=.18,wspace=.35)
    salvar(fig,'05_distribuicoes_municipais','SINAN/MS + IBGE. Apenas municípios com registros utilizáveis; falta de registro não foi preenchida com zero. Extremos foram mantidos.')
    fig,ax=plt.subplots(figsize=(10.6,6.4))
    r=pd.read_csv(DATA/'ranking_municipios_2024.csv').head(15).iloc[::-1]
    labels=[str(nome).rsplit(' - ',1)[0]+' / '+uf for nome,uf in zip(r.nome_referencia,r.uf)]
    ax.barh(labels,r.incidencia_100mil,color='#126e82'); ax.grid(axis='x')
    ax.set(title='Maiores incidências municipais observadas em 2024',xlabel='Casos prováveis operacionais por 100 mil habitantes')
    ax.xaxis.set_major_formatter(FuncFormatter(numero)); fig.subplots_adjust(left=.30,bottom=.15)
    salvar(fig,'06_ranking_municipal','SINAN/MS + IBGE. Seleção: população >= 10 mil e pelo menos 20 casos. Ranking descritivo; não mede risco individual nem causalidade.')
    fig,ax=plt.subplots(figsize=(9.7,6))
    for i,uf in enumerate(UFS.values()):
        s=d.loc[d.uf.eq(uf)]
        ax.scatter(s.populacao,s.casos_probaveis_operacionais+1,s=14,alpha=.5,color=cores(i),label=uf)
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set(title='População e volume de casos municipais em 2024',xlabel='População residente (escala log)',ylabel='Casos + 1 (escala log)')
    ax.legend(ncol=3,frameon=False); ax.grid(True,which='major')
    fig.subplots_adjust(bottom=.15)
    salvar(fig,'07_populacao_casos','SINAN/MS + IBGE. Associação descritiva entre tamanho populacional e contagem; não demonstra causalidade ou maior incidência.')
    fig,axs=plt.subplots(2,2,figsize=(11,10.8))
    anos=[2002,2016,2024,2025]; vmax=float(e.loc[e.ano.isin(anos),'incidencia_100mil'].max())
    norm=Normalize(0,vmax); cmap=plt.colormaps['YlOrRd']
    centros={'MA':(-45.1,-5.2),'PI':(-42.6,-7.5),'CE':(-39.5,-5.4),'RN':(-36.5,-5.7),
             'PB':(-36.8,-7.3),'PE':(-38.2,-8.5),'AL':(-36.5,-9.5),'SE':(-37.3,-10.7),'BA':(-41.7,-12.8)}
    for ax,ano in zip(axs.flat,anos):
        taxas=e.loc[e.ano.eq(ano)].set_index('uf').incidencia_100mil
        for uf in UFS.values():
            j=ler_json(RAW/f'referencias_etapa2/malha_{uf}.json')
            for feature in j['features']:
                geometry=feature['geometry']
                polygons=geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
                for poly in polygons:
                    # Ring exterior; os nove polígonos estaduais não dependem de furos para esta escala.
                    ax.add_patch(Polygon(np.asarray(poly[0])[:,:2],closed=True,facecolor=cmap(norm(taxas[uf])),edgecolor='#ffffff',lw=.8))
            x,y=centros[uf]; ax.text(x,y,uf,ha='center',fontsize=8,color='#172a40',fontweight='bold')
        ax.set(xlim=(-49.5,-34.2),ylim=(-18.6,-.5),aspect='equal',title=str(ano)); ax.axis('off')
    fig.suptitle('Distribuição espacial da incidência operacional',fontsize=16,fontweight='bold',y=.97)
    sm=plt.cm.ScalarMappable(norm=norm,cmap=cmap)
    fig.colorbar(sm,ax=list(axs.flat),orientation='horizontal',fraction=.035,pad=.03,label='Casos por 100 mil habitantes — mesma escala nos quatro mapas')
    salvar(fig,'08_mapas_estaduais','SINAN/MS + IBGE. Malha simplificada atual; coordenadas geográficas. Visualização estadual, sem inferência sobre limites municipais históricos.')
    fig,ax=plt.subplots(figsize=(11,5.6))
    categorias=['descartado','classificacao_nao_encerrada']
    ax.plot(a.ano_arquivo,a.flag_descartado/a.registros*100,label='Classificação 5 (descartado)',color='#df8450',lw=2)
    ax.plot(a.ano_arquivo,a.classificacao_nao_encerrada/a.registros*100,label='Sem classificação / 0 / 8 / 9',color='#126e82',lw=2)
    ax.set(title='Composição da classificação: uma limitação da série',xlabel='Ano do arquivo de notificação',ylabel='Percentual dos registros extraídos (%)')
    ax.grid(axis='y'); ax.legend(frameon=False); fig.subplots_adjust(bottom=.16)
    salvar(fig,'09_qualidade_classificacao','SINAN/MS. Ausência do código 5 em um arquivo não comprova ausência de descartes na vigilância; pode refletir a seleção da publicação.')
    (OUT/'figuras.json').write_text(json.dumps(arquivos,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(arquivos)} figuras geradas em {OUT}',flush=True)
    return arquivos

if __name__=='__main__':gerar()
