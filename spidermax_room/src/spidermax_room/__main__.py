"""
CLI entry point for MAX ROOM WebSocket server.

Usage:
    python -m spidermax_room.server
    python -m spidermax_room.server --host 0.0.0.0 --port 8765
"""

import argparse
import sys

from spidermax_room.server import RoomSocketServer


def main() -> None:
    parser = argparse.ArgumentParser(description="MAX ROOM WebSocket Server v2.1.0")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    args = parser.parse_args()

    server = RoomSocketServer(host=args.host, port=args.port)
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
