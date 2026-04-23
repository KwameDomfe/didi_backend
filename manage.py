#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None  # type: ignore


def main():
    """Run administrative tasks."""
    # Load environment variables from a .env file if present
    if load_dotenv is not None:
        load_dotenv()

    if (
        'runserver' in sys.argv
        and os.environ.get('DJANGO_DEBUG') is None
        and os.environ.get('DEBUG') is None
    ):
        os.environ['DJANGO_DEBUG'] = 'True'

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
