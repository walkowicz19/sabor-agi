package br.sabor.corebank.customer;

import jakarta.enterprise.context.ApplicationScoped;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@ApplicationScoped
public final class InMemoryCustomerRepository implements CustomerRepository {
    private final Map<String, Customer> rows = new ConcurrentHashMap<>();

    @Override
    public Optional<Customer> find(String customerNumber) {
        return Optional.ofNullable(rows.get(customerNumber));
    }

    @Override
    public void insert(Customer customer) {
        rows.put(customer.customerNumber(), customer);
    }

    @Override
    public void update(Customer customer) {
        rows.put(customer.customerNumber(), customer);
    }
}
