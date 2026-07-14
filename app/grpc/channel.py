"""gRPC channel factory for outbound (client) connections."""

import grpc


def make_channel(target: str) -> grpc.aio.Channel:
    """Return an insecure async gRPC channel to *target* (``host:port``)."""
    return grpc.aio.insecure_channel(target)
