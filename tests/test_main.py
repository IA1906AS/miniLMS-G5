import pytest

from uv_demo import main


def test_main(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    captured = capsys.readouterr()
    assert "Hello from uv-demo!" in captured.out
