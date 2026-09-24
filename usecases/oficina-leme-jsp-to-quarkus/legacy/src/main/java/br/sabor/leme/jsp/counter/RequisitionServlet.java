package br.sabor.leme.jsp.counter;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

public final class RequisitionServlet extends HttpServlet {
    private final RequisitionBook book = new RequisitionBook(new PartCatalog());

    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        HttpSession session = request.getSession(false);
        if (session == null || !Approver.servletAccepts((String) session.getAttribute("role"))) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED);
            return;
        }
        long id = Long.parseLong(request.getParameter("id"));
        Requisition row = book.read(id);
        response.setContentType("text/plain; charset=UTF-8");
        response.getWriter().print(row.getId() + " " + row.getPartCode() + " cost " + row.getUnitCost());
    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        HttpSession session = request.getSession(false);
        String role = session == null ? null : (String) session.getAttribute("role");
        if (!Approver.servletAccepts(role)) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED);
            return;
        }
        String userId = (String) session.getAttribute("userId");
        String partCode = request.getParameter("partCode");
        int quantity = Integer.parseInt(request.getParameter("quantity"));
        Requisition row = book.issue(userId, role, partCode, quantity);
        response.sendRedirect("counter.jsp?issued=" + row.getId());
    }
}
