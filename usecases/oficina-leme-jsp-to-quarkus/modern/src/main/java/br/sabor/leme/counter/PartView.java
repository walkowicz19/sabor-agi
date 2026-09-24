package br.sabor.leme.counter;

import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record PartView(String code, String name, int onHand, String unitCost) {}
