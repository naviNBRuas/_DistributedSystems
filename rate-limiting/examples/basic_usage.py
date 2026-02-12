import time
import sys
import os

# Add src to path for running example without installation
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from rate_limiter import TokenBucketLimiter, LeakyBucketLimiter

def main():
    print("=== Rate Limiting Demo ===")
    
    # Token Bucket
    print("\n1. Token Bucket (Rate: 5/s, Capacity: 5)")
    limiter = TokenBucketLimiter(rate=5, capacity=5)
    
    start = time.time()
    allowed = 0
    rejected = 0
    
    # Try 10 requests rapidly
    for i in range(10):
        if limiter.allow_request():
            print(f"Request {i+1}: Allowed")
            allowed += 1
        else:
            print(f"Request {i+1}: Rejected")
            rejected += 1
    
    print(f"Summary: {allowed} allowed, {rejected} rejected")
    
    # Leaky Bucket
    print("\n2. Leaky Bucket (Rate: 2/s, Capacity: 3)")
    leaky = LeakyBucketLimiter(rate=2, capacity=3)
    
    for i in range(6):
        if leaky.allow_request():
            print(f"Request {i+1}: Queued")
        else:
            print(f"Request {i+1}: Dropped (Bucket Full)")

if __name__ == "__main__":
    main()
