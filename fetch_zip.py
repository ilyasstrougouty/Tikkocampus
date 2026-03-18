import subprocess, json, urllib.request, tempfile, zipfile, io
url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], text=True).strip()
repo = url.split(':')[-1].replace('.git', '') if 'git@' in url else '/'.join(url.split('/')[-2:]).replace('.git', '')
runs = json.loads(urllib.request.urlopen(urllib.request.Request(f'https://api.github.com/repos/{repo}/actions/runs')).read())
run_id = runs['workflow_runs'][0]['id']

print(f"Fetching logs for run {run_id}...")
req = urllib.request.Request(f'https://api.github.com/repos/{repo}/actions/runs/{run_id}/logs')
try:
    with urllib.request.urlopen(req) as resp:
        with zipfile.ZipFile(io.BytesIO(resp.read())) as z:
            for name in z.namelist():
                if "macos-latest" in name and "NPM Install" in name:
                    print(f"--- {name} ---")
                    text = z.read(name).decode('utf-8')
                    print('\n'.join(text.split('\n')[-50:]))
except Exception as e:
    print(e)
