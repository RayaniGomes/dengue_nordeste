"""Ponto de entrada da Etapa 2. Reutiliza produtos ou reconstrói com --reprocessar."""
import argparse
from coletar import ROOT

def executar_etapa(reprocessar=False,documentar=True):
    tabela=ROOT/'data/processed/etapa2/municipio_ano_limpo.csv'
    if reprocessar or not tabela.exists():
        if not all((ROOT/f'data/interim/sinan_ne_{a}.csv.gz').exists() for a in range(2000,2026)):
            from coletar import coletar
            from integrar import integrar
            coletar(); integrar()
        from coletar_referencias_etapa2 import coletar_referencias
        from coletar_complemento_2026 import coletar_complemento
        coletar_referencias(); coletar_complemento()
        from limpar_analisar import executar
        executar()
    else:
        print('Usando tabelas da Etapa 2 já produzidas. --reprocessar refaz a limpeza.')
    if reprocessar or not (ROOT/'outputs/etapa2/figuras.json').exists():
        from graficos_etapa2 import gerar
        gerar()
    if documentar:
        from documentar_etapa2 import gerar
        gerar()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reprocessar',action='store_true')
    executar_etapa(p.parse_args().reprocessar)
