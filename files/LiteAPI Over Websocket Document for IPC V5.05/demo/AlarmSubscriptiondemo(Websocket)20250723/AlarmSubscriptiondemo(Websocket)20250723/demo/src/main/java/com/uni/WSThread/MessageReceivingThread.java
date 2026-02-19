package com.uni.WSThread;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.text.SimpleDateFormat;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.uni.Main;
import com.uni.WSBean.WebsocketReq;
import com.uni.WSBean.WebsocketRsp;

import io.netty.channel.Channel;

public class MessageReceivingThread implements Runnable {
    private static Long LAPI_Cseq = 1444l;
    // LAPI event notification base path
    private static final String LAPI_BASE_PATH = "/LAPI/V1.0/System/Event/Notification/";

    private Channel channel;
    private JSONObject jsonObject;
    private static String currentFolderPath;

    public MessageReceivingThread(Channel channel, JSONObject jsonObject) {
        this.channel = channel;
        this.jsonObject = jsonObject;
    }

    @Override
    public void run() {
        requestReceive(channel, jsonObject);
    }


    public void requestReceive(Channel channel, JSONObject message) {
        InetSocketAddress addr = (InetSocketAddress) channel.remoteAddress();
        String currentIP = addr.getAddress().getHostAddress();
        WebsocketReq websocketReq = JSON.toJavaObject(jsonObject, WebsocketReq.class);
        WebsocketRsp websocketRsp = JSON.toJavaObject(jsonObject, WebsocketRsp.class);
        
        // Process response message
        if (LAPI_Cseq.equals(websocketRsp.getCseq())) {
            String msg = JSON.toJSONString(websocketRsp);
            System.out.println("Alarm ID is:" + msg);
            return;
        }
        
        // Process request message
        String requestURL = websocketReq.getRequestURL();
        if (requestURL != null && requestURL.contains(LAPI_BASE_PATH)) {
            String msg = JSON.toJSONString(websocketReq);
            
            System.out.println("Received event data from:" + currentIP + "event data:" + msg);
            String returnData = "Method：POST" + "\n" + "URL：" + requestURL + "\n" + "Received data:" + msg;
            downloadFile(Main.alarmDataDownloadPath, returnData);
        }
    }

    // Download return data to local
    public static boolean downloadFile(String filePath, String data) {
        String parentFolderPath = filePath;
        String newFolderName = "SubscriptionData_";

        // Increment number to distinguish files. Find existing folders and determine the next number
        int folderNumber = 1;
        // Build a unique folder name
        String uniqueFolderName;
        File parentFolder = new File(parentFolderPath);
        // If currentFolderPath is null, initialize the folder path
        if (currentFolderPath == null) {
            while (true) {
                uniqueFolderName = newFolderName + folderNumber;
                File newFile = new File(parentFolder, uniqueFolderName);
                if (newFile.exists()) {
                    folderNumber++;
                } else {
                    break;
                }
            }
            // Create folder
            File newFolder = new File(parentFolderPath, uniqueFolderName);
            if (newFolder.mkdirs()) {
                System.out.println("Folder created successfully:" + newFolder.getAbsolutePath());
                currentFolderPath = newFolder.getAbsolutePath();
            } else {
                System.out.println("Failed to create folder:" + newFolder.getAbsolutePath());
                return false; // If folder creation fails, return false
            }
        } else {
            uniqueFolderName = new File(currentFolderPath).getName();
        }
        // Specify the path for the new file
        String timeStamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd-HH-mm-ss"));
        String newFilePathBase = currentFolderPath + File.separator + "data_" + timeStamp + ".txt";
        String newFilePath = newFilePathBase;
        int fileNumber = 1;

        //  If the file already exists, increase the count in the filename
        while(new File(newFilePath).exists()){
            newFilePath = currentFolderPath + File.separator + "data_" + timeStamp + "_" + fileNumber + ".txt";
            fileNumber++;
        }
        
        // Data to write to file
        String dataToWrite = data;
        // Create and write to file
        File newFile = new File(newFilePath);
        try {
            if (newFile.createNewFile()) {
                System.out.println("New file created successfully:" + newFile.getAbsolutePath());
            } else {
                System.out.println("Failed to create new file:" + newFile.getAbsolutePath());
                return false; // If file creation fails, return false
            }
            // Write data to the new file
            try (FileWriter fileWriter = new FileWriter(newFilePath)) {
                fileWriter.write(dataToWrite);
                System.out.println("Data successfully written to file:" + newFile.getAbsolutePath());
            } catch (IOException e) {
                System.out.println("Error occurred while writing to file:" + e.getMessage());
                e.printStackTrace();
                return false; // If an error occurs while writing to the file, return false
            }
        } catch (IOException e) {
            System.out.println("Error occurred while creating a new file:" + newFile.getAbsolutePath());
            e.printStackTrace();
            return false; // Return false if an error occurs while creating the file
        }
        return true; // Return a boolean value indicating whether the file was successfully downloaded
    }
}