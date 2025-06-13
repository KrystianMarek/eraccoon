# Motor Controller Proxy/Multiplexer Package
"""
This package provides a proxy/multiplexer service for Arduino motor control.
Exposes motor control via Unix socket interface while managing serial communication.
"""

import json
import os
from datetime import datetime
from pathlib import Path

__version__ = "2.1.0"

def get_build_info():
    """Get build information from static build_info.json file or fallback to runtime detection"""
    # Default build info
    build_info = {
        'version': __version__,
        'build_date': 'unknown',
        'build_timestamp': 0,
        'git_commit': 'unknown',
        'git_branch': 'unknown',
        'git_root': 'unknown',
        'git_dirty': False,
        'build_environment': 'development'
    }

    # Try to load from static build_info.json (production/container)
    build_info_file = Path(__file__).parent / 'build_info.json'
    if build_info_file.exists():
        try:
            with open(build_info_file, 'r') as f:
                static_info = json.load(f)
                build_info.update(static_info)
                return build_info
        except (json.JSONDecodeError, IOError) as e:
            # Fall through to runtime detection
            pass

    # Fallback: Runtime detection for development
    build_info['build_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    build_info['build_timestamp'] = int(datetime.now().timestamp())

    # Try to get git info at runtime (development only)
    try:
        import subprocess

        # Find git root directory
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                              capture_output=True, text=True, timeout=2,
                              cwd=os.path.dirname(os.path.dirname(__file__)))
        if result.returncode == 0:
            git_root = result.stdout.strip()
            build_info['git_root'] = git_root

            # Get commit hash
            result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                                  capture_output=True, text=True, timeout=2,
                                  cwd=git_root)
            if result.returncode == 0:
                build_info['git_commit'] = result.stdout.strip()

            # Get branch name
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                  capture_output=True, text=True, timeout=2,
                                  cwd=git_root)
            if result.returncode == 0:
                build_info['git_branch'] = result.stdout.strip()

            # Check if dirty
            result = subprocess.run(['git', 'diff', '--quiet'],
                                  capture_output=True, timeout=2, cwd=git_root)
            build_info['git_dirty'] = result.returncode != 0

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError, ImportError):
        pass

    return build_info