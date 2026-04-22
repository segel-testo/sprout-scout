"""
Integration test: run scanner against each of the 5 example URLs from
url-collection.txt and print a summary of dishes / delivery links / fallback.

Run with: venv/Scripts/python.exe -m tests.scan_examples
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.scanner import scan_restaurant


EXAMPLES = [
    ("zen", "https://www.zen-restaurant.at/", {"name": "Zen"}),
    ("akakiko", "https://akakiko.at/lieferservice", {"name": "Akakiko"}),
    ("ofenbarung", "https://pages.resmio.com/pizzeria-ofenbarung/de/preview/modern", {"name": "Pizzeria Ofenbarung"}),
    ("misterbeans", "https://www.misterbeans.at/Coffeeshop/Unser-Coffeeshop/", {"name": "Mister Beans"}),
    ("bruder", "https://www.bruderundschwester.com/speisekarte", {"name": "Bruder & Schwester"}),
]


async def main():
    for rid, url, meta in EXAMPLES:
        print(f"\n=== {rid}  {url} ===")
        try:
            # bypass cache for testing
            from services import scanner
            result = await scanner._scan_uncached(rid, url, meta)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        dishes = result.get("dishes", [])
        print(f"  no_menu: {result.get('no_menu')}  dishes: {len(dishes)}")
        if result.get("delivery_link"):
            print(f"  delivery_link: {result['delivery_link']['platform']} -> {result['delivery_link']['url']}")
        for d in dishes[:5]:
            print(f"    - [{d['confidence']}] {d['name']!r}  kws={d['matched_keywords']}")
        if len(dishes) > 5:
            print(f"    ... and {len(dishes) - 5} more")


if __name__ == "__main__":
    asyncio.run(main())
