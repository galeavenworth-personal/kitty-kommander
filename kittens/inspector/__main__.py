"""Standalone CLI entry point for the Inspector Kitten.

Usage::

    python -m kittens.inspector --socket unix:/tmp/kitty-kommander-myapp ls
    python -m kittens.inspector desktop
    python -m kittens.inspector sockets

Reuses the same arg parser and dispatch logic as the kitten entry point
in ``__init__.py``.  The only difference is the argument source:
``sys.argv[1:]`` here vs. kitty's ``args[1:]`` in kitten mode.
"""

import sys

from . import _dispatch, _parse_args


def main() -> None:
    opts = _parse_args(sys.argv[1:])
    _dispatch(opts)


if __name__ == "__main__":
    main()
