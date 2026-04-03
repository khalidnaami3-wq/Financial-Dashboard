@echo off
setlocal

:: Check if venv exists
if not exist "venv\Scripts\activate" (
    echo [ERROR] Virtual environment not found. Please run 'python -m venv venv' first.
    pause
    exit /b
)

:: Activate venv and run streamlit
echo [INFO] Activating virtual environment...
call venv\Scripts\activate

echo [INFO] Starting Streamlit Application...
python -m streamlit run main.py

pause
