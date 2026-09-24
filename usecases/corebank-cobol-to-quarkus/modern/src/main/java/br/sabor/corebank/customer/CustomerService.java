package br.sabor.corebank.customer;

import br.sabor.corebank.ApiException;
import br.sabor.corebank.security.PinHasher;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.math.BigDecimal;

@ApplicationScoped
public class CustomerService {
    private final CustomerRepository customers;
    private final PinHasher pins;

    @Inject
    public CustomerService(CustomerRepository customers) {
        this(customers, new PinHasher());
    }

    CustomerService(CustomerRepository customers, PinHasher pins) {
        this.customers = customers;
        this.pins = pins;
    }

    public CustomerView register(String customerNumber, String name, String branchCode, String pin) {
        String number = requireDigits(customerNumber, 10, "Customer number must be 10 digits");
        String branch = requireDigits(branchCode, 4, "Branch code must be 4 digits");
        String cleanName = NamePolicy.normalize(name);
        if (customers.find(number).isPresent()) {
            throw new ApiException(409, "Customer number already exists");
        }
        Customer customer = new Customer(number, cleanName, branch, pins.hash(pin), BigDecimal.ZERO, "A");
        customers.insert(customer);
        return CustomerView.of(customer);
    }

    public CustomerView inquire(String customerNumber) {
        return CustomerView.of(load(customerNumber));
    }

    public void changePin(String customerNumber, String oldPin, String newPin) {
        Customer customer = load(customerNumber);
        if (!pins.verify(oldPin, customer.pinHash())) {
            throw new ApiException(400, "Old PIN does not match");
        }
        customers.update(customer.withPinHash(pins.hash(newPin)));
    }

    private Customer load(String customerNumber) {
        String number = requireDigits(customerNumber, 10, "Customer number must be 10 digits");
        return customers.find(number).orElseThrow(() -> new ApiException(404, "Customer not found"));
    }

    private static String requireDigits(String raw, int length, String message) {
        if (raw == null || !raw.matches("\\d{" + length + "}")) {
            throw new ApiException(400, message);
        }
        return raw;
    }
}
