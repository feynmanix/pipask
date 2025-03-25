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
- Run **integration** tests with `poetry run pytest -m integration`
- Run static checks and formatting using `./run-checks.sh`

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
