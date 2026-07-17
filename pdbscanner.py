#!/usr/bin/env python3
import argparse
from time import sleep, time

from photo_db.client import init_client
from photo_db.config import Config

if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(
        description="Photo DB Scanner - scans and imports unique images \ninto the central storage"
    )
    parser.add_argument(
        "-d", "--debug", dest="debug", action="store_const", default=False, const=True
    )
    parser.add_argument(
        "-s",
        "--scan_path",
        dest="scanpath",
        default=None,
        help="Path to scan (recursively) for images",
    )
    parser.add_argument(
        "-l",
        "--library_path",
        dest="libpath",
        default=None,
        help="Local path of image db or url for webservice",
    )
    parser.add_argument("-u", "--user", dest="user", default=None, help="username for webservice")
    parser.add_argument(
        "-p", "--password", dest="password", default=None, help="password for webservice"
    )
    args = parser.parse_args()
    if args.user and not args.password:
        raise argparse.ArgumentError(None, "Missing password with provided user?")
    if args.password and not args.user:
        raise argparse.ArgumentError(None, "Missing user with provided password?")

    config = Config(
        store_url=args.libpath,
        store_user=args.user,
        store_pass=args.password,
    )
    from photo_db.scanner import Scanner

    client = init_client(config=config)
    sc = Scanner(client, config=config)
    t1 = time()
    print(config.info())
    sc.scan_dir(args.scanpath)
    while not sc.uploading_complete(blocking=False, verbose=True):
        sleep(1)
    t2 = time()
    print(f"Done - processed {sc.processed} images in {t2 - t1:.2f} seconds")
