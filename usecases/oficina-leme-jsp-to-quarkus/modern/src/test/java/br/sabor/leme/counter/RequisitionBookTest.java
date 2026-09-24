package br.sabor.leme.counter;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.sabor.leme.ApiException;
import org.junit.jupiter.api.Test;

class RequisitionBookTest {
    @Test
    void approveRefusesToDriveOnHandBelowZero() {
        PartCatalog catalog = new PartCatalog();
        RequisitionBook book = new RequisitionBook(catalog);
        RequisitionView opened = book.create("2001", "CLERK", "100331", 2);
        ApiException error = assertThrows(ApiException.class, () -> book.approve("MANAGER", opened.id()));
        assertEquals(409, error.status());
        assertEquals(1, catalog.onHand("100331"));
        assertEquals("PENDING", book.read("3001", "MANAGER", opened.id()).status());
    }

    @Test
    void aClerkCannotReadAnotherClerksRequisitionOrItsCost() {
        PartCatalog catalog = new PartCatalog();
        RequisitionBook book = new RequisitionBook(catalog);
        RequisitionView opened = book.create("2001", "CLERK", "100214", 1);
        ApiException hidden = assertThrows(ApiException.class, () -> book.read("2002", "CLERK", opened.id()));
        assertEquals(404, hidden.status());
        assertEquals(null, book.read("2001", "CLERK", opened.id()).unitCost());
        assertEquals("18.50", book.read("3001", "MANAGER", opened.id()).unitCost());
    }
}
