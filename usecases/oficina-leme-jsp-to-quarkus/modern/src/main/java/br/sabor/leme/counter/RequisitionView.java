package br.sabor.leme.counter;

import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record RequisitionView(
        long id,
        String partCode,
        String partName,
        int quantity,
        String status,
        String requestedBy,
        String unitCost) {}
