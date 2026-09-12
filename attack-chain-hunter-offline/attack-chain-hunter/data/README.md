# Local Scenario Data

Each JSON file in `scenarios/` is a complete synthetic incident fixture. It includes the alert, packet metadata, assets, vulnerabilities, server logs, identity state, network state, service health, attack graph, failure condition, expected recovery, and verification target. Keeping the fixture together makes replay deterministic and keeps the demo independent of network-connected sources.
