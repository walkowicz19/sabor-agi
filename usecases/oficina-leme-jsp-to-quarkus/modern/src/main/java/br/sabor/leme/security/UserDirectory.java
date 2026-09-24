package br.sabor.leme.security;

import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class UserDirectory {
    @Inject
    PasswordHasher hasher;

    @ConfigProperty(name = "leme.user.nia.id")
    String niaId;

    @ConfigProperty(name = "leme.user.nia.password")
    String niaPassword;

    @ConfigProperty(name = "leme.user.rita.id")
    String ritaId;

    @ConfigProperty(name = "leme.user.rita.password")
    String ritaPassword;

    @ConfigProperty(name = "leme.user.helio.id")
    String helioId;

    @ConfigProperty(name = "leme.user.helio.password")
    String helioPassword;

    private final Map<String, User> users = new HashMap<>();
    private String dummyHash;

    @PostConstruct
    void load() {
        dummyHash = hasher.hash("not-a-fixture-password");
        add(niaId, niaPassword, "CLERK", "Nia Costa");
        add(ritaId, ritaPassword, "CLERK", "Rita Campos");
        add(helioId, helioPassword, "MANAGER", "Helio Prado");
    }

    private void add(String id, String password, String role, String displayName) {
        users.put(id, new User(id, role, displayName, hasher.hash(password)));
    }

    public Optional<User> authenticate(String userId, String password) {
        User user = userId == null ? null : users.get(userId);
        String hash = user == null ? dummyHash : user.passwordHash();
        boolean matches = hasher.verify(password, hash);
        if (user == null || !matches) {
            return Optional.empty();
        }
        return Optional.of(user);
    }

    public String passwordHash(String userId) {
        User user = users.get(userId);
        return user == null ? null : user.passwordHash();
    }

    public record User(String id, String role, String displayName, String passwordHash) {}
}
