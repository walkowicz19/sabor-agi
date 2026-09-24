package br.sabor.corebank.customer;

import br.sabor.corebank.security.SessionStore;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

@Path("/customers")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class CustomerResource {
    @Inject
    CustomerService customers;

    @Inject
    SessionStore sessions;

    public record RegisterRequest(String customerNumber, String name, String branchCode, String pin) {}

    public record PinChange(String oldPin, String newPin) {}

    @POST
    public Response register(@HeaderParam("X-Operator-Token") String token, RegisterRequest request) {
        sessions.require(token);
        if (request == null) {
            throw new br.sabor.corebank.ApiException(400, "Body required");
        }
        CustomerView created = customers.register(
                request.customerNumber(), request.name(), request.branchCode(), request.pin());
        return Response.status(Response.Status.CREATED).entity(created).build();
    }

    @GET
    @Path("/{customerNumber}")
    public CustomerView inquire(
            @HeaderParam("X-Operator-Token") String token, @PathParam("customerNumber") String customerNumber) {
        sessions.require(token);
        return customers.inquire(customerNumber);
    }

    @POST
    @Path("/{customerNumber}/pin")
    public Response changePin(
            @HeaderParam("X-Operator-Token") String token,
            @PathParam("customerNumber") String customerNumber,
            PinChange request) {
        sessions.require(token);
        if (request == null) {
            throw new br.sabor.corebank.ApiException(400, "Body required");
        }
        customers.changePin(customerNumber, request.oldPin(), request.newPin());
        return Response.noContent().build();
    }
}
