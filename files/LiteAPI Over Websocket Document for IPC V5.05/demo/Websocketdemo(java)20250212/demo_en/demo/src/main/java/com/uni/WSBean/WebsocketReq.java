package com.uni.WSBean;

import com.alibaba.fastjson.annotation.JSONField;

import lombok.Data;



/**
 * WebSocket requests entity class
 *
 */
@Data
public class WebsocketReq {


    /**
     * request url
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_1, name = "RequestURL")
    private String requestURL;

    /**
     * request method
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_2, name = "Method")
    private String method;

    /**
     * Request Number
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_3, name = "Cseq")
    private Long cseq;

    /**
     * request data
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_4, name = "Data")
    private Object data;
}
