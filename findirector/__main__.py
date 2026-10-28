"""Точка запуска монолита: здесь собираются зависимости (Infrastructure -> Application -> UI)."""
import argparse
import sys
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from findirector.application import PlanService
from findirector.infrastructure import SqlitePlanRepository
from findirector.ui import console
from findirector.ui.web import WebApp


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """Браузер держит запасные соединения; однопоточный сервер на них зависает."""
    daemon_threads = True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="findirector", description="Финдиректор: прибыль и деньги")
    parser.add_argument("mode", nargs="?", choices=["web", "console"], default="web")
    parser.add_argument("--db", default="findirector.db", help="файл SQLite (создаётся при первом запуске)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.mode == "console":
        console.main()
        return

    app = WebApp(PlanService(SqlitePlanRepository(args.db)))
    with make_server(args.host, args.port, app, server_class=ThreadingWSGIServer) as server:
        print(f"Финдиректор: http://{args.host}:{args.port}/  (БД: {args.db}; Ctrl+C — выход)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
