"""Exceptions used throughout package.

This module MUST NOT try to import from anything within `pip._internal` to
operate. This is expected to be importable from any/all files within the
subpackage and, thus, should not depend on them.
"""


import configparser
import contextlib
import locale
import logging
import pathlib
import re
import sys
from itertools import chain, groupby, repeat
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Union


from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text

if TYPE_CHECKING:
    from typing import Literal

    # from pipask._vendor.pip.metadata import BaseDistribution
    # from pipask._vendor.pip.req.req_install import InstallRequirement

logger = logging.getLogger(__name__)


#
# Scaffolding
#
def _is_kebab_case(s: str) -> bool:
    return re.match(r"^[a-z]+(-[a-z]+)*$", s) is not None


def _prefix_with_indent(
    s: Union[Text, str],
    console: Console,
    *,
    prefix: str,
    indent: str,
) -> Text:
    if isinstance(s, Text):
        text = s
    else:
        text = console.render_str(s)

    return console.render_str(prefix, overflow="ignore") + console.render_str(
        f"\n{indent}", overflow="ignore"
    ).join(text.split(allow_blank=True))


class PipError(Exception):
    """The base pip error."""


class DiagnosticPipError(PipError):
    """An error, that presents diagnostic information to the user.

    This contains a bunch of logic, to enable pretty presentation of our error
    messages. Each error gets a unique reference. Each error can also include
    additional context, a hint and/or a note -- which are presented with the
    main error message in a consistent style.

    This is adapted from the error output styling in `sphinx-theme-builder`.
    """

    reference: str

    def __init__(
        self,
        *,
        kind: 'Literal["error", "warning"]' = "error",
        reference: Optional[str] = None,
        message: Union[str, Text],
        context: Optional[Union[str, Text]],
        hint_stmt: Optional[Union[str, Text]],
        note_stmt: Optional[Union[str, Text]] = None,
        link: Optional[str] = None,
    ) -> None:
        # Ensure a proper reference is provided.
        if reference is None:
            assert hasattr(self, "reference"), "error reference not provided!"
            reference = self.reference
        assert _is_kebab_case(reference), "error reference must be kebab-case!"

        self.kind = kind
        self.reference = reference

        self.message = message
        self.context = context

        self.note_stmt = note_stmt
        self.hint_stmt = hint_stmt

        self.link = link

        super().__init__(f"<{self.__class__.__name__}: {self.reference}>")

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"reference={self.reference!r}, "
            f"message={self.message!r}, "
            f"context={self.context!r}, "
            f"note_stmt={self.note_stmt!r}, "
            f"hint_stmt={self.hint_stmt!r}"
            ")>"
        )

    def __rich_console__(
        self,
        console: Console,
        options: ConsoleOptions,
    ) -> RenderResult:
        colour = "red" if self.kind == "error" else "yellow"

        yield f"[{colour} bold]{self.kind}[/]: [bold]{self.reference}[/]"
        yield ""

        if not options.ascii_only:
            # Present the main message, with relevant context indented.
            if self.context is not None:
                yield _prefix_with_indent(
                    self.message,
                    console,
                    prefix=f"[{colour}]×[/] ",
                    indent=f"[{colour}]│[/] ",
                )
                yield _prefix_with_indent(
                    self.context,
                    console,
                    prefix=f"[{colour}]╰─>[/] ",
                    indent=f"[{colour}]   [/] ",
                )
            else:
                yield _prefix_with_indent(
                    self.message,
                    console,
                    prefix="[red]×[/] ",
                    indent="  ",
                )
        else:
            yield self.message
            if self.context is not None:
                yield ""
                yield self.context

        if self.note_stmt is not None or self.hint_stmt is not None:
            yield ""

        if self.note_stmt is not None:
            yield _prefix_with_indent(
                self.note_stmt,
                console,
                prefix="[magenta bold]note[/]: ",
                indent="      ",
            )
        if self.hint_stmt is not None:
            yield _prefix_with_indent(
                self.hint_stmt,
                console,
                prefix="[cyan bold]hint[/]: ",
                indent="      ",
            )

        if self.link is not None:
            yield ""
            yield f"Link: {self.link}"


#
# Actual Errors
#
class ConfigurationError(PipError):
    """General exception in configuration"""

class InstallationError(PipError):
    """General exception during installation"""


class UninstallationError(PipError):
    """General exception during uninstallation"""

class CommandError(PipError):
    """Raised when there is an error in command-line arguments"""

class HashError(InstallationError):
    """
    A failure to verify a package against known-good hashes

    :cvar order: An int sorting hash exception classes by difficulty of
        recovery (lower being harder), so the user doesn't bother fretting
        about unpinned packages when he has deeper issues, like VCS
        dependencies, to deal with. Also keeps error reports in a
        deterministic order.
    :cvar head: A section heading for display above potentially many
        exceptions of this kind
    :ivar req: The InstallRequirement that triggered this error. This is
        pasted on after the exception is instantiated, because it's not
        typically available earlier.

    """

    req: Optional["InstallRequirement"] = None
    head = ""
    order: int = -1

    def body(self) -> str:
        """Return a summary of me for display under the heading.

        This default implementation simply prints a description of the
        triggering requirement.

        :param req: The InstallRequirement that provoked this error, with
            its link already populated by the resolver's _populate_link().

        """
        return f"    {self._requirement_name()}"

    def __str__(self) -> str:
        return f"{self.head}\n{self.body()}"

    def _requirement_name(self) -> str:
        """Return a description of the requirement that triggered me.

        This default implementation returns long description of the req, with
        line numbers

        """
        return str(self.req) if self.req else "unknown package"


class VcsHashUnsupported(HashError):
    """A hash was provided for a version-control-system-based requirement, but
    we don't have a method for hashing those."""

    order = 0
    head = (
        "Can't verify hashes for these requirements because we don't "
        "have a way to hash version control repositories:"
    )


class DirectoryUrlHashUnsupported(HashError):
    """A hash was provided for a version-control-system-based requirement, but
    we don't have a method for hashing those."""

    order = 1
    head = (
        "Can't verify hashes for these file:// requirements because they "
        "point to directories:"
    )


class HashMissing(HashError):
    """A hash was needed for a requirement but is absent."""

    order = 2
    head = (
        "Hashes are required in --require-hashes mode, but they are "
        "missing from some requirements. Here is a list of those "
        "requirements along with the hashes their downloaded archives "
        "actually had. Add lines like these to your requirements files to "
        "prevent tampering. (If you did not enable --require-hashes "
        "manually, note that it turns on automatically when any package "
        "has a hash.)"
    )

    def __init__(self, gotten_hash: str) -> None:
        """
        :param gotten_hash: The hash of the (possibly malicious) archive we
            just downloaded
        """
        self.gotten_hash = gotten_hash

    def body(self) -> str:
        # Dodge circular import.
        from pip._internal.utils.hashes import FAVORITE_HASH

        package = None
        if self.req:
            # In the case of URL-based requirements, display the original URL
            # seen in the requirements file rather than the package name,
            # so the output can be directly copied into the requirements file.
            package = (
                self.req.original_link
                if self.req.is_direct
                # In case someone feeds something downright stupid
                # to InstallRequirement's constructor.
                else getattr(self.req, "req", None)
            )
        return "    {} --hash={}:{}".format(
            package or "unknown package", FAVORITE_HASH, self.gotten_hash
        )


class HashUnpinned(HashError):
    """A requirement had a hash specified but was not pinned to a specific
    version."""

    order = 3
    head = (
        "In --require-hashes mode, all requirements must have their "
        "versions pinned with ==. These do not:"
    )


class HashMismatch(HashError):
    """
    Distribution file hash values don't match.

    :ivar package_name: The name of the package that triggered the hash
        mismatch. Feel free to write to this after the exception is raise to
        improve its error message.

    """

    order = 4
    head = (
        "THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS "
        "FILE. If you have updated the package versions, please update "
        "the hashes. Otherwise, examine the package contents carefully; "
        "someone may have tampered with them."
    )

    def __init__(self, allowed: Dict[str, List[str]], gots: Dict[str, "_Hash"]) -> None:
        """
        :param allowed: A dict of algorithm names pointing to lists of allowed
            hex digests
        :param gots: A dict of algorithm names pointing to hashes we
            actually got from the files under suspicion
        """
        self.allowed = allowed
        self.gots = gots

    def body(self) -> str:
        return f"    {self._requirement_name()}:\n{self._hash_comparison()}"

    def _hash_comparison(self) -> str:
        """
        Return a comparison of actual and expected hash values.

        Example::

               Expected sha256 abcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde
                            or 123451234512345123451234512345123451234512345
                    Got        bcdefbcdefbcdefbcdefbcdefbcdefbcdefbcdefbcdef

        """

        def hash_then_or(hash_name: str) -> "chain[str]":
            # For now, all the decent hashes have 6-char names, so we can get
            # away with hard-coding space literals.
            return chain([hash_name], repeat("    or"))

        lines: List[str] = []
        for hash_name, expecteds in self.allowed.items():
            prefix = hash_then_or(hash_name)
            lines.extend((f"        Expected {next(prefix)} {e}") for e in expecteds)
            lines.append(
                f"             Got        {self.gots[hash_name].hexdigest()}\n"
            )
        return "\n".join(lines)


class UnsupportedPythonVersion(InstallationError):
    """Unsupported python version according to Requires-Python package
    metadata."""


class ConfigurationFileCouldNotBeLoaded(ConfigurationError):
    """When there are errors while loading a configuration file"""

    def __init__(
        self,
        reason: str = "could not be loaded",
        fname: Optional[str] = None,
        error: Optional[configparser.Error] = None,
    ) -> None:
        super().__init__(error)
        self.reason = reason
        self.fname = fname
        self.error = error

    def __str__(self) -> str:
        if self.fname is not None:
            message_part = f" in {self.fname}."
        else:
            assert self.error is not None
            message_part = f".\n{self.error}\n"
        return f"Configuration file {self.reason}{message_part}"


_DEFAULT_EXTERNALLY_MANAGED_ERROR = f"""\
The Python environment under {sys.prefix} is managed externally, and may not be
manipulated by the user. Please use specific tooling from the distributor of
the Python installation to interact with this environment instead.
"""


class ExternallyManagedEnvironment(DiagnosticPipError):
    """The current environment is externally managed.

    This is raised when the current environment is externally managed, as
    defined by `PEP 668`_. The ``EXTERNALLY-MANAGED`` configuration is checked
    and displayed when the error is bubbled up to the user.

    :param error: The error message read from ``EXTERNALLY-MANAGED``.
    """

    reference = "externally-managed-environment"

    def __init__(self, error: Optional[str]) -> None:
        if error is None:
            context = Text(_DEFAULT_EXTERNALLY_MANAGED_ERROR)
        else:
            context = Text(error)
        super().__init__(
            message="This environment is externally managed",
            context=context,
            note_stmt=(
                "If you believe this is a mistake, please contact your "
                "Python installation or OS distribution provider. "
                "You can override this, at the risk of breaking your Python "
                "installation or OS, by passing --break-system-packages."
            ),
            hint_stmt=Text("See PEP 668 for the detailed specification."),
        )

    @staticmethod
    def _iter_externally_managed_error_keys() -> Iterator[str]:
        # LC_MESSAGES is in POSIX, but not the C standard. The most common
        # platform that does not implement this category is Windows, where
        # using other categories for console message localization is equally
        # unreliable, so we fall back to the locale-less vendor message. This
        # can always be re-evaluated when a vendor proposes a new alternative.
        try:
            category = locale.LC_MESSAGES
        except AttributeError:
            lang: Optional[str] = None
        else:
            lang, _ = locale.getlocale(category)
        if lang is not None:
            yield f"Error-{lang}"
            for sep in ("-", "_"):
                before, found, _ = lang.partition(sep)
                if not found:
                    continue
                yield f"Error-{before}"
        yield "Error"

    @classmethod
    def from_config(
        cls,
        config: Union[pathlib.Path, str],
    ) -> "ExternallyManagedEnvironment":
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(config, encoding="utf-8")
            section = parser["externally-managed"]
            for key in cls._iter_externally_managed_error_keys():
                with contextlib.suppress(KeyError):
                    return cls(section[key])
        except KeyError:
            pass
        except (OSError, UnicodeDecodeError, configparser.ParsingError):
            from pip._internal.utils._log import VERBOSE

            exc_info = logger.isEnabledFor(VERBOSE)
            logger.warning("Failed to read %s", config, exc_info=exc_info)
        return cls(None)
