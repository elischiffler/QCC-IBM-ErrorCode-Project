# QCC-Club: Project

This project runs randomized benchmarking (RB) experiments using Qiskit + IBM Quantum.

## Get the code

Download this folder as a ZIP (or clone it) and open a terminal in the project directory.

## Setup

### macOS / Linux

```bash
cd "/path/to/QCC-Club"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
cd "C:\\path\\to\\QCC-Club"
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

## Running on test mode:
```bash
export QCC_TEST_MODE=1
export QCC_NOISE=1
python MasterScript.py
```

## IBM Quantum token

The script uses your IBM Quantum API token to log in.

**Set an environment variable** so you won't have to paste it every time.

### macOS / Linux

```bash
export IBM_QUANTUM_TOKEN="PASTE_YOUR_TOKEN_HERE"
```

### Windows (PowerShell)

```powershell
setx IBM_QUANTUM_TOKEN "PASTE_YOUR_TOKEN_HERE"
```

Close and reopen your terminal after `setx` on Windows.


## Run

### macOS / Linux

Make sure your virtual environment is activated (you should see `(.venv)` in your terminal), then run:

```bash
python MasterScript.py
```

### Windows (PowerShell)

Make sure your virtual environment is activated, then run:

```powershell
py .\MasterScript.py
```

## Notes

- If you did **not** set `IBM_QUANTUM_TOKEN`, the program will prompt you to paste your token (input hidden).
- If you see `ModuleNotFoundError`, re-run:

```bash
python -m pip install -r requirements.txt
```