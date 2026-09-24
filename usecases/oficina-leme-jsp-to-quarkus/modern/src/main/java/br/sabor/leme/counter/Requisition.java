package br.sabor.leme.counter;

final class Requisition {
    private final long id;
    private final String partCode;
    private final String partName;
    private final int quantity;
    private final String unitCost;
    private final String requestedBy;
    private String status;

    Requisition(
            long id,
            String partCode,
            String partName,
            int quantity,
            String unitCost,
            String status,
            String requestedBy) {
        this.id = id;
        this.partCode = partCode;
        this.partName = partName;
        this.quantity = quantity;
        this.unitCost = unitCost;
        this.status = status;
        this.requestedBy = requestedBy;
    }

    long id() {
        return id;
    }

    String partCode() {
        return partCode;
    }

    String partName() {
        return partName;
    }

    int quantity() {
        return quantity;
    }

    String unitCost() {
        return unitCost;
    }

    String requestedBy() {
        return requestedBy;
    }

    String status() {
        return status;
    }

    void setStatus(String status) {
        this.status = status;
    }

    RequisitionView view(String role) {
        String cost = "MANAGER".equals(role) ? unitCost : null;
        return new RequisitionView(id, partCode, partName, quantity, status, requestedBy, cost);
    }
}
