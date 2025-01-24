@echo off
title Analizador de Ordenanzas Fiscales
:: Cambiar al directorio donde está el script
cd /d "K:/Agente_000_Analiza_Documentacion"
:: Activar el entorno virtual
call venv\Scripts\activate
:: Ejecutar el script de Python
python main.py
:: Pausar para que no se cierre automáticamente
pause
