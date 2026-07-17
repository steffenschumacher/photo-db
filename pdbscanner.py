#!/usr/bin/env python3
"""Headless CLI for scanning a folder and importing new photos.

This is the "scan only" counterpart to the PySide6 desktop UI
(``photodb-ui.py``) - same ``Scanner``/duplicate-detection pipeline, no
GUI, browsing, or thumbnails. Handy for servers/headless boxes, cron jobs,
or anyone who doesn't want the Qt dependency at all.

Usage:
    uv run python pdbscanner.py -s /path/to/import -l /path/to/library
    uv run python pdbscanner.py -s /path/to/import -l https://host/api -u alice -p secret
"""

import argparse
from time import sleep, time

from photo_db.client import init_client
from photo_db.config import Config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Photo DB Scanner - scans and imports unique images \ninto the central storage"
    )
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_const",
        default=False,
        const=True,
        help="Print periodic progress updates (every ~100 photos) while scanning; "
        "off by default to keep output to just the per-photo import log",
    )
    parser.add_argument(
        "-s",
        "--scan_path",
        dest="scanpath",
        required=True,
        help="Path to scan (recursively) for images",
    )
    parser.add_argument(
        "-l",
        "--library_path",
        dest="libpath",
        default=None,
        help="Local path of image db or url for webservice (defaults to Config's usual "
        "PH_STORE_URL/.env resolution if omitted)",
    )
    parser.add_argument("-u", "--user", dest="user", default=None, help="username for webservice")
    parser.add_argument(
        "-p", "--password", dest="password", default=None, help="password for webservice"
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.user and not args.password:
        parser.error("Missing password with provided user?")
    if args.password and not args.user:
        parser.error("Missing user with provided password?")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    config = Config(
        store_url=args.libpath,
        store_user=args.user,
        store_pass=args.password,
        debug=args.debug,
    )
    from photo_db.scanner import Scanner

    client = init_client(config=config)
    sc = Scanner(client, config=config)
    t1 = time()
    print(config.info())
    sc.scan_dir(args.scanpath)
    while not sc.uploading_complete(blocking=False, verbose=args.debug)[0]:
        sleep(1)
    t2 = time()
    print(f"Done - processed {sc.processed} images in {t2 - t1:.2f} seconds")


if __name__ == "__main__":
    main()
