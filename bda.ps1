<#
  bda.ps1 - Atajos del proyecto Big Data Aplicado (Puerto de Huelva) para Windows.

  Uso:  .\bda.ps1 <orden> [argumentos]
  Si Windows bloquea el script la primera vez, ejecutad UNA vez en PowerShell:
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

  Órdenes:
    construir              Construye la imagen de Spark/Jupyter (la primera vez tarda ~5-10 min)
    iniciar [perfil]       Arranca el núcleo. Perfiles: monitor | bi | todo
    parar                  Detiene los contenedores (conserva HDFS)
    estado                 Contenedores en marcha y direcciones web
    datos [escala]         Genera los datos simulados (escala por defecto 1)
    ingesta                Copia los datos generados a HDFS (/puerto/raw)
    verificar              Comprueba SHA-256 de HDFS contra el manifiesto
    hdfs <args>            Ejecuta un comando hdfs en el NameNode (ej: .\bda.ps1 hdfs dfs -ls /puerto)
    escalar <serv> <n>     Cambia el número de réplicas (ej: .\bda.ps1 escalar datanode 4)
    consola <servicio>     Abre una consola bash dentro de un contenedor
    logs <servicio>        Últimas líneas del registro de un servicio
    reset                  Borra los contenedores (¡se pierde HDFS!) y conserva volúmenes
    reset-bi               Borra además la base de datos PostgreSQL y Superset
    urls                   Muestra las direcciones web
#>
# Sin [CmdletBinding]: así los argumentos tipo "-ls" o "-put" llegan intactos a hdfs.
param([string]$Orden = "ayuda")
$Resto = $args

$ErrorActionPreference = "Continue"   # los comandos docker informan de sus propios errores
Set-Location -Path $PSScriptRoot
$Imagen = "bda-puerto/spark:3.5.8"
$TodosPerfiles = @("--profile", "monitor", "--profile", "bi")

function Mostrar-Urls {
    Write-Host ""
    Write-Host "  HDFS NameNode ...... http://localhost:9870" -ForegroundColor Cyan
    Write-Host "  Spark master ....... http://localhost:8080" -ForegroundColor Cyan
    Write-Host "  JupyterLab ......... http://localhost:8888" -ForegroundColor Cyan
    Write-Host "  Spark (aplicación) . http://localhost:4040  (solo con una SparkSession abierta)" -ForegroundColor Cyan
    Write-Host "  Prometheus ......... http://localhost:9090  (perfil monitor)" -ForegroundColor DarkCyan
    Write-Host "  Grafana ............ http://localhost:3000  admin / bda2027 (perfil monitor)" -ForegroundColor DarkCyan
    Write-Host "  Superset ........... http://localhost:8088  admin / bda2027 (perfil bi)" -ForegroundColor DarkCyan
    Write-Host "  PostgreSQL ......... localhost:5432  bda / bda2027, BD puerto_dw (perfil bi)" -ForegroundColor DarkCyan
    Write-Host ""
}

function Comprobar-Docker {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker no responde. Abrid Docker Desktop y esperad a que diga 'Engine running'." -ForegroundColor Red
        exit 1
    }
}

function Construir-SiFalta {
    docker image inspect $Imagen *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ">> La imagen $Imagen no existe todavía: construyéndola (solo la primera vez)..." -ForegroundColor Yellow
        docker compose build spark-master
        if ($LASTEXITCODE -ne 0) { Write-Host "Falló la construcción de la imagen." -ForegroundColor Red; exit 1 }
    }
}

switch ($Orden.ToLower()) {
    "construir" {
        Comprobar-Docker
        docker compose build spark-master
    }
    "iniciar" {
        Comprobar-Docker
        Construir-SiFalta
        $perfil = if ($Resto) { $Resto[0].ToLower() } else { "" }
        switch ($perfil) {
            ""        { docker compose up -d }
            "monitor" { docker compose --profile monitor up -d }
            "bi"      { docker compose --profile bi up -d }
            "todo"    { docker compose @TodosPerfiles up -d }
            default   { Write-Host "Perfil desconocido: $perfil (usad monitor, bi o todo)" -ForegroundColor Red; exit 1 }
        }
        Write-Host ">> Arrancando. El NameNode tarda ~30 s en estar listo." -ForegroundColor Green
        Mostrar-Urls
    }
    "parar" {
        docker compose @TodosPerfiles stop
    }
    "estado" {
        docker compose @TodosPerfiles ps --format "table {{.Service}}\t{{.Name}}\t{{.Status}}"
        Mostrar-Urls
    }
    "datos" {
        $escala = if ($Resto) { $Resto[0] } else { "1" }
        docker compose exec jupyter python3 /datos/generador/generar_datos.py --escala $escala
    }
    "ingesta" {
        docker compose exec namenode bash /scripts/ingesta.sh
    }
    "verificar" {
        docker compose exec namenode bash /scripts/verificar_manifiesto.sh
    }
    "hdfs" {
        docker compose exec namenode hdfs @Resto
    }
    "escalar" {
        if (-not $Resto -or $Resto.Count -lt 2) { Write-Host "Uso: .\bda.ps1 escalar <datanode|spark-worker> <n>"; exit 1 }
        $servicio = $Resto[0]; $n = $Resto[1]
        docker compose up -d --no-recreate --scale "$servicio=$n" $servicio
        docker compose ps $servicio
    }
    "consola" {
        $servicio = if ($Resto) { $Resto[0] } else { "namenode" }
        docker compose @TodosPerfiles exec $servicio bash
    }
    "logs" {
        $servicio = if ($Resto) { $Resto[0] } else { "namenode" }
        docker compose @TodosPerfiles logs --tail 80 $servicio
    }
    "reset" {
        $ok = Read-Host "Se borrarán los contenedores y TODO el contenido de HDFS. ¿Seguro? (s/n)"
        if ($ok -eq "s") { docker compose @TodosPerfiles down --remove-orphans }
    }
    "reset-bi" {
        $ok = Read-Host "Se borrarán contenedores, PostgreSQL, Superset, Grafana y Prometheus. ¿Seguro? (s/n)"
        if ($ok -eq "s") { docker compose @TodosPerfiles down -v --remove-orphans }
    }
    "urls" { Mostrar-Urls }
    default {
        $inicio = (Get-Content $PSCommandPath -Encoding UTF8 | Select-String -Pattern "^<#" | Select-Object -First 1).LineNumber
        $fin = (Get-Content $PSCommandPath -Encoding UTF8 | Select-String -Pattern "^#>" | Select-Object -First 1).LineNumber
        Get-Content $PSCommandPath -Encoding UTF8 | Select-Object -Skip $inicio -First ($fin - $inicio - 1) | Write-Host
        Write-Host "Primeros pasos:  .\bda.ps1 iniciar   ->   .\bda.ps1 datos   ->   .\bda.ps1 ingesta" -ForegroundColor Green
    }
}
