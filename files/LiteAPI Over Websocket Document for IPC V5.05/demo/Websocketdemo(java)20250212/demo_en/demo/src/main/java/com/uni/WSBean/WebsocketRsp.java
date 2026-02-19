package com.uni.WSBean;

import com.alibaba.fastjson.annotation.JSONField;
import lombok.Data;


/**
 * Response
 */
@Data
public class WebsocketRsp {

    /**
     * Response URL
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_1, name = "ResponseURL")
    private String responseURL;

    /**
     * response code
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_2, name = "ResponseCode")
    private Long responseCode;

    /**
     * Response
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_3, name = "ResponseString")
    private String responseString;

    /**
     * Serial Number
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_4, name = "Cseq")
    private Long cseq;

    /**
     * Response data
     */
    @JSONField(ordinal = CommonDef.JSON_ORDINAL_LEVEL_5, name = "Data")
    private Object data;

    public WebsocketRsp() {
        this.responseCode = WebsocketCodeEnum.SUCCESS.getCode();
        this.responseString = WebsocketCodeEnum.SUCCESS.getMessage();
    }

}
