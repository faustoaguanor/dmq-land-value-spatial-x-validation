# Guia de RunPod, paso a paso

Todo lo que necesita GPU va al pod. Lo tabular (OLS, GWR, Random Forest, HGB,
el ajuste de hiperparametros, el n efectivo y la importancia) se corre en el
portatil, gratis, ANTES de alquilar nada.

---

## Paso 0. En el portatil, antes de gastar un peso

```powershell
cd <ruta-local>\revision_metodologica
.\run_all.ps1 -Correcciones
```

Cinco o seis horas. Cuando termine, empaqueta llevandote lo ya calculado:

```powershell
python empaquetar_para_pod.py --con-salidas
```

Eso escribe `revision_pod.zip` (unos 3 MB) con los datos, el codigo y los
resultados que ya tienes. El pod los encontrara hechos y no los repetira.

---

## Paso 1. Crear el pod

- GPU: **RTX 4090**.
- Plantilla: una de **PyTorch** con CUDA 12.x (trae torch instalado; el guion de
  instalacion lo detecta y no lo descarga otra vez).
- Container disk: **20 GB** basta.
- Volumen de red: no hace falta. Todo lo que se produce cabe en unos pocos MB.

---

## Paso 2. Subir el zip

La forma facil, para 3 MB: **Connect -> HTTP Service (puerto 8888)**, que abre
JupyterLab, y arrastras `revision_pod.zip` a `/workspace`.

Alternativa sin navegador, con `runpodctl` (viene instalado en el pod):

```powershell
runpodctl send revision_pod.zip        # en tu portatil, imprime un codigo
```
```bash
runpodctl receive <codigo>             # en el pod
```

---

## Paso 3. Instalar y comprobar

En la terminal del pod:

```bash
cd /workspace
python -c "import zipfile; zipfile.ZipFile('revision_pod.zip').extractall('.')"
cd replicacion/revision_metodologica
bash setup_pod.sh
```

Se descomprime con Python a proposito: muchas imagenes de pod no traen `unzip`
instalado, y Python siempre esta. Si prefieres la herramienta clasica,
`apt-get update && apt-get install -y unzip zip` la instala en un minuto.

`setup_pod.sh` instala lo que falte y corre la verificacion: compara las huellas
SHA-256 de los tres archivos de datos, comprueba que hay 5051 predios, 4040 de
entrenamiento y 1011 de prueba, y que la GPU responde. Si algo no cuadra, para
ahi y avisa.

---

## Paso 4. La prueba de 10 minutos antes de comprometerte

```bash
python obs4_imputacion/04b_protocolo_en_fold.py --brazos global \
       --esquemas ConjuntoDePrueba20 --modelos GNNWR
```

Tiene que dar un **RMSE entre 94 y 102**. Tu GNNWR publicado es 98,08 con una
desviacion de 3,56 sobre diez semillas; aqui la semilla es otra, asi que basta
con que caiga en ese rango. Si cae fuera, para y revisa antes de seguir.

Coste de esta comprobacion: unos 15 centavos.

---

## Paso 5. Lanzar el trabajo largo

Primero, tmux, para que no se muera si se cae el navegador:

```bash
tmux new -s tesis
```

Dentro de tmux, en secuencia:

```bash
bash run_all.sh --solo-redes
```

O, para aprovechar que la GPU se queda a medias con lotes tan pequenos, en tres
ventanas paralelas (dentro de tmux: Ctrl+B y luego C abre una ventana nueva,
Ctrl+B y un numero cambia entre ellas):

```bash
# ventana 1
python obs2_equivalencia_gnnwr/02d_sannwr_original.py 2>&1 | tee registros/02d.log
# ventana 2
python obs4_imputacion/04b_protocolo_en_fold.py \
       --modelos GNNWR SANNWR-adaptado SANNWR-original 2>&1 | tee registros/04b.log
```

Dos procesos usan menos de 2 GB de los 24 y caben de sobra en 8 vCPU. Corriendo
en paralelo el reloj de pared baja casi a la mitad.

Para salir dejandolo corriendo: **Ctrl+B, sueltas, y luego D**.
Para volver: `tmux attach -t tesis`.

---

## Paso 6. Mientras corre

```bash
tail -f registros/04b.log            # ver un registro en vivo (Ctrl+C para salir)
ls salidas/obs4/parciales | wc -l    # cuantas combinaciones llevan hechas
nvidia-smi                           # comprobar que la GPU esta trabajando
```

Si el pod se cae o lo paras, no pierdes nada mas que el entrenamiento en curso:
al relanzar el mismo comando continua donde iba.

---

## Paso 7. El informe que lo reune todo

```bash
python 99_informe_revision.py
```

---

## Paso 8. Traerte los resultados ANTES de terminar el pod

```bash
cd /workspace/replicacion/revision_metodologica
tar -czf salidas.tar.gz salidas registros
```

`tar` viene en todas las imagenes; `zip` a menudo no. En Windows, 7-Zip o el
propio Explorador abren el .tar.gz sin problema. Si prefieres un zip:

```bash
python -c "import shutil; shutil.make_archive('salidas','zip','.','salidas')"
```

Lo bajas arrastrandolo desde JupyterLab, o con `runpodctl send salidas.tar.gz`
desde el pod y `runpodctl receive <codigo>` en tu portatil.

En el portatil, descomprimelo encima de `revision_metodologica/`: el pod traia lo
tuyo, asi que su `salidas/` es un superconjunto y puedes reemplazar sin miedo.

**Solo entonces** termina el pod. El disco desaparece con el.

---

## Resumen del gasto

| Bloque | Entrenamientos | 4090 |
|---|---|---|
| 02d, SANNWR original frente a adaptado | 70 | 7,5 h |
| 04b, 3 redes x 16 particiones x 2 brazos | 96 | 10 h |
| 02a, paquete GNNWR de referencia | 6 | 45 min |

En serie son unas 18 h ($13). En dos ventanas paralelas, unas 10 h de reloj
de pared, y el coste baja en proporcion.
