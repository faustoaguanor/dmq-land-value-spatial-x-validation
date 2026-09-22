"""Lectura validada de una corrida base y smearing de su propio entrenamiento.

No entrena ni escribe archivos. Las medias multisemilla se obtienen por separado
en cifras_canonicas.py; este modulo solo opera sobre vectores por predio.
"""
from pathlib import Path

import numpy as np
import pandas as pd


def cargar_predicciones(ruta, referencia=None):
    """Devuelve train/test en log y USD/m², conservando orden e identificadores.

    Si se aporta una referencia con predio_join, split y valor_m2, exige identidad
    de claves, particiones y objetivo. El factor nunca se toma de otro resumen.
    """
    ruta = Path(ruta)
    df = pd.read_csv(ruta)
    requeridas = {'predio_join', 'split', 'y_obs_log', 'y_pred_log'}
    if not requeridas.issubset(df.columns):
        raise ValueError(f'{ruta}: faltan columnas {sorted(requeridas - set(df.columns))}')
    ids = pd.to_numeric(df['predio_join'], errors='raise')
    if not np.isfinite(ids).all() or not np.equal(ids, np.floor(ids)).all():
        raise ValueError(f'{ruta}: identificadores no enteros o ausentes')
    df['predio_join'] = ids.astype('int64')
    if df['predio_join'].duplicated().any():
        raise ValueError(f'{ruta}: identificadores duplicados')
    if set(df['split']) != {'train', 'test'}:
        raise ValueError(f'{ruta}: se requieren exclusivamente train y test, ambos presentes')
    if not np.isfinite(df[['y_obs_log', 'y_pred_log']].to_numpy(dtype=float)).all():
        raise ValueError(f'{ruta}: observaciones o predicciones no finitas')
    if referencia is not None:
        ref = referencia[['predio_join', 'split', 'valor_m2']].copy()
        ref['predio_join'] = ref['predio_join'].astype('int64')
        if ref['predio_join'].duplicated().any() or set(ref['predio_join']) != set(df['predio_join']):
            raise ValueError(f'{ruta}: claves distintas a la referencia')
        ref = ref.set_index('predio_join').loc[df['predio_join']]
        if not np.array_equal(df['split'].to_numpy(), ref['split'].to_numpy()):
            raise ValueError(f'{ruta}: particiones distintas a la referencia')
        if not np.allclose(df['y_obs_log'], np.log(ref['valor_m2']), rtol=0, atol=1e-6):
            raise ValueError(f'{ruta}: objetivo distinto a la referencia')
    tr = df.loc[df['split'].eq('train')]
    with np.errstate(over='raise', invalid='raise'):
        factor = float(np.exp(tr['y_obs_log'] - tr['y_pred_log']).mean())
        df['obs_usd'] = np.exp(df['y_obs_log'])
        df['pred_usd'] = np.exp(df['y_pred_log']) * factor
    if not np.isfinite(factor) or factor <= 0 or not np.isfinite(df[['obs_usd', 'pred_usd']]).all().all():
        raise ValueError(f'{ruta}: retransformacion no finita o factor invalido')
    df['error_abs'] = (df['obs_usd'] - df['pred_usd']).abs()
    df['error_cuad'] = (df['obs_usd'] - df['pred_usd']) ** 2
    df.attrs['smearing_factor'] = factor
    return df
