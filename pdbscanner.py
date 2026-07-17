#!/usr/bin/env python3
import argparse
from time import sleep, time

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
    parser.add_argument("-p", "--password", dest="pw", default=None, help="password for webservice")
    args = parser.parse_args()
    if args.libpath:
        Config.STORE_URL = args.libpath
    if args.user:
        Config.STORE_USER = args.user
        if not args.pw:
            raise argparse.ArgumentError("Missing password with provided user?")
    if args.pw:
        Config.STORE_PASS = args.pw
        if not args.pw:
            raise argparse.ArgumentError("Missing user with provided password?")
    from photo_db.scanner import Scanner

    sc = Scanner()
    t1 = time()
    print(Config.info())
    sc.scan_dir(args.scanpath)
    while not sc.uploading_complete(blocking=False, verbose=True):
        sleep(1)
    t2 = time()
    print(f"Done - processed {sc.processed} images in {t2 - t1:.2f} seconds")
