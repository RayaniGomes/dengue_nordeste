"""Perfil dos campos necessários à harmonização, antes de aplicar filtros."""
from collections import Counter
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
resultados=[]
for ano in range(2000,2026):
    path=ROOT/f'data/interim/sinan_ne_{ano}.csv.gz'
    cols=pd.read_csv(path,nrows=0).columns.tolist()
    campos=[c for c in ['classificacao_original','criterio_original','NDUPLIC','NDUPLIC_N','ID_AGRAVO','ID_DG_NOT','CS_SEXO'] if c in cols]
    frequencias={c:Counter() for c in campos}
    contagens=Counter()
    for d in pd.read_csv(path,dtype='string',keep_default_na=False,chunksize=100000):
        contagens['registros']+=len(d)
        for c in campos:frequencias[c].update(d[c].replace('','AUSENTE').value_counts().to_dict())
        dt=pd.to_datetime(d.data_notificacao_original,format='%Y-%m-%d',errors='coerce')
        ds=pd.to_datetime(d.data_sintomas_original,format='%Y-%m-%d',errors='coerce')
        contagens['notificacao_invalida_ou_fora_arquivo']+=int((dt.isna()|dt.dt.year.ne(ano)).sum())
        contagens['sintomas_invalidos_ou_posteriores']+=int((ds.isna()|ds.gt(dt)).sum())
        contagens['sintomas_ano_anterior']+=int(ds.dt.year.lt(ano).sum())
    resultados.append({'ano':ano,**contagens,'frequencias':{k:dict(v) for k,v in frequencias.items()}})
    print(ano,contagens['registros'],resultados[-1]['frequencias'].get('ID_AGRAVO',{}),flush=True)
(ROOT/'data/metadata/diagnostico_etapa2.json').write_text(json.dumps(resultados,ensure_ascii=False,indent=2),encoding='utf-8')
