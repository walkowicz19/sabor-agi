package br.sabor.corebank.customer;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.not;
import static org.junit.jupiter.api.Assertions.assertFalse;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.http.ContentType;
import org.junit.jupiter.api.Test;

@QuarkusTest
class CustomerResourceTest {
    @Test
    void menuDoesNotExposeTheDeadWireTransfer() {
        given().when()
                .get("/menu")
                .then()
                .statusCode(200)
                .body("actions.name", hasItem("register"))
                .body("actions.name", not(hasItem("wire-transfer")));
    }

    @Test
    void cobolBackdoorOperatorIsRejected() {
        given().contentType(ContentType.JSON)
                .body("{\"operatorId\":\"9999\",\"pin\":\"ADMIN\"}")
                .when()
                .post("/sessions")
                .then()
                .statusCode(401);
    }

    @Test
    void registrationRequiresASessionAndDoesNotReturnThePin() {
        String token = signOn();
        given().contentType(ContentType.JSON)
                .body("{\"customerNumber\":\"0000000042\",\"name\":\"Ada Lovelace\",\"branchCode\":\"0010\",\"pin\":\"135790\"}")
                .when()
                .post("/customers")
                .then()
                .statusCode(401);

        String body = given().contentType(ContentType.JSON)
                .header("X-Operator-Token", token)
                .body("{\"customerNumber\":\"0000000042\",\"name\":\"Ada Lovelace\",\"branchCode\":\"0010\",\"pin\":\"135790\"}")
                .when()
                .post("/customers")
                .then()
                .statusCode(201)
                .body("name", equalTo("Ada Lovelace"))
                .body("balance", equalTo(0))
                .extract()
                .asString();
        assertFalse(body.contains("135790"));
        assertFalse(body.contains("pinHash"));
    }

    @Test
    void tellerPageIsTheMenuAndOmitsTheDeadWirePath() {
        String page = given().when().get("/").then().statusCode(200).extract().asString();
        assertFalse(page.toLowerCase().contains("wire"));
        assertFalse(page.contains("246810"));
        assertFalse(page.contains("ADMIN"));
    }

    @Test
    void pinChangeAndSignOffFollowTheMenu() {
        String token = signOn();
        given().contentType(ContentType.JSON)
                .header("X-Operator-Token", token)
                .body("{\"customerNumber\":\"0000000088\",\"name\":\"Katherine Johnson\",\"branchCode\":\"0012\",\"pin\":\"135790\"}")
                .when()
                .post("/customers")
                .then()
                .statusCode(201)
                .body("status", equalTo("A"))
                .body("balance", equalTo(0));

        given().contentType(ContentType.JSON)
                .header("X-Operator-Token", token)
                .body("{\"customerNumber\":\"42\",\"name\":\"Katherine Johnson\",\"branchCode\":\"0012\",\"pin\":\"135790\"}")
                .when()
                .post("/customers")
                .then()
                .statusCode(400);

        given().contentType(ContentType.JSON)
                .header("X-Operator-Token", token)
                .body("{\"oldPin\":\"135790\",\"newPin\":\"246802\"}")
                .when()
                .post("/customers/0000000088/pin")
                .then()
                .statusCode(204);

        given().header("X-Operator-Token", token)
                .when()
                .get("/customers/0000000088")
                .then()
                .statusCode(200)
                .body("name", equalTo("Katherine Johnson"))
                .body(not(containsString("246802")));

        given().header("X-Operator-Token", token).when().delete("/sessions").then().statusCode(204);

        given().contentType(ContentType.JSON)
                .header("X-Operator-Token", token)
                .body("{\"customerNumber\":\"0000000089\",\"name\":\"Mary Jackson\",\"branchCode\":\"0012\",\"pin\":\"135790\"}")
                .when()
                .post("/customers")
                .then()
                .statusCode(401);
    }

    @Test
    void inquiryRequiresASession() {
        String token = signOn();
        given().contentType(ContentType.JSON)
                .header("X-Operator-Token", token)
                .body("{\"customerNumber\":\"0000000077\",\"name\":\"Grace Hopper\",\"branchCode\":\"0007\",\"pin\":\"222222\"}")
                .when()
                .post("/customers")
                .then()
                .statusCode(201);

        given().when().get("/customers/0000000077").then().statusCode(401);

        given().header("X-Operator-Token", token)
                .when()
                .get("/customers/0000000077")
                .then()
                .statusCode(200)
                .body("name", equalTo("Grace Hopper"));
    }

    private static String signOn() {
        return given().contentType(ContentType.JSON)
                .body("{\"operatorId\":\"1001\",\"pin\":\"246810\"}")
                .when()
                .post("/sessions")
                .then()
                .statusCode(200)
                .extract()
                .path("token");
    }
}
