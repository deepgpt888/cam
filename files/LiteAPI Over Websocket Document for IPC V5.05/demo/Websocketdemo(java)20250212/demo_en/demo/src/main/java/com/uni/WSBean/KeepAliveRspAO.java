package com.uni.WSBean;

import com.alibaba.fastjson.annotation.JSONField;

import lombok.Data;


/**
 * Stay alive response
 */
@Data
public class KeepAliveRspAO {
    /**
     * The current UTC time of the server
     */
    @JSONField(ordinal = 1, name = "Timestamp")
    private Long timestamp;

    /**
     * Next heartbeat interval, unit: seconds
     */
    @JSONField(ordinal = 1, name = "Timeout")
    private Integer timeout;
}
