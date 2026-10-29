"""Validação independente dos produtos e, opcionalmente, dos hashes dos originais."""
import argparse
import json
import pandas as pd
from coletar import ROOT, sha256

def validar(hashes=False):
    tipos={'codigo_uf':'string','codigo_municipio_6':'string','codigo_ibge':'string'}
    out=ROOT/'data/processed'
    municipal=pd.read_csv(out/'dengue_municipio_ano.csv',dtype=tipos)
    estadual=pd.read_csv(out/'dengue_estado_ano.csv',dtype=tipos)
    pop=pd.read_csv(out/'populacao_nordeste.csv',dtype=tipos)
    mensal=pd.read_csv(out/'dengue_estado_mes_notificacao.csv',dtype=tipos)
    classes=pd.read_csv(out/'classificacao_estado_ano.csv',dtype=tipos)
    v=json.loads((ROOT/'data/metadata/validacao_integracao.json').read_text(encoding='utf-8'))
    auditorias=pd.DataFrame(v['auditorias'])
    assert not municipal.duplicated(['codigo_municipio_6','ano']).any()
    assert not estadual.duplicated(['codigo_uf','ano']).any()
    assert not pop.duplicated(['nivel','codigo_ibge','ano']).any()
    assert not mensal.duplicated(['codigo_uf','ano','mes_notificacao']).any()
    assert municipal.codigo_municipio_6.str.fullmatch(r'\d{6}').all()
    assert estadual.groupby('ano').codigo_uf.nunique().eq(9).all()
    assert len(estadual)==9*(v['fim']-v['inicio']+1)
    assert pop.populacao.dropna().gt(0).all()
    assert municipal.loc[municipal.status_integracao.eq('integrado'),'populacao'].notna().all()
    assert municipal.loc[municipal.status_integracao.eq('sem_registro_sinan'),'notificacoes'].isna().all()
    for ano,d in estadual.groupby('ano'):
        audit=auditorias.loc[auditorias.ano.eq(ano)].iloc[0]
        total=int(d.notificacoes.sum())
        assert total==int(audit.registros_ne_ano_valido)
        assert int(municipal.loc[municipal.ano.eq(ano),'notificacoes'].sum())+int(audit.ne_ano_valido_sem_municipio_consistente)==total
        assert int(classes.loc[classes.ano.eq(ano),'notificacoes'].sum())==total
        esperado=total-int(audit.data_notificacao_ausente_ou_invalida)-int(audit.data_notificacao_ano_divergente)
        # As datas auditadas abrangem também registros com NU_ANO inválido;
        # a igualdade é garantida apenas quando não há divergência de NU_ANO.
        if not audit.ano_divergente_ou_ausente:
            assert int(mensal.loc[mensal.ano.eq(ano),'notificacoes'].sum())==esperado
    manifesto=json.loads((ROOT/'data/metadata/manifesto_extracao.json').read_text(encoding='utf-8'))
    if hashes:
        for m in manifesto:
            p=ROOT/m['arquivo']
            assert p.stat().st_size==m['bytes'],p
            assert sha256(p)==m['sha256'],p
    print(f'OK: {len(estadual)} estados-ano, {len(municipal)} municípios-ano, {len(manifesto)} recursos rastreados.')
    if hashes:print('Todos os hashes e tamanhos dos originais conferem.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hashes',action='store_true')
    validar(p.parse_args().hashes)
