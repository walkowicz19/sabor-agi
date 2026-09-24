package br.sabor.leme.jsp.auth;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/** 2014-03-02. Passwords are stored and compared as the characters the clerk typed. */
public final class PlainPasswords {
    private final Map<String, String> passwords;
    private final Map<String, String> roles;

    public PlainPasswords() {
        Map<String, String> stored = new HashMap<String, String>();
        stored.put("2001", "135790");
        stored.put("2002", "112233");
        stored.put("3001", "246810");
        passwords = Collections.unmodifiableMap(stored);
        Map<String, String> assigned = new HashMap<String, String>();
        assigned.put("2001", "CLERK");
        assigned.put("2002", "CLERK");
        assigned.put("3001", "MANAGER");
        roles = Collections.unmodifiableMap(assigned);
    }

    public boolean matches(String userId, String password) {
        String stored = passwords.get(userId);
        return stored != null && stored.equals(password);
    }

    public String storedPassword(String userId) {
        return passwords.get(userId);
    }

    public String role(String userId) {
        return roles.get(userId);
    }
}
