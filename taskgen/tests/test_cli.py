from click.testing import CliRunner

from taskgen.cli import main


def test_list_and_topics():
    r = CliRunner().invoke(main, ["list"])
    assert r.exit_code == 0 and "dlp.shanks" in r.output
    r = CliRunner().invoke(main, ["topics"])
    assert r.exit_code == 0 and "ecc.scalar_mult" in r.output


def test_preview_is_seeded():
    a = CliRunner().invoke(main, ["preview", "powmod.binary_mod@sem2", "--seed", "5"])
    b = CliRunner().invoke(main, ["preview", "powmod.binary_mod@sem2", "--seed", "5"])
    assert a.exit_code == 0 and a.output == b.output


def test_validate_one():
    r = CliRunner().invoke(main, ["validate", "crypto.lcg", "--count", "5"])
    assert r.exit_code == 0 and "ok    crypto.lcg@sem2" in r.output
