"""Fontes primárias de classificação e malhas simplificadas para a EDA."""
import json
from coletar import RAW, META, UFS, baixar, agora

def coletar_referencias():
    referencias=[
      ('https://portalsinan.saude.gov.br/images/documentos/Agravos/Dengue/DIC_DADOS_ONLINE.pdf',
       'dicionario_online_2015.pdf','SINAN/MS — dicionário Online, revisão 21/10/2015'),
      ('https://saude.es.gov.br/Media/sesa/LACEN/Fichas_SINAN/ficha_16_sinan_Dengue.pdf',
       'ficha_dengue_2006.pdf','Ministério da Saúde — ficha SINAN NET, 25/09/2006, hospedada na SESA/ES'),
      ('https://bvsms.saude.gov.br/bvs/publicacoes/Guia_Vig_Epid_novo2.pdf',
       'guia_vigilancia_historico.pdf','Ministério da Saúde — guia histórico, ficha CENEPI de 30/05/2001'),
      ('https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue',
       'notas_sinan.html','Ministério da Saúde — definição de casos prováveis e residência'),
    ]
    for url,nome,origem in referencias:
        baixar(url,RAW/'referencias_etapa2'/nome,origem)
        print('Referência:',nome,flush=True)
    for codigo,uf in UFS.items():
        url=f'https://servicodados.ibge.gov.br/api/v3/malhas/estados/{codigo}?formato=application/vnd.geo%2Bjson&qualidade=minima'
        baixar(url,RAW/f'referencias_etapa2/malha_{uf}.json','IBGE — API de malhas simplificadas',{'codigo_uf':codigo})
        print('Malha:',uf,flush=True)
    manifesto=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((RAW/'referencias_etapa2').glob('*.meta.json'))]
    (META/'manifesto_referencias_etapa2.json').write_text(json.dumps({'consultado_em':agora(),'recursos':manifesto},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':coletar_referencias()
