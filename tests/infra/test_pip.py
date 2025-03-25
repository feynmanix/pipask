from pipask.cli_helpers import ParsedArgs
from pipask.infra.pip import get_pip_report


import pytest


@pytest.mark.integration
async def test_pip_resolves_package_to_install():
    args = ["install", "pyfluent-iterables>1.1.0,<1.3.0"]
    report = get_pip_report(ParsedArgs(other_args=args, help=False, dry_run=False, report=None, raw_args=args))
    assert report is not None
    assert len(report.install) == 1
    assert report.install[0].pinned_requirement == "pyfluent-iterables==1.2.0"
