"""Integra os CSVs extraidos do PostgreSQL, mantendo as regras do relatorio revisado."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

METRICAS = ['notificacoes','casos_provaveis','casos_confirmados','possiveis_duplicatas',
            'sem_idade','sem_sexo','sem_mes_sintomas']


def hash_arquivo(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while bloco:=f.read(4<<20): h.update(bloco)
    return h.hexdigest()


def localizar_manifesto(root):
    """Seleciona a extracao concluida mais recente, ignorando tentativas incompletas."""
    candidatos=[]
    for p in (Path(root)/'data/metadata/postgresql/relatorio_2000_2025').glob('*/manifesto.json'):
        m=json.loads(p.read_text(encoding='utf-8'))
        if m.get('status')=='concluido': candidatos.append((m['concluido_em'],p))
    if not candidatos: raise FileNotFoundError('Nenhuma extracao PostgreSQL concluida. Execute scripts/extrair_postgresql.py --env CAMINHO_DO_ENV.')
    return max(candidatos,key=lambda x:x[0])[1]


def conferir_arquivos(root, caminho):
    """Confere proveniencia, periodo e integridade dos cinco arquivos de entrada."""
    root=Path(root).resolve(); caminho=Path(caminho)
    m=json.loads(caminho.read_text(encoding='utf-8'))
    if m['status']!='concluido' or m['schema']!='public' or m['periodo']!=[2000,2025] or not m['somente_leitura']:
        raise ValueError('Manifesto nao corresponde a base tratada escolhida.')
    esperados={'notificacao_dengue_ne','populacao_municipio_ano','populacao_ne','municipio_ne','estado_ne'}
    if set(m['arquivos'])!=esperados: raise ValueError('Conjunto de tabelas inesperado.')
    linhas=[]
    for nome, meta in m['arquivos'].items():
        p=(root/meta['arquivo']).resolve()
        if not p.is_relative_to(root/'data/raw/postgresql'): raise ValueError('Caminho fora da pasta de extracao.')
        if p.stat().st_size!=meta['bytes'] or hash_arquivo(p)!=meta['sha256']: raise ValueError('Arquivo divergente: '+nome)
        if meta['registros_csv']!=meta['registros_postgresql']: raise ValueError('Contagem divergente no manifesto.')
        linhas.append({'tabela':nome,'registros':meta['registros_csv'],'sha256_conferido':True})
    for chave in ['resumo_anual','dicionario']:
        if hash_arquivo(root/m[chave]['arquivo'])!=m[chave]['sha256']: raise ValueError('Metadado divergente: '+chave)
    return m,pd.DataFrame(linhas)


def integrar(root, caminho):
    """Agrega em blocos, integra por chaves e concilia contagens e denominadores."""
    root=Path(root).resolve(); caminho=Path(caminho)
    m,auditoria=conferir_arquivos(root,caminho)
    def ler(nome):
        return pd.read_csv(root/m['arquivos'][nome]['arquivo'],dtype={'cod_mun7':'string','cod_mun6':'string'})
    mun=ler('municipio_ne'); uf=ler('estado_ne'); pop=ler('populacao_municipio_ano'); pop_bruta=ler('populacao_ne')
    for nome,df,chaves in [('municipio_ne',mun,['cod_mun7']),('estado_ne',uf,['uf_cod']),
                          ('populacao_municipio_ano',pop,['cod_mun7','ano']),('populacao_ne',pop_bruta,['cod_mun7','ano'])]:
        if len(df)!=m['arquivos'][nome]['registros_csv']: raise ValueError('Contagem de apoio divergente: '+nome)
        if df.duplicated(chaves).any(): raise ValueError('Chave duplicada: '+nome)
    if set(uf.uf_cod)!=set(range(21,30)) or not mun.uf_cod.isin(uf.uf_cod).all(): raise ValueError('UFs fora do recorte.')
    if not pop.ano.between(2000,2025).all() or not pop.populacao.gt(0).all(): raise ValueError('Denominador invalido.')
    if not pop_bruta.ano.between(2000,2025).all(): raise ValueError('Ano fora do periodo na populacao consolidada.')
    if not pop.cod_mun7.isin(mun.cod_mun7).all() or not pop_bruta.cod_mun7.isin(mun.cod_mun7).all(): raise ValueError('Populacao sem cadastro municipal.')
    cadastro=mun[['cod_mun7','nome','uf_cod']].merge(uf[['uf_cod','sigla']],on='uf_cod',validate='many_to_one').rename(columns={'sigla':'uf','nome':'municipio'})
    partes=[]; anuais=[]
    colunas=['cod_mun7','ano','caso_provavel','caso_confirmado','possivel_duplicata','idade_anos','sexo','mes_sintomas']
    tipos={'cod_mun7':'string','ano':'int16','idade_anos':'Int16','mes_sintomas':'Int8',
           'sexo':'string','caso_provavel':'boolean','caso_confirmado':'boolean','possivel_duplicata':'boolean'}
    arquivo=root/m['arquivos']['notificacao_dengue_ne']['arquivo']
    for i,bloco in enumerate(pd.read_csv(arquivo,usecols=colunas,dtype=tipos,true_values=['t'],false_values=['f'],chunksize=200_000),1):
        if not bloco.ano.between(2000,2025).all() or not bloco.cod_mun7.isin(mun.cod_mun7).all(): raise ValueError('Notificacao fora do periodo ou sem municipio.')
        cont=pd.DataFrame({'cod_mun7':bloco.cod_mun7,'ano':bloco.ano,'notificacoes':1,
            'casos_provaveis':bloco.caso_provavel.fillna(False).astype('int64'),
            'casos_confirmados':bloco.caso_confirmado.fillna(False).astype('int64'),
            'possiveis_duplicatas':bloco.possivel_duplicata.fillna(False).astype('int64'),
            'sem_idade':bloco.idade_anos.isna().astype('int64'),
            'sem_sexo':bloco.sexo.fillna('').str.strip().eq('').astype('int64'),
            'sem_mes_sintomas':bloco.mes_sintomas.isna().astype('int64')})
        partes.append(cont.groupby(['cod_mun7','ano'],observed=True,as_index=False)[METRICAS].sum())
        anuais.append(cont.groupby('ano',as_index=False)[METRICAS].sum())
        if i%5==0: print(f'Blocos processados: {i} ({i*200_000:,} registros)',flush=True)
    observado=pd.concat(partes,ignore_index=True).groupby(['cod_mun7','ano'],as_index=False,observed=True)[METRICAS].sum()
    anual=pd.concat(anuais,ignore_index=True).groupby('ano',as_index=False)[METRICAS].sum().sort_values('ano').reset_index(drop=True)
    esperado=pd.read_csv(root/m['resumo_anual']['arquivo']).sort_values('ano').reset_index(drop=True)
    pd.testing.assert_frame_equal(anual,esperado,check_dtype=False)
    if set(anual.ano)!=set(range(2000,2026)): raise ValueError('Cobertura anual incompleta.')
    painel=pop.rename(columns={'fonte':'fonte_populacao'}).merge(observado,on=['cod_mun7','ano'],how='outer',validate='one_to_one',indicator=True)
    sem_pop=painel.loc[painel['_merge'].eq('right_only')]
    if int(sem_pop.casos_provaveis.sum())!=0: raise ValueError('Casos provaveis sem populacao.')
    for c in METRICAS: painel[c]=painel[c].fillna(0).astype('int64')
    painel=painel.drop(columns='_merge').merge(cadastro,on='cod_mun7',how='left',validate='many_to_one')
    if painel.uf.isna().any(): raise ValueError('Cadastro municipal incompleto apos integracao.')
    painel['incidencia_provaveis_100mil']=(painel.casos_provaveis/painel.populacao*100_000).where(painel.populacao.gt(0))
    painel=painel.sort_values(['uf_cod','cod_mun7','ano']).reset_index(drop=True)
    painel_uf=painel.groupby(['uf_cod','uf','ano'],as_index=False)[METRICAS+['populacao']].sum(min_count=1)
    painel_uf['incidencia_provaveis_100mil']=painel_uf.casos_provaveis/painel_uf.populacao*100_000
    regiao=painel_uf.groupby('ano',as_index=False)[METRICAS+['populacao']].sum(min_count=1)
    regiao['incidencia_provaveis_100mil']=regiao.casos_provaveis/regiao.populacao*100_000
    pd.testing.assert_frame_equal(regiao[['ano']+METRICAS],anual,check_dtype=False)
    if len(painel_uf)!=9*26: raise ValueError('Painel UF-ano incompleto.')
    if not painel_uf.populacao.gt(0).all(): raise ValueError('Populacao estadual invalida.')
    if int(painel.populacao.sum())!=int(pop.populacao.sum()): raise ValueError('Populacao duplicada ou perdida na juncao.')
    cobertura=(pop.merge(cadastro[['cod_mun7','uf']],on='cod_mun7',validate='many_to_one')
               .assign(interpolada=lambda x:x.fonte.eq('interpolada'))
               .groupby(['uf','ano'],as_index=False).agg(municipios_com_populacao=('cod_mun7','nunique'),municipios_interpolados=('interpolada','sum')))
    stamp=datetime.now(ZoneInfo('America/Fortaleza')).strftime('%Y%m%d_%H%M%S')
    saida=root/'data/processed/postgresql/relatorio_2000_2025'/m['execucao']/'integracao'/stamp
    saida.mkdir(parents=True,exist_ok=False)
    arquivos={}
    for nome,df in [('painel_municipio_ano',painel),('painel_uf_ano',painel_uf),('painel_regiao_ano',regiao),('cobertura_populacao_uf_ano',cobertura)]:
        p=saida/(nome+'.csv'); df.to_csv(p,index=False)
        relido=pd.read_csv(p,dtype={'cod_mun7':'string'})
        if len(relido)!=len(df): raise ValueError('Falha na escrita do painel.')
        arquivos[nome]={'arquivo':p.relative_to(root).as_posix(),'linhas':len(df),'sha256':hash_arquivo(p)}
    validacao={'status':'concluido','concluido_em':datetime.now(ZoneInfo('America/Fortaleza')).isoformat(),
        'manifesto_entrada':caminho.relative_to(root).as_posix(),'sha256_manifesto_entrada':hash_arquivo(caminho),
        'periodo':[2000,2025],'origem':'public.notificacao_dengue_ne e tabelas IBGE do mesmo snapshot',
        'totais':{c:int(regiao[c].sum()) for c in METRICAS},'notificacoes_sem_populacao':int(sem_pop.notificacoes.sum()),
        'casos_provaveis_sem_populacao':int(sem_pop.casos_provaveis.sum()),
        'soma_populacao_municipio_ano':int(pop.populacao.sum()),'arquivos':arquivos,
        'verificacoes':['SHA-256 das entradas','chaves unicas','juncoes validadas','recorte temporal e geografico',
                        'sete metricas por ano conciliadas com PostgreSQL','populacao conservada na juncao',
                        '26 anos e 234 UF-anos','casos provaveis sem denominador igual a zero'],
        'limites':['Notificacoes ja tratadas no banco; nao e SINAN bruto nacional.',
                   'Flags e populacao interpolada mantidas como no banco; nenhuma decisao pendente encerrada.',
                   'Somente agregados sao exibidos no notebook; arquivos individuais permanecem locais.']}
    meta=root/'data/metadata/postgresql/relatorio_2000_2025'/m['execucao']/'integracoes'/(stamp+'.json')
    meta.parent.mkdir(parents=True,exist_ok=True); meta.write_text(json.dumps(validacao,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'manifesto':m,'auditoria_arquivos':auditoria,'painel_municipio_ano':painel,
            'painel_uf_ano':painel_uf,'painel_regiao_ano':regiao,'cobertura':cobertura,
            'validacao':validacao,'caminho_validacao':meta.relative_to(root).as_posix(),'saida':saida}