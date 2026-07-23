from unittest.mock import patch

from unstructured_api.__main__ import cli


def test_cli_api_mode():
    with (
        patch("sys.argv", ["unstructured-api", "--mode", "api"]),
        patch("unstructured_api.server.start") as mock_start,
    ):
        cli()
        mock_start.assert_called_once_with(host="0.0.0.0", port=8000)


def test_cli_serverless_mode():
    with (
        patch("sys.argv", ["unstructured-api", "--mode", "serverless"]),
        patch("unstructured_api.worker.start") as mock_start,
    ):
        cli()
        mock_start.assert_called_once()


def test_cli_custom_host_and_port():
    with (
        patch(
            "sys.argv",
            [
                "unstructured-api",
                "--mode",
                "api",
                "--host",
                "0.0.0.0",
                "--port",
                "1234",
            ],
        ),
        patch("unstructured_api.server.start") as mock_start,
    ):
        cli()
        mock_start.assert_called_once_with(host="0.0.0.0", port=1234)
