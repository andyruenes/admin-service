"""Async gRPC server lifecycle management.

Register servicers here as .proto definitions are added.
"""

import grpc

from app.config import settings

_server: grpc.aio.Server | None = None


async def start_grpc_server() -> grpc.aio.Server:
    global _server
    server = grpc.aio.server()
    # add_*Servicer(server, ...) calls go here once protos are compiled
    server.add_insecure_port(f"[::]:{settings.GRPC_SERVER_PORT}")
    await server.start()
    _server = server
    return server


async def stop_grpc_server() -> None:
    if _server is not None:
        await _server.stop(grace=5)
