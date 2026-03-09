@echo off
setlocal enabledelayedexpansion

REM ---------------------------------------------------------------------------
REM  Prepare ThorVG C library for Windows wheel builds (cibuildwheel before-all).
REM
REM  Usage:  ci\prepare_thorvg_windows.bat <project_dir>
REM     e.g. ci\prepare_thorvg_windows.bat D:\a\thorvg-cython\thorvg-cython
REM ---------------------------------------------------------------------------

set "PROJECT=%~1"
if "%PROJECT%"=="" (
    echo ERROR: project directory not specified
    exit /b 1
)

echo === prepare_thorvg_windows ===
echo PROJECT = %PROJECT%

REM 1. Ensure meson + ninja are available
python -m pip install meson ninja
if errorlevel 1 (
    echo FAILED: pip install meson ninja
    exit /b 1
)

REM 2. Clone thorvg if not already present
set "THORVG_DIR=%PROJECT%\thorvg"
if not exist "%THORVG_DIR%\" (
    echo Cloning thorvg ...
    git clone https://github.com/psychowasp/thorvg.git "%THORVG_DIR%"
    if errorlevel 1 (
        echo FAILED: git clone
        exit /b 1
    )
) else (
    echo thorvg directory already exists, skipping clone.
)

REM 3. Verify the header we need
if not exist "%THORVG_DIR%\src\bindings\capi\thorvg_capi.h" (
    echo FAILED: thorvg_capi.h not found after clone!
    echo Expected: %THORVG_DIR%\src\bindings\capi\thorvg_capi.h
    dir "%THORVG_DIR%\src\bindings\capi\" 2>nul
    exit /b 1
)
echo Found thorvg_capi.h

REM 4. Build thorvg
echo Building thorvg ...
cd /d "%THORVG_DIR%"
if errorlevel 1 (
    echo FAILED: cd to %THORVG_DIR%
    exit /b 1
)
call build_windows.bat
if errorlevel 1 (
    echo FAILED: build_windows.bat
    exit /b 1
)

REM 5. Verify build output
if not exist "%THORVG_DIR%\output\windows_x64\thorvg.lib" (
    echo WARNING: thorvg.lib not found at expected location
    dir "%THORVG_DIR%\output\" /s 2>nul
)

echo === prepare_thorvg_windows DONE ===
exit /b 0
