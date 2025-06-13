"""
src.search.__main__
===================

Command-line entry point for semantic search.

Example
-------
    python -m src.search "custom healthcare software"
"""

import sys
from ..semantic_query import main as query_main  # assumes semantic_query.py defines main()

def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m src.search "your query"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])     # support multi-word queries
    query_main(query)

if __name__ == "__main__":  # pragma: no cover
    main()