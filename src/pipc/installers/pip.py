import sys
import subprocess
import click


def pip_pass_through(args: list[str]) -> None:
    python_executable = sys.executable
    if not python_executable:
        click.echo("No Python executable found.")
        sys.exit(1)
    pip_args = [python_executable, "-m", "pip"] + args
    try:
        subprocess.run(pip_args, check=True, text=True, stdout=sys.stdout, stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)  # Preserve the original exit code