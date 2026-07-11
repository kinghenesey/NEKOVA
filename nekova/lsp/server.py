# =============================================================
# NEKOVA LSP — Server
# =============================================================
# A minimal Language Server Protocol server over stdio, hand-rolled
# rather than built on a framework like pygls — consistent with the
# rest of NEKOVA's toolchain (lexer, parser, interpreter are all
# hand-written too) and avoids adding a new mandatory dependency for
# what's fundamentally an optional editor-integration feature.
#
# Implements just enough of the spec for v1: initialize/initialized/
# shutdown/exit, textDocument/didOpen/didChange/didClose, and
# publishing diagnostics on every change. Hover and completion are
# separate, later pieces (see hover.py / completions.py once they
# exist) that plug into the same dispatch table below.
#
# Wire format (the LSP standard, same as HTTP-style headers):
#   Content-Length: <N>\r\n
#   \r\n
#   <N bytes of UTF-8 JSON-RPC content>
#
# Run via `nekova lsp` (see main.py's dispatch), which just calls
# main() here. Editors spawn this as a subprocess and talk to it over
# its stdin/stdout — nothing here should ever print to stdout except
# through send_message, or it'll corrupt the protocol stream.

import sys
import json

from nekova.lsp.diagnostics import compute_diagnostics
from nekova.lsp.hover import compute_hover
from nekova.lsp.completions import compute_completions

# uri -> current in-memory text of that open document. This is the
# server's whole picture of "what's open" — LSP documents are synced
# incrementally by the client sending the *full* text on every change
# (we request TextDocumentSyncKind.Full below, the simplest option;
# incremental sync would save bandwidth but isn't worth the added
# complexity for source files this size).
_open_documents = {}


def read_message(stream):
    """
    Read one Content-Length-framed JSON-RPC message from a binary
    stream. Returns the parsed dict, or None at EOF (stdin closed —
    the client disconnected, time for the server to exit).
    """
    headers = {}
    while True:
        line = stream.readline()
        if not line:
            return None  # EOF
        line = line.decode("utf-8").rstrip("\r\n")
        if line == "":
            break  # blank line ends the header block
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()

    length = int(headers.get("content-length", 0))
    if length == 0:
        return {}
    body = stream.read(length)
    return json.loads(body.decode("utf-8"))


def write_message(stream, message: dict):
    """Write one Content-Length-framed JSON-RPC message."""
    body = json.dumps(message).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    stream.write(header)
    stream.write(body)
    stream.flush()


def _respond(stream, request_id, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    write_message(stream, msg)


def _notify(stream, method: str, params: dict):
    write_message(stream, {
        "jsonrpc": "2.0", "method": method, "params": params,
    })


def _publish_diagnostics(stream, uri: str, text: str):
    diagnostics = compute_diagnostics(text)
    _notify(stream, "textDocument/publishDiagnostics", {
        "uri": uri,
        "diagnostics": diagnostics,
    })


# ── Request/notification handlers ────────────────────────────

def _handle_initialize(stream, request_id, params):
    _respond(stream, request_id, {
        "capabilities": {
            # Full-document sync: the client sends the whole file's
            # text on every change, not incremental edits. Simpler,
            # and NEKOVA source files are small enough it doesn't
            # matter for latency.
            "textDocumentSync": 1,
            "hoverProvider": True,
            "completionProvider": {"triggerCharacters": ["."]},
        },
        "serverInfo": {"name": "nekova-lsp", "version": "1"},
    })


def _handle_did_open(stream, params):
    doc = params["textDocument"]
    uri, text = doc["uri"], doc["text"]
    _open_documents[uri] = text
    _publish_diagnostics(stream, uri, text)


def _handle_did_change(stream, params):
    uri = params["textDocument"]["uri"]
    # Full sync: the last entry in contentChanges is the complete new
    # text (no range means "the whole document").
    changes = params.get("contentChanges", [])
    if not changes:
        return
    text = changes[-1]["text"]
    _open_documents[uri] = text
    _publish_diagnostics(stream, uri, text)


def _handle_did_close(stream, params):
    uri = params["textDocument"]["uri"]
    _open_documents.pop(uri, None)
    # Clear any diagnostics for a file that's no longer open, so
    # stale red squiggles don't linger in the editor's Problems view.
    _notify(stream, "textDocument/publishDiagnostics", {
        "uri": uri, "diagnostics": [],
    })


def _handle_hover(stream, request_id, params):
    try:
        uri = params["textDocument"]["uri"]
        position = params["position"]
        text = _open_documents.get(uri)
        if text is None:
            _respond(stream, request_id, None)
            return
        result = compute_hover(text, position["line"], position["character"])
    except (KeyError, TypeError):
        # Malformed request — respond with "no hover info" rather
        # than crashing the whole server over one bad request.
        result = None
    _respond(stream, request_id, result)


def _handle_completion(stream, request_id, params):
    try:
        uri = params["textDocument"]["uri"]
        position = params["position"]
        text = _open_documents.get(uri)
        if text is None:
            _respond(stream, request_id, [])
            return
        result = compute_completions(text, position["line"], position["character"])
    except (KeyError, TypeError):
        result = []
    _respond(stream, request_id, result)


def dispatch(stream, message: dict) -> bool:
    """
    Handle one incoming message. Returns False when the server should
    stop (received 'exit').
    """
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params", {}) or {}

    if method == "initialize":
        _handle_initialize(stream, request_id, params)
    elif method == "initialized":
        pass  # notification, nothing to do
    elif method == "textDocument/didOpen":
        _handle_did_open(stream, params)
    elif method == "textDocument/didChange":
        _handle_did_change(stream, params)
    elif method == "textDocument/didClose":
        _handle_did_close(stream, params)
    elif method == "textDocument/hover":
        _handle_hover(stream, request_id, params)
    elif method == "textDocument/completion":
        _handle_completion(stream, request_id, params)
    elif method == "shutdown":
        _respond(stream, request_id, None)
    elif method == "exit":
        return False
    elif request_id is not None:
        # Unhandled request (e.g. hover/completion before those are
        # wired up) — respond with "not supported" rather than
        # leaving the client hanging on a request it'll never get an
        # answer to.
        _respond(stream, request_id, error={
            "code": -32601, "message": f"Method not found: {method}",
        })
    # Unhandled notifications are silently ignored, per spec.
    return True


def main():
    """Entry point for `nekova lsp`. Blocks, serving over stdio until
    the client sends 'exit' or closes the connection."""
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        message = read_message(stdin)
        if message is None:
            break  # client disconnected
        if not dispatch(stdout, message):
            break


if __name__ == "__main__":
    main()