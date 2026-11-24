@echo off
cd /d "%~dp0"
echo ================================================
echo   Smart Waste Management - Gemini AI
echo ================================================
echo.
echo Installing or checking required Python packages...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Package installation failed. Check Python and your internet connection.
    pause
    exit /b 1
)
echo.
echo Starting the Streamlit website...
python -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo The app stopped with an error. Read the message above.
    pause
)
