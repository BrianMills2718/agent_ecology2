# README Diagram Drafts

For review - these will be integrated into the README.

## Single Agent Internal Architecture

```mermaid
graph TD
    subgraph Agent["Agent: Market Maker"]
        LLM[LLM Core]

        subgraph Workflow["State Machine"]
            S1[monitor] -->|signal detected| S2[analyze]
            S2 -->|opportunity found| S3[plan]
            S3 -->|plan ready| S4[execute]
            S4 -->|complete| S1
            S2 -->|no opportunity| S1
        end

        subgraph Memory["Memory Artifacts"]
            RAG[(RAG Store)]
            KG[(Knowledge Graph)]
            Work[Working Memory]
        end

        subgraph Tools["Self-Built Tools"]
            T1[price_checker]
            T2[risk_scorer]
            T3[order_builder]
        end

        LLM --> Workflow
        Workflow -->|query| RAG
        Workflow -->|lookup| KG
        Workflow -->|invoke| Tools
        Tools -->|results| Workflow
    end
```

## Capital Structure (Code Dependencies)

```mermaid
graph BT
    subgraph Primitives["Primitive Tools"]
        JSON[json_parser]
        HTTP[http_client]
        Math[math_utils]
        String[string_fmt]
        Store[kv_store]
    end

    subgraph Libraries["Composed Libraries"]
        API[api_client]
        Validate[data_validator]
        Cache[cache_layer]
        Report[report_builder]
    end

    subgraph Modules["Functional Modules"]
        Monitor[market_monitor]
        Executor[trade_executor]
        Notifier[alert_system]
    end

    subgraph Product["Product"]
        Bot[trading_bot]
    end

    JSON -->|"parse responses"| API
    HTTP -->|"raw requests"| API

    JSON -->|"schema check"| Validate
    Math -->|"range check"| Validate

    Store -->|"read/write"| Cache
    JSON -->|"serialize"| Cache

    String -->|"templates"| Report
    Math -->|"calculations"| Report

    API -->|"market data"| Monitor
    Cache -->|"historical"| Monitor
    Validate -->|"clean data"| Monitor

    API -->|"order submission"| Executor
    Validate -->|"order validation"| Executor

    Report -->|"format alerts"| Notifier
    API -->|"send alerts"| Notifier

    Monitor -->|"signals"| Bot
    Executor -->|"execution"| Bot
    Notifier -->|"notifications"| Bot
```

## Organization Structure (Ostrom/DAO Style)

```mermaid
graph TD
    subgraph Commons["Shared Commons"]
        Treasury[(Shared Treasury)]
        Knowledge[(Knowledge Base)]
        Infra[Shared Infrastructure]
    end

    subgraph Governance["Governance Layer"]
        Access[Access Contract]
        Voting[Voting Contract]
        Dispute[Dispute Resolution]
    end

    subgraph WorkGroups["Work Groups"]
        subgraph Guild1["Research Guild"]
            A1[Agent A]
            A2[Agent B]
        end

        subgraph Guild2["Trading Guild"]
            A3[Agent C]
            A4[Agent D]
        end

        subgraph Guild3["Infrastructure Guild"]
            A5[Agent E]
        end
    end

    subgraph JointVentures["Cross-Guild Projects"]
        JV1[Joint Project X]
        JV2[Joint Project Y]
    end

    Access -->|"governs"| Treasury
    Access -->|"governs"| Knowledge
    Voting -->|"modifies"| Access
    Dispute -->|"resolves"| Voting

    A1 & A2 -->|"contribute"| Knowledge
    A3 & A4 -->|"contribute"| Treasury
    A5 -->|"maintains"| Infra

    Guild1 -->|"research for"| JV1
    Guild2 -->|"capital for"| JV1
    Guild2 -->|"execution for"| JV2
    Guild3 -->|"infra for"| JV1 & JV2

    JV1 -->|"profits to"| Treasury
    JV2 -->|"profits to"| Treasury
```

## Action Chain (Immediate Caller Model)

```mermaid
sequenceDiagram
    participant A as Agent A
    participant B as Artifact B<br/>(escrow)
    participant C as Artifact C<br/>(ledger)

    A->>B: invoke(deposit, 100)
    Note over B: B's contract checks:<br/>caller = A ✓

    B->>C: invoke(transfer, A→escrow, 100)
    Note over C: C's contract checks:<br/>caller = B (not A!)

    C-->>B: success
    B-->>A: deposit confirmed

    Note over A,C: C never sees A directly.<br/>B is the immediate caller.<br/>This enables trustless delegation.
```

## The Narrow Waist (5 Actions)

```mermaid
graph LR
    subgraph Agents
        A1[Agent 1]
        A2[Agent 2]
        A3[Agent N]
    end

    subgraph Actions["5 Actions<br/>(the narrow waist)"]
        direction TB
        invoke[invoke]
        read[read]
        write[write]
        edit[edit]
        delete[delete]
    end

    subgraph Artifacts
        Art1[Ledger]
        Art2[Escrow]
        Art3[Custom Code]
        Art4[Memory]
        Art5[Contract]
    end

    A1 & A2 & A3 --> invoke
    A1 & A2 & A3 --> read
    A1 & A2 & A3 --> write
    A1 & A2 & A3 --> edit
    A1 & A2 & A3 --> delete

    invoke --> Art1 & Art2 & Art3
    read --> Art1 & Art2 & Art3 & Art4 & Art5
    write --> Art3 & Art4
    edit --> Art3 & Art4
    delete --> Art3 & Art4
```
