import subprocess, json, urllib.request
url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], text=True).strip()
reponame = url.split(':')[-1].replace('.git', '') if 'git@' in url else '/'.join(url.split('/')[-2:]).replace('.git', '')
req = urllib.request.Request(f'https://api.github.com/repos/{reponame}/actions/runs')
res = urllib.request.urlopen(req)
runs = json.loads(res.read())
run_id = runs['workflow_runs'][0]['id']

req2 = urllib.request.Request(f'https://api.github.com/repos/{reponame}/actions/runs/{run_id}/jobs')
res2 = urllib.request.urlopen(req2)
jobs = json.loads(res2.read())

with open('gh_jobs_output.txt', 'w') as f:
    for job in jobs['jobs']:
        f.write(f"[{job['name']}] => {job['conclusion']}\n")
        if job['conclusion'] == 'failure':
            for step in job['steps']:
                if step['conclusion'] == 'failure':
                    f.write(f"  --> FAILED STEP: {step['name']}\n")
