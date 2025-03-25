# pipask: pip with consent

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
2. `pipask` will perform checks on the requested packages to be installed (i.e., it will *not* check transitive dependencies).
3. `pipask` will print a report with the results and prompt you whether to continue with the installation.
4. If you proceed, `pipask` will hand over the actual installation to `pip`.

To run checks without installing, you can use the `--dry-run` flag:
```bash
pipask install requests --dry-run
```

In order to use `pipask` as a drop-in replacement for `pip`, you can create an alias:
```bash
alias pip='pipask'
```

# Development
See [CONTRIBUTING.md](https://github.com/feynmanix/pipask/blob/main/CONTRIBUTING.md) for development guidance.
