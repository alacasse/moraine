package system.authz
import rego.v1

default allow := false
allow if {
    input.identity == data.broker_private.token
    input.method == "GET"
    input.path == ["health"]
}
allow if {
    input.identity == data.broker_private.token
    input.method == "POST"
    input.path == ["v1", "data", "broker", "decision"]
    input.params == {"strict-builtin-errors": ["true"]}
}
