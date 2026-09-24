package br.sabor.corebank.customer;

import java.util.Optional;

public interface CustomerRepository {
    Optional<Customer> find(String customerNumber);

    void insert(Customer customer);

    void update(Customer customer);
}
