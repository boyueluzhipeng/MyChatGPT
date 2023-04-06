from concurrent import futures
import time
import grpc
from . import audios_pb2
from . import audios_pb2_grpc


class Greeter(audios_pb2_grpc.MainServerServicer):
    def __init__(self, rec_callback=None):
        self.rec_callback = rec_callback
    
    def getStream(self, request_iterator, context):
        for request in request_iterator:
            buf = request.datas
            if self.rec_callback:
                buf = self.rec_callback(buf)
            yield audios_pb2.Reply(datas = buf)



class Dxr_grpc_server:
    def __init__(self, port=50051, rec_callback=None) -> None:
        self.port = port
        self.rec_callback = rec_callback

    def serve(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        audios_pb2_grpc.add_MainServerServicer_to_server(Greeter(self.rec_callback), server)
        server.add_insecure_port('[::]:'+str(self.port))
        server.start()
        print('server start')
        try:
            while True:
                time.sleep(1/60)

        except KeyboardInterrupt:
            server.stop(0)
            
    def run(self):
        self.serve()