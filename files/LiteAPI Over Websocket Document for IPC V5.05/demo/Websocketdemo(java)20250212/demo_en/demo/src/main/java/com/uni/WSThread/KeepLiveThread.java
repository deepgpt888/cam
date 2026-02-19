package com.uni.WSThread;

import io.netty.channel.Channel;
import io.netty.handler.codec.http.websocketx.TextWebSocketFrame;

import com.alibaba.fastjson.JSON;

import com.alibaba.fastjson.JSONObject;
import com.uni.WSBean.KeepAliveRspAO;
import com.uni.WSBean.WebsocketReq;
import com.uni.WSBean.WebsocketRsp;

public class KeepLiveThread  implements Runnable{


    private Channel channel;
    private JSONObject jsonObject;
    private static int lives = 60;

    public static int getLives() {
        return lives;
    }
    public KeepLiveThread(Channel channel, JSONObject jsonObject) {
        this.channel = channel;
        this.jsonObject = jsonObject;
    }

    @Override
    public void run() {
        requestReceive(channel, jsonObject);
    }

    private void requestReceive(Channel channel, JSONObject jsonObject) {
        String currentIP = channel.remoteAddress().toString();
        WebsocketReq websocketReq = JSON.toJavaObject(jsonObject, WebsocketReq.class);
        WebsocketRsp websocketRsp = new WebsocketRsp();
        websocketRsp.setCseq(websocketReq.getCseq());
        websocketRsp.setResponseURL(websocketReq.getRequestURL());
        KeepAliveRspAO keepAliveRspAO = new KeepAliveRspAO();
        //设置保活时间
        keepAliveRspAO.setTimeout(lives);
        keepAliveRspAO.setTimestamp(System.currentTimeMillis() / 1000L);
        websocketRsp.setData(keepAliveRspAO);
        String msg = JSON.toJSONString(websocketRsp);
        System.out.println("Server response to keep alive" + currentIP + ":" + msg);
        channel.writeAndFlush(new TextWebSocketFrame(msg));
    }
}
