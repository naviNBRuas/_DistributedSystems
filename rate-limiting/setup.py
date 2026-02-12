from setuptools import setup, find_packages

setup(
    name="rate-limiting",
    version="0.1.0",
    description="Distributed rate limiting algorithms",
    author="Your Name",
    package_dir={"": "src"},
    py_modules=["rate_limiter", "distributed_limiter"],
    install_requires=[
        "redis>=4.0.0",
    ],
    python_requires=">=3.7",
)
