# HyperCode DSL Specification v0.1

## Syntax Overview
- Statements end with `;`
- Blocks use `{` and `}`
- Strings use double quotes
- Identifiers use letters, digits, `_`, starting with a letter
- Numbers support integers only in v0.1
- Comments start with `//` and end at newline

## Grammar
- program := statement*
- statement := mission_stmt | agent_stmt | set_stmt | remember_stmt | call_stmt
- mission_stmt := `mission` IDENT `{` statement* `}`
- agent_stmt := `agent` IDENT `do` IDENT `(` arg_list? `)` `;`
- set_stmt := `set` IDENT `=` value `;`
- remember_stmt := `remember` IDENT STRING `;`
- call_stmt := `call` IDENT `.` IDENT `(` arg_list? `)` `;`
- arg_list := value (`,` value)*
- value := STRING | NUMBER | IDENT

## Constructs
- mission: groups related actions under a mission id
- agent do: directs a named agent to perform an action
- set: assigns a scalar in mission memory
- remember: stores a labeled string in knowledge
- call: invokes a namespaced service action with args

## Errors
- Syntax errors return position and expected tokens
- Unknown identifiers are accepted in v0.1 and validated downstream

## Semantics
- Mission-scoped memory applies within the enclosing mission block
- Execution engine maps agent and call actions to orchestration operations

## Examples
mission alpha {
  set retries = 3;
  agent orchestrator do queue("alpha");
  call memory.store("alpha","ready");
  remember note "initialized";
}
