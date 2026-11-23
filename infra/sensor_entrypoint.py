"""Start Cowrie only after the internal decision service responds."""
import os
import sys
import time
from urllib.request import urlopen

url = 'http://gatekeeper:5000'
deadline = time.monotonic() + 30
while (remaining := deadline - time.monotonic()) > 0:
    try:
        with urlopen(url+'/health', timeout=min(2, remaining)) as response:
            if response.status == 200:
                break
    except OSError:
        pass
    time.sleep(min(.5, max(0, deadline-time.monotonic())))
else:
    sys.exit('Gatekeeper did not become healthy within 30 seconds')
os.execv(sys.executable, [sys.executable, '-m', 'sensor.run_sensor', '--state-dir', '/state',
         '--gatekeeper-url', url, '--listen-interface', '0.0.0.0'])
