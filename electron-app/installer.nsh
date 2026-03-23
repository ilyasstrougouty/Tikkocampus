!macro customInit
  ; Kill the Electron app first silently (no DOS box flash)
  DetailPrint "Closing Tikkocampus..."
  nsExec::ExecToStack '"$SYSDIR\taskkill.exe" /F /IM Tikkocampus.exe /T'
  
  ; Then kill the backend silently
  DetailPrint "Closing backend..."
  nsExec::ExecToStack '"$SYSDIR\taskkill.exe" /F /IM backend.exe /T'
  
  ; Small delay to let Windows release file locks
  Sleep 1000
!macroend
