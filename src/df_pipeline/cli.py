"""
CLI utilities for ETL runner scripts.

This module provides lightweight building blocks for writing consistent,
observable runner scripts:

- :func:`log_runner` — decorator that adds start/finish logging and elapsed
  time to any ``main`` function.
- :func:`default_parser` — pre-configured :class:`argparse.ArgumentParser`
  with ``config``, ``--verbose``/``--silent``, ``--debug``/``--no-debug``,
  and ``--dry-run`` flags.

These are intentionally minimal. They handle the cross-cutting concerns
(timing, flag parsing) that every runner reinvents, without imposing any
structure on the runner itself.

Example runner
--------------
::

    import logging
    from df_pipeline.cli import log_runner, default_parser

    logger = logging.getLogger(__name__)
    script_name = "my_etl"
    default_config = "config.yaml"

    @log_runner(script_name, logger)
    def main(*, config_filename: str, dry_run: bool = False, run_start_dttm=None):
        ...

    if __name__ == "__main__":
        parser = default_parser()
        args = parser.parse_args()
        main(config_filename=args.config or default_config, dry_run=args.dry_run)
"""

from __future__ import annotations

import argparse

from functools import wraps
from logging import Logger
from typing import Callable

import pandas as pd


def log_runner(script_name: str, logger: Logger) -> Callable:
    """
    Decorator that wraps a runner function with lifecycle logging and timing.

    The decorated function receives two extra keyword arguments injected by
    the wrapper:

    - ``dry_run`` (bool): forwarded from the call site or defaulting to
      ``False``.
    - ``run_start_dttm`` (pd.Timestamp): timestamp captured just before the
      function body runs. Useful for stamping output tables.

    Parameters
    ----------
    script_name : str
        Human-readable name used in log messages.
    logger : logging.Logger
        Logger instance to write messages to.

    Returns
    -------
    Callable
        Decorator.

    Examples
    --------
    ::

        @log_runner("chemistry_etl", logger)
        def main(*, config_filename: str, dry_run: bool = False, run_start_dttm=None):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, dry_run: bool = False, **kwargs):
            logger.info("=== %s runner start ===", script_name)
            run_start_dttm = pd.Timestamp.now()

            try:
                result = func(
                    *args,
                    dry_run=dry_run,
                    run_start_dttm=run_start_dttm,
                    **kwargs,
                )
            finally:
                elapsed = (pd.Timestamp.now() - run_start_dttm).total_seconds()
                logger.info("Run finished — elapsed %.3f secs", elapsed)
                logger.info("=== %s runner done ===", script_name)

            return result

        return wrapper
    return decorator


def default_parser(
    description: str = "ETL runner",
    *,
    verbose: bool = True,
    debug: bool = False,
    dry_run: bool = False,
) -> argparse.ArgumentParser:
    """
    Create a pre-configured argument parser for ETL runner scripts.

    Provides four standard flags found in most runners:

    - ``config`` (positional, optional): path to a YAML config file.
    - ``--verbose`` / ``--silent``: enable or disable INFO-level logging.
    - ``--debug`` / ``--no-debug``: enable or disable DEBUG-level logging.
    - ``--dry-run``: skip writing outputs (runner must honour this flag).

    Parameters
    ----------
    description : str
        Description string shown in ``--help``.
    verbose : bool
        Default for ``--verbose`` / ``--silent``. Defaults to ``True``.
    debug : bool
        Default for ``--debug`` / ``--no-debug``. Defaults to ``False``.
    dry_run : bool
        Default for ``--dry-run``. Defaults to ``False``.

    Returns
    -------
    argparse.ArgumentParser

    Examples
    --------
    ::

        parser = default_parser("Brine composition ETL")
        args = parser.parse_args()
        # args.config, args.verbose, args.debug, args.dry_run
    """
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Path to YAML config file.",
    )

    # --verbose / --silent (mutually exclusive)
    group_v = parser.add_mutually_exclusive_group()
    group_v.add_argument(
        "--verbose",
        dest="verbose",
        action="store_const",
        const=True,
        default=verbose,
        help="Enable INFO-level logging (default: %(default)s).",
    )
    group_v.add_argument(
        "--silent",
        dest="verbose",
        action="store_const",
        const=False,
        help="Suppress INFO-level logging.",
    )

    # --debug / --no-debug (mutually exclusive)
    group_d = parser.add_mutually_exclusive_group()
    group_d.add_argument(
        "--debug",
        dest="debug",
        action="store_const",
        const=True,
        default=debug,
        help="Enable DEBUG-level logging (default: %(default)s).",
    )
    group_d.add_argument(
        "--no-debug",
        dest="debug",
        action="store_const",
        const=False,
        help="Disable DEBUG-level logging.",
    )

    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_const",
        const=True,
        default=dry_run,
        help="Skip writing outputs.",
    )

    return parser
