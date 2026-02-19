package com.uni.Websocketserver;

import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Thread task handler
 */
@Component
@Order(1)
public final class KeepLiveThreadPoolExecutor {

    /**
     * Thread pool parameter - thread pool count
     */
    private static final AtomicInteger THREAD_NUM = new AtomicInteger(1);

    /**
     * Thread pool parameter - core thread count
     */
    private static final Integer CORE_POOL_SIZE = 50;

    /**
     * Thread pool parameter - maximum thread count
     */
    private static final Integer MAX_POOL_SIZE = 100;

    /**
     * Thread pool parameter - keep alive time
     */
    private static final Integer KEEP_ALIVE_TIME = 5;

    /**
     * Thread pool parameter - thread count
     */
    private static final Integer QUEUE_SIZE = 1000;


    /**
     * Create thread pool
     */
    public static final ExecutorService EXECUTOR_SERVICE = new java.util.concurrent.ThreadPoolExecutor(CORE_POOL_SIZE,
                                                                                  MAX_POOL_SIZE, KEEP_ALIVE_TIME,
                                                                                  TimeUnit.MINUTES,
                                                                                  new ArrayBlockingQueue<Runnable>(
                                                                                          QUEUE_SIZE),
                                                                                  new NVRThreadFactory(
                                                                                          "KeepLiveThreadPool"));

    private KeepLiveThreadPoolExecutor() {
    }

    /**
     * Custom thread initialization
     */
    private static final class NVRThreadFactory implements ThreadFactory {
        /**
         * Name prefix
         */
        private final String namePrefix;

        private NVRThreadFactory(String namePrefix1) {
            this.namePrefix = namePrefix1;
        }

        /**
         * Create thread
         * 
         */
        @Override
        public Thread newThread(Runnable r) {
            Thread thread = new Thread(r, namePrefix + "-" + THREAD_NUM.getAndIncrement());
            return thread;
        }
    }


}
