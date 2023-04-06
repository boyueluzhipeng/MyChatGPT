import queue
import threading
# from Dxr_mqtt.dxr_log import *
import asyncio
import logging
import time
import cv2
import numpy as np
from aiortsp.transport import RTPTransportClient, transport_for_scheme
from aiortsp.rtsp.connection import RTSPConnection
from aiortsp.rtsp.session import RTSPMediaSession
logger = logging.getLogger('rtsp_client')
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
logger.setLevel(logging.ERROR)

recv = b''
thermalStream = b''
frame_list = []

class Probe(RTPTransportClient):

    def __init__(self, origin_queue=None):
        self.rtp_count = 0
        self.rtcp_count = 0
        self.origin_queue = origin_queue

    def handle_rtp(self, rtp):
        global thermalStream, frame_list
        # V：RTP协议的版本号，占2位，当前协议版本号为2
        # P：填充标志，占1位，如果P=1，则在该报文的尾部填充一个或多个额外的八位组，它们不是有效载荷的一部分
        # X：扩展标志，保留为0，后续如有需求可增加扩展头信息
        # CC：CSRC计数器，占4位，指示CSRC标识符的个数
        # M: maker标志位； thermalStream数据较多时将采取分包发送，分包数据maker标志位为0，结束包maker标志位为 1
        # PT: 有效载荷类型，占7位，用于说明RTP报文中有效载荷的类型，当前热成像流统一返回 109（即0x6D
        # 序列号：占16位，用于标识发送者所发送的RTP报文的序列号，每发送一个报文，序列号增1。这个字段当下层的 承载协议用UDP的时候，网络状况不好的时候可以用来检查丢包。同时出现网络抖动的情况可以用来对数据进行 重新排序，在helix服务器中这个字段是从0开始的，同时音频包和视频包的sequence是分别记数的；
        # 时戳(Timestamp)：占32位，时戳反映了该RTP报文的第一个八位组的采样时刻。接收者使用时戳来计算延迟和延 迟抖动，并进行同步控制
        # 同步信源(SSRC)标识符：占32位，用于标识同步信源。该标识符是随机选择的，参加同一视频会议的两个同步信 源不能有相同的SSRC
        # 特约信源(CSRC)标识符：每个CSRC标识符占32位，可以有0～15个。每个CSRC标识了包含在该RTP报文有效载荷中 的所有特约信源
        # 载荷 encoding 为thermalStream 类型
        # FUA：FU Indicator，FU Header，FU Payload
        # FU Indicator：FU Indicator是一个8bit的字段，它的结构如下：
        # 0 1 2 3 4 5 6 7
        # +---------------+
        # |0|1|0|0|0|0|0|0|
        # +---------------+
        # |F|NRI|  Type   |
        # +---------------+
        # F：0表示单一NALU，1表示分片NALU
        # NRI：NALU的重要性指示，值越大，重要性越高
        # Type：NALU的类型, 16~23为FU-A，24~31为FU-B
        # 前两位为版本号，后面为负载类型
        # FU Header：FU Header是一个8bit的字段，它的结构如下：
        # 0 1 2 3 4 5 6 7
        # +---------------+
        # |0|1|0|0|0|0|0|0|
        # +---------------+
        # |S|E|R|  Type   |
        # +---------------+
        # S：1表示该NALU的开始，0表示该NALU的中间或结束
        # E：1表示该NALU的结束，0表示该NALU的中间或开始
        # R：保留位
        # Type：NALU的类型, 16~23为FU-A，24~31为FU-B
        d = rtp.pack()
        v = d[0] >> 6
        p = (d[0] >> 5) & 0x01
        x = (d[0] >> 4) & 0x01
        cc = d[0] & 0x0f
        m = (d[1] >> 7) & 0x01
        pt = d[1] & 0x7f
        seq = (d[2] << 8) + d[3]
        ts = (d[4] << 24) + (d[5] << 16) + (d[6] << 8) + d[7]
        ssrc = (d[8] << 24) + (d[9] << 16) + (d[10] << 8) + d[11]
        # 特约信源(CSRC)标识符：每个CSRC标识符占32位，可以有0～15个。每个CSRC标识了包含在该RTP报文有效载荷中 的所有特约信源
        csrc = []
        for i in range(cc):
            csrc.append((d[12 + i * 4] << 24) + (d[13 + i * 4] << 16) + (d[14 + i * 4] << 8) + d[15 + i * 4])
        payload = d[12 + cc * 4:]
        # 如果P=1，则在该报文的尾部填充一个或多个额外的八位组，它们不是有效载荷的一部分
        if p == 1:
            payload = payload[:-1]
        if m == 1:
            thermalStream += payload
            
            # 如果长度不为442500，如果大于442500，截取442500长度的数据，如果小于442500，将数据拼接到thermalStream中
            if len(thermalStream) == 442500:
                # print('v:{}, p:{}, x:{}, cc:{}, m:{}, spt:{}, seq:{}, ts:{}, ssrc:{}, csrc:{}, len(thermalStream):{}'.format(v, p, x, cc, m, pt, seq, ts, ssrc, csrc, len(thermalStream)), end='\r')  
                # 去掉前128 + 4个字节，剩下的为384*288*4 表示每个像素点的温度数据用 float（4 字节）
                frame = np.frombuffer(thermalStream[132:], dtype=np.float32).reshape(288, 384)
                if self.origin_queue is not None:
                    if self.origin_queue.full():
                        self.origin_queue.get()
                    self.origin_queue.put(frame)
            else:
                # print(len(thermalStream))
                pass
            thermalStream = b''
        else:
            thermalStream += payload  
        # payload为视频数据，可以进行解码，转码，保存等操作
        # print(payload)
        self.rtp_count += 1

    def handle_rtcp(self, rtcp):
        self.rtcp_count += 1
        logger.debug('RTCP received: %s', rtcp)

class RTSP_Client:
    def __init__(self, ip, port, username, password, logger=None):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.url = f'rtsp://{username}:{password}@{ip}:{port}/ISAPI/Streaming/thermal/channels/2/streamType/pixel-to-pixel_thermometry_data'
        print(self.url)
        self.origin_queue = queue.Queue(maxsize=1)
        self.probe = Probe(self.origin_queue)
        # 在这里启动一个线程，用来接收视频数据
        self.thread = threading.Thread(target=self.start)
        self.thread.setDaemon(True)
        self.is_running = True
        self.thread.start()
        self.logger = logger
        
    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect())
        
    def stop(self):
        self.is_running = False
        self.thread.join()

    async def connect(self):
        async  with RTSPConnection(self.ip, self.port, self.username, self.password, logger=None) as conn:
            transport_class = transport_for_scheme('rtsp')
            async with transport_class(conn, logger=None, timeout=0) as transport:
                transport.subscribe(self.probe)
                async with RTSPMediaSession(conn, self.url, transport, logger=self.logger, media_type='application') as sess:
                    try:
                        print('starting stream...')
                        await sess.play()
                        print('stream started')
                        while conn.running and transport.running:
                            print('running...')
                            await asyncio.sleep(sess.session_keepalive)
                            await sess.keep_alive()
                    except asyncio.CancelledError:
                        print('stopping stream...')
                        #断线重连
            await sess.teardown()
                        
    def read(self):
        return time.time(), self.origin_queue.get()

    # 定义一个方法，用来将温度数据转换为frame
    def transform(self, frame):
        frame_original = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        frame_original = cv2.cvtColor(frame_original, cv2.COLOR_GRAY2BGR)
        frame_original = cv2.applyColorMap(frame_original, cv2.COLORMAP_JET)
        return frame_original
    
    # 定义一个方法用来获取温度大于某个值的坐标
    def get_point(self, frame, threshold):
        point_list = []
        for i in range(frame.shape[0]):
            for j in range(frame.shape[1]):
                if frame[i, j] > threshold:
                    point_list.append((j, i))
        return point_list

if __name__ == '__main__':
    # asyncio.run(main())
    # logger = logging.getLogger('rtsp')
    # logger.setLevel(logging.DEBUG)
    client = RTSP_Client('192.168.3.68', 554, 'admin', 'Asb11023', logger=None)
    while True:
        time_stamp, temp_data = client.read()
        print(time_stamp)
        frame = client.transform(temp_data)
        # print(client.get_point(temp_data, 10))
        cv2.imshow('frame', frame)
        cv2.waitKey(1)