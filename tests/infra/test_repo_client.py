from contextlib import aclosing

from pipask.infra.repo_client import RepoClient
import pytest


@pytest.mark.integration
@pytest.mark.parametrize(
    "repo_url",
    [
        "https://github.com/mifeet/pyfluent-iterables",  # This repo was moved -> client should follow 301 redirect
        "https://gitlab.com/ase/ase",
    ],
)
async def test_repo_info(repo_url: str):
    async with aclosing(RepoClient()) as repo_client:
        repo_info = await repo_client.get_repo_info(repo_url)
        assert repo_info is not None
        assert repo_info.star_count > 1
