package com.uni.WSBean;

import com.alibaba.fastjson.annotation.JSONField;

import lombok.Data;


/**
 * Keep-alive response
 */
@Data
public class KeepAliveRspAO {
    /**
     * Server current UTC time
     */
    @JSONField(ordinal = 1, name = "Timestamp")
    private Long timestamp;

    /**
     * Next heartbeat interval, in seconds
     */
    @JSONField(ordinal = 1, name = "Timeout")
    private Integer timeout;
}
