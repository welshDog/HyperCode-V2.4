# Full MCP Tool Reference

## GitHub tools (`HyperCode:github`)

- `create_issue` — Create GitHub issue
- `create_pull_request` — Open PR
- `get_file_contents` — Read repo file
- `push_files` — Push multiple files in one commit
- `list_commits` — Get commit history
- `search_code` — Search codebase

## Filesystem tools (`HyperCode:filesystem`)

- `read_file` — Read any file
- `write_file` — Write/create file
- `list_directory` — List dir contents
- `search_files` — Search by pattern

## Usage example

```
# In a skill or agent instruction:
Use HyperCode:github:push_files to commit the new agent files.
Use HyperCode:filesystem:read_file to load the agent spec.
```
