"""Gera o notebook e o dicionário dos arquivos da Etapa 1."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def criar():
    campos=[
      ('ano','inteiro','SINAN/NU_ANO ou IBGE/período','Ano de notificação nas bases de dengue; ano da população nas bases populacionais.'),
      ('nivel','texto','IBGE','N6 = município; N3 = unidade da federação. Apenas populacao_nordeste.csv.'),
      ('codigo_ibge','texto','IBGE/localidade.id','Código completo de 7 dígitos para município ou 2 para UF; ausente se não houve correspondência populacional.'),
      ('codigo_municipio_6','texto','ID_MN_RESI e IBGE/localidade.id','Chave municipal de 6 dígitos; reduz código de 7 aos seis primeiros. Não é chave individual.'),
      ('codigo_uf','texto','SINAN/SG_UF e IBGE/localidade.id','21 MA; 22 PI; 23 CE; 24 RN; 25 PB; 26 PE; 27 AL; 28 SE; 29 BA.'),
      ('uf','texto','Derivado de codigo_uf','Sigla da UF de residência ou da localidade populacional.'),
      ('nome_localidade','texto','IBGE/localidade.nome','Nome retornado na tabela e ano consultados; não usar nome como chave.'),
      ('notificacoes','inteiro ou ausente','Contagem de linhas do SINAN','Registros com ano válido antes de filtrar classificação/agravo/duplicidade. Não equivale a casos confirmados ou prováveis. NA = sem grupo correspondente.'),
      ('populacao','inteiro ou ausente','IBGE/SIDRA','Pessoas residentes no território e ano. Sem imputação. Ausente em 2023 ou valores especiais sem população numérica.'),
      ('tipo_populacao','texto','Metadados da coleta','estimativa_anual; censo_2000; contagem_e_estimativas_2007; censo_2010; censo_2022.'),
      ('tabela_ibge','inteiro ou ausente','IBGE/SIDRA','6579; 202; 793; 4714.'),
      ('fonte_populacao','URL','Coleta IBGE','URL completa da consulta incluindo filtros territoriais, variável, ano e classificação.'),
      ('extracao_populacao','data-hora ISO 8601','Coleta','Instante do download original com deslocamento -03:00; cache preserva a data.'),
      ('status_integracao','texto','Junção','integrado = chaves nas duas fontes e população numérica; sem_populacao_no_ano = contagem sem chave populacional correspondente; sem_populacao_valida = chave encontrada, mas valor populacional não numérico; sem_registro_sinan = população sem grupo de notificações. Não representa qualidade epidemiológica.'),
      ('mes_notificacao','inteiro 1–12 ou ausente','SINAN/DT_NOTIFIC','Mês da notificação; na base mensal somente datas válidas com ano igual ao NU_ANO. Não é mês dos sintomas.'),
      ('classificacao_original','texto','CLASSI_FIN ou CON_CLASSI','Código original sem harmonização histórica. AUSENTE identifica branco somente no agregado por classificação; no recorte individual o branco é preservado.'),
      ('campo_classificacao','texto','Layout SINAN','Nome do campo original: CON_CLASSI nos layouts antigos ou CLASSI_FIN nos recentes. Consultar códigos no dicionário compatível com o período.'),
      ('ano_arquivo','inteiro','Nome do recurso SINAN','Ano do ZIP de origem. Preservado mesmo se NU_ANO divergente.'),
      ('ano_valido','booleano','Comparação NU_ANO/ano_arquivo','True quando NU_ANO é numérico e igual ao ano do arquivo. False permanece no recorte e fica fora dos totais.'),
      ('codigo_municipio_residencia_original','texto','SINAN/ID_MN_RESI','Código original de residência com 6 ou 7 dígitos, sem alteração.'),
      ('municipio_consistente','booleano','Validação geográfica','Código de 6/7 dígitos cujo prefixo coincide com a UF de residência; existência na população é validada depois na junção.'),
      ('data_notificacao_original','texto data','SINAN/DT_NOTIFIC','Valor original; conversão inválida é auditada sem substituir o texto.'),
      ('data_sintomas_original','texto data','SINAN/DT_SIN_PRI','Valor original dos primeiros sintomas, preservado para análise posterior.'),
      ('data_notificacao_consistente','booleano','Conversão DT_NOTIFIC','Data interpretável como AAAA-MM-DD e com ano igual ao ano do arquivo.'),
      ('criterio_original','texto','CRITERIO ou CON_CRITER','Código original de critério de confirmação/descarte; harmonização pendente na Etapa 2.'),
      ('evolucao_original','texto','EVOLUCAO ou CON_EVOLUC','Código original da evolução; harmonização pendente na Etapa 2.'),
      ('NDUPLIC','texto opcional','SINAN/layout antigo','Marcação original de duplicidade; mantida somente quando existe na fonte. Não aplicada ao numerador nesta etapa.'),
      ('NDUPLIC_N','texto opcional','SINAN/layout recente','Marcação original; no dicionário atual, 2 = duplicidade/não contar. Preservada para a limpeza.'),
      ('ID_AGRAVO','texto opcional','SINAN','Código do agravo conforme fonte; preservado para verificar seleção epidemiológica.'),
      ('ID_DG_NOT','texto opcional','SINAN/layout antigo','Código diagnóstico original; não harmonizado nesta etapa.'),
      ('CS_SEXO','texto opcional','SINAN','Código original de sexo; não utilizado na integração.'),
      ('NU_IDADE','texto opcional','SINAN/layout antigo','Idade codificada original; não interpretar diretamente como anos.'),
      ('NU_IDADE_N','texto opcional','SINAN/layout recente','Idade codificada com unidade; não interpretar diretamente como anos.'),
      ('estados','inteiro','Cobertura anual','Quantidade de UFs na grade de estado-ano.'),
      ('estados_com_populacao','inteiro','Cobertura anual','Quantidade de UFs com denominador numérico naquele ano.'),
    ]
    (ROOT/'docs').mkdir(exist_ok=True)
    with open(ROOT/'docs/dicionario_dados.csv','w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['variavel','tipo','origem','descricao_e_regras']); w.writerows(campos)
    cells=[]
    def md(s):cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(True)})
    def code(s):cells.append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(True)})
    md('# Etapa 1 — Coleta e integração: dengue no Nordeste\n\nIMD1151, 2026.2. Período: 2000–2025. Fontes: SINAN/MS e IBGE/SIDRA.\n\nEste notebook acompanha uma coleta real e reproduzível. Leia `README.md` antes de interpretar as contagens como casos. População de 2023 permanece ausente: não houve imputação.\n')
    md('## 1. Configuração\n\nO caminho do projeto é localizado a partir da pasta atual. Para outra organização, defina `ROOT` manualmente. As opções abaixo permitem repetir a coleta e o processamento. Com ambas falsas, arquivos existentes são usados; numa pasta sem resultados, as etapas necessárias são executadas.\n')
    code('from pathlib import Path\nimport sys\nimport json\nimport pandas as pd\n\nbase = Path.cwd().resolve()\ncandidatos = [base, base / "dengue_nordeste", *base.parents]\nROOT = next((p for p in candidatos if (p / "scripts/coletar.py").is_file()), None)\nif ROOT is None:\n    raise FileNotFoundError("Abra o notebook a partir da pasta dengue_nordeste.")\nsys.path.insert(0, str(ROOT / "scripts"))\nfrom coletar import coletar\nfrom integrar import integrar\nINICIO, FIM = 2000, 2025\nRECOLETAR = False\nREINTEGRAR = False\nprint("Projeto:", ROOT)\nprint("Período:", INICIO, "a", FIM)\n')
    md('## 2. Coleta oficial e rastreabilidade\n\nArquivos anuais CSV/ZIP são descobertos no catálogo oficial, evitando paginação de milhões de registros. A população é consultada com filtros dos nove estados, nos níveis municipal e estadual. Os originais ficam em `data/raw`; o manifesto registra URLs, extração, atualização na fonte e hashes.\n')
    code('manifesto_path = ROOT / "data/metadata/manifesto_extracao.json"\nif RECOLETAR or not manifesto_path.exists():\n    coletar(INICIO, FIM, atualizar=RECOLETAR)\nmanifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))\nstatus_coleta = json.loads((ROOT / "data/metadata/status_coleta.json").read_text(encoding="utf-8"))\nassert not status_coleta["erros"], status_coleta["erros"]\nprint("Recursos no manifesto:", len(manifesto))\nprint(pd.DataFrame(manifesto)[["origem", "arquivo", "extraido_em", "bytes"]].head(8).to_string(index=False))\nprint("Anos sem publicação anual de população na série:", status_coleta["populacao_sem_publicacao_anual"])\n')
    md('## 3. Seleção e integração\n\nSelecionamos UF de residência (`SG_UF`), normalizamos `ID_MN_RESI` para seis dígitos e integramos pelo código e `NU_ANO`. A população mantém o código IBGE completo. As junções preservam chaves sem correspondência. Não aplicamos filtros de caso, remoção de duplicidade ou imputação de população nesta etapa.\n')
    code('validacao_path = ROOT / "data/metadata/validacao_integracao.json"\nif REINTEGRAR or not validacao_path.exists():\n    integrar(INICIO, FIM)\nvalidacao = json.loads(validacao_path.read_text(encoding="utf-8"))\nassert (validacao["inicio"], validacao["fim"]) == (INICIO, FIM), "Resultados de outro recorte: ative REINTEGRAR."\nfor campo in ["estados", "notificacoes_ne", "linhas_municipio_ano", "linhas_estado_ano", "populacao_ausente_estado_ano", "status_municipal"]:\n    print(campo + ":", validacao[campo])\n')
    md('## 4. Bases prontas para a limpeza\n\nLeia códigos como texto. As contagens ausentes não são zero. A base mensal segue o mês de notificação; para sazonalidade por início dos sintomas, utilize os recortes individuais na Etapa 2.\n')
    code('tipos = {"codigo_municipio_6": "string", "codigo_ibge": "string", "codigo_uf": "string"}\nmunicipal = pd.read_csv(ROOT / "data/processed/dengue_municipio_ano.csv", dtype=tipos)\nestadual = pd.read_csv(ROOT / "data/processed/dengue_estado_ano.csv", dtype=tipos)\nmensal = pd.read_csv(ROOT / "data/processed/dengue_estado_mes_notificacao.csv", dtype={"codigo_uf": "string"})\npopulacao = pd.read_csv(ROOT / "data/processed/populacao_nordeste.csv", dtype=tipos)\nprint(municipal[["ano", "codigo_municipio_6", "codigo_ibge", "uf", "notificacoes", "populacao", "status_integracao"]].head(10).to_string(index=False))\n')
    md('## 5. Verificações da integração\n\nAlém das verificações feitas pelo script, conferimos as chaves, o total estadual, a classificação e a reconciliação dos registros sem município consistente. A etapa não prova ausência de subnotificação nem resolve comparabilidade epidemiológica.\n')
    code('assert not municipal.duplicated(["codigo_municipio_6", "ano"]).any()\nassert not estadual.duplicated(["codigo_uf", "ano"]).any()\nassert estadual.groupby("ano").uf.nunique().eq(9).all()\nassert estadual.ano.between(INICIO, FIM).all()\nassert len(estadual) == 9 * (FIM - INICIO + 1)\nassert populacao.populacao.dropna().gt(0).all()\nassert int(estadual.notificacoes.sum()) == validacao["notificacoes_ne"]\nauditorias = pd.DataFrame(validacao["auditorias"])\nsem_municipio = int(auditorias.ne_ano_valido_sem_municipio_consistente.sum())\nassert int(municipal.notificacoes.sum()) + sem_municipio == int(estadual.notificacoes.sum())\nclasses = pd.read_csv(ROOT / "data/processed/classificacao_estado_ano.csv")\nassert int(classes.notificacoes.sum()) == int(estadual.notificacoes.sum())\nprint("Validações concluídas.")\nprint("Registros no total estadual sem município consistente:", sem_municipio)\nprint(pd.read_csv(ROOT / "data/processed/cobertura_anual.csv").to_string(index=False))\n')
    md('## 6. Pendências e dicionário\n\nOs extremos e as inconsistências deverão ser investigados na Etapa 2. O dicionário oficial atual foi preservado, mas não define automaticamente todos os códigos dos layouts antigos. Para calcular incidência, primeiro harmonize o numerador e documente o denominador de 2023.\n')
    code('print(auditorias[["ano", "registros_brasil", "registros_ne", "ano_divergente_ou_ausente", "municipio_invalido_ou_uf_divergente", "data_sintomas_ausente_ou_invalida"]].to_string(index=False))\nprint("\\nStatus da integração municipal:")\nprint(municipal.status_integracao.value_counts().to_string())\nprint("\\nDicionário:")\nprint(pd.read_csv(ROOT / "docs/dicionario_dados.csv").head(10).to_string(index=False))\n')
    md('## 7. Próxima etapa e declaração de IA\n\nA coleta e a integração fornecem a matéria-prima da análise. Antes de divulgar incidência: definir caso; investigar duplicidade/agravo, datas e códigos; escolher referência temporal; tratar cobertura e justificar população de 2023.\n\nChatGPT/Codex foi utilizado na implementação e documentação. O grupo deverá registrar as revisões humanas realmente realizadas e as contribuições individuais.\n\nFontes: [SINAN/Dengue](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue), [SIDRA 6579](https://sidra.ibge.gov.br/tabela/6579), [202](https://sidra.ibge.gov.br/tabela/202), [793](https://sidra.ibge.gov.br/tabela/793), [4714](https://sidra.ibge.gov.br/tabela/4714). URLs completas e datas efetivas constam do manifesto.\n')
    # IDs estáveis de célula, compatíveis com nbformat 4.5.
    for i,c in enumerate(cells):c['id']=f'etapa1-{i:02d}'
    notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'language_info':{'name':'python','version':'3.11'}},'nbformat':4,'nbformat_minor':5}
    (ROOT/'notebooks').mkdir(exist_ok=True)
    (ROOT/'notebooks/01_coleta_integracao.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=1),encoding='utf-8')
    print('Notebook e dicionário criados.')

if __name__=='__main__':criar()
