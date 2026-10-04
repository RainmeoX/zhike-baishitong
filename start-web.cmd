@echo off
cd /d "%~dp0"
"C:\Users\Rainmeo\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
