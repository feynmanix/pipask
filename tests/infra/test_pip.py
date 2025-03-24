from pipc.cli_helpers import ParsedArgs
from pipc.infra.pip import get_pip_report


import pytest


@pytest.mark.integration
async def test_pip_resolves_package_to_install():
    report = get_pip_report(
        ParsedArgs(other_args=["install", "pyfluent-iterables>1.1.0,<2.0.0"], help=False, dry_run=False, report=None)
    )
    assert report is not None
    assert len(report.install) == 1
    assert report.install[0].pinned_requirement == "pyfluent-iterables==1.2.0"
