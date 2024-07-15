import subprocess
import random
import json
import networkx as nx
from collections import defaultdict


def load_topology(filename):
    # Load the JSON data from the file
    with open(filename, 'r') as file:
        data = json.load(file)

    # Create a new multigraph
    G = nx.MultiGraph()

    # Add nodes to the graph from the 'ases' section of the JSON
    for as_info in data['ases']:
        G.add_node(as_info['asn'], isd=as_info['isd'], intfs=as_info['intfs'])

    # Map interfaces to ASes for connecting edges
    interface_to_asn = {}
    for as_info in data['ases']:
        asn = as_info['asn']
        for intf in as_info['intfs']:
            interface_to_asn[intf] = asn

    # Add edges to the graph from the 'links' section of the JSON
    for link in data['links']:
        from_asn = interface_to_asn[link['from']]
        to_asn = interface_to_asn[link['to']]
        G.add_edge(from_asn, to_asn, capacity=link['cap'], key=link["id"], latency=link['latency'], packet_loss=link['packet_loss'])

    return G

def limit_path_entries(paths, max_count=3):
    """
    Limits the number of identical paths to max_count.
    """
    path_counts = defaultdict(int)
    limited_paths = []
    
    for path in paths:
        # print(path)
        path_tuple = tuple(path)
        if path_counts[path_tuple] < max_count:
            path_counts[path_tuple] += 1
            limited_paths.append(path)
    
    return limited_paths

def unique_edge_paths(paths, G):
    """
    Converts a list of paths (list of node ids) to a list of edge paths (list of edges),
    ensuring different edges are used if there are multiple paths between the same nodes.
    """
    limited_paths = limit_path_entries(paths)
    edge_paths = []
    edge_usage = defaultdict(int)
    
    for path in limited_paths:
        edge_path = []
        for i in range(len(path) - 1):
            source, target = path[i], path[i+1]
            all_edges = list(G.edges(source, target, keys=True))
           
            if not all_edges:
                raise ValueError(f"No edge found between {source} and {target}")
            
            newEdges = []
            for edge in all_edges:
                if edge[0] == source and edge[1] == target:
                    newEdges.append(edge)

            edge_index = edge_usage[(source, target)]
            edge = all_edges[edge_index % len(all_edges)]
            edge_path.append((source, target, edge[2]))
            edge_usage[(source, target)] += 1
        
        edge_paths.append(edge_path)

    return edge_paths

def unique_scion_paths(paths, G):
    """
    Converts a list of paths (list of node ids) to a list of edge paths (list of edges),
    ensuring different edges are used if there are multiple paths between the same nodes.
    """
    limited_paths = limit_path_entries(paths)
    edge_paths = []
    edge_usage = defaultdict(int)
    
    for path in limited_paths:
        edge_path = []
        for i in range(len(path) - 1):
            source, target = path[i], path[i+1]
            all_edges = list(G.edges(source, target, keys=True))
           
            
            if not all_edges:
                raise ValueError(f"No edge found between {source} and {target}")
            
            newEdges = []
            for edge in all_edges:
                if edge[0] == source and edge[1] == target:
                    newEdges.append(edge)

            edge_index = edge_usage[(source, target)]
            edge = all_edges[edge_index % len(all_edges)]
            parts = edge[2].split(",")
            fromId = parts[0].split("-")[2]
            toId = parts[1].split("-")[2]

            if f"{source}" in parts[1]:
                fromId = parts[1].split("-")[2]
                toId = parts[0].split("-")[2]
            edge_data = G.get_edge_data(edge[0], edge[1], edge[2])
            scion_edge = {
                'from': source,
                'to': target,
                'link': edge[2],
                'from_id': fromId,
                'to_id': toId,
                'capacity':edge_data['capacity'],
                'latency': edge_data['latency'],
                'packet_loss': edge_data['packet_loss'],
            }
            edge_path.append(scion_edge)
            edge_usage[(source, target)] += 1
        
        edge_paths.append(edge_path)
    
    return edge_paths

def print_scion_paths(paths):

    for i, path in enumerate(paths):
        print(f"Path {i + 1} ({len(path)} hops):")
        str = ""
        last_edge_from = ""
        for edge in path:
            if last_edge_from != edge['from']:
                str += f"  {edge['from']} "
            str += f"{edge['from_id']}>{edge['to_id']}  {edge['to']}  "
            last_edge_from = edge['to']
        print(str)
        print("")

def print_scion_paths_extended(paths):
    for i, path in enumerate(paths):
        print(f"Path {i + 1} ({len(path)} hops):")
        for edge in path:
            print(f"  {edge['from']} {edge['from_id']} -> {edge['to']} {edge['to_id']}")
            print(f"    - Capacity: {edge['capacity']}")
            print(f"    - Latency: {edge['latency']}")
            print(f"    - Packet Loss: {edge['packet_loss']}")

def get_scion_paths(graph, src_asn, dst_asn, cut=5000):
    # Find all paths between the source and destination ASes
    print(f"Finding paths between {src_asn} and {dst_asn}")
    shortest = nx.shortest_path_length(graph, src_asn, dst_asn)
    paths = nx.all_simple_paths(graph, src_asn, dst_asn, cutoff=shortest + 3)
    i = 0
    res = []

    for path in paths:
        # print(path)
        res.append(path)
        i += 1
        if i >= cut:
            break
    result = unique_scion_paths(res, graph)

    result.sort(key=lambda x: len(x))
    return result


def simulate_scion_traffic(src_asn, dst_asn, paths, distribution):
    """
    Simulate traffic between the source and destination ASes using the specified paths and distribution.
    """
    print(f"Simulating traffic from AS{src_asn} to AS{dst_asn} using {len(paths)} paths"
            f" and distribution '{distribution}'")
    # Create a dictionary to track the usage of each edge
    edge_usage = {}

    # Calculate initial metrics for each path
    path_metrics = []
    for path in paths:
        total_latency = sum(edge['latency'] for edge in path)
        max_loss = max(edge['packet_loss'] for edge in path)
        min_capacity = min(edge['capacity'] for edge in path)
        path_metrics.append({
            'latency': total_latency,
            'loss': max_loss,
            'goodput': min_capacity
        })
        # Track how often each edge is used
        for edge in path:
            edge_id = edge['link']
            if edge_id not in edge_usage:
                edge_usage[edge_id] = {
                    'capacity': edge['capacity'],
                    'usage_count': 0
                }
            edge_usage[edge_id]['usage_count'] += 1

    # Adjust capacities based on distribution
    for i, path in enumerate(paths):
        for edge in path:
            edge_id = edge['link']
            if edge_id in edge_usage:
                original_capacity = edge_usage[edge_id]['capacity']
                usage_count = edge_usage[edge_id]['usage_count']
                distributed_capacity = original_capacity / usage_count
                used_capacity = distribution[i] * distributed_capacity
                edge_usage[edge_id]['capacity'] -= used_capacity

                # Update path's goodput
                if used_capacity < path_metrics[i]['goodput']:
                    path_metrics[i]['goodput'] = used_capacity

    return path_metrics


def run():
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
        


run()