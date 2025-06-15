UDP 可靠传输模拟程序

一、运行环境
1. 服务器端（主机）
操作系统：Windows
依赖环境：
python3 >= 3.6 # Python 3.6 及以上版本
2. 客户端（主机）
操作系统：Windows
依赖环境：与服务器端一致。

二、参数配置

1. 服务器端参数（代码内配置）
#python
# udpserver.py 关键配置
PORT=8888
self.sock.bind(('0.0.0.0', PORT))  # 监听所有IP的8888端口（可修改端口）

2. 客户端参数（命令行传入）
#python
python udpclient.py <server_ip> <server_port>

必选参数：
<server_ip>：主机 回环IP 地址（127.0.0.1）。
<server_port>：服务器端口（ 8888，需与服务器代码一致）。

三、启动命令

1. 服务器端
#python
# 启动服务器
python udpserver.py

预期输出：
启动 UDP服务器已启动，监听端口 8888
SYN 来自 ('127.0.0.1', 58511) 的连接请求
ACK 来自 ('127.0.0.1', 58511) 的连接完成确认
接收 ('127.0.0.1', 58511) 的数据包 Seq=1 长度=56
...

2. 客户端
#python
python udpclient.py 127.0.0.1 8888

预期输出：
连接 建立成功
第1个（第0-55字节）client端已发送
第1个（第0-55字节）server端已收到，RTT是2.56ms
第2个（第56-99字节）client端已发送
...

四、程序功能说明

1. 核心特性
基于 UDP 协议模拟 TCP 的可靠传输机制。
实现了三次握手连接建立（SYN, SYN-ACK, ACK）。
支持序列号、确认号、滑动窗口机制。
实现超时重传和快速重传（重复 ACK 触发）。
统计 RTT 时间、丢包率等网络性能指标。
2. 数据包格式
2字节类型 + 4字节序列号 + 4字节确认号 + 2字节长度 （+ 数据负载）

TYPE=1: SYN（同步请求）
TYPE=2: SYN_ACK（同步确认）
TYPE=3: ACK（确认）
TYPE=4: DATA（数据）
TYPE=5: ACK_DATA（带时间戳的数据确认）

五、输出说明

1. 客户端关键输出
 建立成功
第X个（第Y-Z字节）client端已发送
第X个（第Y-Z字节）server端已收到，RTT是XX.XXms
重传 第X个（第Y-Z字节）数据包
快速重传 收到X次ACKX，触发快速重传
快速重传 第X个（第Y-Z字节）数据包
2. 服务器端关键输出
SYN 来自 (IP, PORT) 的连接请求
接收 (IP, PORT) 的数据包 Seq=X 长度=Y
收到乱序包: X，期望: Y，发送ACK: Z
丢包模拟 丢弃数据包 Seq=X

六、性能指标汇总

程序运行结束后，客户端会输出详细的性能统计：
汇总信息
丢包率：X.XX% 
最大RTT: XX.XXms
最小RTT: XX.XXms
平均RTT: XX.XXms
RTT标准差: XX.XXms

（PS：此程序的服务器端亦可在虚拟机Linux系统上实现，只需确保Linux上有相应的python配置，并打开相对于UDP的8888端口的防火墙，保证主机与虚拟机可以ping通，即可实现通信。）
