package br.sabor.leme.jsp.counter;

public final class Requisition {
    private final long id;
    private final String partCode;
    private final String requestedBy;
    private final int quantity;
    private final String unitCost;
    private final int onHandAfter;

    public Requisition(long id, String partCode, String requestedBy, int quantity, String unitCost, int onHandAfter) {
        this.id = id;
        this.partCode = partCode;
        this.requestedBy = requestedBy;
        this.quantity = quantity;
        this.unitCost = unitCost;
        this.onHandAfter = onHandAfter;
    }

    public long getId() {
        return id;
    }

    public String getPartCode() {
        return partCode;
    }

    public String getRequestedBy() {
        return requestedBy;
    }

    public int getQuantity() {
        return quantity;
    }

    public String getUnitCost() {
        return unitCost;
    }

    public int getOnHandAfter() {
        return onHandAfter;
    }
}
