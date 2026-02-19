package com.uni.Websocketserver;

import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Processing thread tasks
 */
@Component
@Order(1)
public final class KeepLiveThreadPoolExecutor {

    /**
     * Thread Pool Parameters - Number of Thread Pools
     */
    private static final AtomicInteger THREAD_NUM = new AtomicInteger(1);

    /**
     * Thread Pool Parameters - Number of Core Threads
     */
    private static final Integer CORE_POOL_SIZE = 50;

    /**
     * Thread Pool Parameters - Maximum Number of Threads
     */
    private static final Integer MAX_POOL_SIZE = 100;

    /**
     * Thread pool parameters - keep alive time
     */
    private static final Integer KEEP_ALIVE_TIME = 5;

    /**
     * Thread Pool Parameters - Number of Threads
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
         * Naming prefix
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
