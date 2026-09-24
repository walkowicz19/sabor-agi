package br.sabor.leme.security;

import br.sabor.leme.ApiException;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.DELETE;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import java.util.Map;

@Path("/sessions")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class SessionResource {
    @Inject
    UserDirectory users;

    @Inject
    SessionStore sessions;

    @Inject
    LoginRateLimit limits;

    public record SignOn(String userId, String password) {}

    @POST
    public Map<String, String> signOn(SignOn request) {
        if (request == null || request.userId() == null || request.userId().isBlank()) {
            throw new ApiException(401, "Sign-on failed");
        }
        limits.check(request.userId());
        return users.authenticate(request.userId(), request.password())
                .map(user -> {
                    limits.clear(user.id());
                    return Map.of(
                            "token", sessions.open(user),
                            "role", user.role(),
                            "displayName", user.displayName());
                })
                .orElseThrow(() -> {
                    limits.recordFailure(request.userId());
                    return new ApiException(401, "Sign-on failed");
                });
    }

    @DELETE
    public Response signOff(@HeaderParam("Authorization") String authorization) {
        sessions.require(authorization);
        sessions.close(authorization);
        return Response.noContent().build();
    }
}
