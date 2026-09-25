                      
"""
Script to remove comments from .py, .html, .css, .js files in the current directory and subdirectories.
Also adjusts CSS theme to be more gaming-like minimalist (less neon).
"""

import os
import re
import tokenize
import io
from typing import List, Tuple


def remove_python_comments (file_path: str) -> str:
    """Remove comments from a Python file using tokenize module."""
    with open (file_path, 'r', encoding='utf-8') as f:
        source = f.read ()

                                                                         
    try:
        tokens = list (tokenize.generate_tokens (io.StringIO (source).readline))
    except tokenize.TokenError as e:
                                                                            
                                                                 
        print (f"Warning: Tokenize failed for {file_path}: {e}. Skipping comment removal.")
        return source

                               
    filtered_tokens = [token for token in tokens if token.type != tokenize.COMMENT]

                                   
    try:
                                                                                    
                                                                                  
                                                                                             
                                                                                               
                                                                                 
        new_source = tokenize.untokenize (filtered_tokens)
    except Exception as e:
        print (f"Warning: Untokenize failed for {file_path}: {e}. Skipping comment removal.")
        return source

    return new_source


def remove_html_comments (content: str) -> str:
    """Remove HTML comments (<!-- ... -->) but not inside script/style tags?
    We'll do a simple regex that may remove comments incorrectly if they appear in strings.
    For simplicity, we'll remove all HTML comments."""
                                                             
    return re.sub (r'<!--.*?-->', '', content, flags = re.DOTALL)


def remove_css_js_comments (content: str) -> str:
    """Remove /* ... */ and // comments from CSS/JS files, but not inside strings."""
                                                                 
    content = re.sub (r'/\*.*?\*/', '', content, flags = re.DOTALL)

                                                        
                                                       
    lines = content.split ('\n')
    result_lines = []
    for line in lines:
                                                           
        in_string = None                          
        escape = False
        new_line = []
        i = 0
        while i < len (line):
            c = line[i]
            if escape:
                escape = False
                new_line.append (c)
                i += 1
                continue

            if c == '\\':
                escape = True
                new_line.append (c)
                i += 1
                continue

            if in_string is None and c in ('"', "'", '`'):
                in_string = c
                new_line.append (c)
                i += 1
                continue

            if in_string is not None and c == in_string:
                in_string = None
                new_line.append (c)
                i += 1
                continue

                                                           
            if in_string is None and c == '/' and i + 1 < len (line) and line[i+1] == '/':
                                                            
                break

            new_line.append (c)
            i += 1

        result_lines.append (''.join (new_line))

    return '\n'.join (result_lines)


def adjust_css_theme (css_content: str) -> str:
    """Adjust CSS color variables to be more gaming-like minimalist (less neon)."""
                                                   
                                                                                             

    def replace_hex_color (match):
        hex_color = match.group (1)
                            
        r = int (hex_color[0:2], 16)
        g = int (hex_color[2:4], 16)
        b = int (hex_color[4:6], 16)

                                                
                                                                                                     
                                                                                 
                                                         
        if r > 200 and g > 200 and b > 200:
                                         
            r = max (0, r - 50)
            g = max (0, g - 50)
            b = max (0, b - 50)
        elif (r > 200 and g > 200) or (r > 200 and b > 200) or (g > 200 and b > 200):
                                                       
            r = max (0, r - 30)
            g = max (0, g - 30)
            b = max (0, b - 30)
        elif r > 200:
            r = max (0, r - 40)
        elif g > 200:
            g = max (0, g - 40)
        elif b > 200:
            b = max (0, b - 40)

                             
        return f'#{r:02x}{g:02x}{b:02x}'

                        
    css_content = re.sub (r'#([0-9a-fA-F]{6})', replace_hex_color, css_content)

                                                                                  
                                                     
    return css_content


def process_file (file_path: str) -> None:
    """Process a single file based on its extension."""
    ext = os.path.splitext (file_path)[1].lower ()

    try:
        with open (file_path, 'r', encoding='utf-8') as f:
            original_content = f.read ()
    except Exception as e:
        print (f"Error reading {file_path}: {e}")
        return

    new_content = original_content
    if ext == '.py':
        new_content = remove_python_comments (file_path)
    elif ext == '.html':
        new_content = remove_html_comments (original_content)
    elif ext in ('.css', '.js'):
        new_content = remove_css_js_comments (original_content)
        if ext == '.css':
                                                 
            new_content = adjust_css_theme (new_content)
    else:
                                
        return

                                   
    if new_content != original_content:
        try:
            with open (file_path, 'w', encoding='utf-8') as f:
                f.write (new_content)
            print (f"Processed: {file_path}")
        except Exception as e:
            print (f"Error writing {file_path}: {e}")
    else:
        print (f"No changes needed: {file_path}")


def main ():
    """Walk through current directory and subdirectories, processing files."""
    root_dir = os.getcwd ()
    for dirpath, dirnames, filenames in os.walk (root_dir):
        for filename in filenames:
            file_path = os.path.join (dirpath, filename)
            process_file (file_path)


if __name__ == '__main__':
    main ()