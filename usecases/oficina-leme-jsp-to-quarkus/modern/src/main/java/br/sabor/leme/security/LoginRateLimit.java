package br.sabor.leme.security;

import br.sabor.leme.ApiException;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.concurrent.ConcurrentHashMap;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class LoginRateLimit {
    private final ConcurrentHashMap<String, Deque<Long>> failures = new ConcurrentHashMap<>();

    @Inject
    @ConfigProperty(name = "leme.login.max-failures")
    int maxFailures;

    @Inject
    @ConfigProperty(name = "leme.login.window-minutes")
    int windowMinutes;

    public void check(String userId) {
        if (userId == null || userId.isBlank()) {
            return;
        }
        long now = System.currentTimeMillis();
        Deque<Long> stamps = failures.get(userId);
        if (stamps == null) {
            return;
        }
        synchronized (stamps) {
            prune(stamps, now);
            if (stamps.size() >= maxFailures) {
                long retryMs = stamps.peekFirst() + windowMillis() - now;
                int retrySeconds = (int) Math.max(1, (retryMs + 999) / 1000);
                throw new ApiException(429, "Too many sign-on attempts", retrySeconds);
            }
        }
    }

    public void recordFailure(String userId) {
        if (userId == null || userId.isBlank()) {
            return;
        }
        Deque<Long> stamps = failures.computeIfAbsent(userId, ignored -> new ArrayDeque<>());
        long now = System.currentTimeMillis();
        synchronized (stamps) {
            prune(stamps, now);
            stamps.addLast(now);
        }
    }

    public void clear(String userId) {
        if (userId != null) {
            failures.remove(userId);
        }
    }

    public void reset() {
        failures.clear();
    }

    private void prune(Deque<Long> stamps, long now) {
        long cutoff = now - windowMillis();
        while (!stamps.isEmpty() && stamps.peekFirst() < cutoff) {
            stamps.removeFirst();
        }
    }

    private long windowMillis() {
        return windowMinutes * 60_000L;
    }
}
