package broker
import rego.v1

default decision := {"decision": "deny", "reason": "scope_denied"}

common if {
    input.subject == input.grant.agent
    input.subject == input.trusted.agent
    input.grant.owner == input.trusted.owner
    input.grant.account_id == input.trusted.account
    input.grant.revoked == false
    input.now < input.grant.expires_at
}

read_scope if {
    input.operation == "read"
    input.resource_ref in input.grant.resource_refs
}
read_scope if { input.operation == "list" }

send_scope if {
    input.operation == "reply"
    input.reply_to_ref == input.grant.reply_to_ref
    input.recipient == input.grant.recipient
    input.blocked == false
}

snapshot_valid if {
    input.snapshot.policy_revision == input.policy_revision
    input.snapshot.prepared_at <= input.now
    input.now < input.snapshot.review_expires_at
    input.snapshot.principal == input.subject
    input.snapshot.account_id == input.trusted.account
    input.snapshot.grant_id == input.grant.id
}

consent_valid if {
    snapshot_valid
    input.approval.human == input.trusted.owner
    input.approval.action_digest == input.action_digest
    input.approval.accepted_at <= input.now
    input.now < input.approval.accepted_at + 60
    input.now < input.approval.expires_at
}

decision := {"decision": "allow", "reason": "authorized"} if { common; read_scope }
decision := {"decision": "review", "reason": "requires_approval"} if {
    common; send_scope; input.phase == "preflight"
}
decision := {"decision": "allow", "reason": "approved"} if {
    common; send_scope; input.phase == "execute"; consent_valid
}
