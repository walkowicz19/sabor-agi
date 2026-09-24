package br.sabor.leme.jsp.auth;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

public final class LoginServlet extends HttpServlet {
    private final PlainPasswords passwords = new PlainPasswords();
    private final SessionGate sessions = new SessionGate();

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String userId = request.getParameter("userId");
        String password = request.getParameter("password");
        if (!passwords.matches(userId, password)) {
            response.sendRedirect("login.jsp?failed=1");
            return;
        }
        String kept = sessions.accept(request.getRequestedSessionId());
        HttpSession session = request.getSession(true);
        session.setAttribute("acceptedSessionId", kept);
        session.setAttribute("userId", userId);
        session.setAttribute("role", passwords.role(userId));
        response.sendRedirect("counter.jsp");
    }
}
