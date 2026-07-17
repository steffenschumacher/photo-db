from photo_db.config import Config
import argparse


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(description="PhotoDB importer")
    parser.add_argument(
        "-d", "--debug", dest="debug", action="store_const", default=False, const=True
    )
    parser.add_argument("-c", "--config_path", dest="cfgpath", default=None)
    parser.add_argument("-l", "--logfile", dest="logfile", default=None)
    parser.add_argument("-n", "--node-criteria", dest="nodecrit", default=None)
    args = parser.parse_args()

    if args.cfgpath:
        read_config("{}/config.ini".format(args.cfgpath), force=True)
    else:
        load_config()
