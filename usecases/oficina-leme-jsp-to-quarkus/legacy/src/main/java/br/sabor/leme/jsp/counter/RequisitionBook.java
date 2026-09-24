package br.sabor.leme.jsp.counter;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Issues stock immediately. The counter page refuses a quantity above on-hand.
 * This method does not.
 */
public final class RequisitionBook {
    private final PartCatalog catalog;
    private final Map<Long, Requisition> rows = new LinkedHashMap<Long, Requisition>();
    private long nextId = 1L;

    public RequisitionBook(PartCatalog catalog) {
        this.catalog = catalog;
    }

    public static boolean counterPageWouldRefuse(int onHand, int quantity) {
        return quantity > onHand;
    }

    public Requisition issue(String userId, String role, String partCode, int quantity) {
        if (!Approver.servletAccepts(role)) {
            throw new IllegalStateException("Sign-on required");
        }
        Part part = catalog.require(partCode);
        part.setOnHand(part.getOnHand() - quantity);
        Requisition row = new Requisition(
                nextId++, partCode, userId, quantity, part.getUnitCost(), part.getOnHand());
        rows.put(row.getId(), row);
        return row;
    }

    public Requisition read(long id) {
        Requisition row = rows.get(id);
        if (row == null) {
            throw new IllegalArgumentException("Requisition not found");
        }
        return row;
    }
}
