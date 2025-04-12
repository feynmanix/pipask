from typing import Optional

from pipask._vendor.pip._internal.distributions.base import AbstractDistribution
from pipask._vendor.pip._internal.distributions.sdist import SourceDistribution
from pipask._vendor.pip._internal.distributions.wheel import WheelDistribution
from pipask._vendor.pip._internal.index.package_finder import PackageFinder
from pipask._vendor.pip._internal.metadata import BaseDistribution
from pipask._vendor.pip._internal.network.session import PipSession
from pipask._vendor.pip._internal.req.req_install import InstallRequirement
from pipask.infra.metadata import (
    fetch_metadata_from_pypi_is_available,
)


def make_distribution_for_install_requirement(
    install_req: InstallRequirement,
    session: PipSession,
) -> AbstractDistribution:
    """Returns a Distribution for the given InstallRequirement"""
    # Editable requirements will always be source distributions. They use the
    # legacy logic until we create a modern standard for them.
    if install_req.editable:
        return SourceDistribution(install_req)

    # If it's a wheel, it's a WheelDistribution
    if install_req.is_wheel:
        return WheelDistribution(install_req)

    # Otherwise, a SourceDistribution.
    # MODIFIED for pipask: We can do with metadata obtained from PyPI if available
    # instead of building the source distribution.
    if distribution := VirtualMetadataOnlyDistribution.create_if_metadata_available(install_req, session):
        return distribution
    return SourceDistribution(install_req)


# MODIFIED for pipask: A new class that wraps around just the metadata
class VirtualMetadataOnlyDistribution(AbstractDistribution):
    """Not a real distribution, but a wrapper around a metadata fetched from a remote index."""

    def __init__(self, req: InstallRequirement, metadata_distribution: BaseDistribution) -> None:
        super().__init__(req)
        self._metadata_distribution = metadata_distribution

    @classmethod
    def create_if_metadata_available(cls, req: InstallRequirement, session: PipSession) -> Optional["VirtualMetadataOnlyDistribution"]:
        """Create a distribution if metadata is available"""
        metadata_distribution = fetch_metadata_from_pypi_is_available(req, session)
        if metadata_distribution is None:
            return None
        return cls(req, metadata_distribution)

    @property
    def build_tracker_id(self) -> str | None:
        return None

    def get_metadata_distribution(self) -> BaseDistribution:
        """Returns metadata from the memory"""
        return self._metadata_distribution

    def prepare_distribution_metadata(
        self,
        finder: PackageFinder,
        build_isolation: bool,
        check_build_deps: bool,
    ) -> None:
        pass
