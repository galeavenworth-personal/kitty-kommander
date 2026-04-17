#!/usr/bin/env python3
"""Thin CLI wrapper over `cue lsp` so Claude Code (and humans) can run
hover/definition/references/symbols on CUE files without waiting for an
official cue-lsp plugin in the Claude Code marketplace.

The native LSP tool in Claude Code is plugin-gated and CUE isn't on the
list (as of cue v0.16 / April 2026). `cue lsp` itself is a standard LSP
stdio server — this script speaks enough JSON-RPC to drive one-shot
queries against it.

Cold-start per invocation: each call spawns a fresh `cue lsp`, initializes,
didOpens the target file, runs the query, shuts down cleanly. Typical
latency ~0.5–1.5s on a small schema tree. If that becomes a bottleneck,
promote this to a background daemon with a socket/FIFO; for now the
simpler shape wins.

Positions in this CLI are 1-based (matching editor and Claude Code LSP
tool conventions); they're converted to LSP's 0-based internally.

Usage:
    scripts/cue-lsp.py hover     --file schema/cli/launch.cue --line 7 --char 1
    scripts/cue-lsp.py def       --file schema/cli/launch.cue --line 7 --char 1
    scripts/cue-lsp.py refs      --file schema/cli/launch.cue --line 7 --char 1
    scripts/cue-lsp.py symbols   --file schema/cli/launch.cue
    scripts/cue-lsp.py --json hover --file schema/cli/launch.cue --line 7 --char 1
"""

from __future__ import annotations

import argparse
import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path

TIMEOUT = 10.0  # generous; cue lsp cold start on first file can be slow


def find_repo_root(start: Path) -> Path:
    """Walk up from `start` looking for cue.mod — the CUE module root.
    Falls back to cwd if not found (script still works, just with a
    narrower workspace scope)."""
    d = start.resolve()
    for _ in range(40):
        if (d / "cue.mod").is_dir():
            return d
        if d.parent == d:
            break
        d = d.parent
    return Path.cwd()


class LSP:
    """Minimal LSP JSON-RPC client over subprocess stdio."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.proc = subprocess.Popen(
            ["cue", "lsp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(root),
        )
        self._next_id = 1

    def _send(self, msg: dict) -> None:
        body = json.dumps(msg).encode()
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        assert self.proc.stdin is not None
        self.proc.stdin.write(header + body)
        self.proc.stdin.flush()

    def _recv(self, timeout: float = TIMEOUT) -> dict | None:
        """Read one framed LSP message. Returns None on timeout/EOF."""
        assert self.proc.stdout is not None
        deadline = time.time() + timeout
        header = b""
        while b"\r\n\r\n" not in header:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            r, _, _ = select.select([self.proc.stdout], [], [], remaining)
            if not r:
                return None
            chunk = self.proc.stdout.read1(1)
            if not chunk:
                return None
            header += chunk
        head, _, rest = header.partition(b"\r\n\r\n")
        length = 0
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1].strip())
        body = rest
        while len(body) < length:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            r, _, _ = select.select([self.proc.stdout], [], [], remaining)
            if not r:
                return None
            body += self.proc.stdout.read1(length - len(body))
        return json.loads(body.decode())

    def request(self, method: str, params: dict) -> dict:
        """Send a request, drain notifications until matching response."""
        rid = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            msg = self._recv()
            if msg is None:
                raise RuntimeError(f"timeout waiting for {method}")
            if msg.get("id") == rid:
                return msg
            # else it's a server-initiated notification/request; ignore.

    def notify(self, method: str, params: dict) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def initialize(self) -> None:
        root_uri = f"file://{self.root}"
        resp = self.request(
            "initialize",
            {
                "processId": os.getpid(),
                "rootUri": root_uri,
                "capabilities": {},
                "workspaceFolders": [{"uri": root_uri, "name": self.root.name}],
            },
        )
        if "error" in resp:
            raise RuntimeError(f"initialize failed: {resp['error']}")
        self.notify("initialized", {})

    def did_open(self, path: Path) -> str:
        """Open a .cue file in the server. Returns the URI used."""
        uri = f"file://{path.resolve()}"
        text = path.read_text()
        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "cue",
                    "version": 1,
                    "text": text,
                }
            },
        )
        return uri

    def shutdown(self) -> None:
        try:
            self.request("shutdown", {})
        except Exception:
            pass
        try:
            self.notify("exit", {})
        except Exception:
            pass
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def fmt_location(root: Path, loc: dict) -> str:
    """Format a Location/DocumentLink into `path:line:char` (1-based)."""
    uri = loc.get("uri") or loc.get("targetUri", "")
    path = uri.removeprefix("file://")
    try:
        rel = Path(path).resolve().relative_to(root)
        shown = str(rel)
    except ValueError:
        shown = path
    rng = loc.get("range") or loc.get("targetRange") or {}
    start = rng.get("start", {})
    line = start.get("line", 0) + 1
    char = start.get("character", 0) + 1
    return f"{shown}:{line}:{char}"


def cmd_hover(lsp: LSP, uri: str, line: int, char: int) -> dict:
    return lsp.request(
        "textDocument/hover",
        {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": char - 1},
        },
    )


def cmd_definition(lsp: LSP, uri: str, line: int, char: int) -> dict:
    return lsp.request(
        "textDocument/definition",
        {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": char - 1},
        },
    )


def cmd_references(lsp: LSP, uri: str, line: int, char: int) -> dict:
    return lsp.request(
        "textDocument/references",
        {
            "textDocument": {"uri": uri},
            "position": {"line": line - 1, "character": char - 1},
            "context": {"includeDeclaration": True},
        },
    )


def cmd_symbols(lsp: LSP, uri: str) -> dict:
    return lsp.request(
        "textDocument/documentSymbol",
        {"textDocument": {"uri": uri}},
    )


def main() -> int:
    p = argparse.ArgumentParser(
        description="Drive `cue lsp` directly for CUE code intelligence.",
    )
    p.add_argument(
        "op",
        choices=["hover", "def", "definition", "refs", "references", "symbols"],
        help="LSP operation to perform",
    )
    p.add_argument("--file", required=True, help="Path to .cue file")
    p.add_argument("--line", type=int, default=1, help="1-based line")
    p.add_argument("--char", type=int, default=1, help="1-based character")
    p.add_argument("--json", action="store_true", help="Raw JSON output")
    args = p.parse_args()

    path = Path(args.file).resolve()
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    root = find_repo_root(path.parent)
    lsp = LSP(root)
    try:
        lsp.initialize()
        uri = lsp.did_open(path)

        if args.op == "hover":
            resp = cmd_hover(lsp, uri, args.line, args.char)
        elif args.op in ("def", "definition"):
            resp = cmd_definition(lsp, uri, args.line, args.char)
        elif args.op in ("refs", "references"):
            resp = cmd_references(lsp, uri, args.line, args.char)
        elif args.op == "symbols":
            resp = cmd_symbols(lsp, uri)
        else:
            print(f"unknown op: {args.op}", file=sys.stderr)
            return 2
    finally:
        lsp.shutdown()

    if "error" in resp:
        print(f"lsp error: {resp['error']}", file=sys.stderr)
        return 1

    result = resp.get("result")
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    # Pretty output
    if result is None or result == [] or result == {}:
        print(f"(no {args.op} result at {path.name}:{args.line}:{args.char})")
        return 0

    if args.op == "hover":
        contents = result.get("contents") if isinstance(result, dict) else None
        if isinstance(contents, dict) and "value" in contents:
            print(contents["value"])
        elif isinstance(contents, list):
            for c in contents:
                if isinstance(c, dict):
                    print(c.get("value", c))
                else:
                    print(c)
        else:
            print(contents)
        return 0

    if args.op in ("def", "definition", "refs", "references"):
        items = result if isinstance(result, list) else [result]
        for loc in items:
            print(fmt_location(root, loc))
        return 0

    if args.op == "symbols":
        # Flat or hierarchical. Handle both.
        def walk(sym, depth=0):
            name = sym.get("name", "?")
            kind = sym.get("kind", "?")
            rng = sym.get("range") or sym.get("location", {}).get("range", {})
            start = rng.get("start", {})
            line = start.get("line", 0) + 1
            print(f"{'  ' * depth}{name}  [{kind}]  line {line}")
            for child in sym.get("children", []) or []:
                walk(child, depth + 1)

        for s in result:
            walk(s)
        return 0

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
