"""Hermes gRPC client.

Requires compiled stubs — run scripts/compile_protos.sh first.
The channel lifecycle is managed externally (app.state.hermes_channel in main.py).
"""

import grpc

from app.grpc.generated.hermes import gateway_pb2_grpc, lists_pb2_grpc
from app.grpc.generated.hermes.control import business_pb2_grpc
from app.grpc.generated.hermes.v2 import message_trace_pb2_grpc, whatsapp_pb2_grpc


class HermesClient:
    """Thin wrapper around all hermes-server service stubs."""

    def __init__(self, channel: grpc.aio.Channel) -> None:
        # gateway.proto services
        self.events = gateway_pb2_grpc.EventServiceStub(channel)
        self.notifications = gateway_pb2_grpc.NotificationServiceStub(channel)
        self.notifications_out = gateway_pb2_grpc.NotificationOutServiceStub(channel)
        self.firebase = gateway_pb2_grpc.FirebaseServiceStub(channel)
        # lists.proto services
        self.lists = lists_pb2_grpc.ListServiceStub(channel)
        self.contacts = lists_pb2_grpc.ContactServiceStub(channel)
        self.list_delivery = lists_pb2_grpc.DeliveryServiceStub(channel)
        # v2/whatsapp.proto
        self.whatsapp = whatsapp_pb2_grpc.WhatsappServiceStub(channel)
        # v2/message-trace.proto
        self.message_trace = message_trace_pb2_grpc.MessageTraceServiceStub(channel)
        # control/business.proto
        self.business = business_pb2_grpc.BusinessServiceStub(channel)
