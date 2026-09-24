package br.sabor.corebank.customer;

import java.math.BigDecimal;

/** What inquiry is allowed to return. The PIN hash is not on this type. */
public record CustomerView(String customerNumber, String name, String branchCode, BigDecimal balance, String status) {
    public static CustomerView of(Customer customer) {
        return new CustomerView(
                customer.customerNumber(), customer.name(), customer.branchCode(), customer.balance(), customer.status());
    }
}
