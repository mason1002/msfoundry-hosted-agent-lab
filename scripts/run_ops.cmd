@echo off
setlocal EnableExtensions

set "ROOT=%~dp0.."
set "VENV=%ROOT%\.venv-local"
set "PYTHON=%VENV%\Scripts\python.exe"

where uv >nul 2>&1
if errorlevel 1 (
    echo uv is required: https://docs.astral.sh/uv/getting-started/installation/ 1>&2
    exit /b 1
)

if not exist "%PYTHON%" (
    uv venv "%VENV%" --python 3.13
    if errorlevel 1 exit /b 1
)

uv pip install --python "%PYTHON%" --prerelease allow -r "%ROOT%\requirements-ops.txt"
if errorlevel 1 exit /b 1

pushd "%ROOT%"
"%PYTHON%" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%