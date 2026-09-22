"""Contratos de lectura que evitan mezclar corridas, claves y factores."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

spec = importlib.util.spec_from_file_location('predicciones_base_check', Path(__file__).resolve().parents[1] / 'analisis/predicciones_base.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PrediccionesBaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / 'pred.csv'
        self.df = pd.DataFrame({'predio_join': ['01320007', '2', '3'], 'split': ['train', 'train', 'test'],
                                'y_obs_log': np.log([20., 60., 100.]), 'y_pred_log': np.log([10., 20., 25.])})
        self.ref = pd.DataFrame({'predio_join': [3, 2, 1320007], 'split': ['test', 'train', 'train'], 'valor_m2': [100., 60., 20.]})

    def test_factor_solo_train(self):
        self.df.to_csv(self.ruta,index=False)
        out = mod.cargar_predicciones(self.ruta)
        self.assertAlmostEqual(out.attrs['smearing_factor'],2.5)
        self.assertAlmostEqual(out.loc[2,'pred_usd'],62.5)
        self.df.loc[2,'y_obs_log'] = np.log(1000.)
        self.df.to_csv(self.ruta,index=False)
        self.assertAlmostEqual(mod.cargar_predicciones(self.ruta).attrs['smearing_factor'],2.5)

    def test_alineacion_por_id_no_por_posicion(self):
        self.df.to_csv(self.ruta,index=False)
        out = mod.cargar_predicciones(self.ruta,self.ref)
        self.assertEqual(out.predio_join.tolist(),[1320007,2,3])
        self.assertAlmostEqual(out.loc[2,'pred_usd'],62.5)

    def test_rechaza_incompatibilidades(self):
        for caso in ['duplicado','sin_train','no_finito','particion','objetivo','id_faltante']:
            with self.subTest(caso=caso):
                df=self.df.copy();ref=self.ref.copy()
                if caso=='duplicado':df.loc[1,'predio_join']='01320007'
                if caso=='sin_train':df['split']='test'
                if caso=='no_finito':df.loc[0,'y_pred_log']=np.nan
                if caso=='particion':ref.loc[1,'split']='test'
                if caso=='objetivo':ref.loc[0,'valor_m2']=101.
                if caso=='id_faltante':ref=ref.iloc[:2]
                df.to_csv(self.ruta,index=False)
                with self.assertRaises(ValueError):mod.cargar_predicciones(self.ruta,ref)

if __name__=='__main__':unittest.main()
