from pbft import PBFTNode, InMemoryNetwork
import sys

def run_simulation():
    # Setup network
    network = InMemoryNetwork()
    
    # Create nodes
    nodes = []
    print("Initializing 4 nodes...")
    for i in range(4):
        node = PBFTNode(node_id=i, total_nodes=4, network=network)
        nodes.append(node)
        
    print(f"Nodes created. Fault tolerance f={(4-1)//3}")
        
    # Propose
    print("Node 0 proposing 'execute_transaction'...")
    request_state = nodes[0].propose("execute_transaction")
    
    print(f"Request ID: {request_state.request_id}")
    print(f"Committed: {request_state.committed}")
    
    if request_state.committed:
        print("SUCCESS: Consensus reached!")
    else:
        print("FAILURE: Consensus not reached.")
        
if __name__ == "__main__":
    run_simulation()
