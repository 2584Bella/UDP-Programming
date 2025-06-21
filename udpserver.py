import socket   #用于网络通信
import struct   #用于数据包的打包和解包
import random   #生成随机数，用于模拟丢包
from threading import Thread    #实现多线程并发
from datetime import datetime   #日期和时间处理

# 协议参数
#缓冲区大小
BUFFER_SIZE = 1024 #单次接收数据的最大字节数
#定义报文类型
SYN = 1 #同步
SYN_ACK = 2 #同步确认
ACK = 3
DATA = 4
ACK_DATA = 5 #带时间戳的确认包
#数据包格式
#（2 字节类型、4 字节序列号、4 字节确认号、2 字节长度）
ADDR_FORMAT = '>H II H' #大端字节序，包含两个无符号短整型和两个无符号整型
PORT = 8888


class UDPServer:
    def __init__(self):
        #创建套接字（使用Ipv4,UDP协议）
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #绑定到所有可用接口的 8888 端口
        self.sock.bind(('0.0.0.0', PORT))#监听所有可用网络接口的连接请求
        self.drop_rate = 0.3  # 丢包率
        self.connections = {} #维护客户端连接状态
        print(f"[启动] UDP服务器已启动，监听端口 {PORT}")

    #客户端请求处理
    def handle_client(self, data, addr):
        if len(data) < 12:
            print("[错误] 无效报文长度")
            return
        #解包
        type_, seq, ack, length = struct.unpack(ADDR_FORMAT, data[:12])

        if type_ == SYN:
            print(f"[SYN] 来自 {addr} 的连接请求")
            syn_ack = struct.pack(ADDR_FORMAT, SYN_ACK, 0, seq + 1, 0)#返回客户端确认号seq+1=2
            self.sock.sendto(syn_ack, addr)
            #记录客户端连接状态
            self.connections[addr] = {
                'status': 'connected',
                'expected_seq': 1, #初始期望序列号为 1
                'last_ack': 0
            }

        elif type_ == DATA:
            if addr not in self.connections:
                print(f"[警告] 未知客户端 {addr}")
                return

            # 模拟丢包
            if random.random() < self.drop_rate:
                print(f"[丢包模拟] 丢弃数据包 Seq={seq}")
                return

            # 获取当前时间
            server_time = datetime.now().strftime('%H:%M:%S') #格式化为字符串

            if seq == self.connections[addr]['expected_seq']: #如果收到的是期望的包
                print(f"[接收] {addr} 的数据包 Seq={seq} 长度={length}")
                ack_num = seq #当前确认号
                # 更新期望接收的序列号
                self.connections[addr]['expected_seq'] += 1
                self.connections[addr]['last_ack'] = seq
                #发送Ack
                ack_pkt = struct.pack(ADDR_FORMAT, ACK_DATA, 0, ack_num, 0) + server_time.encode() #字节序列号和长度为0
                self.sock.sendto(ack_pkt, addr)

            else:#如果收到的是乱序包
                print(f"收到乱序包: {seq}，期望:{self.connections[addr]['expected_seq']}，发送[ACK]:{self.connections[addr]['last_ack']}")
                #重复发送之前的ACK
                ack_num = self.connections[addr]['last_ack']
                ack_pkt = struct.pack(ADDR_FORMAT, ACK_DATA, 0, ack_num, 0) + server_time.encode()#将字符串转换为字节串（bytes对象）
                self.sock.sendto(ack_pkt, addr)

        elif type_ == ACK:
            print(f"[ACK] 来自 {addr} 的连接完成确认")

    def start(self):
        while True:
            try:
                #主线程持续接收数据包
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                #为每个客户端请求创建新线程处理
                Thread(target=self.handle_client, args=(data, addr)).start()#（目标函数，传递给目标函数的参数）
            except Exception as e:
                print(f"[错误] {e}")


if __name__ == '__main__':
    UDPServer().start()#启动服务器端
