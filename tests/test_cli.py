from app.cli import main
from tests.conftest import encode


def test_cli_writes_preview_and_json(tmp_path, bands, capsys):
    src = tmp_path / "in.png"
    src.write_bytes(encode(bands))
    out, js = tmp_path / "out.png", tmp_path / "out.json"
    code = main([str(src), "--width", "30", "--colors", "3", "--out", str(out), "--json", str(js)])
    assert code == 0 and out.exists() and js.exists()
    assert "30 x 20 stitches, 3 colors" in capsys.readouterr().out


def test_cli_level_flag(tmp_path, noise):
    src = tmp_path / "in.png"
    src.write_bytes(encode(noise))
    assert main([str(src), "--level", "1", "--out", str(tmp_path / "o.png")]) == 0


def test_cli_reports_bad_input(tmp_path, capsys):
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"nope")
    assert main([str(bad), "--out", str(tmp_path / "o.png")]) == 1
    assert "error:" in capsys.readouterr().err


def test_cli_reports_invalid_settings(tmp_path, bands, capsys):
    src = tmp_path / "in.png"
    src.write_bytes(encode(bands))
    assert main([str(src), "--width", "5", "--out", str(tmp_path / "o.png")]) == 1
    assert "error:" in capsys.readouterr().err
