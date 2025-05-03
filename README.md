# pipask: Know What You're Installing Before It's Too Late
A safer way to install Python packages without compromising convenience.
![pipask-demo](https://github.com/feynmanix/pipask/blob/main/.github/pipask-demo.gif?raw=true)

Pipask is a drop-in replacement for pip that performs security checks before installing a package.
Unlike `pip`, which needs to download and execute code from source distribution first to get dependency metadata, 
pipask relies on metadata from PyPI whenever possible. If 3rd party code execution is necessary, pipask asks for consent first.
The actual installation is handed over to `pip` if installation is approved.

See the **[introductory blog post](https://medium.com/data-science-collective/pipask-know-what-youre-installing-before-it-s-too-late-2a6afce80987)** for more information.

## Installation

The recommended way to install `pipask` is with [pipx](https://pipx.pypa.io/stable/#install-pipx) to isolate dependencies:
```bash
pipx install pipask
```

Alternatively, you can install it using `pip`:
```bash
pip install pipask
```
    
## Usage

Use `pipask` exactly as you would use `pip`:
```bash
pipask install requests
pipask install 'fastapi>=0.100.0'
pipask install -r requirements.txt
```

For maximum convenience, alias pip to point to pipask:
```bash
alias pip='pipask'
```

Add this to your shell configuration file (`~/.bashrc`, `~/.bash_profile`, `~/.zshrc`, etc.). You can always fall back to native pip with `python -m pip` if needed.

To run checks without installing, use the `--dry-run` flag:
```bash
pipask install requests --dry-run
```

## Security Checks

Pipask performs these checks before allowing installation:

* **Repository popularity** - verification of links from PyPI to repositories, number of stars on GitHub or GitLab source repo (warning below 1000 stars)
* **Package and release age** - warning for new packages (less than 22 days old) or stale releases (older than 365 days)
* **Known vulnerabilities** in the package available in PyPI (failure for HIGH or CRITICAL vulnerabilities, warning for MODERATE vulnerabilities)
* **Number of downloads** from PyPI in the last month (warning below 1000 downloads)
* **Metadata verification**: Checks for license availability, development status, and yanked packages

All checks are executed for requested (i.e., explicitly specified) packages. Only the known vulnerabilities check is executed for transitive dependencies.

## How pipask works

Under the hood, pipask:

1. Uses PyPI's JSON API to retrieve metadata without downloading or executing code
2. When code execution is unavoidable, asks for confirmation first
3. Collects security information from multiple sources:
   - Download statistics from pypistats.org
   - Repository popularity from GitHub or GitLab
   - Vulnerability details from OSV.dev
   - Attestation metadata from PyPI integrity API
4. Presents a formatted report and asks for consent
5. Hands over to standard pip for the actual installation if approved

## Development
See [CONTRIBUTING.md](https://github.com/feynmanix/pipask/blob/main/CONTRIBUTING.md) for development guidance.
