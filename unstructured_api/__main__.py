import argparse


def cli():
    parser = argparse.ArgumentParser(prog="unstructured-api")
    parser.add_argument("--mode", choices=["serverless", "api"], default="serverless")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.mode == "serverless":
        from .worker import start

        start()
    elif args.mode == "api":
        from .server import start

        start(host=args.host, port=args.port)


if __name__ == "__main__":
    cli()
