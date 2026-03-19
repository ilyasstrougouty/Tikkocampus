import PyInstaller.__main__
import platform

print("Starting PyInstaller compilation for Target OS...")

executable_name = 'backend'
if platform.system() == 'Windows':
    executable_name = 'backend.exe'

# Define PyInstaller arguments
args = [
    'app.py',
    '--name', 'backend',
    '--onedir',
    '--windowed',
    '--noconfirm',
    '--clean',
    '--collect-all', 'uvicorn',
    '--collect-all', 'fastapi',
    '--collect-all', 'playwright',
    '--collect-all', 'tiktok_uploader',
    '--hidden-import', 'uvicorn.protocols.http.httptools_impl',
    '--hidden-import', 'uvicorn.protocols.http.h11_impl',
    '--hidden-import', 'uvicorn.protocols.websockets.websockets_impl',
    '--hidden-import', 'uvicorn.loggers',
    '--hidden-import', 'uvicorn.lifespan.on',
    '--hidden-import', 'email_validator',
    '--add-data', f'web;web',
    '--add-data', f'cookies.txt;.',
    '--add-data', f'targets.txt;.',
    '--collect-all=playwright',
    '--collect-all=webview',
    '--collect-all=onnxruntime',
    '--collect-all=posthog',
]

print(f"Running PyInstaller with args: {args}")
PyInstaller.__main__.run(args)

print(f"Compilation finished! Output should be in the 'dist/{executable_name}' folder.")
