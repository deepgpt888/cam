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

    public void run(String ip, int port) {

        System.out.println("Starting websocket server...");
        // Main thread group
        EventLoopGroup bossGroup = new NioEventLoopGroup();
        // Work Thread Group
        EventLoopGroup workerGroup = new NioEventLoopGroup();
        try {
            // Server startup auxiliary class, used to set TCP related parameters
            ServerBootstrap b = new ServerBootstrap();
            // Set as primary and secondary thread model
            b.group(bossGroup, workerGroup)
                    // Set up the server-side NIO communication model
                    .channel(NioServerSocketChannel.class)
                    .option(ChannelOption.SO_BACKLOG, 5)
                    .childOption(ChannelOption.SO_KEEPALIVE, true)// 2-hour no data activation of heartbeat mechanism
                    // Set up a ChannelPipeline, which is a business responsibility chain composed
                    // of handlers that are concatenated and processed by the thread pool
                    .childHandler(new ChannelInitializer<SocketChannel>() {
                        // Add handlers for processing, usually including message encoding and decoding,
                        // business processing, as well as logs, permissions, filtering, etc
                        @Override
                        public void initChannel(SocketChannel ch) throws Exception {
                            ch.pipeline().addLast("http-codec", new HttpServerCodec());// Set up a decoder to encode or decode request and response messages into HTTP messages.
                            ch.pipeline().addLast("aggregator", new HttpObjectAggregator(65535));// Set the file size for a single request to convert multiple messages into a single HTTP request or response
                            ch.pipeline().addLast("http-chunked", new ChunkedWriteHandler());// Used for partitioned transmission of big data, sending HTML5 files to clients to support WebSocket communication between browsers and servers
                            // ch.pipeline().addLast("adapter",new FunWebSocketServerHandler()); //Pre interceptor
                            ch.pipeline().addLast("handler", new WebSocketHandler());// Custom business handler
                        }
                    });
            Channel channel = null;
            try {
                // Bind the port, start the select thread, poll and listen for channel events, and once an event is detected, it will be handed over to the thread pool for processing
                channel = b.bind(ip, port).sync().channel();
                System.out.println("WebSocket server started successfully:" + channel + "\n");
            } catch (Exception e) {
                e.printStackTrace();
                System.out.println("The webSocket server failed to start, the port is occupied or a service is already running on that port. Please check the IP port settings\n");
            }
            try {
                channel.closeFuture().sync();
            } catch (InterruptedException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }
        } finally {
            // Exit, release thread pool resources
            workerGroup.shutdownGracefully();
            bossGroup.shutdownGracefully();
            System.out.println("Websocket Server closed.");
        }
    }

}
