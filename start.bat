@echo off
chcp 65001 >nul
echo ========================================
echo   RedNote Remix - Starting...
echo ========================================
echo.

echo [1/3] Checking dependencies...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo [2/3] Checking Playwright browser...
playwright install chromium --with-deps

echo.
echo [3/3] Starting Streamlit app...
echo.
echo App will open in your browser: http://localhost:8501
echo Press Ctrl+C to stop the server
echo.
streamlit run app.py

pause
