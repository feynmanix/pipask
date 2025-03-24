# pipc: pip with consent

# Usage
1. Install `pipc` with `pip -g install pipc`.
2. Once installed, you can use `pipc` as a drop-in replacement for `pip`.
    ```bash
    pipc install requests
    ```
3. `pipc` will perform checks on the requested packages to be installed (i.e., it will *not* check transitive dependencies).
4. `pipc` will print a report with the results and prompt you whether to continue with the installation.
5. If you proceed, `pipc` will hand over the actual installation to `pip`.

To run checks without installing, you can use the `--dry-run` flag:
```bash
pipc install requests --dry-run
```

In order to use `pipc` as a drop-in replacement for `pip`, you can create an alias:
```bash
alias pip='pipc'
```

# Development
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidance.
