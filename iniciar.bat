@echo off
title Inicializador - Shopee Extractor ^& Organizer
echo ===================================================
echo   Inicializando Shopee Extractor ^& Organizer...
echo ===================================================
echo.

:: Verifica se a pasta do ambiente virtual existe
if not exist .venv (
    echo [ERRO] Pasta .venv nao encontrada!
    echo Por favor, certifique-se de que o ambiente virtual esta configurado.
    pause
    exit /b
)

:: Ativa o ambiente virtual
echo [1/2] Ativando ambiente virtual (.venv)...
call .venv\Scripts\activate

:: Inicia a aplicação desktop python
echo [2/2] Abrindo a interface desktop...
echo.
echo ===================================================
echo   [OK] Aplicativo rodando!
echo   Para fechar, feche a janela principal do programa.
echo ===================================================
echo.

python main.py
pause
