package com.uni;

import com.uni.WSThread.SubscribeThread;
import com.uni.Websocketserver.WebSocketHandler.WSEventCallback;
import com.uni.Websocketserver.Websocket;

public class Main {

    /**
     * Authentication key (consistent with the device settings)
     */
    public static String secret = "123456";
    /**
     * Fill in the URL for data subscription /LAPI/V1.0/System/Event/Subscription
     */
    public static final String subscribeURL = "/LAPI/V1.0/System/Event/Subscription";
    /**
     * Specify the file path to save the received alarm data
     */
    public static String alarmDataDownloadPath = "returnData";

    /**
     * Destination IPv4 address for data transmission
     */
    public static String ip = "172.20.177.10";
    /**
     * Destination port for data transmission, range [1, 65535]
     */
    public static int port = 50235;
    /**
     * Subscription duration
     */
    public static int subscriptionDuration = 60;

    /**
     * Subscription event type
     * For NVR, fill in 0 or leave blank for full subscription; for IPC, fill in 65535 or leave blank for full subscription
     */
    public static int receiveAlarmEventType = 0;


    public static SubscribeThread subscribeThread = null;
    public static void main(String[] args) {

        // This demo only supports single-device connection
        
        // Callback for successful WebSocket connection establishment
        WSEventCallback successConnectCallback = (wsOperator) -> {
            try {
                Thread.sleep(2000);
                // Start subscription
                subscribeThread = new SubscribeThread(wsOperator);
                subscribeThread.start();
                
                // Cancel subscription
                // subscribeThread.stopRefreshAndCancelSubscription();
            } catch (InterruptedException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }
        };

        try {
            new Websocket().run(ip, port, successConnectCallback);
        } catch (Exception e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
            System.out.println("WebSocket server failed to start, please check if the port is occupied");
        }
    }

}
