# pipask: pip with informed consent

![pipask-demo](https://github.com/feynmanix/pipask/blob/main/.github/pipask-demo.gif?raw=true)

# Installation
The recommended way to install `pipask` is with [pipx](https://pipx.pypa.io/stable/#install-pipx) so that `pipask` dependencies are isolated from the rest of your system:
```bash
pipx install pipask
```

Alternatively, you can install it using `pip`:
```bash
pip install pipask
```
    
# Usage
1. Once installed, you can use `pipask` as a drop-in replacement for `pip`, e.g.,:
    ```bash
    pipask install 'requests>=2.0.0'
    ```
2. `pipask` will perform checks on the packages to be installed.
3. You will get a report with the results and be prompted whether to continue with the installation.
4. If you proceed, `pipask` will hand over the actual installation to `pip`.

To run checks without installing, you can use the `--dry-run` flag:
```bash
pipask install requests --dry-run
```

In order to use `pipask` as a drop-in replacement for pip, you can alias pip to point to pipask so you don't have to remember to use it. Just add 
```bash
alias pip='pipask'
```
to your shell configuration file (`~/.bashrc` , `~/.bash_profile`, `~/.zshrc`, etc.). You can always fall back on your native pip with `python -m pip` if `pipask` doesn't work for any reason.

# Checks
* Popularity of the source repository as measured by the number of stars on GitHub or GitLab (warning below 1000 stars)
* Package and release age (warning for packages with no release older than 22 days, or for releases older than 365 days)
* Known vulnerabilities in the package available in PyPI (failure for HIGH or CRITICAL vulnerabilities, warning for MODERATE vulnerabilities)
* Check for development status and yanked status in PyPI metadata
* Number of downloads from PyPI in the last month (warning below 1000 downloads; take this with a grain of sault for reasons outlined in [PyPI documentation](https://packaging.python.org/en/latest/guides/analyzing-pypi-package-downloads/))
* License availability

All checks are executed for requested (i.e., explicitly specified) packages. Only the known vulnerabilities check is executed for transitive dependencies.

Feel free to contribute or open an issue to request more checks.

# Development
See [CONTRIBUTING.md](https://github.com/feynmanix/pipask/blob/main/CONTRIBUTING.md) for development guidance.

