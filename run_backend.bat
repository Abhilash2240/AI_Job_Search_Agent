@echo off
title AI Job Search Agent - Backend Service
echo ==============================================================================
echo Starting AI Job Search Agent Backend API
echo ==============================================================================

set PYTHONPATH=%cd%\backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause

