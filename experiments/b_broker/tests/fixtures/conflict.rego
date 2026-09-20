package broker
import rego.v1
default decision := {"decision": "deny", "reason": "scope_denied"}
decision := {"decision": "allow", "reason": "authorized"} if { input.action.type == "order.create" }
decision := {"decision": "deny", "reason": "scope_denied"} if { input.action.quantity == 1 }
