from dataclasses import dataclass
import click
from rich.progress import Progress, TextColumn, TaskID, TimeElapsedColumn
from rich.progress import ProgressColumn
from rich.text import Text
from rich.spinner import Spinner
from rich.progress import Task
from rich.console import RenderableType
from pipask.checks.types import CheckResultType
from rich.console import Console


@dataclass
class ParsedArgs:
    other_args: list[str]
    help: bool
    dry_run: bool
    report: str | None

    @staticmethod
    def from_click_context(ctx: click.Context) -> "ParsedArgs":
        return ParsedArgs(
            other_args=ctx.args,
            help=ctx.params["help"],
            dry_run=ctx.params["dry_run"],
            report=ctx.params["report"] or None,
        )


class CheckTask:
    def __init__(self, progress: Progress, task_id: TaskID):
        self._task_id = task_id
        self._progress = progress
        self._result: CheckResultType | None = None

    def update(self, partial_result: bool | CheckResultType):
        if partial_result is True:
            partial_result = CheckResultType.SUCCESS
        elif partial_result is False:
            partial_result = CheckResultType.FAILURE
        self._result = CheckResultType.get_worst(self._result, partial_result)
        self._progress.update(self._task_id, advance=1, result=self._result)

    def start(self):
        self._progress.start_task(self._task_id)


class SimpleTaskProgress:
    def __init__(self, console: Console | None = None):
        self.progress = Progress(
            _SpinnerAndStatusColumn(), _StateAwareTextColumn(), TimeElapsedColumn(), console=console
        )

    def __enter__(self):
        self.progress.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.progress.__exit__(exc_type, exc_value, traceback)

    def add_task(self, description: str, start: bool = True, total: int = 1) -> CheckTask:
        return CheckTask(self.progress, self.progress.add_task(description, start=start, total=total))


class _SpinnerAndStatusColumn(ProgressColumn):
    def __init__(self):
        self.spinner = Spinner("dots", style="progress.spinner")
        super().__init__()

    def render(self, task: Task) -> RenderableType:
        if task.finished:
            if task.fields["result"] is True or task.fields["result"] is CheckResultType.SUCCESS:
                return CheckResultType.SUCCESS.rich_icon
            elif task.fields["result"] is False or task.fields["result"] is CheckResultType.FAILURE:
                return CheckResultType.FAILURE.rich_icon
            elif task.fields["result"] is CheckResultType.WARNING:
                return CheckResultType.WARNING.rich_icon
            else:
                return " "
        elif task.started:
            return self.spinner.render(task.get_time())
        else:
            return " "


class _StateAwareTextColumn(TextColumn):
    def __init__(self):
        super().__init__("{task.description}")

    def render(self, task: Task) -> Text:
        text_with_format = self.text_format.format(task=task)
        if not task.finished:
            text_with_format += "..."
        if not task.started:
            text_with_format = "[grey30]" + text_with_format + "[/grey30]"
        return Text.from_markup(text_with_format, style=self.style, justify=self.justify)
