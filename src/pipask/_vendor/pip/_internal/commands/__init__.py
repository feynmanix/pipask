"""
Package containing all pip commands
"""

from collections import namedtuple
from typing import Any, Dict, Optional


CommandInfo = namedtuple("CommandInfo", "module_path, class_name, summary")

# This dictionary does a bunch of heavy lifting for help output:
# - Enables avoiding additional (costly) imports for presenting `--help`.
# - The ordering matters for help display.
#
# Even though the module path starts with the same "pip._internal.commands"
# prefix, the full path makes testing easier (specifically when modifying
# `commands_dict` in test setup / teardown).
# MODIFIED for pipask - changed package path to pipask._vendor...
commands_dict: Dict[str, CommandInfo] = {
    "install": CommandInfo(
        "pipask._vendor.pip._internal.commands.install",
        "InstallCommand",
        "Install packages.",
    ),
    "download": CommandInfo(
        "pipask._vendor.pip._internal.commands.download",
        "DownloadCommand",
        "Download packages.",
    ),
    "uninstall": CommandInfo(
        "pipask._vendor.pip._internal.commands.uninstall",
        "UninstallCommand",
        "Uninstall packages.",
    ),
    "freeze": CommandInfo(
        "pipask._vendor.pip._internal.commands.freeze",
        "FreezeCommand",
        "Output installed packages in requirements format.",
    ),
    "inspect": CommandInfo(
        "pipask._vendor.pip._internal.commands.inspect",
        "InspectCommand",
        "Inspect the python environment.",
    ),
    "list": CommandInfo(
        "pipask._vendor.pip._internal.commands.list",
        "ListCommand",
        "List installed packages.",
    ),
    "show": CommandInfo(
        "pipask._vendor.pip._internal.commands.show",
        "ShowCommand",
        "Show information about installed packages.",
    ),
    "check": CommandInfo(
        "pipask._vendor.pip._internal.commands.check",
        "CheckCommand",
        "Verify installed packages have compatible dependencies.",
    ),
    "config": CommandInfo(
        "pipask._vendor.pip._internal.commands.configuration",
        "ConfigurationCommand",
        "Manage local and global configuration.",
    ),
    "search": CommandInfo(
        "pipask._vendor.pip._internal.commands.search",
        "SearchCommand",
        "Search PyPI for packages.",
    ),
    "cache": CommandInfo(
        "pipask._vendor.pip._internal.commands.cache",
        "CacheCommand",
        "Inspect and manage pip's wheel cache.",
    ),
    "index": CommandInfo(
        "pipask._vendor.pip._internal.commands.index",
        "IndexCommand",
        "Inspect information available from package indexes.",
    ),
    "wheel": CommandInfo(
        "pipask._vendor.pip._internal.commands.wheel",
        "WheelCommand",
        "Build wheels from your requirements.",
    ),
    "hash": CommandInfo(
        "pipask._vendor.pip._internal.commands.hash",
        "HashCommand",
        "Compute hashes of package archives.",
    ),
    "completion": CommandInfo(
        "pipask._vendor.pip._internal.commands.completion",
        "CompletionCommand",
        "A helper command used for command completion.",
    ),
    "debug": CommandInfo(
        "pipask._vendor.pip._internal.commands.debug",
        "DebugCommand",
        "Show information useful for debugging.",
    ),
    "help": CommandInfo(
        "pipask._vendor.pip._internal.commands.help",
        "HelpCommand",
        "Show help for commands.",
    ),
}


def get_similar_commands(name: str) -> Optional[str]:
    """Command name auto-correct."""
    from difflib import get_close_matches

    name = name.lower()

    close_commands = get_close_matches(name, commands_dict.keys())

    if close_commands:
        return close_commands[0]
    else:
        return None
