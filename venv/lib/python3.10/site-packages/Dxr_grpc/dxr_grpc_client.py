import json
import grpc
import cv2
import numpy as np
from . import Datas_pb2
from . import Datas_pb2_grpc
from threading import Thread
import time
            
class Dxr_grpc_client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.channel = grpc.insecure_channel(self.ip + ':' + self.port)
        self.stub = Datas_pb2_grpc.MainServerStub(self.channel)
        # 启动线程，用来持续监听self.channel是否连接，如果断开则重新连接
        # self.thread = Thread(target=self._keep_connect, args=(), daemon=True)
        # self.thread.start()
        
    def _keep_connect(self):
        while True:
            time.sleep(1)
            # grpc_health.v1.Health.Check
            res = grpc.channel_ready_future(self.channel).result()
            if res is not None:
                print('channel is not ready, reconnecting...')
                self.channel = grpc.insecure_channel(self.ip + ':' + self.port)
                self.stub = Datas_pb2_grpc.MainServerStub(self.channel)
            else:
                pass
        
    def self_request(self, frame, json_data):
        ret, buf = cv2.imencode('.jpg', frame)
        if ret != 1:
            return
        yield Datas_pb2.Request(datas = buf.tobytes(), json_data = json.dumps(json_data))
        
    def get_response(self, frame, json_data):
        try:
            responses = self.stub.getStream( self.self_request(frame, json_data))
            for req in responses:
                dBuf = np.frombuffer(req.datas, dtype = np.uint8)
                dst = cv2.imdecode(dBuf, cv2.IMREAD_COLOR)
                res_json_data = json.loads(req.json_data)
                return_dit = {
                    'dst': dst,
                    'res_json_data': res_json_data
                }
                yield return_dit
        except grpc.RpcError as e:
            pass
            
            
if __name__ == '__main__':
    client = Dxr_grpc_client('10.10.8.152', '50051')
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    json_data = {
        'type': 'face',
    }
    while True:
        ret, frame = cap.read()
        if ret != 1:
            continue
        responses = client.get_response(frame, json_data)
        for req in responses:
            cv2.imshow('dst Image', req['dst'])
            k = cv2.waitKey(1)
            if k == 27:
                break
            elif k == ord('g'):
                json_data['type'] = 'gray'
            elif k == ord('b'):
                json_data['type'] = 'blur'
            elif k == ord('c'):
                json_data['type'] = 'canny'
            elif k == ord('r'):
                json_data['type'] = 'rotate'
            elif k == ord('f'):
                json_data['type'] = 'face'
            else:
                pass
            