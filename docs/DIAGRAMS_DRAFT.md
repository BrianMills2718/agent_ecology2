# README Diagram Drafts

For review - these will be integrated into the README.

## Single Agent Architecture

```mermaid
graph TD
    subgraph Agent["Agent"]
        subgraph Workflow["State Machine"]
            S1[observe] -->|"new info"| S2[analyze]
            S2 -->|"insight"| S3[plan]
            S3 -->|"ready"| S4[act]
            S4 -->|"result"| S5[learn]
            S5 --> S1
            S2 -->|"uncertain"| S1
        end

        subgraph Knowledge["Knowledge Artifacts"]
            RAG[(Experience<br/>Memory)]
            KG[(Knowledge<br/>Graph)]
            Work[Working<br/>Memory]
        end

        subgraph Tools["Self-Built Tools"]
            T1[artifact_searcher]
            T2[contract_analyzer]
            T3[strategy_evaluator]
        end

        subgraph Config["Config (tradeable)"]
            Prompt[system_prompt]
            Model[model_choice]
            Params[parameters]
        end

        Workflow -->|"recall"| RAG
        Workflow -->|"query relationships"| KG
        Workflow -->|"current context"| Work
        Workflow -->|"invoke"| Tools
        S5 -->|"store insight"| RAG
        S5 -->|"update relations"| KG
    end
```

## Capital Structure

Shows how agents build artifacts that increase their collective capability. Two different high-level capabilities share underlying infrastructure - like how steel serves both auto and construction industries.

```mermaid
graph BT
    subgraph Foundation["Foundation Tools"]
        Parse[text_parser]
        Embed[embedder]
        Store[vector_store]
        Graph[graph_db]
        Reason[inference_engine]
    end

    subgraph Knowledge["Knowledge Infrastructure"]
        KG[knowledge_graph_builder]
        Retriever[semantic_retriever]
        Patterns[pattern_detector]
    end

    subgraph Understanding["Understanding Layer"]
        EntityEx[entity_extractor]
        RelationEx[relation_extractor]
        Summarizer[context_summarizer]
    end

    subgraph Capabilities["Agent Capabilities"]
        Strategic[strategic_planner]
        Social[social_modeler]
    end

    Parse -->|"tokenized text"| Embed
    Embed -->|"vectors"| Store
    Embed -->|"vectors"| Graph

    Store -->|"similarity search"| Retriever
    Graph -->|"structured data"| KG
    Reason -->|"inference rules"| KG

    KG -->|"entity context"| EntityEx
    Retriever -->|"relevant docs"| EntityEx
    KG -->|"known relations"| RelationEx
    Patterns -->|"templates"| RelationEx

    Store -->|"historical"| Patterns
    Reason -->|"logic"| Patterns

    EntityEx -->|"entities"| Summarizer
    RelationEx -->|"relations"| Summarizer
    Retriever -->|"context"| Summarizer

    Summarizer -->|"world model"| Strategic
    KG -->|"causal chains"| Strategic
    Patterns -->|"what worked"| Strategic
    Reason -->|"planning"| Strategic

    Summarizer -->|"agent profiles"| Social
    KG -->|"interaction history"| Social
    Patterns -->|"behavior patterns"| Social
    Reason -->|"prediction"| Social
```

**Key insight**: `knowledge_graph_builder`, `semantic_retriever`, and `pattern_detector` are shared infrastructure. Both `strategic_planner` (for planning actions) and `social_modeler` (for understanding other agents) depend on them. Building better knowledge infrastructure benefits ALL higher-level capabilities.

## Organization Structure (Ostrom/DAO Style)

```mermaid
graph TD
    subgraph Commons["Shared Commons"]
        Treasury[(Shared<br/>Treasury)]
        Knowledge[(Collective<br/>Knowledge)]
        Infra[Shared<br/>Infrastructure]
    end

    subgraph Governance["Governance Layer"]
        Access[Access Contract<br/>who can use what]
        Voting[Voting Contract<br/>how rules change]
        Dispute[Dispute Contract<br/>conflict resolution]
    end

    subgraph WorkGroups["Overlapping Work Groups"]
        subgraph Guild1["Research Guild"]
            A1[Agent A]
            A2[Agent B]
        end

        subgraph Guild2["Building Guild"]
            A3[Agent C]
            A4[Agent D]
        end

        subgraph Guild3["Infrastructure Guild"]
            A5[Agent E]
        end
    end

    subgraph JointVentures["Cross-Guild Collaborations"]
        JV1[Project Alpha]
        JV2[Project Beta]
    end

    Access -->|"governs"| Treasury
    Access -->|"governs"| Knowledge
    Voting -->|"can modify"| Access
    Dispute -->|"appeals to"| Voting

    A1 & A2 -->|"contribute findings"| Knowledge
    A3 & A4 -->|"contribute scrip"| Treasury
    A5 -->|"maintains"| Infra

    Guild1 -->|"research"| JV1
    Guild2 -->|"building"| JV1
    Guild2 -->|"building"| JV2
    Guild3 -->|"infra"| JV1 & JV2

    JV1 -->|"returns"| Treasury
    JV2 -->|"returns"| Treasury

    A2 -.->|"also member"| Guild2
    A4 -.->|"also member"| Guild3
```

**Key features**: Overlapping membership (A2 in two guilds), shared commons with governance, joint ventures that combine capabilities, dispute resolution without central authority.
