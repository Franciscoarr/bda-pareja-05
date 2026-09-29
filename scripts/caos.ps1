<#
  caos.ps1 - Pruebas de estabilidad (fase 4): para y vuelve a arrancar contenedores al azar
  y deja un registro en entregas\F4\caos_registro.csv.

  Uso (en OTRA ventana de PowerShell, desde la carpeta del repositorio):
     .\scripts\caos.ps1 -Minutos 30 -PausaMin 60 -PausaMax 180

  Solo afecta a DataNodes y workers de Spark (nunca al NameNode ni a Prometheus).
#>
param(
    [int]$Minutos = 30,
    [int]$PausaMin = 60,     # segundos entre fallos (mínimo)
    [int]$PausaMax = 180,    # segundos entre fallos (máximo)
    [int]$Caida = 120        # segundos que el contenedor permanece parado
)
Set-Location -Path (Join-Path $PSScriptRoot "..")
$registro = "entregas\F4\caos_registro.csv"
New-Item -ItemType Directory -Force -Path "entregas\F4" | Out-Null
if (-not (Test-Path $registro)) { "momento,accion,contenedor" | Out-File -FilePath $registro -Encoding utf8 }

$victimas = docker ps --format "{{.Names}}" | Where-Object { $_ -match "bda-puerto-(datanode|spark-worker)-\d+" }
if (-not $victimas) { Write-Host "No hay DataNodes ni workers en marcha." -ForegroundColor Red; exit 1 }
Write-Host "Posibles víctimas: $($victimas -join ', ')" -ForegroundColor Yellow

$fin = (Get-Date).AddMinutes($Minutos)
while ((Get-Date) -lt $fin) {
    Start-Sleep -Seconds (Get-Random -Minimum $PausaMin -Maximum $PausaMax)
    $v = Get-Random -InputObject $victimas
    $t = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "$t  PARO $v" -ForegroundColor Red
    docker stop $v | Out-Null
    "$t,parada,$v" | Out-File -FilePath $registro -Append -Encoding utf8
    Start-Sleep -Seconds $Caida
    $t = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "$t  ARRANCO $v" -ForegroundColor Green
    docker start $v | Out-Null
    "$t,arranque,$v" | Out-File -FilePath $registro -Append -Encoding utf8
}
Write-Host "Prueba de caos terminada. Registro en $registro"
