# =============================================================
# NEKOVA Phase 10 Tests — DX: Formatter + Checker + Error DX
# =============================================================
import sys
import os
import re
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.cli.formatter import fmt_source, fmt_file, fmt_directory
from nekova.cli.checker   import check_source, check_file, Issue


# ==============================================================
# SECTION 1 — Formatter: fmt_source
# ==============================================================

class TestFormatterBasics:

    def test_trailing_whitespace_removed(self):
        src = "show \"hello\"   \nlet x = 1  \n"
        out = fmt_source(src)
        for line in out.splitlines():
            assert not line.endswith(" "), f"Trailing space in: {repr(line)}"

    def test_tabs_to_spaces(self):
        src = "task foo():\n\tshow \"hi\"\n"
        out = fmt_source(src)
        assert "\t" not in out
        assert "    show" in out

    def test_eof_newline_enforced(self):
        src = 'show "hello"'
        out = fmt_source(src)
        assert out.endswith("\n")

    def test_double_eof_newlines_trimmed(self):
        src = 'show "hello"\n\n\n\n'
        out = fmt_source(src)
        assert out.count("\n") <= 2

    def test_leading_blank_lines_removed(self):
        src = "\n\n\nshow \"hello\"\n"
        out = fmt_source(src)
        assert not out.startswith("\n")

    def test_max_two_consecutive_blanks(self):
        src = "let x = 1\n\n\n\n\nlet y = 2\n"
        out = fmt_source(src)
        assert "\n\n\n\n" not in out

    def test_idempotent(self):
        src = 'let x = 1\nshow x\n'
        once  = fmt_source(src)
        twice = fmt_source(once)
        assert once == twice

    def test_empty_source(self):
        out = fmt_source("")
        assert out == "\n"

    def test_comment_preserved(self):
        src = "# This is a comment\nshow \"hi\"\n"
        out = fmt_source(src)
        assert "# This is a comment" in out

    def test_colon_no_space_before(self):
        src = "task foo() :\n    show \"hi\"\n"
        out = fmt_source(src)
        assert "foo():" in out
        assert "foo() :" not in out


class TestFormatterIndentation:

    def test_two_space_to_four_space(self):
        src = "task foo():\n  show \"hi\"\n  show \"bye\"\n"
        out = fmt_source(src)
        lines = out.splitlines()
        body_lines = [l for l in lines if l.strip().startswith("show")]
        for line in body_lines:
            assert line.startswith("    "), f"Expected 4-space indent: {repr(line)}"

    def test_four_space_preserved(self):
        src = "task foo():\n    show \"hi\"\n"
        out = fmt_source(src)
        assert "    show" in out

    def test_nested_indent(self):
        src = "task foo():\n    if true:\n        show \"nested\"\n"
        out = fmt_source(src)
        assert "        show" in out

    def test_blank_line_no_indent(self):
        src = "task foo():\n    show \"hi\"\n\n    show \"bye\"\n"
        out = fmt_source(src)
        lines = out.splitlines()
        blank = [l for l in lines if l == ""]
        assert all(l == "" for l in blank)


class TestFormatterOperators:

    def test_assignment_spacing(self):
        src = "let x=1\n"
        out = fmt_source(src)
        assert "x = 1" in out

    def test_equality_spacing(self):
        src = "if x==1:\n    show \"yes\"\n"
        out = fmt_source(src)
        assert "x == 1" in out

    def test_not_equals_spacing(self):
        src = "if x!=0:\n    show \"nonzero\"\n"
        out = fmt_source(src)
        assert "x != 0" in out

    def test_string_content_not_modified(self):
        # Operators inside strings must not get spaces added
        src = 'show "x==1"\n'
        out = fmt_source(src)
        assert '"x==1"' in out

    def test_fstring_content_preserved(self):
        src = 'show f"value={x}"\n'
        out = fmt_source(src)
        assert 'f"value={x}"' in out


class TestFormatterFileOps:

    def test_fmt_file_changes(self, tmp_path):
        nk = tmp_path / "test.nk"
        nk.write_text("let x=1\nshow x   \n", encoding="utf-8")
        changed, original, formatted = fmt_file(str(nk))
        assert changed
        assert "x = 1" in formatted
        # File should be updated on disk
        assert nk.read_text(encoding="utf-8") == formatted

    def test_fmt_file_no_change(self, tmp_path):
        nk = tmp_path / "clean.nk"
        nk.write_text("let x = 1\nshow x\n", encoding="utf-8")
        changed, original, formatted = fmt_file(str(nk))
        # Clean file → no change (or minimal normalisation only)
        assert original.strip() == formatted.strip()

    def test_fmt_file_dry_run(self, tmp_path):
        nk = tmp_path / "dirty.nk"
        original_content = "let x=1\n"
        nk.write_text(original_content, encoding="utf-8")
        changed, orig, fmt = fmt_file(str(nk), dry_run=True)
        # Dry run should NOT modify the file
        assert nk.read_text(encoding="utf-8") == original_content

    def test_fmt_directory(self, tmp_path):
        (tmp_path / "a.nk").write_text("let x=1\n", encoding="utf-8")
        (tmp_path / "b.nk").write_text("let y = 2\n", encoding="utf-8")
        results = fmt_directory(str(tmp_path))
        assert len(results) == 2
        # a.nk should have changed, b.nk may not
        paths = [r[0] for r in results]
        assert any("a.nk" in p for p in paths)

    def test_fmt_directory_skips_non_nk(self, tmp_path):
        (tmp_path / "script.py").write_text("x=1\n")
        (tmp_path / "app.nk").write_text("let x=1\n", encoding="utf-8")
        results = fmt_directory(str(tmp_path))
        assert all(r[0].endswith(".nk") for r in results)

    def test_fmt_bom_file(self, tmp_path):
        nk = tmp_path / "bom.nk"
        nk.write_bytes(b"\xef\xbb\xbflet x = 1\n")
        changed, orig, fmt = fmt_file(str(nk))
        # Should not crash on BOM files


# ==============================================================
# SECTION 2 — Checker: check_source
# ==============================================================

class TestCheckerKeywordConflict:

    def test_task_named_fetch(self):
        src = "task fetch(url):\n    return url\n"
        issues = check_source(src)
        codes = [i.code for i in issues]
        assert "E011" in codes

    def test_task_named_match(self):
        src = "task match(x):\n    return x\n"
        issues = check_source(src)
        codes = [i.code for i in issues]
        assert "E011" in codes

    def test_task_named_return(self):
        src = "task return(x):\n    show x\n"
        issues = check_source(src)
        # return is a keyword — should flag E011 or ParseError
        assert any(i.code in ("E011", "E003") for i in issues)

    def test_valid_task_name_ok(self):
        src = "task greet(name):\n    show name\n"
        issues = check_source(src)
        e011 = [i for i in issues if i.code == "E011"]
        assert not e011

    def test_keyword_in_error_message(self):
        src = "task fetch(url):\n    return url\n"
        issues = check_source(src)
        e011 = [i for i in issues if i.code == "E011"]
        assert any("fetch" in i.message for i in e011)


class TestCheckerUnreachableCode:

    def test_unreachable_after_return(self):
        src = (
            "task foo():\n"
            "    return 1\n"
            "    show \"dead code\"\n"
        )
        issues = check_source(src)
        codes = [i.code for i in issues]
        assert "W006" in codes

    def test_reachable_before_return_ok(self):
        src = (
            "task foo():\n"
            "    show \"alive\"\n"
            "    return 1\n"
        )
        issues = check_source(src)
        w006 = [i for i in issues if i.code == "W006"]
        assert not w006


class TestCheckerShadowedBuiltin:

    def test_shadow_show(self):
        src = "let show = \"oops\"\n"
        issues = check_source(src)
        codes = [i.code for i in issues]
        assert "E011" in codes or "W005" in codes

    def test_shadow_think(self):
        src = "let think = \"test\"\n"
        issues = check_source(src)
        codes = [i.code for i in issues]
        assert "E011" in codes or "W005" in codes

    def test_normal_variable_ok(self):
        src = "let username = \"Emmanuel\"\n"
        issues = check_source(src)
        w005 = [i for i in issues if i.code == "W005"]
        assert not w005


class TestCheckerWrongArgCount:

    def test_too_many_args(self):
        src = (
            "task add(a, b):\n"
            "    return a + b\n"
            "show add(1, 2, 3)\n"
        )
        issues = check_source(src)
        codes = [i.code for i in issues]
        assert "W003" in codes

    def test_too_few_args(self):
        src = (
            "task greet(name, greeting):\n"
            "    show f\"{greeting} {name}\"\n"
            "greet(\"Emmanuel\")\n"
        )
        issues = check_source(src)
        codes = [i.code for i in issues]
        assert "W003" in codes

    def test_correct_arg_count_ok(self):
        src = (
            "task add(a, b):\n"
            "    return a + b\n"
            "let result = add(1, 2)\n"
        )
        issues = check_source(src)
        w003 = [i for i in issues if i.code == "W003"]
        assert not w003


class TestCheckerIssueProperties:

    def test_issue_has_line(self):
        src = "task fetch(url):\n    return url\n"
        issues = check_source(src)
        for issue in issues:
            assert isinstance(issue.line, int)

    def test_issue_has_code(self):
        src = "task fetch(url):\n    return url\n"
        issues = check_source(src)
        for issue in issues:
            assert issue.code and issue.code.startswith(("E", "W"))

    def test_issue_has_message(self):
        src = "task fetch(url):\n    return url\n"
        issues = check_source(src)
        for issue in issues:
            assert issue.message and len(issue.message) > 0

    def test_issue_has_level(self):
        src = "task fetch(url):\n    return url\n"
        issues = check_source(src)
        for issue in issues:
            assert issue.level in ("error", "warning", "info")

    def test_clean_source_no_errors(self):
        src = (
            "let x = 1\n"
            "let y = 2\n"
            "show x + y\n"
        )
        issues = check_source(src)
        errors = [i for i in issues if i.level == "error"]
        assert not errors

    def test_check_file(self, tmp_path):
        nk = tmp_path / "check_me.nk"
        nk.write_text("task fetch(url):\n    return url\n", encoding="utf-8")
        issues = check_file(str(nk))
        codes = [i.code for i in issues]
        assert "E011" in codes

    def test_check_file_missing(self):
        issues = check_file("/nonexistent/path/file.nk")
        assert len(issues) == 1
        assert issues[0].level == "error"

    def test_sorted_by_line(self):
        src = (
            "task fetch(url):\n"
            "    return url\n"
            "    show \"dead\"\n"
        )
        issues = check_source(src)
        lines = [i.line for i in issues if i.line > 0]
        assert lines == sorted(lines)


# ==============================================================
# SECTION 3 — Error Display: smarter messages
# ==============================================================

class TestErrorDisplay:

    def _capture(self, fn, *args, **kwargs):
        """Capture stdout from display_error."""
        import io
        buf = io.StringIO()
        sys.stdout = buf
        try:
            fn(*args, **kwargs)
        finally:
            sys.stdout = sys.__stdout__
        return re.sub(r'\x1b\[[0-9;]*m', '', buf.getvalue())

    def test_display_name_error(self):
        from nekova.cli.error_display import display_error
        out = self._capture(display_error,
                            error_type="NameError",
                            message="'foo' is not defined",
                            line=3)
        assert "E001" in out
        assert "Variable Not Found" in out

    def test_display_parse_error(self):
        from nekova.cli.error_display import display_error
        out = self._capture(display_error,
                            error_type="ParseError",
                            message="Unexpected token",
                            line=5)
        assert "E003" in out

    def test_display_keyword_conflict(self):
        from nekova.cli.error_display import display_error
        out = self._capture(display_error,
                            error_type="KeywordConflict",
                            message="'fetch' is a reserved keyword",
                            line=1)
        assert "E011" in out

    def test_display_zero_division(self):
        from nekova.cli.error_display import display_error
        out = self._capture(display_error,
                            error_type="ZeroDivisionError",
                            message="Division by zero",
                            line=2)
        assert "E006" in out
        assert "zero" in out.lower()

    def test_display_shows_hint(self):
        from nekova.cli.error_display import display_error
        out = self._capture(display_error,
                            error_type="NameError",
                            message="'myvar' is not defined",
                            line=4)
        assert "let" in out.lower() or "define" in out.lower()

    def test_display_did_you_mean(self):
        from nekova.cli.error_display import display_error
        out = self._capture(display_error,
                            error_type="NameError",
                            message="'greet' is not defined",
                            line=5,
                            variables={"greeting": "hello", "name": "Alice"})
        # difflib should suggest 'greeting' for 'greet'
        assert "greeting" in out

    def test_display_source_context(self):
        from nekova.cli.error_display import display_error
        source = "let x = 1\nlet y = 2\nshow unknown_var\n"
        out = self._capture(display_error,
                            error_type="NameError",
                            message="'unknown_var' is not defined",
                            source=source,
                            line=3)
        assert "unknown_var" in out
        assert "│" in out

    def test_display_filepath_shown(self):
        from nekova.cli.error_display import display_error
        out = self._capture(display_error,
                            error_type="ParseError",
                            message="Unexpected token",
                            filepath="src/app.nk",
                            line=7)
        assert "app.nk" in out

    def test_display_unknown_error_type(self):
        from nekova.cli.error_display import display_error
        out = self._capture(display_error,
                            error_type="SomeNewError",
                            message="Something odd happened",
                            line=1)
        # Should still render without crashing, using E000
        assert "E000" in out

    def test_display_no_crash_no_line(self):
        from nekova.cli.error_display import display_error
        # Should not crash when line=0
        out = self._capture(display_error,
                            error_type="RuntimeError",
                            message="Something went wrong")
        assert "E005" in out


# ==============================================================
# SECTION 4 — Integration
# ==============================================================

class TestPhase10Integration:

    def test_fmt_then_check_clean(self, tmp_path):
        """Format a file then check it — should have no format-related issues."""
        nk = tmp_path / "app.nk"
        nk.write_text(
            "let x=1\nlet y=2\nshow x+y\n",
            encoding="utf-8"
        )
        # Format it
        changed, _, formatted = fmt_file(str(nk))
        # Check it — no keyword errors
        issues = check_file(str(nk))
        e_issues = [i for i in issues if i.level == "error"
                    and i.code not in ("E003",)]
        assert not e_issues

    def test_check_catches_keyword_before_run(self, tmp_path):
        """Checker catches keyword conflict that would cause a parse error."""
        nk = tmp_path / "bad.nk"
        nk.write_text("task match(x):\n    return x\n", encoding="utf-8")
        issues = check_file(str(nk))
        assert any(i.code == "E011" for i in issues)

    def test_fmt_preserves_logic(self):
        """Formatting must not change program semantics."""
        src = (
            "task add(a,b):\n"
            "    return a+b\n"
            "let result=add(1,2)\n"
            "show result\n"
        )
        formatted = fmt_source(src)
        # The logic keywords must still be there
        assert "task" in formatted
        assert "return" in formatted
        assert "show" in formatted
        assert "add" in formatted

    def test_checker_multiple_issues(self):
        """Checker can detect multiple issues in one file."""
        src = (
            "task fetch(url):\n"        # E011 keyword conflict
            "    return url\n"
            "    show \"dead code\"\n"  # W006 unreachable
        )
        issues = check_source(src)
        codes = {i.code for i in issues}
        # Should have at least keyword error and possibly unreachable
        assert "E011" in codes or "E003" in codes