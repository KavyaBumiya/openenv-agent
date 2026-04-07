"""OpenEnv server entrypoint shim for validators expecting server/app.py."""

print("=" * 80, flush=True)
print("[ENTRYPOINT-START] server/app.py entrypoint starting...", flush=True)
print("=" * 80, flush=True)

import os
import sys
import traceback

# Add current directory to path so we can import customer_support_env
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
print(f"[STARTUP] Added to sys.path: {sys.path[0]}", flush=True)
sys.stdout.flush()

print("[IMPORTS] Importing modules...", flush=True)
import uvicorn
print("[IMPORTS] uvicorn imported OK", flush=True)

# Add explicit error handling for import failures
try:
	print("[STARTUP] Importing app from customer_support_env.server.app...", flush=True)
	sys.stdout.flush()
	sys.stderr.flush()
	from customer_support_env.server.app import app
	print("[STARTUP] App imported successfully OK", flush=True)
	sys.stdout.flush()
	sys.stderr.flush()
except Exception as e:
	print(f"[FATAL] Failed to import app: {e}", flush=True)
	print(f"[FATAL] Traceback:", flush=True)
	traceback.print_exc(file=sys.stdout)
	sys.stdout.flush()
	sys.stderr.flush()
	sys.exit(1)


def main() -> None:
	"""Start the environment API server."""
	try:
		print("[MAIN] Entering main() function...", flush=True)
		sys.stdout.flush()
		sys.stderr.flush()
		
		print("[MAIN] Reading environment variables...", flush=True)
		host = os.getenv("HOST", "0.0.0.0")
		port = int(os.getenv("PORT", "7860"))
		print(f"[MAIN] Config: host={host}, port={port}", flush=True)
		
		print(f"[MAIN] Starting uvicorn server...", flush=True)
		print(f"[MAIN] Server will listen on http://{host}:{port}", flush=True)
		print(f"[MAIN] API docs available at http://{host}:{port}/docs", flush=True)
		sys.stdout.flush()
		sys.stderr.flush()
		
		uvicorn.run(app, host=host, port=port, log_level="info")
		
	except KeyboardInterrupt:
		print("[MAIN] Server interrupted", flush=True)
		sys.exit(0)
	except OSError as e:
		if "Address already in use" in str(e) or "Errno 48" in str(e) or "Errno 98" in str(e):
			print(f"[FATAL] Port {port} already in use - check for other running services", flush=True)
			print(f"[FATAL] Exception: {e}", flush=True)
			traceback.print_exc(file=sys.stdout)
			sys.exit(1)
		else:
			print(f"[FATAL] Network error during server startup: {e}", flush=True)
			print(f"[FATAL] Full traceback:", flush=True)
			traceback.print_exc(file=sys.stdout)
			sys.exit(1)
	except Exception as e:
		print(f"[FATAL] Uvicorn startup failed: {e}", flush=True)
		traceback.print_exc(file=sys.stdout)
		sys.stdout.flush()
		sys.stderr.flush()
		sys.exit(1)


if __name__ == "__main__":
	print("[MAIN] Calling main()...", flush=True)
	sys.stdout.flush()
	sys.stderr.flush()
	main()
