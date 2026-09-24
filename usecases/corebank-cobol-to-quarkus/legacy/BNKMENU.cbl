      ******************************************************************
      * PROGRAM-ID. BNKMENU
      * DATE-WRITTEN. 2003-04-17
      * BRANCH TELLER MENU AND CUSTOMER REGISTRATION.
      * FICTIONAL TRAINING FIXTURE. NOT A REAL BANK. NO DOCS SHIPPED.
      * KNOWN ROT, LEFT AS IT WAS:
      *   PINS STORED AND COMPARED IN PLAINTEXT.
      *   OPERATOR 9999 / ADMIN SIGNS ON WITHOUT A FILE LOOKUP.
      *   INQUIRY DOES NOT CHECK THE SIGN-ON FLAG.
      *   TWO NAME CHECKS DISAGREE. THE SECOND ONE ALLOWS BLANKS.
      *   7000-WIRE-TRANSFER IS NEVER REACHED FROM THE MENU.
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. BNKMENU.
       AUTHOR. BRANCH-OPS.
       DATE-WRITTEN. 2003-04-17.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CUSTMAST ASSIGN TO "CUSTMAST.DAT"
               ORGANIZATION IS LINE SEQUENTIAL.
       DATA DIVISION.
       FILE SECTION.
       FD CUSTMAST.
       01 CUST-REC.
          05 CUST-ID        PIC 9(10).
          05 CUST-NAME      PIC X(40).
          05 BRANCH-CODE    PIC 9(4).
          05 PIN-PLAIN      PIC X(6).
          05 BALANCE        PIC S9(7)V99.
          05 CUST-STATUS    PIC X.
       WORKING-STORAGE SECTION.
       01 WS-CHOICE         PIC 9 VALUE 0.
       01 WS-SIGNED-IN      PIC X VALUE "N".
       01 WS-EOF            PIC X VALUE "N".
       01 WS-FOUND          PIC X VALUE "N".
       01 WS-NAME-OK        PIC X VALUE "N".
       01 WS-OP-ID          PIC 9(4).
       01 WS-OP-PIN         PIC X(6).
       01 WS-IN-ID          PIC 9(10).
       01 WS-IN-NAME        PIC X(40).
       01 WS-IN-BRANCH      PIC 9(4).
       01 WS-IN-PIN         PIC X(6).
       01 WS-OLD-PIN        PIC X(6).
       01 WS-NEW-PIN        PIC X(6).
       01 WS-MSG            PIC X(40).
       PROCEDURE DIVISION.
       MAIN-SECTION.
           PERFORM 1000-SIGN-ON.
           PERFORM UNTIL WS-CHOICE = 9
               PERFORM 2000-SHOW-MENU
               ACCEPT WS-CHOICE
               PERFORM 2100-DISPATCH
           END-PERFORM.
           STOP RUN.

       1000-SIGN-ON.
           DISPLAY "OPERATOR ID:".
           ACCEPT WS-OP-ID.
           DISPLAY "OPERATOR PIN:".
           ACCEPT WS-OP-PIN.
           IF WS-OP-ID = 9999 AND WS-OP-PIN = "ADMIN"
               MOVE "Y" TO WS-SIGNED-IN
               DISPLAY "BACKDOOR SIGN-ON"
           ELSE
               IF WS-OP-ID = 1001 AND WS-OP-PIN = "246810"
                   MOVE "Y" TO WS-SIGNED-IN
               ELSE
                   DISPLAY "SIGN-ON FAILED"
               END-IF
           END-IF.

       2000-SHOW-MENU.
           DISPLAY "1 REGISTER CUSTOMER".
           DISPLAY "2 INQUIRY".
           DISPLAY "3 CHANGE PIN".
           DISPLAY "9 EXIT".

       2100-DISPATCH.
           EVALUATE WS-CHOICE
               WHEN 1
                   PERFORM 3000-REGISTER
               WHEN 2
                   PERFORM 4000-INQUIRY
               WHEN 3
                   PERFORM 5000-CHANGE-PIN
               WHEN 9
                   CONTINUE
               WHEN OTHER
                   DISPLAY "INVALID OPTION"
           END-EVALUATE.

       3000-REGISTER.
           IF WS-SIGNED-IN NOT = "Y"
               DISPLAY "NOT SIGNED ON"
               EXIT PARAGRAPH
           END-IF.
           DISPLAY "CUSTOMER NUMBER (10 DIGITS):".
           ACCEPT WS-IN-ID.
           DISPLAY "NAME:".
           ACCEPT WS-IN-NAME.
           DISPLAY "BRANCH (4 DIGITS):".
           ACCEPT WS-IN-BRANCH.
           DISPLAY "PIN (6 DIGITS):".
           ACCEPT WS-IN-PIN.
           PERFORM 3100-CHECK-NAME.
           PERFORM 3110-VALIDATE-NAME.
           IF WS-NAME-OK NOT = "Y"
               DISPLAY "NAME REJECTED"
               EXIT PARAGRAPH
           END-IF.
           PERFORM 3200-WRITE-CUSTOMER.

       3100-CHECK-NAME.
           IF WS-IN-NAME = SPACES
               MOVE "N" TO WS-NAME-OK
           ELSE
               MOVE "Y" TO WS-NAME-OK
           END-IF.

       3110-VALIDATE-NAME.
      * DUPLICATE OF 3100-CHECK-NAME. THIS COPY ACCEPTS BLANKS.
           MOVE "Y" TO WS-NAME-OK.

       3200-WRITE-CUSTOMER.
           OPEN EXTEND CUSTMAST.
           MOVE WS-IN-ID TO CUST-ID.
           MOVE WS-IN-NAME TO CUST-NAME.
           MOVE WS-IN-BRANCH TO BRANCH-CODE.
           MOVE WS-IN-PIN TO PIN-PLAIN.
           MOVE 0 TO BALANCE.
           MOVE "A" TO CUST-STATUS.
           WRITE CUST-REC.
           CLOSE CUSTMAST.
           DISPLAY "REGISTERED".

       4000-INQUIRY.
      * DOES NOT CHECK WS-SIGNED-IN.
           DISPLAY "CUSTOMER NUMBER:".
           ACCEPT WS-IN-ID.
           MOVE "N" TO WS-FOUND.
           MOVE "N" TO WS-EOF.
           OPEN INPUT CUSTMAST.
           PERFORM UNTIL WS-EOF = "Y" OR WS-FOUND = "Y"
               READ CUSTMAST
                   AT END MOVE "Y" TO WS-EOF
                   NOT AT END
                       IF CUST-ID = WS-IN-ID
                           MOVE "Y" TO WS-FOUND
                           DISPLAY CUST-NAME
                           DISPLAY PIN-PLAIN
                           DISPLAY BALANCE
                       END-IF
               END-READ
           END-PERFORM.
           CLOSE CUSTMAST.
           IF WS-FOUND NOT = "Y"
               DISPLAY "NOT FOUND"
           END-IF.

       5000-CHANGE-PIN.
           IF WS-SIGNED-IN NOT = "Y"
               DISPLAY "NOT SIGNED ON"
               EXIT PARAGRAPH
           END-IF.
           DISPLAY "CUSTOMER NUMBER:".
           ACCEPT WS-IN-ID.
           DISPLAY "OLD PIN:".
           ACCEPT WS-OLD-PIN.
           DISPLAY "NEW PIN:".
           ACCEPT WS-NEW-PIN.
           MOVE "REWRITE NOT IMPLEMENTED" TO WS-MSG.
           DISPLAY WS-MSG.

       7000-WIRE-TRANSFER.
      * DEAD. OPTION 7 IS NOT ON THE MENU AND NEVER PERFORMS THIS.
           MOVE "WIRE FEE" TO WS-MSG.
           SUBTRACT 15 FROM BALANCE.
           SUBTRACT 15 FROM BALANCE.
           DISPLAY WS-MSG.
