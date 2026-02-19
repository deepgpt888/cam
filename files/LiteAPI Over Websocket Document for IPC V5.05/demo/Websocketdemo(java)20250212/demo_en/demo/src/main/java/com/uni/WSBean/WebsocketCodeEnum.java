package com.uni.WSBean;

import org.jetbrains.annotations.NotNull;

/**
 * WEBSocket error code
 */
public enum WebsocketCodeEnum {
    /**
     * Response successful
     */
    SUCCESS(0, "Succeed"),

    /**
     * Common error
     */
    COMMON_ERROR(1, "Common error"),

    /**
     * Invalid Arguments
     */
    INVALID_ARGUMENTS(2, "Invalid Arguments"),

    /**
     * Authentication failed
     */
    NOT_AUTHORIZED(3, "Not Authorized"),

    /**
     * Feature not supported
     */
    NOT_SUPPORTED(4, "Not Supported"),

    /**
     * Abnormal user status
     */
    AbNORMAL_USER_STASUS(5, "Abnormal User Status"),

    /**
     * Partial Success
     */
    PARTIALLY_SUCCEED(102, "Partially Succeed"),

    /**
     * Token exception or expiration
     */
    INVALID_TOKEN(1002, "Invalid token"),

    /**
     * The device does not exist
     */
    DEVICE_NOT_EXIST(2001, "Device not exist"),

    /**
     * Server Internal Error
     */
    INTERNAL_SERVER_ERROR(500, "Internal Server Error");

    /**
     * attribute-code
     */
    private long code;

    /**
     * attribute-message
     */
    private String message;

    WebsocketCodeEnum(long code1, String message1) {
        this.code = code1;
        this.message = message1;
    }

    /**
     * Get variables-code
     *
     * @return Integer
     * 
     */
    public Long getCode() {
        return code;
    }

    /**
     * Get variables-message
     *
     * @return String
     * 
     */
    public String getMessage() {
        return message;
    }

    /**
     * Convert the error code into corresponding specific information
     *
     * @param code error code
     * @return CodeEnum
     * 
     */
    public static CodeEnum lapiCodeTypeToUcs(@NotNull Long code) {
        CodeEnum codeEnum;

        if (code == WebsocketCodeEnum.NOT_SUPPORTED.code) {
            codeEnum = CodeEnum.FUNCTION_NOT_SUPPORTED;
        } else if (code == WebsocketCodeEnum.INVALID_ARGUMENTS.code) {
            codeEnum = CodeEnum.INVALID_PARAM;
        } else if (code == WebsocketCodeEnum.NOT_AUTHORIZED.code) {
            codeEnum = CodeEnum.NO_PERMISSION;
        } else {
            codeEnum = CodeEnum.COMMON_SERVER_ERROR;
        }
        return codeEnum;
    }

    /**
     * Error code conversion
     *
     * @param code error code
     * @return CodeEnum
     * 
     */
    public static WebsocketCodeEnum UcsCodeTypeToLapi(@NotNull Integer code) {
        WebsocketCodeEnum codeEnum;

        if (code.equals(CodeEnum.FUNCTION_NOT_SUPPORTED.getCode())) {
            codeEnum = WebsocketCodeEnum.NOT_SUPPORTED;
        } else if (code.equals(CodeEnum.INVALID_PARAM.getCode())) {
            codeEnum = WebsocketCodeEnum.INVALID_ARGUMENTS;
        } else if (code.equals(CodeEnum.NO_PERMISSION.getCode())) {
            codeEnum = WebsocketCodeEnum.NOT_AUTHORIZED;
        } else {
            codeEnum = WebsocketCodeEnum.COMMON_ERROR;
        }
        return codeEnum;
    }
}
