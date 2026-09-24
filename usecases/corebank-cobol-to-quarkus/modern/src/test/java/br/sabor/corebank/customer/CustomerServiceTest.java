package br.sabor.corebank.customer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.sabor.corebank.ApiException;
import br.sabor.corebank.security.PinHasher;
import org.junit.jupiter.api.Test;

class CustomerServiceTest {
    @Test
    void rejectsBlankNameThatTheDuplicateCobolCheckAccepted() {
        CustomerService service = new CustomerService(new InMemoryCustomerRepository(), new PinHasher());
        ApiException error = assertThrows(
                ApiException.class, () -> service.register("0000000001", "   ", "0001", "123456"));
        assertEquals(400, error.status());
    }

    @Test
    void rejectsDuplicateCustomerNumber() {
        CustomerService service = new CustomerService(new InMemoryCustomerRepository(), new PinHasher());
        service.register("0000000001", "Ada Lovelace", "0001", "123456");
        ApiException error = assertThrows(
                ApiException.class, () -> service.register("0000000001", "Grace Hopper", "0001", "654321"));
        assertEquals(409, error.status());
    }

    @Test
    void rejectsCustomerNumberAndBranchThatAreNotTheLegacyWidths() {
        CustomerService service = new CustomerService(new InMemoryCustomerRepository(), new PinHasher());
        ApiException number = assertThrows(
                ApiException.class, () -> service.register("42", "Ada Lovelace", "0001", "123456"));
        assertEquals(400, number.status());
        ApiException branch = assertThrows(
                ApiException.class, () -> service.register("0000000002", "Ada Lovelace", "10", "123456"));
        assertEquals(400, branch.status());
        ApiException pin = assertThrows(
                ApiException.class, () -> service.register("0000000002", "Ada Lovelace", "0001", "1234"));
        assertEquals(400, pin.status());
    }

    @Test
    void changePinReplacesTheHashAndKeepsTheBalance() {
        InMemoryCustomerRepository repository = new InMemoryCustomerRepository();
        PinHasher hasher = new PinHasher();
        CustomerService service = new CustomerService(repository, hasher);
        service.register("0000000001", "Ada Lovelace", "0001", "123456");
        service.changePin("0000000001", "123456", "999999");
        Customer stored = repository.find("0000000001").orElseThrow();
        assertEquals(true, hasher.verify("999999", stored.pinHash()));
        assertEquals("0", stored.balance().toPlainString());
    }
}
