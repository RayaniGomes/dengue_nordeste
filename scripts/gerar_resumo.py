"""Escreve um resumo legível da execução e um pacote portátil sem microdados."""
from pathlib import Path
import json
import zipfile
import platform
import sys
import pandas as pd
from coletar import ROOT, agora, sha256

def gerar():
    ambiente={'registrado_em':agora(),'python':sys.version,'pandas':pd.__version__,
              'sistema':platform.platform(),'scripts_sha256':{
                  p.name:sha256(p) for p in sorted((ROOT/'scripts').glob('*.py'))}}
    (ROOT/'data/metadata/ambiente_execucao.json').write_text(json.dumps(ambiente,ensure_ascii=False,indent=2),encoding='utf-8')
    v=json.loads((ROOT/'data/metadata/validacao_integracao.json').read_text(encoding='utf-8'))
    manifesto=json.loads((ROOT/'data/metadata/manifesto_extracao.json').read_text(encoding='utf-8'))
    p=pd.read_csv(ROOT/'data/processed/dengue_municipio_ano.csv')
    a=pd.DataFrame(v['auditorias'])
    datas=sorted(m['extraido_em'] for m in manifesto)
    tamanho=sum(m['bytes'] for m in manifesto)
    linhas=[
      '# Resultado da Etapa 1 — coleta e integração', '',
      f'Resumo gerado em {agora()} (UTC-03:00).', '',
      f'- Recorte: {v["inicio"]}–{v["fim"]}; nove UFs do Nordeste.',
      '- Fontes: arquivos oficiais SINAN/Dengue e API IBGE/SIDRA.',
      f'- Extrações: de {datas[0]} até {datas[-1]}.',
      f'- Recursos rastreados: {len(manifesto)}; {tamanho/1024**2:.1f} MiB de arquivos originais.',
      f'- Registros SINAN de residentes no NE, antes da validação do ano: {int(a.registros_ne.sum()):,}.',
      f'- Notificações com ano válido nas tabelas integradas: {v["notificacoes_ne"]:,}.',
      f'- Registros com ano divergente/ausente, preservados nos recortes e excluídos dos totais: {int(a.ano_divergente_ou_ausente.sum()):,}.',
      f'- Linhas municipais por ano, considerando a união das chaves: {v["linhas_municipio_ano"]:,}.',
      f'- Linhas estaduais por ano: {v["linhas_estado_ano"]}.',
      f'- Registros com ano válido no total estadual sem município consistente: {int(a.ne_ano_valido_sem_municipio_consistente.sum()):,}.',
      f'- Linhas municipais com população ausente: {int(p.populacao.isna().sum()):,}.',
      '', '## Situação das junções municipais', '',
    ]
    linhas += [f'- {k}: {n:,} linhas.' for k,n in v['status_municipal'].items()]
    linhas += ['', '## Verificações concluídas', '',
      '- Chaves únicas, junções um-para-um, nove UFs por ano e conservação das contagens.',
      '- Reconciliação dos totais estaduais com os municipais e a auditoria de códigos inconsistentes.',
      '- Conferência independente dos arquivos contra os hashes do manifesto.',
      '- Execução sequencial de todas as células Python do notebook, com saídas reais.',
      '', '## Pendências para a Etapa 2', '',
      '**2023 não tem denominador anual na série do IBGE consultada.** Os dados de dengue desse ano foram coletados, mas a população permanece ausente. As nove linhas estaduais de 2023 e as chaves municipais sem correspondência estão sinalizadas. Não foi feita interpolação nem repetição silenciosa de 2022.',
      '',
      'Os números acima são contagens de registros notificados disponíveis na fonte. A definição de casos de dengue, o tratamento das marcações de duplicidade e a harmonização das classificações ainda devem ser realizados antes do cálculo de incidência. As mudanças de layouts e de cobertura dos arquivos precisam ser investigadas; os totais não devem ser usados como uma série homogênea de casos sem essa verificação.',
      '',
      'O pacote ZIP portátil contém scripts, notebook executado, documentação, bases agregadas e metadados. Os ZIPs nacionais e recortes individuais ficam na pasta local `data/` e não foram duplicados no pacote. Para reconstruí-los após descompactar, execute `scripts/coletar.py`; para uma atualização completa, utilize `--atualizar`.',
    ]
    (ROOT/'docs/resumo_execucao.md').write_text('\n'.join(linhas)+'\n',encoding='utf-8')
    pacote=ROOT.parent/'dengue_nordeste_etapa1.zip'
    with zipfile.ZipFile(pacote,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file():continue
            rel=p.relative_to(ROOT)
            if any(s in rel.parts for s in ('raw','interim','__pycache__','.ipynb_checkpoints','.venv')):continue
            if p.suffix=='.part':continue
            z.write(p,Path(ROOT.name)/rel)
    with zipfile.ZipFile(pacote) as z:
        assert z.testzip() is None
    print(pacote)
    print(f'{pacote.stat().st_size/1024**2:.2f} MiB')

if __name__=='__main__':gerar()
