<%@ page contentType="text/html; charset=UTF-8" %>
<%@ page import="br.sabor.leme.jsp.counter.Approver" %>
<%@ page import="br.sabor.leme.jsp.counter.CounterMenu" %>
<%@ page import="br.sabor.leme.jsp.counter.PartCatalog" %>
<%@ page import="br.sabor.leme.jsp.counter.RequisitionBook" %>
<%
    String role = (String) session.getAttribute("role");
    PartCatalog catalog = new PartCatalog();
    int onHand = catalog.require("100331").getOnHand();
    boolean blocked = RequisitionBook.counterPageWouldRefuse(onHand, 2);
%>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Oficina Leme counter</title>
</head>
<body>
    <h1>Counter</h1>
    <ul>
        <% for (String link : CounterMenu.links()) { %>
        <li><%= link %></li>
        <% } %>
    </ul>
    <% if (blocked) { %>
    <p>The page will not issue 2 of 100331. On hand is <%= onHand %>.</p>
    <% } %>
    <% if (Approver.pageShowsApprove(role)) { %>
    <form method="post" action="requisitions">
        <input type="hidden" name="partCode" value="100331">
        <input type="hidden" name="quantity" value="2">
        <button type="submit">Approve issue</button>
    </form>
    <% } %>
</body>
</html>
