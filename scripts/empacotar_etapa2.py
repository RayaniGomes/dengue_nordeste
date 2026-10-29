"""Pacote portátil: código, tabelas agregadas, notebook e relatório, sem microdados."""
from pathlib import Path
import zipfile
from coletar import ROOT

def empacotar():
    destino=ROOT.parent/'dengue_nordeste_etapa2.zip'
    ignorados={'.git','.venv','__pycache__','.ipynb_checkpoints','tmp','raw','interim'}
    with zipfile.ZipFile(destino,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file():continue
            rel=p.relative_to(ROOT)
            if ignorados.intersection(rel.parts) or p.suffix=='.part':continue
            z.write(p,Path(ROOT.name)/rel)
    with zipfile.ZipFile(destino) as z:
        assert z.testzip() is None
    print(destino)
    print(f'{destino.stat().st_size/1024**2:.2f} MiB')

if __name__=='__main__':empacotar()
