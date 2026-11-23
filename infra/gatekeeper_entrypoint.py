"""Select the explicitly configured policy before listening inside the lab."""
import os
import sys
from pathlib import Path

profile = os.environ.get('GATEKEEPER_PROFILE', 'DEFAULT')
args = [sys.executable, '-m', 'gatekeeper.decision_api', '--host', '0.0.0.0',
        '--port', '5000', '--db', '/app/data/gatekeeper.db']
if profile == 'LAB_DEMO':
    args.append('--lab-mode')
elif profile != 'DEFAULT' or not Path('models/model_s3.json').is_file():
    sys.exit('Invalid profile or missing DEFAULT model')
os.execv(sys.executable, args)
