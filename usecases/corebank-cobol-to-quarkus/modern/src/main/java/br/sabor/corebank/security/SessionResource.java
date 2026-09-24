package br.sabor.corebank.security;

import br.sabor.corebank.ApiException;
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
    OperatorDirectory operators;

    @Inject
    SessionStore sessions;

    public record SignOn(String operatorId, String pin) {}

    @POST
    public Map<String, String> signOn(SignOn request) {
        if (request == null || !operators.authenticate(request.operatorId(), request.pin())) {
            throw new ApiException(401, "Sign-on failed");
        }
        return Map.of("token", sessions.open(request.operatorId()));
    }

    @DELETE
    public Response signOff(@HeaderParam("X-Operator-Token") String token) {
        sessions.close(token);
        return Response.noContent().build();
    }
}
