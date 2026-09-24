package br.sabor.leme;

import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.ExceptionMapper;
import jakarta.ws.rs.ext.Provider;
import java.util.Map;

@Provider
public final class ApiExceptionMapper implements ExceptionMapper<ApiException> {
    @Override
    public Response toResponse(ApiException exception) {
        Response.ResponseBuilder builder = Response.status(exception.status())
                .type(MediaType.APPLICATION_JSON)
                .entity(Map.of("error", exception.getMessage()));
        if (exception.retryAfterSeconds() != null) {
            builder.header("Retry-After", exception.retryAfterSeconds());
        }
        return builder.build();
    }
}
