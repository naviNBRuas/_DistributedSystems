"""
Bloom Filter Implementation

Space-efficient probabilistic data structures for membership testing.
"""

import hashlib
import math
import struct
import array
from typing import List, Dict, Any, Union


class BloomFilter:
    """
    Standard Bloom Filter using Double Hashing.
    
    Space-efficient set membership test with configurable false positive rate.
    Uses a single Python integer as a bit-array for maximum space efficiency
    without external dependencies.
    """
    
    def __init__(self, expected_elements: int, false_positive_rate: float = 0.01):
        """
        Initialize Bloom filter
        
        Args:
            expected_elements: Expected number of elements to store
            false_positive_rate: Desired false positive probability (0 < p < 1)
        """
        if expected_elements <= 0:
            raise ValueError("expected_elements must be positive")
        if not (0 < false_positive_rate < 1):
            raise ValueError("false_positive_rate must be between 0 and 1")
        
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate
        
        # Calculate optimal filter size (m) and hash functions (k)
        self.size = self._optimal_size(expected_elements, false_positive_rate)
        self.num_hashes = self._optimal_hashes(self.size, expected_elements)
        
        # Initialize bit array as a single integer (acting as a bitfield)
        self.bit_array = 0
        self.count = 0
    
    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        """
        Calculate optimal filter size (m) in bits.
        m = -(n * ln(p)) / (ln(2)^2)
        """
        if p == 0:
            p = 1e-10  # Avoid division by zero/log(0)
        return int(-n * math.log(p) / (math.log(2) ** 2))
    
    @staticmethod
    def _optimal_hashes(m: int, n: int) -> int:
        """
        Calculate optimal number of hash functions (k).
        k = (m/n) * ln(2)
        """
        return max(1, int(m * math.log(2) / n))
    
    def _get_hash_seeds(self, element: Union[str, bytes]) -> tuple[int, int]:
        """
        Generate two 64-bit hash seeds from the element using MD5.
        MD5 is chosen for speed and distribution, not cryptographic security.
        """
        if isinstance(element, str):
            data = element.encode('utf-8')
        elif isinstance(element, (bytes, bytearray)):
            data = element
        else:
            data = str(element).encode('utf-8')
            
        digest = hashlib.md5(data).digest()
        # Unpack two unsigned long long (64-bit) integers
        h1, h2 = struct.unpack('QQ', digest)
        return h1, h2

    def add(self, element: Union[str, bytes]):
        """
        Add element to filter.
        Uses Double Hashing: g(i) = (h1 + i * h2) % m
        """
        h1, h2 = self._get_hash_seeds(element)
        for i in range(self.num_hashes):
            idx = (h1 + i * h2) % self.size
            self.bit_array |= (1 << idx)
        
        self.count += 1
    
    def contains(self, element: Union[str, bytes]) -> bool:
        """
        Check if element is potentially in the set.
        Returns False if definitely not present, True if probably present.
        """
        h1, h2 = self._get_hash_seeds(element)
        for i in range(self.num_hashes):
            idx = (h1 + i * h2) % self.size
            if not (self.bit_array & (1 << idx)):
                return False
        return True
    
    def __contains__(self, element: Union[str, bytes]) -> bool:
        return self.contains(element)
    
    def __len__(self) -> int:
        return self.count

    def get_stats(self) -> Dict[str, Any]:
        """Return filter statistics."""
        # Count set bits efficiently
        set_bits = bin(self.bit_array).count('1')
        return {
            "size_bits": self.size,
            "num_hashes": self.num_hashes,
            "elements_added": self.count,
            "expected_elements": self.expected_elements,
            "target_false_positive_rate": self.false_positive_rate,
            "fill_ratio": set_bits / self.size if self.size > 0 else 0.0
        }


class CountingBloomFilter(BloomFilter):
    """
    Counting Bloom Filter.
    Supports element removal by using counters instead of bits.
    Uses array.array for memory efficiency compared to standard lists.
    """
    
    def __init__(self, expected_elements: int, false_positive_rate: float = 0.01):
        super().__init__(expected_elements, false_positive_rate)
        # Use 'I' (unsigned int) for counters. 
        # For huge filters, this consumes 32x more memory than a bitarray,
        # but supports deletions.
        self.buckets = array.array('I', [0] * self.size)
        # We don't use self.bit_array
        del self.bit_array

    def add(self, element: Union[str, bytes]):
        h1, h2 = self._get_hash_seeds(element)
        for i in range(self.num_hashes):
            idx = (h1 + i * h2) % self.size
            # Prevent overflow if necessary, though 'I' is large (4 bytes)
            if self.buckets[idx] < 4294967295:
                self.buckets[idx] += 1
        self.count += 1

    def contains(self, element: Union[str, bytes]) -> bool:
        h1, h2 = self._get_hash_seeds(element)
        for i in range(self.num_hashes):
            idx = (h1 + i * h2) % self.size
            if self.buckets[idx] == 0:
                return False
        return True

    def remove(self, element: Union[str, bytes]) -> bool:
        """
        Remove element from filter.
        Returns True if element was likely present and removed, False otherwise.
        Note: If False positives exist, this might remove an element that wasn't added,
        affecting other elements (false negatives). This is inherent to CBFs.
        """
        if not self.contains(element):
            return False
        
        h1, h2 = self._get_hash_seeds(element)
        indices = []
        for i in range(self.num_hashes):
            idx = (h1 + i * h2) % self.size
            indices.append(idx)
        
        # Decrement all
        for idx in indices:
            if self.buckets[idx] > 0:
                self.buckets[idx] -= 1
        
        self.count -= 1
        return True
        
    def get_stats(self) -> Dict[str, Any]:
        """Return filter statistics."""
        # Calculate fill ratio for counting filter (buckets > 0)
        non_zero = sum(1 for b in self.buckets if b > 0)
        
        return {
            "size_bits": self.size,  # This is actually number of counters
            "num_hashes": self.num_hashes,
            "elements_added": self.count,
            "expected_elements": self.expected_elements,
            "target_false_positive_rate": self.false_positive_rate,
            "fill_ratio": non_zero / self.size if self.size > 0 else 0.0
        }


class ScalableBloomFilter:
    """
    Scalable Bloom Filter.
    Dynamically adapts to the number of elements by adding new layers of Bloom filters.
    Maintains a target false positive rate by tightening the error rate of subsequent layers.
    """
    
    def __init__(self, initial_size: int = 1000, false_positive_rate: float = 0.01,
                 error_tightening_ratio: float = 0.9, growth_factor: int = 2):
        """
        Args:
            initial_size: Initial capacity.
            false_positive_rate: Target global false positive rate.
            error_tightening_ratio: Factor to reduce error rate for new filters (r < 1).
            growth_factor: Factor to grow capacity for new filters (s > 1).
        """
        self.initial_size = initial_size
        self.target_fp_rate = false_positive_rate
        self.ratio = error_tightening_ratio
        self.scale = growth_factor
        
        self.filters: List[BloomFilter] = []
        self.count = 0
        
        # Initialize first filter
        # The first filter gets a portion of the total allowed error.
        # A common strategy ensures the infinite sum of errors converges to target_fp_rate.
        # P_0 = target * (1 - ratio)
        self._add_filter()

    def _add_filter(self):
        # Calculate parameters for the new filter
        k = len(self.filters)
        capacity = self.initial_size * (self.scale ** k)
        
        # Tighten the error rate for this layer to keep global error bounded
        # fp_rate_k = target * (ratio ^ k) * (1 - ratio) is a safe approximation
        # to ensure sum(fp_rate_k) <= target.
        fp_rate = self.target_fp_rate * (self.ratio ** k) * (1 - self.ratio)
        
        new_filter = BloomFilter(capacity, fp_rate)
        self.filters.append(new_filter)

    def add(self, element: Union[str, bytes]):
        # Check if the current filter is full
        current_filter = self.filters[-1]
        if current_filter.count >= current_filter.expected_elements:
            self._add_filter()
            current_filter = self.filters[-1]
            
        current_filter.add(element)
        self.count += 1

    def contains(self, element: Union[str, bytes]) -> bool:
        # Check all filters. If any says "present", it is present.
        for f in self.filters:
            if f.contains(element):
                return True
        return False
        
    def __contains__(self, element: Union[str, bytes]) -> bool:
        return self.contains(element)

    def __len__(self) -> int:
        return self.count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_elements": self.count,
            "num_filters": len(self.filters),
            "filters": [f.get_stats() for f in self.filters]
        }