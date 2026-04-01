"""OpenEnv server entrypoint shim for validators expecting server/app.py."""

import os

import uvicorn

from customer_support_env.server.app import app


def main() -> None:
	"""Start the environment API server."""
	host = os.getenv("HOST", "0.0.0.0")
	port = int(os.getenv("PORT", "7860"))
	uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
	main()
