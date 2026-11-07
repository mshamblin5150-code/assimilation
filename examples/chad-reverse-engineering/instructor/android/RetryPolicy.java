package org.assimilation.lab;

public final class RetryPolicy {
    private RetryPolicy() {}

    public static int delaySeconds(int attempts) {
        return attempts < 3 ? 2 : 10;
    }
}
