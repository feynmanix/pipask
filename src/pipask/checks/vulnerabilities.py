from pipask.checks.types import CheckResult, CheckResultType
from pipask.checks.base_checker import Checker
from pipask.infra.pip_report import InstallationReportItem
from pipask.infra.pypi import ReleaseResponse
from typing import Awaitable
import asyncio
from collections import defaultdict
from pipask.infra.vulnerability_details import VulnerabilitySeverity, VulnerabilityDetails, VulnerabilityDetailsService

MAX_DISPLAYED_VULNERABILITIES = 5


class ReleaseVulnerabilityChecker(Checker):
    priority = 40

    def __init__(self, vulnerability_details_service: VulnerabilityDetailsService):
        self._vulnerability_details_service = vulnerability_details_service

    @property
    def description(self) -> str:
        return "Checking known vulnerabilities"

    async def check(
        self, package: InstallationReportItem, release_info_future: Awaitable[ReleaseResponse | None]
    ) -> CheckResult:
        pkg = package.pinned_requirement
        resolved_release_info = await release_info_future
        if resolved_release_info is None:
            return CheckResult(
                pkg,
                result_type=CheckResultType.FAILURE,
                message="No release information available",
                priority=self.priority,
            )

        relevant_vulnerabilities = [v for v in resolved_release_info.vulnerabilities if not v.withdrawn]
        if len(relevant_vulnerabilities) == 0:
            return CheckResult(
                pkg,
                result_type=CheckResultType.SUCCESS,
                message="No known vulnerabilities found",
                priority=self.priority,
            )

        vulnerability_details = await asyncio.gather(
            *(self._vulnerability_details_service.get_details(v) for v in relevant_vulnerabilities)
        )
        worst_severity = VulnerabilitySeverity.get_worst(*(v.severity for v in vulnerability_details))
        formatted_vulnerabilities = _format_vulnerabilities(vulnerability_details)
        return CheckResult(
            pkg,
            result_type=worst_severity.result_type if worst_severity is not None else CheckResultType.WARNING,
            message=f"Found the following vulnerabilities: {formatted_vulnerabilities}",
            priority=self.priority,
        )


def _format_vulnerabilities(vulnerabilities: list[VulnerabilityDetails]) -> str:
    severity_order = list(VulnerabilitySeverity)
    sorted_vulnerabilities = sorted(
        vulnerabilities,
        key=lambda v: (severity_order.index(v.severity) if v.severity is not None else len(severity_order)),
    )
    sorted_vulnerabilities = sorted_vulnerabilities[:MAX_DISPLAYED_VULNERABILITIES]

    by_severity = defaultdict(list)
    for vuln in sorted_vulnerabilities:
        by_severity[vuln.severity].append(vuln)
    formatted = []
    for severity in [*VulnerabilitySeverity, None]:
        if severity not in by_severity:
            continue
        formatted_ids = [
            f"[link={vuln.link}]{vuln.id}[/link]" if vuln.link else vuln.id  #
            for vuln in by_severity[severity]
            if vuln.id is not None
        ]
        color = severity.result_type.rich_color if severity is not None else "default"
        formatted_severity = severity.value if severity is not None else "unknown severity"
        formatted.append(f"[{color}]{', '.join(formatted_ids)} ({formatted_severity})[/{color}]")
    result = ", ".join(formatted)
    if len(vulnerabilities) > MAX_DISPLAYED_VULNERABILITIES:
        result += f" and {len(vulnerabilities) - MAX_DISPLAYED_VULNERABILITIES} more"
    return result
