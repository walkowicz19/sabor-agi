package br.sabor.leme.jsp.counter;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** The name search is assembled as SQL text. */
public final class PartSearch {
    private final PartCatalog catalog;

    public PartSearch(PartCatalog catalog) {
        this.catalog = catalog;
    }

    public String sqlFor(String typed) {
        return "SELECT code, name, on_hand, unit_cost FROM parts WHERE name LIKE '%" + typed + "%'";
    }

    public List<Part> find(String typed) {
        String sql = sqlFor(typed == null ? "" : typed);
        String needle = between(sql, "LIKE '%", "%'").toLowerCase(Locale.ROOT);
        List<Part> found = new ArrayList<Part>();
        for (Part part : catalog.all()) {
            if (needle.length() == 0 || part.getName().toLowerCase(Locale.ROOT).contains(needle)) {
                found.add(part);
            }
        }
        return found;
    }

    private static String between(String sql, String open, String close) {
        int start = sql.indexOf(open);
        int end = sql.lastIndexOf(close);
        if (start < 0 || end < start) {
            return "";
        }
        return sql.substring(start + open.length(), end);
    }
}
