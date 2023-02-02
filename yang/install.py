import json
import subprocess
import sys


def run(cmd):
    print(' + {}'.format(' '.join(cmd)))
    sys.stdout.flush()
    subprocess.check_call(cmd)


with open('manifest.json', 'r') as f:
    manifest = json.load(f)

for model in manifest['models']:
    run(['sysrepoctl', '-i', model, '-s', model.split("/")[0]])

for feature in manifest['features']:
    parts = feature.split(':')
    run(['sysrepoctl', '--change', parts[0], '--enable-feature', parts[1]])
