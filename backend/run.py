"""
Ponto de entrada local: `python run.py`.

No Windows o psycopg assíncrono não funciona com o ProactorEventLoop (padrão do asyncio),
então o servidor sobe explicitamente num SelectorEventLoop.
"""

import asyncio
import sys

import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config("app.main:app", host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(server.serve())
