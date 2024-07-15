# ai4scion-topo-simulation
Test framework to simulate scion traffic over multiple paths to train agents

## Usage

```python
# Sample ASNs
asns = [47377, 12392] 
graph = load_topology('output_fixed.json')
print("Loaded Topology")
print("Nodes:", len(graph.nodes))
print("Edges:", len(graph.edges))

# Get random combination of ASes
res = [(a, b) for idx, a in enumerate(asns) for b in asns[idx + 1:]]
for elem in res:

    src_asn = elem[0]
    dst_asn = elem[1]
    
    # Get all SCION paths, adjust cut depending on topology/number of paths
    result = get_scion_paths(graph, src_asn, dst_asn)

    # Debug statements
    print_scion_paths(result[:2])
    print_scion_paths_extended(result[:2])

    # Simulate traffic using the first two paths and a 50/50 distribution
    distribution = [0.5, 0.5]
    selected_path_set = result[:2]
    sim_result = simulate_scion_traffic(src_asn, dst_asn, selected_path_set, distribution)

    i = 0
    print("Results:")
    for res in sim_result:
        print(f"Path {i + 1}: Latency {res['latency']}, Loss {res['loss']}, Goodput {res['goodput']}")
        i += 1
```