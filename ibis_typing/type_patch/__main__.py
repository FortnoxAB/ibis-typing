"""Apply type-patches to ibis .py modules."""

import argparse
import logging

from . import patched_modules


def write_patched_modules(verbose: bool = False) -> None:
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    for writer in patched_modules.get_patched_module_writers():
        writer.write_patched_module()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    write_patched_modules(parser.parse_args().verbose)
