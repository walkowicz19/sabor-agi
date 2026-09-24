package br.sabor.leme.counter;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.not;
import static org.junit.jupiter.api.Assertions.assertFalse;

import br.sabor.leme.FixtureState;
import br.sabor.leme.security.UserDirectory;
import io.quarkus.test.junit.QuarkusTest;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import jakarta.inject.Inject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

@QuarkusTest
class CounterResourceTest {
    @Inject
    FixtureState state;

    @Inject
    UserDirectory users;

    @BeforeEach
    void reset() {
        state.reset();
    }

    private static String token(String userId, String password) {
        return given().contentType(ContentType.JSON)
                .body("{\"userId\":\"" + userId + "\",\"password\":\"" + password + "\"}")
                .when()
                .post("/sessions")
                .then()
                .statusCode(200)
                .extract()
                .path("token");
    }

    @Test
    void failedSignOnDoesNotEchoThePasswordAndLocksAfterFiveFailures() {
        for (int attempt = 0; attempt < 5; attempt++) {
            String body = given().contentType(ContentType.JSON)
                    .body("{\"userId\":\"2001\",\"password\":\"000000\"}")
                    .when()
                    .post("/sessions")
                    .then()
                    .statusCode(401)
                    .extract()
                    .asString();
            assertFalse(body.contains("000000"));
            assertFalse(body.contains("135790"));
        }
        given().contentType(ContentType.JSON)
                .body("{\"userId\":\"2001\",\"password\":\"135790\"}")
                .when()
                .post("/sessions")
                .then()
                .statusCode(429)
                .header("Retry-After", not(equalTo(null)));
    }

    @Test
    void signOnRotatesTheTokenAndSignOffDropsIt() {
        String first = token("2001", "135790");
        String second = token("2001", "135790");
        given().header("Authorization", "Bearer " + first)
                .when()
                .get("/parts")
                .then()
                .statusCode(401);
        given().header("Authorization", "Bearer " + second)
                .when()
                .get("/parts")
                .then()
                .statusCode(200);
        given().header("Authorization", "Bearer " + second)
                .when()
                .delete("/sessions")
                .then()
                .statusCode(204);
        given().header("Authorization", "Bearer " + second)
                .when()
                .get("/parts")
                .then()
                .statusCode(401);
    }

    @Test
    void anExpiredTokenIsRejected() {
        String clerk = token("2001", "135790");
        state.expireSessions();
        given().header("Authorization", "Bearer " + clerk)
                .when()
                .get("/parts")
                .then()
                .statusCode(401);
    }

    @Test
    void clerksDoNotSeeUnitCostAndSearchStaysLiteral() {
        String clerk = token("2001", "135790");
        String manager = token("3001", "246810");
        String hash = users.passwordHash("2001");

        String clerkParts = given().header("Authorization", "Bearer " + clerk)
                .when()
                .get("/parts")
                .then()
                .statusCode(200)
                .header("X-Content-Type-Options", "nosniff")
                .header("Cache-Control", "no-store")
                .body("synthetic", equalTo(true))
                .body("note", containsString("Synthetic"))
                .extract()
                .asString();
        assertFalse(clerkParts.contains("unitCost"));
        assertFalse(clerkParts.contains("18.50"));
        assertFalse(clerkParts.contains(hash.substring(0, 16)));
        assertFalse(clerkParts.contains("SELECT"));

        given().header("Authorization", "Bearer " + manager)
                .when()
                .get("/parts")
                .then()
                .statusCode(200)
                .body("parts.find { it.code == '100214' }.unitCost", equalTo("18.50"));

        given().header("Authorization", "Bearer " + clerk)
                .queryParam("q", "shoe' OR '1'='1")
                .when()
                .get("/parts")
                .then()
                .statusCode(200)
                .body("parts.size()", equalTo(0))
                .body(not(containsString("SELECT")));
    }

    @Test
    void requisitionsStayWithTheClerkUntilAManagerApprovesWithinStock() {
        String nia = token("2001", "135790");
        String rita = token("2002", "112233");
        String helio = token("3001", "246810");

        Response created = given().contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + nia)
                .body("{\"partCode\":\"100331\",\"quantity\":1}")
                .when()
                .post("/requisitions");
        created.then().statusCode(201).body("status", equalTo("PENDING")).body("unitCost", equalTo(null));
        int id = created.path("id");
        assertFalse(created.asString().contains("22.00"));

        given().header("Authorization", "Bearer " + rita)
                .when()
                .get("/requisitions/" + id)
                .then()
                .statusCode(404);

        given().contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + nia)
                .when()
                .post("/requisitions/" + id + "/approve")
                .then()
                .statusCode(403);

        given().header("Authorization", "Bearer " + helio)
                .when()
                .post("/requisitions/" + id + "/approve")
                .then()
                .statusCode(200)
                .body("status", equalTo("APPROVED"))
                .body("unitCost", equalTo("22.00"));

        given().header("Authorization", "Bearer " + helio)
                .when()
                .get("/parts?q=100331")
                .then()
                .statusCode(200)
                .body("parts[0].onHand", equalTo(0));

        given().header("Authorization", "Bearer " + helio)
                .when()
                .post("/requisitions/" + id + "/approve")
                .then()
                .statusCode(409);
    }

    @Test
    void approveLeavesStockUntouchedWhenTheBinIsShortAndRejectDoesNotIssue() {
        String nia = token("2001", "135790");
        String helio = token("3001", "246810");

        int shortId = given().contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + nia)
                .body("{\"partCode\":\"100331\",\"quantity\":2}")
                .when()
                .post("/requisitions")
                .then()
                .statusCode(201)
                .extract()
                .path("id");
        given().header("Authorization", "Bearer " + helio)
                .when()
                .post("/requisitions/" + shortId + "/approve")
                .then()
                .statusCode(409);
        given().header("Authorization", "Bearer " + helio)
                .when()
                .get("/parts?q=100331")
                .then()
                .body("parts[0].onHand", equalTo(1));

        int rejectId = given().contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + nia)
                .body("{\"partCode\":\"100214\",\"quantity\":1}")
                .when()
                .post("/requisitions")
                .then()
                .statusCode(201)
                .extract()
                .path("id");
        given().header("Authorization", "Bearer " + helio)
                .when()
                .post("/requisitions/" + rejectId + "/reject")
                .then()
                .statusCode(200)
                .body("status", equalTo("REJECTED"));
        given().header("Authorization", "Bearer " + helio)
                .when()
                .get("/parts?q=100214")
                .then()
                .body("parts[0].onHand", equalTo(4));
    }

    @Test
    void widthsRolesAndTheDeadTransferStayClosed() {
        String nia = token("2001", "135790");
        String helio = token("3001", "246810");

        given().contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + helio)
                .body("{\"partCode\":\"100214\",\"quantity\":1}")
                .when()
                .post("/requisitions")
                .then()
                .statusCode(403);

        given().contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + nia)
                .body("{\"partCode\":\"331\",\"quantity\":1}")
                .when()
                .post("/requisitions")
                .then()
                .statusCode(400);

        given().contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + nia)
                .body("{\"partCode\":\"100214\",\"quantity\":0}")
                .when()
                .post("/requisitions")
                .then()
                .statusCode(400);

        given().contentType(ContentType.JSON)
                .header("Authorization", "Bearer " + nia)
                .body("{\"partCode\":\"100214\",\"quantity\":100}")
                .when()
                .post("/requisitions")
                .then()
                .statusCode(400);

        given().when().get("/parts").then().statusCode(401);
        given().when().get("/transfer").then().statusCode(404);
        given().when().post("/transfer").then().statusCode(404);
    }
}
