package broker
import rego.v1
default decision := {"decision": "deny", "reason": "scope_denied"}
decision := true if { input.action.type == "order.create" }
