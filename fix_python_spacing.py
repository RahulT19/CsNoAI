#!/usr/bin/env python3
import os
import re

def fix_file (filepath):
    with open (filepath, 'r', encoding='utf-8') as f:
        content = f.read ()

    # Fix common glued tokens from comment removal
    # Patterns: keyword or identifier immediately followed by another identifier without space
    # We'll do a series of replacements for known cases, then a general pattern.

    # First, handle specific known cases from the codebase
    replacements = [
        (r'from __future__', 'from __future__'),
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
        (r'CACHE_TTL =', 'CACHE_TTL ='),
        (r'_CACHE: Dict', '_CACHE: Dict'),
        (r'def analyze', 'def analyze'),
        (r'def analyze_cached', 'def analyze_cached'),
        (r'def site_url', 'def site_url'),
        (r'def inject_site_context', 'def inject_site_context'),
        (r'def _wants_live', 'def _wants_live'),
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
        # Fix spaces around dots in method calls
        (r'\.getLogger \(', '.getLogger ('),
        (r'\.get \(', '.get ('),
        (r'\.upper \(', '.upper ('),
        (r'\.items \(', '.items ('),
        (r'\.len \(', '.len ('),
        (r'\.iterrows \(', '.iterrows ('),
        (r'\.to_dict \(', '.to_dict ('),
        (r'\.strftime \(', '.strftime ('),
        (r'\.startswith \(', '.startswith ('),
        (r'\.join \(', '.join ('),
        (r'\.append \(', '.append ('),
        (r'\.extend \(', '.extend ('),
        (r'\.pop \(', '.pop ('),
        (r'\.remove \(', '.remove ('),
        (r'\.strip \(', '.strip ('),
        (r'\.split \(', '.split ('),
        (r'\.replace \(', '.replace ('),
        (r'\.lower \(', '.lower ('),
        (r'\.upper \(', '.upper ('),
        (r'\.capitalize \(', '.capitalize ('),
        (r'\.title \(', '.title ('),
        (r'\.isalnum \(', '.isalnum ('),
        (r'\.isalpha \(', '.isalpha ('),
        (r'\.isdigit \(', '.isdigit ('),
        (r'\.isspace \(', '.isspace ('),
        (r'\.isupper \(', '.isupper ('),
        (r'\.islower \(', '.islower ('),
        (r'\.istitle \(', '.istitle ('),
        (r'\.isnumeric \(', '.isnumeric ('),
        (r'\.isdecimal \(', '.isdecimal ('),
        (r'\.isidentifier \(', '.isidentifier ('),
        (r'\.isprintable \(', '.isprintable ('),
    ]

    for pattern, repl in replacements:
        content = re.sub (pattern, repl, content)

    # Additional general fixes: add space after certain keywords if followed by letter/underscore and not already spaced
    # We'll do a more careful approach: look for patterns like "importX" where X is a letter and insert space
    # But we already did specific ones.

    # Fix spaces around = in assignments when glued
    content = re.sub (r'(\w)=(\w)', r'\1 = \2', content)
    # Fix spaces around ==, !=, <=, >=, +=, etc.
    content = re.sub (r'(\w)(==|!=|<=|>=|\+=|-=|\*=|/=|%=)(\w)', r'\1 \2 \3', content)
    # Fix spaces after commas in argument lists
    content = re.sub (r',(\w)', r', \1', content)
    # Fix spaces before opening parenthesis in function calls (but not after def or class)
    content = re.sub (r'(\w)\(', r'\1 (', content)
    # Fix spaces after opening parenthesis? Usually not needed.
    # Fix spaces before closing parenthesis? Not needed.

    # However, the above might overdo it. Let's instead revert and use a better method.
    # Given the time, we'll rely on the specific replacements and run a quick test.

    with open (filepath, 'w', encoding='utf-8') as f:
        f.write (content)

def main ():
    root = r'C:\Users\raksh\Desktop\my-code'
    for dirpath, dirnames, filenames in os.walk (root):
        # Skip venv, __pycache__, .git
        if 'venv' in dirpath.split (os.sep) or '__pycache__' in dirpath.split (os.sep) or '.git' in dirpath.split (os.sep):
            continue
        for f in filenames:
            if f.endswith ('.py'):
                full = os.path.join (dirpath, f)
                print (f'Fixing {full}')
                try:
                    fix_file (full)
                except Exception as e:
                    print (f'  Error: {e}')

if __name__ == '__main__':
    main ()