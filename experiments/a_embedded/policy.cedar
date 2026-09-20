// Context is constructed by ExecutionGate, from authenticated identity and SQLite grants.
forbid(principal, action, resource)
when {
    principal != context.grant_agent || resource != context.grant_account ||
    context.revoked || context.now >= context.expires_at
};

permit(principal, action == Action::"email.send", resource)
when {
    !context.recipients.isEmpty() &&
    context.allowed_recipients.containsAll(context.recipients) &&
    context.allowed_documents.containsAll(context.attachment_ids)
};

permit(principal, action == Action::"order.create", resource)
when {
    context.allowed_merchants.contains(context.merchant) &&
    context.currency == context.allowed_currency &&
    context.quantity > 0 && context.amount_minor > 0 &&
    context.amount_minor <= context.hard_limit_minor &&
    context.shipping_address_id == "home" && !context.recurring
};

permit(principal, action == Action::"document.read", resource)
when { context.allowed_documents.contains(context.document_id) };
