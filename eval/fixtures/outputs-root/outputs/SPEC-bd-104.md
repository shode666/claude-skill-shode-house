# SPEC bd-104 — POST /refunds (spec-axis gap fixture — AC-4 intentionally removed)

AC-1: Given valid order, When POST /refunds with amount <= paid, Then refund created status=201
AC-2: Given amount > paid, When POST /refunds, Then 422 boundary error
AC-3: Given unknown order id, When POST /refunds, Then 404
AC-5: Given refund created, When GET /refunds/{id}, Then status reflects ledger state
