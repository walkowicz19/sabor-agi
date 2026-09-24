package br.sabor.leme;

public final class ApiException extends RuntimeException {
    private final int status;
    private final Integer retryAfterSeconds;

    public ApiException(int status, String message) {
        this(status, message, null);
    }

    public ApiException(int status, String message, Integer retryAfterSeconds) {
        super(message);
        this.status = status;
        this.retryAfterSeconds = retryAfterSeconds;
    }

    public int status() {
        return status;
    }

    public Integer retryAfterSeconds() {
        return retryAfterSeconds;
    }
}
