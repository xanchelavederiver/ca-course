"""Comment-preserving YAML round trip of sheet specs."""

from taskgen_web import sheetedit

from .conftest import REPO

SEM2 = (REPO / "sheets/sem2/kontrolnaya.yaml").read_text(encoding="utf-8")


def test_unchanged_data_round_trips_byte_identical():
    for path in sorted((REPO / "sheets").rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        data = sheetedit.to_plain(sheetedit.load(text))
        assert sheetedit.merged_text(text, data) == text, path


def test_form_edit_keeps_comments_and_block_scalars():
    data = sheetedit.to_plain(sheetedit.load(SEM2))
    data["budget"] = {"min": 7, "max": 9}
    data["groups"][1]["count"] = 40
    data["slots"][2]["topics"] = ["dlp.generic"]
    out = sheetedit.merged_text(SEM2, data)
    assert out.splitlines()[:5] == SEM2.splitlines()[:5]  # header comment
    assert "intro: |\n  Цель контрольной работы" in out
    assert '- {name: "6412", count: 40}' in out
    assert "topics: [dlp.generic]" in out
    assert "\n\nbudget:\n  min: 7\n  max: 9\n\nslots:" in out
    back = sheetedit.to_plain(sheetedit.load(out))
    assert back == data


def test_new_multiline_strings_become_block_scalars():
    out = sheetedit.merged_text("id: x\n", {"id": "x", "intro": "a\nb"})
    assert "intro: |\n  a\n  b\n" in out


def test_removed_keys_and_list_items():
    data = sheetedit.to_plain(sheetedit.load(SEM2))
    del data["budget"]
    data["slots"] = data["slots"][:2]
    out = sheetedit.merged_text(SEM2, data)
    assert "\nbudget:" not in out and "Эллиптические" not in out
    assert sheetedit.to_plain(sheetedit.load(out)) == data


def test_edit_keeps_unchanged_parts_byte_identical():
    data = sheetedit.to_plain(sheetedit.load(SEM2))
    data["title"] = "Контрольная работа №1"
    out = sheetedit.merged_text(SEM2, data)
    changed = [(a, b) for a, b in zip(SEM2.splitlines(), out.splitlines()) if a != b]
    assert changed[0] == ("title: Контрольная работа", "title: Контрольная работа №1")
    assert not any(line.endswith(" ") for line in out.splitlines())
