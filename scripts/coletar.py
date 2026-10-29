"""Coleta reproduzível de fontes oficiais. Execute a partir de qualquer diretório."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
META = ROOT / 'data' / 'metadata'
PORTAL = 'https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue'
IBGE = 'https://servicodados.ibge.gov.br/api/v3/agregados'
UFS = {'21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB',
       '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA'}

def agora():
    return datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec='seconds')

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def baixar(url, path, origem, extra=None, atualizar=False):
    """Download atômico; cache exige metadados e hash íntegro."""
    path = Path(path)
    sidecar = path.with_name(path.name + '.meta.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not atualizar and path.exists() and sidecar.exists():
        m = json.loads(sidecar.read_text(encoding='utf-8'))
        if m['url'] == url and m['sha256'] == sha256(path):
            return path
    partial = path.with_name(path.name + '.part')
    for tentativa in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'IMD1151-EDA/1.0'})
            with urllib.request.urlopen(req, timeout=45) as r, open(partial, 'wb') as f:
                headers = dict(r.headers)
                for block in iter(lambda: r.read(1024 * 1024), b''):
                    f.write(block)
            if headers.get('Content-Length') and partial.stat().st_size != int(headers['Content-Length']):
                raise ValueError('Download incompleto: tamanho diferente de Content-Length')
            partial.replace(path)
            m = {'origem': origem, 'url': url, 'extraido_em': agora(),
                 'fuso': 'America/Fortaleza (UTC-03:00)',
                 'arquivo': path.relative_to(ROOT).as_posix(),
                 'bytes': path.stat().st_size, 'sha256': sha256(path),
                 'http_last_modified': headers.get('Last-Modified'),
                 'http_etag': headers.get('ETag'), **(extra or {})}
            sidecar.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
            return path
        except Exception:
            if tentativa == 2:
                raise
            time.sleep(2 ** tentativa)

def ler_json(path):
    b = Path(path).read_bytes()
    return json.loads((gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b).decode('utf-8'))

def coletar(inicio=2000, fim=2025, atualizar=False, workers=3):
    if not 2000 <= inicio <= fim <= 2025:
        raise ValueError('O recorte permitido é 2000 a 2025.')
    META.mkdir(parents=True, exist_ok=True)
    catalogo = baixar(PORTAL, RAW/'sinan/catalogo.html', 'Ministério da Saúde/SINAN', atualizar=atualizar)
    html = catalogo.read_text(encoding='utf-8')
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if not match:
        raise ValueError('Formato do catálogo alterado: revisar recursos antes de continuar.')
    pacote = json.loads(match.group(1))['props']['pageProps']
    (META/'catalogo_sinan.json').write_text(json.dumps(pacote,ensure_ascii=False,indent=2),encoding='utf-8')
    tarefas = []
    for ano in range(inicio, fim+1):
        recursos = [r for r in pacote['resources'] if r['format'].upper() == 'CSV'
                    and re.fullmatch(r'Dengue\s*-\s*'+str(ano), r['name'])]
        if len(recursos) != 1:
            raise ValueError(f'Esperado exatamente um CSV para {ano}; encontrados {len(recursos)}')
        r = recursos[0]
        tarefas.append((r['url'], RAW/f'sinan/DENGBR{ano%100:02d}.csv.zip', 'Ministério da Saúde/SINAN',
                        {'ano_arquivo':ano, 'recurso_id':r['id'], 'atualizado_na_fonte':r.get('last_modified')}))
    dic = next(r for r in pacote['resources'] if 'dicion' in r['name'].lower())
    tarefas.append((dic['url'], RAW/'sinan/dicionario_dengue_oficial.pdf', 'Ministério da Saúde/SINAN', {}))

    periodos_path = baixar(f'{IBGE}/6579/periodos', RAW/'ibge/periodos_6579.json', 'IBGE/SIDRA', atualizar=atualizar)
    periodos = {int(p['id']) for p in ler_json(periodos_path)}
    # Total da população: censos do universo, contagem e estimativas anuais.
    fontes = {2000:(202,93,'censo_2000','2[0]|1[0]'),
              2007:(793,93,'contagem_e_estimativas_2007',''),
              2010:(202,93,'censo_2010','2[0]|1[0]'),
              2022:(4714,93,'censo_2022','')}
    for ano in range(inicio, fim+1):
        if ano in periodos:
            tabela, variavel, tipo, classificacao = 6579,9324,'estimativa_anual',''
        elif ano in fontes:
            tabela, variavel, tipo, classificacao = fontes[ano]
        else:
            # Não inventar uma estimativa oficial para anos sem publicação (2023).
            continue
        for nivel in ('N6','N3'):
            locais = f'N6[N3[{",".join(UFS)}]]' if nivel == 'N6' else f'N3[{",".join(UFS)}]'
            url = f'{IBGE}/{tabela}/periodos/{ano}/variaveis/{variavel}?localidades={locais}'
            if classificacao:
                url += '&classificacao=' + classificacao
            tarefas.append((url, RAW/f'ibge/pop_{ano}_{nivel}.json', 'IBGE/SIDRA',
                            {'ano':ano,'nivel':nivel,'tabela':tabela,'variavel':variavel,'tipo_populacao':tipo}))
    for tabela in (6579,202,793,4714):
        tarefas.append((f'{IBGE}/{tabela}/metadados', RAW/f'ibge/metadados_{tabela}.json', 'IBGE/SIDRA', {}))
    erros=[]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures={executor.submit(baixar,*args,atualizar=atualizar):args[1] for args in tarefas}
        for futuro in as_completed(futures):
            path=futures[futuro]
            try:
                futuro.result()
                print('OK',path.relative_to(ROOT),flush=True)
            except Exception as e:
                erros.append({'arquivo':str(path.relative_to(ROOT)),'erro':str(e)})
                print('ERRO',path.name,str(e),flush=True)
    manifesto=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(RAW.rglob('*.meta.json'))]
    (META/'manifesto_extracao.json').write_text(json.dumps(manifesto,ensure_ascii=False,indent=2),encoding='utf-8')
    (META/'status_coleta.json').write_text(json.dumps({'executado_em':agora(),'inicio':inicio,'fim':fim,
        'estados':UFS,'erros':erros,'populacao_sem_publicacao_anual':[a for a in range(inicio,fim+1)
          if a not in periodos and a not in fontes]},ensure_ascii=False,indent=2),encoding='utf-8')
    if erros:
        raise RuntimeError(f'{len(erros)} download(s) falharam. Consulte data/metadata/status_coleta.json e execute novamente.')
    return manifesto

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inicio',type=int,default=2000)
    p.add_argument('--fim',type=int,default=2025)
    p.add_argument('--atualizar',action='store_true')
    p.add_argument('--workers',type=int,default=3)
    a=p.parse_args()
    coletar(a.inicio,a.fim,a.atualizar,a.workers)
