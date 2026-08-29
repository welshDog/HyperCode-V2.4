#!/usr/bin/env python3
import sys
import yaml
import argparse

def main():
    parser = argparse.ArgumentParser(description='Remove duplicate service blocks from docker-compose.agents-full.yml')
    parser.add_argument('file', help='Path to the docker-compose.agents-full.yml file')
    parser.add_argument('--service', required=True, help='Service name to deduplicate')
    parser.add_argument('--dry-run', action='store_true', help='Only show what would be done')
    parser.add_argument('--validate', action='store_true', help='Validate the YAML after processing')
    args = parser.parse_args()

    with open(args.file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find all service blocks (lines that start with two spaces and a word and a colon)
    service_blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this line starts a service block: two spaces, then a word, then colon
        if line.startswith('  ') and ':' in line and not line.startswith('    '):
            # Potential service name
            service_name = line.split(':')[0].strip()
            if service_name == args.service:
                # Found a service block, now find its end
                start_idx = i
                # Find the end of the block: next line that starts with two spaces and a word and colon (next service) or less than two spaces
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    # Check if this line starts a new service block
                    if next_line.startswith('  ') and ':' in next_line and not next_line.startswith('    '):
                        break
                    # Check if this line is less indented (i.e., starts with less than two spaces)
                    if not next_line.startswith('  ') and next_line.strip() != '':
                        break
                    j += 1
                end_idx = j  # exclusive
                service_blocks.append((start_idx, end_idx, service_name, lines[start_idx:end_idx]))
                i = j
            else:
                i += 1
        else:
            i += 1

    # Filter for the target service
    target_blocks = [block for block in service_blocks if block[2] == args.service]
    if len(target_blocks) <= 1:
        print(f"No duplicates found for service '{args.service}'.")
        return

    print(f"Found {len(target_blocks)} occurrences of service '{args.service}'.")
    for idx, (start, end, name, block_lines) in enumerate(target_blocks):
        print(f"  Occurrence {idx+1}: lines {start+1}-{end}")

    if args.dry_run:
        print("Dry run: no changes made.")
        return

    # Keep the first occurrence, remove the rest
    # We'll build new lines list
    new_lines = []
    i = 0
    while i < len(lines):
        # Check if we are at a service block for the target service
        if i < len(lines) and lines[i].startswith('  ') and ':' in lines[i] and not lines[i].startswith('    '):
            service_name = lines[i].split(':')[0].strip()
            if service_name == args.service:
                # Find the end of this block
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if next_line.startswith('  ') and ':' in next_line and not next_line.startswith('    '):
                        break
                    if not next_line.startswith('  ') and next_line.strip() != '':
                        break
                    j += 1
                end_idx = j
                # Check if this is the first occurrence we want to keep
                if (i, end_idx, service_name) == (target_blocks[0][0], target_blocks[0][1], target_blocks[0][2]):
                    # Keep this block
                    new_lines.extend(lines[i:end_idx])
                # Skip this block (whether we keep it or not, we've handled it)
                i = end_idx
                continue
        new_lines.append(lines[i])
        i += 1

    # Write backup
    backup_file = args.file + '.bak'
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"Backup written to {backup_file}")

    # Write new file
    with open(args.file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Updated {args.file} with duplicates removed.")

    if args.validate:
        # Validate the YAML
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            print("YAML validation passed.")
        except Exception as e:
            print(f"YAML validation failed: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()