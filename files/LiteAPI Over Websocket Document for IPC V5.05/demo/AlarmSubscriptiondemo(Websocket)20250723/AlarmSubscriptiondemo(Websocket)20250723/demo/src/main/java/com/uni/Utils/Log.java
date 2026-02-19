package com.uni.Utils;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Log {
    // Set time format
    static DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    public static void info(String content){
        // Get current time
        LocalDateTime time = LocalDateTime.now();
        // Format time
        String formattedTime = time.format(formatter);
        // Print time-stamped information, e.g.: [time]+from xxx
        System.out.println("[" + formattedTime + "]:" + content);
    }

    public static void info(String content, Object...args){
        Log.info(String.format(content, args));
    }
}
