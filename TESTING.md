# 🧪 Testing Tikkocampus Locally

To avoid broken releases, follow these steps to verify both the Python backend and the Electron frontend on your machine.

## 1. Verify the Python Backend
Run the build script to ensure all dependencies (like Playwright stealth and ChromaDB) are correctly bundled:

```bash
# In the project root
python build_backend.py
```

**How to verify:**
1. Go to `dist/backend/`.
2. Run `backend.exe`.
3. If a terminal window opens and says "Starting Tikkocampus Backend Server..." without a traceback popup, the build is successful.
4. Close the window.

## 2. Verify the Electron Frontend
Build the frontend and package it into a "portable" directory to test the production path resolution:

```bash
cd electron-app
npm run build
npm run pack
```

**How to verify:**
1. Go to `electron-app/dist/win-unpacked/`.
2. Run `Tikkocampus.exe`.
3. The app should open. Try to navigate to the "Settings" or "Arcade" tabs.
4. If it opens and the UI is responsive, the production asset paths are correct.

## 3. Full Cleanup (Before pushing to GitHub)
If both steps above work, you are ready to push!

```bash
git add .
git commit -m "fix(build): stabilize dependencies and paths v1.1.5"
git tag v1.1.5
git push origin main --tags
```
