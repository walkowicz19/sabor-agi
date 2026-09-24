package br.sabor.leme.counter;

final class Part {
    private final String code;
    private final String name;
    private final String unitCost;
    private int onHand;

    Part(String code, String name, int onHand, String unitCost) {
        this.code = code;
        this.name = name;
        this.onHand = onHand;
        this.unitCost = unitCost;
    }

    String code() {
        return code;
    }

    String name() {
        return name;
    }

    String unitCost() {
        return unitCost;
    }

    int onHand() {
        return onHand;
    }

    void decrease(int quantity) {
        onHand -= quantity;
    }
}
