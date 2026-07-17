from photo_db.photo import Photo


def test_similar():
    orig = Photo.from_file("static/08-190641-4631.jpeg")
    modified = Photo.from_file("static/08-190641-4631-modified.jpeg")
    assert orig.similar_to(modified)
    assert orig.preferable_to(modified)
    assert not modified.preferable_to(orig)
    assert not orig.preferable_to(orig)
    assert orig.similar_to_hash(modified.hash)
    assert orig.hash != modified.hash
    unrelated = Photo.from_file("static/25-121007-33d0.jpeg")
    assert not orig.similar_to(unrelated)


def test_duplicate():
    orig = Photo.from_file("static/08-190641-4631.jpeg")
    modified = Photo.from_file("static/08-190641-4631-modified.jpeg")
    assert orig.hash != modified.hash
    assert orig.hash == orig.hash
    unrelated = Photo.from_file("static/25-121007-33d0.jpeg")
    assert orig.hash != unrelated.hash
