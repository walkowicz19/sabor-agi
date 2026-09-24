package br.sabor.leme.counter;

import br.sabor.leme.ApiException;
import br.sabor.leme.security.SessionStore;
import br.sabor.leme.security.SessionStore.Session;
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
import java.util.List;

@Path("/requisitions")
@Produces(MediaType.APPLICATION_JSON)
public class RequisitionResource {
    @Inject
    RequisitionBook book;

    @Inject
    SessionStore sessions;

    public record CreateRequest(String partCode, Integer quantity) {}

    @GET
    public List<RequisitionView> list(@HeaderParam("Authorization") String authorization) {
        Session session = sessions.require(authorization);
        return book.list(session.userId(), session.role());
    }

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    public Response create(@HeaderParam("Authorization") String authorization, CreateRequest request) {
        Session session = sessions.require(authorization);
        if (request == null || request.quantity() == null) {
            throw new ApiException(400, "Quantity must be from 1 to 99");
        }
        RequisitionView created = book.create(
                session.userId(), session.role(), request.partCode(), request.quantity());
        return Response.status(Response.Status.CREATED).entity(created).build();
    }

    @GET
    @Path("/{id}")
    public RequisitionView read(@HeaderParam("Authorization") String authorization, @PathParam("id") long id) {
        Session session = sessions.require(authorization);
        return book.read(session.userId(), session.role(), id);
    }

    @POST
    @Path("/{id}/approve")
    public RequisitionView approve(@HeaderParam("Authorization") String authorization, @PathParam("id") long id) {
        Session session = sessions.require(authorization);
        return book.approve(session.role(), id);
    }

    @POST
    @Path("/{id}/reject")
    public RequisitionView reject(@HeaderParam("Authorization") String authorization, @PathParam("id") long id) {
        Session session = sessions.require(authorization);
        return book.reject(session.role(), id);
    }
}
