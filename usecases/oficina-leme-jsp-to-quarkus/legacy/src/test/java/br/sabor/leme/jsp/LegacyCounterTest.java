package br.sabor.leme.jsp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.sabor.leme.jsp.auth.PlainPasswords;
import br.sabor.leme.jsp.auth.SessionGate;
import br.sabor.leme.jsp.counter.Approver;
import br.sabor.leme.jsp.counter.CounterMenu;
import br.sabor.leme.jsp.counter.PartCatalog;
import br.sabor.leme.jsp.counter.PartSearch;
import br.sabor.leme.jsp.counter.Requisition;
import br.sabor.leme.jsp.counter.RequisitionBook;
import org.junit.jupiter.api.Test;

class LegacyCounterTest {
    @Test
    void passwordsAreStoredAsTheTypedCharacters() {
        PlainPasswords passwords = new PlainPasswords();
        assertEquals("135790", passwords.storedPassword("2001"));
        assertTrue(passwords.matches("2001", "135790"));
    }

    @Test
    void signOnKeepsTheSessionIdTheBrowserSent() {
        assertEquals("JSESSIONID-from-the-client", new SessionGate().accept("JSESSIONID-from-the-client"));
    }

    @Test
    void thePageHidesApproveAndTheServletAcceptsAClerk() {
        assertFalse(Approver.pageShowsApprove("CLERK"));
        assertTrue(Approver.servletAccepts("CLERK"));
    }

    @Test
    void searchPastesTheTypedTextIntoSql() {
        PartSearch search = new PartSearch(new PartCatalog());
        String typed = "shoe' OR '1'='1";
        assertTrue(search.sqlFor(typed).contains(typed));
    }

    @Test
    void theServletIssuesMoreThanAreOnHandAndReturnsTheCost() {
        PartCatalog catalog = new PartCatalog();
        RequisitionBook book = new RequisitionBook(catalog);
        assertTrue(RequisitionBook.counterPageWouldRefuse(catalog.require("100331").getOnHand(), 2));
        Requisition row = book.issue("2001", "CLERK", "100331", 2);
        assertEquals(-1, row.getOnHandAfter());
        assertEquals("22.00", book.read(row.getId()).getUnitCost());
    }

    @Test
    void theCounterDoesNotLinkTheBinTransfer() {
        assertFalse(CounterMenu.links().contains("transfer"));
    }
}
