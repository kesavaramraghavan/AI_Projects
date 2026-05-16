# AI_Projects
**Creating AI Projects**

**LLM Mechanics**
I created **LLM Mechanics** as a hands-on space to understand how LLM systems behave in real apps - especially around context windows, token efficiency, and production API reliability so you can design faster, cheaper, and more dependable AI workflows.

Projects included:
- [Context_Limit](https://github.com/kesavaramraghavan/AI_Projects/tree/main/LLM_Mechanics/Projects/Context_Limit) - explores context window limits and practical handling patterns.
- [Minimal_Token_Count](https://github.com/kesavaramraghavan/AI_Projects/tree/main/LLM_Mechanics/Projects/Minimal_Token_Count) - techniques to reduce tokens while keeping output quality.
- [Prod-Api-Services](https://github.com/kesavaramraghavan/AI_Projects/tree/main/LLM_Mechanics/Projects/Prod-Api-Services) - a production-style FastAPI gateway for secure, observable LLM inference.
- [Prod-real-api-metrics](https://github.com/kesavaramraghavan/AI_Projects/tree/main/LLM_Mechanics/Projects/Prod-real-api-metrics) - monitoring/metrics patterns to track latency, errors, and cost signals.
- [Transcript_CE](https://github.com/kesavaramraghavan/AI_Projects/tree/main/LLM_Mechanics/Projects/Transcript_CE) - transcript-based experiments for processing and evaluating conversation data.

-----------------------------------------------------------------------------------------------

**Generation Controls (GC)** 
I created **Generation Controls** designed as a hands-on space to understand how to control and optimize LLM outputs in real applications covering temperature, top-p, presence/frequency penalties, stopping criteria, and max token limits so you can generate reliable, safe, and cost-efficient results in production AI systems.

Projects included under examples:
- minimal_demo - explores basic generation with all controls exposed.
- business_json_extraction - demonstrates deterministic extraction of structured outputs from text.
- creative_generation - experiments with high-temperature outputs for ideation and creative tasks.
[Generation_controls](https://github.com/kesavaramraghavan/AI_Projects/tree/main/Generation_Controls)

-----------------------------------------------------------------------------------------------

**Log Agent** - A hands-on reference implementation for log intelligence and incident analysis in containerized environments.

Projects included:
[log_agent](https://github.com/kesavaramraghavan/AI_Projects/tree/main/log_agent) - Kafka-to-Elasticsearch log pipeline with a heuristic RCA API and web UI.

-----------------------------------------------------------------------------------------------

**Sentiment Intelligence API**

A FastAPI-based ML system that classifies text into positive, negative, and neutral sentiments using TF-IDF features with a calibrated linear model, supporting real-time and batch inference with production-style logging, model persistence, and retraining capability.

[Sentiment API](https://github.com/kesavaramraghavan/AI_Projects/tree/main/Sentiment_API) - Includes structured pipelines for training, evaluation, and inference with safe artifact versioning, API key–protected retraining, and optimized batch prediction for low-latency deployment.

-----------------------------------------------------------------------------------------------

**Support Ticket Classifier API**

A FastAPI-based ML system that automatically categorizes customer support tickets into 6 departments (billing, technical, account, shipping, returns, general) and assigns priority levels (P1–P4) using TF-IDF features with dual XGBoost classifiers, supporting real-time and batch inference with intelligent queue routing and auto-escalation for critical issues.
[Ticket Classifier API](https://github.com/kesavaramraghavan/AI_Projects/tree/main/Support_ticket_classifier) - Includes a self-training pipeline that bootstraps from built-in seed data on first launch, dual-model evaluation with accuracy and F1 scoring, automatic artifact persistence, and smart queue assignment that prefixes ESCALATION- for P1-critical tickets.

-----------------------------------------------------------------------------------------------

