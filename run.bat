@echo off
setlocal enabledelayedexpansion
title DevStudio Pro — Demarrage
cd /d "%~dp0"

echo.
echo  =====================================================
echo    DevStudio Pro  ^|  IDE Python + Builder Minecraft
echo  =====================================================
echo.

:: ── Chemins ──────────────────────────────────────────────────────────────────
set "APP_DIR=%USERPROFILE%\AppData\Roaming\FFS\DevStudio"
set "VENV_DIR=%APP_DIR%\.venv"
set "APP_FILE=%APP_DIR%\DevStudioPro.pyw"
set "SRC_FILE=%~dp0DevStudioPro.pyw"
set "PYTHONW=%VENV_DIR%\Scripts\pythonw.exe"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"

echo [INFO] Installation : %APP_DIR%

:: ── 1. Python ────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable dans le PATH.
    echo  Telechargez Python 3.10+ sur https://python.org
    echo  Cochez "Add Python to PATH" lors de l'installation.
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do set PY_VER=%%V
echo [OK] Python %PY_VER% detecte.

:: ── 2. Dossier ───────────────────────────────────────────────────────────────
if not exist "%APP_DIR%\" (
    mkdir "%APP_DIR%"
    if errorlevel 1 ( echo [ERREUR] Impossible de creer %APP_DIR% & pause & exit /b 1 )
    echo [OK] Dossier cree.
)

:: ── 3. Source .pyw present ? ─────────────────────────────────────────────────
if not exist "%SRC_FILE%" (
    echo [ERREUR] DevStudioPro.pyw introuvable a cote de run.bat
    echo  Chemin cherche : %SRC_FILE%
    pause & exit /b 1
)

:: ── 4. Copier / mettre a jour ─────────────────────────────────────────────────
if not exist "%APP_FILE%" (
    copy /Y "%SRC_FILE%" "%APP_FILE%" >nul
    echo [OK] DevStudioPro.pyw installe.
) else (
    robocopy "%~dp0." "%APP_DIR%" "DevStudioPro.pyw" /XO /NJH /NJS /NS /NC >nul 2>&1
    if !errorlevel! EQU 1 ( echo [INFO] DevStudioPro.pyw mis a jour. ) else ( echo [OK] DevStudioPro.pyw a jour. )
)

:: ── 5. Venv ───────────────────────────────────────────────────────────────────
if not exist "%VENV_DIR%\" (
    echo [1/3] Creation du venv...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 ( echo [ERREUR] Echec creation venv. & pause & exit /b 1 )
    echo [1/3] Venv cree.
) else (
    echo [1/3] Venv OK.
)

:: ── 6. PyQt6 ─────────────────────────────────────────────────────────────────
echo [2/3] Verification PyQt6...
"%PYTHON%" -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo [2/3] Installation de PyQt6 (premiere fois, patientez)...
    "%VENV_DIR%\Scripts\pip.exe" install --upgrade PyQt6 --quiet
    if errorlevel 1 ( echo [ERREUR] Echec installation PyQt6. & pause & exit /b 1 )
    echo [2/3] PyQt6 installe.
) else (
    echo [2/3] PyQt6 OK.
)

:: ── 7. Lancement ──────────────────────────────────────────────────────────────
:: On utilise pythonw.exe directement (chemin absolu dans le venv).
:: PAS de "start" ni de "deactivate" avant : pythonw doit garder le venv actif.
echo [3/3] Lancement (mode sans console)...
echo.
cd /d "%APP_DIR%"

"%PYTHONW%" "%APP_FILE%" %*

:: Si pythonw retourne une erreur ou ne trouve pas la fenetre, on repasse en mode console
if errorlevel 1 (
    echo.
    echo [!] Erreur detectee — relance en mode console pour diagnostic...
    echo.
    "%PYTHON%" "%APP_FILE%" %*
    echo.
    pause
)

endlocal
