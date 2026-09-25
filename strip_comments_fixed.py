                      
import os
import re
import tokenize
import io

def strip_python_comments (filepath):
    with open (filepath, 'r', encoding='utf-8') as f:
        source = f.read ()
                                    
    result = []
    try:
        g = tokenize.tokenize (io.BytesIO (source.encode ('utf-8')).readline)
        for token in g:
                                                                               
            if token.type == tokenize.COMMENT:
                continue
                                   
            result.append ((token.type, token.string))
    except tokenize.TokenError as e:
                                                                                      
        print (f"Tokenize error in {filepath}: {e}. Falling back to simple comment removal.")
        lines = source.split ('\n')
        out_lines = []
        for line in lines:
                                                                                         
                                                               
            stripped = line.split ('#')[0]
            out_lines.append (stripped)
        source = '\n'.join (out_lines)
        if not source.endswith ('\n'):
            source += '\n'
        with open (filepath, 'w', encoding='utf-8') as f:
            f.write (source)
        return

    stripped = tokenize.untokenize (result).decode ('utf-8')
                           
    if not stripped.endswith ('\n'):
        stripped += '\n'
    with open (filepath, 'w', encoding='utf-8') as f:
        f.write (stripped)

def strip_html_comments (filepath):
    with open (filepath, 'r', encoding='utf-8') as f:
        content = f.read ()
                                                                                     
                                                              
    stripped = re.sub (r'<!--.*?-->', '', content, flags = re.DOTALL)
    with open (filepath, 'w', encoding='utf-8') as f:
        f.write (stripped)

def strip_css_comments (filepath):
    with open (filepath, 'r', encoding='utf-8') as f:
        content = f.read ()
                               
    stripped = re.sub (r'/\*.*?\*/', '', content, flags = re.DOTALL)
    with open (filepath, 'w', encoding='utf-8') as f:
        f.write (stripped)

def strip_js_comments (filepath):
    with open (filepath, 'r', encoding='utf-8') as f:
        content = f.read ()
                               
    content = re.sub (r'/\*.*?\*/', '', content, flags = re.DOTALL)
                                                      
                                                                                                                               
                                                                                         
    lines = content.split ('\n')
    new_lines = []
    for line in lines:
                                                                                                                     
                                                                                                                     
                                                                                     
                                                                               
        if '//' in line:
                                                                                                                                      
                                                                                      
                                                                                                                     
            if '://' in line:
                new_lines.append (line)
                continue
            line = line.split ('//')[0]
        new_lines.append (line)
    stripped = '\n'.join (new_lines)
    with open (filepath, 'w', encoding='utf-8') as f:
        f.write (stripped)

def process_file (filepath):
    ext = os.path.splitext (filepath)[1].lower ()
    if ext == '.py':
        strip_python_comments (filepath)
    elif ext == '.html':
        strip_html_comments (filepath)
    elif ext == '.css':
        strip_css_comments (filepath)
    elif ext == '.js':
        strip_js_comments (filepath)
    else:
        pass

def main ():
    root = r'C:\Users\raksh\Desktop\my-code'
                                                                      
    for dirpath, dirnames, filenames in os.walk (root):
                                      
        if 'venv' in dirpath.split (os.sep) or '__pycache__' in dirpath.split (os.sep) or '.git' in dirpath.split (os.sep):
            continue
        for f in filenames:
            if f.endswith (('.py', '.html', '.css', '.js')):
                full = os.path.join (dirpath, f)
                print (f'Processing {full}')
                try:
                    process_file (full)
                except Exception as e:
                    print (f'  Error: {e}')

if __name__ == '__main__':
    main ()