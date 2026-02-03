#!/usr/bin/env python3
"""
PlantUML to Markdown Documentation Generator

This script converts .puml files to PNG images and generates corresponding
Markdown documentation files with embedded images.

Usage:
    python generate_docs.py
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


# Configuration
PUML_DIR = Path(__file__).parent / "puml"
OUTPUT_IMG_DIR = Path(__file__).parent / "images"
OUTPUT_MD_DIR = Path(__file__).parent / "md"

# Diagram metadata: descriptions for each diagram
DIAGRAM_DESCRIPTIONS = {
    "senzu-ai-backend-architecture": {
        "title": "Backend Architecture",
        "description": """
This diagram illustrates the high-level backend architecture of Senzu AI, showing the main components
and their interactions. The system follows a microservices architecture with clear separation of concerns.

### Key Components:
- **API Gateway**: Entry point for all client requests, handles routing and authentication
- **Inference Service**: Orchestrates the prediction workflow
- **Feature Service**: Handles feature engineering and storage
- **Model Service**: Manages ML model lifecycle and inference
- **Data Ingestion Service**: Fetches data from external sports data providers
- **Data Layer**: PostgreSQL for relational data, Redis for caching, S3 for data lake storage
""",
    },
    "senzu-ai-class-diagram": {
        "title": "Domain Model",
        "description": """
The domain model defines the core entities and their relationships in the Senzu AI system.
This class diagram shows the data structures used throughout the application.

### Core Entities:
- **User**: System users with authentication
- **Sport**: Supported sports (NBA, NFL, etc.)
- **Team**: Sports teams with external provider IDs
- **Match**: Sporting events with teams, scores, and status
- **OddsSnapshot**: Betting odds from various providers at specific timestamps
- **FeatureVector**: Computed features for ML inference
- **ModelRun**: Trained model versions with metadata
- **Prediction**: Probability predictions and expected value calculations
- **BacktestResult**: Historical model performance metrics
""",
    },
    "senzu-ai-sequence-diagram": {
        "title": "Prediction Request Flow",
        "description": """
This sequence diagram shows the high-level flow of a prediction request from a user through the system.
It demonstrates how different services collaborate to generate predictions.

### Flow Steps:
1. Client sends prediction request to API Gateway
2. Authentication is verified
3. Cache is checked for existing predictions
4. If cache miss, Inference Service orchestrates prediction
5. Feature Service builds feature vector from match data
6. Model Service loads model and runs inference
7. Prediction is stored and cached
8. Response is returned to client

### Performance Optimizations:
- Redis caching reduces redundant computations
- Feature vectors are reused across predictions
- Models are kept warm in memory
""",
    },
    "senzu-ai-deployment-diagram": {
        "title": "Deployment Architecture",
        "description": """
The deployment diagram shows how the Senzu AI system is deployed in a cloud environment
(AWS/GCP) with infrastructure components and their relationships.

### Infrastructure Components:
- **API / Web Layer**: API Gateway and Auth Service (containerized)
- **Backend Services**: Inference, Feature, Model, and Ingestion services (containerized)
- **Persistence & Cache**: PostgreSQL RDS, S3 Data Lake, Redis Cache
- **ML Pipeline**: Airflow/Prefect for orchestration, MLflow for model registry

### Scalability Considerations:
- Services are containerized for easy scaling
- Database uses RDS for managed operations
- S3 provides unlimited storage for historical data
- Redis cache improves read performance
""",
    },
    "senzu-ai-database-schema": {
        "title": "Database Schema (ER Diagram)",
        "description": """
The database schema defines all tables, columns, relationships, and indexes used in the PostgreSQL database.
This ER diagram provides a comprehensive view of data storage and relationships.

### Schema Organization:
- **User & Auth**: User authentication and refresh tokens
- **Sports Domain**: Sports, teams, and matches
- **Odds Data**: Time-series odds snapshots (partitioned by month)
- **Feature Store**: Computed feature vectors with versioning
- **Model Management**: Model metadata, evaluations, and backtests
- **Predictions**: Prediction results (partitioned by month)
- **Data Ingestion Tracking**: Job status and error logging

### Performance Optimizations:
- Strategic indexing on frequently queried columns
- Partitioning for large tables (odds_snapshots, predictions)
- JSONB columns for flexible metadata storage
""",
    },
    "senzu-ai-service-interfaces": {
        "title": "Service Interface Definitions",
        "description": """
This diagram defines the interfaces (contracts) for all services in the system. It shows
the methods each service exposes and the data transfer objects (DTOs) they use.

### Service Interfaces:
- **IAuthService**: User authentication and token management
- **IInferenceService**: Prediction orchestration and EV calculation
- **IFeatureService**: Feature engineering and validation
- **IModelService**: Model loading, inference, and evaluation
- **IDataIngestionService**: External data fetching and validation
- **Repository Interfaces**: Data access for matches, odds, predictions, features
- **ICacheService**: Caching operations with pattern invalidation

### Design Principles:
- Clear separation of concerns
- Dependency injection friendly
- Testable interfaces
- Comprehensive type definitions
""",
    },
    "senzu-ai-prediction-flow-detailed": {
        "title": "Detailed Prediction Request Flow",
        "description": """
This comprehensive sequence diagram details the complete prediction flow from authentication
through feature building, model inference, EV calculation, and caching.

### Detailed Steps:
1. **Authentication Phase**: Token verification
2. **Cache Check**: Redis lookup for existing predictions
3. **Feature Building**:
   - Fetch match and team data
   - Retrieve historical matches
   - Compute form, H2H, and odds features
   - Validate and store feature vector
4. **Model Inference**:
   - Load active model from cache or S3
   - Run inference on feature vector
   - Calculate confidence intervals
5. **EV Calculation**: Compute expected value from probabilities and odds
6. **Persistence**: Store predictions in database
7. **Caching**: Cache results in Redis
8. **Monitoring**: Log metrics and latency

### Performance Metrics:
- Feature building: ~200-500ms
- Model inference: ~50-100ms
- Total latency: ~300-700ms (cache miss)
- Cache hit: ~10-20ms
""",
    },
    "senzu-ai-model-deployment-flow": {
        "title": "Model Training & Deployment Flow",
        "description": """
This sequence diagram shows the end-to-end flow of training a new model and deploying it to production.

### Training Pipeline Steps:
1. **Data Preparation**: Export features and labels from feature store and data lake
2. **Data Splitting**: Time-based split (train/validation/test)
3. **Model Training**: Train with hyperparameters, early stopping, metric tracking
4. **Model Evaluation**: Calculate accuracy, log loss, Brier score, calibration
5. **Backtesting**: Simulate betting strategy to compute ROI and Sharpe ratio
6. **Model Registration**: Save artifact to S3, register in MLflow and database

### Deployment Steps:
1. **Model Review**: ML engineer reviews metrics and performance
2. **Model Activation**: Atomically switch active model in database
3. **Cache Invalidation**: Clear cached models and predictions
4. **Model Warming**: Pre-load new model into memory/cache
5. **Monitoring Setup**: Configure drift detection and performance tracking

### Safety Measures:
- Transaction-based activation prevents inconsistencies
- Rollback procedure documented
- Continuous monitoring for performance degradation
""",
    },
    "senzu-ai-ingestion-sequence": {
        "title": "Data Ingestion Sequence (Scheduled Job)",
        "description": """
This sequence diagram illustrates the complete data ingestion process, from fetching data
from external providers to storing it in the database and triggering downstream processes.

### Ingestion Steps:
1. **Job Initialization**: Create job record, initialize API client
2. **Fetch Match Schedule**: GET request to provider API with retry logic
3. **Fetch Odds Data**: Retrieve current odds for all markets
4. **Data Validation**: Schema validation, duplicate detection
5. **Data Transformation**: Map external IDs, convert formats, standardize names
6. **Team Management**: Create new teams if not found
7. **Upsert Matches**: Insert new matches or update existing ones
8. **Bulk Insert Odds**: Batch insert odds snapshots for performance
9. **Cache Invalidation**: Clear prediction caches for updated matches
10. **Trigger Feature Computation**: Queue async jobs for new/updated matches
11. **Job Completion**: Update job status and log metrics

### Error Handling:
- Exponential backoff for retryable errors (500, 502, 503, 429)
- Skip invalid records and continue with valid ones
- Transaction rollback on fatal errors
- Alert on job failures
""",
    },
    "senzu-ai-feature-pipeline": {
        "title": "Feature Engineering Pipeline",
        "description": """
This activity diagram shows the feature engineering pipeline, which transforms raw match
and odds data into feature vectors suitable for ML inference.

### Feature Categories:
1. **Team Form Features**: Win rates, points per game, momentum, home/away splits
2. **Head-to-Head Features**: Historical matchup statistics and trends
3. **Market Odds Features**: Implied probabilities, odds movement, market consensus
4. **Contextual Features**: Rest days, season progress, time of day, home advantage
5. **Statistical Features**: Expected goals (xG), possession, shot efficiency

### Pipeline Phases:
1. **Data Retrieval**: Fetch match, team, odds, and historical data
2. **Feature Computation**: Parallel computation of feature categories
3. **Aggregation**: Combine all features into single vector
4. **Transformation**: Normalize, scale, encode, handle missing values
5. **Validation**: Check for NaN/Inf, validate ranges and schema
6. **Storage**: Save to database and cache in Redis
7. **Export**: Queue for S3 data lake export (for training)

### Performance:
- Parallel feature computation reduces latency
- Caching prevents redundant calculations
- Typical computation time: 200-500ms
""",
    },
    "senzu-ai-data-ingestion-workflow": {
        "title": "Data Ingestion Workflow",
        "description": """
This activity diagram provides an overview of the data ingestion workflow, showing decision
points, error handling, and post-processing actions.

### Workflow Phases:
1. **Data Fetching**: Call external provider APIs with authentication and rate limiting
2. **Data Validation**: Schema validation, duplicate detection, error filtering
3. **Data Transformation**: Map to internal schema, enrich with metadata
4. **Data Persistence**: Transactional upsert of matches and bulk insert of odds
5. **Post-Processing**: Feature computation triggering, cache invalidation, metrics tracking

### Error Handling Strategy:
- **Retryable Errors**: Network timeouts, rate limits (429), server errors (500/502/503)
- **Non-Retryable Errors**: Authentication failures (401), bad requests (400)
- **Partial Failures**: Continue with valid records, log invalid records separately

### Trigger Sources:
- Scheduled cron jobs (every 5 minutes)
- Manual API triggers
- Webhooks from providers
- Event-driven (match status changes)

### Performance Considerations:
- Bulk operations reduce database round trips
- Batch size typically 1000 records per insert
- Transaction management ensures data consistency
""",
    },
}


def extract_title_from_puml(puml_content: str) -> str:
    """Extract the title from PlantUML content."""
    match = re.search(r'title\s+(.+)', puml_content)
    if match:
        return match.group(1).strip()
    return "Untitled Diagram"


def generate_png_from_puml(puml_file: Path, output_dir: Path) -> Path:
    """
    Generate PNG image from PlantUML file using plantuml command.

    Args:
        puml_file: Path to .puml file
        output_dir: Directory to save PNG file

    Returns:
        Path to generated PNG file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run plantuml command
    cmd = ["plantuml", "-tpng", "-o", str(output_dir.absolute()), str(puml_file.absolute())]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"PlantUML conversion failed: {result.stderr}")

    # PlantUML creates PNG with same name as .puml file
    png_file = output_dir / f"{puml_file.stem}.png"

    if not png_file.exists():
        raise FileNotFoundError(f"Expected PNG file not created: {png_file}")

    return png_file


def generate_markdown_doc(
    diagram_name: str,
    png_path: Path,
    title: str,
    description: str,
    output_dir: Path
) -> Path:
    """
    Generate Markdown documentation file with embedded image.

    Args:
        diagram_name: Name of the diagram (without extension)
        png_path: Path to PNG image file
        title: Diagram title
        description: Diagram description
        output_dir: Directory to save Markdown file

    Returns:
        Path to generated Markdown file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create relative path from md directory to images directory
    rel_img_path = os.path.relpath(png_path, output_dir)

    markdown_content = f"""# {title}

{description.strip()}

## Diagram

![{title}]({rel_img_path})

## Related Diagrams

"""

    # Add related diagrams based on diagram type
    if "architecture" in diagram_name.lower():
        markdown_content += "- [Domain Model](./senzu-ai-class-diagram.md)\n"
        markdown_content += "- [Deployment Architecture](./senzu-ai-deployment-diagram.md)\n"
        markdown_content += "- [Database Schema](./senzu-ai-database-schema.md)\n"
    elif "sequence" in diagram_name.lower() or "flow" in diagram_name.lower():
        markdown_content += "- [Backend Architecture](./senzu-ai-backend-architecture.md)\n"
        markdown_content += "- [Service Interfaces](./senzu-ai-service-interfaces.md)\n"
    elif "class" in diagram_name.lower():
        markdown_content += "- [Database Schema](./senzu-ai-database-schema.md)\n"
        markdown_content += "- [Service Interfaces](./senzu-ai-service-interfaces.md)\n"

    markdown_content += """
## Source

This documentation was automatically generated from PlantUML diagrams.

- Source file: [`../puml/{diagram_name}.puml`](../puml/{diagram_name}.puml)
- Image: [`../images/{diagram_name}.png`](../images/{diagram_name}.png)

## Navigation

Return to [Documentation Index](./README.md)
""".format(diagram_name=diagram_name)

    md_file = output_dir / f"{diagram_name}.md"
    md_file.write_text(markdown_content)

    return md_file


def generate_index(md_files: List[Tuple[str, str]], output_dir: Path) -> Path:
    """
    Generate an index/README file listing all diagrams.

    Args:
        md_files: List of (diagram_name, title) tuples
        output_dir: Directory to save index file

    Returns:
        Path to generated index file
    """
    markdown_content = """# Senzu AI Architecture Documentation

This directory contains automatically generated documentation from PlantUML diagrams.
Each document includes a rendered diagram image and detailed descriptions of the components and flows.

## Architecture Diagrams

### System Overview
- [Backend Architecture](./senzu-ai-backend-architecture.md) - High-level system architecture and component interactions
- [Deployment Architecture](./senzu-ai-deployment-diagram.md) - Cloud deployment and infrastructure components

### Data Models
- [Domain Model](./senzu-ai-class-diagram.md) - Core entities and their relationships
- [Database Schema](./senzu-ai-database-schema.md) - Complete database schema with tables, indexes, and partitioning
- [Service Interfaces](./senzu-ai-service-interfaces.md) - Service contracts and DTOs

### Process Flows
- [Prediction Request Flow](./senzu-ai-sequence-diagram.md) - High-level prediction flow
- [Detailed Prediction Flow](./senzu-ai-prediction-flow-detailed.md) - Comprehensive prediction workflow with all steps
- [Data Ingestion Sequence](./senzu-ai-ingestion-sequence.md) - Data ingestion from external providers
- [Data Ingestion Workflow](./senzu-ai-data-ingestion-workflow.md) - Ingestion workflow with decision points

### ML & Features
- [Feature Engineering Pipeline](./senzu-ai-feature-pipeline.md) - Feature computation and transformation flow
- [Model Training & Deployment](./senzu-ai-model-deployment-flow.md) - End-to-end ML model lifecycle

## About

These diagrams provide a comprehensive view of the Senzu AI sports prediction system, covering:
- System architecture and components
- Data models and database design
- API workflows and service interactions
- ML pipeline and feature engineering
- Data ingestion and processing

### Regenerating Documentation

To regenerate this documentation from PlantUML source files:

```bash
cd docs/plantuml
python generate_docs.py
```

### Project Structure

```
docs/plantuml/
├── puml/              # PlantUML source files (.puml)
├── images/            # Generated PNG images
├── md/                # Generated Markdown documentation
├── generate_docs.py   # Documentation generator script
└── README.md          # This file
```

## Navigation

- [Project README](../../README.md)
- [Claude AI Instructions](../CLAUDE.md)
"""

    index_file = output_dir / "README.md"
    index_file.write_text(markdown_content)

    return index_file


def main():
    """Main execution function."""
    print("Senzu AI Documentation Generator")
    print("=" * 50)

    # Find all .puml files
    puml_files = sorted(PUML_DIR.glob("*.puml"))

    if not puml_files:
        print(f"No .puml files found in {PUML_DIR}")
        return

    print(f"Found {len(puml_files)} PlantUML files")
    print()

    generated_docs = []

    for puml_file in puml_files:
        diagram_name = puml_file.stem
        print(f"Processing: {diagram_name}")

        # Read PlantUML content to extract title
        puml_content = puml_file.read_text()
        extracted_title = extract_title_from_puml(puml_content)

        # Get metadata
        metadata = DIAGRAM_DESCRIPTIONS.get(diagram_name, {
            "title": extracted_title,
            "description": f"Documentation for {extracted_title}."
        })

        try:
            # Generate PNG
            print(f"  → Generating PNG...")
            png_path = generate_png_from_puml(puml_file, OUTPUT_IMG_DIR)
            print(f"  ✓ Created: {png_path.name}")

            # Generate Markdown
            print(f"  → Generating Markdown...")
            md_path = generate_markdown_doc(
                diagram_name,
                png_path,
                metadata["title"],
                metadata["description"],
                OUTPUT_MD_DIR
            )
            print(f"  ✓ Created: {md_path.name}")

            generated_docs.append((diagram_name, metadata["title"]))
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            print()
            continue

    # Generate index
    print("Generating index...")
    index_path = generate_index(generated_docs, OUTPUT_MD_DIR)
    print(f"✓ Created: {index_path.name}")
    print()

    print("=" * 50)
    print(f"Documentation generation complete!")
    print(f"  - {len(generated_docs)} diagrams processed")
    print(f"  - Images: {OUTPUT_IMG_DIR}")
    print(f"  - Markdown: {OUTPUT_MD_DIR}")
    print(f"  - Index: {index_path}")


if __name__ == "__main__":
    main()
