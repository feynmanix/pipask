from pipask.exception import PipAskCodeExecutionDeniedException


class PackageCodeExecutionGuard:
    @staticmethod
    def check_execution_allowed(package_name: str | None, package_url: str | None):
        """
        This function should be called before any code path in the forked pip code
        that may execute 3rd party code from the packages to be installed.

        It may display a warning, ask for user consent, or raise an exception depending on configuration.

        :raises PipAskCodeExecutionDeniedException: if 3rd party code execution is not allowed
        """
        if package_name is None:
            package_name = "<unknown>"  # TODO: derive from package_url if possible
        if package_url is None:
            package_url = "<unknown>"
        raise PipAskCodeExecutionDeniedException(
            f"No execution allowed for now (package {package_name} from {package_url})"
        )  # TODO
