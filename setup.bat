@echo off
echo Setting up Python environment...

:: Remove existing virtual environment
rmdir /s /q venv
rmdir /s /q .venv

:: Create new virtual environment
python -m venv .venv

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Run the follow-up script
python setup_env.py

:: Deactivate virtual environment
deactivate 