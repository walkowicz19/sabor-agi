package br.sabor.corebank.security;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class OperatorDirectory {
    private final String operatorId;
    private final String pinHash;
    private final PinHasher pins = new PinHasher();

    @Inject
    public OperatorDirectory(
            @ConfigProperty(name = "corebank.operator.id") String operatorId,
            @ConfigProperty(name = "corebank.operator.pin") String pin) {
        this.operatorId = operatorId;
        this.pinHash = pins.hash(pin);
    }

    public boolean authenticate(String id, String pin) {
        return operatorId.equals(id) && pins.verify(pin, pinHash);
    }
}
