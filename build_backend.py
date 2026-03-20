import PyInstaller.__main__
import platform
import os
import importlib.util
import sys

print("Starting Tikkocampus Backend Build (v1.2.6)...")

# CRITICAL: Verify we are running in the venv (Skip for CI environments like GitHub Actions)
if not os.environ.get('GITHUB_ACTIONS'):
    if not hasattr(sys, 'real_prefix') and not (sys.base_prefix != sys.prefix):
        print("\n[!] ERROR: You must run this build using the virtual environment!")
        print("Please run: .\\venv\\Scripts\\python.exe build_backend.py\n")
        sys.exit(1)
else:
    print("Running in CI environment (GitHub Actions). Skipping venv enforcement.")

executable_name = 'backend'
if platform.system() == 'Windows':
    executable_name = 'backend.exe'

# Locate package paths dynamically
def get_pkg_path(pkg_name):
    spec = importlib.util.find_spec(pkg_name)
    if spec and spec.submodule_search_locations:
        return spec.submodule_search_locations[0]
    return None

stealth_path = get_pkg_path('playwright_stealth')
stealth_js_path = os.path.join(stealth_path, 'js') if stealth_path else None

playwright_path = get_pkg_path('playwright')
playwright_driver_path = os.path.join(playwright_path, 'driver') if playwright_path else None

# Define PyInstaller arguments
args = [
    'backend.py',
    '--name', 'backend',
    '--onedir',
    '--windowed',
    '--noconfirm',
    '--clean',
    
    # Collect only the ones that definitely need hints
    '--collect-all', 'dotenv',
    '--collect-all', 'chromadb',
    '--collect-all', 'litellm',
    '--collect-all', 'langchain_text_splitters',
    
    # Manually bundle the missing stealth JS files if found
    '--collect-submodules', 'playwright_stealth',
    '--collect-all', 'playwright',
    '--hidden-import', 'unit_test_deps',
]

if stealth_js_path and os.path.exists(stealth_js_path):
    args.extend(['--add-data', f'{stealth_js_path}{os.pathsep}playwright_stealth/js'])

# Add Playwright driver if found
if playwright_driver_path and os.path.exists(playwright_driver_path):
    args.extend(['--add-data', f'{playwright_driver_path}{os.pathsep}playwright/driver'])

# Add the web directory (CRITICAL for the UI to work)
if os.path.exists('web'):
    args.extend(['--add-data', f'web{os.pathsep}web'])

# Add optional runtime data files if they exist (except cookies.txt which we want to keep external)
for extra_file in ['targets.txt']:
    if os.path.exists(extra_file):
        args.extend(['--add-data', f'{extra_file}{os.pathsep}.'])

print(f"Running PyInstaller with VENV-enforced v1.2.6 configuration...")
PyInstaller.__main__.run(args)

print(f"\n[SUCCESS] Build complete! Results available in: dist/{executable_name}")
