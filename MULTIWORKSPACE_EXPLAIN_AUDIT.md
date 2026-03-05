# Auditoria EXPLAIN - Multiworkspace

- Gerado em: `2026-03-05T12:22:00Z`
- Banco alvo: `sqlite`

## accounts_by_workspace

```sql
SELECT id, name, type, currency FROM accounts WHERE workspace_id = ? ORDER BY id DESC LIMIT 50
```
Plano:
- SEARCH accounts USING INDEX idx_accounts_workspace (workspace_id=?)

## categories_by_workspace

```sql
SELECT id, name, kind FROM categories WHERE workspace_id = ? ORDER BY id DESC LIMIT 100
```
Plano:
- SEARCH categories USING INDEX idx_categories_workspace (workspace_id=?)

## transactions_recent_by_workspace

```sql
SELECT id, date, account_id, category_id FROM transactions WHERE workspace_id = ? ORDER BY date DESC, id DESC LIMIT 200
```
Plano:
- SEARCH transactions USING INDEX idx_transactions_workspace (workspace_id=?)
- USE TEMP B-TREE FOR ORDER BY

## open_invoices_by_workspace

```sql
SELECT i.id, i.card_id, i.invoice_period, i.due_date FROM credit_card_invoices i JOIN credit_cards c ON c.id = i.card_id AND c.workspace_id = i.workspace_id WHERE i.workspace_id = ? AND i.status = 'OPEN' ORDER BY i.due_date ASC LIMIT 100
```
Plano:
- SEARCH i USING INDEX idx_credit_card_invoices_workspace (workspace_id=?)
- SEARCH c USING COVERING INDEX idx_credit_cards_workspace (workspace_id=? AND rowid=?)
- USE TEMP B-TREE FOR ORDER BY

## assets_by_workspace

```sql
SELECT id, symbol, asset_class, current_value FROM assets WHERE workspace_id = ? ORDER BY id DESC LIMIT 200
```
Plano:
- SEARCH assets USING INDEX idx_assets_workspace (workspace_id=?)

## trades_recent_by_workspace

```sql
SELECT id, asset_id, date, side FROM trades WHERE workspace_id = ? ORDER BY date DESC, id DESC LIMIT 200
```
Plano:
- SEARCH trades USING INDEX idx_trades_workspace (workspace_id=?)
- USE TEMP B-TREE FOR ORDER BY

## prices_recent_by_workspace

```sql
SELECT id, asset_id, date, price FROM prices WHERE workspace_id = ? ORDER BY date DESC, id DESC LIMIT 200
```
Plano:
- SEARCH prices USING INDEX idx_prices_workspace (workspace_id=?)
- USE TEMP B-TREE FOR ORDER BY

## workspace_members

```sql
SELECT user_id, role FROM workspace_users WHERE workspace_id = ? ORDER BY user_id
```
Plano:
- SEARCH workspace_users USING INDEX ux_workspace_users_workspace_user (workspace_id=?)

## permissions_by_workspace_user

```sql
SELECT module, can_view, can_add, can_edit, can_delete FROM permissions WHERE workspace_user_id = ? ORDER BY module
```
Plano:
- SEARCH permissions USING INDEX ux_permissions_workspace_user_module (workspace_user_id=?)
