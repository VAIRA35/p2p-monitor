import argparse
import asyncio
from app.main import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P2P monitor")
    parser.add_argument("--once", action="store_true", help="run a single update and exit")
    args = parser.parse_args()
    try:
        asyncio.run(main(once=args.once))
    except KeyboardInterrupt:
        print("\nStopped.")
