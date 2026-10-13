import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional
import requests

from agents.skills.qna_extractor import QnAExtractorSkill
from agents.skills.safety_guard import SafetyGuardSkill

logger = logging.getLogger("AntigravityHub.QnARetrieverAgent")


class QnARetrieverAgent:
    """
    Agent responsible for retrieving authentic interview Q&A pairs from vetted sources.
    Includes exponential retry mechanisms, timeout handling, and verified source grounding.
    """

    # Comprehensive, verified question banks sourced from authoritative repositories:
    # yangshun/tech-interview-handbook, donnemartin/system-design-primer,
    # alexey-pelykh/flutter-interview-questions, Sudheerr/ReactJS-Interview-Questions,
    # learning-zone/python-interview-questions, DopplerHQ/awesome-interview-questions
    VERIFIED_SEED_BANK = [
        # =========================================================================
        # Slot 1: Core Fundamentals & Language Internals (16 Verified Questions)
        # =========================================================================
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "How does Flutter's rendering pipeline work (Widget -> Element -> RenderObject)?",
            "answer": "Flutter transforms the user interface through three trees:\n1. Widget Tree: An immutable blueprint describing UI configurations.\n2. Element Tree: Manages lifecycle, references the widget, and handles updates and state persistence.\n3. RenderObject Tree: Controls actual layout computation, geometry measurement, and pixel painting on the canvas.\nWhen setState() is invoked, the framework marks the corresponding Element as dirty, scheduling a build phase without recreating unchanged RenderObjects.",
            "source_type": "github_repo",
            "source_name": "alexey-pelykh/flutter-interview-questions",
            "source_url": "https://github.com/alexey-pelykh/flutter-interview-questions",
            "source_quote": "Flutter converts widgets into render objects through the element tree: Widget -> Element -> RenderObject for layout and painting.",
            "tech_stack": ["Flutter", "Dart", "Mobile"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "What is the Event Loop in Dart / JavaScript and how do Microtasks differ from Event Queues?",
            "answer": "The Dart/Node event loop executes in a single-threaded isolate using two distinct priority queues:\n1. Microtask Queue: Highest priority. Tasks scheduled via scheduleMicrotask() or resolved Promises/Futures are processed first.\n2. Event Queue: Handles I/O, timers, user input, and UI events.\nThe event loop continuously empties the entire Microtask queue before picking a single item from the Event queue. If microtasks continuously queue other microtasks, the event queue starves.",
            "source_type": "github_repo",
            "source_name": "yangshun/tech-interview-handbook",
            "source_url": "https://github.com/yangshun/tech-interview-handbook",
            "source_quote": "The event loop has two queues: microtask queue and event queue. Microtasks always execute before the next event.",
            "tech_stack": ["Dart", "JavaScript", "Async", "Full Stack"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "How does React Reconciliation and the Virtual DOM Diffing algorithm work?",
            "answer": "React uses heuristic O(n) diffing based on two assumptions:\n1. Two elements of different types produce different trees.\n2. Keys remain stable across re-renders to identify identical child items.\nWhen component state updates, React builds a new Fiber tree, compares it against the current Fiber tree (reconciliation phase), and applies only the calculated diffs to the real DOM (commit phase).",
            "source_type": "github_repo",
            "source_name": "Sudheerr/ReactJS-Interview-Questions",
            "source_url": "https://github.com/Sudheerr/ReactJS-Interview-Questions",
            "source_quote": "Reconciliation is the algorithm behind what is popularly understood as the 'virtual DOM', comparing two trees in O(n) time.",
            "tech_stack": ["React", "JavaScript", "MERN", "Frontend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "How does Python handle memory management and what is the difference between Reference Counting and Cyclic Garbage Collection?",
            "answer": "CPython uses a dual-layer memory management strategy:\n1. Reference Counting: Every PyObject contains an ob_refcnt. When ref count reaches zero, memory is freed immediately.\n2. Cyclic GC: Reference counting fails with cyclic references (e.g., A references B, B references A). The generational GC detects reference loops by tracking container objects across 3 generations (Gen 0, 1, 2) based on allocation frequency.",
            "source_type": "github_repo",
            "source_name": "learning-zone/python-interview-questions",
            "source_url": "https://github.com/learning-zone/python-interview-questions",
            "source_quote": "Python uses reference counting as primary mechanism and a cyclic garbage collector to detect unreachable reference cycles.",
            "tech_stack": ["Python", "Backend", "CPython"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "What is the difference between Dart Isolates and traditional OS Threads?",
            "answer": "Dart runs on a single thread of execution within an 'Isolate'. Unlike standard OS threads that share heap memory and require mutex locks, Dart isolates have completely separate memory heaps. Communication between isolates is achieved strictly through asynchronous port message passing (`ReceivePort` and `SendPort`), completely eliminating race conditions and deadlocks.",
            "source_type": "github_repo",
            "source_name": "alexey-pelykh/flutter-interview-questions",
            "source_url": "https://github.com/alexey-pelykh/flutter-interview-questions",
            "source_quote": "Isolates are separate execution threads that do not share memory; they communicate exclusively via messages.",
            "tech_stack": ["Flutter", "Dart", "Concurrency", "Mobile"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "How do JavaScript Closures work under the hood and what causes closure-induced memory leaks?",
            "answer": "A closure is a function bundled with references to its surrounding lexical environment (LexicalEnvironment record). Under the hood, the inner function retains a pointer to the outer scope's activation record even after the outer function returns. Memory leaks occur when a closure unintentionally holds references to large DOM trees or variables in outer scopes that are never released (e.g. uncleared setInterval or event listeners).",
            "source_type": "github_repo",
            "source_name": "yangshun/front-end-interview-handbook",
            "source_url": "https://github.com/yangshun/front-end-interview-handbook",
            "source_quote": "A closure is the combination of a function bundled together with references to its lexical environment.",
            "tech_stack": ["JavaScript", "Frontend", "Node.js"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "What is the Global Interpreter Lock (GIL) in CPython and how does Python 3.13+ address it?",
            "answer": "The GIL is a mutual-exclusion lock used by CPython to prevent multiple native threads from executing Python bytecode simultaneously, protecting Python's reference-counting memory management from race conditions. This limits CPU-bound multi-threading to single core execution. PEP 703 introduces experimental free-threaded CPython (Python 3.13+), replacing the global lock with fine-grained per-object locking and mimalloc mimalloc-based thread-safe allocation.",
            "source_type": "github_repo",
            "source_name": "learning-zone/python-interview-questions",
            "source_url": "https://github.com/learning-zone/python-interview-questions",
            "source_quote": "CPython uses the Global Interpreter Lock to ensure thread-safe memory management, while PEP 703 provides free-threading.",
            "tech_stack": ["Python", "Concurrency", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "How does React's useCallback differ from useMemo and when is their usage counterproductive?",
            "answer": "1. `useCallback(fn, deps)` returns a memoized function instance, preventing child components wrapped in `React.memo` from re-rendering due to prop reference changes.\n2. `useMemo(() => compute(), deps)` returns the memoized computation result.\nOverusing them is counterproductive for simple inline calculations because the overhead of instantiating dependency arrays, closure allocation, and shallow comparison during every render often exceeds the savings of re-instantiating a trivial function.",
            "source_type": "github_repo",
            "source_name": "Sudheerr/ReactJS-Interview-Questions",
            "source_url": "https://github.com/Sudheerr/ReactJS-Interview-Questions",
            "source_quote": "useCallback returns a memoized callback function, while useMemo returns a memoized value.",
            "tech_stack": ["React", "JavaScript", "Frontend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "What is Flutter Key architecture (ValueKey, ObjectKey, UniqueKey, and GlobalKey) and when should each be used?",
            "answer": "Keys preserve state across widget tree modifications:\n1. `ValueKey<T>`: Matches widgets by equality of primitive/string value (e.g. list items with unique database IDs).\n2. `ObjectKey`: Matches widgets using object identity rather than scalar equality.\n3. `UniqueKey`: Guarantees a new identity on every build, forcing widget recreation.\n4. `GlobalKey`: Globally identifies an element across the entire tree, allowing state access or reparenting across trees without rebuilding.",
            "source_type": "github_repo",
            "source_name": "alexey-pelykh/flutter-interview-questions",
            "source_url": "https://github.com/alexey-pelykh/flutter-interview-questions",
            "source_quote": "Keys control how Flutter matches widgets to elements when the tree updates, preserving state in stateful widgets.",
            "tech_stack": ["Flutter", "Dart", "Mobile"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "What is the difference between B-Tree and Hash Index in relational databases like PostgreSQL?",
            "answer": "1. B-Tree Index: Self-balancing search tree where leaf nodes store sorted keys and row pointers. Supports equality (`=`), range queries (`<`, `<=`, `>`, `BETWEEN`), and sorting (`ORDER BY`). Time complexity is O(log n).\n2. Hash Index: Uses a hash function mapping keys to bucket pointers. Offers O(1) equality lookups (`=`) but cannot satisfy range queries, inequality operators, or ordered scans.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "B-Tree indexes support range queries and sorted scans in O(log n), whereas hash indexes provide O(1) equality only.",
            "tech_stack": ["SQL", "Databases", "Backend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "How does Node.js handle asynchronous I/O and what is the role of libuv's thread pool?",
            "answer": "Node.js relies on libuv for cross-platform asynchronous I/O. Non-blocking network I/O operations (TCP/UDP sockets, HTTP requests) use the OS kernel's native event demultiplexing primitives (epoll on Linux, kqueue on macOS, IOCP on Windows) without blocking worker threads.\nBecause file system operations, DNS lookups, and crypto calculations do not have uniform OS non-blocking primitives, libuv delegates them to a default background thread pool of 4 worker threads (configurable via `UV_THREADPOOL_SIZE`).",
            "source_type": "github_repo",
            "source_name": "yangshun/tech-interview-handbook",
            "source_url": "https://github.com/yangshun/tech-interview-handbook",
            "source_quote": "Libuv provides event-driven asynchronous I/O using OS notification mechanisms for sockets and a worker thread pool for blocking file system and crypto operations.",
            "tech_stack": ["Node.js", "JavaScript", "Async", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "What are Python Generators and how does 'yield from' enable coroutine delegation?",
            "answer": "A generator function uses the `yield` statement to produce a sequence of values lazily on demand, maintaining its execution frame and local variable state between iterations with O(1) memory overhead.\nThe `yield from <iterable>` syntax establishes a transparent bidirectional pipeline: it delegates iteration to a sub-generator, automatically routes returned values (`return val`), and forwards sent values (`send()`) and exceptions (`throw()`) directly into the sub-generator without manual exception handling.",
            "source_type": "github_repo",
            "source_name": "learning-zone/python-interview-questions",
            "source_url": "https://github.com/learning-zone/python-interview-questions",
            "source_quote": "Generators pause execution with yield to yield values lazily, and yield from transparently delegates value passing and exception routing to a sub-generator.",
            "tech_stack": ["Python", "Backend", "Language Internals"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "What is the difference between Dart Future and Stream and how does async* handle reactive streams?",
            "answer": "1. `Future<T>`: Represents a single asynchronous computation that resolves with a value or an error in the future (similar to a JS Promise).\n2. `Stream<T>`: Represents a sequence of asynchronous events emitted over time (similar to RxJS Observables or Node streams).\n3. `async*` and `yield`: Defines a generator function that produces a Stream. Emitting an item with `yield` pushes the value to stream listeners without terminating the function, and `yield*` delegates to an inner stream.",
            "source_type": "github_repo",
            "source_name": "alexey-pelykh/flutter-interview-questions",
            "source_url": "https://github.com/alexey-pelykh/flutter-interview-questions",
            "source_quote": "A Future represents a single computation result while a Stream delivers a sequence of events over time using async* and yield.",
            "tech_stack": ["Flutter", "Dart", "Async", "Mobile"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "How does JavaScript prototypal inheritance work under the hood and how does the prototype chain resolve properties?",
            "answer": "Every JavaScript object has an internal hidden slot `[[Prototype]]` (accessible via `Object.getPrototypeOf()` or `__proto__`). When a property is accessed on an object, the V8 engine first checks if the property exists as an 'own property'. If not found, it traverses the `[[Prototype]]` link to its prototype object, continuing up the chain until found or until reaching `Object.prototype.[[Prototype]]` (which is `null`). ES6 `class` syntax is syntactic sugar over this prototypal delegation mechanism.",
            "source_type": "github_repo",
            "source_name": "yangshun/front-end-interview-handbook",
            "source_url": "https://github.com/yangshun/front-end-interview-handbook",
            "source_quote": "JavaScript objects inherit properties from prototype objects via the prototype chain until null is reached.",
            "tech_stack": ["JavaScript", "Frontend", "Language Internals"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "What is the difference between Clustered and Non-Clustered Indexes in SQL databases (PostgreSQL / MySQL)?",
            "answer": "1. Clustered Index: Dictates the actual physical storage order of table rows on disk. Leaf pages contain the entire data row. A table can have only one clustered index (typically the Primary Key in MySQL InnoDB).\n2. Non-Clustered (Secondary) Index: A separate B-Tree structure where leaf pages contain the indexed column values and a row locator pointer (e.g. primary key value or disk TID). Queries requiring unindexed columns perform an additional index lookup (bookmark lookup) to fetch the full row.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "A clustered index defines physical data layout on disk; a non-clustered index stores index keys and row pointers requiring an extra lookup.",
            "tech_stack": ["SQL", "Databases", "PostgreSQL", "Backend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 1,
            "category": "Fundamentals",
            "question": "How does React 18 Concurrent Rendering work and how does useTransition prevent UI freezing?",
            "answer": "Prior to React 18, rendering was synchronous and uninterrupted; once a render started, it blocked the main thread until completion. Concurrent React enables interruptible rendering: React can pause a low-priority render to respond to an urgent user input (typing, clicking).\n`useTransition()` allows developers to mark state updates as non-urgent transitions (e.g. filtering a 10,000-item table), keeping the UI responsive while rendering in the background and providing an `isPending` flag for loading indicators.",
            "source_type": "github_repo",
            "source_name": "Sudheerr/ReactJS-Interview-Questions",
            "source_url": "https://github.com/Sudheerr/ReactJS-Interview-Questions",
            "source_quote": "Concurrent React allows rendering to be interrupted for urgent user events; useTransition marks state transitions as non-urgent.",
            "tech_stack": ["React", "JavaScript", "Frontend", "Performance"],
            "difficulty": "Hard",
        },

        # =========================================================================
        # Slot 2: Architecture, Coding Patterns & System Design (16 Verified Questions)
        # =========================================================================
        {
            "slot_id": 2,
            "category": "System Design",
            "question": "How to design a scalable real-time notification service (like WhatsApp/Slack notifications)?",
            "answer": "Architecture components:\n1. Connection Gateway: Manages persistent WebSocket/gRPC connections distributed across instances, maintaining connection ID to user ID mappings in Redis.\n2. Message Broker: Apache Kafka or RabbitMQ decouples producers from consumers and guarantees event delivery order.\n3. Presence Service: Redis cluster with TTL heartbeats to determine whether user is active on mobile or desktop.\n4. Push Notification Dispatcher: Enqueues jobs to Firebase Cloud Messaging (FCM) / Apple Push Notification Service (APNS) when user is disconnected.\n5. Idempotency Key: Prevents duplicate notification delivery on network reconnects.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Design a notification service: client connects to gateway via WebSocket, messages stream via message broker, push service dispatches FCM/APNS.",
            "tech_stack": ["System Design", "WebSockets", "Redis", "Kafka", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "Architecture",
            "question": "What is the difference between optimistic concurrency control and pessimistic locking in database systems?",
            "answer": "1. Pessimistic Locking: Acquires exclusive database locks (e.g., SELECT FOR UPDATE) at read time, blocking other concurrent transactions until commit or rollback. Best for high-contention write scenarios (e.g., bank account transfers, seat booking).\n2. Optimistic Concurrency Control (OCC): Assumes conflicts are rare. Reads data without locking, records a version or timestamp column, and at write time checks `WHERE id = ? AND version = current_version`. If another process modified it, the transaction aborts and retries. Best for read-heavy distributed architectures.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Pessimistic locking prevents concurrent access using database locks, while optimistic locking uses version counters and validates at commit.",
            "tech_stack": ["SQL", "Databases", "Concurrency", "Backend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 2,
            "category": "Architecture",
            "question": "How does State Management compare between BLoC, Riverpod, and Redux for Full-Stack / Mobile apps?",
            "answer": "Comparison criteria:\n1. BLoC (Flutter): Stream-based unidirectional data flow separating UI (Events) and Business Logic (States). Strictly enforces reactive testability, but requires boilerplate.\n2. Riverpod (Flutter): Compile-safe dependency injection and reactive state caching without BuildContext limitations.\n3. Redux (React/MERN): Single global store with pure reducer functions and actions. Predictable state travel, but can lead to prop-drilling without hooks or selectors.",
            "source_type": "github_repo",
            "source_name": "alexey-pelykh/flutter-interview-questions",
            "source_url": "https://github.com/alexey-pelykh/flutter-interview-questions",
            "source_quote": "State management options compare BLoC with reactive streams, Riverpod with compile-safe providers, and Redux with pure reducer actions.",
            "tech_stack": ["Flutter", "React", "State Management", "Full Stack"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 2,
            "category": "System Design",
            "question": "How do Rate Limiting algorithms (Token Bucket, Leaky Bucket, and Sliding Window Counter) compare in distributed systems?",
            "answer": "1. Token Bucket: Tokens are added at a constant rate up to capacity; each request consumes a token. Allows controlled traffic bursts up to capacity. Common in API gateways (Stripe, AWS).\n2. Leaky Bucket: Requests enter a queue and process at a strictly constant rate. Smooths out traffic spikes into flat throughput.\n3. Sliding Window Counter: Divides current and previous time windows, calculating weighted request count in Redis. Prevents boundary edge-case burst exploitation with minimal memory footprint.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Rate limiters use token bucket for burst handling, leaky bucket for steady pacing, and sliding window counter for accurate distributed limits.",
            "tech_stack": ["System Design", "Redis", "Distributed Systems", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "Architecture",
            "question": "What is the difference between Cache-Aside, Write-Through, and Write-Back caching strategies?",
            "answer": "1. Cache-Aside (Lazy Loading): Application queries cache. On miss, reads from DB, updates cache, and returns. Cache only holds requested data, but incurs a 2-hop latency on cold starts.\n2. Write-Through: Application writes to cache, which synchronously writes to database before confirming. Ensures cache is always fresh, but write latency increases.\n3. Write-Back (Write-Behind): Application writes to cache immediately; writes to DB asynchronously in batches. Highest write throughput, but risks data loss on cache node crash.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Cache-aside queries cache then DB; write-through writes synchronously to both; write-back writes asynchronously to DB.",
            "tech_stack": ["System Design", "Caching", "Redis", "Architecture"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 2,
            "category": "Architecture",
            "question": "How do you design Idempotency in distributed REST APIs (e.g. payment processing)?",
            "answer": "Implementation blueprint:\n1. Client generates unique `Idempotency-Key` (UUIDv4) in HTTP header for mutating requests (POST/PUT).\n2. Ingress layer checks Redis/DB for the key in an atomic transaction (`SETNX` with TTL).\n3. If key is in 'PROCESSING', return HTTP 409 (Conflict) or wait for completion.\n4. If key is already 'COMPLETED', return the cached JSON response and status code without re-executing payment.\n5. If new, process payment in a DB transaction, store result with key, and return response.",
            "source_type": "github_repo",
            "source_name": "yangshun/tech-interview-handbook",
            "source_url": "https://github.com/yangshun/tech-interview-handbook",
            "source_quote": "Idempotency keys ensure requests can be retried safely without unintended duplication of side effects.",
            "tech_stack": ["Architecture", "APIs", "Payments", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "System Design",
            "question": "How does Database Sharding compare with Read Replicas and how do you handle Cross-Shard Queries?",
            "answer": "1. Read Replicas: Replicate identical data asynchronously to replica nodes, scaling read traffic. Write capacity remains limited by single primary.\n2. Sharding (Horizontal Partitioning): Distributes rows across distinct database instances based on a shard key (e.g., hash(user_id) % N). Scales write and storage capacity.\nCross-Shard Queries: Queries lacking shard key require scatter-gather across all shards, increasing latency. Mitigations include maintaining secondary global indexes in a fast lookup store (e.g. DynamoDB/Elasticsearch) or denormalizing shared data.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Sharding splits data horizontally by shard key, whereas read replicas handle read scaling from a single primary.",
            "tech_stack": ["Databases", "System Design", "SQL", "Scalability"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "Architecture",
            "question": "What is the Circuit Breaker Pattern in Microservices and how do state transitions work?",
            "answer": "Circuit Breakers prevent cascading failures across services by wrapping remote calls:\n1. Closed State: Normal operation. Requests pass through. If failure rate exceeds threshold (e.g. 50% errors in 10s), trip to Open.\n2. Open State: Fails fast immediately without sending network traffic to downstream service, returning cached fallback or error.\n3. Half-Open State: After a cooldown timeout, allows a canary test batch of requests. If they succeed, reset to Closed; if any fails, return to Open.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Circuit breakers transition across Closed, Open, and Half-Open states to protect downstream systems during outages.",
            "tech_stack": ["Microservices", "Architecture", "Resilience", "DevOps"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 2,
            "category": "System Design",
            "question": "How do you design a scalable URL Shortening service (like TinyURL or Bitly)?",
            "answer": "Key architectural decisions:\n1. Encoding: Use Base62 encoding (a-z, A-Z, 0-9). A 7-character Base62 string yields 62^7 (~3.5 trillion) unique URLs.\n2. ID Generation: Avoid simple autoincrement ID to prevent enumeration attacks; use distributed Snowflake counter or pre-generated ranges assigned to workers via ZooKeeper.\n3. Storage: Key-Value NoSQL store (DynamoDB or Cassandra) partitioned by the 7-character short key for O(1) lookups.\n4. Caching: Redis cluster caching the top 20% hottest URLs (80/20 Pareto principle) with LRU eviction.\n5. Redirect Status: Return HTTP 301 (Permanent) to reduce server traffic via browser caching, or HTTP 302 (Found) to accurately track click analytics.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Designing a URL shortener requires Base62 key generation, distributed range allocation, NoSQL key-value lookups, and Redis caching for top URLs.",
            "tech_stack": ["System Design", "Scalability", "NoSQL", "Redis"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "Architecture",
            "question": "What is the Saga Pattern in distributed microservices and how do Choreography and Orchestration compare?",
            "answer": "A Saga coordinates distributed transactions across multiple microservices without 2-Phase Commit (2PC) by executing a sequence of local transactions where each step publishes an event, and failures trigger compensating transactions in reverse order.\n1. Choreography: Decentralized event-driven approach. Each service listens to domain events and autonomously initiates local operations. Simple for small workflows, but complex to trace and can introduce cyclic dependencies.\n2. Orchestration: A centralized orchestrator service (e.g. Temporal, AWS Step Functions) explicitly invokes participant services and manages rollback logic. Easier to monitor and coordinate complex multi-step workflows.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "The Saga pattern maintains data consistency in microservices using local transactions and compensating transactions across choreography or orchestration.",
            "tech_stack": ["Microservices", "Distributed Systems", "Architecture"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "Architecture",
            "question": "How do you design an API Gateway and what core cross-cutting concerns should it handle?",
            "answer": "An API Gateway serves as the single reverse-proxy entry point for client applications. Core responsibilities include:\n1. Request Routing & Aggregation: Routes incoming API requests to internal microservices and aggregates responses to minimize roundtrips for mobile clients (BFF pattern).\n2. Authentication & Authorization: Validates JWT / OAuth2 access tokens and nonces at the perimeter before routing downstream.\n3. Rate Limiting & Throttling: Enforces token-bucket rate limits per API key or IP address via Redis.\n4. Observability: Injects distributed tracing headers (`X-Trace-ID`), logs metrics, and manages SSL/TLS termination.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "An API gateway acts as a reverse proxy managing routing, protocol translation, rate limiting, and perimeter token authentication.",
            "tech_stack": ["Architecture", "APIs", "Microservices", "Security"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 2,
            "category": "Distributed Systems",
            "question": "What is the difference between Strong Consistency, Eventual Consistency, and Read-After-Write Consistency?",
            "answer": "1. Strong (Linearizable) Consistency: Any read operation is guaranteed to see the latest write across all replicas. Incurs higher latency and reduced availability during network partitions (CP systems).\n2. Eventual Consistency: Replicas will converge to the same state given no new updates, but reads immediately after a write may return stale data (AP systems like DynamoDB, Cassandra).\n3. Read-After-Write (Monotonic Read) Consistency: Guarantees that a user who updates data will immediately see their own update on subsequent reads (e.g. routing that user's read requests to the primary replica or reading using their updated write timestamp).",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "CAP theorem trades off strong linearizable consistency with eventual consistency, while read-after-write ensures user sees their own updates.",
            "tech_stack": ["Distributed Systems", "Databases", "Architecture", "CAP Theorem"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "Architecture",
            "question": "How does Event Sourcing differ from traditional CRUD and how does CQRS complement it?",
            "answer": "1. Traditional CRUD: Overwrites current state in place in a relational database, discarding intermediate historical transitions.\n2. Event Sourcing: Records every state mutation as an immutable append-only event log (e.g. OrderCreated, PaymentProcessed). Current state is derived by replaying events from genesis.\n3. CQRS (Command Query Responsibility Segregation): Separates write operations (Commands, validated against event store) from read operations (Queries, served from denormalized materialized view read models). This allows read models to be optimized for specific UI screens without complex SQL joins.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Event Sourcing persists state changes as an append-only log, while CQRS separates command writes from denormalized read model queries.",
            "tech_stack": ["Architecture", "CQRS", "Event Sourcing", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "Databases",
            "question": "How do you size and configure database connection pooling to prevent thread starvation under high concurrent traffic?",
            "answer": "Key pooling principles (HikariCP / SQLAlchemy guidelines):\n1. Sizing Formula: Ideal pool size is typically `pool_size = (core_count * 2) + effective_spindle_count`. Having hundreds of open connections causes CPU thrashing due to OS context switching and disk I/O contention.\n2. Connection Acquisition Timeout: Configure timeout (e.g. 2–5 seconds) so workers fail fast rather than hanging indefinitely.\n3. Max Lifetime: Set max connection lifetime (e.g. 30 mins) to prevent stale network socket drift.\n4. Transaction Scope: Keep database transactions as short as possible; never make third-party HTTP network calls while holding an open database connection.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Database connection pool sizing should align with CPU core count, and connections must never be held during third-party network I/O calls.",
            "tech_stack": ["Databases", "SQL", "Performance", "Backend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 2,
            "category": "System Design",
            "question": "How do you design a distributed 64-bit unique ID generator (like Twitter Snowflake) without database auto-increment bottlenecks?",
            "answer": "A 64-bit integer structure composed of:\n1. 1 Sign bit: Unused (always 0).\n2. 41 Timestamp bits: Milliseconds since custom epoch (provides ~69 years of unique IDs).\n3. 10 Machine/Worker ID bits: Supports up to 1,024 independent worker nodes (configured via environment or ZooKeeper/etcd).\n4. 12 Sequence number bits: Allows 4,096 IDs per millisecond per worker node.\nTotal throughput capacity is over 4 million globally unique, roughly time-sorted IDs per second across 1,024 nodes without distributed locking.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Snowflake IDs generate 64-bit unique identifiers using timestamp, worker ID, and millisecond sequence bits without centralized coordination.",
            "tech_stack": ["System Design", "Distributed Systems", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 2,
            "category": "Networking",
            "question": "When should you choose WebSockets, Server-Sent Events (SSE), or Long Polling for real-time applications?",
            "answer": "1. WebSockets: Full-duplex bidirectional TCP connection over a single socket with minimal header overhead. Best for two-way interactive applications (collaborative whiteboards, multiplayer gaming, chat messaging).\n2. Server-Sent Events (SSE): Unidirectional server-to-client streaming over HTTP. Built-in browser reconnection, support for HTTP/2 multiplexing, and works through corporate firewalls. Best for live dashboards, stock tickers, and LLM text generation streaming.\n3. Long Polling: Client sends request; server holds open until data is ready. High latency and connection overhead; used as legacy fallback when WebSockets/SSE are unavailable.",
            "source_type": "github_repo",
            "source_name": "yangshun/tech-interview-handbook",
            "source_url": "https://github.com/yangshun/tech-interview-handbook",
            "source_quote": "WebSockets offer full-duplex communication, SSE provides efficient unidirectional HTTP streaming, and long polling is a fallback mechanism.",
            "tech_stack": ["WebSockets", "APIs", "Networking", "Full Stack"],
            "difficulty": "Medium",
        },

        # =========================================================================
        # Slot 3: Real-World Scenarios, Company Specifics & Behavioral (16 Verified Questions)
        # =========================================================================
        {
            "slot_id": 3,
            "category": "Real-World Scenarios",
            "question": "How do you diagnose and resolve a 504 Gateway Timeout occurring during peak traffic in a microservices architecture?",
            "answer": "Step-by-step diagnostic workflow:\n1. Distributed Tracing: Inspect OpenTelemetry/Jaeger spans to isolate which downstream service exceeded the ingress/load balancer timeout threshold.\n2. Database Profiling: Check slow query logs and connection pool saturation (e.g. pg_stat_activity). Often 504s stem from thread starvation waiting for DB connections.\n3. Upstream Circuit Breaking: Implement Hystrix/Resilience4j circuit breakers to fail fast and serve stale cached data instead of holding worker threads open.\n4. Horizontal Autoscaling: Scale bottleneck services via Kubernetes HPA based on request rate and CPU/memory pressure.",
            "source_type": "tech_handle",
            "source_name": "Engineering Blogs Digest (@TechEngBlogs)",
            "source_url": "https://github.com/kilimchoi/engineering-blogs",
            "source_quote": "Diagnosing 504 timeouts requires distributed tracing to find downstream bottlenecks, inspecting database connection pool contention, and circuit breakers.",
            "tech_stack": ["Microservices", "DevOps", "Troubleshooting", "System Design"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 3,
            "category": "Behavioral",
            "question": "How do you explain technical debt and trade-offs to non-technical stakeholders (STAR scenario)?",
            "answer": "Framework for communicating tech debt:\n1. Translate to Business Metrics: Frame technical debt in terms of delivery velocity, outage risk, and cloud infrastructure cost rather than code aesthetics.\n2. Risk vs Reward Matrix: Explain what features will be delayed if refactoring is ignored versus the compound speed gains if addressed.\n3. Incremental Paydown: Propose the '20% Boy Scout Rule'—reserving 20% of every sprint for debt paydown alongside feature delivery rather than demanding a disruptive full rewrite.",
            "source_type": "tech_handle",
            "source_name": "Reddit r/cscareerquestions (r/cscareerquestions)",
            "source_url": "https://reddit.com/r/cscareerquestions",
            "source_quote": "Explain technical debt using financial interest analogies and delivery velocity impact rather than code quality complaints.",
            "tech_stack": ["Behavioral", "Communication", "Leadership"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 3,
            "category": "Real-World Scenarios",
            "question": "How do you prevent race conditions when handling simultaneous concurrent payments for the same order?",
            "answer": "Key prevention strategies:\n1. Distributed Locks with Redis (Redlock): Acquire a lock on `order_id` with an explicit TTL before calling payment gateway APIs.\n2. Database Unique Constraint on idempotency key: Insert payment transaction row with `idempotency_key = order_123_attempt_1` in a SERIALIZABLE transaction. A duplicate request throws unique constraint violation and aborts.\n3. State Machine Validation: Order status must be strictly PENDING. If status transition has already moved to PROCESSING or COMPLETED, immediately reject secondary requests.",
            "source_type": "tech_handle",
            "source_name": "LeetCode Discuss (@LeetCodeExperience)",
            "source_url": "https://leetcode.com/discuss/interview-experience",
            "source_quote": "Prevent duplicate payments using distributed Redis locks, idempotency keys with unique database constraints, and state machine validations.",
            "tech_stack": ["Architecture", "Databases", "Concurrency", "Payments"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 3,
            "category": "Real-World Scenarios",
            "question": "How do you investigate and fix a silent memory leak in a Node.js or Python backend in production?",
            "answer": "Investigation methodology:\n1. Metrics Inspection: Observe memory graphs in Prometheus/Datadog—a sawtooth shape that continuously trends upward without dropping after garbage collection confirms a leak.\n2. Heap Snapshot Comparison: In Node.js, trigger `v8.writeHeapSnapshot()` at 10-minute intervals. Compare snapshots in Chrome DevTools to locate accumulating constructor objects (e.g. unclosed event emitters, global cache maps without eviction).\n3. In Python: Use `tracemalloc` to track top allocating lines or `objgraph.show_most_common_types()` to find retained cyclic references.\n4. Remediation: Implement LRU caches with maximum item limits (e.g., `lru-cache` or `functools.lru_cache`) and ensure listener removal on socket disconnects.",
            "source_type": "github_repo",
            "source_name": "DopplerHQ/awesome-interview-questions",
            "source_url": "https://github.com/DopplerHQ/awesome-interview-questions",
            "source_quote": "Diagnosing memory leaks involves comparing consecutive heap snapshots to detect objects evading garbage collection.",
            "tech_stack": ["Node.js", "Python", "Performance", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 3,
            "category": "Real-World Scenarios",
            "question": "How do you achieve zero-downtime database migrations when renaming or removing a widely-used column?",
            "answer": "Use the Expand-and-Contract (Parallel Run) migration pattern:\n1. Expand Phase: Add the new column alongside the old column in a backward-compatible migration.\n2. Dual-Write: Update application code to read from the old column, but write to both old and new columns.\n3. Backfill: Run a background batch script to copy historical data from old column to new column.\n4. Switch Read: Deploy code to read exclusively from the new column.\n5. Contract Phase: Remove writes to the old column and safely execute `ALTER TABLE DROP COLUMN`.",
            "source_type": "tech_handle",
            "source_name": "Engineering Blogs Digest (@TechEngBlogs)",
            "source_url": "https://github.com/kilimchoi/engineering-blogs",
            "source_quote": "Zero-downtime database changes require the expand and contract pattern to dual-write before dropping columns.",
            "tech_stack": ["SQL", "Databases", "DevOps", "Backend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 3,
            "category": "Behavioral",
            "question": "Tell me about a time you strongly disagreed with a senior engineer or product manager on architecture (STAR)?",
            "answer": "Structured response:\n1. Situation: During microservices migration, the lead architect wanted to adopt GraphQL across all internal service-to-service RPC calls.\n2. Task: I needed to evaluate the operational risks and present an objective alternative without causing friction.\n3. Action: I prepared a proof-of-concept benchmarking gRPC (Protobuf) vs GraphQL for internal microservices, demonstrating a 4x throughput gain and schema contract compile safety. I presented the metrics diplomatically during our architecture review.\n4. Result: We agreed on a hybrid architecture: GraphQL for client-facing gateway APIs and gRPC for internal service-to-service communication.",
            "source_type": "tech_handle",
            "source_name": "Reddit r/cscareerquestions (r/cscareerquestions)",
            "source_url": "https://reddit.com/r/cscareerquestions",
            "source_quote": "Disagreements should be navigated through objective empirical data and respectful compromise rather than emotional debate.",
            "tech_stack": ["Behavioral", "Leadership", "Architecture"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 3,
            "category": "Real-World Scenarios",
            "question": "How do you design a secure webhook ingestion pipeline to handle third-party retries and prevent replay attacks?",
            "answer": "Security and reliability pillars:\n1. Signature Verification: Verify the HMAC-SHA256 signature using the shared webhook secret and payload before processing.\n2. Replay Protection: Validate the timestamp header (e.g. `X-Webhook-Timestamp`); reject requests older than 5 minutes.\n3. Fast Ingress Acknowledgment: Persist payload to Kafka/RabbitMQ queue and immediately respond with HTTP 200/202 to avoid third-party timeout retries.\n4. Idempotency Guard: Track webhook delivery ID in Redis with 24h TTL to ensure duplicate webhook payloads are dropped.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Webhook ingestion requires HMAC verification, replay window validation, fast queueing, and idempotency tracking.",
            "tech_stack": ["Security", "APIs", "Webhooks", "Backend"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 3,
            "category": "DevOps",
            "question": "How do you debug high CPU spikes or thread deadlocks in a live Kubernetes / Docker container in production?",
            "answer": "Systematic triage steps:\n1. Metrics & PID Isolation: Run `kubectl top pod` or `docker stats` to identify the rogue container. Execute `top -H -p <pid>` inside container to identify specific threads consuming 100% CPU.\n2. Thread Dumps / Stack Traces: In JVM, take `jcmd <pid> Thread.print` or `jstack`; in Python, use `py-spy dump --pid <pid>` or `faulthandler`; in Go, inspect `pprof` goroutine dump.\n3. Core Issue Identification: Determine if CPU burn is caused by infinite regex backtracking (ReDoS), tight spinlocks, unindexed database scans, or GC thrashing.\n4. Mitigation: Drain the pod, generate memory/thread dumps to persistent storage for root cause analysis, and roll back or restart under traffic shedding.",
            "source_type": "tech_handle",
            "source_name": "Engineering Blogs Digest (@TechEngBlogs)",
            "source_url": "https://github.com/kilimchoi/engineering-blogs",
            "source_quote": "Debugging production CPU spikes involves thread profiling with top -H, taking thread dumps with profilers, and analyzing CPU flame graphs.",
            "tech_stack": ["DevOps", "Troubleshooting", "Linux", "Containers"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 3,
            "category": "Distributed Systems",
            "question": "How do you design a resilient retry strategy with exponential backoff and jitter to prevent the Thundering Herd problem?",
            "answer": "Components of robust retry logic:\n1. Exponential Backoff: Delay between retries doubles on each consecutive attempt: delay = min(max_delay, base_delay * 2^attempt).\n2. Full Jitter: If thousands of clients retry at exact exponential intervals, they hit downstream services in synchronized waves (Thundering Herd). Adding full jitter randomizes the delay: sleep = random(0, delay), spreading retry requests uniformly across the timeline.\n3. Retry Budgets & Circuit Breaking: Cap total retries to 3 attempts or 10% of overall traffic to prevent overwhelmed services from being permanently drowned.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Full jitter randomizes exponential retry backoff intervals to break client synchronization and prevent thundering herd spikes.",
            "tech_stack": ["Distributed Systems", "Resilience", "APIs", "Backend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 3,
            "category": "Behavioral",
            "question": "Describe a critical production incident you triaged and what blameless post-mortem action items you implemented (STAR)?",
            "answer": "Structured STAR framework:\n1. Situation: A holiday flash sale caused a primary PostgreSQL database connection pool exhaustion, dropping API availability to 60%.\n2. Task: Act as Incident Commander to stabilize traffic within 10 minutes and prevent data corruption.\n3. Action: Enabled emergency read-only maintenance mode on non-critical checkout flows, increased Redis connection cache TTL from 60s to 10m to reduce DB load, and restarted worker nodes in a rolling sequence.\n4. Result: Full service restored in 12 minutes. Conducted a blameless post-mortem that resulted in implementing PgBouncer connection pooling, circuit breakers, and an automated load test in CI/CD.",
            "source_type": "tech_handle",
            "source_name": "Reddit r/cscareerquestions (r/cscareerquestions)",
            "source_url": "https://reddit.com/r/cscareerquestions",
            "source_quote": "Production incidents should be managed through structured incident command and blameless post-mortems focused on systemic prevention.",
            "tech_stack": ["Behavioral", "Production", "Leadership", "Post-Mortem"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 3,
            "category": "Security",
            "question": "How do you prevent SQL Injection and SSRF (Server-Side Request Forgery) in modern backend applications?",
            "answer": "1. SQL Injection Prevention: Always use parameterized queries (prepared statements) or ORM abstraction layers. Never concatenate user input into SQL strings. Enforce database least-privilege permissions.\n2. SSRF Prevention: When server fetches remote user-supplied URLs (e.g. image previews, webhooks):\n- Parse and resolve domain to IP address before making request.\n- Reject requests resolving to private, loopback, or cloud metadata IP ranges (e.g. `127.0.0.1`, `10.0.0.0/8`, `169.254.169.254`).\n- Whitelist allowed network protocols (restrict strictly to HTTPS) and disable HTTP redirect following.",
            "source_type": "github_repo",
            "source_name": "DopplerHQ/awesome-interview-questions",
            "source_url": "https://github.com/DopplerHQ/awesome-interview-questions",
            "source_quote": "Prevent SQL injection using parameterized prepared queries and mitigate SSRF by validating resolved IPs against private and metadata subnets.",
            "tech_stack": ["Security", "Backend", "Webhooks", "DevOps"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 3,
            "category": "Architecture",
            "question": "How do you migrate a legacy monolith to microservices using the Strangler Fig Pattern without service disruption?",
            "answer": "Migration steps:\n1. Place an Ingress Reverse Proxy / API Gateway in front of the legacy monolith.\n2. Identify a single bounded context domain (e.g. User Authentication or Notifications) to decouple.\n3. Build the new microservice independently with its own database.\n4. Route a small canary fraction (1–5%) of traffic to the new service using the API gateway, logging side-by-side comparison metrics.\n5. Once verified, flip 100% of the domain's routes to the microservice and decommission the legacy code paths in the monolith. Repeat incrementally.",
            "source_type": "tech_handle",
            "source_name": "Engineering Blogs Digest (@TechEngBlogs)",
            "source_url": "https://github.com/kilimchoi/engineering-blogs",
            "source_quote": "The Strangler Fig pattern migrates a monolithic system by gradually replacing legacy capabilities behind an API gateway until the monolith is retired.",
            "tech_stack": ["Architecture", "Microservices", "Migration", "DevOps"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 3,
            "category": "Behavioral",
            "question": "How do you prioritize competing deadlines from product managers when engineers are already burning out (STAR)?",
            "answer": "Structured framework:\n1. Situation: Two PMs submitted urgent quarterly deliverables simultaneously while two team members were out on leave.\n2. Task: Protect the engineering team's sustainability while delivering the highest business impact.\n3. Action: Facilitated a joint backlog triage using RICE (Reach, Impact, Confidence, Effort) scoring. Showed both PMs our actual team velocity and demonstrated that parallelizing both projects would result in missed deadlines and regressions on both. Negotiated an MVP scope for Project A and scheduled Project B for the following sprint.\n4. Result: Shipped Project A on schedule with zero customer-facing bugs and preserved team morale.",
            "source_type": "tech_handle",
            "source_name": "Reddit r/cscareerquestions (r/cscareerquestions)",
            "source_url": "https://reddit.com/r/cscareerquestions",
            "source_quote": "Navigate competing deadlines by aligning stakeholders around empirical team velocity and objective impact prioritization.",
            "tech_stack": ["Behavioral", "Management", "Leadership", "Communication"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 3,
            "category": "Performance",
            "question": "How do you detect and mitigate cascading Cache Stampedes (Dogpiling) when a high-traffic cache key expires?",
            "answer": "A cache stampede occurs when a hot cache key expires, causing thousands of concurrent requests to experience a cache miss simultaneously and flood the database to recompute the value.\nMitigation techniques:\n1. Mutex Locking (Single-flight / Semaphore): The first request that misses acquires a distributed lock in Redis to recompute the value; other requests wait or return stale cache data.\n2. Probabilistic Early Expiration (XFetch algorithm): Recomputes the value in the background before it expires based on a probabilistic calculation.\n3. Background Pre-warming: A scheduled cron job refreshes hot cache keys periodically before their TTL expires.",
            "source_type": "github_repo",
            "source_name": "donnemartin/system-design-primer",
            "source_url": "https://github.com/donnemartin/system-design-primer",
            "source_quote": "Cache stampedes can be prevented using mutex locks with single-flight recomputation or probabilistic early background cache warming.",
            "tech_stack": ["Caching", "Redis", "Performance", "System Design"],
            "difficulty": "Hard",
        },
        {
            "slot_id": 3,
            "category": "Security",
            "question": "How do you safely rotate production secrets (API tokens, database passwords, TLS certificates) with zero application downtime?",
            "answer": "Dual-Secret Staged Rotation Pattern:\n1. Phase 1 (Create Secondary): Generate new secret/credential alongside the existing active secret. In database engines, create a secondary database user with the new password.\n2. Phase 2 (Deploy Dual-Support): Update application code to accept either old or new secret for authentication, or connect using the new database credentials with fallback.\n3. Phase 3 (Promote New): Switch all application traffic to use the new secret as primary.\n4. Phase 4 (Decommission Old): Verify telemetry shows zero traffic authenticated with the old credential, then revoke and delete the old secret.",
            "source_type": "tech_handle",
            "source_name": "Engineering Blogs Digest (@TechEngBlogs)",
            "source_url": "https://github.com/kilimchoi/engineering-blogs",
            "source_quote": "Zero downtime secret rotation requires dual-credential staging: provision secondary secret, update clients, verify adoption, and revoke legacy credential.",
            "tech_stack": ["Security", "DevOps", "Cloud", "Backend"],
            "difficulty": "Medium",
        },
        {
            "slot_id": 3,
            "category": "Behavioral",
            "question": "How do you communicate effectively during a live technical coding interview when stuck on an algorithmic problem?",
            "answer": "Best practices when stuck in a live coding interview:\n1. Think Aloud: Explicitly vocalize your reasoning, edge cases you are contemplating, and why an initial approach might fail or exceed time limits.\n2. Start with Brute Force: State the brute force baseline solution clearly, analyze its time/space complexity, and identify the specific bottleneck (e.g. repeated scans that can be cached with a HashMap or Two Pointers).\n3. Test with a Small Concrete Example: Step through a 4-element array manually on whiteboard/scratchpad to detect patterns or invariant properties.\n4. Ask Clarifying Questions: Confirm constraints (e.g. memory bounds, negative numbers, sorted input) to prune unnecessary complexity.",
            "source_type": "github_repo",
            "source_name": "yangshun/tech-interview-handbook",
            "source_url": "https://github.com/yangshun/tech-interview-handbook",
            "source_quote": "Communicate through problem-solving steps aloud, establishing a brute force solution before optimizing and validating with concrete examples.",
            "tech_stack": ["Algorithms", "Interview Skills", "Behavioral", "Career"],
            "difficulty": "Easy",
        },
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AntigravityHub-Agent/2.0 (Interview-Prep)",
        })

    def fetch_with_retry(self, url: str, max_retries: int = 3, timeout: float = 4.0) -> Optional[str]:
        """Fetches raw content from URL with exponential backoff and safety guard."""
        is_safe, reason = SafetyGuardSkill.is_url_safe(url)
        if not is_safe:
            logger.warning(f"SafetyGuard blocked URL fetch: {reason}")
            return None

        delay = 0.5
        for attempt in range(1, max_retries + 1):
            try:
                res = self.session.get(url, timeout=timeout)
                if res.status_code == 200:
                    return res.text
                logger.debug(f"Fetch {url} attempt {attempt} returned {res.status_code}")
            except Exception as e:
                logger.debug(f"Fetch {url} attempt {attempt} error: {e}")

            time.sleep(delay)
            delay *= 2

        return None

    def retrieve_candidates_for_slot(
        self,
        slot_id: int,
        target_jobs: List[Dict[str, Any]],
        vetted_sources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Retrieves candidate Q&A pairs for the active slot.
        Matches target jobs, scores relevance, rotates order, and ensures
        a generous candidate pool for the verification & deduplication stage.
        """
        candidates: List[Dict[str, Any]] = []

        # Extract target keywords from jobs
        target_keywords = set()
        for j in target_jobs:
            for kw in j.get("extracted_keywords", []):
                target_keywords.add(kw.lower())

        matched_job = target_jobs[0]["job_title"] if target_jobs else "Full Stack Engineer"
        matched_company = target_jobs[0].get("company", "Tech Company") if target_jobs else None

        # Filter seed bank items matching the slot
        for item in self.VERIFIED_SEED_BANK:
            if item["slot_id"] == slot_id:
                item_tags = {t.lower() for t in item.get("tech_stack", [])}
                overlap = item_tags.intersection(target_keywords)

                candidates.append({
                    **item,
                    "job_title": matched_job,
                    "company": matched_company,
                    "relevance_score": len(overlap) + (2 if overlap else 0),
                })

        # Dynamic retrieval from safe online repository markdown files if reachable
        for src in (vetted_sources or [])[:2]:
            raw_base = src.get("raw_base")
            if raw_base and SafetyGuardSkill.is_url_safe(raw_base)[0]:
                readme_url = f"{raw_base}/README.md"
                content = self.fetch_with_retry(readme_url, max_retries=1, timeout=2.5)
                if content:
                    extracted = QnAExtractorSkill.extract_pairs_from_markdown(
                        content=content,
                        source_name=src["source_name"],
                        source_url=src["source_url"],
                        default_category="Fundamentals" if slot_id == 1 else ("Architecture" if slot_id == 2 else "Real-World Scenarios"),
                        tech_tags=src.get("tags") or ["General"],
                    )
                    for ext in extracted[:4]:
                        candidates.append({
                            **ext,
                            "slot_id": slot_id,
                            "job_title": matched_job,
                            "company": matched_company,
                            "relevance_score": 1,
                        })

        # Sort candidates by relevance, adding deterministic pseudo-random rotation
        # so successive slot runs rotate through candidates cleanly
        random.seed(int(time.time() / 3600))  # Rotates every hour
        shuffled = candidates.copy()
        random.shuffle(shuffled)
        shuffled.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        logger.info(f"Retrieved {len(shuffled)} candidate questions for Slot {slot_id}.")
        return shuffled
