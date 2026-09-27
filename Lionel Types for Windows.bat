@echo off
rem Double-click to start Lionel Types.
rem The first run sets things up, which needs Python 3 and an internet connection.
setlocal
cd /d "%~dp0"
set "VENV=.venv"

if not exist "%VENV%\Scripts\pythonw.exe" (
    echo Setting up Lionel Types for the first time...
    py -3 -m venv "%VENV%" 2>nul || python -m venv "%VENV%"
)
if not exist "%VENV%\Scripts\pythonw.exe" (
    echo.
    echo Lionel Types needs Python 3. Get it from https://www.python.org/downloads/
    pause
    exit /b 1
)

fc /b requirements.txt "%VENV%\installed-requirements.txt" >nul 2>&1 || (
    "%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || (
        echo.
        echo Could not install what Lionel Types needs. Check the internet connection and try again.
        pause
        exit /b 1
    )
    copy /y requirements.txt "%VENV%\installed-requirements.txt" >nul
)

start "" "%VENV%\Scripts\pythonw.exe" -m lionel_types %*
