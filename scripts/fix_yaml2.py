#!/usr/bin/env python3
import sys
import re

def main():
    compose_file = "H:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.agents-full.yml"

    with open(compose_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        # Check if the line is a comment line consisting only of # and box drawing characters and spaces
        stripped = line.lstrip()
        if stripped.startswith('#'):
            rest = stripped[1:]
            # Check if rest consists only of spaces and box drawing characters (U+2550)
            if all(c == ' ' or c == '═' for c in rest):
                # This is a fancy separator line
                # Keep the leading whitespace and the #, then add a space and 80 = characters
                indent = line[:len(line)-len(stripped)]
                new_line = indent + '# ' + '='*80 + '\n'
                new_lines.append(new_line)
                continue
        new_lines.append(line)

    with open(compose_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print("Fixed fancy separator lines in docker-compose.agents-full.yml")

if __name__ == "__main__":
    main()