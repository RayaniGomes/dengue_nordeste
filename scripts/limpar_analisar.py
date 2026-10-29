"""Etapa 2: limpeza rastreável e EDA; não contém modelos preditivos."""
from __future__ import annotations
import json
from pathlib import Path
import platform
import sys
import numpy as np
import pandas as pd
from coletar import ROOT, UFS, agora, sha256

OUT=ROOT/'data/processed/etapa2'
CLEAN=ROOT/'data/interim/etapa2'
META=ROOT/'data/metadata'
CLASSIFICACOES={
 '1':'dengue_classica_legado','2':'dengue_complicacoes_legado',
 '3':'febre_hemorragica_legado','4':'choque_dengue_legado',
 '5':'descartado','8':'inconclusivo','10':'dengue',
 '11':'dengue_sinais_alarme','12':'dengue_grave','13':'chikungunya',
 '':'sem_classificacao','0':'ignorado','9':'ignorado'}
COMPATIVEIS={'1','2','3','4','10','11','12'}
MOTIVOS=['uf_invalida','notificacao_invalida_ou_fora_recorte',
         'agravo_incompativel_ou_ausente','duplicidade_marcada',
         'classificacao_desconhecida','descartado','chikungunya',
         'sintomas_invalidos_ou_fora_recorte','sintomas_apos_notificacao']

def limpar_registros(d, ano, data_corte='2025-12-31'):
    """Função pura: preserva flags sobrepostas e um motivo exclusivo de exclusão."""
    d=d.copy()
    for c in d.columns:
        d[c]=d[c].fillna('').astype('string').str.strip()
    d['linha_recorte']=np.arange(len(d))+2
    d['ano_arquivo']=ano
    dt=pd.to_datetime(d.data_notificacao_original,format='%Y-%m-%d',errors='coerce')
    ds=pd.to_datetime(d.data_sintomas_original,format='%Y-%m-%d',errors='coerce')
    d['data_notificacao']=dt
    d['data_sintomas']=ds
    d['ano_notificacao']=dt.dt.year.astype('Int64')
    d['ano_sintomas']=ds.dt.year.astype('Int64')
    d['mes_sintomas']=ds.dt.month.astype('Int64')
    d['atraso_notificacao_dias']=(dt-ds).dt.days.astype('Int64')
    d['ano_notificacao_divergente_arquivo']=dt.notna()&dt.dt.year.ne(ano)
    nu=pd.to_numeric(d['ano'],errors='coerce')
    d['nu_ano_divergente_data']=dt.notna()&(nu.isna()|nu.ne(dt.dt.year))
    # Os arquivos de 2016 misturam vocabulários legado e novo. Não aplicar o
    # código 2 (complicações, legado) indiscriminadamente aos layouts recentes.
    comuns={'','0','5','8','9','13'}
    permitidos=comuns | ({'1','2','3','4'} if ano<=2013 else {'10','11','12'})
    if ano==2016:permitidos |= {'1','2','3','4'}
    conhecida=d.classificacao_original.isin(permitidos)
    d['classificacao_harmonizada']=d.classificacao_original.map(CLASSIFICACOES).where(conhecida,'desconhecida').fillna('desconhecida')
    # ID_DG_NOT dos arquivos legados é diagnóstico, NÃO é o campo CID-10.
    if 'ID_AGRAVO' in d:
        agravo=d.ID_AGRAVO.str.upper().str.replace('.','',regex=False)
        agravo_ok=agravo.isin(['A90','A91'])
        d['agravo_verificado_por']='ID_AGRAVO'
    else:
        agravo_ok=pd.Series(True,index=d.index)
        d['agravo_verificado_por']='recurso_Dengue_legado_sem_campo_CID'
    duplicada=d['NDUPLIC_N'].eq('2') if 'NDUPLIC_N' in d else pd.Series(False,index=d.index)
    # Só o valor 2 do campo documentado NDUPLIC_N é excluído. Flags legadas S/1
    # não recebem significado presumido; ficam preservadas para revisão humana.
    flags={
      'uf_invalida':~d.codigo_uf.isin(UFS),
      'notificacao_invalida_ou_fora_recorte':dt.isna()|~dt.between(pd.Timestamp('2000-01-01'),pd.Timestamp(data_corte)),
      'agravo_incompativel_ou_ausente':~agravo_ok,
      'duplicidade_marcada':duplicada,
      'classificacao_desconhecida':~conhecida,
      'descartado':d.classificacao_original.eq('5'),
      'chikungunya':d.classificacao_original.eq('13'),
      'sintomas_invalidos_ou_fora_recorte':ds.isna()|~ds.dt.year.between(2000,2025),
      'sintomas_apos_notificacao':ds.notna()&dt.notna()&ds.gt(dt),
    }
    motivo=pd.Series('incluido',index=d.index,dtype='string')
    for nome in MOTIVOS:
        flag=flags[nome].fillna(True)
        d['flag_'+nome]=flag
        motivo.loc[motivo.eq('incluido')&flag]=nome
    d['motivo_exclusao']=motivo
    d['caso_provavel_operacional']=motivo.eq('incluido')
    d['classificacao_compativel_dengue']=d.classificacao_original.isin(COMPATIVEIS)
    d['caso_criterio_estrito']=d.caso_provavel_operacional & d.classificacao_compativel_dengue & d.criterio_original.isin(['1','2'])
    d['municipio_valido']=d.codigo_municipio_6.str.fullmatch(r'\d{6}').fillna(False)&d.codigo_municipio_6.str[:2].eq(d.codigo_uf)
    return d

def contar(d,keys):
    return d.groupby(keys,dropna=False).size().rename('n').reset_index()

def consolidar(partes,keys,nome):
    d=pd.concat(partes,ignore_index=True)
    return d.groupby(keys,dropna=False,as_index=False)['n'].sum().rename(columns={'n':nome})

def salvar(d,nome):
    d.to_csv(OUT/f'{nome}.csv',index=False,encoding='utf-8-sig',float_format='%.8f')

def executar():
    OUT.mkdir(parents=True,exist_ok=True); CLEAN.mkdir(parents=True,exist_ok=True)
    auditoria=[]; classificacoes=[]; entradas=[]
    estado=[]; estrito=[]; municipio=[]; municipio_estrito=[]; meses=[]; notificacoes=[]
    chaves_observadas=[]; atrasos=[]
    complemento_path=META/'complemento_2026.json'
    if not complemento_path.exists():
        raise FileNotFoundError('Execute scripts/coletar_complemento_2026.py antes da limpeza.')
    complemento=json.loads(complemento_path.read_text(encoding='utf-8'))
    data_corte=complemento['data_corte']
    fontes=[(a,ROOT/f'data/interim/sinan_ne_{a}.csv.gz') for a in range(2000,2026)]
    if complemento['registros_recorte']>0:
        fontes.append((2026,ROOT/complemento['arquivo_recorte']))
    for ano,path in fontes:
        original=pd.read_csv(path,dtype='string',keep_default_na=False)
        d=limpar_registros(original,ano,data_corte=data_corte)
        entradas.append({'arquivo':path.relative_to(ROOT).as_posix(),'sha256':sha256(path)})
        incl=d.loc[d.caso_provavel_operacional].copy()
        strict=d.loc[d.caso_criterio_estrito]
        # Denominador de cobertura: notificações com datas clínicas e residência
        # utilizáveis, inclusive as descartadas; permite zero de casos apenas
        # onde há registro observado, sem transformar ausência municipal em zero.
        observada=(~d.flag_uf_invalida & ~d.flag_notificacao_invalida_ou_fora_recorte &
                   ~d.flag_sintomas_invalidos_ou_fora_recorte & ~d.flag_sintomas_apos_notificacao & d.municipio_valido)
        chaves_observadas.append(contar(d.loc[observada],['codigo_municipio_6','ano_sintomas']))
        estado.append(contar(incl,['codigo_uf','ano_sintomas']))
        estrito.append(contar(strict,['codigo_uf','ano_sintomas']))
        municipio.append(contar(incl.loc[incl.municipio_valido],['codigo_municipio_6','ano_sintomas']))
        municipio_estrito.append(contar(strict.loc[strict.municipio_valido],['codigo_municipio_6','ano_sintomas']))
        meses.append(contar(incl,['codigo_uf','ano_sintomas','mes_sintomas']))
        base_not=d.loc[~d.flag_notificacao_invalida_ou_fora_recorte & ~d.flag_uf_invalida]
        notificacoes.append(contar(base_not,['codigo_uf','ano_notificacao']))
        classificacoes.append(contar(d.assign(ano_arquivo=ano),['ano_arquivo','classificacao_original','classificacao_harmonizada']))
        motivos=d.motivo_exclusao.value_counts().to_dict()
        a={'ano_arquivo':ano,'registros':len(d),'incluidos':len(incl),'criterio_estrito':len(strict),
          'incluidos_atraso_superior60':int(incl.atraso_notificacao_dias.gt(60).sum()),
          'sem_municipio_entre_incluidos':int((~incl.municipio_valido).sum()),
          'nu_ano_divergente_data':int(d.nu_ano_divergente_data.sum()),
          'ano_notificacao_divergente_arquivo':int(d.ano_notificacao_divergente_arquivo.sum()),
          'classificacao_nao_encerrada':int(d.classificacao_original.isin(['','0','8','9']).sum()),
          **{f'excluido_{m}':int(motivos.get(m,0)) for m in MOTIVOS},
          **{f'flag_{m}':int(d['flag_'+m].sum()) for m in MOTIVOS}}
        auditoria.append(a)
        for uf,g in incl.groupby('codigo_uf'):
            atrasos.append({'ano_arquivo':ano,'codigo_uf':uf,'registros':len(g),
              'mediana_dias':g.atraso_notificacao_dias.median(),
              'p95_dias':g.atraso_notificacao_dias.quantile(.95),
              'maior_60_dias':int(g.atraso_notificacao_dias.gt(60).sum())})
        # Todas as linhas, flags e motivos são preservados; o gzip é atômico.
        saida=CLEAN/f'sinan_ne_{ano}_classificado.csv.gz'
        parcial=saida.with_name(saida.name+'.part')
        d.to_csv(parcial,index=False,compression={'method':'gzip','compresslevel':1})
        parcial.replace(saida)
        print(f'{ano}: {len(d):,} registros -> {len(incl):,} prováveis operacionais',flush=True)
    aud=pd.DataFrame(auditoria); salvar(aud,'auditoria_limpeza')
    salvar(pd.DataFrame(atrasos),'atrasos_notificacao')
    salvar(consolidar(classificacoes,['ano_arquivo','classificacao_original','classificacao_harmonizada'],'registros'),'classificacoes_harmonizadas')
    total=int(aud.incluidos.sum())
    assert int(aud.registros.sum()) == total + int(aud[[f'excluido_{m}' for m in MOTIVOS]].sum().sum())
    ca=consolidar(estado,['codigo_uf','ano_sintomas'],'casos_probaveis_operacionais').rename(columns={'ano_sintomas':'ano'})
    ce=consolidar(estrito,['codigo_uf','ano_sintomas'],'casos_criterio_estrito').rename(columns={'ano_sintomas':'ano'})
    cm=consolidar(municipio,['codigo_municipio_6','ano_sintomas'],'casos_probaveis_operacionais').rename(columns={'ano_sintomas':'ano'})
    cme=consolidar(municipio_estrito,['codigo_municipio_6','ano_sintomas'],'casos_criterio_estrito').rename(columns={'ano_sintomas':'ano'})
    obs=consolidar(chaves_observadas,['codigo_municipio_6','ano_sintomas'],'registros_com_datas_utilizaveis').rename(columns={'ano_sintomas':'ano'})
    pop=pd.read_csv(ROOT/'data/processed/populacao_nordeste.csv',dtype={'codigo_ibge':'string','codigo_uf':'string','codigo_municipio_6':'string'})
    pop['populacao']=pd.to_numeric(pop.populacao,errors='coerce')
    grade=pd.MultiIndex.from_product([list(UFS),range(2000,2026)],names=['codigo_uf','ano']).to_frame(index=False)
    e=grade.merge(ca,on=['codigo_uf','ano'],how='left',validate='one_to_one').merge(ce,on=['codigo_uf','ano'],how='left',validate='one_to_one')
    assert e.casos_probaveis_operacionais.notna().all()
    e['casos_criterio_estrito']=e.casos_criterio_estrito.fillna(0).astype(int)
    e=e.merge(pop.loc[pop.nivel.eq('N3'),['codigo_uf','ano','populacao','tipo_populacao']],on=['codigo_uf','ano'],how='left',validate='one_to_one')
    e['uf']=e.codigo_uf.map(UFS)
    e['incidencia_100mil']=e.casos_probaveis_operacionais/e.populacao*100000
    e['incidencia_criterio_estrito_100mil']=e.casos_criterio_estrito/e.populacao*100000
    e=e.sort_values(['codigo_uf','ano'])
    e['variacao_anual_pct']=e.groupby('codigo_uf').casos_probaveis_operacionais.pct_change(fill_method=None)*100
    # Outliers temporais são sinalizados no histórico da mesma UF, nunca removidos.
    g=e.groupby('codigo_uf').incidencia_100mil
    e['q1_uf']=g.transform(lambda s:s.quantile(.25)); e['q3_uf']=g.transform(lambda s:s.quantile(.75))
    e['limite_superior_iqr_uf']=e.q3_uf+1.5*(e.q3_uf-e.q1_uf)
    e['outlier_temporal_iqr']=e.incidencia_100mil.gt(e.limite_superior_iqr_uf).astype('boolean').mask(e.incidencia_100mil.isna(),pd.NA)
    salvar(e,'estado_ano_limpo')
    pm=pop.loc[pop.nivel.eq('N6'),['codigo_municipio_6','codigo_ibge','codigo_uf','ano','nome_localidade','populacao','tipo_populacao']]
    m=obs.merge(cm,on=['codigo_municipio_6','ano'],how='outer',validate='one_to_one')
    m=m.merge(cme,on=['codigo_municipio_6','ano'],how='outer',validate='one_to_one')
    observados=m.registros_com_datas_utilizaveis.gt(0)
    m.loc[observados,['casos_probaveis_operacionais','casos_criterio_estrito']]=m.loc[observados,['casos_probaveis_operacionais','casos_criterio_estrito']].fillna(0)
    m=m.merge(pm,on=['codigo_municipio_6','ano'],how='outer',validate='one_to_one')
    m['codigo_uf']=m.codigo_uf.fillna(m.codigo_municipio_6.str[:2]); m['uf']=m.codigo_uf.map(UFS)
    # Somente o nome pode receber referência de outro ano; população nunca.
    nomes=pm.sort_values('ano').drop_duplicates('codigo_municipio_6',keep='last').set_index('codigo_municipio_6').nome_localidade
    m['nome_referencia']=m.nome_localidade.fillna(m.codigo_municipio_6.map(nomes))
    m['status_cobertura']=np.select([m.registros_com_datas_utilizaveis.isna(),m.populacao.isna()],
                                   ['sem_registro_utilizavel','sem_populacao'],default='integrado')
    m['incidencia_100mil']=m.casos_probaveis_operacionais/m.populacao*100000
    m['incidencia_criterio_estrito_100mil']=m.casos_criterio_estrito/m.populacao*100000
    # Outlier espacial: outros municípios da mesma UF no mesmo ano.
    gm=m.groupby(['codigo_uf','ano']).incidencia_100mil
    m['q1_uf_ano']=gm.transform(lambda s:s.quantile(.25)); m['q3_uf_ano']=gm.transform(lambda s:s.quantile(.75))
    m['limite_superior_iqr_uf_ano']=m.q3_uf_ano+1.5*(m.q3_uf_ano-m.q1_uf_ano)
    m['outlier_espacial_iqr']=m.incidencia_100mil.gt(m.limite_superior_iqr_uf_ano).astype('boolean').mask(m.incidencia_100mil.isna(),pd.NA)
    salvar(m,'municipio_ano_limpo')
    salvar(m.loc[m.outlier_espacial_iqr.fillna(False)],'outliers_municipais')
    salvar(e.loc[e.outlier_temporal_iqr.fillna(False)],'outliers_estaduais')
    mensal=consolidar(meses,['codigo_uf','ano_sintomas','mes_sintomas'],'casos_probaveis_operacionais').rename(columns={'ano_sintomas':'ano','mes_sintomas':'mes'})
    calendario=pd.MultiIndex.from_product([list(UFS),range(2000,2026),range(1,13)],names=['codigo_uf','ano','mes']).to_frame(index=False)
    mensal=calendario.merge(mensal,on=['codigo_uf','ano','mes'],how='left',validate='one_to_one')
    # Todos os estados-ano possuem casos observados; zero aqui é contagem de
    # registros disponíveis para uma célula do calendário, sem afirmar ausência de transmissão.
    mensal['casos_probaveis_operacionais']=mensal.casos_probaveis_operacionais.fillna(0).astype(int)
    mensal['uf']=mensal.codigo_uf.map(UFS)
    anual=mensal.groupby(['codigo_uf','ano']).casos_probaveis_operacionais.transform('sum')
    mensal['participacao_no_ano_pct']=mensal.casos_probaveis_operacionais/anual.replace(0,np.nan)*100
    salvar(mensal,'estado_mes_sintomas')
    saz=mensal.loc[mensal.ano.between(2001,2024)].groupby(['codigo_uf','uf','mes'],as_index=False).agg(
        participacao_media_pct=('participacao_no_ano_pct','mean'),
        participacao_mediana_pct=('participacao_no_ano_pct','median'),anos=('ano','nunique'))
    salvar(saz,'sazonalidade_estados')
    regional=e.groupby('ano',as_index=False).agg(casos_probaveis_operacionais=('casos_probaveis_operacionais','sum'),casos_criterio_estrito=('casos_criterio_estrito','sum'))
    # min_count=9 impede usar a soma parcial de populações como denominador regional.
    rp=e.groupby('ano').populacao.sum(min_count=9).rename('populacao')
    regional=regional.merge(rp,on='ano',validate='one_to_one')
    regional['incidencia_100mil']=regional.casos_probaveis_operacionais/regional.populacao*100000
    regional['fracao_criterio_estrito_pct']=regional.casos_criterio_estrito/regional.casos_probaveis_operacionais*100
    salvar(regional,'nordeste_ano')
    salvar(consolidar(notificacoes,['codigo_uf','ano_notificacao'],'notificacoes_com_data_valida'),'notificacoes_por_data')
    descr=e.groupby('uf')[['casos_probaveis_operacionais','incidencia_100mil']].describe(percentiles=[.25,.5,.75]).stack(0,future_stack=True).reset_index()
    salvar(descr,'estatisticas_estaduais')
    cobertura=m.groupby('ano',as_index=False).agg(municipios_na_base=('codigo_municipio_6','size'),municipios_com_registro=('registros_com_datas_utilizaveis','count'),municipios_com_incidencia=('incidencia_100mil','count'))
    salvar(cobertura,'cobertura_municipal')
    ranking=m.loc[m.ano.eq(2024)&m.populacao.ge(10000)&m.casos_probaveis_operacionais.ge(20)].sort_values('incidencia_100mil',ascending=False).head(20)
    salvar(ranking,'ranking_municipios_2024')
    ultimo=e.loc[e.ano.eq(2025)].sort_values('incidencia_100mil',ascending=False)
    pico=regional.loc[regional.casos_probaveis_operacionais.idxmax()]
    mm=mensal.loc[mensal.ano.between(2001,2024)].groupby(['ano','mes'],as_index=False).casos_probaveis_operacionais.sum()
    mm['participacao_pct']=mm.casos_probaveis_operacionais/mm.groupby('ano').casos_probaveis_operacionais.transform('sum')*100
    saz_ne=mm.groupby('mes',as_index=False).agg(participacao_media_pct=('participacao_pct','mean'))
    salvar(saz_ne,'sazonalidade_nordeste')
    sem1=float(saz_ne.loc[saz_ne.mes.le(6),'participacao_media_pct'].sum())
    ano24=m.loc[m.ano.eq(2024)&m.incidencia_100mil.notna()].copy()
    # Spearman = Pearson dos postos; dispensa scipy e preserva empates por posto médio.
    rho=float(ano24[['populacao','casos_probaveis_operacionais']].rank().corr().iloc[0,1])
    resumo={'gerado_em':agora(),'versao_regras':'2.0','inicio':2000,'fim':2025,
        'eixo_temporal_principal':'ano/mês de início dos sintomas, sem substituição por notificação',
        'data_corte_notificacoes':data_corte,'complemento_2026':True,
        'registros_entrada':int(aud.registros.sum()),'casos_probaveis_operacionais':total,
        'casos_criterio_estrito':int(aud.criterio_estrito.sum()),
        'casos_atraso_superior60_dias':int(aud.incluidos_atraso_superior60.sum()),
        'exclusoes':{x:int(aud['excluido_'+x].sum()) for x in MOTIVOS},
        'soma_estado_ano':int(e.casos_probaveis_operacionais.sum()),
        'soma_municipio_ano':int(m.casos_probaveis_operacionais.sum()),
        'casos_sem_municipio_valido':int(aud.sem_municipio_entre_incluidos.sum()),
        'soma_mensal':int(mensal.casos_probaveis_operacionais.sum()),
        'incidencia_ausente_estado_ano':int(e.incidencia_100mil.isna().sum()),
        'pico_casos_ano':int(pico.ano),'pico_casos':int(pico.casos_probaveis_operacionais),
        'participacao_media_primeiro_semestre_2001_2024_pct':sem1,
        'mes_pico_sazonal':int(saz_ne.loc[saz_ne.participacao_media_pct.idxmax(),'mes']),
        'uf_maior_incidencia_2025':ultimo.iloc[0].uf,'maior_incidencia_2025':float(ultimo.iloc[0].incidencia_100mil),
        'outliers_estaduais':int(e.outlier_temporal_iqr.fillna(False).sum()),
        'spearman_populacao_casos_municipais_2024':rho,
        'metodo_correlacao':'Pearson dos postos médios (Spearman), sem teste inferencial',
        'fontes_classificacao':['DIC_DADOS_ONLINE.pdf (SINAN, 2015)','ficha SINAN NET (2006)','guia MS/ficha CENEPI (2001)'],
        'software':{'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__,'plataforma':platform.platform()},
        'entradas':entradas,'script_sha256':sha256(Path(__file__))}
    assert resumo['soma_estado_ano']==resumo['soma_mensal']==total
    assert resumo['soma_municipio_ano']+resumo['casos_sem_municipio_valido']==total
    assert not e.duplicated(['codigo_uf','ano']).any()
    assert not m.duplicated(['codigo_municipio_6','ano']).any()
    assert e.casos_criterio_estrito.le(e.casos_probaveis_operacionais).all()
    assert e.loc[e.ano.eq(2023),'incidencia_100mil'].isna().all()
    (META/'validacao_etapa2.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in resumo.items() if k not in ['entradas','software']},ensure_ascii=False,indent=2),flush=True)
    return resumo

if __name__=='__main__':executar()
