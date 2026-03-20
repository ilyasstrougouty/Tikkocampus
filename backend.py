import sys
import os

def run_auth():
    """Import and run the auth flow logic."""
    import auth
    auth.run_login_flow()

def run_app(port=8000, host="127.0.0.1"):
    """Import and run the FastAPI server."""
    import app
    app.run_server(host=host, port=port)

if __name__ == "__main__":
    # If the first argument is 'auth', run the authentication flow
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        run_auth()
    elif "--test" in sys.argv:
        # Diagnostic Mode: run the unit test logic
        try:
            import unit_test_deps
            unit_test_deps.log("Starting Diagnostic Mode via backend.exe --test")
            unit_test_deps.test_ports()
            unit_test_deps.test_system_browsers()
            unit_test_deps.test_playwright()
            unit_test_deps.test_ffmpeg()
            unit_test_deps.log("Diagnostic Complete.")
        except Exception as e:
            print(f"FAILED to run diagnostics: {e}")
        sys.exit(0)
    else:
        # Default behavior: run the FastAPI server with dynamic port support
        port = 8000
        host = "127.0.0.1"
        
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])
                
        if "--host" in sys.argv:
            idx = sys.argv.index("--host")
            if idx + 1 < len(sys.argv):
                host = sys.argv[idx + 1]
                
        run_app(port=port, host=host)
