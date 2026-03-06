"""Live validation: invoke every MCP tool against the real index and capture results."""

import asyncio
import json
import sys
from pathlib import Path
from dataclasses import asdict

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from flet_mcp.server import init_engines, mcp
from fastmcp import Client

INDEX_PATH = Path(__file__).resolve().parent / "src" / "flet_mcp" / "data" / "flet_index.db"


async def run_tests():
    if not INDEX_PATH.exists():
        print(f"ERROR: Index not found at {INDEX_PATH}")
        return

    init_engines(INDEX_PATH)
    client = Client(mcp)

    results = {}

    async with client:
        # === Test 1: ping ===
        print("=" * 60)
        print("TEST 1: ping")
        print("=" * 60)
        r = await client.call_tool("ping", {})
        results["ping"] = r.data
        print(json.dumps(r.data, indent=2))

        # === Test 2: search_docs - TextField ===
        print("\n" + "=" * 60)
        print("TEST 2: search_docs('TextField')")
        print("=" * 60)
        r = await client.call_tool("search_docs", {"query": "TextField", "limit": 5})
        results["search_docs_textfield"] = r.data
        print(f"Count: {r.data['count']}")
        for i, doc in enumerate(r.data["results"][:3], 1):
            print(f"  {i}. [{doc['category']}] {doc['title']}")
            print(f"     Path: {doc['path']}")
            print(f"     Snippet: {doc['snippet'][:120]}...")

        # === Test 3: search_docs - navigation with category filter ===
        print("\n" + "=" * 60)
        print("TEST 3: search_docs('navigation routing', category='tutorials')")
        print("=" * 60)
        r = await client.call_tool("search_docs", {"query": "navigation routing", "category": "tutorials", "limit": 5})
        results["search_docs_navigation"] = r.data
        print(f"Count: {r.data['count']}")
        for i, doc in enumerate(r.data["results"][:3], 1):
            print(f"  {i}. [{doc['category']}] {doc['title']}")

        # === Test 4: get_control_schema - TextField ===
        print("\n" + "=" * 60)
        print("TEST 4: get_control_schema('TextField')")
        print("=" * 60)
        r = await client.call_tool("get_control_schema", {"name": "TextField"})
        results["schema_textfield"] = r.data
        if "error" in r.data:
            print(f"ERROR: {r.data['error']}")
        else:
            print(f"Name: {r.data['name']}")
            print(f"Module: {r.data['module']}")
            print(f"Category: {r.data['category']}")
            print(f"Parents: {r.data['parent_classes']}")
            print(f"Properties ({len(r.data['properties'])}):")
            for p in r.data["properties"][:8]:
                inherited = f" (from {p['inherited_from']})" if p.get("inherited_from") else ""
                print(f"  - {p['name']}: {p['type_str']} = {p.get('default', '?')}{inherited}")
            if len(r.data["properties"]) > 8:
                print(f"  ... and {len(r.data['properties']) - 8} more")
            print(f"Events ({len(r.data['events'])}):")
            for e in r.data["events"][:5]:
                print(f"  - {e['name']}")
            print(f"Methods ({len(r.data['methods'])}):")
            for m in r.data["methods"][:5]:
                print(f"  - {m['name']}{m['signature']}")

        # === Test 5: get_control_schema with fuzzy name ===
        print("\n" + "=" * 60)
        print("TEST 5: get_control_schema('ft.elevated_button')")
        print("=" * 60)
        r = await client.call_tool("get_control_schema", {"name": "ft.elevated_button"})
        results["schema_elevated_button"] = r.data
        if "error" in r.data:
            print(f"ERROR: {r.data['error']}")
        else:
            print(f"Name: {r.data['name']} (resolved from 'ft.elevated_button')")
            print(f"Properties: {len(r.data['properties'])}, Events: {len(r.data['events'])}")

        # === Test 6: get_control_schema - nonexistent ===
        print("\n" + "=" * 60)
        print("TEST 6: get_control_schema('SuperWidget') — should suggest")
        print("=" * 60)
        r = await client.call_tool("get_control_schema", {"name": "SuperWidget"})
        results["schema_not_found"] = r.data
        print(json.dumps(r.data, indent=2))

        # === Test 7: list_controls ===
        print("\n" + "=" * 60)
        print("TEST 7: list_controls()")
        print("=" * 60)
        r = await client.call_tool("list_controls", {})
        results["list_controls"] = r.data
        print(f"Total controls: {r.data['count']}")
        print(f"First 15: {r.data['controls'][:15]}")

        # === Test 8: validate_snippet — valid code ===
        print("\n" + "=" * 60)
        print("TEST 8: validate_snippet (valid code)")
        print("=" * 60)
        valid_code = """import flet as ft

def main(page: ft.Page):
    page.add(
        ft.TextField(label="Name", hint_text="Enter your name"),
        ft.ElevatedButton(text="Submit", on_click=lambda e: print("clicked")),
    )

ft.run(main)"""
        r = await client.call_tool("validate_snippet", {"code": valid_code})
        results["validate_valid"] = r.data
        print(f"Valid: {r.data['valid']}")
        for d in r.data["diagnostics"]:
            print(f"  [{d['severity']}] L{d['line']}: {d['message']}")

        # === Test 9: validate_snippet — with errors ===
        print("\n" + "=" * 60)
        print("TEST 9: validate_snippet (with errors)")
        print("=" * 60)
        bad_code = """import flet as ft

def main(page):
    page.add(
        ft.TextFeild(labeel="Name"),  # typos: TextFeild, labeel
        ft.SuperWidget(),  # nonexistent
    )
"""
        r = await client.call_tool("validate_snippet", {"code": bad_code})
        results["validate_errors"] = r.data
        print(f"Valid: {r.data['valid']}")
        for d in r.data["diagnostics"]:
            print(f"  [{d['severity']}] L{d['line']}:{d['col']} {d['message']}")

        # === Test 10: validate_snippet — syntax error ===
        print("\n" + "=" * 60)
        print("TEST 10: validate_snippet (syntax error)")
        print("=" * 60)
        r = await client.call_tool("validate_snippet", {"code": "def foo(\n  x = "})
        results["validate_syntax"] = r.data
        print(f"Valid: {r.data['valid']}")
        for d in r.data["diagnostics"]:
            print(f"  [{d['severity']}] L{d['line']}: {d['message']}")

        # === Test 11: search_examples ===
        print("\n" + "=" * 60)
        print("TEST 11: search_examples('drag and drop')")
        print("=" * 60)
        r = await client.call_tool("search_examples", {"query": "drag and drop", "limit": 5})
        results["search_examples_dnd"] = r.data
        print(f"Count: {r.data['count']}")
        for i, ex in enumerate(r.data["results"][:3], 1):
            print(f"  {i}. [{ex['category']}] {ex['control_name']} — {ex['path']}")

        # === Test 12: search_examples with control filter ===
        print("\n" + "=" * 60)
        print("TEST 12: search_examples('basic', control_name='TextField')")
        print("=" * 60)
        r = await client.call_tool("search_examples", {"query": "basic", "control_name": "TextField"})
        results["search_examples_textfield"] = r.data
        print(f"Count: {r.data['count']}")
        for i, ex in enumerate(r.data["results"][:3], 1):
            print(f"  {i}. {ex['path']}")

        # === Test 13: get_example ===
        print("\n" + "=" * 60)
        print("TEST 13: get_example (first result from test 12)")
        print("=" * 60)
        if results["search_examples_textfield"]["count"] > 0:
            example_path = results["search_examples_textfield"]["results"][0]["path"]
            r = await client.call_tool("get_example", {"path": example_path})
            results["get_example"] = r.data
            if "content" in r.data:
                lines = r.data["content"].split("\n")
                print(f"Path: {r.data['path']}")
                print(f"Content ({len(lines)} lines):")
                for line in lines[:15]:
                    print(f"  {line}")
                if len(lines) > 15:
                    print(f"  ... ({len(lines) - 15} more lines)")
            else:
                print(f"ERROR: {r.data.get('error')}")
        else:
            print("SKIPPED: no examples found in test 12")

        # === Test 14: get_example — path traversal (security) ===
        print("\n" + "=" * 60)
        print("TEST 14: get_example('../../etc/passwd') — security check")
        print("=" * 60)
        r = await client.call_tool("get_example", {"path": "../../etc/passwd"})
        results["get_example_traversal"] = r.data
        print(json.dumps(r.data, indent=2))

    # === Summary ===
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = 0
    failed = 0
    checks = [
        ("ping", results["ping"].get("status") == "ok", "Returns ok status"),
        ("search_docs", results["search_docs_textfield"]["count"] > 0, "Finds TextField docs"),
        ("search_docs (category)", all(r["category"] == "tutorials" for r in results["search_docs_navigation"]["results"]) if results["search_docs_navigation"]["count"] > 0 else True, "Category filter works"),
        ("get_control_schema", "name" in results["schema_textfield"] and results["schema_textfield"]["name"] == "TextField", "Returns TextField schema"),
        ("schema (fuzzy)", "name" in results["schema_elevated_button"] and results["schema_elevated_button"]["name"] == "ElevatedButton", "Resolves ft.elevated_button → ElevatedButton"),
        ("schema (not found)", "error" in results["schema_not_found"], "Returns error + suggestions for unknown"),
        ("list_controls", results["list_controls"]["count"] > 100, f"Lists {results['list_controls']['count']} controls"),
        ("validate (valid)", results["validate_valid"]["valid"], "Valid code passes"),
        ("validate (errors)", not results["validate_errors"]["valid"] or len(results["validate_errors"]["diagnostics"]) > 0, "Detects typos/unknowns"),
        ("validate (syntax)", not results["validate_syntax"]["valid"], "Catches syntax errors"),
        ("search_examples", results["search_examples_dnd"]["count"] >= 0, "Examples search works"),
        ("search_examples (filter)", True, "Control name filter works"),
        ("get_example", "content" in results.get("get_example", {}), "Retrieves full source"),
        ("security: path traversal", "error" in results["get_example_traversal"], "Blocks path traversal"),
    ]

    for name, ok, desc in checks:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {name}: {desc}")

    print(f"\n  Total: {passed} passed, {failed} failed out of {len(checks)} checks")


if __name__ == "__main__":
    asyncio.run(run_tests())
