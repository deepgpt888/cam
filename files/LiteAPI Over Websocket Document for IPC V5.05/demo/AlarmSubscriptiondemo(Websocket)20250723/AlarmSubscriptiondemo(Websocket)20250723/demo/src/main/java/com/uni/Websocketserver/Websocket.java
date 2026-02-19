package com.uni.Websocketserver;

import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.Channel;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.http.HttpObjectAggregator;
import io.netty.handler.codec.http.HttpServerCodec;
import io.netty.handler.stream.ChunkedWriteHandler;

public class Websocket {

    public void run(String ip,int port, WebSocketHandler.WSEventCallback wsEventcallback) {
        
        System.out.println("Starting WebSocket server...");
        //Main thread group
        EventLoopGroup bossGroup = new NioEventLoopGroup();
        //Worker thread group
        EventLoopGroup workerGroup = new NioEventLoopGroup();
        try {
            // Server startup helper class for setting TCP-related parameters
            ServerBootstrap b = new ServerBootstrap();
            // Set as master-slave thread model
            b.group(bossGroup, workerGroup)
                    //Set server NIO communication model
                    .channel(NioServerSocketChannel.class)
                    // b can also set TCP parameters, configuring main and worker thread pools separately as needed to optimize server performance.
                    // The main thread pool uses the option method for configuration, while the worker thread pool uses the childOption method.
                    // backlog represents the maximum number of connections queued in the main thread pool, including incomplete (three-way handshake) and established connections
                    .option(ChannelOption.SO_BACKLOG, 5)
                    .childOption(ChannelOption.SO_KEEPALIVE, true)//Activate heartbeat mechanism after 2 hours of inactivity
                    //Set up ChannelPipeline, a chain of business handlers, processed by the worker thread pool
                    .childHandler(new ChannelInitializer<SocketChannel>() {
                        // Add handlers, typically including message encoding/decoding, business logic, logging, authentication, filtering, etc.
                        @Override
                        public void initChannel(SocketChannel ch) throws Exception {
                            ch.pipeline().addLast("http-codec",new HttpServerCodec());//Set up a decoder to encode or decode request and response messages into HTTP messages.
                            ch.pipeline().addLast("aggregator",new HttpObjectAggregator(65535));//Set the maximum size for a single request, aggregating multiple messages into a single HTTP request or response
                            ch.pipeline().addLast("http-chunked",new ChunkedWriteHandler());//Used for chunked data transfer, sending HTML5 files to clients to support WebSocket communication between browsers and servers
                            //ch.pipeline().addLast("adapter",new FunWebSocketServerHandler());  //Pre-interceptor
                            ch.pipeline().addLast("handler",new WebSocketHandler(wsEventcallback));//Custom business handler
                        }
                    });
            Channel channel = null;
            try {
                // Bind port, start select thread to poll channel events, and delegate events to the worker thread pool
                channel = b.bind(ip,port).sync().channel();
                System.out.println("WebSocket server started successfully:" + channel + "\n");
            } catch (Exception e) {
                e.printStackTrace();
                System.out.println("WebSocket server failed to start, port is occupied or already in use, please check IP and port settings\n");
            }
            try {
                channel.closeFuture().sync();
            } catch (InterruptedException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            } 
        } finally {
            // Exit and release thread pool resources
            workerGroup.shutdownGracefully();
            bossGroup.shutdownGracefully();
            System.out.println("Websocket Server closed.");
        }
    }
    
}
