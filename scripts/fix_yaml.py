#!/usr/bin/env python3
import sys
import re

def main():
    compose_file = "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.agents-full.yml"

    with open(compose_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace the fancy box-drawing lines with simple lines
    # Pattern: lines that contain only the box drawing characters (with possible spaces and #)
    # We'll replace lines that consist of optional whitespace, #, then only the box drawing characters
    # The box drawing character is U+2550 (═)
    # We'll keep the same indentation and the #, but replace the box drawing sequence with a simple line of = characters

    def replace_fancy_line(match):
        # match.group(0) is the entire line
        # We want to keep the leading whitespace and the #, then replace the rest with = characters
        # But we don't know the exact length. We'll keep the same length by counting characters.
        line = match.group(0)
        # Remove the newline at the end if present
        if line.endswith('\n'):
            line = line[:-1]
            has_newline = True
        else:
            has_newline = False

        # Find the position of the first non-space character after the #
        # Actually, we know the line starts with optional spaces, then #
        # We want to keep the indentation and the # and a space, then fill the rest with =
        # Let's split the line into indentation, the #, and the rest
        import re
        match_inner = re.match(r'(\s*)(#\s*)(.*)', line)
        if match_inner:
            indent = match_inner.group(1)
            hash_and_space = match_inner.group(2)  # includes the # and following spaces
            # We want to keep the hash_and_space, then fill the rest with = characters
            # The total length of the line should remain the same
            total_len = len(line)
            new_rest_len = total_len - len(indent) - len(hash_and_space)
            if new_rest_len < 0:
                new_rest_len = 0
            new_line = indent + hash_and_space + ('=' * new_rest_len)
            if has_newline:
                new_line += '\n'
            return new_line
        else:
            # If we can't match, return the line unchanged
            return line if not has_newline else line + '\n'

    # Apply the replacement to lines that contain the box drawing character
    lines = content.splitlines(keepends=True)
    new_lines = []
    for line in lines:
        if '═' in line:
            # Check if it's a comment line with only the box drawing characters
            stripped = line.lstrip()
            if stripped.startswith('#') and all(c == '═' for c in stripped[1:].strip()):
                new_line = replace_fancy_line(line)
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    new_content = ''.join(new_lines)

    with open(compose_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("Fixed fancy box-drawing lines in docker-compose.agents-full.yml")

if __name__ == "__main__":
    main()