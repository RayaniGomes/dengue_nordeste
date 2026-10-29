"""Seleciona residentes no Nordeste e integra contagens com população por código e ano."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import zipfile
import pandas as pd
from coletar import ROOT, RAW, META, UFS, agora, ler_json, sha256

OUT = ROOT/'data/processed'
INTERIM = ROOT/'data/interim'
KEEP = {'NU_ANO','DT_NOTIFIC','DT_SIN_PRI','SG_UF','ID_MN_RESI',
        'CON_CLASSI','CLASSI_FIN','CON_CRITER','CRITERIO','CON_EVOLUC','EVOLUCAO',
        'NDUPLIC','NDUPLIC_N','ID_AGRAVO','ID_DG_NOT','CS_SEXO','NU_IDADE_N','NU_IDADE'}

def codigo6(s):
    s=s.fillna('').astype('string').str.strip().str.replace(r'\.0$','',regex=True)
    return s.where(s.str.fullmatch(r'\d{6,7}'),pd.NA).str[:6]

def populacao(inicio, fim):
    linhas=[]
    for path in sorted((RAW/'ibge').glob('pop_*_N*.json')):
        if path.name.endswith('.meta.json'): continue
        m=json.loads(path.with_name(path.name+'.meta.json').read_text(encoding='utf-8'))
        if not inicio <= m['ano'] <= fim: continue
        dados=ler_json(path)
        if not isinstance(dados,list) or len(dados)!=1:
            raise ValueError(f'Resposta IBGE inesperada: {path}')
        resultados=dados[0]['resultados']
        if len(resultados)!=1:
            raise ValueError(f'Consulta não está no total da população: {path}')
        for serie in resultados[0]['series']:
            local=serie['localidade']; v=serie['serie'].get(str(m['ano']))
            if not str(v).isdigit():
                pop=None
            else: pop=int(v)
            cod=str(local['id']); uf=cod[:2]
            if uf not in UFS: raise ValueError(f'UF fora do Nordeste na população: {cod}')
            linhas.append({'ano':m['ano'],'nivel':m['nivel'], 'codigo_ibge':cod,
                'codigo_municipio_6':cod[:6] if m['nivel']=='N6' else None,
                'codigo_uf':uf,'uf':UFS[uf], 'nome_localidade':local['nome'],
                'populacao':pop, 'tipo_populacao':m['tipo_populacao'],
                'tabela_ibge':m['tabela'], 'fonte_populacao':m['url'],
                'extracao_populacao':m['extraido_em']})
    p=pd.DataFrame(linhas)
    assert not p.duplicated(['ano','nivel','codigo_ibge']).any(), 'População com chave duplicada'
    assert not p.loc[p.nivel.eq('N6')].duplicated(['ano','codigo_municipio_6']).any(), 'Colisão nos códigos de seis dígitos'
    assert p.populacao.dropna().gt(0).all(), 'População não positiva'
    return p

def somar_partes(partes, keys):
    return pd.concat(partes,ignore_index=True).groupby(keys,dropna=False,as_index=False)['notificacoes'].sum()

def processar_sinan(ano):
    path=RAW/f'sinan/DENGBR{ano%100:02d}.csv.zip'
    with zipfile.ZipFile(path) as z:
        arquivos=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(arquivos)!=1: raise ValueError(f'ZIP ambíguo: {path}')
        with z.open(arquivos[0]) as f:
            header=f.readline().decode('utf-8-sig').strip()
    colunas=header.split(',')
    for c in ('NU_ANO','SG_UF','ID_MN_RESI','DT_NOTIFIC','DT_SIN_PRI'):
        if c not in colunas: raise ValueError(f'{c} ausente em {ano}')
    classe='CLASSI_FIN' if 'CLASSI_FIN' in colunas else 'CON_CLASSI'
    criterio='CRITERIO' if 'CRITERIO' in colunas else 'CON_CRITER'
    evolucao='EVOLUCAO' if 'EVOLUCAO' in colunas else 'CON_EVOLUC'
    partes_mun=[]; partes_uf=[]; partes_mensais=[]; partes_classes=[]
    audit=Counter(); classes=Counter()
    saida=INTERIM/f'sinan_ne_{ano}.csv.gz'
    parcial=saida.with_name(saida.name+'.part')
    with gzip.open(parcial,'wt',encoding='utf-8',newline='') as destino:
        primeiro=True
        for chunk in pd.read_csv(path,dtype='string',usecols=lambda c:c in KEEP,
                                 chunksize=100_000,encoding='utf-8',keep_default_na=False):
            audit['registros_brasil']+=len(chunk)
            uf=chunk.SG_UF.str.strip().str.upper().replace({v:k for k,v in UFS.items()})
            cod=codigo6(chunk.ID_MN_RESI)
            audit['codigo_ne_com_uf_residencia_ausente_ou_externa']+=int((cod.str[:2].isin(UFS)&~uf.isin(UFS)).sum())
            chunk=chunk.loc[uf.isin(UFS)].copy()
            if chunk.empty: continue
            chunk['codigo_uf']=uf.loc[chunk.index]
            chunk['uf']=chunk.codigo_uf.map(UFS)
            chunk['codigo_municipio_6']=cod.loc[chunk.index]
            chunk['codigo_municipio_residencia_original']=chunk.ID_MN_RESI
            chunk['municipio_consistente']=chunk.codigo_municipio_6.str[:2].eq(chunk.codigo_uf).fillna(False)
            audit['registros_ne']+=len(chunk)
            chunk['ano_arquivo']=ano
            chunk['ano']=pd.to_numeric(chunk.NU_ANO,errors='coerce').astype('Int64')
            audit['ano_divergente_ou_ausente']+=int(chunk.ano.ne(ano).fillna(True).sum())
            # NU_ANO é preservado; arquivo anual não substitui um ano inconsistente.
            chunk['ano_valido']=chunk.ano.eq(ano).fillna(False)
            chunk['classificacao_original']=chunk[classe] if classe in chunk else ''
            chunk['campo_classificacao']=classe
            chunk['criterio_original']=chunk[criterio] if criterio in chunk else ''
            chunk['evolucao_original']=chunk[evolucao] if evolucao in chunk else ''
            chunk['data_notificacao_original']=chunk.DT_NOTIFIC
            chunk['data_sintomas_original']=chunk.DT_SIN_PRI
            dt=pd.to_datetime(chunk.DT_NOTIFIC,format='%Y-%m-%d',errors='coerce')
            chunk['mes_notificacao']=dt.dt.month.astype('Int64')
            chunk['data_notificacao_consistente']=dt.dt.year.eq(ano)
            ds=pd.to_datetime(chunk.DT_SIN_PRI,format='%Y-%m-%d',errors='coerce')
            audit['data_notificacao_ausente_ou_invalida']+=int(dt.isna().sum())
            audit['data_notificacao_ano_divergente']+=int((dt.notna()&dt.dt.year.ne(ano)).sum())
            audit['data_sintomas_ausente_ou_invalida']+=int(ds.isna().sum())
            audit['sintomas_posteriores_notificacao']+=int((ds.notna()&dt.notna()&ds.gt(dt)).sum())
            audit['municipio_invalido_ou_uf_divergente']+=int((~chunk.municipio_consistente).sum())
            cols=['ano_arquivo','ano','ano_valido','codigo_uf','uf','codigo_municipio_residencia_original',
                'codigo_municipio_6','municipio_consistente','data_notificacao_original','data_sintomas_original',
                'mes_notificacao','data_notificacao_consistente','classificacao_original','campo_classificacao',
                'criterio_original','evolucao_original']
            for c in ('NDUPLIC','NDUPLIC_N','ID_AGRAVO','ID_DG_NOT','CS_SEXO','NU_IDADE','NU_IDADE_N'):
                if c in chunk: cols.append(c)
            chunk[cols].to_csv(destino,index=False,header=primeiro)
            primeiro=False
            validos=chunk.loc[chunk.ano_valido]
            audit['registros_ne_ano_valido']+=len(validos)
            audit['ne_ano_valido_sem_municipio_consistente']+=int((~validos.municipio_consistente).sum())
            classes.update(validos.classificacao_original.fillna('').replace('','AUSENTE').tolist())
            def agrupar(d, keys):
                return d.groupby(keys,dropna=False).size().rename('notificacoes').reset_index()
            partes_uf.append(agrupar(validos,['codigo_uf','ano']))
            partes_classes.append(agrupar(validos.assign(classificacao_original=validos.classificacao_original.replace('','AUSENTE')),
                                         ['codigo_uf','ano','classificacao_original','campo_classificacao']))
            partes_mun.append(agrupar(validos.loc[validos.municipio_consistente],['codigo_municipio_6','ano']))
            partes_mensais.append(agrupar(validos.loc[validos.data_notificacao_consistente],['codigo_uf','ano','mes_notificacao']))
    parcial.replace(saida)
    resumo={'ano':ano,**dict(audit),'campo_classificacao':classe,'frequencias_classificacao':dict(classes),
            'colunas_fonte':colunas,'arquivo_bruto':path.relative_to(ROOT).as_posix(),
            'sha256_bruto':sha256(path)}
    (META/f'auditoria_sinan_{ano}.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Processado {ano}: {audit["registros_ne"]:,} registros de residentes no NE',flush=True)
    return (somar_partes(partes_mun,['codigo_municipio_6','ano']),
            somar_partes(partes_uf,['codigo_uf','ano']),
            somar_partes(partes_mensais,['codigo_uf','ano','mes_notificacao']),
            somar_partes(partes_classes,['codigo_uf','ano','classificacao_original','campo_classificacao']),resumo)

def integrar(inicio=2000,fim=2025):
    OUT.mkdir(parents=True,exist_ok=True); INTERIM.mkdir(parents=True,exist_ok=True)
    p=populacao(inicio,fim)
    resultados=[processar_sinan(a) for a in range(inicio,fim+1)]
    cm=pd.concat([r[0] for r in resultados],ignore_index=True)
    cu=pd.concat([r[1] for r in resultados],ignore_index=True)
    mensal=pd.concat([r[2] for r in resultados],ignore_index=True)
    classificacoes=pd.concat([r[3] for r in resultados],ignore_index=True)
    auditorias=[r[4] for r in resultados]
    # Outer join não perde notificações com código sem população no mesmo ano.
    pm=p.loc[p.nivel.eq('N6')].drop(columns='nivel')
    municipal=cm.merge(pm,on=['codigo_municipio_6','ano'],how='outer',validate='one_to_one',indicator=True)
    municipal['status_integracao']=municipal.pop('_merge').astype('string').replace({
        'both':'integrado','left_only':'sem_populacao_no_ano','right_only':'sem_registro_sinan'})
    municipal.loc[municipal.status_integracao.eq('integrado') & municipal.populacao.isna(),
                  'status_integracao']='sem_populacao_valida'
    municipal['codigo_uf']=municipal.codigo_uf.fillna(municipal.codigo_municipio_6.str[:2])
    municipal['uf']=municipal.codigo_uf.map(UFS)
    # Estado-ano: inclui todos os nove estados, inclusive 2023 sem denominador.
    grade=pd.MultiIndex.from_product([list(UFS),range(inicio,fim+1)],names=['codigo_uf','ano']).to_frame(index=False)
    estadual=grade.merge(cu,on=['codigo_uf','ano'],how='left',validate='one_to_one')
    estadual=estadual.merge(p.loc[p.nivel.eq('N3')].drop(columns=['nivel','codigo_municipio_6']),
                            on=['codigo_uf','ano'],how='left',validate='one_to_one')
    estadual['uf']=estadual.codigo_uf.map(UFS)
    estadual['status_integracao']=estadual.populacao.notna().map({True:'integrado',False:'sem_populacao_no_ano'})
    # Retém ausência como NA: não transforma falta de registro em zero epidemiológico.
    municipal['notificacoes']=municipal.notificacoes.astype('Int64')
    estadual['notificacoes']=estadual.notificacoes.astype('Int64')
    for d in (municipal,estadual): d['populacao']=d.populacao.astype('Int64')
    mensal['uf']=mensal.codigo_uf.map(UFS)
    classificacoes['uf']=classificacoes.codigo_uf.map(UFS)
    assert int(estadual.notificacoes.sum()) == sum(a['registros_ne_ano_valido'] for a in auditorias)
    assert int(municipal.notificacoes.sum()) + sum(a['ne_ano_valido_sem_municipio_consistente'] for a in auditorias) == int(estadual.notificacoes.sum())
    assert int(classificacoes.notificacoes.sum()) == int(estadual.notificacoes.sum())
    assert estadual.uf.nunique()==9 and len(estadual)==9*(fim-inicio+1)
    # Relatório da cobertura, sem calcular incidência antes de definir os casos.
    cobertura=estadual.groupby('ano',as_index=False).agg(estados=('uf','nunique'),
        notificacoes=('notificacoes','sum'),estados_com_populacao=('populacao','count'))
    for nome,d in [('populacao_nordeste',p),('dengue_municipio_ano',municipal),
        ('dengue_estado_ano',estadual),('dengue_estado_mes_notificacao',mensal),
        ('classificacao_estado_ano',classificacoes),('cobertura_anual',cobertura)]:
        d.to_csv(OUT/f'{nome}.csv',index=False,encoding='utf-8-sig')
    municipal.loc[municipal.status_integracao.ne('integrado')].to_csv(OUT/'pendencias_integracao.csv',index=False,encoding='utf-8-sig')
    resumo={'gerado_em':agora(),'inicio':inicio,'fim':fim,'estados':list(UFS.values()),
        'notificacoes_ne':int(estadual.notificacoes.sum()),'linhas_municipio_ano':len(municipal),
        'linhas_estado_ano':len(estadual),'populacao_ausente_estado_ano':int(estadual.populacao.isna().sum()),
        'status_municipal':{str(k):int(v) for k,v in municipal.status_integracao.value_counts().items()},
        'verificacoes':'chaves únicas; 9 UFs; conservação das contagens estaduais, municipais e por classificação',
        'auditorias':auditorias}
    (META/'validacao_integracao.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in resumo.items() if k!='auditorias'},ensure_ascii=False,indent=2),flush=True)
    return resumo

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inicio',type=int,default=2000)
    parser.add_argument('--fim',type=int,default=2025)
    args=parser.parse_args()
    integrar(args.inicio,args.fim)
