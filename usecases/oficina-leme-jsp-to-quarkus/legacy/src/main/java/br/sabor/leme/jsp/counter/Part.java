package br.sabor.leme.jsp.counter;

public final class Part {
    private final String code;
    private final String name;
    private final String unitCost;
    private int onHand;

    public Part(String code, String name, int onHand, String unitCost) {
        this.code = code;
        this.name = name;
        this.onHand = onHand;
        this.unitCost = unitCost;
    }

    public String getCode() {
        return code;
    }

    public String getName() {
        return name;
    }

    public String getUnitCost() {
        return unitCost;
    }

    public int getOnHand() {
        return onHand;
    }

    public void setOnHand(int onHand) {
        this.onHand = onHand;
    }
}
