import json
import subprocess
import sys


with open('manifest.json', 'r') as f:
    manifest = json.load(f)

for model in manifest['models']:
    cmd = ['sysrepoctl', '--install', '--yang', model]
    print(' + {}'.format(' '.join(cmd)))
    sys.stdout.flush()
    subprocess.check_call(cmd)

