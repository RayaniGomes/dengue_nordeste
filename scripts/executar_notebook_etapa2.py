"""Executa o notebook em kernel real do mesmo Python e salva saídas verificadas."""
import os
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/matplotlib'))
os.environ.setdefault('JUPYTER_RUNTIME_DIR',str(ROOT/'tmp/jupyter'))
Path(os.environ['JUPYTER_RUNTIME_DIR']).mkdir(parents=True,exist_ok=True)
path=ROOT/'notebooks/02_limpeza_eda.ipynb'
nb=nbformat.read(path,as_version=4)
km=KernelManager(kernel_name='python3')
km.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
client=NotebookClient(nb,km=km,timeout=600,resources={'metadata':{'path':str(ROOT)}})
client.execute()
nbformat.validate(nb)
nbformat.write(nb,path)
print('Notebook executado em kernel real, validado e salvo com saídas.')
