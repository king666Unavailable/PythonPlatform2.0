"""Django management entry point for the refactored system."""

import os
import sys


def _runserver_address_is_set(arguments: list[str]) -> bool:
    """Return whether runserver received an addrport positional argument."""

    options_with_values = {"--settings", "--pythonpath", "--verbosity"}
    skip_next = False
    for argument in arguments:
        if skip_next:
            skip_next = False
            continue
        if argument in options_with_values:
            skip_next = True
            continue
        if argument.startswith("-"):
            continue
        return True
    return False


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        runserver_arguments = sys.argv[2:]
        if "--help" not in runserver_arguments and "-h" not in runserver_arguments:
            if not _runserver_address_is_set(runserver_arguments):
                from django.conf import settings

                default_address = f"127.0.0.1:{settings.PYTHONPLATFORM_BACKEND_PORT}"
                sys.argv.insert(2, default_address)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
