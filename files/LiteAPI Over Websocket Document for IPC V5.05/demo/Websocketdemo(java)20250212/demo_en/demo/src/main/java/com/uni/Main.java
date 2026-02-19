package com.uni;

import com.uni.Websocketserver.Websocket;

public class Main {
    public static void main(String[] args) {

        String ip = "172.20.177.12";
        int port = 8080;
        try {
            new Websocket().run(ip,port);
        } catch (Exception e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
            System.out.println("WebSocket server startup failed, please check if the port is occupied");
        }
    }

}
