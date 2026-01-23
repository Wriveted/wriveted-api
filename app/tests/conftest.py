"""
Root conftest for test configuration.

This file is loaded by pytest before other conftest.py files
and provides global test configuration options.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command line options for test configuration."""
    parser.addoption(
        "--run-isolated-tests",
        action="store_true",
        default=False,
        help="Run tests that require isolation (e.g., connection pool stress tests)",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "isolated: mark test as requiring isolation from other tests",
    )


def pytest_collection_modifyitems(config, items):
    """Skip isolated tests unless --run-isolated-tests is passed."""
    if config.getoption("--run-isolated-tests"):
        # When running isolated tests, skip non-isolated tests
        skip_regular = pytest.mark.skip(
            reason="Skipping non-isolated test when running with --run-isolated-tests"
        )
        for item in items:
            if "isolated" not in item.keywords:
                item.add_marker(skip_regular)
    else:
        # When running regular tests, skip isolated tests
        skip_isolated = pytest.mark.skip(
            reason="Isolated test - run with --run-isolated-tests"
        )
        for item in items:
            if "isolated" in item.keywords:
                item.add_marker(skip_isolated)
