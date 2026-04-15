"""Seed data for the Adaptive Learning Engine (Phase 15, F7/F17/F18/F22).

Hand-curated skill graph + company profiles for the research core. The
graph is deliberately small enough to reason about but dense enough to
produce interesting Dijkstra paths and meaningful Knapsack tradeoffs.

Loaded once on app startup if the `skill_nodes` table is empty.

Reference for the paper:
- 60 skills across 9 domains (DSA, Web, Systems, DB, Cloud, ML, SysDesign, Mobile, Fundamentals)
- 80+ weighted prerequisite edges (base learning hours)
- 20 company profiles each with 6-12 required skills
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SeedNode:
    name: str
    domain: str
    description: str
    difficulty_tier: int   # 1-5


@dataclass
class SeedEdge:
    from_skill: str
    to_skill: str
    base_weight_hours: float
    domain: str


@dataclass
class SeedCompany:
    company: str
    role: str
    required_skills: list[str]
    preferred_skills: list[str]
    difficulty_tier: int


# ════════════════════════════════════════════════════════════════
# Nodes
# ════════════════════════════════════════════════════════════════

SEED_NODES: list[SeedNode] = [
    # ── DSA ────────────────────────────────────────────────
    SeedNode("Arrays", "dsa", "Array operations, two-pointer, sliding window", 1),
    SeedNode("Strings", "dsa", "String manipulation, pattern matching", 1),
    SeedNode("Hashing", "dsa", "Hash maps, sets, collision resolution", 1),
    SeedNode("Linked Lists", "dsa", "Singly/doubly linked lists, reversal, detection", 2),
    SeedNode("Stacks & Queues", "dsa", "LIFO/FIFO structures, monotonic stacks", 2),
    SeedNode("Sorting", "dsa", "Merge sort, quicksort, heapsort, counting sort", 2),
    SeedNode("Searching", "dsa", "Binary search, ternary search", 2),
    SeedNode("Trees", "dsa", "Binary trees, BST, traversals", 3),
    SeedNode("Heaps", "dsa", "Binary heap, priority queue operations", 3),
    SeedNode("Tries", "dsa", "Prefix trees, autocomplete", 3),
    SeedNode("Graphs", "dsa", "BFS, DFS, adjacency representations", 4),
    SeedNode("Dynamic Programming", "dsa", "Memoization, tabulation, classical DP", 4),
    SeedNode("Backtracking", "dsa", "Recursive exploration with pruning", 4),
    SeedNode("Greedy Algorithms", "dsa", "Exchange argument, interval scheduling", 3),
    SeedNode("DSA Advanced", "dsa", "Segment trees, Fenwick trees, advanced graph algos", 5),
    # ── Web ────────────────────────────────────────────────
    SeedNode("HTML/CSS", "web", "Semantic HTML, modern CSS, flex/grid", 1),
    SeedNode("JavaScript", "web", "ES6+, closures, prototypes, async", 2),
    SeedNode("TypeScript", "web", "Static typing, generics, inference", 3),
    SeedNode("React", "web", "Components, hooks, state management", 3),
    SeedNode("Next.js", "web", "SSR, routing, API routes", 4),
    SeedNode("Node.js", "web", "Event loop, modules, streams", 3),
    SeedNode("Express", "web", "Middleware, routing, REST APIs", 3),
    SeedNode("REST APIs", "web", "HTTP verbs, status codes, versioning", 2),
    SeedNode("GraphQL", "web", "Schemas, resolvers, federation", 4),
    # ── Systems ────────────────────────────────────────────
    SeedNode("Git", "systems", "Branching, merging, rebase", 1),
    SeedNode("Linux/Shell", "systems", "Bash, process management, pipes", 2),
    SeedNode("Docker", "systems", "Containers, images, compose", 3),
    SeedNode("CI/CD", "systems", "Pipelines, testing automation", 3),
    SeedNode("Kubernetes", "systems", "Pods, services, deployments", 5),
    # ── Databases ──────────────────────────────────────────
    SeedNode("SQL", "db", "Joins, aggregates, window functions", 2),
    SeedNode("PostgreSQL", "db", "Indexes, transactions, EXPLAIN", 3),
    SeedNode("MongoDB", "db", "Documents, aggregation, indexes", 3),
    SeedNode("Redis", "db", "Caching, pub/sub, data structures", 3),
    # ── Cloud ──────────────────────────────────────────────
    SeedNode("AWS Basics", "cloud", "EC2, S3, IAM, VPC", 3),
    SeedNode("AWS Advanced", "cloud", "Lambda, DynamoDB, Step Functions", 4),
    SeedNode("GCP", "cloud", "Compute Engine, Cloud Run, BigQuery", 4),
    # ── ML ─────────────────────────────────────────────────
    SeedNode("Python", "ml", "Python fundamentals, stdlib", 1),
    SeedNode("NumPy/Pandas", "ml", "Array and dataframe operations", 2),
    SeedNode("Scikit-learn", "ml", "Classical ML, pipelines, metrics", 3),
    SeedNode("Deep Learning", "ml", "Neural nets, backprop, optimization", 4),
    SeedNode("PyTorch", "ml", "Tensors, autograd, training loops", 4),
    SeedNode("NLP", "ml", "Tokenization, embeddings, transformers", 5),
    SeedNode("LLMs", "ml", "Prompting, RAG, fine-tuning", 5),
    # ── System Design ──────────────────────────────────────
    SeedNode("System Design Basics", "sysdesign", "Load balancing, caching, sharding", 3),
    SeedNode("System Design Advanced", "sysdesign", "CAP, consistency models, event-driven", 5),
    SeedNode("Distributed Systems", "sysdesign", "Consensus, replication, failure modes", 5),
    SeedNode("Microservices", "sysdesign", "Service boundaries, communication patterns", 4),
    # ── Mobile ─────────────────────────────────────────────
    SeedNode("React Native", "mobile", "Cross-platform mobile with React", 3),
    SeedNode("Flutter", "mobile", "Dart, widgets, state management", 3),
    # ── Fundamentals ───────────────────────────────────────
    SeedNode("OS Concepts", "fundamentals", "Processes, threads, memory, scheduling", 3),
    SeedNode("Computer Networks", "fundamentals", "TCP/IP, HTTP, routing", 3),
    SeedNode("DBMS Theory", "fundamentals", "Normalization, ACID, query planning", 3),
    SeedNode("OOP", "fundamentals", "Encapsulation, inheritance, polymorphism", 2),
    # ── Languages ──────────────────────────────────────────
    SeedNode("Java", "languages", "JVM, collections, streams", 2),
    SeedNode("C++", "languages", "STL, templates, memory management", 3),
    SeedNode("Go", "languages", "Goroutines, channels, tooling", 3),
    # ── Problem Solving ────────────────────────────────────
    SeedNode("Problem Solving", "soft", "Pattern recognition, decomposition", 2),
    SeedNode("Communication", "soft", "Written + verbal technical communication", 2),
]


# ════════════════════════════════════════════════════════════════
# Edges — (u → v) means "u is a prerequisite for v"
# base_weight_hours = estimated hours to go from u to v
# ════════════════════════════════════════════════════════════════

SEED_EDGES: list[SeedEdge] = [
    # ── DSA prerequisite chain ─────────────────────────────
    SeedEdge("Arrays", "Strings", 2, "dsa"),
    SeedEdge("Arrays", "Hashing", 3, "dsa"),
    SeedEdge("Arrays", "Linked Lists", 3, "dsa"),
    SeedEdge("Arrays", "Stacks & Queues", 2, "dsa"),
    SeedEdge("Arrays", "Searching", 2, "dsa"),
    SeedEdge("Arrays", "Sorting", 3, "dsa"),
    SeedEdge("Linked Lists", "Trees", 4, "dsa"),
    SeedEdge("Stacks & Queues", "Trees", 3, "dsa"),
    SeedEdge("Sorting", "Searching", 2, "dsa"),
    SeedEdge("Trees", "Heaps", 3, "dsa"),
    SeedEdge("Trees", "Tries", 3, "dsa"),
    SeedEdge("Trees", "Graphs", 4, "dsa"),
    SeedEdge("Hashing", "Graphs", 3, "dsa"),
    SeedEdge("Graphs", "Dynamic Programming", 5, "dsa"),
    SeedEdge("Graphs", "Backtracking", 4, "dsa"),
    SeedEdge("Graphs", "Greedy Algorithms", 3, "dsa"),
    SeedEdge("Dynamic Programming", "DSA Advanced", 6, "dsa"),
    SeedEdge("Graphs", "DSA Advanced", 8, "dsa"),
    SeedEdge("Backtracking", "DSA Advanced", 5, "dsa"),
    # ── Web stack ──────────────────────────────────────────
    SeedEdge("HTML/CSS", "JavaScript", 4, "web"),
    SeedEdge("JavaScript", "TypeScript", 3, "web"),
    SeedEdge("JavaScript", "React", 5, "web"),
    SeedEdge("React", "Next.js", 4, "web"),
    SeedEdge("TypeScript", "React", 2, "web"),
    SeedEdge("JavaScript", "Node.js", 4, "web"),
    SeedEdge("Node.js", "Express", 3, "web"),
    SeedEdge("Express", "REST APIs", 2, "web"),
    SeedEdge("REST APIs", "GraphQL", 4, "web"),
    SeedEdge("React", "React Native", 4, "mobile"),
    # ── Systems + Cloud ────────────────────────────────────
    SeedEdge("Git", "CI/CD", 3, "systems"),
    SeedEdge("Linux/Shell", "Docker", 4, "systems"),
    SeedEdge("Docker", "Kubernetes", 6, "systems"),
    SeedEdge("Docker", "CI/CD", 2, "systems"),
    SeedEdge("Linux/Shell", "AWS Basics", 4, "cloud"),
    SeedEdge("AWS Basics", "AWS Advanced", 6, "cloud"),
    SeedEdge("AWS Basics", "GCP", 4, "cloud"),
    SeedEdge("AWS Advanced", "Microservices", 4, "sysdesign"),
    # ── Databases ──────────────────────────────────────────
    SeedEdge("SQL", "PostgreSQL", 3, "db"),
    SeedEdge("SQL", "MongoDB", 3, "db"),
    SeedEdge("Hashing", "Redis", 3, "db"),
    SeedEdge("DBMS Theory", "SQL", 2, "db"),
    SeedEdge("DBMS Theory", "PostgreSQL", 2, "db"),
    # ── ML track ───────────────────────────────────────────
    SeedEdge("Python", "NumPy/Pandas", 3, "ml"),
    SeedEdge("NumPy/Pandas", "Scikit-learn", 4, "ml"),
    SeedEdge("Scikit-learn", "Deep Learning", 6, "ml"),
    SeedEdge("Deep Learning", "PyTorch", 4, "ml"),
    SeedEdge("PyTorch", "NLP", 5, "ml"),
    SeedEdge("NLP", "LLMs", 6, "ml"),
    # ── System Design ──────────────────────────────────────
    SeedEdge("REST APIs", "System Design Basics", 4, "sysdesign"),
    SeedEdge("Redis", "System Design Basics", 3, "sysdesign"),
    SeedEdge("PostgreSQL", "System Design Basics", 3, "sysdesign"),
    SeedEdge("System Design Basics", "System Design Advanced", 8, "sysdesign"),
    SeedEdge("System Design Basics", "Microservices", 5, "sysdesign"),
    SeedEdge("Microservices", "Distributed Systems", 6, "sysdesign"),
    SeedEdge("System Design Advanced", "Distributed Systems", 5, "sysdesign"),
    # ── Languages ──────────────────────────────────────────
    SeedEdge("OOP", "Java", 3, "languages"),
    SeedEdge("OOP", "C++", 4, "languages"),
    SeedEdge("Java", "Python", 2, "languages"),
    # ── Fundamentals feed ──────────────────────────────────
    SeedEdge("OS Concepts", "System Design Basics", 3, "fundamentals"),
    SeedEdge("Computer Networks", "System Design Basics", 3, "fundamentals"),
    SeedEdge("Computer Networks", "Distributed Systems", 5, "fundamentals"),
    # ── Problem solving underpins everything ─────────────
    SeedEdge("Problem Solving", "Arrays", 1, "soft"),
    SeedEdge("Problem Solving", "Dynamic Programming", 2, "soft"),
]


# ════════════════════════════════════════════════════════════════
# Company profiles
# ════════════════════════════════════════════════════════════════

SEED_COMPANIES: list[SeedCompany] = [
    # ── Tier 1 (MAANG) ─────────────────────────────────────
    SeedCompany(
        "Google",
        "SWE",
        required_skills=[
            "Arrays", "Hashing", "Trees", "Graphs", "Dynamic Programming",
            "DSA Advanced", "System Design Basics", "OS Concepts", "Problem Solving",
        ],
        preferred_skills=["Distributed Systems", "C++", "Python"],
        difficulty_tier=5,
    ),
    SeedCompany(
        "Meta",
        "SWE",
        required_skills=[
            "Arrays", "Hashing", "Trees", "Graphs", "Dynamic Programming",
            "DSA Advanced", "System Design Basics", "React", "JavaScript",
        ],
        preferred_skills=["GraphQL", "System Design Advanced"],
        difficulty_tier=5,
    ),
    SeedCompany(
        "Amazon",
        "SDE",
        required_skills=[
            "Arrays", "Trees", "Graphs", "Dynamic Programming",
            "System Design Basics", "AWS Basics", "Java", "SQL", "Git",
        ],
        preferred_skills=["AWS Advanced", "Microservices"],
        difficulty_tier=5,
    ),
    SeedCompany(
        "Microsoft",
        "SDE",
        required_skills=[
            "Arrays", "Trees", "Graphs", "Dynamic Programming",
            "System Design Basics", "C++", "Git", "OS Concepts",
        ],
        preferred_skills=["Azure", "Distributed Systems"],
        difficulty_tier=5,
    ),
    SeedCompany(
        "Netflix",
        "SWE",
        required_skills=[
            "Arrays", "Trees", "System Design Advanced", "Java",
            "AWS Advanced", "Microservices", "Distributed Systems",
        ],
        preferred_skills=["Kubernetes", "Redis"],
        difficulty_tier=5,
    ),
    # ── Indian unicorns ────────────────────────────────────
    SeedCompany(
        "Flipkart",
        "SDE",
        required_skills=[
            "Arrays", "Trees", "Graphs", "Dynamic Programming",
            "System Design Basics", "Java", "SQL", "Git",
        ],
        preferred_skills=["React", "Redis"],
        difficulty_tier=4,
    ),
    SeedCompany(
        "Swiggy",
        "Backend Engineer",
        required_skills=[
            "Arrays", "Trees", "System Design Basics", "Java",
            "PostgreSQL", "Redis", "REST APIs",
        ],
        preferred_skills=["Microservices", "Kubernetes"],
        difficulty_tier=4,
    ),
    SeedCompany(
        "Zomato",
        "Frontend Engineer",
        required_skills=[
            "HTML/CSS", "JavaScript", "TypeScript", "React",
            "Next.js", "Git", "REST APIs",
        ],
        preferred_skills=["GraphQL", "System Design Basics"],
        difficulty_tier=4,
    ),
    SeedCompany(
        "Uber India",
        "Backend Engineer",
        required_skills=[
            "Arrays", "Trees", "Graphs", "Dynamic Programming",
            "System Design Advanced", "Go", "Distributed Systems",
        ],
        preferred_skills=["Microservices", "Kubernetes"],
        difficulty_tier=5,
    ),
    # ── Product companies ──────────────────────────────────
    SeedCompany(
        "Stripe",
        "SWE",
        required_skills=[
            "Arrays", "Trees", "DSA Advanced", "System Design Advanced",
            "Python", "Distributed Systems", "Problem Solving",
        ],
        preferred_skills=["Go", "PostgreSQL"],
        difficulty_tier=5,
    ),
    SeedCompany(
        "Adobe",
        "SDE",
        required_skills=[
            "Arrays", "Trees", "Graphs", "DSA Advanced",
            "C++", "System Design Basics",
        ],
        preferred_skills=["OOP", "OS Concepts"],
        difficulty_tier=4,
    ),
    SeedCompany(
        "Salesforce",
        "SDE",
        required_skills=[
            "Arrays", "Trees", "Java", "REST APIs", "SQL", "OOP", "Git",
        ],
        preferred_skills=["System Design Basics"],
        difficulty_tier=4,
    ),
    # ── Finance ────────────────────────────────────────────
    SeedCompany(
        "Goldman Sachs",
        "Analyst (Tech)",
        required_skills=[
            "Arrays", "Trees", "Dynamic Programming", "Java",
            "SQL", "OS Concepts", "DBMS Theory",
        ],
        preferred_skills=["Python"],
        difficulty_tier=4,
    ),
    SeedCompany(
        "JP Morgan",
        "SDE",
        required_skills=[
            "Arrays", "Trees", "Java", "SQL", "REST APIs", "Git",
        ],
        preferred_skills=["System Design Basics"],
        difficulty_tier=3,
    ),
    # ── Service companies (India grads) ────────────────────
    SeedCompany(
        "TCS",
        "Digital",
        required_skills=[
            "Arrays", "Trees", "Java", "SQL", "Git", "Problem Solving",
        ],
        preferred_skills=["OOP", "REST APIs"],
        difficulty_tier=2,
    ),
    SeedCompany(
        "Infosys",
        "Systems Engineer",
        required_skills=[
            "Arrays", "Java", "SQL", "Git", "Problem Solving",
        ],
        preferred_skills=["OOP"],
        difficulty_tier=2,
    ),
    SeedCompany(
        "Wipro",
        "Project Engineer",
        required_skills=[
            "Arrays", "Java", "SQL", "Git",
        ],
        preferred_skills=["Problem Solving"],
        difficulty_tier=2,
    ),
    SeedCompany(
        "Accenture",
        "Associate SE",
        required_skills=[
            "Arrays", "Java", "SQL", "Git",
        ],
        preferred_skills=["OOP"],
        difficulty_tier=2,
    ),
    # ── Specialty roles ────────────────────────────────────
    SeedCompany(
        "OpenAI",
        "ML Engineer",
        required_skills=[
            "Python", "NumPy/Pandas", "Scikit-learn",
            "Deep Learning", "PyTorch", "NLP", "LLMs",
        ],
        preferred_skills=["Distributed Systems", "AWS Advanced"],
        difficulty_tier=5,
    ),
    SeedCompany(
        "Startup",
        "Full-Stack Intern",
        required_skills=[
            "HTML/CSS", "JavaScript", "React", "Node.js",
            "REST APIs", "SQL", "Git",
        ],
        preferred_skills=["TypeScript", "PostgreSQL"],
        difficulty_tier=3,
    ),
]
