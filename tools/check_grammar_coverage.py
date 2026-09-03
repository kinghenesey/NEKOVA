#!/usr/bin/env python3
# =============================================================
# NEKOVA — Grammar Coverage Checker  (Phase 27 prerequisite)
# =============================================================
# GRAMMAR.md is meant to be the honest, current spec of what
# nekova/parser/parser.py (and its mixins) actually do — not an
# idealized version of it. This script is what keeps that true
# over time: it walks every real parse method in the codebase and
# checks it's accounted for in GRAMMAR.md, via an explicit mapping
# table below.
#
# The mapping is deliberately EXPLICIT rather than inferred by
# fuzzy name-matching ("_parse_if" probably means "if_stmt", but
# "probably" isn't good enough for a check that's supposed to catch
# drift) — every real parse method must have a line in
# PARSE_METHOD_TO_GRAMMAR_RULES below, and every rule name it names
# must actually exist in GRAMMAR.md. Adding a new parse method
# without updating both this mapping and GRAMMAR.md itself is
# exactly the kind of drift this script exists to catch.
#
# Usage:
#   python3 tools/check_grammar_coverage.py
# Exit code 0 = grammar and parser are in sync. Exit code 1 = drift
# found, with a specific listing of what's missing.
# =============================================================

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAMMAR_PATH = os.path.join(REPO_ROOT, "GRAMMAR.md")

PARSE_FILES = [
    "nekova/parser/parser.py",
    "nekova/parser/async_parser.py",
    "nekova/parser/class_parser.py",
    "nekova/parser/match_parser.py",
    "nekova/parser/web_parser.py",
]

# Methods that are drivers/dispatchers/aliases/helpers rather than
# their own grammar production — each maps to the rule(s) it feeds
# into or dispatches across, not a brand-new rule of its own.
PARSE_METHOD_TO_GRAMMAR_RULES = {
    # Top-level driver / dispatcher — not productions themselves,
    # they route to the 'statement' alternation as a whole.
    "parse_best_effort":          ["program"],
    "_parse_all_statements":      ["program"],
    "_parse_statement":           ["statement"],

    # Thin aliases used by the async mixin — delegate straight to
    # the real productions, not distinct rules.
    "parse_block":                ["block"],
    "parse_expr":                 ["expression"],

    # One rule each, straightforward.
    "_parse_speak":                ["speak_stmt"],
    "_parse_listen_stmt":          ["listen_stmt"],
    "_parse_every":                ["every_stmt"],
    "_parse_test":                 ["test_stmt"],
    "_parse_expect":               ["expect_stmt"],
    "_parse_imagine":              ["imagine_stmt"],
    "_parse_imagine_expr":         ["imagine_expr"],
    "_parse_shape":                ["shape_def"],
    "_parse_schema_def":           ["schema_def"],
    "_parse_agent_def":            ["agent_def"],
    "_parse_watch":                ["watch_stmt"],
    "_parse_yield":                ["yield_stmt"],
    "_parse_decorator":            ["decorator_stmt"],
    "_parse_error_def":            ["error_def"],
    "_parse_assert":               ["assert_stmt"],
    "_parse_raise":                ["raise_stmt"],
    "_parse_show":                 ["show_stmt"],
    "_parse_think_using_model":    ["think_clause"],
    "_parse_think_with_budget":    ["think_clause"],
    "_parse_think_on_error":       ["think_clause"],
    "_parse_think":                ["think_stmt", "think_expr"],
    "_parse_remember":             ["remember_stmt"],
    "_parse_recall":               ["recall_stmt"],
    "_parse_think_expr":           ["think_expr"],
    "_parse_recall_expr":          ["recall_expr"],
    "_parse_forget":               ["forget_stmt"],
    "_parse_model":                ["model_stmt"],
    "_parse_pipeline":             ["pipeline_call_stmt"],
    "_parse_autonomous":           ["autonomous_stmt"],
    "_parse_memory":               ["memory_stmt"],
    "_parse_sandbox":              ["sandbox_stmt"],
    "_parse_pipeline_def":         ["pipeline_def", "pipeline_step"],
    "_parse_run_pipeline":         ["run_pipeline_stmt"],
    "_parse_if":                   ["if_stmt"],
    "_parse_repeat":               ["repeat_stmt"],
    "_parse_while":                ["while_stmt"],
    "_parse_try":                  ["try_stmt"],
    "_parse_for":                  ["for_stmt"],
    "_parse_task_param_list":      ["task_params", "task_param"],
    "_parse_task":                 ["task_def"],
    "_parse_prompt":               ["prompt_def"],
    "_parse_prompt_body":          ["prompt_def"],
    "_parse_retry":                ["retry_stmt"],
    "_parse_observe":              ["observe_stmt"],
    "_parse_mock":                 ["mock_stmt"],
    "_parse_return":               ["return_stmt"],
    "_parse_global":               ["global_stmt"],
    "_parse_unpack":               ["unpack_stmt"],
    "_parse_use":                  ["use_stmt"],
    "_parse_import":               ["import_stmt"],
    "_parse_converse":             ["converse_stmt"],
    "_parse_enum":                 ["enum_def"],
    "_parse_const":                ["const_stmt"],
    "_parse_let":                  ["let_stmt"],
    "_parse_list_destructure":     ["list_destructure", "destructure_targets"],
    "_parse_dict_destructure":     ["dict_destructure"],
    "_parse_identifier_statement": ["identifier_stmt"],
    "_parse_block_with_docstring": ["block_with_docstring"],
    "_parse_block":                ["block"],
    "_parse_expression":           ["expression"],
    "_parse_ternary":              ["ternary_expr"],
    "_parse_logical_or":           ["logical_or_expr"],
    "_parse_logical_and":          ["logical_and_expr"],
    "_parse_comparison":           ["comparison_expr", "comparison_op"],
    "_parse_addition":             ["addition_expr"],
    "_parse_multiplication":       ["multiplication_expr"],
    "_parse_unary":                ["unary_expr"],
    "_parse_primary":              ["primary_expr", "postfix_chain"],
    "_parse_list":                 ["list_literal", "list_items", "list_item"],
    "_parse_set":                  ["set_literal"],
    "_parse_dict":                 ["dict_literal", "dict_items", "dict_item"],
    "_parse_fstring":              ["F_STRING"],

    # Mixins
    "parse_async_function":        ["async_task_def"],
    "parse_await_expr":            ["await_expr_stmt"],
    "parse_stream_think":          ["stream_think_stmt"],
    "parse_fetch_expr":            ["fetch_stmt"],
    "parse_class_definition":      ["class_def", "class_member"],
    "parse_new_instance":          ["new_instance_stmt"],
    "parse_self_expr":             ["self_stmt"],
    "_parse_param_list":           ["param_list"],
    "_parse_match":                ["match_stmt"],
    "_parse_inline_or_block":      ["inline_or_block"],
    "_parse_route":                ["route_stmt"],
    "_parse_serve":                ["serve_stmt"],
}


def find_parse_methods() -> dict:
    """Returns {method_name: file_path} for every parse method in
    the codebase, across parser.py and every mixin file."""
    found = {}
    for rel_path in PARSE_FILES:
        full_path = os.path.join(REPO_ROOT, rel_path)
        with open(full_path, encoding="utf-8") as f:
            content = f.read()
        for name in re.findall(r"def ((?:_)?parse_\w+)\(", content):
            found[name] = rel_path
    return found


def find_grammar_rules() -> set:
    """Returns the set of every rule name defined in GRAMMAR.md —
    any line (inside an ```ebnf fenced block) of the form
    'rule_name = ...' or 'rule_name\\n = ...' (this grammar wraps
    long rule names onto their own line before the '=')."""
    with open(GRAMMAR_PATH, encoding="utf-8") as f:
        content = f.read()

    rules = set()
    in_block = False
    pending_name = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```ebnf"):
            in_block = True
            continue
        if stripped == "```":
            in_block = False
            pending_name = None
            continue
        if not in_block or not stripped:
            continue

        # A line that's just an identifier (rule name on its own
        # line, '=' follows on the next line).
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", stripped):
            pending_name = stripped
            continue

        # 'name = ...' on one line
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
        if m:
            rules.add(m.group(1))
            pending_name = None
            continue

        # continuation of a pending 'name\n= ...' split
        if pending_name and stripped.startswith("="):
            rules.add(pending_name)
            pending_name = None

    return rules


def main() -> int:
    parse_methods = find_parse_methods()
    grammar_rules = find_grammar_rules()

    unmapped = []
    stale_mapping_targets = []

    for method_name, file_path in sorted(parse_methods.items()):
        if method_name not in PARSE_METHOD_TO_GRAMMAR_RULES:
            unmapped.append((method_name, file_path))
            continue
        for rule_name in PARSE_METHOD_TO_GRAMMAR_RULES[method_name]:
            if rule_name not in grammar_rules:
                stale_mapping_targets.append((method_name, rule_name))

    # Also flag mapping entries for methods that no longer exist —
    # catches the other direction of drift (a method was removed or
    # renamed but the mapping/grammar weren't updated).
    removed_methods = [
        name for name in PARSE_METHOD_TO_GRAMMAR_RULES
        if name not in parse_methods
    ]

    ok = not unmapped and not stale_mapping_targets and not removed_methods

    print(f"Parse methods found:  {len(parse_methods)}")
    print(f"Grammar rules found:  {len(grammar_rules)}")
    print()

    if unmapped:
        print("UNMAPPED parse methods (exist in code, no entry in "
              "PARSE_METHOD_TO_GRAMMAR_RULES):")
        for name, path in unmapped:
            print(f"  - {name}  ({path})")
        print()

    if stale_mapping_targets:
        print("STALE mapping targets (mapping points at a grammar "
              "rule that doesn't exist in GRAMMAR.md):")
        for method_name, rule_name in stale_mapping_targets:
            print(f"  - {method_name} -> '{rule_name}' not found")
        print()

    if removed_methods:
        print("STALE mapping entries (method no longer exists in "
              "the codebase — was it renamed?):")
        for name in removed_methods:
            print(f"  - {name}")
        print()

    if ok:
        print("OK — every parse method is accounted for in GRAMMAR.md.")
        return 0
    else:
        print("FAILED — grammar coverage check found drift. Update "
              "GRAMMAR.md and/or PARSE_METHOD_TO_GRAMMAR_RULES in "
              "this script to match.")
        return 1


if __name__ == "__main__":
    sys.exit(main())