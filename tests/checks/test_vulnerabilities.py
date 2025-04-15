from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipask.checks.types import CheckResult, CheckResultType
from pipask.checks.vulnerabilities import ReleaseVulnerabilityChecker, _format_vulnerabilities
from pipask.infra.pypi import ProjectInfo, ReleaseResponse, VerifiedPypiReleaseInfo, VulnerabilityPypi
from pipask.infra.vulnerability_details import (
    VulnerabilityDetails,
    VulnerabilityDetailsService,
    VulnerabilitySeverity,
)


@pytest.fixture
def vulnerability_details_service():
    service = MagicMock(spec=VulnerabilityDetailsService)
    service.get_details = AsyncMock()
    return service


@pytest.fixture
def checker(vulnerability_details_service):
    return ReleaseVulnerabilityChecker(vulnerability_details_service)


sample_project_info = ProjectInfo(name="requests", version="2.31.0")


@pytest.mark.asyncio
async def test_no_vulnerabilities(checker):
    release_info = VerifiedPypiReleaseInfo(ReleaseResponse(info=sample_project_info, vulnerabilities=[]))
    result = await checker.check(release_info)

    assert result == CheckResult(
        result_type=CheckResultType.SUCCESS,
        message="No known vulnerabilities found",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "severity,result_type,message",
    [
        (
            VulnerabilitySeverity.CRITICAL,
            CheckResultType.FAILURE,
            "[red][link=https://example.com/cve-2023-1234]CVE-2023-1234[/link] (CRITICAL)[/red]",
        ),
        (
            VulnerabilitySeverity.HIGH,
            CheckResultType.FAILURE,
            "[red][link=https://example.com/cve-2023-1234]CVE-2023-1234[/link] (HIGH)[/red]",
        ),
        (
            VulnerabilitySeverity.MEDIUM,
            CheckResultType.WARNING,
            "[yellow][link=https://example.com/cve-2023-1234]CVE-2023-1234[/link] (Medium)[/yellow]",
        ),
        (
            VulnerabilitySeverity.LOW,
            CheckResultType.NEUTRAL,
            "[default][link=https://example.com/cve-2023-1234]CVE-2023-1234[/link] (Low)[/default]",
        ),
        (
            None,
            CheckResultType.WARNING,
            "[default][link=https://example.com/cve-2023-1234]CVE-2023-1234[/link] (unknown severity)[/default]",
        ),
    ],
)
async def test_single_vulnerability(checker, vulnerability_details_service, severity, result_type, message):
    vuln = VulnerabilityPypi(
        id="CVE-2023-1234",
        withdrawn=None,
        aliases=[],
        fixed_in=["2.32.0"],
    )
    release_info = VerifiedPypiReleaseInfo(ReleaseResponse(info=sample_project_info, vulnerabilities=[vuln]))
    vulnerability_details_service.get_details.return_value = VulnerabilityDetails(
        id="CVE-2023-1234", severity=severity, link="https://example.com/cve-2023-1234"
    )

    result = await checker.check(release_info)

    assert result == CheckResult(
        result_type=result_type,
        message=f"Found the following vulnerabilities: {message}",
    )


@pytest.mark.asyncio
async def test_withdrawn_vulnerability(checker):
    vuln = VulnerabilityPypi(
        id="CVE-2023-1234",
        withdrawn=datetime.now(),
        aliases=[],
        fixed_in=["2.32.0"],
    )
    release_info = VerifiedPypiReleaseInfo(ReleaseResponse(info=sample_project_info, vulnerabilities=[vuln]))

    result = await checker.check(release_info)

    assert result.result_type == CheckResultType.SUCCESS
    assert "No known vulnerabilities found" in result.message


@pytest.mark.asyncio
async def test_multiple_vulnerabilities(checker, vulnerability_details_service):
    vulns = [
        VulnerabilityPypi(id="CVE-1C", withdrawn=None, aliases=[], fixed_in=["2.32.0"]),
        VulnerabilityPypi(id="CVE-2M", withdrawn=None, aliases=[], fixed_in=["2.32.0"]),
        VulnerabilityPypi(id="CVE-3L", withdrawn=None, aliases=[], fixed_in=["2.32.0"]),
    ]
    release_info = VerifiedPypiReleaseInfo(ReleaseResponse(info=sample_project_info, vulnerabilities=vulns))
    details_map = {
        "CVE-1C": VulnerabilityDetails(id="CVE-1C", severity=VulnerabilitySeverity.CRITICAL),
        "CVE-2M": VulnerabilityDetails(id="CVE-2M", severity=VulnerabilitySeverity.MEDIUM),
        "CVE-3L": VulnerabilityDetails(id="CVE-3L", severity=VulnerabilitySeverity.LOW),
    }

    vulnerability_details_service.get_details.side_effect = lambda vuln: details_map[vuln.id]

    result = await checker.check(release_info)

    assert result == CheckResult(
        result_type=CheckResultType.FAILURE,
        message="Found the following vulnerabilities: [red]CVE-1C (CRITICAL)[/red], [yellow]CVE-2M (Medium)[/yellow], [default]CVE-3L (Low)[/default]",
    )


def test_format_vulnerabilities():
    vulnerabilities = [
        VulnerabilityDetails(id="CVE-2", link="https://example.com/cve-2", severity=VulnerabilitySeverity.HIGH),
        VulnerabilityDetails(id="CVE-1", link="https://example.com/cve-1", severity=VulnerabilitySeverity.CRITICAL),
        VulnerabilityDetails(id="CVE-3", link="https://example.com/cve-3", severity=VulnerabilitySeverity.HIGH),
        VulnerabilityDetails(id="CVE-4", link=None, severity=VulnerabilitySeverity.HIGH),
        VulnerabilityDetails(id="CVE-5", link=None, severity=None),
    ]
    assert (
        _format_vulnerabilities(vulnerabilities)
        == "[red][link=https://example.com/cve-1]CVE-1[/link] (CRITICAL)[/red], [red][link=https://example.com/cve-2]CVE-2[/link], [link=https://example.com/cve-3]CVE-3[/link], CVE-4 (HIGH)[/red], [default]CVE-5 (unknown severity)[/default]"
    )


def test_format_long_list_of_vulnerabilities():
    vulnerabilities = [
        VulnerabilityDetails(id="CVE-1", link=None, severity=VulnerabilitySeverity.CRITICAL),
        VulnerabilityDetails(id="CVE-2", link=None, severity=VulnerabilitySeverity.CRITICAL),
        VulnerabilityDetails(id="CVE-3", link=None, severity=VulnerabilitySeverity.HIGH),
        VulnerabilityDetails(id="CVE-4", link=None, severity=VulnerabilitySeverity.LOW),
        VulnerabilityDetails(id="CVE-5", link=None, severity=VulnerabilitySeverity.LOW),
        VulnerabilityDetails(id="CVE-6", link=None, severity=VulnerabilitySeverity.LOW),
        VulnerabilityDetails(id="CVE-7", link=None, severity=VulnerabilitySeverity.LOW),
    ]
    assert (
        _format_vulnerabilities(vulnerabilities)
        == "[red]CVE-1, CVE-2 (CRITICAL)[/red], [red]CVE-3 (HIGH)[/red], [default]CVE-4, CVE-5 (Low)[/default] and 2 more"
    )
