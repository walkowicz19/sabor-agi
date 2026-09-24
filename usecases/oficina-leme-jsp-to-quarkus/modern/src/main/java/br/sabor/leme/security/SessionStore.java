package br.sabor.leme.security;

import br.sabor.leme.ApiException;
import br.sabor.leme.security.UserDirectory.User;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.HexFormat;
import java.util.concurrent.ConcurrentHashMap;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class SessionStore {
    private final SecureRandom random = new SecureRandom();
    private final ConcurrentHashMap<String, Session> byHash = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, String> hashByUser = new ConcurrentHashMap<>();

    @Inject
    @ConfigProperty(name = "leme.session.minutes")
    int sessionMinutes;

    public String open(User user) {
        String previous = hashByUser.remove(user.id());
        if (previous != null) {
            byHash.remove(previous);
        }
        byte[] raw = new byte[32];
        random.nextBytes(raw);
        String token = HexFormat.of().formatHex(raw);
        String hash = sha256(token);
        long expiresAt = System.currentTimeMillis() + sessionMinutes * 60_000L;
        byHash.put(hash, new Session(user.id(), user.role(), user.displayName(), expiresAt));
        hashByUser.put(user.id(), hash);
        return token;
    }

    public Session require(String header) {
        String token = bearer(header);
        Session session = byHash.get(sha256(token));
        if (session == null || session.expiresAt() <= System.currentTimeMillis()) {
            if (session != null) {
                closeToken(token);
            }
            throw new ApiException(401, "Sign-on required");
        }
        return session;
    }

    public void close(String header) {
        if (header == null || !header.startsWith("Bearer ")) {
            return;
        }
        closeToken(header.substring("Bearer ".length()).trim());
    }

    public void reset() {
        byHash.clear();
        hashByUser.clear();
    }

    public void expireAll() {
        long past = System.currentTimeMillis() - 1;
        byHash.replaceAll((hash, session) ->
                new Session(session.userId(), session.role(), session.displayName(), past));
    }

    private void closeToken(String token) {
        if (token == null || token.isEmpty()) {
            return;
        }
        String hash = sha256(token);
        Session session = byHash.remove(hash);
        if (session != null) {
            hashByUser.remove(session.userId(), hash);
        }
    }

    private static String bearer(String header) {
        if (header == null || !header.startsWith("Bearer ")) {
            throw new ApiException(401, "Sign-on required");
        }
        String token = header.substring("Bearer ".length()).trim();
        if (token.isEmpty()) {
            throw new ApiException(401, "Sign-on required");
        }
        return token;
    }

    private static String sha256(String token) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(token.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (Exception ex) {
            throw new IllegalStateException("Session hashing failed", ex);
        }
    }

    public record Session(String userId, String role, String displayName, long expiresAt) {}
}
