"""Container-local liveness probe; deliberately no credentials or DB contents."""
import os
import sys
import urllib.request


def main():
    try:
        port = int(os.getenv('CHATIDY_PORT', '8877'))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/healthz', timeout=3) as response:
            return 0 if response.status == 200 and response.read(64) == b'{"status": "ok"}' else 1
    except (OSError, ValueError):
        return 1


if __name__ == '__main__':
    sys.exit(main())
