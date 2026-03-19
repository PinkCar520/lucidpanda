import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # We will use regex to find blocks of `conn = self._get_conn()` and `cursor = conn.cursor(...)`
    # and replace them with `with self._get_conn() as conn:` and `with conn.cursor(...) as cursor:`
    # We will then indent all subsequent lines in that block until `except Exception as e:` or `return` or `finally:`
    
    # Since regex is too hard for python scopes, let's do line by line state machine.
    lines = content.split('\n')
    new_lines = []
    
    i = 0
    in_conn_block = False
    conn_indent = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Match `conn = self._get_conn()`
        match_conn = re.match(r'^(\s*)conn\s*=\s*self\._get_conn\(\)\s*$', line)
        if match_conn:
            in_conn_block = True
            conn_indent = len(match_conn.group(1))
            new_lines.append(match_conn.group(1) + "with self._get_conn() as conn:")
            new_lines.append(match_conn.group(1) + "    with conn.cursor() as cursor:")  # we default to standard cursor, but let's check next line
            
            # Check if next line is a cursor def
            i += 1
            if i < len(lines):
                next_line = lines[i]
                match_cur = re.match(r'^\s*cursor\s*=\s*conn\.cursor\((.*)\)\s*$', next_line)
                if match_cur:
                    cursor_args = match_cur.group(1)
                    if cursor_args:
                        new_lines[-1] = match_conn.group(1) + f"    with conn.cursor({cursor_args}) as cursor:"
                else:
                    # Not a cursor def line, we still indent and add it
                    if next_line.strip():
                        new_lines.append("    " + "    " + next_line)
                    else:
                        new_lines.append(next_line)
            i += 1
            continue
            
        if in_conn_block:
            # Check if we exited the try block or hit except/finally
            if re.match(r'^\s*(except|finally).*:', line) and len(line) - len(line.lstrip()) <= conn_indent:
                in_conn_block = False
                new_lines.append(line)
            # Or if we hit return at the same level (very rare)
            elif re.match(r'^\s*return ', line) and len(line) - len(line.lstrip()) <= conn_indent:
                in_conn_block = False
                new_lines.append(line)
            else:
                # Indent lines inside the with blocks
                stripped = line.strip()
                if stripped == "conn.close()" or stripped == "cursor.close()":
                    pass # Remove explicit close
                else:
                    if stripped:
                        new_lines.append("    " + "    " + line)
                    else:
                        new_lines.append(line)
        else:
            new_lines.append(line)
            
        i += 1

    with open(filepath, 'w') as f:
        f.write('\n'.join(new_lines))

if __name__ == "__main__":
    db_dir = "/Users/caomeifengli/workspace/LucidPanda/src.lucidpanda/db"
    for f in ["intelligence.py", "fund.py", "market.py"]:
        path = os.path.join(db_dir, f)
        if os.path.exists(path):
            fix_file(path)
            print(f"Fixed {f}")
