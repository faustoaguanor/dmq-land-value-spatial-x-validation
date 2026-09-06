"""
02b_equivalencia_estructural.py -- observacion 1.2, parte interna.

Comprueba, con aritmetica y no con prosa, que la implementacion propia hace lo
que dice la formulacion publicada de GNNWR (Du et al. 2020) y en que se aparta
la de SANNWR-adaptado respecto de Ni et al. (2022). Es el complemento barato de
02a: aunque el paquete de referencia no se pueda instalar, estas comprobaciones
se pueden correr y reportar.

Se verifica:

  E1  la salida es y = sum_k w_k(d) * beta_k^OLS * x_k, no otra composicion
  E2  si la red devolviera pesos identicos a 1, la prediccion coincide con OLS
      (propiedad definitoria: la red modula coeficientes globales)
  E3  los beta OLS estan congelados y no se mueven al entrenar
  E4  la entrada de la red es el vector completo de distancias a los n puntos de
      entrenamiento, con distancia nula a si mismo antes de estandarizar
  E5  la estandarizacion de distancias se ajusta solo con entrenamiento
  E6  SANNWR-adaptado usa d = 0,5*z(d_espacial) + 0,5*z(d_atributiva) con peso
      fijo, no aprendido: es el punto que obliga a rotularla "adaptado"
  E7  SANNWR-original si funde las dos distancias con una red entrenable (SAPDNN),
      que es lo que define al diseno publicado. Lo que rinde ese diseno bajo el
      protocolo completo lo mide 02d_sannwr_original.py

Corre en CPU en menos de un minuto sobre una submuestra.
Uso:  python obs2_equivalencia_gnnwr/02b_equivalencia_estructural.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy.spatial.distance import cdist
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from comun.rutas import salida, pr, tabla_md      # noqa: E402
from comun import datos as D, nombres as N        # noqa: E402
from comun import entrenadores as E               # noqa: E402

N_SUB = 160          # submuestra: las comprobaciones son estructurales, no de ajuste
TOL = 1e-4


class Unos(nn.Module):
    """SWNN degenerada que devuelve pesos identicos a 1."""

    def __init__(self, outsize):
        super().__init__()
        self.outsize = outsize

    def forward(self, x):
        return torch.ones(x.shape[0], self.outsize, dtype=x.dtype, device=x.device)


def preparar(conj, n_sub=N_SUB, semilla=42):
    rng = np.random.default_rng(semilla)
    idx = np.sort(rng.choice(np.where(conj.train_mask)[0], size=n_sub, replace=False))
    idx_te = np.sort(rng.choice(np.where(conj.test_mask)[0], size=40, replace=False))
    sc = StandardScaler().fit(conj.X[idx])
    Xtr = sc.transform(conj.X[idx])
    Xte = sc.transform(conj.X[idx_te])
    ytr = conj.y_log[idx]
    Xtr_i, Xte_i = E.add_intercept(Xtr), E.add_intercept(Xte)
    ols = LinearRegression(fit_intercept=False).fit(Xtr_i, ytr).coef_.flatten().astype(np.float32)
    return dict(idx=idx, idx_te=idx_te, Xtr=Xtr, Xte=Xte, Xtr_i=Xtr_i, Xte_i=Xte_i,
                ytr=ytr, ols=ols, ctr=conj.coords[idx], cte=conj.coords[idx_te])


def main() -> int:
    torch.manual_seed(42)
    conj = D.cargar()
    p = preparar(conj)
    filas = []

    def anotar(codigo, descripcion, esperado, obtenido, ok):
        filas.append({"codigo": codigo, "comprobacion": descripcion,
                      "esperado": esperado, "obtenido": obtenido,
                      "estado": "PASA" if ok else "FALLA"})
        pr(f"  {codigo}  {'PASA' if ok else 'FALLA'}  {descripcion}  -> {obtenido}")

    dtr, dte = E._distancias(N.GNNWR, p["ctr"], p["cte"], p["Xtr"], p["Xte"])
    red = E.RedPonderada(len(p["idx"]), p["Xtr_i"].shape[1], p["ols"])
    red.eval()

    # E1 -- composicion de la salida
    with torch.no_grad():
        td = torch.tensor(dte, dtype=torch.float32)
        tx = torch.tensor(p["Xte_i"], dtype=torch.float32)
        y_modelo = red(td, tx).numpy().ravel()
        w = red.swnn(td).numpy()
    y_manual = (w * p["Xte_i"] * p["ols"][None, :]).sum(axis=1)
    dif = float(np.max(np.abs(y_modelo - y_manual)))
    anotar("E1", "salida = suma_k w_k(d)*beta_k^OLS*x_k",
           f"diferencia < {TOL}", f"max|dif| = {dif:.2e}", dif < TOL)

    # E2 -- pesos unitarios reducen el modelo a OLS
    red2 = E.RedPonderada(len(p["idx"]), p["Xtr_i"].shape[1], p["ols"])
    red2.swnn = Unos(p["Xtr_i"].shape[1])
    red2.eval()
    with torch.no_grad():
        y_unos = red2(td, tx).numpy().ravel()
    y_ols = p["Xte_i"] @ p["ols"]
    dif2 = float(np.max(np.abs(y_unos - y_ols)))
    anotar("E2", "con w=1 la prediccion coincide con OLS",
           f"diferencia < {TOL}", f"max|dif| = {dif2:.2e}", dif2 < TOL)

    # E3 -- beta OLS congelados
    congelado = not red.out.weight.requires_grad
    antes = red.out.weight.detach().clone()
    opt = torch.optim.Adadelta(red.parameters(), lr=0.2)
    red.train()
    perdida = ((red(torch.tensor(dtr, dtype=torch.float32),
                    torch.tensor(p["Xtr_i"], dtype=torch.float32)).squeeze()
                - torch.tensor(p["ytr"], dtype=torch.float32)) ** 2).mean()
    opt.zero_grad()
    perdida.backward()
    opt.step()
    movio = float(torch.max(torch.abs(red.out.weight.detach() - antes)))
    anotar("E3", "los coeficientes OLS no se entrenan",
           "requires_grad=False y sin cambio tras un paso",
           f"requires_grad={red.out.weight.requires_grad}, max|delta|={movio:.2e}",
           congelado and movio == 0.0)

    # E4 -- entrada de la red
    d_bruta = cdist(p["ctr"], p["ctr"])
    diag_cero = float(np.max(np.abs(np.diag(d_bruta)))) == 0.0
    dim_ok = dtr.shape[1] == len(p["idx"]) and dte.shape[1] == len(p["idx"])
    anotar("E4", "la entrada es el vector de distancias a los n de entrenamiento",
           f"ancho = n_train = {len(p['idx'])}, diagonal nula antes de escalar",
           f"ancho train={dtr.shape[1]}, ancho test={dte.shape[1]}, diag_cero={diag_cero}",
           dim_ok and diag_cero)

    # E5 -- el escalador de distancias se ajusta solo con entrenamiento
    sc = StandardScaler().fit(cdist(p["ctr"], p["ctr"]))
    esperado_te = sc.transform(cdist(p["cte"], p["ctr"])).astype(np.float32)
    dif5 = float(np.max(np.abs(esperado_te - dte)))
    anotar("E5", "distancias de evaluacion escaladas con el ajuste del entrenamiento",
           f"diferencia < {TOL}", f"max|dif| = {dif5:.2e}", dif5 < TOL)

    # E6 -- distancia hibrida de SANNWR-adaptado
    htr, hte = E._distancias(N.SANNWR, p["ctr"], p["cte"], p["Xtr"], p["Xte"])
    sc_sp = StandardScaler().fit(cdist(p["ctr"], p["ctr"]))
    sc_at = StandardScaler().fit(cdist(p["Xtr"], p["Xtr"]))
    esperado_h = (0.5 * sc_sp.transform(cdist(p["cte"], p["ctr"]))
                  + 0.5 * sc_at.transform(cdist(p["Xte"], p["Xtr"])))
    dif6 = float(np.max(np.abs(esperado_h - hte)))
    alfa_fijo = (E.ALPHA_SANNWR == 0.5) and not any(
        "alpha" in n.lower() for n, _ in E.RedPonderada(
            len(p["idx"]), p["Xtr_i"].shape[1], p["ols"]).named_parameters())
    anotar("E6", "distancia hibrida 0,5/0,5 con peso fijo (no aprendido)",
           f"d = 0,5*z(esp) + 0,5*z(atr), alpha constante; diferencia < {TOL}",
           f"max|dif| = {dif6:.2e}, alpha={E.ALPHA_SANNWR}, sin parametro alpha={alfa_fijo}",
           dif6 < TOL and alfa_fijo)

    # E7 -- el SANNWR publicado: la fusion de las dos distancias es APRENDIDA
    otr, ote = E._distancias(N.SANNWR_ORIG, p["ctr"], p["cte"], p["Xtr"], p["Xte"])
    forma_ok = ote.shape == (len(p["idx_te"]), len(p["idx"]), 2)
    red_o = E.RedPonderadaSAPDNN(len(p["idx"]), p["Xtr_i"].shape[1], p["ols"])
    entrenables = sum(int(t.numel()) for t in red_o.sapdnn.parameters() if t.requires_grad)
    td_o = torch.tensor(ote, dtype=torch.float32)
    red_o.eval()
    with torch.no_grad():
        fundida_antes = red_o.sapdnn(td_o).squeeze(-1).clone()
    opt_o = torch.optim.Adadelta(red_o.parameters(), lr=0.2)
    red_o.train()
    perdida_o = ((red_o(torch.tensor(otr, dtype=torch.float32),
                        torch.tensor(p["Xtr_i"], dtype=torch.float32)).squeeze()
                  - torch.tensor(p["ytr"], dtype=torch.float32)) ** 2).mean()
    opt_o.zero_grad()
    perdida_o.backward()
    opt_o.step()
    red_o.eval()
    with torch.no_grad():
        movio_fusion = float(torch.max(torch.abs(red_o.sapdnn(td_o).squeeze(-1) - fundida_antes)))
    anotar("E7", "SANNWR-original funde las dos distancias con una red entrenable",
           f"entrada (n_eval, n_train, 2), SAPDNN 2->{E.SAPDNN_HIDDEN}->1 con parametros que cambian",
           f"forma={ote.shape}, parametros SAPDNN={entrenables}, "
           f"cambio de la fusion tras un paso={movio_fusion:.2e}",
           forma_ok and entrenables > 0 and movio_fusion > 0)

    df = pd.DataFrame(filas)
    dst = salida("obs2", "equivalencia_estructural.csv")
    df.to_csv(dst, index=False, encoding="utf-8")

    # Tabla de divergencias declaradas frente a la especificacion publicada.
    div = pd.DataFrame([
        {"aspecto": "ponderacion", "GNNWR publicado (Du et al. 2020)": "SWNN sobre distancias espaciales",
         "implementacion evaluada": "igual", "divergencia": "no"},
        {"aspecto": "coeficientes base", "GNNWR publicado (Du et al. 2020)": "OLS global congelado",
         "implementacion evaluada": "igual", "divergencia": "no"},
        {"aspecto": "arquitectura SWNN", "GNNWR publicado (Du et al. 2020)": "capas densas decrecientes con PReLU, dropout y BatchNorm",
         "implementacion evaluada": f"{E.DENSE_LAYERS}, PReLU, dropout {E.DROP_OUT}, BatchNorm",
         "divergencia": "configuracion fijada, no ajustada con estos datos"},
        {"aspecto": "optimizador", "GNNWR publicado (Du et al. 2020)": "Adadelta (el paquete usa Adagrad por defecto)",
         "implementacion evaluada": f"Adadelta lr {E.START_LR}, weight decay {E.WEIGHT_DECAY}",
         "divergencia": "coincide con el articulo, no con el defecto del paquete"},
        {"aspecto": "escalado", "GNNWR publicado (Du et al. 2020)": "minmax en el paquete",
         "implementacion evaluada": "estandarizacion (media 0, desviacion 1)",
         "divergencia": "si"},
        {"aspecto": "parada", "GNNWR publicado (Du et al. 2020)": "no especificada",
         "implementacion evaluada": f"parada temprana, paciencia {E.PATIENCE}, 10% de validacion",
         "divergencia": "decision propia"},
        {"aspecto": "recorte de gradiente", "GNNWR publicado (Du et al. 2020)": "no especificado",
         "implementacion evaluada": f"norma maxima {E.GRAD_CLIP}", "divergencia": "decision propia"},
        {"aspecto": "distancia (SANNWR)", "GNNWR publicado (Du et al. 2020)": "Ni et al. 2022: integracion aprendida de proximidad espacial y atributiva (SAPDNN)",
         "implementacion evaluada": "combinacion lineal fija 0,5/0,5",
         "divergencia": "si -- motivo del rotulo SANNWR-adaptado; el diseno publicado se "
                        "implementa aparte como SANNWR-original y se corre en 02d"},
    ])
    dstd = salida("obs2", "divergencias_declaradas.csv")
    div.to_csv(dstd, index=False, encoding="utf-8")

    md = ["# Observacion 1.2 -- equivalencia estructural", "",
          "Comprobaciones sobre la implementacion propia (no requieren el paquete de referencia).", "",
          tabla_md(df[["codigo", "comprobacion", "obtenido", "estado"]]), "",
          "## Divergencias declaradas frente a la especificacion publicada", "",
          tabla_md(div), "",
          "Lectura: las comprobaciones E1-E5 establecen que la implementacion realiza la",
          "operacion que define a GNNWR. No establecen equivalencia numerica con el paquete",
          "de los autores, que depende ademas del escalado, del optimizador y de la parada;",
          "esa comparacion es la de 02a/02c. Mientras no se cierre, lo defendible es escribir",
          "\"la implementacion de GNNWR evaluada aqui\" y no \"GNNWR\" a secas.", ""]
    dstm = salida("obs2", "equivalencia_estructural.md")
    dstm.write_text("\n".join(md), encoding="utf-8")

    n_falla = int((df["estado"] == "FALLA").sum())
    pr(f"\n[csv] {dst}\n[csv] {dstd}\n[md]  {dstm}")
    pr(f"comprobaciones que fallan: {n_falla}")
    return 1 if n_falla else 0


if __name__ == "__main__":
    raise SystemExit(main())
