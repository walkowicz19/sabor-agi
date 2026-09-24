package br.sabor.leme;

import br.sabor.leme.counter.PartCatalog;
import br.sabor.leme.counter.RequisitionBook;
import br.sabor.leme.security.LoginRateLimit;
import br.sabor.leme.security.SessionStore;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

@ApplicationScoped
public class FixtureState {
    @Inject
    SessionStore sessions;

    @Inject
    LoginRateLimit limits;

    @Inject
    PartCatalog catalog;

    @Inject
    RequisitionBook book;

    public void reset() {
        sessions.reset();
        limits.reset();
        catalog.reseed();
        book.clear();
    }

    public void expireSessions() {
        sessions.expireAll();
    }
}
