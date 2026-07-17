from photo_db.scanner import Scanner

from .conftest import STATIC_DIR


def test_scan(local_store_client, clean_store):
    sc = Scanner(local_store_client)

    folder = str(STATIC_DIR)
    sc.scan_dir(folder)
    sc.uploading_complete(blocking=True)
    print("All db photos:")
    for x in sc.processed_photos():
        print(x)
    print("Done")
