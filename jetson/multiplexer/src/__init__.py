# Motor Controller Proxy/Multiplexer Package
"""
This package provides a proxy/multiplexer service for Arduino motor control.
Exposes motor control via Unix socket interface while managing serial communication.
"""

import subprocess
import os
from datetime import datetime

__version__ = "2.1.0"

def get_build_info():
    """Get build information including git commit if available"""
    build_info = {
        'version': __version__,
        'build_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'git_commit': 'unknown',
        'git_branch': 'unknown'
    }

    try:
        # Try to get git commit hash
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                              capture_output=True, text=True, timeout=2,
                              cwd=os.path.dirname(os.path.dirname(__file__)))
        if result.returncode == 0:
            build_info['git_commit'] = result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    try:
        # Try to get git branch
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                              capture_output=True, text=True, timeout=2,
                              cwd=os.path.dirname(os.path.dirname(__file__)))
        if result.returncode == 0:
            build_info['git_branch'] = result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    return build_info