import os
import grpc
from concurrent import futures
from prometheus_client import start_http_server, Counter, Histogram
import proto.echo_pb2 as echo_pb2
import proto.echo_pb2_grpc as echo_pb2_grpc

REQS = Counter("echo_requests_total", "total")
LAT  = Histogram("echo_latency_seconds", "latency")

class Echo(echo_pb2_grpc.EchoServiceServicer):
    @LAT.time()
    def Say(self, request, context):
        REQS.inc()
        return echo_pb2.EchoReply(message=f"echo: {request.message}")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    echo_pb2_grpc.add_EchoServiceServicer_to_server(Echo(), server)
    port = os.getenv("PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    start_http_server(int(os.getenv("METRICS_PORT", "9100")))
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()