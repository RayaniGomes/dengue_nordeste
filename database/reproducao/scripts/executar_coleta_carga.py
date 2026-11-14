"""Coleta SINAN/IBGE e carga auditada em esquema PostgreSQL isolado.

python scripts/executar_coleta_carga.py --env CAMINHO --schema coleta_20261113 [--piloto]
A camada public e as análises existentes não são recarregadas.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import psycopg
from psycopg import sql
import pyarrow as pa
import pyarrow.csv as pacsv
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

def agora():
    return datetime.now(ZoneInfo('America/Fortaleza')).isoformat()

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while bloco := f.read(4 << 20):
            h.update(bloco)
    return h.hexdigest()

class Registro:
    def __init__(self, pasta, esquema):
        self.pasta = pasta
        self.path = pasta / 'manifesto.json'
        pasta.mkdir(parents=True, exist_ok=True)
        self.dados = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {
            'iniciado_em': agora(), 'esquema': esquema, 'arquivos': {}, 'status': 'iniciado'}
        if self.dados['esquema'] != esquema:
            raise ValueError('Manifesto pertence a outro esquema.')

    def relativo(self, path):
        return path.relative_to(self.pasta).as_posix()

    def salvar(self):
        self.dados['atualizado_em'] = agora()
        tmp = self.path.with_suffix('.json.part')
        tmp.write_text(json.dumps(self.dados, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def valido(self, path, url):
        anterior = self.dados['arquivos'].get(self.relativo(path))
        return bool(anterior and anterior.get('url') == url and path.is_file()
                    and path.stat().st_size == anterior['bytes'] and sha256(path) == anterior['sha256'])

def baixar(session, url, destino, reg):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if reg.valido(destino, url):
        print('Cache verificado:', reg.relativo(destino), flush=True)
        return
    parcial = destino.with_suffix(destino.suffix + '.part')
    for tentativa in range(1, 6):
        try:
            with session.get(url, stream=True, timeout=(20, 120)) as r:
                r.raise_for_status()
                h = hashlib.sha256()
                n = 0
                with parcial.open('wb') as f:
                    for bloco in r.iter_content(chunk_size=1 << 20):
                        f.write(bloco)
                        h.update(bloco)
                        n += len(bloco)
                meta = {'url': url, 'url_resposta': r.url, 'coletado_em': agora(),
                        'bytes': n, 'sha256': h.hexdigest(), 'http_status': r.status_code,
                        'last_modified': r.headers.get('Last-Modified'), 'etag': r.headers.get('ETag')}
            parcial.replace(destino)
            reg.dados['arquivos'][reg.relativo(destino)] = meta
            reg.salvar()
            print(f'Baixado: {reg.relativo(destino)} ({n / 1e6:.1f} MB)', flush=True)
            return
        except (requests.RequestException, OSError) as exc:
            print(f'Tentativa {tentativa}/5: {type(exc).__name__} em {url}', flush=True)
            if tentativa == 5:
                raise
            time.sleep(min(2 ** tentativa, 20))

def linhas_csv(path):
    """Conta registros com parser independente de COPY, respeitando aspas e quebras."""
    with path.open(encoding='utf-8-sig', newline='') as f:
        cab = next(csv.reader(f))
    leitor = pacsv.open_csv(str(path),
        read_options=pacsv.ReadOptions(column_names=cab, skip_rows=1, block_size=8 << 20),
        parse_options=pacsv.ParseOptions(newlines_in_values=True),
        convert_options=pacsv.ConvertOptions(include_columns=[cab[0]],
                                             column_types={cab[0]: pa.string()}, check_utf8=False))
    try:
        return sum(lote.num_rows for lote in leitor)
    finally:
        leitor.close()

def sinan_ano(session, ano, pasta, reg, modulo):
    url = modulo.url_ano(ano)
    destino_zip = pasta / f'ano={ano}' / f'DENGBR{ano % 100:02d}.csv.zip'
    destino_csv = destino_zip.with_suffix('')
    print(f'SINAN {ano}: coleta e conferência', flush=True)
    baixar(session, url, destino_zip, reg)
    meta_zip = reg.dados['arquivos'][reg.relativo(destino_zip)]
    meta_csv = reg.dados['arquivos'].get(reg.relativo(destino_csv), {})
    valido = reg.valido(destino_csv, url) and meta_csv.get('zip_sha256') == meta_zip['sha256']
    if not valido:
        parcial = destino_csv.with_suffix('.csv.part')
        h = hashlib.sha256()
        with zipfile.ZipFile(destino_zip) as z:
            membros = [m for m in z.namelist() if m.lower().endswith('.csv')]
            if len(membros) != 1:
                raise ValueError(f'Esperado um CSV no ZIP de {ano}.')
            with z.open(membros[0]) as origem, parcial.open('wb') as destino:
                while bloco := origem.read(4 << 20):
                    destino.write(bloco)
                    h.update(bloco)
        parcial.replace(destino_csv)
        meta_csv = {'url': url, 'coletado_em': meta_zip['coletado_em'],
                    'membro_zip': membros[0], 'zip_sha256': meta_zip['sha256'],
                    'sha256': h.hexdigest(), 'bytes': destino_csv.stat().st_size}
        reg.dados['arquivos'][reg.relativo(destino_csv)] = meta_csv
        reg.salvar()
    if 'linhas_csv' not in meta_csv:
        meta_csv['linhas_csv'] = linhas_csv(destino_csv)
        reg.salvar()
    print(f'SINAN {ano}: {meta_csv["linhas_csv"]:,} registros no CSV', flush=True)

def ibge_coletar(session, pasta, reg, coleta, carga, ufs, piloto=False):
    frames = []
    for tab in coleta.TABELAS[:1] if piloto else coleta.TABELAS:
        for sigla, uf in list(ufs.items())[:1] if piloto else ufs.items():
            print(f'IBGE/SIDRA: {tab["nome"]}, {sigla}', flush=True)
            url = coleta.montar_url(tab, [uf])
            path = pasta / 'respostas_sidra' / f'{tab["nome"]}_{sigla}.json'
            baixar(session, url, path, reg)
            payload = json.loads(path.read_bytes())
            frame = coleta.parsear_sidra(payload, tab['nome'], tab['prioridade'])
            frames.append(frame)
    if piloto:
        return None
    pop = coleta.consolidar(frames)
    path = pasta / 'populacao_municipios_ne.csv'
    pop.to_csv(path, index=False)
    reg.dados['arquivos'][reg.relativo(path)] = {
        'url': 'derivado_das_respostas_sidra_preservadas', 'coletado_em': agora(),
        'bytes': path.stat().st_size, 'sha256': sha256(path), 'linhas_csv': len(pop)}
    estados_path = pasta / 'estados.json'
    municipios_path = pasta / 'municipios.json'
    baixar(session, carga.LOCALIDADES + '/estados', estados_path, reg)
    baixar(session, carga.LOCALIDADES + '/municipios', municipios_path, reg)
    estados = json.loads(estados_path.read_bytes())
    municipios = json.loads(municipios_path.read_bytes())
    if not isinstance(estados, list) or not isinstance(municipios, list):
        raise ValueError('Resposta de localidades deve ser uma lista.')
    df_estado = pd.DataFrame([{'uf_cod': e['id'], 'sigla': e['sigla'], 'nome': e['nome'],
        'regiao_sigla': e['regiao']['sigla'], 'regiao': e['regiao']['nome']} for e in estados]).sort_values('uf_cod')
    df_municipio = pd.DataFrame([carga.linha_municipio(m) for m in municipios]).sort_values('cod_mun7')
    reg.salvar()
    return pop, df_estado, df_municipio

def public_resumo(banco):
    with psycopg.connect(**banco, connect_timeout=15) as con:
        con.read_only = True
        existe = con.execute("SELECT to_regclass('public.notificacao_dengue_ne')").fetchone()[0]
        if not existe:
            return None
        return list(con.execute("""SELECT count(*), count(*) FILTER
            (WHERE caso_provavel AND ano BETWEEN 2000 AND 2025) FROM public.notificacao_dengue_ne""").fetchone())

def preparar_esquema(banco, esquema):
    with psycopg.connect(**banco, connect_timeout=15) as con:
        with con.transaction():
            existe = con.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s', (esquema,)).fetchone()
            if existe:
                marcador = con.execute('SELECT to_regclass(%s)', (esquema + '._execucao_coleta',)).fetchone()[0]
                if not marcador:
                    raise RuntimeError('Esquema preexistente não pertence a esta rotina; nada foi substituído.')
                metodo = con.execute(sql.SQL('SELECT metodo FROM {}._execucao_coleta').format(sql.Identifier(esquema))).fetchone()
                if metodo != ('coleta_carga_v1',):
                    raise RuntimeError('Marcador de execução incompatível.')
            else:
                con.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(esquema)))
                con.execute(sql.SQL('CREATE TABLE {}._execucao_coleta (metodo text PRIMARY KEY, criado_em timestamptz DEFAULT now())').format(sql.Identifier(esquema)))
                con.execute(sql.SQL('INSERT INTO {}._execucao_coleta (metodo) VALUES (%s)').format(sql.Identifier(esquema)), ('coleta_carga_v1',))

def validar(banco, esquema, reg, anos, resumo_antes, pop):
    with psycopg.connect(**banco, connect_timeout=15) as con:
        con.read_only = True
        if con.execute('SELECT current_schema()').fetchone()[0] != esquema:
            raise RuntimeError('Search path não aponta para o esquema isolado.')
        contagens = dict(con.execute('SELECT ano_arquivo,count(*) FROM sinan_dengue GROUP BY 1 ORDER BY 1').fetchall())
        print('Contagem real do SINAN concluida; conferindo CSVs e IBGE.', flush=True)
        controles = {ano: (linhas, nulos) for ano, linhas, nulos in con.execute('SELECT ano_arquivo,linhas,bytes_nulos FROM sinan_dengue_carga ORDER BY 1')}
        por_ano = []
        for ano in anos:
            chave = f'dengue_csv/ano={ano}/DENGBR{ano % 100:02d}.csv'
            esperado = reg.dados['arquivos'][chave]['linhas_csv']
            if contagens.get(ano) != esperado or controles[ano][0] != esperado:
                raise RuntimeError(f'Contagem divergente no ano {ano}.')
            por_ano.append({'ano': ano, 'linhas_csv': esperado, 'linhas_postgresql': contagens[ano], 'bytes_nulos_removidos': controles[ano][1]})
        n_pop = con.execute('SELECT count(*) FROM populacao_ne').fetchone()[0]
        if n_pop != len(pop):
            raise RuntimeError('Contagem de população não confere com o CSV.')
        sem_par = con.execute('SELECT count(*) FROM populacao_ne p LEFT JOIN municipio m USING (cod_mun7) WHERE m.cod_mun7 IS NULL').fetchone()[0]
        if sem_par:
            raise RuntimeError('Há municípios da população sem cadastro IBGE.')
        ibge = {'populacao_ne': n_pop, 'estado': con.execute('SELECT count(*) FROM estado').fetchone()[0],
                'municipio': con.execute('SELECT count(*) FROM municipio').fetchone()[0],
                'populacao_municipio_ano': con.execute('SELECT count(*) FROM populacao_municipio_ano').fetchone()[0],
                'sem_correspondencia_municipal': sem_par}
        versao = con.execute('SHOW server_version').fetchone()[0]
    print('Contagens conciliadas; conferindo resumo da camada public.', flush=True)
    depois = public_resumo(banco)
    if depois != resumo_antes:
        raise RuntimeError('O resumo de public mudou durante a execução; conferir atividade concorrente.')
    return {'concluido_em': agora(), 'banco': banco['dbname'], 'esquema': esquema, 'postgresql': versao,
            'fontes': ['SINAN/OpenDataSUS (CSV anual)', 'IBGE/SIDRA', 'IBGE/Localidades'],
            'periodo_coletado': [min(anos), max(anos)], 'periodo_analitico_do_projeto': [2000, 2025],
            'sinan_registros': sum(contagens.values()), 'sinan_por_ano': por_ano, 'ibge': ibge,
            'public_resumo_antes': resumo_antes, 'public_resumo_depois': depois, 'public_preservado': True,
            'validacao': 'CSV contado com parser independente e conciliado com PostgreSQL e tabela de controle',
            'manifesto_bruto': reg.path.relative_to(ROOT).as_posix()}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--env', type=Path, required=True)
    ap.add_argument('--schema', default='coleta_' + datetime.now(ZoneInfo('America/Fortaleza')).strftime('%Y%m%d'))
    ap.add_argument('--piloto', action='store_true')
    a = ap.parse_args()
    if not re.fullmatch(r'coleta_[a-z0-9_]{1,55}', a.schema):
        ap.error('Use um esquema exclusivo com prefixo coleta_; public não é permitido.')
    if not a.env.is_file():
        ap.error('Arquivo de configuração privada não encontrado.')
    load_dotenv(a.env, override=True)
    sys.path.insert(0, str(ROOT / 'src'))
    from config import BANCO, ANO_INICIO, ANO_FIM_COLETA, UFS_NORDESTE
    from coleta.dengue import coleta_dengue_csv as csv_sinan
    from coleta.ibge import coleta_ibge
    from carga.dengue import carga_dengue
    from carga.ibge import carga_ibge
    pasta = ROOT / 'data' / 'raw' / a.schema
    reg = Registro(pasta, a.schema)
    resumo = public_resumo(BANCO)
    reg.dados['public_resumo_antes'] = resumo
    reg.dados['status'] = 'piloto' if a.piloto else 'coletando'
    reg.salvar()
    with requests.Session() as session:
        session.headers.update({'User-Agent': 'dengue_nordeste-coleta/1.0'})
        try:
            sinan_ano(session, ANO_FIM_COLETA, pasta / 'dengue_csv', reg, csv_sinan)
            if a.piloto:
                ibge_coletar(session, pasta / 'ibge', reg, coleta_ibge, carga_ibge, UFS_NORDESTE, piloto=True)
                reg.dados['status'] = 'piloto_aprovado'
                reg.salvar()
                print('Piloto aprovado; nenhuma tabela foi carregada.', flush=True)
                return
            for ano in range(ANO_INICIO, ANO_FIM_COLETA):
                sinan_ano(session, ano, pasta / 'dengue_csv', reg, csv_sinan)
            pop, estados, municipios = ibge_coletar(session, pasta / 'ibge', reg, coleta_ibge, carga_ibge, UFS_NORDESTE)
            preparar_esquema(BANCO, a.schema)
            os.environ['PGOPTIONS'] = f'-c search_path={a.schema},pg_catalog -c default_statistics_target=10'
            with psycopg.connect(**BANCO, connect_timeout=15) as con:
                if con.execute('SELECT current_schema()').fetchone()[0] != a.schema:
                    raise RuntimeError('Conexão não está isolada no esquema da coleta.')
            reg.dados['status'] = 'carregando'
            reg.salvar()
            csv_sinan.DESTINO = pasta / 'dengue_csv'
            print('Carga SINAN no esquema', a.schema, flush=True)
            carga_dengue.carregar(range(ANO_INICIO, ANO_FIM_COLETA + 1))
            # Um ANALYZE interrompido nao desfaz o COPY ja confirmado. Completa so o que falta.
            with psycopg.connect(**BANCO, autocommit=True) as con:
                sem_estatisticas = con.execute(
                    "SELECT relname FROM pg_stat_all_tables WHERE schemaname=%s "
                    "AND relname ~ '^sinan_dengue_[0-9]{4}$' AND last_analyze IS NULL",
                    (a.schema,)).fetchall()
                for (tabela,) in sem_estatisticas:
                    con.execute(sql.SQL('ANALYZE {}.{}').format(sql.Identifier(a.schema), sql.Identifier(tabela)))
            carga_ibge.ARQUIVO_POPULACAO = pasta / 'ibge' / 'populacao_municipios_ne.csv'
            carga_ibge.baixar_localidades = lambda: (estados, municipios)
            print('Carga IBGE no esquema', a.schema, flush=True)
            carga_ibge.carregar()
            print('Carga IBGE concluida; iniciando contagem real das tabelas SINAN.', flush=True)
            resultado = validar(BANCO, a.schema, reg, range(ANO_INICIO, ANO_FIM_COLETA + 1), resumo, pop)
            saida = ROOT / 'reports' / 'validation' / (a.schema + '_carga.json')
            saida.parent.mkdir(parents=True, exist_ok=True)
            saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
            reg.dados['status'] = 'concluido'
            reg.dados['resultado'] = resultado
            reg.dados.pop('tipo_erro', None)
            reg.salvar()
            manifesto_publico = saida.with_name(a.schema + '_manifesto.json')
            manifesto_publico.write_text(reg.path.read_text(encoding='utf-8'), encoding='utf-8')
            print(json.dumps(resultado, ensure_ascii=False, indent=2), flush=True)
        except Exception as exc:
            reg.dados['status'] = 'falhou'
            reg.dados['tipo_erro'] = type(exc).__name__
            reg.salvar()
            raise

if __name__ == '__main__':
    main()