package broker_test
import rego.v1
import data.broker

base := {
    "phase": "preflight", "now": 100,
    "subject": {"principal": "agent:alice", "account": "alice"},
    "grant": {"owner": "human:alice", "agent": "agent:alice", "account": "alice", "revoked": false,
              "expires_at": 400, "recipients": ["trusted@example.test"], "document_ids": ["public-note"],
              "merchants": ["shop.test"], "currency": "CAD", "auto_limit_minor": 1000, "hard_limit_minor": 5000},
    "action": {"type": "order.create", "account": "alice", "merchant": "shop.test", "currency": "CAD",
               "shipping_address_id": "home", "recurring": false, "quantity": 1, "amount_minor": 500},
    "policy_revision": "p1", "snapshot": null, "approval": null,
}
email := {"type": "email.send", "account": "alice", "to": ["trusted@example.test"], "cc": [], "bcc": [],
          "attachments": [{"id": "public-note", "version": 1}]}
read := {"type": "document.read", "account": "alice", "document_id": "public-note"}

check_action(changes) := result if {
    action := object.union(base.action, changes)
    result := broker.decision with input as object.union(base, {"action": action})
}

test_default_deny if {
    result := broker.decision with input as {}
    result.decision == "deny"
}
test_order_boundaries if {
    check_action({"amount_minor": 1000}).decision == "allow"
    check_action({"amount_minor": 1001}).decision == "review"
    check_action({"amount_minor": 5000}).decision == "review"
    check_action({"amount_minor": 5001}).decision == "deny"
}
test_order_scope_and_types if {
    every changes in [{"amount_minor": 0}, {"amount_minor": -1}, {"amount_minor": true},
                      {"amount_minor": "500"}, {"amount_minor": 1.5}, {"quantity": 0}, {"quantity": false},
                      {"merchant": "evil"}, {"currency": "USD"}, {"shipping_address_id": "away"}, {"recurring": true}] {
        check_action(changes).decision == "deny"
    }
}
test_email_review if {
    result := broker.decision with input as object.union(base, {"action": email})
    result.decision == "review"
}
test_each_recipient_field if {
    every field in ["to", "cc", "bcc"] {
        action := object.union(email, {field: ["evil@example.test"]})
        result := broker.decision with input as object.union(base, {"action": action})
        result.decision == "deny"
    }
}
test_empty_recipients if {
    action := object.union(email, {"to": []})
    result := broker.decision with input as object.union(base, {"action": action})
    result.decision == "deny"
}
test_attachment_scope if {
    action := object.union(email, {"attachments": [{"id": "tax-return", "version": 1}]})
    result := broker.decision with input as object.union(base, {"action": action})
    result.decision == "deny"
}
test_read_scope if {
    allowed := broker.decision with input as object.union(base, {"action": read})
    denied := broker.decision with input as object.union(base, {"action": object.union(read, {"document_id": "tax-return"})})
    allowed.decision == "allow"
    denied.decision == "deny"
}
test_bindings_and_grant_lifetime if {
    every changes in [{"revoked": true}, {"expires_at": 100}, {"owner": "human:bob"},
                      {"agent": "agent:bob"}, {"account": "bob"}] {
        grant := object.union(base.grant, changes)
        result := broker.decision with input as object.union(base, {"grant": grant})
        result.decision == "deny"
    }
    check_action({"account": "bob"}).decision == "deny"
}

execute := object.union(object.remove(base, ["action"]), {
    "phase": "execute", "action": email,
    "snapshot": {"policy_revision": "p1", "prepared_at": 90, "review_expires_at": 300,
                 "prepared_action": email, "action_digest": "d1"},
    "approval": {"human": "human:alice", "action_digest": "d1", "accepted_at": 99, "expires_at": 159},
})
test_approved_execute if {
    result := broker.decision with input as execute
    result.decision == "allow"
}
test_consent_binding_and_age if {
    every changes in [{"human": "human:bob"}, {"action_digest": "wrong"}, {"accepted_at": 101},
                      {"accepted_at": 40}, {"expires_at": 100}] {
        approval := object.union(execute.approval, changes)
        result := broker.decision with input as object.union(execute, {"approval": approval})
        result.decision == "deny"
    }
    missing := broker.decision with input as object.union(execute, {"approval": null})
    missing.decision == "deny"
}
test_snapshot_binding_and_age if {
    every changes in [{"policy_revision": "old"}, {"prepared_at": 101}, {"review_expires_at": 100},
                      {"prepared_action": read}] {
        snapshot := object.union(execute.snapshot, changes)
        result := broker.decision with input as object.union(execute, {"snapshot": snapshot})
        result.decision == "deny"
    }
}
