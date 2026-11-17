#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BadWords Automated Test Runner.
Discovers and executes all unit, heuristic, and visual regression tests in tests/.

Usage:
    python3 run_tests.py
"""

import os
import sys
import unittest
import time

# Ensure repo root and src/ are in sys.path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(REPO_ROOT, "src")
TESTS_DIR = os.path.join(REPO_ROOT, "tests")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(1, REPO_ROOT)

# Set headless Qt environment
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("_BW_AUTO_HEAL_ATTEMPTED", "1")
os.environ.setdefault("BADWORDS_DEV", "1")


def main():
    print("=" * 60)
    print(" BadWords Automated Test Suite Runner")
    print("=" * 60)
    print(f"Python: {sys.version.split()[0]} ({sys.platform})")
    print(f"Root:   {REPO_ROOT}")
    print(f"Tests:  {TESTS_DIR}")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=TESTS_DIR, pattern="test_*.py")

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print(f" Tests run: {result.testsRun} in {elapsed:.2f}s")
    if result.wasSuccessful():
        print(" ALL TESTS PASSED! [OK]")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f" FAILURES: {len(result.failures)}, ERRORS: {len(result.errors)}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

