from concurrent import futures
import copy
import time
import cv2
import grpc
import numpy as np
from . import Datas_pb2
from . import Datas_pb2_grpc
import json


class Greeter(Datas_pb2_grpc.MainServerServicer):
    def __init__(self, rec_callback=None):
        self.rec_callback = rec_callback
    
    def getStream(self, request_iterator, context):
        for request in request_iterator:
            dBuf = np.frombuffer(request.datas, dtype=np.uint8)
            dst = cv2.imdecode(dBuf, cv2.IMREAD_COLOR)
            dst_copy = copy.deepcopy(dst)
            json_data = json.loads(request.json_data)
            if self.rec_callback:
                dst, json_data = self.rec_callback(dst, json_data)
            if dst is None:
                dst = dst_copy
            _, buf = cv2.imencode('.jpg', dst)
            yield Datas_pb2.Reply(datas = buf.tobytes(), json_data = json.dumps(json_data))



class Dxr_grpc_server:
    def __init__(self, port=50051, rec_callback=None) -> None:
        self.port = port
        self.rec_callback = rec_callback

    def serve(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        Datas_pb2_grpc.add_MainServerServicer_to_server(Greeter(self.rec_callback), server)
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