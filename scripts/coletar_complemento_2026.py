"""Complemento de notificações tardias; o estudo continua restrito a sintomas até 2025."""
import json
import zipfile
import pandas as pd
from coletar import ROOT, RAW, META, baixar, sha256, agora, UFS
from integrar import KEEP, codigo6

def coletar_complemento():
    catalogo=json.loads((META/'catalogo_sinan.json').read_text(encoding='utf-8'))
    recurso=next(r for r in catalogo['resources'] if r['format']=='CSV' and r['name']=='Dengue - 2026')
    path=baixar(recurso['url'],RAW/'sinan/DENGBR26.csv.zip','Ministério da Saúde/SINAN',
        {'ano_arquivo':2026,'recurso_id':recurso['id'],'atualizado_na_fonte':recurso['last_modified'],
         'finalidade':'Complementar sintomas até 2025 notificados em 2026; não incluir sintomas de 2026'})
    destino=ROOT/'data/interim/complemento_2026_sintomas_ate2025.csv.gz'
    partes=[]; total=0; total_ne=0; menor_sintoma=None
    for d in pd.read_csv(path,dtype='string',keep_default_na=False,usecols=lambda c:c in KEEP,chunksize=100000):
        total+=len(d)
        uf=d.SG_UF.str.strip().str.upper().replace({v:k for k,v in UFS.items()})
        ds=pd.to_datetime(d.DT_SIN_PRI,format='%Y-%m-%d',errors='coerce')
        total_ne+=int(uf.isin(UFS).sum())
        minimo=ds.loc[uf.isin(UFS)].min()
        if pd.notna(minimo) and (menor_sintoma is None or minimo<menor_sintoma):menor_sintoma=minimo
        d=d.loc[uf.isin(UFS)&ds.dt.year.between(2000,2025)].copy()
        if d.empty:continue
        d['codigo_uf']=uf.loc[d.index]; d['uf']=d.codigo_uf.map(UFS)
        d['codigo_municipio_residencia_original']=d.ID_MN_RESI
        d['codigo_municipio_6']=codigo6(d.ID_MN_RESI)
        d['ano']=d.NU_ANO; d['ano_arquivo']=2026
        d['data_notificacao_original']=d.DT_NOTIFIC; d['data_sintomas_original']=d.DT_SIN_PRI
        d['classificacao_original']=d.CLASSI_FIN; d['campo_classificacao']='CLASSI_FIN'
        d['criterio_original']=d.CRITERIO; d['evolucao_original']=d.EVOLUCAO
        cols=['ano','ano_arquivo','codigo_uf','uf','codigo_municipio_residencia_original','codigo_municipio_6',
              'data_notificacao_original','data_sintomas_original','classificacao_original','campo_classificacao',
              'criterio_original','evolucao_original']+[c for c in ['NDUPLIC_N','ID_AGRAVO','CS_SEXO','NU_IDADE_N'] if c in d]
        partes.append(d[cols])
    if partes:
        resultado=pd.concat(partes,ignore_index=True)
    else:
        resultado=pd.DataFrame(columns=['ano','ano_arquivo','codigo_uf','uf','codigo_municipio_residencia_original','codigo_municipio_6',
            'data_notificacao_original','data_sintomas_original','classificacao_original','campo_classificacao','criterio_original','evolucao_original'])
    resultado.to_csv(destino,index=False,compression='gzip')
    meta=json.loads(path.with_name(path.name+'.meta.json').read_text(encoding='utf-8'))
    resumo={'gerado_em':agora(),'data_corte':meta['extraido_em'][:10],'recurso_original':meta,
            'registros_brasil_2026_lidos':total,'registros_ne_2026_lidos':total_ne,
            'menor_data_sintomas_ne':str(menor_sintoma),'registros_recorte':len(resultado),
            'registros_por_ano_sintomas':{str(k):int(v) for k,v in pd.to_datetime(resultado.data_sintomas_original).dt.year.value_counts().items()},
            'arquivo_recorte':destino.relative_to(ROOT).as_posix(),'sha256_recorte':sha256(destino)}
    (META/'complemento_2026.json').write_text(json.dumps(resumo,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in resumo.items() if k!='recurso_original'},ensure_ascii=False,indent=2),flush=True)
    return resumo

if __name__=='__main__':coletar_complemento()
