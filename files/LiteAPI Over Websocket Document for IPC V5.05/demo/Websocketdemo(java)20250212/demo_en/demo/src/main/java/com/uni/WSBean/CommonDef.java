package com.uni.WSBean;

/**
 * WSS module common definition
 *
 */
public final class CommonDef {

    /**
     * LAPI message response timeout
     */
    public static final Integer LAPI_TIMEOUT = 5000;

    /**
     * WebSocket port
     */
    public static final Integer WEBSOCKET_PORT = 82;

    /**
     * Sign timeout period
     */
    public static final Integer SIGN_TIME = 5;

    /**
     * The parameters carried in the connection URI need to be removed
     * Get URL parameters and their values
     */
    public static final Integer URI_DELETE_PARAM = 9;

    /**
     * Parameter number 2 in the method of obtaining URL
     */
    public static final Integer URI_PARAM_GET_1 = 2;

    /**
     * Parameter number 3 in the method of obtaining URL
     */
    public static final Integer URI_PARAM_GET_2 = 3;

    /**
     * Netty initialization parameters
     */
    public static final Integer NETTY_MAX_CONTENT_LENGTH = 1024;

    /**
     * Netty initialization parameters
     */
    public static final Integer NETTY_MAX_CONTENT_LENGTH_2 = 62;

    /**
     * Load Balance
     */
    public static final Double MAX_DEVICE_NUM_PRESENT = 0.5;

    /*********************** Json serialization priority **************************/
    /**
     * Level1
     */
    public static final int JSON_ORDINAL_LEVEL_1 = 1;

    /**
     * Level2
     */
    public static final int JSON_ORDINAL_LEVEL_2 = 2;

    /**
     * Level3
     */
    public static final int JSON_ORDINAL_LEVEL_3 = 3;

    /**
     * Level4
     */
    public static final int JSON_ORDINAL_LEVEL_4 = 4;

    /**
     * Level5
     */
    public static final int JSON_ORDINAL_LEVEL_5 = 5;

    /**
     * Level6
     */
    public static final int JSON_ORDINAL_LEVEL_6 = 6;

    /**
     * Level7
     */
    public static final int JSON_ORDINAL_LEVEL_7 = 7;

    /**
     * Level8
     */
    public static final int JSON_ORDINAL_LEVEL_8 = 8;

    /**
     * Level9
     */
    public static final int JSON_ORDINAL_LEVEL_9 = 9;

    /**
     * Level10
     */
    public static final int JSON_ORDINAL_LEVEL_10 = 10;

    /**
     * Level11
     */
    public static final int JSON_ORDINAL_LEVEL_11 = 11;

    /**
     * Level12
     */
    public static final int JSON_ORDINAL_LEVEL_12 = 12;

    /**
     * Level13
     */
    public static final int JSON_ORDINAL_LEVEL_13 = 13;

    /**
     * Level14
     */
    public static final int JSON_ORDINAL_LEVEL_14 = 14;

    /**
     * Level15
     */
    public static final int JSON_ORDINAL_LEVEL_15 = 15;

    /**
     * Level16
     */
    public static final int JSON_ORDINAL_LEVEL_16 = 16;

    /**
     * nonce length
     */
    public static final int NONCE_LENGTH = 16;

    /**
     * Equipment serial number length
     */
    public static final Integer DEVICE_SN_LEN = 20;

    /**
     * HTTP response code
     * unauthenticated
     * 401
     */
    public static final int HTTP_RESPONSE_CODE_401 = 401;

    /**
     * HTTP response code not found 404
     */
    public static final int HTTP_RESPONSE_CODE_404 = 404;

    private CommonDef() {

    }

}
