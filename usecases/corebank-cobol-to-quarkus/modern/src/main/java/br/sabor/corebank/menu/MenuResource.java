package br.sabor.corebank.menu;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import java.util.List;
import java.util.Map;

@Path("/menu")
@Produces(MediaType.APPLICATION_JSON)
public class MenuResource {
    @GET
    public Map<String, Object> menu() {
        return Map.of(
                "actions",
                List.of(
                        action("1", "register", "POST", "/customers"),
                        action("2", "inquiry", "GET", "/customers/{customerNumber}"),
                        action("3", "change-pin", "POST", "/customers/{customerNumber}/pin"),
                        action("9", "exit", "NONE", "")));
    }

    private static Map<String, String> action(String code, String name, String method, String path) {
        return Map.of("code", code, "name", name, "method", method, "path", path);
    }
}
