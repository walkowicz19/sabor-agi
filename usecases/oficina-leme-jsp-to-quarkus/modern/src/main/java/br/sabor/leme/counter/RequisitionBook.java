package br.sabor.leme.counter;

import br.sabor.leme.ApiException;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@ApplicationScoped
public class RequisitionBook {
    private final PartCatalog catalog;
    private final Map<Long, Requisition> rows = new LinkedHashMap<>();
    private long nextId = 1L;

    @Inject
    public RequisitionBook(PartCatalog catalog) {
        this.catalog = catalog;
    }

    public void clear() {
        synchronized (catalog.lock()) {
            rows.clear();
            nextId = 1L;
        }
    }

    public RequisitionView create(String userId, String role, String partCode, int quantity) {
        if (!"CLERK".equals(role)) {
            throw new ApiException(403, "Only a clerk can open a requisition");
        }
        if (partCode == null || !partCode.matches("\\d{6}")) {
            throw new ApiException(400, "Part code must be 6 digits");
        }
        if (quantity < 1 || quantity > 99) {
            throw new ApiException(400, "Quantity must be from 1 to 99");
        }
        synchronized (catalog.lock()) {
            Part part = catalog.require(partCode);
            Requisition row = new Requisition(
                    nextId++, part.code(), part.name(), quantity, part.unitCost(), "PENDING", userId);
            rows.put(row.id(), row);
            return row.view(role);
        }
    }

    public List<RequisitionView> list(String userId, String role) {
        synchronized (catalog.lock()) {
            return rows.values().stream()
                    .filter(row -> visible(userId, role, row))
                    .sorted(Comparator.comparingLong(Requisition::id))
                    .map(row -> row.view(role))
                    .toList();
        }
    }

    public RequisitionView read(String userId, String role, long id) {
        synchronized (catalog.lock()) {
            return visibleRow(userId, role, id).view(role);
        }
    }

    public RequisitionView approve(String role, long id) {
        if (!"MANAGER".equals(role)) {
            throw new ApiException(403, "Only a manager can approve");
        }
        synchronized (catalog.lock()) {
            Requisition row = require(id);
            if (!"PENDING".equals(row.status())) {
                throw new ApiException(409, "Requisition is not pending");
            }
            catalog.issue(row.partCode(), row.quantity());
            row.setStatus("APPROVED");
            return row.view(role);
        }
    }

    public RequisitionView reject(String role, long id) {
        if (!"MANAGER".equals(role)) {
            throw new ApiException(403, "Only a manager can reject");
        }
        synchronized (catalog.lock()) {
            Requisition row = require(id);
            if (!"PENDING".equals(row.status())) {
                throw new ApiException(409, "Requisition is not pending");
            }
            row.setStatus("REJECTED");
            return row.view(role);
        }
    }

    private Requisition visibleRow(String userId, String role, long id) {
        Requisition row = rows.get(id);
        if (row == null || !visible(userId, role, row)) {
            throw new ApiException(404, "Requisition not found");
        }
        return row;
    }

    private Requisition require(long id) {
        Requisition row = rows.get(id);
        if (row == null) {
            throw new ApiException(404, "Requisition not found");
        }
        return row;
    }

    private static boolean visible(String userId, String role, Requisition row) {
        return "MANAGER".equals(role) || row.requestedBy().equals(userId);
    }
}
