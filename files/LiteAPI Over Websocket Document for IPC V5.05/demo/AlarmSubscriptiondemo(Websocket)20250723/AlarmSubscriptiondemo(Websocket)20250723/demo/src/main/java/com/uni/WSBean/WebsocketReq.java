package com.uni.WSBean;

import com.alibaba.fastjson.annotation.JSONField;

import lombok.Data;



/**
 * WebSocket request entity class
 *
 */
@Data
public class WebsocketReq {


    /**
     * Request URL
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_1, name = "RequestURL")
    private String requestURL;

    /**
     * Request method
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_2, name = "Method")
    private String method;

    /**
     * Request sequence number
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_3, name = "Cseq")
    private Long cseq;

    /**
     * Request data
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_4, name = "Data")
    private Object data;
}
