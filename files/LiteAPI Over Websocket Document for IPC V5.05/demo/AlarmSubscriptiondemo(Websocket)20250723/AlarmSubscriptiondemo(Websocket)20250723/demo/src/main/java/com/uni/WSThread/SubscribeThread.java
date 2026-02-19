package com.uni.WSThread;

import java.net.InetSocketAddress;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.uni.Main;
import com.uni.Utils.Log;
import com.uni.WSBean.WebsocketReq;
import com.uni.WSBean.WebsocketRsp;
import com.uni.WSThread.MessageReceivingThread;
import com.uni.Websocketserver.WSOperator;

import io.netty.channel.Channel;
import io.netty.handler.codec.http.websocketx.TextWebSocketFrame;

public class SubscribeThread extends Thread {
    private boolean isStop = false; // Set flag. When isStop is false, start refreshing subscription; when isStop is true, stop refreshing subscription
    private int subscribeId = 0;
    private WSOperator wsOperator;
    private JSONObject jsonObject;

    public SubscribeThread(WSOperator wsOperator) {
        this.wsOperator = wsOperator;
    }

    @Override
    public void run() {
        // Execute data subscription
        this.subscribeId = subscribe(
                Main.subscriptionDuration,
                Main.receiveAlarmEventType);
        if (this.subscribeId == -1) {
            Log.info("Subscription failed");
            return;
        }

        // Keep-alive subscription timer
        int keepaliveTime = 0;
        // Keep-alive success count
        int keepaliveCount = 0;

        /* Execute subscription refresh */
        while (isStop == false) {
            try {
                Thread.sleep(1000);
                if (isStop) {
                    return;
                }
                // Refresh keep-alive subscription timer
                keepaliveTime++;

                if (keepaliveTime >= Main.subscriptionDuration - 10) {
                    boolean res = refreshSubscription(this.subscribeId, Main.subscriptionDuration);
                    keepaliveCount++;
                    Log.info("Keep-alive refresh count: %s", keepaliveCount);
                    if (res) {
                        keepaliveTime = 0;
                        continue;
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * Data subscription
     */
    private int subscribe(int duration,  int eventType) {
        // Fill in the request body for "data subscription"
        String requestBody = "{" +
                "\"Duration\": " + duration + "," +
                "\"Type\": " + eventType  +
                "}";

        // Send data subscription request
        try {
            Log.info("Processing data subscription");
            WebsocketRsp websocketRsp = this.wsOperator.sendLapiRequest(Main.subscribeURL, "POST", requestBody);
            // Log.info("Server request to: " + currentIP + " for \"data subscription\":\n", msg);
            // channel.writeAndFlush(new TextWebSocketFrame(msg));
            if (websocketRsp == null || websocketRsp.getResponseCode() != 0) {
                Log.info("Data subscription failed");
                return -1;
            }
            String returnData = JSON.toJSONString(websocketRsp);
            JSONObject data = (JSONObject) websocketRsp.getData();
            System.out.println("Received response: " + returnData);
            System.out.println("Data subscription successful");
            String AlarmReturnData = "Method: POST" + "\n" + "URL: "+ Main.subscribeURL + "\n" + "Response data: " + returnData;
            MessageReceivingThread.downloadFile(Main.alarmDataDownloadPath, AlarmReturnData); // Download data to local
            return data.getInteger("ID");
        } catch (Exception e) {
            // TODO: handle exception
            e.printStackTrace();
        }
        return -1;
    }

    /**
     * Refresh subscription
     */
    private boolean refreshSubscription(int subscribeId, int duration) {
        Log.info("Refreshing keep-alive, subscription ID: %d", subscribeId);
        // Fill in the request body for "refresh subscription"
        String requestBody = "{\"Duration\": " + duration + "}";
        // Send refresh subscription request
        WebsocketRsp websocketRsp = this.wsOperator.sendLapiRequest(Main.subscribeURL + "/" + subscribeId, "PUT", requestBody);

        if (websocketRsp != null && websocketRsp.getResponseCode() == 0) {
            String returnData = JSON.toJSONString(websocketRsp);
            System.out.println("Received response: " + returnData);
            System.out.println("Refresh subscription successful");
            String AlarmReturnData = "Method: PUT" + "\n" + "URL: "+ Main.subscribeURL + "/" + subscribeId + "\n" + "Response data: " + returnData;
            MessageReceivingThread.downloadFile(Main.alarmDataDownloadPath, AlarmReturnData); // Download data to local
            return true;
        } else {
            Log.info("Refresh subscription failed");
            return false;
        }
    }

    /**
     * Cancel subscription
     */
    private boolean cancelSubscription(int subscribeId) {
        Log.info("Cancelling subscription, subscription ID: %d", subscribeId);
        // Send unsubscription request
        WebsocketRsp websocketRsp = 
            this.wsOperator.sendLapiRequest(Main.subscribeURL + "/" + subscribeId, "DELETE", null);

        if (websocketRsp != null && websocketRsp.getResponseCode() == 0) {
            String returnData = JSON.toJSONString(websocketRsp);
            System.out.println("Received response: " + returnData);
            System.out.println("Unsubscription successful");
            String AlarmReturnData = "Method: DELETE" + "\n" + "URL: "+ Main.subscribeURL + "/" + subscribeId + "\n" + "Response data: " + returnData;
            MessageReceivingThread.downloadFile(Main.alarmDataDownloadPath, AlarmReturnData); // Download data to local
            return true;
        } else {
            Log.info("Unsubscription failed");
            return false;
        }
    }

    /**
     * Stop refreshing subscription + Cancel subscription
     */
    public void stopRefreshAndCancelSubscription() {
        if (this.isStop) {
            return;
        }

        this.isStop = true; // Flag to stop refreshing subscription when isStop is true
        // Cancel subscription
        cancelSubscription(this.subscribeId);
    }

}
