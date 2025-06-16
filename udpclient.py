import socket           #用于网络通信
import struct           #用于数据包的打包和解包
import time             #用于计时和超时控制
import argparse         #用于解析命令行参数
import random           #用于生成随机数据和模拟网络环境
import pandas as pd     #用于数据分析和统计

BUFFER_SIZE = 1024 #单次接收数据的最大字节数
SYN = 1 #同步
SYN_ACK = 2 #同步确认
ACK = 3
DATA = 4
ACK_DATA = 5 #数据确认

#数据包格式
#（2 字节类型、4 字节序列号、4 字节确认号、2 字节长度）
ADDR_FORMAT = '>H II H' #大端字节序，包含两个无符号短整型和两个无符号整型
WINDOW_SIZE = 400  # 窗口大小（字节）
MIN_SIZE = 40  # 最小包大小
MAX_SIZE = 80  # 最大包大小
INIT_TIMEOUT = 0.3  # 初始超时时间（秒）
total_packets=30   #总传输包数

class UDPClient:
    def __init__(self, server_ip, server_port):
        self.server_addr = (server_ip, server_port) #服务器地址元组
        #创建套接字（使用Ipv4,UDP协议）
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq_base = 1  # 窗口基序号
        self.timeout = INIT_TIMEOUT
        self.sent = {}  # 已发送但未确认的包
        self.total_packets = total_packets  # 总共需要发送的包数量
        self.rtt_list = []  #记录rtt时间
        self.retransmit_count = 0  # 重传次数
        self.next_seq = 1  # 下一个要发送的序号
        self.byte_index = 0  # 当前字节索引
        self.timer_running = False  # 计时器状态
        self.acked_count = 0  # 已确认的包数量
        self.ack_counts = {}  # 记录每个ACK号的接收次数
        self.fast_retransmit_threshold = 3  # 触发快速重传的重复ACK阈值

    def connect(self):
        #发送syn包，初始序列号为1
        syn = struct.pack(ADDR_FORMAT, SYN, self.seq_base, 0, 0)
        #调用sendto() 操作系统会自动在 UDP 头部添加源端口和目的端口（根据显式指定目标地址（self.server_addr））
        self.sock.sendto(syn, self.server_addr)
        self.sock.settimeout(self.timeout)#设置套接字超时时间
        try:
            data, _ = self.sock.recvfrom(BUFFER_SIZE)  #接收数据包内容，忽略服务器地址
            #从二进制数据中解包协议头部
            type_, server_seq, ack, _ = struct.unpack(ADDR_FORMAT, data[:12])
            if type_ == SYN_ACK and ack == self.seq_base + 1:
                #发送ack包
                ack_ = struct.pack(ADDR_FORMAT, ACK, server_seq + 1, server_seq + 1, 0) #确认服务器的syn，期望服务器发送的下一个包
                self.sock.sendto(ack_, self.server_addr)
                self.next_seq = self.seq_base #从基序号开始发送
                print("[连接] 建立成功")
        except socket.timeout:  #超时抛出超时异常
            print("[连接] 超时，退出")
            exit()

    def send_window(self):
        if (self.next_seq - 1) >= self.total_packets:
            return  # 已经发送了足够数量的包

        usage = self.window_usage()  # 计算当前窗口已使用的字节数
        while (self.next_seq - 1) < self.total_packets and usage < WINDOW_SIZE:
            block_len = random.randint(MIN_SIZE, MAX_SIZE)
            #如果超出窗口大小
            if usage + block_len > WINDOW_SIZE:
                break
            #bytes()：将整数列表转换为字节对象，网络传输需要二进制字节数据
            payload = bytes([random.randint(0, 255) for _ in range(block_len)])
            seq = self.next_seq #当前序列号
            #ack号为0，不携带确认信息
            pkt = struct.pack(ADDR_FORMAT, DATA, seq, 0, block_len) + payload
            self.sock.sendto(pkt, self.server_addr)
            print(f"第{seq}个（第{self.byte_index}~{self.byte_index + block_len - 1}字节）client端已发送")
            #记录已发送但未确认的数据包信息
            self.sent[seq] = {
                'payload': payload,
                'time': time.time(),
                'start': self.byte_index,
                'end': self.byte_index + block_len - 1,
                'acked': False,
                'retries': 0 # 重传次数计数
            }
            #更新当前字节索引
            self.byte_index += block_len
            self.next_seq += 1
            usage += block_len
        #当窗口中有未确认的数据包且计时器未运行时，启动计时器监控首个未确认包的超时状态。
        if not self.timer_running and self.sent:
            self.start_timer()

    #启动计时器
    def start_timer(self):
        self.timer_start = time.time()
        self.timer_running = True

    #停止计时器
    def stop_timer(self):
        self.timer_running = False

    #检查是否超时，触发超时处理
    def check_timer(self):
        if self.timer_running and (time.time() - self.timer_start > self.timeout):
            self.handle_timeout()#超时处理
            return True
        return False

    #超时处理
    def handle_timeout(self):
        self.stop_timer()
        # 重传窗口内所有未确认的包
        for seq in sorted(self.sent):#对键进行升序排序
            info = self.sent[seq]
            if not info['acked']:#重传
                pkt = struct.pack(ADDR_FORMAT, DATA, seq, 0, len(info['payload'])) + info['payload']
                self.sock.sendto(pkt, self.server_addr)
                info['time'] = time.time()  # 更新发送时间
                info['retries'] += 1  # 增加重传次数
                self.retransmit_count += 1  # 总重传次数+1
                print(f"[重传] 第{seq}个（第{info['start']}~{info['end']}字节）数据包")

        # 如果仍有未确认的包，重启计时器
        if self.sent:
            self.start_timer()

    def receive_ack(self):
        try:
            self.sock.settimeout(0.05)  # 设置短超时，避免长时间阻塞
            data, _ = self.sock.recvfrom(BUFFER_SIZE)

            #数据包长度不符合
            if len(data) < 12:
                return

            type_, _, ack_seq, _ = struct.unpack(ADDR_FORMAT, data[:12])

            if type_ == ACK_DATA:
                if ack_seq == 0:
                    return
                # 记录ACK计数
                self.ack_counts[ack_seq] = self.ack_counts.get(ack_seq, 0) + 1

                # 检查是否触发快速重传（必须是重复ACK且达到阈值）
                if ack_seq < self.next_seq and self.ack_counts.get(ack_seq, 0) >= self.fast_retransmit_threshold:
                    print(f"[快速重传] 收到{self.ack_counts[ack_seq]}次ACK{ack_seq}，触发快速重传")
                    self.handle_fast_retransmit(ack_seq + 1)  # 重传下一个期望的分组
                    # 重置计数避免重复触发
                    self.ack_counts[ack_seq] = 0

                old_base = self.seq_base  # 记录旧的窗口基序号

                # 处理累积确认
                for seq in list(self.sent): #list获得字典的键
                    if seq <= ack_seq and not self.sent[seq]['acked']:
                        rtt = (time.time() - self.sent[seq]['time']) * 1000 #单位为毫秒
                        self.rtt_list.append(rtt)
                        self.sent[seq]['acked'] = True
                        self.acked_count += 1
                        print(
                            f"第{seq}个（第{self.sent[seq]['start']}~{self.sent[seq]['end']}字节）server端已收到，RTT是{rtt:.2f}ms")

                # 滑动窗口：移除所有已确认的数据包
                while self.seq_base in self.sent and self.sent[self.seq_base]['acked']:
                    del self.sent[self.seq_base]
                    self.seq_base += 1
                    # 窗口滑动后，清除旧ACK计数
                    self.ack_counts = {k: v for k, v in self.ack_counts.items() if k >= self.seq_base}

                # 如果窗口滑动了，调整计时器
                if old_base != self.seq_base:
                    self.stop_timer()
                    if self.sent:
                        self.start_timer()
        except socket.timeout:
            pass

    #处理快速重传逻辑
    def handle_fast_retransmit(self, seq_num):
        if seq_num in self.sent and not self.sent[seq_num]['acked']:
            info = self.sent[seq_num]
            pkt = struct.pack(ADDR_FORMAT, DATA, seq_num, 0, len(info['payload'])) + info['payload']
            self.sock.sendto(pkt, self.server_addr)
            info['time'] = time.time()  # 更新发送时间
            info['retries'] += 1  # 增加重传次数
            self.retransmit_count += 1  # 总重传次数+1
            print(f"[快速重传] 第{seq_num}个（第{info['start']}~{info['end']}字节）数据包")

    def window_usage(self):
        return sum(len(info['payload']) for info in self.sent.values() if not info['acked']) #遍历数据包信息，如果未被确认，就获取数据包长度相加

    def all_acked(self):
        # 已发送足够数量的包(非重传)且所有包都已确认
        return (self.next_seq - 1) >= self.total_packets and len(self.sent) == 0

    def start(self):
        self.connect()
        while not self.all_acked():
            self.send_window()  # 发送窗口内的数据
            self.receive_ack()  # 接收确认
            self.check_timer()  # 检查超时并重传

            # 动态调整超时时间
            if len(self.rtt_list) >= 10:
                self.timeout = 5 * (sum(self.rtt_list[-10:]) / 10) / 1000

        self.summary() #输出汇总信息

    def summary(self):
        df = pd.DataFrame(self.rtt_list, columns=["RTT"])  # 创建RTT数据框
        total_sent = self.acked_count + self.retransmit_count  # 总发送次数
        loss_rate = (self.total_packets / total_sent) * 100
        print("\n[汇总信息]")
        print(f"丢包率：{loss_rate:.2f}% ")
        print(f"最大RTT: {df['RTT'].max():.2f}ms")
        print(f"最小RTT: {df['RTT'].min():.2f}ms")
        print(f"平均RTT: {df['RTT'].mean():.2f}ms")
        print(f"RTT标准差: {df['RTT'].std():.2f}ms")


if __name__ == "__main__":
    #创建一个参数解析器对象，用于处理命令行输入
    parser = argparse.ArgumentParser()
    #添加位置参数
    parser.add_argument("server_ip", help="服务器IP地址")
    parser.add_argument("server_port", type=int, help="服务器端口")
    #解析命令行参数
    args = parser.parse_args()
    client = UDPClient(args.server_ip, args.server_port)
    client.start()
