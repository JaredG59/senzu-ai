# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Senzu AI is an AI-powered sports prediction backend system that provides probability predictions and expected value (EV) calculations for sports betting markets. The system ingests data from sports data providers, runs ML inference, and serves predictions through a REST/GraphQL API.

## Architecture

The system follows a microservices architecture with the following core components:

### Service Layer
- **API Gateway / Web API**: Entry point for all HTTP requests (REST/GraphQL), handles routing and response formatting
- **Auth Service**: User authentication and token verification
- **Inference Service**: Orchestrates the prediction workflow - builds feature vectors, loads models, runs inference, calculates EV, and stores predictions
- **Feature Service**: Responsible for feature engineering - builds feature vectors from raw data and manages feature storage/retrieval
- **Model Service**: Manages ML model lifecycle - loads model artifacts, handles model versioning, and performs inference
- **Data Ingestion Service**: Pulls data from external sports data provider APIs and upserts match/odds data into the system

### Data Layer
- **Prediction Repository**: Stores prediction results (probabilities, EV)
- **Match & Odds Repository**: Stores match metadata and betting odds data
- **Feature Repository**: Stores computed features for matches

### Infrastructure
- **PostgreSQL**: Primary relational data store for all repositories
- **S3 / Data Lake**: Historical feature storage for model retraining
- **Redis Cache**: Caching layer for predictions and in-memory model storage

### External Systems
- **Sports Data Provider APIs**: Source of match and odds data (JSON APIs)
- **AI Training Pipeline**: External system that trains models and deploys artifacts to the Model Service

## Data Flow

1. **Ingestion**: Data Ingestion Service fetches match/odds data from provider APIs and stores in Match & Odds Repository
2. **Prediction Request**: User requests prediction via API Gateway
3. **Feature Building**: Inference Service calls Feature Service to build feature vector from match data
4. **Inference**: Inference Service loads model from Model Service and runs inference to get probabilities
5. **Storage**: Predictions stored in Prediction Repository and cached in Redis
6. **Response**: API Gateway returns predicted probabilities + EV to user

## Development Status

This repository is in early planning stages. The architecture diagram (`senzu-ai_class_diagram.puml`) defines the intended system design.
