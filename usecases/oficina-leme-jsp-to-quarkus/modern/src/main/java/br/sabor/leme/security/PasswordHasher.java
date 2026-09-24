package br.sabor.leme.security;

import jakarta.enterprise.context.ApplicationScoped;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.spec.KeySpec;
import java.util.Base64;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

/** PBKDF2-HMAC-SHA256. The password is not stored. */
@ApplicationScoped
public class PasswordHasher {
    private static final int ITERATIONS = 120_000;
    private static final int KEY_BITS = 256;
    private final SecureRandom random = new SecureRandom();

    public String hash(String password) {
        if (password == null || password.isEmpty()) {
            throw new IllegalArgumentException("Password required");
        }
        byte[] salt = new byte[16];
        random.nextBytes(salt);
        return encode(salt) + ":" + encode(derive(password, salt));
    }

    public boolean verify(String password, String stored) {
        if (password == null || password.isEmpty() || stored == null || !stored.contains(":")) {
            return false;
        }
        String[] parts = stored.split(":", 2);
        try {
            byte[] salt = decode(parts[0]);
            byte[] expected = decode(parts[1]);
            return MessageDigest.isEqual(derive(password, salt), expected);
        } catch (IllegalArgumentException ex) {
            return false;
        }
    }

    private static byte[] derive(String password, byte[] salt) {
        PBEKeySpec spec = new PBEKeySpec(password.toCharArray(), salt, ITERATIONS, KEY_BITS);
        try {
            KeySpec key = spec;
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(key).getEncoded();
        } catch (Exception ex) {
            throw new IllegalStateException("Password hashing failed", ex);
        } finally {
            spec.clearPassword();
        }
    }

    private static String encode(byte[] raw) {
        return Base64.getEncoder().encodeToString(raw);
    }

    private static byte[] decode(String text) {
        return Base64.getDecoder().decode(text);
    }
}
