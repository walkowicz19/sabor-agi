package br.sabor.corebank.security;

import br.sabor.corebank.ApiException;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@ApplicationScoped
public class SessionStore {
    private final Map<String, String> tokens = new ConcurrentHashMap<>();

    public String open(String operatorId) {
        String token = UUID.randomUUID().toString();
        tokens.put(token, operatorId);
        return token;
    }

    public void require(String token) {
        if (token == null || !tokens.containsKey(token)) {
            throw new ApiException(401, "Operator session required");
        }
    }

    public void close(String token) {
        if (token != null) {
            tokens.remove(token);
        }
    }
}
