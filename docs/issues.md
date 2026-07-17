# Issues list

#1 this happens for some reason: (FIXED in v0.1.3 - TOCTOU race between `exists()` and `makedirs()` when multiple scanner worker threads uploaded photos from the same year/month concurrently; the loser thread's `makedirs()` call raised `FileExistsError` even though the directory had just been created as intended by another thread a moment earlier. Fixed by using `makedirs(..., exist_ok=True)` in `LocalStore._write_thumbnail()`, `LocalStore.abs_folder()`, `LocalStore.__init__()`, and `LeanCache.__init__()` instead of an exists()-then-makedirs() check. Regression test added: `test/test_thumbnail.py::test_write_thumbnail_tolerates_concurrent_same_month_uploads`.)

Received unhandled exception: [Errno 17] File exists: '/nas/Photos/hspics/.thumbs/2013/02'
Traceback (most recent call last):
  File "/home/stsmr/photo-db/photo_db/scanner/scanner.py", line 101, in uploading_complete
    ph: LocalPhoto = fut.result(timeout=None if blocking else 0.1)
                     ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/stsmr/.local/share/uv/python/cpython-3.13.14-linux-x86_64-gnu/lib/python3.13/concurrent/futures/_base.py", line 453, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "/home/stsmr/.local/share/uv/python/cpython-3.13.14-linux-x86_64-gnu/lib/python3.13/concurrent/futures/_base.py", line 402, in __get_result
    raise self._exception
  File "/home/stsmr/.local/share/uv/python/cpython-3.13.14-linux-x86_64-gnu/lib/python3.13/concurrent/futures/thread.py", line 59, in run
    result = self.fn(*self.args, **self.kwargs)
  File "/home/stsmr/photo-db/photo_db/scanner/scanner.py", line 181, in process_image
    self.check_with_central_photos(ph)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^
  File "/home/stsmr/photo-db/photo_db/scanner/scanner.py", line 239, in check_with_central_photos
    ph.uuid = self.client.upload(pic.read())
              ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/home/stsmr/photo-db/photo_db/client/local_client.py", line 18, in upload
    return self.store.upload(image)
           ~~~~~~~~~~~~~~~~~^^^^^^^
  File "/home/stsmr/photo-db/photo_db/store/logic.py", line 107, in upload
    self._write_thumbnail(ph, photo)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "/home/stsmr/photo-db/photo_db/store/logic.py", line 169, in _write_thumbnail
    makedirs(thumb_dir)
    ~~~~~~~~^^^^^^^^^^^
  File "<frozen os>", line 228, in makedirs
FileExistsError: [Errno 17] File exists: '/nas/Photos/hspics/.thumbs/2013/02'
