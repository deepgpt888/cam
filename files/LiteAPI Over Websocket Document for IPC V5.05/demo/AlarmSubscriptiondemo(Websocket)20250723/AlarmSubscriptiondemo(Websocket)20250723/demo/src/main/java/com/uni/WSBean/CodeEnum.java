package com.uni.WSBean;

public enum CodeEnum {
    SUCCESS(200, "Success.", "响应成功"),
    COMMON_SERVER_ERROR(1000, "Server internal error.", "服务器内部错误"),
    INVALID_PARAM(1003, "Invalid parameter.", "无效参数"),
    RESOURCE_REACH_UPPER_LIMIT(1004, "The resource limit is reached.", "资源已达上限"),
    REQUEST_TIMEOUT(1005, "Request timeout.", "请求超时"),
    FUNCTION_NOT_SUPPORTED(1006, "Function not supported.", "功能不支持"),
    NOT_REGISTER(1007, "Device not bound.", "设备未绑定"),
    NOT_YOUR_DEVICE(1008, "The device has been added to another cloud account.", "该设备已被其他用户绑定"),
    RESOURCE_NOT_EXIST(1009, "Resource not found.", "资源不存在"),
    ENDTIME_IS_EARLIER_THAN_CURRENT_TIME(1010, "The end time cannot be earlier than the current time.", "结束时间不能早于当前时间"),
    ENDTIME_IS_EARLIER_THAN_START_TIME(1011, "The end time cannot be earlier than the start time.", "结束时间不能早于开始时间"),
    NO_PERMISSION(1012, "Permission required.", "用户无权限");

    private final Integer code;
    private final String message;
    private final String zh;

    private CodeEnum(Integer resultCode, String resultMsg, String resultZh) {
        this.code = resultCode;
        this.message = resultMsg;
        this.zh = resultZh;
    }

    public Integer getCode() {
        return this.code;
    }

    public String getMessage() {
        return this.message;
    }

    public String getZh() {
        return this.zh;
    }

    public static CodeEnum getByCode(Integer code) {
        CodeEnum[] var1 = values();
        int var2 = var1.length;

        for(int var3 = 0; var3 < var2; ++var3) {
            CodeEnum codeEnum = var1[var3];
            if (codeEnum.getCode().equals(code)) {
                return codeEnum;
            }
        }

        return COMMON_SERVER_ERROR;
    }
}
