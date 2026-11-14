"""Executa a CP1 em uma copia isolada sem dados individuais, .env ou configuracao PostgreSQL."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
import nbformat

ROOT=Path(__file__).resolve().parents[1]


def verificar(ambiente_limpo=False):
    tmp=ROOT/'tmp'; tmp.mkdir(exist_ok=True)
    referencia_path=ROOT/'database/validacao/notebook01_execucao.json'
    ref=json.loads(referencia_path.read_text(encoding='utf-8'))
    anterior=json.loads((ROOT/ref['manifesto_integracao']).read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='portatil_sem_banco_',dir=tmp) as pasta:
        isolado=Path(pasta).resolve()
        if not isolado.is_relative_to(tmp.resolve()): raise ValueError('Diretorio temporario fora dos limites.')
        for rel in ['scripts','notebooks','docs','data/processed/insumos_portateis']:
            alvo=isolado/rel; alvo.mkdir(parents=True,exist_ok=True)
        for nome in ['integrar_postgresql.py','extrair_postgresql.py','executar_notebook_coleta_postgresql.py']:
            shutil.copy2(ROOT/'scripts'/nome,isolado/'scripts'/nome)
        shutil.copy2(ROOT/'requirements.txt',isolado/'requirements.txt')
        shutil.copy2(ROOT/'notebooks/01_coleta_integracao.ipynb',isolado/'notebooks/01_coleta_integracao.ipynb')
        for nome in ['dicionario_dados.csv','dicionario_dados.json','dicionario_dados.md']:
            shutil.copy2(ROOT/'docs'/nome,isolado/'docs'/nome)
        shutil.copytree(ROOT/'data/processed/insumos_portateis',isolado/'data/processed/insumos_portateis',dirs_exist_ok=True)
        # Um clone tambem contem manifestos antigos, mas nao os arquivos raw ignorados.
        for p in (ROOT/'data/metadata/postgresql/relatorio_2000_2025').glob('*/manifesto.json'):
            alvo=isolado/p.relative_to(ROOT); alvo.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,alvo)
        assert not (isolado/'data/raw').exists() and not list(isolado.rglob('.env'))
        ambiente=dict(os.environ)
        for chave in list(ambiente):
            if chave.startswith('PG') or chave in ('DENGUE_ENV','DENGUE_MODO_DADOS','JUPYTER_RUNTIME_DIR'):
                ambiente.pop(chave,None)
        ambiente['DENGUE_MODO_DADOS']='auto'
        ambiente['PYTHONIOENCODING']='utf-8'
        python_exec=sys.executable
        if ambiente_limpo:
            print('Criando ambiente virtual temporario e instalando requirements.txt...',flush=True)
            env_dir=isolado/'.venv'
            subprocess.run([sys.executable,'-m','venv',str(env_dir)],check=True,capture_output=True)
            python_exec=str(env_dir/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
            instalado=subprocess.run([python_exec,'-m','pip','install','-r',str(isolado/'requirements.txt')],
                                     env=ambiente,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=900)
            if instalado.returncode:
                raise RuntimeError('Instalacao isolada de requirements.txt falhou; nenhuma verificacao aprovada foi registrada.')
            print('Dependencias instaladas no ambiente novo; executando notebook sem banco...',flush=True)
        r=subprocess.run([python_exec,'-B',str(isolado/'scripts/executar_notebook_coleta_postgresql.py')],
                         cwd=isolado,env=ambiente,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=900)
        if r.returncode:
            raise RuntimeError('Notebook isolado falhou:\n'+r.stdout+'\n'+r.stderr)
        nb=nbformat.read(isolado/'notebooks/01_coleta_integracao.ipynb',as_version=4); nbformat.validate(nb)
        celulas=[c for c in nb.cells if c.cell_type=='code']
        assert [c.execution_count for c in celulas]==list(range(1,len(celulas)+1))
        assert not any(o.output_type=='error' for c in celulas for o in c.outputs)
        textos='\n'.join(o.get('text','') for c in celulas for o in c.outputs if o.output_type=='stream')
        assert 'pacote CP1 portatil' in textos
        candidatos=list((isolado/'data/metadata/postgresql/relatorio_2000_2025/portatil_20261113/integracoes').glob('*.json'))
        assert len(candidatos)==1
        v=json.loads(candidatos[0].read_text(encoding='utf-8'))
        assert v['status']=='concluido' and v['perfil_entrada']=='portatil_agregado'
        assert v['totais']==anterior['totais']
        comparacoes={k:a['sha256']==anterior['arquivos'][k]['sha256'] for k,a in v['arquivos'].items()}
        assert all(comparacoes.values()),comparacoes
        resultado={'status':'aprovado','verificado_em':datetime.now(ZoneInfo('America/Fortaleza')).isoformat(),
            'modo':'auto, com selecao do pacote portatil','kernel_real':True,'celulas_executadas':len(celulas),'erros':0,
            'arquivos_individuais_presentes':False,'env_privado_presente':False,'configuracao_postgresql_no_ambiente':False,
            'manifestos_antigos_sem_raw':'presentes para verificar fallback real de um clone',
            'totais':v['totais'],'paineis_identicos_por_sha256':comparacoes,
            'referencia':ref['manifesto_integracao'],
            'ambiente_python_novo':ambiente_limpo,'requirements_instalado_do_zero':ambiente_limpo,
            'limite':('Python base ja instalado; dependencias instaladas em venv novo a partir de requirements.txt.' if ambiente_limpo else 'Ambiente Python reutilizado; instalacao de dependencias do zero nao realizada nesta verificacao.')}
    saida=ROOT/'database/validacao/reproducao_sem_banco.json'
    saida.write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(resultado,ensure_ascii=False,indent=2),flush=True)
    return resultado


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ambiente-limpo',action='store_true')
    a=ap.parse_args(); verificar(a.ambiente_limpo)