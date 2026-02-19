package com.uni.Websocketserver;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.text.DecimalFormat;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadPoolExecutor;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.uni.Main;
import com.uni.WSBean.WebsocketReq;
import com.uni.WSBean.WebsocketRsp;
import com.uni.WSThread.KeepLiveThread;
import com.uni.WSThread.MessageReceivingThread;

import org.apache.commons.codec.binary.Base64;
import org.apache.commons.codec.binary.StringUtils;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.Channel;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelFutureListener;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInboundHandlerAdapter;
import io.netty.channel.group.ChannelGroup;
import io.netty.channel.group.DefaultChannelGroup;
import io.netty.handler.codec.http.DefaultFullHttpResponse;
import io.netty.handler.codec.http.FullHttpRequest;
import io.netty.handler.codec.http.FullHttpResponse;
import io.netty.handler.codec.http.HttpHeaderNames;
import io.netty.handler.codec.http.HttpResponseStatus;
import io.netty.handler.codec.http.HttpUtil;
import io.netty.handler.codec.http.HttpVersion;
import io.netty.handler.codec.http.QueryStringDecoder;
import io.netty.handler.codec.http.websocketx.CloseWebSocketFrame;
import io.netty.handler.codec.http.websocketx.PingWebSocketFrame;
import io.netty.handler.codec.http.websocketx.PongWebSocketFrame;
import io.netty.handler.codec.http.websocketx.TextWebSocketFrame;
import io.netty.handler.codec.http.websocketx.WebSocketClientProtocolHandler;
import io.netty.handler.codec.http.websocketx.WebSocketFrame;
import io.netty.handler.codec.http.websocketx.WebSocketServerHandshaker;
import io.netty.handler.codec.http.websocketx.WebSocketServerHandshakerFactory;
import io.netty.handler.codec.http.websocketx.WebSocketServerProtocolHandler;
import io.netty.handler.ssl.SslHandshakeCompletionEvent;
import io.netty.util.CharsetUtil;
import io.netty.util.concurrent.GlobalEventExecutor;

public class WebSocketHandler extends ChannelInboundHandlerAdapter {

    // Handler class for WebSocket handshake
    private WebSocketServerHandshaker handshaker;

    public static interface WSEventCallback {
        void onSuccessConnect(WSOperator wsOperator);
    }

    public WebSocketHandler(WSEventCallback callback) {
        this.wsEventcallback = callback;
    }

    private WSEventCallback wsEventcallback;
    // Used to handle subsequent LAPI requests and responses
    private WSOperator wsOperator;

    // Authentication key (must match device settings)
    private static String SECRET = Main.secret;

    // Registration interface
    private static String LAPI_REGISTER = "/LAPI/V1.0/System/UpServer/Register";
    // Keep-alive interface
    private static String LAPI_KEEPALIVE = "/LAPI/V1.0/System/UpServer/Keepalive";
    // Close connection
    private static String LAPI_UNREGISTER = "/LAPI/V1.0/System/UpServer/Unregister";

    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg)
            throws Exception {
        if (msg instanceof FullHttpRequest) {
            // WebSocket connection request
            handleHttpRequest(ctx, (FullHttpRequest) msg);
        } else if (msg instanceof WebSocketFrame) {
            // WebSocket business processing
            handleWebSocketRequest(ctx, (WebSocketFrame) msg);
        }
    }

    /**
     * When the client connects to the server (open connection)
     * Get the client's channel and manage it in ChannelGroup
     */
    @Override
    public void handlerAdded(ChannelHandlerContext ctx) throws Exception {
        System.out.println(ctx.channel().remoteAddress() + "Device connected, IP address:" + ctx.channel().remoteAddress().toString());
    }

    @Override
    public void handlerRemoved(ChannelHandlerContext ctx) throws Exception {
        String channelIP = ctx.channel().remoteAddress().toString();
        System.out.println(ctx.channel().remoteAddress() + "Device removed, IP address:" + channelIP);
    }

    @Override
    public void channelActive(ChannelHandlerContext ctx) throws Exception {
        // Add connection
        System.out.println("Client connected:" + ctx.channel().remoteAddress() + "\n");
    }

    @Override
    public void channelInactive(ChannelHandlerContext ctx) throws Exception {
        System.out.println("Client disconnected:" + ctx.channel().remoteAddress() + "\n");
    }

    @Override
    public void channelReadComplete(ChannelHandlerContext ctx) throws Exception {
        ctx.flush();
    }

    /**
     * Get WebSocket service information
     *
     * @param req
     * @return
     */
    private static String getWebSocketLocation(FullHttpRequest req) {
        String location = req.headers().get("Host") + "/ws";
        return "ws://" + location;
    }

    // Connection exception
    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause)
            throws Exception {
        System.out.println("Exception occurred:" + cause.getMessage() + "\n");
        ctx.channel().close();
    }

    /**
     * Receive handshake request and respond
     * The only HTTP request to create WebSocket
     *
     * @param ctx
     * @param req
     */
    private void handleHttpRequest(ChannelHandlerContext ctx, FullHttpRequest req) throws Exception {
        InetSocketAddress addr = (InetSocketAddress) ctx.channel().remoteAddress();
        String currentIP = addr.getAddress().getHostAddress();
        String uri = req.uri();
        // Device requests connection
        System.out.println(currentIP + "Received handshake request, URL=" + uri);
        JSONObject object = new JSONObject();

        // HTTP decoding failed, specify Upgrade: websocket protocol to the server
        if (!req.decoderResult().isSuccess() || (!"websocket".equals(req.headers().get("Upgrade")))) {
            sendHttpResponse(ctx, req,
                    new DefaultFullHttpResponse(HttpVersion.HTTP_1_1, HttpResponseStatus.BAD_REQUEST));
            System.out.println("Not a connection establishment request");
            return;
        } else if (LAPI_REGISTER.equals(uri)) {
            object.put("Nonce", getCnonce());
            FullHttpResponse fullHttpResponse = new DefaultFullHttpResponse(HttpVersion.HTTP_1_1,
                    HttpResponseStatus.UNAUTHORIZED,
                    Unpooled.copiedBuffer(JSONObject.toJSONString(object), CharsetUtil.UTF_8));
            fullHttpResponse.headers().set(HttpHeaderNames.CONTENT_TYPE, "application/json; charset=UTF-8");
            sendHttpResponse(ctx, req, fullHttpResponse);
            return;
        } else if (uri.contains(LAPI_REGISTER + "?Vendor")) {
            System.out.println(currentIP + "Device initiated second registration");
            // Get request parameters
            QueryStringDecoder decoder = new QueryStringDecoder(req.uri());
            Map<String, List<String>> parameters = decoder.parameters();
            String Vendor = parameters.get("Vendor").get(0);
            String DeviceType = parameters.get("DeviceType").get(0);
            String Devicecode = parameters.get("DeviceCode").get(0);
            String Algorithm = parameters.get("Algorithm").get(0);
            String Nonce = parameters.get("Nonce").get(0);
            String Cnonce = parameters.containsKey("Cnonce") ? parameters.get("Cnonce").get(0) : "";
            String Sign = parameters.get("Sign").get(0);
            String decodedUrl = URLDecoder.decode(Sign, StandardCharsets.UTF_8.toString());
            decodedUrl = decodedUrl.replace(" ", "+");
            System.out.println("Authentication signature:" + decodedUrl);
            String pstr = Vendor + "/" + DeviceType + "/" + Devicecode + "/" + Algorithm + "/" + Nonce;
            // Generate server-side signature
            Mac sha256_HMAC = Mac.getInstance("HmacSHA256");
            SecretKeySpec secretKey = new SecretKeySpec(SECRET.getBytes("utf-8"), "HmacSHA256");
            sha256_HMAC.init(secretKey);
            byte[] hash = sha256_HMAC.doFinal(pstr.getBytes("utf-8"));
            String encodeStr = Base64.encodeBase64String(hash);
            if (!encodeStr.equals(decodedUrl)) {
                System.out.println("Authentication failed:" + encodeStr);
                object.put("Nonce", getCnonce());
                FullHttpResponse fullHttpResponse = new DefaultFullHttpResponse(HttpVersion.HTTP_1_1,
                        HttpResponseStatus.UNAUTHORIZED,
                        Unpooled.copiedBuffer(JSONObject.toJSONString(object), CharsetUtil.UTF_8));
                fullHttpResponse.headers().set(HttpHeaderNames.CONTENT_TYPE, "application/json; charset=UTF-8");
                sendHttpResponse(ctx, req, fullHttpResponse);
                return;
            } else {
                System.out.println("Authentication successful");
                object.put("Cnonce", Cnonce);
                object.put("Resign", encodeStr);
            }
        }

        // Handshake response processing, create WebSocket handshake factory class for local testing
        WebSocketServerHandshakerFactory wsFactory = new WebSocketServerHandshakerFactory(getWebSocketLocation(req),
                null, false, 65535 * 100);
        // Create handshake class based on factory class and HTTP request
        handshaker = wsFactory.newHandshaker(req);
        if (handshaker == null) {
            // WebSocket not supported
            WebSocketServerHandshakerFactory.sendUnsupportedVersionResponse(ctx.channel());
        } else {
            // Construct handshake response message and return it to the client
            ChannelFuture future = handshaker.handshake(ctx.channel(), req);
            if (future.isSuccess()) {
                ctx.channel().writeAndFlush(new TextWebSocketFrame(JSONObject.toJSONString(object)));
            }

            WSOperator wsOperator = new WSOperator(ctx);
            this.wsOperator = wsOperator;
            // Create and start thread
            new Thread(new Runnable() {
                @Override
                public void run() {
                    wsEventcallback.onSuccessConnect(wsOperator);
                }
            }).start();
        }
    }

    /**
     * Receive WebSocket request
     *
     * @param ctx
     * @param req
     * @throws Exception
     */
    private void handleWebSocketRequest(ChannelHandlerContext ctx, WebSocketFrame req) throws Exception {
        String currentIP = ctx.channel().remoteAddress().toString();
        // Receive websocket request, format conversion
        JSONObject jsonObject = JSONObject.parseObject(((TextWebSocketFrame) req).text());
        WebsocketReq websocketReq = JSON.toJavaObject(jsonObject, WebsocketReq.class);

        // Check if it's a close connection command
        if (req instanceof CloseWebSocketFrame) {
            // Close websocket connection
            handshaker.close(ctx.channel(), (CloseWebSocketFrame) req.retain());
            System.out.println(ctx.channel().remoteAddress() + "Disconnected");
            return;
        }
        // Check if it's a Ping message
        if (req instanceof PingWebSocketFrame) {
            ctx.channel().write(new PongWebSocketFrame(req.content().retain()));
            return;
        }
        // This example supports text messages, binary messages are not supported
        if (!(req instanceof TextWebSocketFrame)) {
            throw new UnsupportedOperationException("Only text messages are supported, binary messages are not supported");
        }
        if (ctx == null || this.handshaker == null || ctx.isRemoved()) {
            throw new Exception("Handshake not completed, cannot send WebSocket messages to the device");
        }

        if (LAPI_KEEPALIVE.equals(websocketReq.getRequestURL())) {
            System.out.println("Server received keep-alive request from device:" + websocketReq.getRequestURL());
            // Use thread to receive keep-alive information
            KeepLiveThread keepLiveThread = new KeepLiveThread(ctx.channel(), jsonObject);
            KeepLiveThreadPoolExecutor.EXECUTOR_SERVICE.execute(keepLiveThread);
        } else if (LAPI_UNREGISTER.equals(websocketReq.getRequestURL())) {
            System.out.println(currentIP + "Device disconnected");
        } else {
            if (jsonObject.get("ResponseURL") != null) {
                try {
                    WebsocketRsp websocketRsp = JSON.toJavaObject(jsonObject, WebsocketRsp.class);
                    this.wsOperator.OnReceiveResponse(websocketRsp);
                } catch (Exception e) {
                    e.printStackTrace();
                }
                // this.wsOperator.OnReceiveRequest(websocketReq);
            } else {
                MessageReceivingThread messageReceivingThread = new MessageReceivingThread(ctx.channel(), jsonObject);
                KeepLiveThreadPoolExecutor.EXECUTOR_SERVICE.execute(messageReceivingThread);
            }

        }
    }

    private void sendHttpResponse(ChannelHandlerContext ctx, FullHttpRequest req, FullHttpResponse res) {
        // BAD_REQUEST(400) Response message returned for client request error
        if (res.status().code() != 200) {
            // Put the returned status code into the cache, Unpooled does not use a cache pool
            ByteBuf buf = Unpooled.copiedBuffer(res.status().toString(), CharsetUtil.UTF_8);
            res.content().writeBytes(buf);
            buf.release();
            HttpUtil.setContentLength(res, res.content().readableBytes());
        }
        // Send response message
        ChannelFuture cf = ctx.channel().writeAndFlush(res);
        // Illegal connection directly closes the connection
        if (!HttpUtil.isKeepAlive(req) || res.status().code() != 200) {
            cf.addListener(ChannelFutureListener.CLOSE);
        }
    }

    // Calculate cnonce value, cnonce is used for authentication
    public static String getCnonce() {
        double d = Math.random();
        double d1 = new Date().getTime() / 1000;
        double x = d * d1;
        DecimalFormat df = new DecimalFormat("#");// Round to the nearest integer
        return df.format(x);
    }
}
