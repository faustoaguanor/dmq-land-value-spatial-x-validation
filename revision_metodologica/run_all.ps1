# run_all.ps1 -- ejecucion local en Windows (PowerShell).
#
#   .\run_all.ps1                  # solo lo instantaneo (minutos)
#   .\run_all.ps1 -Correcciones    # todo lo que NO es red neuronal: unas 5-6 h
#   .\run_all.ps1 -Redes           # anade las redes: unos cinco dias en esta maquina
#   .\run_all.ps1 -Correcciones -Rapido   # prueba de humo, cifras NO reportables
#   .\run_all.ps1 -ConForma        # anade las auditorias de forma del documento

param(
    [switch]$Correcciones,
    [switch]$Redes,
    [switch]$Rapido,
    [switch]$ConForma
)

$ErrorActionPreference = "Continue"
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $aqui
$py = Join-Path (Split-Path -Parent $aqui) ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$env:PYTHONIOENCODING = "utf-8"
$rap = if ($Rapido) { @("--rapido") } else { @() }
$tabulares = @("OLS", "GWR", "RF")
$redes = @("GNNWR", "SANNWR-adaptado", "SANNWR-original")

function Paso($titulo, $argumentos) {
    Write-Host ""
    Write-Host "=== $titulo ===" -ForegroundColor Cyan
    $t0 = Get-Date
    & $py @argumentos
    Write-Host ("  ({0:n1} min)" -f ((Get-Date) - $t0).TotalMinutes) -ForegroundColor DarkGray
}

# -- instantaneo -------------------------------------------------------------
Paso "entorno"                        @("00_verificar_entorno.py")
Paso "mascara de imputacion"          @("obs4_imputacion\04a_mascara_imputacion.py")
Paso "equivalencia estructural"       @("obs2_equivalencia_gnnwr\02b_equivalencia_estructural.py")
Paso "tamano efectivo de la muestra"  @("obs6_n_efectivo\06_tamano_efectivo.py")

if ($ConForma) {
    Paso "forma: nomenclatura" @("obs1_nomenclatura\01_auditar_nomenclatura.py", "--emitir-parches")
    Paso "forma: fichas"       @("obs5_homogeneidad\05_fichas_implementacion.py")
}

# -- correcciones sin GPU ----------------------------------------------------
if ($Correcciones -or $Redes) {
    Paso "ajuste de hiperparametros (RF y HGB)" (@("obs5_homogeneidad\05b_ajuste_hiperparametros.py"))
    Paso "imputacion en pliegue (tabulares)" (@("obs4_imputacion\04b_protocolo_en_fold.py", "--modelos") + $tabulares + $rap)
}

# -- redes -------------------------------------------------------------------
if ($Redes) {
    Write-Host ""
    Write-Host "Las redes tardan cerca de una hora por entrenamiento en esta maquina." -ForegroundColor Yellow
    Write-Host "Son unas 110 h en total. En una RTX 4090 son 12-15 h." -ForegroundColor Yellow
    Paso "SANNWR publicado frente a adaptado" (@("obs2_equivalencia_gnnwr\02d_sannwr_original.py") + $rap)
    Paso "imputacion en pliegue (redes)" (@("obs4_imputacion\04b_protocolo_en_fold.py", "--modelos", "GNNWR", "SANNWR-adaptado") + $rap)
}

Paso "informe" @("99_informe_revision.py")

Write-Host ""
Write-Host "salidas en: $aqui\salidas" -ForegroundColor Green
