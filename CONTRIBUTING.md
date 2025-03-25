# Contributing to pipask

This document provides guidelines and instructions for contributing to the project.

## Development Setup

1. Ensure you have Python 3.10 or higher installed
2. Install [Poetry](https://python-poetry.org/docs/#installation) for dependency management
3. Clone the repository:
   ```bash
   git clone https://github.com/feynmanix/pipask.git
   cd pipask
   ```
4. (If needed) activate the desired python version
5. Install dependencies:
   ```bash
   poetry install
   ```


## Development Guidance

- Write tests for new functionality
- Run tests with `poetry run pytest`
- Run **integration** tests with `poetry run pytest -m integration` (requires internet access)
- Run static checks and formatting using `./run-checks.sh`

## Compatibility testing:

To ensure pipask works across different environments, test various installation methods and platforms:

| Installation Method of `pipask` | Execution environment | Unix | Windows |
|---------------------------------|-----------------------|------|---------|
| pipx                            | Global                | ✅   |    |
| pipx                            | venv                  | ✅   |    |
| Global pip                      | Global                | ✅   |    |
| Global pip                      | venv                  | ✅   |    |
| venv pip                        | venv                  | ✅   |    |

Other edge cases to consider (some may not be currently supported):
- installing extras (e.g. `pipask install black[d]`)
- installing from a requirements file (e.g. `pipask install -r requirements.txt`)
- installing from
   - local directory (e.g. `pipask install .`)
   - git (e.g. `pipask install git+https://github.com/feynmanix/pipask.git`)
   - a file (e.g. `pipask install pipask-0.1.0-py3-none-any.whl`)
   - alternative package repository (e.g. `pipask install --index-url https://pypi.org/simple/ requests`)
- editable installs
- `#egg=name` syntax 
- installation flags
  - `--user`
  - `--upgrade` 
  - `--force-reinstall`
- installing an already installed package


## Releasing
1. Bump version before releasing with `bumpver`, e.g.:
   ```bash
   poetry run bumpver update --minor
   ```
2. Push the created tag to the repository, e.g.:
   ```bash
   git push origin tag 1.0.0
   # OR
   # git push --tags
   ```
2. Create a [new release](https://github.com/feynmanix/pipask/releases/new) with the newly created tag. The name of the release should correspond to the version number (e.g., `v1.0.0`).

## Reporting Issues

When reporting issues, please include:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Python version and environment details

Feel free to open an issue for any questions or if you need help with your contribution.
