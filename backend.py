"""
backend.py — Entry point for the Tikkocampus backend.

Routes to either the auth flow, a diagnostic test, or the FastAPI server.
Uses argparse for clean argument handling.
"""
import sys
import os
import argparse


def run_auth():
    """Import and run the auth flow logic."""
    import auth
    auth.run_login_flow()


def run_app(port=8000, host="127.0.0.1"):
    """Import and run the FastAPI server."""
    import app
    app.run_server(host=host, port=port)


def run_diagnostics():
    """Run the dependency diagnostic tests."""
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tikkocampus Backend")
    parser.add_argument("command", nargs="?", default="server",
                        choices=["server", "auth"],
                        help="Command to run: 'server' (default) or 'auth'")
    parser.add_argument("--port", type=int, default=8000, help="Port for the server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--test", action="store_true", help="Run diagnostics and exit")

    args, unknown = parser.parse_known_args()

    if args.test:
        run_diagnostics()
        sys.exit(0)
    elif args.command == "auth":
        run_auth()
    else:
        run_app(port=args.port, host=args.host)
