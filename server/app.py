"""OpenEnv server entrypoint shim for validators expecting server/app.py."""

import os
import sys
import traceback

import uvicorn

# Add explicit error handling for import failures
try:
	print("🔧 [STARTUP] Importing app from customer_support_env.server.app...", flush=True)
	from customer_support_env.server.app import app
	print("✅ [STARTUP] App imported successfully", flush=True)
except Exception as e:
	print(f"❌ [FATAL] Failed to import app: {e}", flush=True)
	print(f"❌ [FATAL] Traceback:", flush=True)
	traceback.print_exc(file=sys.stdout)
	sys.exit(1)


def main() -> None:
	"""Start the environment API server."""
	try:
		print("🔧 [STARTUP] Reading environment variables...", flush=True)
		host = os.getenv("HOST", "0.0.0.0")
		port = int(os.getenv("PORT", "7860"))
		print(f"🔧 [STARTUP] Starting uvicorn on {host}:{port}", flush=True)
		uvicorn.run(app, host=host, port=port, log_level="info")
	except Exception as e:
		print(f"❌ [FATAL] Uvicorn startup failed: {e}", flush=True)
		traceback.print_exc(file=sys.stdout)
		sys.exit(1)


if __name__ == "__main__":
	main()
