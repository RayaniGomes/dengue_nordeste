"""Verifica o primeiro notebook pelo executor PostgreSQL em kernel real."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    runpy.run_path(str(ROOT / 'scripts/executar_notebook_coleta_postgresql.py'), run_name='__main__')
