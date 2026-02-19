package com.uni.Websocketserver;

import java.util.HashMap;
import java.util.concurrent.CompletableFuture;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.uni.WSBean.WebsocketReq;
import com.uni.WSBean.WebsocketRsp;

import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.codec.http.websocketx.TextWebSocketFrame;

public class WSOperator {
    public Long cseq = 1L;
    ChannelHandlerContext wsContext;

    HashMap<String, CompletableFuture<WebsocketRsp>> responseFutureMap = new HashMap<>();

    public WSOperator(ChannelHandlerContext wsContext) {
        this.wsContext = wsContext;
    }

    public WebsocketRsp sendLapiRequest(String url, String method, String data) {
        JSONObject jsonObject = JSONObject.parseObject(data);
        return this.sendLapiRequest(url, method, jsonObject);
    }

    public WebsocketRsp sendLapiRequest(String url, String method, Object data) {
        if (wsContext.isRemoved()) {
            System.out.println("Channel has been disconnected");
            return null;
        }
        CompletableFuture<WebsocketRsp> future = new CompletableFuture<>();
        responseFutureMap.put(cseq.toString(), future);

        WebsocketReq websocketReq = new WebsocketReq();
        websocketReq.setRequestURL(url);
        websocketReq.setMethod(method);
        websocketReq.setCseq(cseq);
        websocketReq.setData(data);
        
        String msg = JSON.toJSONString(websocketReq);
        System.out.println("Sending request: " + msg);
        this.wsContext.channel().writeAndFlush(new TextWebSocketFrame(msg).retain());

        cseq++;

        // Timeout if no response after 5 seconds
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    Thread.sleep(10000L);
                    if(!future.isDone()) {
                        System.out.println("Request timeout");
                        future.complete(null);
                    }
                } catch (InterruptedException e) {
                    // TODO Auto-generated catch block
                    e.printStackTrace();
                }
            }
        }).start();

        try {
            WebsocketRsp response = future.get();
            // System.out.println("Received response: " + response.getData().toString()); // Output: Hello, CompletableFuture!
            return response;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public void OnReceiveRequest(WebsocketReq request) {

    }

    public void OnReceiveResponse(WebsocketRsp response) {
        Long cseq = response.getCseq();
        if ( responseFutureMap.containsKey(cseq.toString()) ) {
            CompletableFuture<WebsocketRsp> future = responseFutureMap.get(cseq.toString());
            future.complete(response);
            responseFutureMap.remove(cseq.toString());
        }
        else {
            System.out.println("Received response, cseq: " + cseq + " but not found in responseFutureMap");
            System.out.println(response.toString());
        }
    }

}
