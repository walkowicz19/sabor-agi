package br.sabor.corebank.security;

import br.sabor.corebank.ApiException;
import java.security.SecureRandom;
import java.security.spec.KeySpec;
import java.util.Base64;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

/** Stores a 6-digit PIN as salt plus PBKDF2. The PIN itself is never stored. */
public final class PinHasher {
    private static final int ITERATIONS = 120_000;
    private static final int KEY_BITS = 256;
    private final SecureRandom random = new SecureRandom();

    public String hash(String pin) {
        requirePin(pin);
        byte[] salt = new byte[16];
        random.nextBytes(salt);
        return encode(salt) + ":" + encode(derive(pin, salt));
    }

    public boolean verify(String pin, String stored) {
        if (pin == null || stored == null || !stored.contains(":")) {
            return false;
        }
        requirePin(pin);
        String[] parts = stored.split(":", 2);
        byte[] salt = decode(parts[0]);
        byte[] expected = decode(parts[1]);
        return java.security.MessageDigest.isEqual(derive(pin, salt), expected);
    }

    public static void requirePin(String pin) {
        if (pin == null || !pin.matches("\\d{6}")) {
            throw new ApiException(400, "PIN must be exactly 6 digits");
        }
    }

    private static byte[] derive(String pin, byte[] salt) {
        try {
            KeySpec spec = new PBEKeySpec(pin.toCharArray(), salt, ITERATIONS, KEY_BITS);
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();
        } catch (Exception ex) {
            throw new IllegalStateException("PIN hashing failed", ex);
        }
    }

    private static String encode(byte[] raw) {
        return Base64.getEncoder().encodeToString(raw);
    }

    private static byte[] decode(String text) {
        return Base64.getDecoder().decode(text);
    }
}
