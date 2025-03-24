# pipask: pip with consent

# Usage
1. Install `pipask` with `pip -g install pipask`.
2. Once installed, you can use `pipask` as a drop-in replacement for `pip`.
    ```bash
    pipask install requests
    ```
3. `pipask` will perform checks on the requested packages to be installed (i.e., it will *not* check transitive dependencies).
4. `pipask` will print a report with the results and prompt you whether to continue with the installation.
5. If you proceed, `pipask` will hand over the actual installation to `pip`.

To run checks without installing, you can use the `--dry-run` flag:
```bash
pipask install requests --dry-run
```

In order to use `pipask` as a drop-in replacement for `pip`, you can create an alias:
```bash
alias pip='pipask'
```

# Development
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidance.
