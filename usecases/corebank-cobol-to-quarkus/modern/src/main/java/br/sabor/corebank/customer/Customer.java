package br.sabor.corebank.customer;

import java.math.BigDecimal;

public record Customer(
        String customerNumber,
        String name,
        String branchCode,
        String pinHash,
        BigDecimal balance,
        String status) {

    public Customer withPinHash(String newHash) {
        return new Customer(customerNumber, name, branchCode, newHash, balance, status);
    }
}
