@echo off
echo ========================================================
echo   SUBIDA AUTOMATICA A HUGGING FACE
echo ========================================================
echo.
echo 1. Ve a tu Space en Hugging Face.
echo 2. Copia la URL del navegador (ej: https://huggingface.co/spaces/Juan/Godtrack)
echo 3. Si te pide usuario/contrasena, usalos.
echo.

set /p space_url="Pega la URL del Space aqui: "

echo.
echo === LIMPIANDO HISTORIAL CORRUPTO ===
if exist .git (
    attrib -h .git
    rmdir /s /q .git
)
echo.
echo Inicializando Git limpio...
git init
echo Agregando archivos (ignora los prohibidos)...
git add .
echo.
echo Guardando cambios...
git commit -m "Subida automatica V8"
echo.
echo Forzando rama MAIN...
git branch -M main
echo.
echo Conectando con Hugging Face...
git remote remove space 2>nul
git remote add space %space_url%
echo.
echo SUBIENDO... (Esto puede tardar unos segundos)
git push --force space main

echo.
echo ========================================================
echo   SI NO HUBO ERRORES ROJOS, YA ESTA LISTO.
echo   Revisa la pestana "App" en Hugging Face en 2 minutos.
echo ========================================================
pause
