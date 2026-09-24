package br.sabor.leme.counter;

import br.sabor.leme.security.SessionStore;
import br.sabor.leme.security.SessionStore.Session;
import jakarta.inject.Inject;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.MediaType;
import java.util.List;

@Path("/parts")
@Produces(MediaType.APPLICATION_JSON)
public class PartResource {
    @Inject
    PartCatalog catalog;

    @Inject
    SessionStore sessions;

    public record PartList(boolean synthetic, String note, List<PartView> parts) {}

    @GET
    public PartList list(@HeaderParam("Authorization") String authorization, @QueryParam("q") String query) {
        Session session = sessions.require(authorization);
        return new PartList(
                true,
                "Synthetic fixture stock.",
                catalog.find(query, session.role()));
    }
}
