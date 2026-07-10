$ErrorActionPreference = "Stop"

$pythonRoot = "C:\Users\Mr Helium\AppData\Local\Programs\Python\Python313"
$runtimeTcl = Join-Path $PSScriptRoot "runtime_tcl"

New-Item -ItemType Directory -Force -Path $runtimeTcl | Out-Null
Copy-Item -Recurse -Force (Join-Path $pythonRoot "tcl\tcl8.6") $runtimeTcl
Copy-Item -Recurse -Force (Join-Path $pythonRoot "tcl\tk8.6") $runtimeTcl

$env:TCL_LIBRARY = Join-Path $runtimeTcl "tcl8.6"
$env:TK_LIBRARY = Join-Path $runtimeTcl "tk8.6"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name SamplingSpectrumDemo `
  --runtime-hook pyinstaller_runtime_hook.py `
  --add-data "runtime_tcl;runtime_tcl" `
  sampling_gui.py
