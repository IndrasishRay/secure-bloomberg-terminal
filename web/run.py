from __future__ import annotations

import argparse
import logging
import sys

import uvicorn

from config.settings import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("web_server.log"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Secure Bloomberg Terminal Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--ssl-keyfile", default=None, help="Path to SSL key file")
    parser.add_argument("--ssl-certfile", default=None, help="Path to SSL certificate file")
    parser.add_argument("--log-level", default=settings.log_level.lower(), help="Logging level")
    args = parser.parse_args()

    ssl_kwargs = {}
    if args.ssl_keyfile and args.ssl_certfile:
        ssl_kwargs["ssl_keyfile"] = args.ssl_keyfile
        ssl_kwargs["ssl_certfile"] = args.ssl_certfile
        logger.info("SSL enabled: key=%s cert=%s", args.ssl_keyfile, args.ssl_certfile)

    logger.info(
        "Starting web server at %s:%s (log_level=%s)",
        args.host,
        args.port,
        args.log_level,
    )

    uvicorn.run(
        "web.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
