package br.sabor.corebank.customer;

import br.sabor.corebank.ApiException;

/**
 * One name rule. The COBOL program had two copies, and the second copy accepted blanks.
 * This is the copy that rejects them.
 */
public final class NamePolicy {
    private NamePolicy() {}

    public static String normalize(String raw) {
        String name = raw == null ? "" : raw.trim();
        if (name.isEmpty() || name.length() > 40) {
            throw new ApiException(400, "Name is required and must be at most 40 characters");
        }
        return name;
    }
}
