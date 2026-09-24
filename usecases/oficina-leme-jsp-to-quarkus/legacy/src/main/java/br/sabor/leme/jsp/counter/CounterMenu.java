package br.sabor.leme.jsp.counter;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class CounterMenu {
    private CounterMenu() {}

    public static List<String> links() {
        return Collections.unmodifiableList(Arrays.asList("search", "issue", "exit"));
    }
}
