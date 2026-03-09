@echo off
setlocal enabledelayedexpansion

REM Build thorvg for Windows (x86_64 and arm64)
REM Requires: meson, ninja, and a C++ compiler (MSVC via VS Developer Prompt)
REM Usage:    build_windows.bat <thorvg_source_dir> [arch]
REM           arch = x64 (default), arm64, or all

set ROOT_DIR=%~1
cd /d "%ROOT_DIR%"
set ROOT_DIR=%CD%\
set BUILD_ROOT=%ROOT_DIR%build_windows
set OUTPUT_DIR=%ROOT_DIR%output

REM Remove Strawberry Perl from PATH — its ccache intercepts cl.exe
set "PATH=%PATH:C:\Strawberry\c\bin;=%"
set "PATH=%PATH:C:\Strawberry\perl\site\bin;=%"
set "PATH=%PATH:C:\Strawberry\perl\bin;=%"

set MESON_COMMON=--vsenv --buildtype=release --default-library=static -Dthreads=true -Dbindings=capi -Dloaders=svg,lottie,ttf -Dextra=lottie_exp

set ARCH=%2
if "%ARCH%"=="" set ARCH=x64

echo === ThorVG Windows Build ===
echo Root: %ROOT_DIR%
echo Arch: %ARCH%
echo.

if "%ARCH%"=="all" (
    call :build_arch x64
    if errorlevel 1 goto :fail
    call :build_arch arm64
    if errorlevel 1 goto :fail
    goto :done
)

call :build_arch %ARCH%
if errorlevel 1 goto :fail
goto :done

REM ---------- build function ----------
:build_arch
set _ARCH=%~1
set _BUILD_DIR=%BUILD_ROOT%\%_ARCH%
set _OUT_DIR=%OUTPUT_DIR%\windows_%_ARCH%

echo ^>^>^> Building: windows_%_ARCH%

if exist "%_BUILD_DIR%" rmdir /s /q "%_BUILD_DIR%"
mkdir "%_BUILD_DIR%"

if "%_ARCH%"=="arm64" (
    meson setup "%_BUILD_DIR%" %MESON_COMMON% --cross-file "%ROOT_DIR%cross\windows_arm64.txt"
) else (
    meson setup "%_BUILD_DIR%" %MESON_COMMON%
)
if errorlevel 1 (
    echo FAILED: meson setup for %_ARCH%
    exit /b 1
)

meson compile -C "%_BUILD_DIR%"
if errorlevel 1 (
    echo FAILED: meson compile for %_ARCH%
    exit /b 1
)

if not exist "%_OUT_DIR%" mkdir "%_OUT_DIR%"
copy /y "%_BUILD_DIR%\src\libthorvg-1.a" "%_OUT_DIR%\thorvg.lib" >nul 2>&1
if not exist "%_OUT_DIR%\thorvg.lib" (
    REM meson/ninja may produce .lib directly on MSVC
    copy /y "%_BUILD_DIR%\src\thorvg-1.lib" "%_OUT_DIR%\thorvg.lib" >nul 2>&1
)
if not exist "%_OUT_DIR%\thorvg.lib" (
    echo WARNING: Could not find static library output. Check %_BUILD_DIR%\src\
    dir "%_BUILD_DIR%\src\*.lib" "%_BUILD_DIR%\src\*.a" 2>nul
)

echo ^<^<^< Done: windows_%_ARCH%
echo.
exit /b 0

:done
echo.
echo === Build Complete ===
echo Output: %OUTPUT_DIR%
if exist "%OUTPUT_DIR%\windows_x64\thorvg.lib" echo   x64:   %OUTPUT_DIR%\windows_x64\thorvg.lib
if exist "%OUTPUT_DIR%\windows_arm64\thorvg.lib" echo   arm64: %OUTPUT_DIR%\windows_arm64\thorvg.lib
exit /b 0

:fail
echo.
echo === Build FAILED ===
exit /b 1
