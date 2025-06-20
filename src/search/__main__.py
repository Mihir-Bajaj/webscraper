"""
src.search.__main__
===================

Command-line entry point for semantic search.

Example
-------
    python -m src.search "custom healthcare software"
"""

import sys
from .semantic import SemanticSearch

def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m src.search "your query"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])     # support multi-word queries
    
    with SemanticSearch() as search:
        results = search.search(query)
        print(search.format_results(results))

if __name__ == "__main__":  # pragma: no cover
    main()