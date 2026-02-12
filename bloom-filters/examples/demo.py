import sys
import os

# Ensure we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from bloom_filter import BloomFilter, CountingBloomFilter, ScalableBloomFilter

def main():
    print("=== Bloom Filter Demo ===\n")

    # 1. Standard Bloom Filter
    print("--- Standard Bloom Filter ---")
    # Initialize for 100,000 items with 1% false positive rate
    bf = BloomFilter(expected_elements=100000, false_positive_rate=0.01)
    
    print(f"Created filter: Size={bf.size} bits, Hashes={bf.num_hashes}")
    
    # Add some emails
    emails = ["alice@example.com", "bob@example.com", "charlie@example.com"]
    for email in emails:
        bf.add(email)
    
    print(f"Added {len(emails)} items.")
    
    # Check membership
    test_emails = ["alice@example.com", "dave@example.com"]
    for email in test_emails:
        present = email in bf
        status = "Found" if present else "Not Found"
        print(f"'{email}': {status}")

    # 2. Counting Bloom Filter (supports removal)
    print("\n--- Counting Bloom Filter ---")
    cbf = CountingBloomFilter(expected_elements=1000, false_positive_rate=0.01)
    
    cbf.add("session_123")
    print(f"Added 'session_123'. Present? {'session_123' in cbf}")
    
    cbf.remove("session_123")
    print(f"Removed 'session_123'. Present? {'session_123' in cbf}")

    # 3. Scalable Bloom Filter (grows automatically)
    print("\n--- Scalable Bloom Filter ---")
    sbf = ScalableBloomFilter(initial_size=100, false_positive_rate=0.01)
    
    print("Adding 1000 items to a filter initially sized for 100...")
    for i in range(1000):
        sbf.add(f"data_{i}")
        
    print(f"Total elements: {len(sbf)}")
    print(f"Number of sub-filters used: {len(sbf.filters)}")
    print(f"First item present? {'data_0' in sbf}")
    print(f"Last item present? {'data_999' in sbf}")

if __name__ == "__main__":
    main()
