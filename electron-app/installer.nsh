!macro customHeader
  !system "taskkill /F /IM backend.exe /T"
!macroend

!macro customInit
  DetailPrint "Ensuring Tikkocampus backend is closed..."
  ExecWait 'taskkill /F /IM backend.exe /T'
!macroend
