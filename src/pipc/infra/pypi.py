from datetime import datetime
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field


class ProjectUrls(BaseModel):
    bug_reports: Optional[str] = Field(None, alias="Bug Reports")
    funding: Optional[str] = Field(None, alias="Funding")
    homepage: Optional[str] = Field(None, alias="Homepage")
    source: Optional[str] = Field(None, alias="Source")
    documentation: Optional[str] = Field(None, alias="Documentation")
    repository: Optional[str] = Field(None, alias="Repository")


class ProjectInfo(BaseModel):
    license: Optional[str] = None
    name: str
    package_url: Optional[str] = None
    project_url: Optional[str] = None
    project_urls: Optional[ProjectUrls] = None
    version: str
    yanked: bool = False
    yanked_reason: Optional[str] = None


class Vulnerability(BaseModel):
    aliases: List[str]
    details: Optional[str] = None
    summary: Optional[str]= None
    fixed_in: List[str]
    id: Optional[str] = None
    link: Optional[str] = None
    source: Optional[str] = None
    withdrawn: Optional[datetime] = None


class ProjectResponse(BaseModel):
    info: ProjectInfo


class ReleaseResponse(BaseModel):
    info: ProjectInfo
    vulnerabilities: List[Vulnerability] = []

# See https://docs.pypi.org/api/json/#get-a-release for API documentation
class PypiClient:
    def __init__(self):
        self.client = httpx.AsyncClient()

    async def get_project_info(self, project_name: str) -> ProjectResponse:
        """Get project metadata from PyPI."""
        url = f"https://pypi.org/pypi/{project_name}/json"
        response = await self.client.get(url)
        response.raise_for_status()
        return ProjectResponse.model_validate(response.json())
    
    async def get_release_info(self, project_name: str, version: str) -> ReleaseResponse:
        """Get metadata for a specific project release from PyPI."""
        url = f"https://pypi.org/pypi/{project_name}/{version}/json"
        response = await self.client.get(url)
        response.raise_for_status()
        return ReleaseResponse.model_validate(response.json())

    async def aclose(self)  -> None:
        await self.client.aclose()    
