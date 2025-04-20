from rich.prompt import Confirm

from pipask.cli_helpers import CheckTask
from pipask.exception import PipAskCodeExecutionDeniedException
from contextvars import ContextVar


class PackageCodeExecutionGuard:
    _execution_allowed: ContextVar[bool | None] = ContextVar("execution_allowed", default=None)
    _progress_task: ContextVar[CheckTask | None] = ContextVar("progress_task", default=None)

    @classmethod
    def reset_confirmation_state(cls, progress_task: CheckTask | None = None):
        cls._execution_allowed.set(None)
        cls._progress_task.set(progress_task)

    @classmethod
    def check_execution_allowed(cls, package_name: str | None, package_url: str | None):
        """
        This function should be called before any code path in the forked pip code
        that may execute 3rd party code from the packages to be installed.

        It may display a warning, ask for user consent, or raise an exception depending on configuration.

        :raises PipAskCodeExecutionDeniedException: if 3rd party code execution is not allowed
        """

        package_detail = ""
        if package_name and package_url:
            package_detail = f"{package_name} from {package_url})"
        elif package_url or package_url:
            package_detail = package_name or package_url
        package_detail_message = f", including {package_detail}" if package_detail else ""

        if cls._execution_allowed.get() is True:
            return
        elif cls._execution_allowed.get() is False:
            raise PipAskCodeExecutionDeniedException(
                f"Building source distribution{' ' + package_detail if package_detail else ''} not allowed"
            )

        if progress_task := cls._progress_task.get():
            progress_task.hide()

        message = f"Unable to resolve dependencies without preparing a source distribution.\nIf you continue, 3rd party code may be executed before pipask can run checks on it{package_detail_message}.\nWould you like to continue?"
        if Confirm.ask(f"\n[yellow]{message}[/yellow]", choices=["y", "n"]):
            PackageCodeExecutionGuard._execution_allowed.set(True)
            if progress_task:
                progress_task.show()
        else:
            PackageCodeExecutionGuard._execution_allowed.set(False)
            raise PipAskCodeExecutionDeniedException(
                f"Building source distribution{' ' + package_detail if package_detail else ''} not allowed"
            )
