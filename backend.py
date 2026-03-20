import sys
import os

def run_auth():
    """Import and run the auth flow logic."""
    import auth
    auth.run_login_flow()

def run_app():
    """Import and run the FastAPI server."""
    import app
    app.run_server()

if __name__ == "__main__":
    # If the first argument is 'auth', run the authentication flow
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        run_auth()
    else:
        # Default behavior: run the FastAPI server
        run_app()
