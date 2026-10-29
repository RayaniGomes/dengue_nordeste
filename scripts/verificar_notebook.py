"""Executa sequencialmente as células Python (sem servidor Jupyter) e registra stdout."""
import contextlib
import io
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'notebooks/01_coleta_integracao.ipynb'
nb=json.loads(path.read_text(encoding='utf-8'))
contexto={'__name__':'__main__'}
os.chdir(ROOT)
contador=0
for i,cell in enumerate(nb['cells']):
    if cell['cell_type']!='code':continue
    contador+=1
    buffer=io.StringIO()
    with contextlib.redirect_stdout(buffer):
        exec(compile(''.join(cell['source']),f'notebook:celula-{i}','exec'),contexto)
    texto=buffer.getvalue()
    cell['execution_count']=contador
    cell['outputs']=[{'output_type':'stream','name':'stdout','text':texto.splitlines(True)}] if texto else []
    print(f'Célula {contador}: OK',flush=True)
nb['metadata']['verificacao']={'metodo':'Células Python executadas sequencialmente via exec, sem servidor Jupyter',
    'celulas_executadas':contador}
path.write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')
print('Notebook verificado e salvo com saídas reais.')
