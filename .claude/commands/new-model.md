Create a new Odoo model for the AslaBot module. Ask me for:

1. Model technical name (e.g., `aslabot.ticket`)
2. Description (human-readable)
3. Key fields needed

Then generate:

1. **Model file** in `addons/aslabot/models/[model_name].py`:
   - Inherit `models.Model`
   - Set `_name`, `_description`, `_order`
   - Include `mail.thread` and `mail.activity.mixin` if it's a document model
   - Add `_logger` import
   - Add all requested fields with proper types and strings
   - Add `name_get` if needed

2. **Update `addons/aslabot/models/__init__.py`** to import the new file

3. **Security line** in `addons/aslabot/security/ir.model.access.csv`:
   - Add read/write/create/unlink for `aslabot.group_asla_user`
   - Add full access for `aslabot.group_asla_admin`

4. **View file** in `addons/aslabot/views/[model_name]_views.xml`:
   - Form view with chatter (if mail.thread)
   - Tree view with key columns
   - Search view with common filters
   - Action and menu item

5. **Update `addons/aslabot/__manifest__.py`** data list with new view and security files

6. **Test stub** in `addons/aslabot/tests/test_[model_name].py`

After generating, run `ruff check addons/aslabot/` to verify.
