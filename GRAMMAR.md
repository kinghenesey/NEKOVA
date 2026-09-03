# NEKOVA Formal Grammar (EBNF)

**Version this grammar describes:** 2.0.0
**Status:** Reference — written directly against `nekova/parser/parser.py`
and its mixins (`async_parser.py`, `class_parser.py`, `match_parser.py`,
`web_parser.py`), not from memory or the docs site. This was the stable
spec **Phase 27** (NEKOVA Parser in NEKOVA — self-hosting milestone 2)
implemented `parser.nk` against; `tools/check_grammar_coverage.py`
continues to cross-check every parse method against it on every run.

## How this was produced, and how to keep it honest

Every rule below traces back to a specific `_parse_*` method (or, for the
four methods that don't follow that naming convention —
`parse_async_function`, `parse_class_definition`, `parse_new_instance`,
`parse_self_expr` — their un-prefixed equivalents in the mixin files).
`tools/check_grammar_coverage.py` (added alongside this file) cross-checks
that every parse method in the codebase has a corresponding rule here,
and fails CI if a new construct is added to the parser without a matching
grammar update — see that script for exactly how the check works.

This grammar does **not** attempt to describe expression precedence via
priority declarations (as a parser-generator grammar would); NEKOVA's
parser is hand-written recursive descent, so precedence is expressed
here the same way the parser expresses it — as a chain of rules, loosest
binding first, each one delegating to the next.

Notation is standard EBNF:
- `|` alternation, `[...]` optional, `{...}` zero-or-more, `(...)` grouping
- Literal tokens in `'single quotes'`
- `IDENTIFIER`, `STRING`, `INTEGER`, `FLOAT`, `MONEY`, `F_STRING` are
  lexer-level terminals (see [Lexical Grammar](#lexical-grammar))
- `NEWLINE` / `INDENT` / `DEDENT` are the lexer's Python-style
  significant-whitespace tokens

---

## Program structure

```ebnf
program        = { statement } ;

statement      = show_stmt | think_stmt | let_stmt | const_stmt
               | if_stmt | while_stmt | repeat_stmt | for_stmt | try_stmt
               | task_def | class_def | shape_def | schema_def | agent_def | error_def | enum_def
               | prompt_def | pipeline_def
               | sandbox_stmt | test_stmt | expect_stmt
               | retry_stmt | observe_stmt | mock_stmt
               | remember_stmt | recall_stmt | forget_stmt
               | converse_stmt | speak_stmt | listen_stmt
               | imagine_stmt | watch_stmt | every_stmt
               | match_stmt | route_stmt | serve_stmt
               | async_task_def | await_expr_stmt | stream_think_stmt
               | fetch_stmt | model_stmt | memory_stmt | autonomous_stmt
               | run_pipeline_stmt | pipeline_call_stmt
               | return_stmt | break_stmt | continue_stmt | pass_stmt
               | global_stmt | use_stmt | import_stmt | unpack_stmt
               | assert_stmt | raise_stmt | decorator_stmt | yield_stmt
               | new_instance_stmt | self_stmt
               | identifier_stmt        (* assignment or call *)
               ;

block          = ':' NEWLINE INDENT { statement } DEDENT
               | ':' statement ;            (* single-line body form *)

block_with_docstring
               = ':' NEWLINE INDENT
                   [ (STRING | F_STRING) NEWLINE ]   (* leading bare
                       string = docstring; unambiguous because a bare
                       string is otherwise never a valid statement *)
                   { statement }
                 DEDENT
               | ':' statement ;
```

---

## Declarations

```ebnf
let_stmt       = 'let' IDENTIFIER [ ':' IDENTIFIER ] '=' expression NEWLINE
               | 'let' list_destructure  '=' expression NEWLINE
               | 'let' dict_destructure  '=' expression NEWLINE ;

list_destructure
               = '[' destructure_targets ']'
               | '(' destructure_targets ')' ;   (* tuple-style, same
                                                      semantics *)
destructure_targets
               = IDENTIFIER { ',' IDENTIFIER } [ ',' '...' IDENTIFIER ]
               | '...' IDENTIFIER ;
               (* '...rest', if present, must be last and captures every
                  remaining item as a list *)

dict_destructure
               = '{' IDENTIFIER { ',' IDENTIFIER } '}' ;
               (* each name is both the key read and the bound variable *)

const_stmt     = 'const' IDENTIFIER [ ':' IDENTIFIER ] '=' expression NEWLINE ;
               (* deliberately simpler than let: no destructuring, no
                  captured think/pipeline/autonomous forms *)

unpack_stmt    = IDENTIFIER { ',' IDENTIFIER } '=' expression NEWLINE ;
               (* a, b, c = [1, 2, 3] *)

global_stmt    = 'global' IDENTIFIER { ',' IDENTIFIER } NEWLINE ;

task_def       = 'task' IDENTIFIER task_params [ '->' IDENTIFIER ] block_with_docstring ;

task_params    = '(' [ task_param { ',' task_param } ] ')' ;
task_param     = [ '*' ] IDENTIFIER [ ':' IDENTIFIER ] [ '=' expression ] ;
               (* order: name, optional type hint, optional default;
                  '*' marks a vararg parameter *)

async_task_def = ( 'async' 'func' | 'async' 'task' ) IDENTIFIER task_params block_with_docstring ;

prompt_def     = 'prompt' IDENTIFIER task_params ':' NEWLINE INDENT
                   (STRING | F_STRING) NEWLINE
                 DEDENT ;
               (* the body is exactly one string/f-string template —
                  no 'f' prefix needed for {var} interpolation inside it *)

class_def      = 'object' IDENTIFIER [ 'extends' IDENTIFIER ] ':' NEWLINE INDENT
                   { class_member }
                 DEDENT
               | 'class' IDENTIFIER [ 'extends' IDENTIFIER ] ':' NEWLINE INDENT
                   { class_member }
                 DEDENT ;
               (* 'object' and 'class' are interchangeable *)

class_member   = field_decl | init_def | method_def ;
field_decl     = IDENTIFIER ':' IDENTIFIER NEWLINE ;
init_def       = 'init' param_list block ;
method_def     = 'func' IDENTIFIER param_list block ;
param_list     = '(' [ IDENTIFIER [ ':' IDENTIFIER ] { ',' IDENTIFIER [ ':' IDENTIFIER ] } ] ')' ;

new_instance_stmt
               = 'new' IDENTIFIER '(' [ expression { ',' expression } ] ')' NEWLINE ;

self_stmt      = 'self' '.' IDENTIFIER [ '=' expression ] NEWLINE
               | 'self' '.' IDENTIFIER '(' [ expression { ',' expression } ] ')' NEWLINE ;

shape_def      = 'shape' IDENTIFIER ':' NEWLINE INDENT
                   { IDENTIFIER IDENTIFIER [ '=' expression ] NEWLINE }
                 DEDENT ;
               (* each line: field_name field_type [= default];
                  a field with no default is required — see
                  Interpreter._validate_shape_fields *)

schema_def     = 'schema' IDENTIFIER ':' NEWLINE INDENT
                   { IDENTIFIER ':' IDENTIFIER [ '=' expression ] NEWLINE }
                 DEDENT ;
               (* Phase 28: a named, reusable schema, structurally
                  identical to shape_def (name/type/default triples,
                  same required-unless-defaulted rule) but with
                  colon-separated fields and the text/number/boolean/
                  list/dict/any vocabulary that `think ... as schema
                  {...}` already validates against, rather than
                  shape's str/int/float/bool names. Deliberately a
                  separate keyword and rule from shape_def, not a
                  variant of it — see SchemaDefinition's docstring in
                  nodes.py for why. 'schema' is a soft keyword (like
                  'prompt'): only treated as this rule when followed
                  by IDENTIFIER ':' — see _looks_like_schema_def *)

agent_def      = 'agent' ( STRING | F_STRING ) ':' NEWLINE INDENT
                   { ( IDENTIFIER | 'model' ) ':' expression NEWLINE }
                 DEDENT ;
               (* Phase 28: a first-class agent declaration — compiles
                  down to the same agent_create/agent_tool calls the
                  function-call API already had (see agents_module.py),
                  so agents built either way interoperate freely.
                  Recognized field keys: 'goal', 'tools' (a list
                  literal — see AgentDefinition's docstring in
                  nodes.py for how its elements are read), 'model'.
                  Unknown keys are ignored, not an error, so this can
                  grow without breaking existing programs. 'model' is
                  also a hard keyword (the top-level `model "..."`
                  statement) — the field-key check accepts that
                  token specifically in addition to IDENTIFIER; any
                  other keyword colliding with a future field name
                  would need the same treatment. Usable as a let-RHS
                  (let researcher = agent "...": ...) via the same
                  .variable capture pattern think/autonomous parallel
                  already use — see _parse_let. 'agent' is a soft
                  keyword: only treated as this rule when followed by
                  a string then ':' — see _looks_like_agent_def *)

error_def      = 'error' IDENTIFIER ':' NEWLINE INDENT
                   { IDENTIFIER IDENTIFIER [ '=' expression ] NEWLINE }
                 DEDENT ;

enum_def       = 'enum' IDENTIFIER ':' IDENTIFIER { ',' IDENTIFIER } NEWLINE ;
               (* single-line member list; each member evaluates to its
                  own name as a string *)

decorator_stmt = '@' IDENTIFIER [ '(' [ expression { ',' expression } ] ')' ] NEWLINE
                 task_def ;
```

---

## Control flow

```ebnf
if_stmt        = 'if' expression block_with_docstring
                 { 'elif' expression block_with_docstring }
                 [ 'else' block_with_docstring ] ;

while_stmt     = 'while' expression block ;

repeat_stmt    = 'repeat' expression block ;
               (* NOTE: 'repeat(' with no space is instead a call to a
                  variable/function literally named 'repeat' — see
                  _parse_statement's REPEAT dispatch, which peeks for
                  '(' immediately after the keyword to disambiguate *)

for_stmt       = 'for' IDENTIFIER { ',' IDENTIFIER } 'in' expression block ;
               (* multiple comma-separated loop variables supported for
                  enumerate()/zip()-shaped iterables *)

try_stmt       = 'try' block
                 [ 'catch' [ IDENTIFIER ] block ]
                 [ 'finally' block ] ;

match_stmt     = 'match' expression ':' NEWLINE INDENT
                   { when_arm }
                   [ else_arm ]
                 DEDENT ;
when_arm       = 'when' expression ':' inline_or_block ;
else_arm       = 'else' ':' inline_or_block ;
inline_or_block
               = statement                          (* same line *)
               | NEWLINE INDENT { statement } DEDENT ;

return_stmt    = 'return' [ expression ] NEWLINE ;
break_stmt     = 'break' NEWLINE ;
continue_stmt  = 'continue' NEWLINE ;
pass_stmt      = 'pass' NEWLINE ;             (* 'pass' is a soft keyword —
                                                   matched as IDENTIFIER *)
yield_stmt     = 'yield' [ expression ] NEWLINE ;

assert_stmt    = 'assert' expression [ ',' STRING ] NEWLINE ;   (* soft keyword *)
raise_stmt     = 'raise' expression NEWLINE ;                   (* soft keyword *)
```

---

## AI-native constructs

```ebnf
think_stmt     = 'think' expression
                 [ 'as' think_format ]
                 { think_clause }
                 NEWLINE ;

think_format   = 'json' | 'list' | 'bool' | 'text'
               | 'schema' dict_literal
               | IDENTIFIER ;           (* a previously-defined shape name *)

think_clause   = 'using' ( expression | list_literal )
                    (* Phase 26c: a list gives a model fallback chain,
                       e.g. using ["model-a", "model-b", "local"] —
                       tried in order, each with its own transient-
                       failure retries, before falling to the next *)
               | 'with' 'budget' ':' ( expression | MONEY )
                    (* Phase 26c: a MONEY literal ($0.01) budgets by
                       estimated cost; a plain number budgets by
                       estimated token count — see
                       Interpreter._check_think_budget *)
               | 'when' 'error' ':' expression ;
               (* 'using', 'budget', 'error' are all soft keywords —
                  matched by identifier value, not reserved *)

               (* Phase 26c: when think_format names a shape, the
                  interpreter validates the response against that
                  shape's fields and, on a mismatch (missing required
                  field or wrong type), automatically re-prompts with
                  the specific problems named — up to 2 additional
                  attempts — before raising. See
                  Interpreter._validate_shape_fields /
                  _exec_ThinkAsStatement. This is interpreter behavior,
                  not additional grammar — the syntax is unchanged. *)

think_expr     = 'think' expression [ 'as' think_format ] { think_clause } ;
               (* think used inline — return think "..." as json, etc.
                  Same grammar as think_stmt, used where an expression
                  is expected instead of a standalone statement. *)

stream_think_stmt
               = 'stream' 'think' expression ':' NEWLINE
                   [ INDENT ]
                   'each' IDENTIFIER ':' block
                   [ DEDENT ] ;
               (* Real, chunk-by-chunk streaming via the Anthropic SDK
                  directly (see async_interpreter.py::_stream_think_async)
                  — requires the anthropic package and a real API key,
                  no mock-provider fallback. Distinct from the
                  think_stream(...) BUILTIN FUNCTION below, which is
                  provider-agnostic (works under the mock provider) and
                  used with an ordinary for-loop instead of this
                  dedicated statement form. Both are real, current
                  constructs — kept separate deliberately, not
                  duplicative: this one for genuine low-level SDK
                  streaming, think_stream() for a portable, testable
                  default. *)

               (* think_stream(...) itself is not new grammar — it is
                  a builtin function (see Interpreter._register_builtins)
                  usable anywhere a call expression is, most commonly
                  as a for-loop's iterable:
                      for chunk in think_stream("..."):
                          show chunk
                  Phase 26c made this genuinely lazy — see
                  _exec_ForStatement's _NEKOVAStreamChunks handling. *)

remember_stmt  = 'remember' STRING '=' expression NEWLINE ;
recall_stmt    = 'recall' STRING NEWLINE ;
recall_expr    = 'recall' STRING [ 'or' expression ] ;
forget_stmt    = 'forget' ( STRING | 'all' ) NEWLINE ;

converse_stmt  = 'converse' block ;
               (* every think/listen inside automatically carries prior
                  turns as context *)

speak_stmt     = 'speak' expression NEWLINE ;
listen_stmt    = 'listen' [ expression ] NEWLINE ;

imagine_stmt   = 'imagine' expression [ 'as' ( 'url' | 'path' ) ] NEWLINE ;
imagine_expr   = 'imagine' expression [ 'as' ( 'url' | 'path' ) ] ;

sandbox_stmt   = 'sandbox' ( 'strict' | 'relaxed' )
                 [ 'allow' ':' '[' [ IDENTIFIER { ',' IDENTIFIER } ] ']' ]
                 block ;
               (* Phase 26c: the allow-list is a bracketed list of bare
                  task-name identifiers captured directly as strings at
                  parse time (not general expressions — these are
                  capability names being declared). When present, only
                  calls to user-defined tasks named in the list are
                  permitted inside the block; builtins remain
                  unrestricted. Nested sandboxes intersect allow-lists.
                  See Interpreter._exec_SandboxStatement /
                  _exec_CallExpression. *)

test_stmt      = 'test' STRING ':' NEWLINE INDENT { expect_stmt } DEDENT
               | 'test' STRING 'repeat' expression 'times'
                 [ ',' 'expect' 'at' 'least' expression 'passes' ]
                 ':' NEWLINE INDENT { statement } DEDENT ;
               (* Phase 26c probabilistic form: runs the body N times;
                  a run counts as one pass only if every expect/
                  expect_snapshot inside it succeeds. Overall test
                  passes if run_passes >= min_passes (which defaults to
                  the full repeat count if 'expect at least' is
                  omitted — no silent tolerance by default). 'repeat',
                  'times', 'expect', 'at', 'least', 'passes' are all
                  soft keywords in this position. See
                  Interpreter._exec_probabilistic_test. *)

expect_stmt    = 'expect' expression NEWLINE ;
mock_stmt      = 'mock' 'think' 'as' expression NEWLINE ;
               (* only meaningful inside a test block *)

retry_stmt     = 'retry' expression 'times' [ 'with' ( 'exponential' | 'linear' ) 'backoff' ]
                 block
                 [ 'fallback' block ] ;

observe_stmt   = 'observe' STRING [ 'with' 'tags' dict_literal ] block ;

pipeline_def   = 'pipeline' IDENTIFIER ':' NEWLINE INDENT
                   { pipeline_step }
                 DEDENT ;
pipeline_step  = 'collect' expression NEWLINE
               | 'process' 'with' 'ai' NEWLINE
               | 'generate' IDENTIFIER NEWLINE
               | 'save' 'to' IDENTIFIER NEWLINE ;
run_pipeline_stmt
               = 'run' 'pipeline' IDENTIFIER NEWLINE
               | IDENTIFIER '=' 'run' 'pipeline' IDENTIFIER NEWLINE ;
pipeline_call_stmt
               = STRING { '->' expression } NEWLINE ;
               (* "prompt" -> agent1 -> agent2 *)

autonomous_stmt
               = 'autonomous' 'parallel' block ;

memory_stmt    = 'memory' IDENTIFIER ':' NEWLINE INDENT
                   { IDENTIFIER '=' expression NEWLINE }
                 DEDENT ;

model_stmt     = 'model' STRING NEWLINE ;

every_stmt     = 'every' duration [ INTEGER 'times' ] block ;
duration       = INTEGER ( 's' | 'm' ) ;    (* e.g. 5s, 1m — lexed as
                                                 part of the identifier
                                                 following the integer *)

watch_stmt     = 'watch' ( STRING | IDENTIFIER ) block ;

fetch_stmt     = 'fetch' expression
                 [ 'method' STRING ]
                 [ 'headers' dict_literal ]
                 [ 'body' dict_literal ]
                 NEWLINE ;

await_expr_stmt
               = 'await' expression NEWLINE ;
```

---

## Web DSL (Phase 7)

```ebnf
route_stmt     = 'route' IDENTIFIER STRING block ;
               (* IDENTIFIER is the HTTP method: GET, POST, PUT, DELETE, ... *)

serve_stmt     = 'serve' [ 'port' ':' expression ] NEWLINE ;
```

---

## Module system

```ebnf
use_stmt       = 'use' IDENTIFIER NEWLINE ;

import_stmt    = 'import' STRING NEWLINE
               | 'import' IDENTIFIER 'from' STRING NEWLINE
               | 'import' IDENTIFIER { ',' IDENTIFIER } 'from' STRING NEWLINE ;
```

---

## Output

```ebnf
show_stmt      = 'show' expression { expression } NEWLINE ;
               (* space-separated multiple expressions *)

identifier_stmt
               = IDENTIFIER '=' expression NEWLINE                    (* assignment *)
               | IDENTIFIER augmented_op expression NEWLINE           (* a += 1 etc. *)
               | IDENTIFIER '(' [ call_args ] ')' NEWLINE ;           (* call statement *)

augmented_op   = '+=' | '-=' | '*=' | '/=' ;
```

---

## Expressions

Precedence, loosest binding first — each rule delegates to the next,
matching the recursive-descent chain in `parser.py` exactly:

```ebnf
expression     = pipe_expr ;

pipe_expr      = ternary_expr { '|>' call_expr } ;
               (* a |> f(x)  ==  f(a, x) — piped value is inserted as
                  the first argument *)

ternary_expr   = logical_or_expr [ 'if' logical_or_expr 'else' ternary_expr ] ;

logical_or_expr
               = logical_and_expr { 'or' logical_and_expr } ;

logical_and_expr
               = comparison_expr { 'and' comparison_expr } ;

comparison_expr
               = addition_expr { comparison_op addition_expr } ;
comparison_op  = '==' | '!=' | '<' | '<=' | '>' | '>='
               | 'in' | 'not' 'in' | 'is' | 'is' 'not' ;

addition_expr  = multiplication_expr { ( '+' | '-' ) multiplication_expr } ;

multiplication_expr
               = unary_expr { ( '*' | '/' | '%' | '**' ) unary_expr } ;

unary_expr     = ( '-' | 'not' ) unary_expr
               | primary_expr ;

primary_expr   = INTEGER | FLOAT | MONEY | BOOLEAN | 'null'
               | STRING postfix_chain
               | F_STRING
               | IDENTIFIER [ call_args ] postfix_chain
               | list_literal | set_literal | dict_literal
               | '(' expression ')'
               | think_expr | recall_expr | imagine_expr
               | 'new' IDENTIFIER '(' [ call_args ] ')'
               | 'self' '.' IDENTIFIER [ '(' [ call_args ] ')' ] ;

postfix_chain  = { index_or_slice | method_or_prop | optional_chain } ;
index_or_slice = '[' expression [ ':' [ expression ] ] ']' ;
method_or_prop = '.' IDENTIFIER [ '(' [ call_args ] ')' ] ;
optional_chain = '?.' IDENTIFIER [ '(' [ call_args ] ')' ] ;
               (* short-circuits to null if the left side is null,
                  instead of raising *)

call_args      = expression { ',' expression } ;

list_literal   = '[' [ list_items ] ']' ;
list_items     = list_item { ',' list_item } ;
list_item      = expression | '...' expression ;      (* spread *)

set_literal    = '{' [ expression { ',' expression } ] '}' ;
               (* disambiguated from dict_literal at the LBRACE dispatch
                  point: a dict entry always has 'key : value' shape;
                  a set element never does. Empty {} is a dict. *)

dict_literal   = '{' [ dict_items ] '}' ;
dict_items     = dict_item { ',' dict_item } ;
dict_item      = ( IDENTIFIER | STRING ) ':' expression
               | '...' expression ;                   (* spread *)
```

---

## Lexical Grammar

```ebnf
IDENTIFIER     = letter_or_underscore { letter_or_underscore | digit } ;

INTEGER        = digit { digit } ;
FLOAT          = digit { digit } '.' digit { digit }
                 [ ( 'e' | 'E' ) [ '+' | '-' ] digit { digit } ] ;
MONEY          = '$' digit { digit } [ '.' digit { digit } ] ;
               (* Phase 26c — a plain decimal amount only; deliberately
                  simpler than FLOAT (no hex, no underscores, no
                  scientific notation) since a cost budget is always
                  something someone typed by hand. See
                  Lexer._read_money. *)

STRING         = '"' { any_char_except_unescaped_quote } '"'
               | "'" { any_char_except_unescaped_quote } "'"
               | '"""' { any_char } '"""' ;      (* triple-quoted *)

F_STRING       = 'f' STRING ;
               (* {expr} placeholders inside are parsed as nested
                  expressions at parse time, not string-substituted at
                  runtime — see Parser._parse_fstring *)

BOOLEAN        = 'true' | 'false' ;
NULL           = 'null' ;

COMMENT        = '#' { any_char_except_newline } ;   (* not a token —
                                                          stripped by
                                                          the lexer *)
```

### Reserved keywords

```
and       as        assert    async     autonomous  await     break
catch     class     collect   const     continue    converse  each
elif      else      enum      error     every       expect    fallback
false     fetch     for       forget    func        generate  global
if        imagine   import    in        init        let       listen
match     memory    mock      model     new         not       null
object    observe   or        parallel  pass        pipeline  prompt
raise     recall    relaxed   remember  repeat      retry     return
route     run       sandbox   save      self        serve     shape
show      speak     stream    strict    task        test      think
true      try       use       watch     when        while     with
yield
```

### Soft (contextual) keywords

These are matched by identifier *value*, not reserved as their own
token type — they remain valid as ordinary variable/function names
everywhere outside the specific position listed. This is a deliberate,
consistent convention across the grammar (see `_parse_test`,
`_parse_retry`, `_parse_sandbox`'s docstrings for the reasoning):

```
allow       at          backoff     budget      each (route context)
error       exponential extends     finally     least
linear      passes      port        prompt      raise
tags        times       to          using
```

---

## Known grammar gaps (tracked, not yet closed)

Honesty over completeness — these exist in the real parser but aren't
fully captured above, either because they're deep in mixin
implementation detail or because coverage-checking them surfaced real
ambiguity worth resolving in Phase 27 itself rather than papering over
here:

- `_parse_decorator`'s exact interaction with `async_task_def` (can a
  decorated task also be async? — parser allows it, grammar above
  doesn't show the combination explicitly)
- F-string nested-expression grammar (what's allowed inside `{...}` —
  currently "the full expression grammar," unverified against edge
  cases like nested f-strings inside an f-string placeholder)
- Exact precedence interaction between `?.` optional chaining and `|>`
  pipe when both appear in one expression

`tools/check_grammar_coverage.py` is the authoritative, automated check
for the first category (every parse method has *a* rule); the other two
are semantic/precedence gaps a coverage checker can't catch by itself —
tracked here by hand instead.