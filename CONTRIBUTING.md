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
- Run static checks and formatting using `./run-checks.sh`


## Reporting Issues

When reporting issues, please include:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Python version and environment details

Feel free to open an issue for any questions or if you need help with your contribution.
