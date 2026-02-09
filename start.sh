#!/bin/bash

echo "========================================"
echo "  RedNote Remix - Starting..."
echo "========================================"
echo

echo "[1/3] Checking dependencies..."
pip show streamlit > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo
echo "[2/3] Checking Playwright browser..."
playwright install chromium

echo
echo "[3/3] Starting Streamlit app..."
echo
echo "App will open in your browser: http://localhost:8501"
echo "Press Ctrl+C to stop the server"
echo
streamlit run app.py
