"""Testes de decisões epidemiológicas/geográficas que podem alterar o numerador."""
import unittest
import pandas as pd
from limpar_analisar import limpar_registros

def registro(**kwargs):
    return {'ano':'2025','codigo_uf':'23','codigo_municipio_6':'230440',
      'data_notificacao_original':'2025-02-03','data_sintomas_original':'2025-01-30',
      'classificacao_original':'10','criterio_original':'2','ID_AGRAVO':'A90',
      'NDUPLIC_N':'0',**kwargs}

class Regras(unittest.TestCase):
    def limpar(self,r,ano=2025):return limpar_registros(pd.DataFrame([r]),ano).iloc[0]
    def test_descartado_excluido(self):
        d=self.limpar(registro(classificacao_original='5'))
        self.assertEqual(d.motivo_exclusao,'descartado')
    def test_codigo_legado_nao_e_descartado(self):
        r=registro(ano='2016',classificacao_original='2',data_notificacao_original='2016-02-03',data_sintomas_original='2016-01-30')
        self.assertTrue(self.limpar(r,2016).caso_provavel_operacional)
        self.assertEqual(self.limpar(registro(classificacao_original='2')).motivo_exclusao,'classificacao_desconhecida')
    def test_inconclusivo_somente_definicao_ampla(self):
        d=self.limpar(registro(classificacao_original='8'))
        self.assertTrue(d.caso_provavel_operacional)
        self.assertFalse(d.caso_criterio_estrito)
    def test_duplicata_marcada_e_nao_listar(self):
        self.assertEqual(self.limpar(registro(NDUPLIC_N='2')).motivo_exclusao,'duplicidade_marcada')
        self.assertTrue(self.limpar(registro(NDUPLIC_N='1')).caso_provavel_operacional)
    def test_chikungunya_nao_entra(self):
        self.assertEqual(self.limpar(registro(classificacao_original='13')).motivo_exclusao,'chikungunya')
    def test_sem_imputacao_de_sintomas(self):
        self.assertEqual(self.limpar(registro(data_sintomas_original='')).motivo_exclusao,'sintomas_invalidos_ou_fora_recorte')
    def test_datas_cronologicas(self):
        self.assertEqual(self.limpar(registro(data_sintomas_original='2025-02-04')).motivo_exclusao,'sintomas_apos_notificacao')
    def test_ano_dos_sintomas_nao_notificacao(self):
        d=self.limpar(registro(data_sintomas_original='2024-12-31'))
        self.assertEqual(d.ano_sintomas,2024)
        self.assertEqual(d.ano_notificacao,2025)
    def test_notificacao_tardia_2026_sem_ampliar_sintomas(self):
        r=registro(ano='2026',data_notificacao_original='2026-01-03',data_sintomas_original='2025-12-31')
        d=limpar_registros(pd.DataFrame([r]),2026,data_corte='2026-10-29').iloc[0]
        self.assertTrue(d.caso_provavel_operacional)
        self.assertEqual(d.ano_sintomas,2025)
        r['data_sintomas_original']='2026-01-01'
        d=limpar_registros(pd.DataFrame([r]),2026,data_corte='2026-10-29').iloc[0]
        self.assertEqual(d.motivo_exclusao,'sintomas_invalidos_ou_fora_recorte')
    def test_ano_ausente_recuperado_da_data(self):
        d=self.limpar(registro(ano=''))
        self.assertTrue(d.caso_provavel_operacional)
        self.assertTrue(d.nu_ano_divergente_data)
    def test_sem_atribuicao_municipal_arbitraria(self):
        d=self.limpar(registro(codigo_municipio_6='290001'))
        self.assertTrue(d.caso_provavel_operacional)
        self.assertFalse(d.municipio_valido)
    def test_CID_ausente_nao_e_dengue_confirmada(self):
        self.assertEqual(self.limpar(registro(ID_AGRAVO='')).motivo_exclusao,'agravo_incompativel_ou_ausente')
    def test_ID_DG_NOT_legado_nao_e_CID(self):
        r=registro(ano='2002',classificacao_original='1',data_notificacao_original='2002-02-03',data_sintomas_original='2002-01-30',ID_DG_NOT='1')
        del r['ID_AGRAVO']
        self.assertTrue(self.limpar(r,2002).caso_provavel_operacional)

if __name__=='__main__':unittest.main()
