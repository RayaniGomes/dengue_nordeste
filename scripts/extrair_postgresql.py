"""Extrai a base tratada do relatorio diretamente do PostgreSQL, em modo somente leitura."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import psycopg
from psycopg import IsolationLevel, sql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
UFS = tuple(range(21, 30))
METRICAS = ('notificacoes', 'casos_provaveis', 'casos_confirmados', 'possiveis_duplicatas',
            'sem_idade', 'sem_sexo', 'sem_mes_sintomas')


def agora():
    return datetime.now(ZoneInfo('America/Fortaleza')).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while bloco := f.read(4 << 20):
            h.update(bloco)
    return h.hexdigest()


def contar_csv(path, notificacoes=False):
    """Le o CSV exportado com parser independente do COPY e reconta as metricas."""
    anos = defaultdict(lambda: [0] * len(METRICAS))
    total = 0
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            total += 1
            if notificacoes:
                ano = int(linha['ano'])
                if not 2000 <= ano <= 2025:
                    raise ValueError('Ano fora do periodo selecionado.')
                valores = (1, linha['caso_provavel'] == 't', linha['caso_confirmado'] == 't',
                           linha['possivel_duplicata'] == 't', linha['idade_anos'] == '',
                           linha['sexo'].strip() == '', linha['mes_sintomas'] == '')
                for i, valor in enumerate(valores):
                    anos[ano][i] += int(valor)
    return total, dict(anos)


def exportar(con, nome, consulta, destino, esperado):
    """Exporta via COPY, verifica contagem por releitura e finaliza atomicamente."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        raise FileExistsError('Arquivo existente preservado: ' + str(destino))
    parcial = destino.with_suffix(destino.suffix + '.part')
    print('Extraindo:', nome, flush=True)
    with parcial.open('wb') as bruto, gzip.GzipFile(filename='', mode='wb', fileobj=bruto,
                                                 compresslevel=3, mtime=0) as gz:
        comando = sql.SQL('COPY ({}) TO STDOUT (FORMAT CSV, HEADER TRUE, ENCODING \'UTF8\')').format(sql.SQL(consulta))
        with con.cursor() as cur, cur.copy(comando) as cp:
            for bloco in cp:
                gz.write(bloco)
    total, por_ano = contar_csv(parcial, nome == 'notificacao_dengue_ne')
    if total != esperado:
        raise RuntimeError(f'{nome}: {total} registros no CSV; esperado {esperado} no banco.')
    parcial.replace(destino)
    print(f'Conferido: {nome}: {total:,} registros', flush=True)
    return {'arquivo': destino.relative_to(ROOT).as_posix(), 'consulta_sql': consulta,
            'registros_csv': total, 'registros_postgresql': esperado,
            'bytes': destino.stat().st_size, 'sha256': sha256(destino)}, por_ano


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--env', required=True, type=Path)
    a = ap.parse_args()
    if not a.env.is_file():
        ap.error('Arquivo de configuracao privada nao encontrado.')
    load_dotenv(a.env, override=True)
    banco = {k: os.environ[v] for k, v in [('host', 'PGHOST'), ('port', 'PGPORT'),
             ('dbname', 'PGDATABASE'), ('user', 'PGUSER'), ('password', 'PGPASSWORD')]}
    execucao = datetime.now(ZoneInfo('America/Fortaleza')).strftime('%Y%m%d_%H%M%S')
    nome = 'relatorio_2000_2025'
    pasta = ROOT / 'data' / 'raw' / 'postgresql' / nome / execucao
    agregados = ROOT / 'data' / 'processed' / 'postgresql' / nome / execucao
    metadados = ROOT / 'data' / 'metadata' / 'postgresql' / nome / execucao
    for p in (pasta, agregados, metadados):
        p.mkdir(parents=True, exist_ok=False)
    manifesto = {'status': 'em_execucao', 'iniciado_em': agora(), 'origem': 'PostgreSQL',
                 'banco': banco['dbname'], 'schema': 'public', 'periodo': [2000, 2025],
                 'recorte': 'residentes do Nordeste, conforme tabela tratada usada no relatorio',
                 'somente_leitura': True, 'arquivos': {}, 'execucao': execucao}
    caminho_manifesto = metadados / 'manifesto.json'

    def salvar():
        tmp = caminho_manifesto.with_suffix('.json.part')
        tmp.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(caminho_manifesto)

    salvar()
    try:
        with psycopg.connect(**banco, connect_timeout=15,
                             options='-c default_transaction_read_only=on -c search_path=pg_catalog') as con:
            con.isolation_level = IsolationLevel.REPEATABLE_READ
            con.read_only = True
            if con.execute('SHOW transaction_read_only').fetchone()[0] != 'on':
                raise RuntimeError('Conexao sem protecao de somente leitura.')
            manifesto['snapshot'] = str(con.execute('SELECT pg_current_snapshot()').fetchone()[0])
            manifesto['transacao_iniciada_em'] = con.execute('SELECT now()').fetchone()[0].isoformat()
            manifesto['postgresql'] = con.execute('SHOW server_version').fetchone()[0]
            print('Consultando totais anuais reais do PostgreSQL...', flush=True)
            anual_sql = """SELECT ano, count(*), count(*) FILTER (WHERE caso_provavel),
                count(*) FILTER (WHERE caso_confirmado), count(*) FILTER (WHERE possivel_duplicata),
                count(*) FILTER (WHERE idade_anos IS NULL),
                count(*) FILTER (WHERE NULLIF(btrim(sexo), '') IS NULL),
                count(*) FILTER (WHERE mes_sintomas IS NULL)
                FROM public.notificacao_dengue_ne WHERE ano BETWEEN 2000 AND 2025
                GROUP BY ano ORDER BY ano"""
            anual = {int(r[0]): list(r[1:]) for r in con.execute(anual_sql)}
            if not anual:
                raise RuntimeError('Tabela tratada vazia no periodo; extracao interrompida.')
            esperado = sum(r[0] for r in anual.values())
            if set(anual) != set(range(2000, 2026)):
                raise RuntimeError('Cobertura anual da tabela tratada incompleta.')
            consultas = {
                'notificacao_dengue_ne': ('SELECT * FROM public.notificacao_dengue_ne WHERE ano BETWEEN 2000 AND 2025 ORDER BY id', esperado),
                'populacao_municipio_ano': ("SELECT p.* FROM public.populacao_municipio_ano p JOIN public.municipio m USING (cod_mun7) WHERE p.ano BETWEEN 2000 AND 2025 AND m.uf_cod BETWEEN 21 AND 29 ORDER BY p.cod_mun7,p.ano", None),
                'populacao_ne': ('SELECT * FROM public.populacao_ne WHERE ano BETWEEN 2000 AND 2025 AND uf_cod BETWEEN 21 AND 29 ORDER BY cod_mun7,ano', None),
                'municipio_ne': ('SELECT * FROM public.municipio WHERE uf_cod BETWEEN 21 AND 29 ORDER BY cod_mun7', None),
                'estado_ne': ('SELECT * FROM public.estado WHERE uf_cod BETWEEN 21 AND 29 ORDER BY uf_cod', None),
            }
            for tabela, (consulta, n) in consultas.items():
                if n is None:
                    n = con.execute(sql.SQL('SELECT count(*) FROM ({}) AS q').format(sql.SQL(consulta))).fetchone()[0]
                meta, recontado = exportar(con, tabela, consulta, pasta / (tabela + '.csv.gz'), n)
                if tabela == 'notificacao_dengue_ne' and recontado != anual:
                    raise RuntimeError('Metricas anuais do CSV divergentes do PostgreSQL.')
                manifesto['arquivos'][tabela] = meta
                salvar()
            faltantes = con.execute("""SELECT count(*) FROM public.notificacao_dengue_ne n
                LEFT JOIN public.populacao_municipio_ano p ON p.cod_mun7=n.cod_mun7 AND p.ano=n.ano
                WHERE n.caso_provavel AND n.ano BETWEEN 2000 AND 2025 AND p.cod_mun7 IS NULL""").fetchone()[0]
            manifesto['casos_provaveis_sem_populacao'] = faltantes
            if faltantes:
                raise RuntimeError('Casos provaveis sem denominador populacional.')
            tabelas = ('notificacao_dengue_ne', 'populacao_municipio_ano', 'populacao_ne', 'municipio', 'estado')
            cols = con.execute("""SELECT table_name,column_name,data_type,udt_name,is_nullable,character_maximum_length
                FROM information_schema.columns WHERE table_schema='public' AND table_name=ANY(%s)
                ORDER BY table_name,ordinal_position""", (list(tabelas),)).fetchall()
            dicionario = [dict(zip(('tabela','coluna','tipo_sql','tipo_interno','permite_nulo','comprimento_maximo'),r)) for r in cols]
            manifesto['consulta_resumo_anual'] = anual_sql
        saida = agregados / 'resumo_anual.csv'
        with saida.open('w', encoding='utf-8', newline='') as f:
            w = csv.writer(f); w.writerow(('ano',) + METRICAS)
            for ano, valores in anual.items():
                w.writerow((ano, *valores))
        dic = metadados / 'dicionario.json'
        dic.write_text(json.dumps(dicionario, ensure_ascii=False, indent=2), encoding='utf-8')
        manifesto['resumo_anual'] = {'arquivo': saida.relative_to(ROOT).as_posix(), 'registros':len(anual),'sha256':sha256(saida)}
        manifesto['dicionario'] = {'arquivo':dic.relative_to(ROOT).as_posix(),'sha256':sha256(dic)}
        manifesto['totais'] = dict(zip(METRICAS, (sum(v[i] for v in anual.values()) for i in range(len(METRICAS)))))
        manifesto['status'] = 'concluido'
        manifesto['concluido_em'] = agora()
        salvar()
        print(json.dumps({'status':'concluido','manifesto':caminho_manifesto.relative_to(ROOT).as_posix(),
                          'totais':manifesto['totais'],'tabelas':{k:v['registros_csv'] for k,v in manifesto['arquivos'].items()},
                          'casos_provaveis_sem_populacao':faltantes},ensure_ascii=False,indent=2), flush=True)
    except Exception as exc:
        manifesto['status']='falhou'; manifesto['tipo_erro']=type(exc).__name__; salvar()
        raise


if __name__ == '__main__':
    main()