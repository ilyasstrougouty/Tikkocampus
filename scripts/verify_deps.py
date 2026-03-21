import sys

modules = [
    "dotenv",
    "fastapi",
    "uvicorn",
    "pydantic",
    "playwright",
    "playwright_stealth",
    "chromadb",
    "langchain_text_splitters",
    "litellm",
    "httpx",
    "webview",
    "onnxruntime",
    "posthog"
]

print("Starting dependency verification...")
missing = []
for mod in modules:
    try:
        __import__(mod)
        print(f"[OK] {mod}")
    except ImportError as e:
        print(f"[ERROR] {mod}: {e}")
        missing.append(mod)

if missing:
    print(f"\nCRITICAL: Missing modules: {missing}")
    sys.exit(1)
else:
    print("\nAll core dependencies are importable!")
    sys.exit(0)
