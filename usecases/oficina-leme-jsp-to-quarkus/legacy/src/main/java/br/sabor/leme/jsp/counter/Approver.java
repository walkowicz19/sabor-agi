package br.sabor.leme.jsp.counter;

/** The page and the servlet do not ask the same question. */
public final class Approver {
    private Approver() {}

    public static boolean pageShowsApprove(String role) {
        return "MANAGER".equals(role);
    }

    public static boolean servletAccepts(String role) {
        return role != null && role.trim().length() > 0;
    }
}
