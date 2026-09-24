package br.sabor.leme.jsp.counter;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class PartCatalog {
    private final Map<String, Part> parts = new LinkedHashMap<String, Part>();

    public PartCatalog() {
        add(new Part("100214", "Brake shoe", 4, "18.50"));
        add(new Part("100088", "Oil filter", 12, "7.40"));
        add(new Part("100331", "V-belt", 1, "22.00"));
        add(new Part("100502", "Cotter pin", 40, "0.35"));
    }

    private void add(Part part) {
        parts.put(part.getCode(), part);
    }

    public Part require(String code) {
        Part part = parts.get(code);
        if (part == null) {
            throw new IllegalArgumentException("Part not found");
        }
        return part;
    }

    public List<Part> all() {
        return new ArrayList<Part>(parts.values());
    }
}
