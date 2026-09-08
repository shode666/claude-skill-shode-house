# SPEC bd-101 — POST /refunds

AC-1: Given valid order, When POST /refunds with amount <= paid, Then refund created status=201
AC-2: Given amount > paid, When POST /refunds, Then 422 boundary error
AC-3: Given unknown order id, When POST /refunds, Then 404
AC-4: Given duplicate request-id, When POST /refunds called twice, Then idempotent — second call returns first result, no double refund
AC-5: Given refund created, When GET /refunds/{id}, Then status reflects ledger state
