# Set execution policy for this process
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Remove existing virtual environments
Remove-Item -Path venv -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path .venv -Recurse -Force -ErrorAction SilentlyContinue

# Create new virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run the follow-up script
python setup_env.py

# Deactivate virtual environment
deactivate 