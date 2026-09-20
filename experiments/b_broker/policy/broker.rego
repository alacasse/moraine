package broker
import rego.v1

default decision := {"decision": "deny", "reason": "scope_denied"}

valid_integer(n) if { is_number(n); n == floor(n); n > 0; n <= 9007199254740991 }

common if {
    input.phase in {"preflight", "execute"}
    input.subject.principal == input.grant.agent
    input.subject.account == input.grant.account
    input.action.account == input.grant.account
    input.grant.owner == "human:alice"
    input.grant.agent == "agent:alice"
    input.grant.account == "alice"
    input.grant.revoked == false
    input.now < input.grant.expires_at
}

email_scope if {
    input.action.type == "email.send"
    recipients := array.concat(array.concat(input.action.to, input.action.cc), input.action.bcc)
    count(recipients) > 0
    every recipient in recipients { recipient in input.grant.recipients }
    every attachment in input.action.attachments {
        attachment.id in input.grant.document_ids
        valid_integer(attachment.version)
    }
}

order_scope if {
    input.action.type == "order.create"
    input.action.merchant in input.grant.merchants
    input.action.currency == input.grant.currency
    input.action.shipping_address_id == "home"
    input.action.recurring == false
    valid_integer(input.action.quantity)
    valid_integer(input.action.amount_minor)
    input.action.amount_minor <= input.grant.hard_limit_minor
}

read_scope if {
    input.action.type == "document.read"
    input.action.document_id in input.grant.document_ids
}

needs_review if { email_scope }
needs_review if { order_scope; input.action.amount_minor > input.grant.auto_limit_minor }
automatic if { order_scope; input.action.amount_minor <= input.grant.auto_limit_minor }
automatic if { read_scope }

snapshot_valid if {
    input.snapshot.policy_revision == input.policy_revision
    input.snapshot.prepared_at <= input.now
    input.now < input.snapshot.review_expires_at
    input.snapshot.prepared_action == input.action
}

consent_valid if {
    snapshot_valid
    input.approval.human == input.grant.owner
    input.approval.action_digest == input.snapshot.action_digest
    input.approval.accepted_at <= input.now
    input.now < input.approval.accepted_at + 60
    input.now < input.approval.expires_at
}

decision := {"decision": "review", "reason": "requires_approval"} if {
    common; input.phase == "preflight"; needs_review
}
decision := {"decision": "allow", "reason": "authorized"} if {
    common; input.phase == "preflight"; automatic
}
decision := {"decision": "allow", "reason": "authorized"} if {
    common; input.phase == "execute"; automatic; snapshot_valid
}
decision := {"decision": "allow", "reason": "approved"} if {
    common; input.phase == "execute"; needs_review; consent_valid
}
