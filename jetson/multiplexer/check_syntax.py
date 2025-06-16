#!/usr/bin/env python3
import ast
import sys

try:
    with open('src/unix_socket_server.py', 'r') as f:
        content = f.read()
    ast.parse(content)
    print('✅ Syntax OK')
except SyntaxError as e:
    print(f'❌ Syntax Error: {e}')
    print(f'Line {e.lineno}: {e.text}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)