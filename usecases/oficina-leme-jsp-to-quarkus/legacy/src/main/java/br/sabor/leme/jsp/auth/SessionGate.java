package br.sabor.leme.jsp.auth;

import java.util.UUID;

/** Keeps the session id the browser already sent. */
public final class SessionGate {
    public String accept(String presentedSessionId) {
        if (presentedSessionId != null && presentedSessionId.trim().length() > 0) {
            return presentedSessionId;
        }
        return UUID.randomUUID().toString();
    }
}
