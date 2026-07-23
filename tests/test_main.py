from unittest.mock import patch

from unstructured_api.__main__ import cli


@patch("unstructured_api.worker.start")
def test_cli_serverless_mode(mock_start):
    with patch("sys.argv", ["unstructured-api", "--mode", "serverless"]):
        cli()
    mock_start.assert_called_once()


@patch("unstructured_api.server.start")
def test_cli_api_mode(mock_start):
    with patch(
        "sys.argv",
        ["unstructured-api", "--mode", "api", "--host", "127.0.0.1", "--port", "9000"],
    ):
        cli()
    mock_start.assert_called_once_with(host="127.0.0.1", port=9000)


@patch("unstructured_api.worker.start")
def test_cli_default_mode(mock_start):
    with patch("sys.argv", ["unstructured-api"]):
        cli()
    mock_start.assert_called_once()
