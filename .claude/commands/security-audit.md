Run a security audit on the AslaBot module:

1. **Access Rules Coverage**: For every model in `addons/aslabot/models/`, verify there's a corresponding line in `ir.model.access.csv`. List any gaps.

2. **sudo() Usage**: Search all Python files for `sudo()` calls. Each must have a comment explaining why. Flag any without justification.

3. **SQL Injection**: Search for `cr.execute` or `self.env.cr.execute`. Verify all use parameterized queries `(query, params)` not string formatting.

4. **Credential Exposure**: Search for patterns that might leak secrets: API keys in code, credentials in XML data, tokens in test files, passwords in comments.

5. **Record Rules**: Check if sensitive models (`aslabot.client.registry`, `aslabot.mcp.connection`, `aslabot.operation.log`) have proper record rules restricting cross-client data access.

6. **MCP Permission Tiers**: Verify that FR-4.3 permission tier logic is correctly enforced — no path allows writing to `res.users`, `ir.rule`, or `account.move` without the confirm-then-execute flow.

Report findings as a checklist with PASS / FAIL / WARNING for each item.
