package br.sabor.leme.counter;

import br.sabor.leme.ApiException;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@ApplicationScoped
public class PartCatalog {
    private final Object lock = new Object();
    private final Map<String, Part> parts = new LinkedHashMap<>();

    public PartCatalog() {
        reseed();
    }

    public Object lock() {
        return lock;
    }

    public void reseed() {
        synchronized (lock) {
            parts.clear();
            add(new Part("100214", "Brake shoe", 4, "18.50"));
            add(new Part("100088", "Oil filter", 12, "7.40"));
            add(new Part("100331", "V-belt", 1, "22.00"));
            add(new Part("100502", "Cotter pin", 40, "0.35"));
        }
    }

    private void add(Part part) {
        parts.put(part.code(), part);
    }

    public List<PartView> find(String query, String role) {
        String typed = query == null ? "" : query.trim();
        if (typed.length() > 40) {
            throw new ApiException(400, "Search is at most 40 characters");
        }
        String needle = typed.toLowerCase(Locale.ROOT);
        synchronized (lock) {
            return parts.values().stream()
                    .filter(part -> needle.isEmpty()
                            || part.code().equals(typed)
                            || part.name().toLowerCase(Locale.ROOT).contains(needle))
                    .sorted(Comparator.comparing(Part::code))
                    .map(part -> view(part, role))
                    .toList();
        }
    }

    public Part require(String code) {
        synchronized (lock) {
            Part part = parts.get(code);
            if (part == null) {
                throw new ApiException(404, "Part not found");
            }
            return part;
        }
    }

    public void issue(String code, int quantity) {
        synchronized (lock) {
            Part part = parts.get(code);
            if (part == null) {
                throw new ApiException(404, "Part not found");
            }
            if (quantity > part.onHand()) {
                throw new ApiException(409, "Not enough on hand");
            }
            part.decrease(quantity);
        }
    }

    public int onHand(String code) {
        return require(code).onHand();
    }

    private static PartView view(Part part, String role) {
        String cost = "MANAGER".equals(role) ? part.unitCost() : null;
        return new PartView(part.code(), part.name(), part.onHand(), cost);
    }
}
