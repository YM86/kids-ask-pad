#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Continuous Integration & local verification script for kids-ask-pad."""
import os
import py_compile
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_server_syntax():
    server_path = os.path.join(BASE_DIR, "server.py")
    assert os.path.isfile(server_path), "server.py not found"
    py_compile.compile(server_path, doraise=True)
    print("[PASS] server.py syntax compile check")


def test_questions_pool():
    js_path = os.path.join(BASE_DIR, "questions.js")
    assert os.path.isfile(js_path), "questions.js not found"
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    q_m = re.search(r"const QUESTIONS = \[\n([\s\S]*?)\n\s*\];", content)
    teen_m = re.search(r"const TEEN_QUESTIONS = \[\n([\s\S]*?)\n\s*\];", content)
    assert q_m, "QUESTIONS array not found in questions.js"
    assert teen_m, "TEEN_QUESTIONS array not found in questions.js"

    q_list = [s.strip().strip('"').rstrip('",') for s in re.findall(r'^\s*"[^"]+",', q_m.group(1), re.M)]
    teen_list = [s.strip().strip('"').rstrip('",') for s in re.findall(r'^\s*"[^"]+",', teen_m.group(1), re.M)]

    assert len(q_list) == 450, f"Expected 450 kid questions, got {len(q_list)}"
    assert len(teen_list) == 450, f"Expected 450 teen questions, got {len(teen_list)}"
    assert len(set(q_list)) == 450, f"Kid pool has duplicates: {450 - len(set(q_list))}"
    assert len(set(teen_list)) == 450, f"Teen pool has duplicates: {450 - len(set(teen_list))}"

    cross = set(q_list).intersection(set(teen_list))
    assert len(cross) == 0, f"Found overlapping questions across pools: {cross}"

    kanji_in_kid = [q for q in q_list if re.search(r"[\u4e00-\u9fff]", q)]
    assert len(kanji_in_kid) == 0, f"Found kanji in kid questions: {kanji_in_kid}"

    print(f"[PASS] questions.js integrity check (450 kid questions, 450 teen questions, 0 duplicates, 0 kanji in kid pool)")


def test_index_html():
    html_path = os.path.join(BASE_DIR, "index.html")
    assert os.path.isfile(html_path), "index.html not found"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # External questions script
    assert '<script src="questions.js"></script>' in html, "Missing script tag for questions.js"

    # Security tags
    assert "Content-Security-Policy" in html, "Missing CSP meta tag"
    assert "https://generativelanguage.googleapis.com" in html, "Missing Google AI Studio in CSP connect-src"
    assert "https://openrouter.ai" in html, "Missing OpenRouter in CSP connect-src"
    assert "https://ja.wikipedia.org" in html, "Missing Wikipedia in CSP connect-src"
    assert "X-Content-Type-Options" in html, "Missing nosniff header"
    assert "strict-origin-when-cross-origin" in html, "Missing Referrer-Policy"
    assert "window.top !== window.self" in html, "Missing clickjacking frame-busting"

    # UI elements
    required_ids = [
        "ask-form", "question", "send", "mic-btn", "cats", "chips",
        "thinking", "answer", "error", "usage", "admin-toggle", "admin-panel",
        "cfg-api-key", "related-block", "related-chips"
    ]
    for el_id in required_ids:
        assert f'id="{el_id}"' in html, f"Missing essential element with id='{el_id}'"

    print("[PASS] index.html security and DOM integrity check")


def test_server_routes():
    server_path = os.path.join(BASE_DIR, "server.py")
    with open(server_path, "r", encoding="utf-8") as f:
        src = f.read()

    assert "/questions.js" in src, "server.py does not handle questions.js route"
    print("[PASS] server.py routing check")


def test_sentence_termination():
    """Verify sentence termination and incomplete sentence clipping."""
    sys.path.insert(0, BASE_DIR)
    import server

    # Test 1: Complete sentences + incomplete trailing fragment -> incomplete fragment must be dropped
    sample = "そらは 青(あお)いよ。たいようの 光(ひかり)が ちきゅうに 当(あ)たるからだよ。そして"
    result = server.sentences(sample, limit=4, max_chars=420)
    assert not result.endswith("そして"), f"Trailing incomplete sentence was not dropped: {result}"
    assert result.endswith("。") or result.endswith("！") or result.endswith("？"), f"Result does not end with terminal punctuation: {result}"

    # Test 2: Verify index.html contains proper terminal punctuation checking
    html_path = os.path.join(BASE_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "/[。．!?！?]$/.test(trimmed)" in html, "index.html missing sentence terminal punctuation test"

    print("[PASS] sentence termination & incomplete fragment dropping check")


def main():
    print("Running kids-ask-pad verification tests...")
    tests = [test_server_syntax, test_questions_pool, test_index_html, test_server_routes, test_sentence_termination]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}", file=sys.stderr)
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {e}", file=sys.stderr)
            failed += 1

    if failed == 0:
        print("\nAll verification tests passed successfully!")
        return 0
    else:
        print(f"\nVerification failed: {failed} error(s).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
