# Multi-Platform Export & Publishing Fan-Out Flow

Feature 1 allows a single approved video project to fan out into platform-specific deliverables for YouTube Shorts, TikTok, and Instagram Reels. Each destination receives custom aspect-ratio muxing via FFmpeg, followed by mandatory Gate 8 export completeness verification before routing to either automated YouTube OAuth distribution or secure manual-export package generation for TikTok and Instagram Reels.

```mermaid
flowchart LR
    classDef live fill:#2e7d32,stroke:#1b5e20,stroke-width:2px,color:#fff;
    classDef gate fill:#c62828,stroke:#b71c1c,stroke-width:2px,color:#fff;
    classDef package fill:#1565c0,stroke:#0d47a1,stroke-width:2px,color:#fff;
    classDef roadmap fill:#424242,stroke:#757575,stroke-width:2px,stroke-dasharray: 3 3,color:#fff;

    ApprovedProject([1 Approved Project
    Status: VIDEO_APPROVED]):::package --> Stitcher[FFmpeg Multi-Platform Engine
    Generates 9:16 Vertical Masters]:::live

    subgraph Fan_Out ["Platform-Specific Media Exports"]
        Stitcher --> ExportYT["YouTube Shorts Export
        (output_asset_ref: .mp4)"]:::live
        Stitcher --> ExportTT["TikTok Video Export
        (output_asset_ref: .mp4)"]:::live
        Stitcher --> ExportIG["Instagram Reels Export
        (output_asset_ref: .mp4)"]:::live
    end

    ExportYT --> Gate8
    ExportTT --> Gate8
    ExportIG --> Gate8

    Gate8{"Publishing Gate 8:
    Are all target platform
    exports COMPLETED?"}:::gate

    Gate8 -->|Failed (Missing Export)| Block[Halt Publishing - HTTP 422
    Gate 8 Incomplete]:::gate

    Gate8 -->|Passed (All Exports Ready)| Dispatcher[Publishing Routing Dispatcher]:::live

    subgraph Delivery_Adapters ["Distribution & Package Adapters"]
        Dispatcher -->|YouTube Track| YTOAuth["YouTube Data API v3 OAuth2
        (Real API Upload Job)"]:::live
        Dispatcher -->|TikTok Track| TTPackage["TikTok Manual Export Packager
        (manifest.json, captions.vtt,
        post_copy.txt, final_tiktok.mp4)"]:::package
        Dispatcher -->|Instagram Track| IGPackage["Instagram Reels Packager
        (manifest.json, captions.vtt,
        post_copy.txt, final_reels.mp4)"]:::package
    end

    YTOAuth --> LiveYT[Live YouTube Short
    yt.be/watch?v=...
    Status: PUBLISHED]:::live

    TTPackage --> HardenedDownloadTT["Hardened Download Endpoint
    /platform-exports/tiktok/download/...
    (Path Traversal Guard + RBAC)"]:::package

    IGPackage --> HardenedDownloadIG["Hardened Download Endpoint
    /platform-exports/instagram/download/...
    (Path Traversal Guard + RBAC)"]:::package

    HardenedDownloadTT -.-> DirectTTAPI["TikTok Direct API Upload
    (Roadmap / Enterprise App Review)"]:::roadmap
    HardenedDownloadIG -.-> DirectIGAPI["Instagram Graph API Upload
    (Roadmap / Meta App Review)"]:::roadmap
```
