from pydantic import BaseModel, Field, model_validator

# See https://pip.pypa.io/en/stable/reference/installation-report/


class InstallationReportItemMetadata(BaseModel):
    name: str
    version: str
    license: str | None = None
    classifier: list[str] = Field(default_factory=list)


class InstallationReportArchiveInfo(BaseModel):
    hash: str | None = None
    hashes: dict[str, str] | None = None

    @model_validator(mode="after")
    def fill_hashes_if_missing(self):
        if self.hash is not None and self.hashes is None:
            hash_name, hash_value = self.hash.split("=", 1)
            self.hashes = {hash_name: hash_value}
        return self


class InstallationReportItemDownloadInfo(BaseModel):
    url: str
    archive_info: InstallationReportArchiveInfo | None = None


class InstallationReportItem(BaseModel):
    metadata: InstallationReportItemMetadata
    download_info: InstallationReportItemDownloadInfo | None
    requested: bool
    is_direct: bool
    is_yanked: bool = False


class PipInstallReport(BaseModel):
    version: str
    install: list[InstallationReportItem]
