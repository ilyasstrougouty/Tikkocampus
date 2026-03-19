import PyInstaller.__main__
import platform
import os

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
    '--collect-all', 'webview',
    '--collect-all', 'onnxruntime',
    '--collect-all', 'posthog',
]

# Add optional data files if they exist (CI fix)
for extra_file in ['cookies.txt', 'targets.txt']:
    if os.path.exists(extra_file):
        args.extend(['--add-data', f'{extra_file}{os.pathsep}.'])


print(f"Running PyInstaller with args: {args}")
PyInstaller.__main__.run(args)

print(f"Compilation finished! Output should be in the 'dist/{executable_name}' folder.")
