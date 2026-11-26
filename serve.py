"""Portable launcher: fixes the Windows event-loop policy, then starts Streamlit.

Cloud platforms (Linux) start `app.py` directly; this file is for local Windows runs.
Usage: python serve.py            (default port 8501)
       set PORT=8502 && python serve.py
"""
import asyncio
import os
import sys
from pathlib import Path

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from streamlit.web import cli

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    port = os.getenv('PORT', '8501')
    sys.argv = ['streamlit', 'run', str(root / 'app.py'),
                '--server.address=127.0.0.1', f'--server.port={port}',
                '--server.headless=true', '--browser.gatherUsageStats=false']
    sys.exit(cli.main())
