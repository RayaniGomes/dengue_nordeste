"""Executa o primeiro notebook PostgreSQL no kernel do ambiente atual e salva apos sucesso."""
import os
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('JUPYTER_RUNTIME_DIR',str(ROOT/'tmp/jupyter'))
Path(os.environ['JUPYTER_RUNTIME_DIR']).mkdir(parents=True,exist_ok=True)
path=ROOT/'notebooks/01_coleta_integracao.ipynb'
nb=nbformat.read(path,as_version=4)
km=KernelManager(kernel_name='python3')
km.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
NotebookClient(nb,km=km,timeout=900,resources={'metadata':{'path':str(ROOT)}}).execute()
nbformat.validate(nb)
part=path.with_suffix('.ipynb.part')
nbformat.write(nb,part)
part.replace(path)
print('Notebook 01 executado integralmente em kernel real e salvo com saidas agregadas.')