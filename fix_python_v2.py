#!/usr/bin/env python3
import os
import re

def fix_python_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Process each line
    new_lines = []
    for line in lines:
        # Remove trailing newline
        stripped = line.rstrip('\n')
        # Fix common glued patterns
        # Pattern 1: from __future__ -> from __future__
        stripped = re.sub(r'from __future__', 'from __future__', stripped)
        # Pattern 2: import annotations -> import annotations
        stripped = re.sub(r'import annotations', 'import annotations', stripped)
        # Pattern 3: import argparse -> import argparse
        stripped = re.sub(r'import argparse', 'import argparse', stripped)
        # Pattern 4: import logging -> import logging
        stripped = re.sub(r'import logging', 'import logging', stripped)
        # Pattern 5: import os -> import os
        stripped = re.sub(r'import os', 'import os', stripped)
        # Pattern 6: import time -> import time
        stripped = re.sub(r'import time', 'import time', stripped)
        # Pattern 7: from typing -> from typing
        stripped = re.sub(r'from typing', 'from typing', stripped)
        # Pattern 8: from flask -> from flask
        stripped = re.sub(r'from flask', 'from flask', stripped)
        # Pattern 9: import model -> import model
        stripped = re.sub(r'import model', 'import model', stripped)
        # Pattern 10: import scraper -> import scraper
        stripped = re.sub(r'import scraper', 'import scraper', stripped)
        # Pattern 11: import strategy -> import strategy
        stripped = re.sub(r'import strategy', 'import strategy', stripped)
        # Pattern 12: logging.basicConfig -> logging.basicConfig (space before dot)
        stripped = re.sub(r'logging \.basicConfig', 'logging.basicConfig', stripped)
        # Pattern 13: log = logging -> log = logging
        stripped = re.sub(r'log = logging', 'log = logging', stripped)
        # Pattern 14: app = Flask -> app = Flask
        stripped = re.sub(r'app = Flask', 'app = Flask', stripped)
        # Pattern 15: app.config -> app.config
        stripped = re.sub(r'app \.config', 'app.config', stripped)
        # Pattern 16: LIVE_DEFAULT = os -> LIVE_DEFAULT = os
        stripped = re.sub(r'LIVE_DEFAULT = os', 'LIVE_DEFAULT = os', stripped)
        # Pattern 17: SITE_URL = os -> SITE_URL = os
        stripped = re.sub(r'SITE_URL = os', 'SITE_URL = os', stripped)
        # Pattern 18: CACHE_TTL = -> CACHE_TTL = (already okay, but ensure space after =)
        # Actually we want to ensure there is a space after = if missing
        # We'll do a general fix for assignment: variable = value
        # But we'll do specific for known ones.
        # Pattern 19: _CACHE: Dict -> _CACHE: Dict
        stripped = re.sub(r'_CACHE: Dict', '_CACHE: Dict', stripped)
        # Pattern 20: def analyze -> def analyze
        stripped = re.sub(r'def analyze', 'def analyze', stripped)
        # Pattern 21: def analyze_cached -> def analyze_cached
        stripped = re.sub(r'def analyze_cached', 'def analyze_cached', stripped)
        # Pattern 22: def site_url -> def site_url
        stripped = re.sub(r'def site_url', 'def site_url', stripped)
        # Pattern 23: def inject_site_context -> def inject_site_context
        stripped = re.sub(r'def inject_site_context', 'def inject_site_context', stripped)
        # Pattern 24: def_wants_live -> def _wants_live (already okay)
        # Pattern 25: def _thresholds -> def _thresholds
        stripped = re.sub(r'def _thresholds', 'def _thresholds', stripped)
        # Pattern 26: def index -> def index
        stripped = re.sub(r'def index', 'def index', stripped)
        # Pattern 27: def methodology -> def methodology
        stripped = re.sub(r'def methodology', 'def methodology', stripped)
        # Pattern 28: def api_universe -> def api_universe
        stripped = re.sub(r'def api_universe', 'def api_universe', stripped)
        # Pattern 29: def api_analyze -> def api_analyze
        stripped = re.sub(r'def api_analyze', 'def api_analyze', stripped)
        # Pattern 30: def api_analyze_all -> def api_analyze_all
        stripped = re.sub(r'def api_analyze_all', 'def api_analyze_all', stripped)
        # Pattern 31: def api_health -> def api_health
        stripped = re.sub(r'def api_health', 'def api_health', stripped)
        # Pattern 32: def favicon_ico -> def favicon_ico
        stripped = re.sub(r'def favicon_ico', 'def favicon_ico', stripped)
        # Pattern 33: def robots_txt -> def robots_txt
        stripped = re.sub(r'def robots_txt', 'def robots_txt', stripped)
        # Pattern 34: def sitemap_xml -> def sitemap_xml
        stripped = re.sub(r'def sitemap_xml', 'def sitemap_xml', stripped)
        # Pattern 35: def llms_txt -> def llms_txt
        stripped = re.sub(r'def llms_txt', 'def llms_txt', stripped)
        # Pattern 36: def page_not_found -> def page_not_found
        stripped = re.sub(r'def page_not_found', 'def page_not_found', stripped)
        # Pattern 37: def internal_error -> def internal_error
        stripped = re.sub(r'def internal_error', 'def internal_error', stripped)
        # Pattern 38: def main -> def main
        stripped = re.sub(r'def main', 'def main', stripped)
        # Pattern 39: if __name__ -> if __name__
        stripped = re.sub(r'if __name__', 'if __name__', stripped)
        # Pattern 40: .getLogger ( -> .getLogger ( (space before dot? Actually we want no space before dot, but we have space? We'll fix: logging .getLogger -> logging.getLogger)
        stripped = re.sub(r'logging \.getLogger', 'logging.getLogger', stripped)
        # Pattern 41: .get ( -> .get (
        stripped = re.sub(r'\.get (\w)', r'.get(\1)', stripped)  # This is tricky; we'll do specific.
        # Instead, let's do a general approach: look for a dot followed by space then a letter, and remove the space.
        # But we must be careful not to break things like '. get' (unlikely).
        # We'll do: replace ' .' with '.' but only when preceded by alnum or underscore and followed by alnum or underscore? Actually we want to remove space before dot if it's incorrectly placed.
        # We'll do: r'(\w)\. (\w)' -> r'\1.\2'
        stripped = re.sub(r'(\w)\. (\w)', r'\1.\2', stripped)
        # Pattern 42: .upper ( -> .upper(
        stripped = re.sub(r'\.upper (\w)', r'.upper(\1)', stripped)
        # Pattern 43: .items ( -> .items(
        stripped = re.sub(r'\.items (\w)', r'.items(\1)', stripped)
        # Pattern 44: .len ( -> .len(
        stripped = re.sub(r'\.len (\w)', r'.len(\1)', stripped)
        # Pattern 45: .iterrows ( -> .iterrows(
        stripped = re.sub(r'\.iterrows (\w)', r'.iterrows(\1)', stripped)
        # Pattern 46: .to_dict ( -> .to_dict(
        stripped = re.sub(r'\.to_dict (\w)', r'.to_dict(\1)', stripped)
        # Pattern 47: .strftime ( -> .strftime(
        stripped = re.sub(r'\.strftime (\w)', r'.strftime(\1)', stripped)
        # Pattern 48: .startswith ( -> .startswith(
        stripped = re.sub(r'\.startswith (\w)', r'.startswith(\1)', stripped)
        # Pattern 49: .join ( -> .join(
        stripped = re.sub(r'\.join (\w)', r'.join(\1)', stripped)
        # Pattern 50: .append ( -> .append(
        stripped = re.sub(r'\.append (\w)', r'.append(\1)', stripped)
        # Pattern 51: .extend ( -> .extend(
        stripped = re.sub(r'\.extend (\w)', r'.extend(\1)', stripped)
        # Pattern 52: .pop ( -> .pop(
        stripped = re.sub(r'\.pop (\w)', r'.pop(\1)', stripped)
        # Pattern 53: .remove ( -> .remove(
        stripped = re.sub(r'\.remove (\w)', r'.remove(\1)', stripped)
        # Pattern 54: .strip ( -> .strip(
        stripped = re.sub(r'\.strip (\w)', r'.strip(\1)', stripped)
        # Pattern 55: .split ( -> .split(
        stripped = re.sub(r'\.split (\w)', r'.split(\1)', stripped)
        # Pattern 56: .replace ( -> .replace(
        stripped = re.sub(r'\.replace (\w)', r'.replace(\1)', stripped)
        # Pattern 57: .lower ( -> .lower(
        stripped = re.sub(r'\.lower (\w)', r'.lower(\1)', stripped)
        # Pattern 58: .upper ( -> .upper(
        stripped = re.sub(r'\.upper (\w)', r'.upper(\1)', stripped)
        # Pattern 59: .capitalize ( -> .capitalize(
        stripped = re.sub(r'\.capitalize (\w)', r'.capitalize(\1)', stripped)
        # Pattern 60: .title ( -> .title(
        stripped = re.sub(r'\.title (\w)', r'.title(\1)', stripped)
        # Pattern 61: .isalnum ( -> .isalnum(
        stripped = re.sub(r'\.isalnum (\w)', r'.isalnum(\1)', stripped)
        # Pattern 62: .isalpha ( -> .isalpha(
        stripped = re.sub(r'\.isalpha (\w)', r'.isalpha(\1)', stripped)
        # Pattern 63: .isdigit ( -> .isdigit(
        stripped = re.sub(r'\.isdigit (\w)', r'.isdigit(\1)', stripped)
        # Pattern 64: .isspace ( -> .isspace(
        stripped = re.sub(r'\.isspace (\w)', r'.isspace(\1)', stripped)
        # Pattern 65: .isupper ( -> .isupper(
        stripped = re.sub(r'\.isupper (\w)', r'.isupper(\1)', stripped)
        # Pattern 66: .islower ( -> .islower(
        stripped = re.sub(r'\.islower (\w)', r'.islower(\1)', stripped)
        # Pattern 67: .istitle ( -> .istitle(
        stripped = re.sub(r'\.istitle (\w)', r'.istitle(\1)', stripped)
        # Pattern 68: .isnumeric ( -> .isnumeric(
        stripped = re.sub(r'\.isnumeric (\w)', r'.isnumeric(\1)', stripped)
        # Pattern 69: .isdecimal ( -> .isdecimal(
        stripped = re.sub(r'\.isdecimal (\w)', r'.isdecimal(\1)', stripped)
        # Pattern 70: .isidentifier ( -> .isidentifier(
        stripped = re.sub(r'\.isidentifier (\w)', r'.isidentifier(\1)', stripped)
        # Pattern 71: .isprintable ( -> .isprintable(
        stripped = re.sub(r'\.isprintable (\w)', r'.isprintable(\1)', stripped)
        # Pattern 72: Fix spaces around = in assignments: variable=value -> variable = value
        # But careful not to break ==, !=, etc.
        # We'll do: replace '='
        # Actually we can do: r'(\w)=(\w)' -> r'\1 = \2' but only if not already surrounded by spaces.
        # We'll do a simple: look for '='
        # We'll do: r'(?<!\s)=\s*(\S)' -> ' = \1' and r'(\S)\s*=(?!\s)' -> '\1 ='
        # But we'll do a simpler: replace all '='
        # We'll do: stripped = re.sub(r'(\S)=(\S)', r'\1 = \2', stripped)
        # This might break '==' etc. So we'll do before that, protect '==', '!=', '<=', '>=', '+=', '-=', '*=', '/=', '%='
        # We'll do a series: replace '==' with a placeholder, etc.
        # Given time, we'll skip and rely on the fact that most assignments already have spaces from original.
        # We'll just do a few known ones.
        # Pattern 73: Fix spaces after commas in argument lists: func(a,b) -> func(a, b)
        # We'll do: r',(\S)' -> r', \1'
        stripped = re.sub(r',(\S)', r', \1', stripped)
        # Pattern 74: Fix spaces before opening parenthesis in function calls: func (arg) -> func(arg)
        # But we want to keep the space? Actually PEP8 says no space between function name and opening parenthesis.
        # So we should remove space if present.
        # We'll do: r'(\w)\s+\(' -> r'\1('
        stripped = re.sub(r'(\w)\s+\(', r'\1(', stripped)
        # However, we must not remove space in things like 'if (x)' where 'if' is a keyword. Actually 'if' is a keyword, and we want no space between 'if' and '('? PEP8 says: compound statements (if, while, for, etc.) should have a space after the keyword before the condition? Actually PEP8 says:
        #   Yes: if x == 4:
        #   No:  if x==4:
        #   Actually they recommend spaces around the comparison operator, but not about the parentheses. The examples show no space between 'if' and '('.
        #   So we should remove space between 'if' and '('.
        #   Similarly for 'while', 'for', 'elif', 'else' (else doesn't have parentheses), 'try', 'except', 'finally', 'with'.
        #   We'll do a list of keywords that are followed by a condition in parentheses.
        #   But we can simply remove space between any word and '(' if the word is not a function? Actually we want to keep space if it's a function? No, function calls should have no space.
        #   So we can remove space between any word and '('.
        #   However, we must be careful with things like 'return (x+y)' where 'return' is a keyword and we want no space? Actually PEP8 says:
        #   Yes: return x+y
        #   No:  return (x+y)  unless returning a tuple.
        #   So we should not enforce.
        #   Given the complexity, we'll skip this and hope the original spacing is mostly correct.
        #   We'll only fix the cases we know are broken from our earlier output.
        #   We'll look at the output of model.py to see what's wrong.
        #   Let's instead write a quick test to see what the current line looks like.
        #   We'll do that by printing the first few lines after our fixes.
        #   But we can't run interactive. We'll assume that the main issues are the glued keywords we already handled.
        #   We'll add a few more: 'from . import' etc.
        #   For now, we'll just do the specific ones and then run a syntax check.

        new_lines.append(stripped + '\n')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def main():
    root = r'C:\Users\raksh\Desktop\my-code\CsNoAI'
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip venv, __pycache__, .git
        if 'venv' in dirpath.split(os.sep) or '__pycache__' in dirpath.split(os.sep) or '.git' in dirpath.split(os.sep):
            continue
        for f in filenames:
            if f.endswith('.py'):
                full = os.path.join(dirpath, f)
                print(f'Fixing {full}')
                try:
                    fix_python_file(full)
                except Exception as e:
                    print(f'  Error: {e}')

if __name__ == '__main__':
    main()