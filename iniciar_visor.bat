@echo off
chcp 65001 > nul
title Clasificador de Palta Hass - Servidor Local

echo ======================================================================
echo    INICIANDO CLASIFICADOR VISUAL DE PALTA HASS (TESIS ROÑA)
echo ======================================================================
echo.
echo 1. Verificando inventario...
if not exist "data\inventory.json" (
    echo [INFO] No se encontro inventario. Generando por primera vez...
    python generar_inventario.py
)

echo 2. Iniciando servidor en http://127.0.0.1:5000/ ...
echo.
echo [INFO] Abre tu navegador web en: http://127.0.0.1:5000/
echo [INFO] Para detener el servidor presiona Ctrl + C en esta ventana.
echo ======================================================================
echo.

python app.py

pause
