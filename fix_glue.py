#!/usr/bin/env python3
import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # List of (pattern, replacement)
    patterns = [
        (r'from __future__', 'from __future__'),
        (r'import annotations', 'import annotations'),
        (r'import argparse', 'import argparse'),
        (r'import logging', 'import logging'),
        (r'import os', 'import os'),
        (r'import time', 'import time'),
        (r'from typing', 'from typing'),
        (r'from flask', 'from flask'),
        (r'import model', 'import model'),
        (r'import scraper', 'import scraper'),
        (r'import strategy', 'import strategy'),
        (r'logging \.basicConfig', 'logging.basicConfig'),
        (r'log = logging', 'log = logging'),
        (r'app = Flask', 'app = Flask'),
        (r'app \.config', 'app.config'),
        (r'LIVE_DEFAULT = os', 'LIVE_DEFAULT = os'),
        (r'SITE_URL = os', 'SITE_URL = os'),
        (r'_CACHE: Dict', '_CACHE: Dict'),
        (r'def analyze', 'def analyze'),
        (r'def analyze_cached', 'def analyze_cached'),
        (r'def site_url', 'def site_url'),
        (r'def inject_site_context', 'def inject_site_context'),
        (r'def _thresholds', 'def _thresholds'),
        (r'def index', 'def index'),
        (r'def methodology', 'def methodology'),
        (r'def api_universe', 'def api_universe'),
        (r'def api_analyze', 'def api_analyze'),
        (r'def api_analyze_all', 'def api_analyze_all'),
        (r'def api_health', 'def api_health'),
        (r'def favicon_ico', 'def favicon_ico'),
        (r'def robots_txt', 'def robots_txt'),
        (r'def sitemap_xml', 'def sitemap_xml'),
        (r'def llms_txt', 'def llms_txt'),
        (r'def page_not_found', 'def page_not_found'),
        (r'def internal_error', 'def internal_error'),
        (r'def main', 'def main'),
        (r'if __name__', 'if __name__'),
    ]

    for pattern, repl in patterns:
        content = re.sub(pattern, repl, content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    root = r'C:\Users\raksh\Desktop\my-code'
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip venv, __pycache__, .git
        if 'venv' in dirpath.split(os.sep) or '__pycache__' in dirpath.split(os.sep) or '.git' in dirpath.split(os.sep):
            continue
        for f in filenames:
            if f.endswith('.py'):
                full = os.path.join(dirpath, f)
                print(f'Fixing {full}')
                try:
                    fix_file(full)
                except Exception as e:
                    print(f'  Error: {e}')

if __name__ == '__main__':
    main()