"""
nekova.lsp — a real Language Server Protocol implementation for NEKOVA.

Phase 26 (Developer Experience). Replaces the VS Code extension's
previous syntax-highlighting-only support with actual diagnostics,
hover docs, and autocomplete, talking to editors over the standard
LSP JSON-RPC-over-stdio transport.

Entry point: `nekova lsp` (see main.py), which runs server.main().
"""