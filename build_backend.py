import PyInstaller.__main__
import platform

print("Starting PyInstaller compilation for Target OS...")

executable_name = 'backend'
if platform.system() == 'Windows':
    executable_name = 'backend.exe'

# Define PyInstaller arguments
args = [
    'app.py',
    f'--name={executable_name}',
    '--onedir',   # onedir is much faster to boot than onefile for heavy AI apps
    '--console',
    '--noconfirm',
    # Ensure all hidden frameworks are aggressively pulled in
    '--hidden-import=chromadb',
    '--hidden-import=playwright',
    '--hidden-import=sqlite3',
    '--hidden-import=webview',
    '--hidden-import=websockets.legacy',
    '--hidden-import=websockets.legacy.server',
    '--hidden-import=websockets.legacy.client',
    '--hidden-import=onnxruntime',
    '--hidden-import=posthog',
    
    # Collect all associated data files / dlls for these massive packages
    '--collect-all=chromadb',
    '--collect-all=playwright',
    '--collect-all=webview',
    '--collect-all=onnxruntime',
    '--collect-all=posthog',
]

print(f"Running PyInstaller with args: {args}")
PyInstaller.__main__.run(args)

print(f"Compilation finished! Output should be in the 'dist/{executable_name}' folder.")
