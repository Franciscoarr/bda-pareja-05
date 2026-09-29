# Instalación del entorno (Windows 10/11)

Tiempo aproximado: 45 minutos la primera vez (depende de la conexión). Hacedlo **en el PC en el que vais a trabajar**
(aula o casa). Si en el aula no tenéis permisos de administrador, el profesor ya lo habrá dejado instalado: empezad en el paso 6.

## 1. Comprobar la virtualización
Administrador de tareas → **Rendimiento** → **CPU** → «Virtualización: **Habilitada**».
Si pone «Deshabilitada», hay que activarla en la BIOS/UEFI (Intel VT-x / AMD-V o SVM). Pedid ayuda si no sabéis.

## 2. WSL 2
PowerShell **como administrador**:
```powershell
wsl --install
wsl --update
```
Reiniciad el PC si lo pide.

## 3. Docker Desktop
1. Descargad Docker Desktop para Windows desde la web oficial de Docker e instaladlo marcando **Use WSL 2**.
2. Abridlo y esperad a que abajo a la izquierda ponga **Engine running**. No hace falta iniciar sesión.
3. Comprobad en PowerShell: `docker version` y `docker compose version`.

## 4. Limitar la memoria de Docker (importante con 16 GB)
Cread el fichero `C:\Users\<vuestro_usuario>\.wslconfig` (sin extensión) con:
```ini
[wsl2]
memory=10GB
processors=4
swap=4GB
```
y aplicadlo: `wsl --shutdown` y volved a abrir Docker Desktop. Con 8 GB de RAM poned `memory=6GB` y usad
`.\bda.ps1 datos 0.3`.

## 5. Git y Visual Studio Code
1. Instalad **Git for Windows** (opciones por defecto) y **Visual Studio Code** (con las extensiones *Python*, *Jupyter*,
   *Docker* y *Markdown All in One*).
2. Configurad Git una vez:
```powershell
git config --global user.name "Nombre Apellido"
git config --global user.email "vuestro-correo@ejemplo.com"
```

## 6. Cuenta de GitHub y repositorio de la pareja
1. Si no tenéis cuenta, cread una en github.com (vale una personal). **Mandad vuestro usuario** al profesor por Moodle
   (actividad «Usuario de GitHub»).
2. Cuando el profesor cree el repositorio de vuestra pareja, os llegará un **correo de invitación**: aceptadla.
3. Clonad el repositorio en una carpeta **sin espacios y fuera de OneDrive**:
```powershell
mkdir C:\bda; cd C:\bda
git clone https://github.com/<organizacion>/<repo-de-vuestra-pareja>.git
cd <repo-de-vuestra-pareja>
```
La primera vez que hagáis `git push`, se abrirá el navegador para iniciar sesión en GitHub.

## 7. Permitir los scripts de PowerShell (una sola vez)
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 8. Primer arranque
```powershell
.\bda.ps1 iniciar      # 5-10 min la primera vez (descarga ~3 GB y construye la imagen de Spark)
.\bda.ps1 estado       # todos los servicios deben estar «Up»
.\bda.ps1 datos
.\bda.ps1 ingesta
```
Abrid http://localhost:8888 y ejecutad `notebooks/00_comprobar_entorno.ipynb`.

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `docker: command not found` o «Docker no responde» | Abrid Docker Desktop y esperad a *Engine running* |
| `No se puede cargar el archivo bda.ps1` | Paso 7 |
| El PC se queda sin memoria | Paso 4; parad perfiles que no uséis (`.\bda.ps1 parar` y arrancad solo lo necesario) |
| `port is already allocated` | Otro programa usa el puerto (p. ej. un PostgreSQL local). Cerradlo o cambiad el puerto en `docker-compose.yml` |
| `/bin/bash^M: bad interpreter` | Habéis copiado los ficheros sin Git. Clonad con Git (el `.gitattributes` lo evita) |
| La construcción de la imagen falla descargando | Red del aula saturada: repetid `.\bda.ps1 construir` |
| Todo iba bien y ahora no arranca | `.\bda.ps1 logs namenode` y buscad `ERROR`; como último recurso `.\bda.ps1 reset` + `iniciar` + `ingesta` |
