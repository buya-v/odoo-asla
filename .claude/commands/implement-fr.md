Implement a specific functional requirement from the AslaBot FRD.

Ask me for the FR number (e.g., FR-3.1) or I can provide it as an argument: `/implement-fr FR-3.1`

Then:

1. Read `docs/FRD.md` to find the exact requirement text
2. Analyze what models, views, and logic are needed
3. Check what already exists in the codebase that relates to this FR
4. Create a brief implementation plan and confirm with me before coding
5. Implement the requirement with:
   - Model changes (if needed)
   - View changes (if needed)
   - Business logic
   - Security rules
   - Tests covering the requirement
6. Run tests: `odoo-bin -d asla_dev --test-tags /aslabot --stop-after-init`
7. Run lint: `ruff check addons/aslabot/`
8. Commit with: `git add -A && git commit -m "feat(aslabot): implement FR-X.X — [description]"`

Always reference the FR number in code comments where the logic directly implements a requirement.
