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

REM 2. Download thorvg release if not already present
set "THORVG_DIR=%PROJECT%\thorvg"
set "THORVG_VERSION=1.0.1"
if not exist "%THORVG_DIR%\" (
    echo Downloading thorvg v%THORVG_VERSION% ...
    curl -sL https://github.com/thorvg/thorvg/archive/refs/tags/v%THORVG_VERSION%.tar.gz -o thorvg-src.tar.gz
    if errorlevel 1 (
        echo FAILED: curl download
        exit /b 1
    )
    tar xzf thorvg-src.tar.gz -C "%PROJECT%"
    if errorlevel 1 (
        echo FAILED: tar extract
        exit /b 1
    )
    move "%PROJECT%\thorvg-%THORVG_VERSION%" "%THORVG_DIR%"
    del thorvg-src.tar.gz
) else (
    echo thorvg directory already exists, skipping download.
)

REM 3. Verify the header we need
if not exist "%THORVG_DIR%\src\bindings\capi\thorvg_capi.h" (
    echo FAILED: thorvg_capi.h not found after download!
    echo Expected: %THORVG_DIR%\src\bindings\capi\thorvg_capi.h
    dir "%THORVG_DIR%\src\bindings\capi\" 2>nul
    exit /b 1
)
echo Found thorvg_capi.h

REM 4. Build thorvg
echo Building thorvg ...
call "%PROJECT%\tools\thorvg_scripts\build_windows.bat" "%THORVG_DIR%"
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
