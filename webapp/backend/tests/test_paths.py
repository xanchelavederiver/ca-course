import pytest
from fastapi import HTTPException

from taskgen_web.paths import FILE_ROOTS, resolve


def test_resolve_whitelist(tmp_path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "a.pdf").write_bytes(b"x")
    (tmp_path / "secret.txt").write_text("x")
    (tmp_path / "build" / "link.pdf").symlink_to(tmp_path / "secret.txt")
    assert resolve(tmp_path, "build/a.pdf", FILE_ROOTS, must_exist=True) == tmp_path / "build" / "a.pdf"
    for bad, code in (("../x", 400), ("/etc/passwd", 400), ("build/../secret.txt", 400),
                      ("secret.txt", 404), ("taskgen/x.py", 404), ("build/link.pdf", 404),
                      ("", 400)):
        with pytest.raises(HTTPException) as e:
            resolve(tmp_path, bad, FILE_ROOTS, must_exist=True)
        assert e.value.status_code == code, bad
