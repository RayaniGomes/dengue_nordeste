"""Invariantes independentes dos agregados da EDA."""
import json
import pandas as pd
from coletar import ROOT, sha256

def validar():
    out=ROOT/'data/processed/etapa2'
    v=json.loads((ROOT/'data/metadata/validacao_etapa2.json').read_text(encoding='utf-8'))
    e=pd.read_csv(out/'estado_ano_limpo.csv',dtype={'codigo_uf':'string'})
    m=pd.read_csv(out/'municipio_ano_limpo.csv',dtype={'codigo_municipio_6':'string'})
    mes=pd.read_csv(out/'estado_mes_sintomas.csv',dtype={'codigo_uf':'string'})
    a=pd.read_csv(out/'auditoria_limpeza.csv')
    n=pd.read_csv(out/'nordeste_ano.csv')
    assert len(e)==234 and e.groupby('ano').uf.nunique().eq(9).all()
    assert len(mes)==234*12
    assert not e.duplicated(['codigo_uf','ano']).any()
    assert not m.duplicated(['codigo_municipio_6','ano']).any()
    assert not mes.duplicated(['codigo_uf','ano','mes']).any()
    assert int(a.incluidos.sum())==int(e.casos_probaveis_operacionais.sum())==int(mes.casos_probaveis_operacionais.sum())==v['casos_probaveis_operacionais']
    assert int(m.casos_probaveis_operacionais.sum())+int(a.sem_municipio_entre_incluidos.sum())==v['casos_probaveis_operacionais']
    exclusoes=[c for c in a if c.startswith('excluido_')]
    assert (a.registros==a.incluidos+a[exclusoes].sum(axis=1)).all()
    assert e.casos_criterio_estrito.le(e.casos_probaveis_operacionais).all()
    assert m.loc[m.status_cobertura.eq('sem_registro_utilizavel'),'casos_probaveis_operacionais'].isna().all()
    assert e.loc[e.ano.eq(2023),'incidencia_100mil'].isna().all()
    assert n.loc[n.ano.eq(2023),'incidencia_100mil'].isna().all()
    esperado=e.groupby(['codigo_uf','ano']).casos_probaveis_operacionais.sum().sort_index()
    mensal=mes.groupby(['codigo_uf','ano']).casos_probaveis_operacionais.sum().sort_index()
    assert esperado.index.equals(mensal.index)
    assert (esperado.to_numpy()==mensal.to_numpy()).all()
    ok=e.populacao.notna()
    assert ((e.loc[ok,'incidencia_100mil']-e.loc[ok,'casos_probaveis_operacionais']/e.loc[ok,'populacao']*100000).abs()<1e-6).all()
    for ano,d in e.groupby('ano'):
        linha=n.loc[n.ano.eq(ano)].iloc[0]
        assert int(linha.casos_probaveis_operacionais)==int(d.casos_probaveis_operacionais.sum())
        if ano!=2023:
            assert abs(linha.incidencia_100mil-d.casos_probaveis_operacionais.sum()/d.populacao.sum()*100000)<1e-6
    saz=pd.read_csv(out/'sazonalidade_estados.csv')
    assert (saz.groupby('uf').participacao_media_pct.sum().sub(100).abs()<1e-5).all()
    assert saz.anos.eq(24).all()
    for entrada in v['entradas']:
        assert sha256(ROOT/entrada['arquivo'])==entrada['sha256'],entrada['arquivo']
    for ref in json.loads((ROOT/'data/metadata/manifesto_referencias_etapa2.json').read_text(encoding='utf-8'))['recursos']:
        assert sha256(ROOT/ref['arquivo'])==ref['sha256']
    assert sha256(ROOT/'scripts/limpar_analisar.py')==v['script_sha256']
    print('OK: chaves, filtros, reconciliação estadual/municipal/mensal, taxas, ausência de 2023, sazonalidade e hashes.')
    return True

if __name__=='__main__':validar()
