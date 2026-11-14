"""Prepara os insumos agregados versionaveis da CP1 a partir da extracao validada."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from integrar_postgresql import METRICAS, conferir_arquivos, hash_arquivo

ROOT=Path(__file__).resolve().parents[1]


def preparar(saida):
    root=ROOT
    candidatos=[]
    for p in (root/'data/metadata/postgresql/relatorio_2000_2025').glob('*/integracoes/*.json'):
        v=json.loads(p.read_text(encoding='utf-8'))
        entrada=root/v['manifesto_entrada']
        if v['status']=='concluido' and entrada.is_file():
            m=json.loads(entrada.read_text(encoding='utf-8'))
            if m.get('perfil','individual')=='individual': candidatos.append((v['concluido_em'],p,v,entrada))
    if not candidatos: raise FileNotFoundError('Execute a extracao e a integracao individuais antes de preparar outro snapshot CP1.')
    _,validacao_path,v,entrada=max(candidatos,key=lambda x:x[0])
    m,_=conferir_arquivos(root,entrada)
    origem_painel=root/v['arquivos']['painel_municipio_ano']['arquivo']
    if hash_arquivo(origem_painel)!=v['arquivos']['painel_municipio_ano']['sha256']: raise ValueError('Painel de origem divergente.')
    painel=pd.read_csv(origem_painel,dtype={'cod_mun7':'string'})
    contagens=painel.loc[painel.notificacoes.gt(0),['cod_mun7','ano',*METRICAS]].sort_values(['cod_mun7','ano'])
    if contagens.duplicated(['cod_mun7','ano']).any(): raise ValueError('Chave municipal duplicada.')
    totais={k:int(contagens[k].sum()) for k in METRICAS}
    if totais!=m['totais']: raise ValueError('Totais do painel divergentes da extracao PostgreSQL.')
    if saida.exists(): raise FileExistsError('Saida existente preservada; escolha --saida diferente para um novo snapshot.')
    saida.mkdir(parents=True)
    dados=saida/'insumos'; dados.mkdir()
    arquivos={}
    def registrar(nome,path,n,origem):
        arquivos[nome]={'arquivo':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':hash_arquivo(path),
                       'registros_csv':int(n),'registros_origem':int(n), 'origem_e_transformacao':origem}
    p=dados/'notificacoes_municipio_ano.csv'; contagens.to_csv(p,index=False)
    registrar('notificacoes_municipio_ano',p,len(contagens),
              'SINAN: agregacao por residencia e ano da tabela public.notificacao_dengue_ne; contagens conciliadas com o snapshot PostgreSQL, nao sao registros individuais.')
    for nome in ['populacao_municipio_ano','populacao_ne','municipio_ne','estado_ne']:
        origem=root/m['arquivos'][nome]['arquivo']; p=dados/(nome+'.csv.gz'); shutil.copy2(origem,p)
        n=len(pd.read_csv(p))
        if n!=m['arquivos'][nome]['registros_csv']: raise ValueError('Contagem IBGE divergente.')
        registrar(nome,p,n,'IBGE/SIDRA ou Localidades: copia da tabela exportada do mesmo snapshot PostgreSQL; valores municipais publicos, sem registros individuais de pessoas.')
    resumo=saida/'resumo_anual.csv'; shutil.copy2(root/m['resumo_anual']['arquivo'],resumo)
    anual=contagens.groupby('ano',as_index=False)[METRICAS].sum().sort_values('ano').reset_index(drop=True)
    esperado=pd.read_csv(resumo).sort_values('ano').reset_index(drop=True)
    pd.testing.assert_frame_equal(anual,esperado,check_dtype=False)
    manifesto={'status':'concluido','perfil':'portatil_agregado','execucao':'portatil_20261113',
        'iniciado_em':m['iniciado_em'],'concluido_em':datetime.now(ZoneInfo('America/Fortaleza')).isoformat(),
        'origem':'Pacote agregado versionado, derivado da extracao PostgreSQL validada',
        'banco':m['banco'],'schema':'public','periodo':[2000,2025],'somente_leitura':True,
        'snapshot':m['snapshot'],'transacao_iniciada_em':m['transacao_iniciada_em'],
        'extracao_entrada':entrada.relative_to(root).as_posix(),'sha256_extracao_entrada':hash_arquivo(entrada),
        'integracao_entrada':validacao_path.relative_to(root).as_posix(),'sha256_integracao_entrada':hash_arquivo(validacao_path),
        'arquivos':arquivos,'totais':totais,'casos_provaveis_sem_populacao':v['casos_provaveis_sem_populacao'],
        'resumo_anual':{'arquivo':resumo.relative_to(root).as_posix(),'registros':26,'sha256':hash_arquivo(resumo)},
        'dicionario':{'arquivo':'docs/dicionario_dados.json','sha256':hash_arquivo(root/'docs/dicionario_dados.json')},
        'dicionario_csv':{'arquivo':'docs/dicionario_dados.csv','sha256':hash_arquivo(root/'docs/dicionario_dados.csv')},
        'fontes':[{'nome':'SINAN/OpenDataSUS','url':'https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR{aa}.csv.zip','papel':'Notificacoes; tabela tratada agregada por municipio de residencia e ano.'},
                  {'nome':'IBGE/SIDRA e Localidades','url':'https://apisidra.ibge.gov.br/values','cadastro':'https://servicodados.ibge.gov.br/api/v1/localidades','papel':'Populacao municipal e cadastro geografico; censos 2000/2010/2022 e estimativas 6579.'}],
        'registros_individuais':False,
        'limites':['Pacote destinado a coleta/integracao CP1 e incidencia anual; nao substitui os dados individuais para idade, sexo ou sazonalidade.',
                   'Os arquivos congelam um snapshot; nova coleta nas fontes oficiais pode conter revisoes.',
                   'Nenhuma regra epidemiologica ou decisao pendente foi alterada.']}
    (saida/'manifesto.json').write_text(json.dumps(manifesto,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'pacote':saida.relative_to(root).as_posix(),'totais':totais,
                      'arquivos':{k:v['registros_csv'] for k,v in arquivos.items()}},ensure_ascii=False,indent=2))
    return manifesto


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--saida',type=Path,default=ROOT/'data/processed/insumos_portateis')
    a=ap.parse_args(); saida=a.saida.resolve()
    if not saida.is_relative_to(ROOT/'data/processed'): ap.error('A saida deve ficar dentro de data/processed.')
    preparar(saida)