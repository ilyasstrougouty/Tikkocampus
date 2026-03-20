!macro customInit
  ; Kill the Electron app first
  DetailPrint "Closing Tikkocampus..."
  ExecWait 'taskkill /F /IM Tikkocampus.exe /T'
  ; Then kill the backend
  DetailPrint "Closing backend..."
  ExecWait 'taskkill /F /IM backend.exe /T'
  ; Small delay to let Windows release file locks
  Sleep 1000
!macroend
