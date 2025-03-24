import pytest


def pytest_collection_modifyitems(config, items):
    run_integration = config.getoption("--integration") or config.getoption("-m") == "integration"
    if not run_integration:
        skip_integration_marker = pytest.mark.skip(reason="Need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration_marker)


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", default=False, help="run integration tests")
