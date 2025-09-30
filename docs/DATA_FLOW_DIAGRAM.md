# TraceOne Monitoring System - Data Flow Diagram

## Complete System Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            D&B API ECOSYSTEM                                   │
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │   Auth Server   │    │   Management    │    │      Pull API              │ │
│  │                 │    │      API        │    │                             │ │
│  │ /v3/token       │    │                 │    │ /v1/notifications/pull      │ │
│  │                 │    │ /registrations  │    │ /v1/notifications/replay    │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ↕ HTTP/REST API
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          TRACEONE MONITORING SERVICE                           │
│                                                                                 │
│ ┌───────────────────────────────────────────────────────────────────────────┐   │
│ │                          SERVICE INITIALIZATION                          │   │
│ │                                                                           │   │
│ │  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐   │   │
│ │  │   Config    │  │  DNB API Auth   │  │     Component Setup         │   │   │
│ │  │   Loader    │→ │  Authenticator  │→ │                             │   │   │
│ │  │             │  │                 │  │ • API Client (rate limited) │   │   │
│ │  │ YAML + ENV  │  │ OAuth2 Tokens   │  │ • Pull Client               │   │   │
│ │  └─────────────┘  └─────────────────┘  │ • Registration Manager      │   │   │
│ │                                         │ • Storage Handlers          │   │   │
│ │                                         └─────────────────────────────┘   │   │
│ └───────────────────────────────────────────────────────────────────────────┘   │
│                                         ↓                                       │
│ ┌───────────────────────────────────────────────────────────────────────────┐   │
│ │                      REGISTRATION MANAGEMENT                             │   │
│ │                                                                           │   │
│ │  ┌─────────────────┐     ┌─────────────────────────────────────────────┐ │   │
│ │  │  Registration   │ ──→ │              D&B API                       │ │   │
│ │  │  Configuration  │     │                                             │ │   │
│ │  │                 │     │  POST /registrations                       │ │   │
│ │  │ • Reference     │     │  {                                          │ │   │
│ │  │ • DUNS List     │     │    "reference": "company_monitor_001",     │ │   │
│ │  │ • Data Blocks   │     │    "duns": ["123456789", "987654321"],     │ │   │
│ │  │ • JSON Paths    │     │    "dataBlocks": ["companyinfo_L2_v1"],    │ │   │
│ │  │ • Delivery      │     │    "jsonPathInclusion": ["primaryName"]    │ │   │
│ │  └─────────────────┘     │  }                                          │ │   │
│ │                           └─────────────────────────────────────────────┘ │   │
│ └───────────────────────────────────────────────────────────────────────────┘   │
│                                         ↓                                       │
│ ┌───────────────────────────────────────────────────────────────────────────┐   │
│ │                    CONTINUOUS MONITORING LOOP                            │   │
│ │                                                                           │   │
│ │  ┌─────────────────┐     ┌─────────────────────────────────────────────┐ │   │
│ │  │   Timer Loop    │ ──→ │           Pull API Request                  │ │   │
│ │  │                 │     │                                             │ │   │
│ │  │ Polling Interval│     │  GET /v1/notifications/pull                │ │   │
│ │  │ (300 seconds)   │     │  ?reference=company_monitor_001             │ │   │
│ │  │                 │     │  &maxNotifications=100                     │ │   │
│ │  │ Rate Limiting   │     │                                             │ │   │
│ │  │ (5 req/sec)     │     │  Response:                                  │ │   │
│ │  │                 │     │  {                                          │ │   │
│ │  │ Error Handling  │     │    "notifications": [                      │ │   │
│ │  │ & Retry Logic   │     │      {                                      │ │   │
│ │  └─────────────────┘     │        "organization": {"duns": "123..."},  │ │   │
│ │                           │        "type": "UPDATE",                    │ │   │
│ │                           │        "elements": [...],                   │ │   │
│ │                           │        "deliveryTimeStamp": "2025-09..."    │ │   │
│ │                           │      }                                      │ │   │
│ │                           │    ]                                        │ │   │
│ │                           │  }                                          │ │   │
│ │                           └─────────────────────────────────────────────┘ │   │
│ └───────────────────────────────────────────────────────────────────────────┘   │
│                                         ↓                                       │
│ ┌───────────────────────────────────────────────────────────────────────────┐   │
│ │                    NOTIFICATION PROCESSING PIPELINE                      │   │
│ │                                                                           │   │
│ │  Notification  →  Parse & →  Validate  →  Route to  →  Mark as           │   │
│ │  Received         Validate   Structure    Handlers     Processed         │   │
│ │                                                                           │   │
│ │  ┌─────────────────────────────────────────────────────────────────────┐ │   │
│ │  │                    MULTI-HANDLER PROCESSING                        │ │   │
│ │  │                                                                     │ │   │
│ │  │  Handler 1 ──┐                                                     │ │   │
│ │  │  (SFTP)      │                                                     │ │   │
│ │  │              ├── Process Notification ──→ Storage Success/Failure │ │   │
│ │  │  Handler 2 ──┤    (Parallel execution)                            │ │   │
│ │  │  (Local)     │                                                     │ │   │
│ │  │              │    • Error isolation                                │ │   │
│ │  │  Handler N ──┘    • Independent processing                        │ │   │
│ │  │  (Custom)         • Detailed logging                              │ │   │
│ │  └─────────────────────────────────────────────────────────────────────┘ │   │
│ └───────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                         ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            STORAGE BACKENDS                                     │
│                                                                                 │
│ ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐   │
│ │    SFTP STORAGE     │  │   LOCAL STORAGE     │  │    DATABASE STORAGE    │   │
│ │                     │  │                     │  │                         │   │
│ │ • SSH Connection    │  │ • File System       │  │ • PostgreSQL/MySQL     │   │
│ │ • Directory Structure│ │ • Directory Structure│ │ • Normalized Schema     │   │
│ │ • File Formats      │  │ • File Formats      │  │ • Indexed Queries       │   │
│ │ • Compression       │  │ • Permissions       │  │ • Transactions          │   │
│ │ • Retry Logic       │  │ • Statistics        │  │ • Backup/Recovery       │   │
│ │                     │  │                     │  │                         │   │
│ │ /notifications/     │  │ ./notifications/    │  │ Tables:                 │   │
│ │ └── 2025/09/14/     │  │ └── 2025/09/14/     │  │ • notifications         │   │
│ │     └── reg_001/    │  │     └── reg_001/    │  │ • elements              │   │
│ │         └── file.json│ │         └── file.json│ │ • organizations         │   │
│ └─────────────────────┘  └─────────────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Transformation Flow

```
D&B Notification (Raw API Response)
           ↓
┌─────────────────────────────────────────────┐
│ {                                           │
│   "transactionDetail": {                   │
│     "transactionID": "abc123",             │
│     "transactionTimestamp": "2025-09-14..."│
│   },                                       │
│   "inquiryDetail": {                       │
│     "reference": "company_monitor_001"      │
│   },                                       │
│   "organization": {                        │
│     "duns": "123456789",                   │
│     "primaryName": "Updated Company Name", │
│     "registeredAddress": {...}             │
│   },                                       │
│   "changeTransactionInformation": {...}    │
│ }                                          │
└─────────────────────────────────────────────┘
           ↓ Parse & Validate
┌─────────────────────────────────────────────┐
│        Notification Object                  │
│                                             │
│ • id: UUID (generated)                     │
│ • type: NotificationType.UPDATE            │
│ • organization: Organization(duns="123...")│
│ • elements: [NotificationElement(...)]     │
│ • delivery_timestamp: datetime             │
│ • processed: false                         │
│ • processing_timestamp: null               │
└─────────────────────────────────────────────┘
           ↓ Storage Transformation
┌─────────────────────────────────────────────┐
│      Storage Format (JSON Example)         │
│                                             │
│ {                                          │
│   "metadata": {                            │
│     "export_timestamp": "2025-09-14...",   │
│     "notification_count": 1,               │
│     "format_version": "1.0",               │
│     "storage_type": "local_file",          │
│     "registration_reference": "comp..."    │
│   },                                       │
│   "notifications": [                       │
│     {                                      │
│       "id": "uuid-here",                   │
│       "type": "UPDATE",                    │
│       "organization": {"duns": "123..."},  │
│       "elements": [                        │
│         {                                  │
│           "element": "primaryName",        │
│           "previous": "Old Name",          │
│           "current": "New Name",           │
│           "timestamp": "2025-09-14..."     │
│         }                                  │
│       ],                                   │
│       "processing_timestamp": "2025-09..." │
│     }                                      │
│   ]                                        │
│ }                                          │
└─────────────────────────────────────────────┘
```

## Background Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ASYNC TASK MANAGER                                   │
│                                                                                 │
│ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│ │  Registration   │  │  Registration   │  │         Task Pool               │   │
│ │      #001       │  │      #002       │  │                                 │   │
│ │                 │  │                 │  │ • Concurrent Execution          │   │
│ │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ • Error Isolation               │   │
│ │ │Background   │ │  │ │Background   │ │  │ • Resource Management          │   │
│ │ │Task         │ │  │ │Task         │ │  │ • Health Monitoring             │   │
│ │ │             │ │  │ │             │ │  │ • Graceful Shutdown             │   │
│ │ │Poll → Store │ │  │ │Poll → Store │ │  │                                 │   │
│ │ │    ↓        │ │  │ │    ↓        │ │  │ Task Lifecycle:                 │   │
│ │ │ Sleep(300s) │ │  │ │ Sleep(300s) │ │  │ START → RUN → ERROR → RESTART  │   │
│ │ │    ↑        │ │  │ │    ↑        │ │  │          ↓                      │   │
│ │ │    └────────┘ │  │ │    └────────┘ │  │        STOP                     │   │
│ │ └─────────────┘ │  │ └─────────────┘ │  │                                 │   │
│ └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘   │
│                                                                                 │
│                    All tasks run concurrently and independently                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Error Handling & Recovery Flow

```
┌─────────────────┐
│   Operation     │
│   Attempted     │
└─────────────────┘
         ↓
    ┌─────────┐
    │Success? │ ──Yes──→ ┌─────────────┐
    └─────────┘          │ Continue    │
         ↓ No             │ Processing  │
┌─────────────────┐      └─────────────┘
│  Error Type?    │
└─────────────────┘
         ↓
┌─────────────────┐      ┌─────────────────┐
│  Transient      │ ──→  │ Exponential     │ ──→ ┌─────────┐
│  (Network,      │      │ Backoff Retry   │     │ Retry   │
│   Rate Limit)   │      │ (1s, 2s, 4s...) │     │Operation│
└─────────────────┘      └─────────────────┘     └─────────┘
         ↓
┌─────────────────┐      ┌─────────────────┐
│  Permanent      │ ──→  │ Log Error &     │ ──→ ┌─────────┐
│  (Auth Failure, │      │ Alert Ops Team  │     │Continue │
│   Config Error) │      │ Disable Component│     │w/o Failed│
└─────────────────┘      └─────────────────┘     │Component│
         ↓                                        └─────────┘
┌─────────────────┐      ┌─────────────────┐
│  Storage Error  │ ──→  │ Try Alternative │ ──→ ┌─────────┐
│  (SFTP Down,    │      │ Storage Backend │     │Store to │
│   Disk Full)    │      │ (Local → SFTP)  │     │Available│
└─────────────────┘      └─────────────────┘     │Backend  │
                                                  └─────────┘
```

This diagram shows how the complete TraceOne monitoring system processes data from the D&B API through to multiple storage backends, with robust error handling and background task management.
