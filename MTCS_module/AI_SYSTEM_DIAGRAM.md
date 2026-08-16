# Universal MTCS_module - Architecture Diagram

## System Overview Flowchart

```mermaid
flowchart TD
    %% Input Layer
    A[Task Configuration YAML] --> B[Task Manager]
    B --> C{System Initialization}
    
    %% Phase 1: Research Preparation
    C --> D[Phase 1: Research Preparation]
    D --> E[LLM Research Idea Generation]
    E --> F[Multi-Strategy Initialization]
    F --> G[Strategy 1: Standard ML]
    F --> H[Strategy 2: Research-Guided]
    F --> I[Strategy 3: Replication]
    F --> J[Strategy 4-7: Advanced Methods]
    
    %% Evaluation of Initial Solutions
    G --> K[Database Code Executor]
    H --> K
    I --> K
    J --> K
    K --> L[trae-agent Sandbox]
    L --> M[Performance Evaluation]
    M --> N[Select Best Root Node]
    
    %% Phase 2: Enhanced Tree Search
    N --> O[Phase 2: Enhanced Tree Search]
    O --> P[PUCT Node Selection]
    P --> Q[LLM Code Mutation]
    Q --> R[Prompt Strategy Selection]
    R --> S[Generate Improved Code]
    S --> T[Database Execution & Tracking]
    T --> U[Score Evaluation]
    U --> V[Backpropagation]
    V --> W{Max Iterations Reached?}
    W -->|No| P
    W -->|Yes| X[Phase 3: Solution Analysis]
    
    %% Phase 3: Solution Analysis
    X --> Y[Top Solution Analysis]
    Y --> Z[Hybrid Generation]
    Z --> AA[Performance Validation]
    AA --> BB[Final Best Solution]
    
    %% Output and Visualization
    BB --> CC[Tree Search Explorer]
    BB --> DD[Results Export]
    BB --> EE[Production-Ready Code]
    
    %% Database Integration
    T --> FF[SQLite Database]
    FF --> GG[Execution Node Tracking]
    GG --> HH[Manual Intervention Support]
    HH --> II[Monitoring Dashboard]
    
    %% Styling
    classDef phase1 fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef phase2 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef phase3 fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef database fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef output fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    
    class D,E,F,G,H,I,J phase1
    class O,P,Q,R,S,T,U,V,W phase2
    class X,Y,Z,AA,BB phase3
    class FF,GG,HH,II database
    class CC,DD,EE output
```

## Detailed Component Architecture

```mermaid
graph TB
    %% Core System Components
    subgraph "Universal MTCS_module"
        subgraph "Input Layer"
            TC[Task Configuration Engine<br/>core/task_manager.py]
            YC[YAML Config Files<br/>tasks/*/task_config.yaml]
        end
        
        subgraph "AI Processing Layer"
            LLM[Enhanced LLM Worker<br/>core/llm_worker_enhanced.py]
            PE[Prompt Engineering Library<br/>core/prompts/]
            PS[Prompt Strategy Manager<br/>Context-Aware Selection]
        end
        
        subgraph "Search & Control Layer"
            MSC[Multi-Phase Controller<br/>core/controller/db_enhanced_search.py]
            TS[Tree Search Algorithm<br/>PUCT Implementation]
            NS[Node Selection & Expansion]
        end
        
        subgraph "Execution Layer"
            DBE[Database Code Executor<br/>core/sandbox/db_code_executor.py]
            TA[trae-agent Integration<br/>Secure Sandboxed Execution]
            EV[Evaluation & Metrics]
        end
        
        subgraph "Data Management Layer"
            DB[(SQLite Database<br/>Execution Tracking)]
            DM[Database Manager<br/>core/database/db_manager.py]
            EN[Execution Nodes<br/>Comprehensive Metadata]
        end
        
        subgraph "Visualization Layer"
            TSE[Tree Search Explorer<br/>tree_search_explorer/]
            WUI[Web UI Interface<br/>Flask + D3.js]
            CV[Code Comparison & Analysis]
        end
    end
    
    %% External Dependencies
    subgraph "External Services"
        GEMINI[Gemini 2.5 Pro<br/>Google Vertex AI]
        OPENAI[OpenAI GPT Models<br/>Alternative LLM Backend]
    end
    
    %% Data Flow Connections
    YC --> TC
    TC --> MSC
    MSC --> LLM
    LLM --> PE
    PE --> PS
    PS --> TS
    TS --> NS
    NS --> DBE
    DBE --> TA
    TA --> EV
    EV --> DM
    DM --> DB
    DB --> EN
    EN --> TSE
    TSE --> WUI
    WUI --> CV
    
    %% External Connections
    LLM -.-> GEMINI
    LLM -.-> OPENAI
    
    %% Styling
    classDef input fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef ai fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef search fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef execution fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef data fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef viz fill:#f1f8e9,stroke:#558b2f,stroke-width:2px
    classDef external fill:#fafafa,stroke:#616161,stroke-width:2px
    
    class TC,YC input
    class LLM,PE,PS ai
    class MSC,TS,NS search
    class DBE,TA,EV execution
    class DB,DM,EN data
    class TSE,WUI,CV viz
    class GEMINI,OPENAI external
```

## Multi-Phase Execution Flow

```mermaid
sequenceDiagram
    participant U as User
    participant TC as Task Config
    participant MSC as Multi-Phase Controller
    participant LLM as LLM Worker
    participant DBE as DB Executor
    participant TA as trae-agent
    participant DB as Database
    participant TSE as Tree Explorer
    
    %% Initialization
    U->>TC: Load task_config.yaml
    TC->>MSC: Initialize system
    
    %% Phase 1: Research Preparation
    Note over MSC,LLM: Phase 1: Research Preparation
    MSC->>LLM: Generate research ideas
    LLM-->>MSC: Domain-specific concepts
    MSC->>LLM: Multi-strategy initialization (7 strategies)
    
    loop For each strategy
        LLM->>DBE: Generate initial code
        DBE->>TA: Execute in sandbox
        TA-->>DBE: Results + auto-fixes
        DBE->>DB: Store execution node
    end
    
    MSC->>MSC: Select best root node
    
    %% Phase 2: Enhanced Tree Search
    Note over MSC,DB: Phase 2: Enhanced Tree Search
    loop PUCT Tree Search (max iterations)
        MSC->>MSC: PUCT node selection
        MSC->>LLM: Generate code mutation
        LLM->>DBE: Mutated code
        DBE->>TA: Execute & evaluate
        TA-->>DBE: Performance metrics
        DBE->>DB: Update node status
        MSC->>MSC: Backpropagate scores
        
        alt Breakthrough detected
            MSC->>MSC: Update best solution
        end
        
        alt Manual intervention needed
            DBE->>U: Flag for manual review
            U->>DBE: Corrected code
        end
    end
    
    %% Phase 3: Solution Analysis
    Note over MSC,DB: Phase 3: Solution Analysis
    MSC->>MSC: Analyze top solutions
    MSC->>LLM: Generate hybrid solutions
    LLM->>DBE: Hybrid code
    DBE->>TA: Final evaluation
    TA-->>DBE: Validation results
    DBE->>DB: Store final results
    
    %% Results & Visualization
    MSC->>TSE: Trigger visualization
    TSE->>DB: Load execution data
    DB-->>TSE: Complete search tree
    TSE->>U: Interactive explorer
    
    U->>TSE: Explore results
    TSE-->>U: Code comparison & analysis
```

## Performance Breakthrough Detection

```mermaid
flowchart LR
    A[New Code Execution] --> B{Score > Parent?}
    B -->|Yes| C{Score > Best Global?}
    B -->|No| D[Record as Exploration]
    
    C -->|Yes| E[🎉 BREAKTHROUGH!<br/>Update Global Best]
    C -->|No| F[Local Improvement]
    
    E --> G[Log Breakthrough Event]
    F --> G
    D --> G
    
    G --> H[Update Tree Search Statistics]
    H --> I[Trigger Explorer Visualization]
    
    %% Breakthrough Types
    E --> J[Strategy Breakthrough<br/>New approach works]
    E --> K[Performance Breakthrough<br/>Significant score jump]
    E --> L[Perfect Score Achieved<br/>AUC = 1.0000]
    
    %% Styling
    classDef breakthrough fill:#4caf50,stroke:#1b5e20,stroke-width:3px,color:#fff
    classDef improvement fill:#2196f3,stroke:#0d47a1,stroke-width:2px,color:#fff
    classDef exploration fill:#ff9800,stroke:#e65100,stroke-width:2px,color:#fff
    classDef perfect fill:#e91e63,stroke:#880e4f,stroke-width:3px,color:#fff
    
    class E,G breakthrough
    class F,H improvement
    class D exploration
    class L perfect
```

## Database-Driven Execution Model

```mermaid
erDiagram
    EXECUTION_NODE {
        string node_id PK
        string parent_id FK
        int generation
        string mutation_type
        text code
        string execution_status
        float score
        float execution_duration
        int auto_fixes
        text error_message
        datetime created_at
        datetime updated_at
    }
    
    SEARCH_RUN {
        string run_id PK
        string task_name
        datetime start_time
        datetime end_time
        float best_score
        int total_nodes
        float success_rate
        json configuration
    }
    
    BREAKTHROUGH_EVENT {
        string event_id PK
        string node_id FK
        string run_id FK
        float old_score
        float new_score
        float improvement
        string breakthrough_type
        datetime timestamp
    }
    
    EXECUTION_NODE ||--o{ EXECUTION_NODE : "parent-child"
    SEARCH_RUN ||--o{ EXECUTION_NODE : "contains"
    EXECUTION_NODE ||--o{ BREAKTHROUGH_EVENT : "triggers"
    SEARCH_RUN ||--o{ BREAKTHROUGH_EVENT : "belongs_to"
```

## Key Achievements Visualization

```mermaid
gitgraph
    commit id: "Start: 0.5111 AUC"
    branch logistic_regression
    checkout logistic_regression
    commit id: "Replicate LR: 0.9845"
    
    checkout main
    branch random_forest
    commit id: "Replicate RF: 0.9924"
    
    checkout main
    branch target_improvement
    commit id: "Target Improve: 0.9787"
    
    checkout main
    branch perfect_solution
    commit id: "🎉 PERFECT: 1.0000 AUC"
    commit id: "Confirmed: 1.0000 AUC"
    
    checkout main
    merge logistic_regression
    merge random_forest
    merge target_improvement
    merge perfect_solution
    commit id: "Final Best: 1.0000"
    commit id: "69.2% Success Rate"
    commit id: "40.2 min Runtime"
```