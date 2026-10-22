# SQL Analytics Lab: upstream project study

Evaluation of LLM agents on tabular data.

**Deepak Gangwar’s documentation for a local study copy of [DataSense / DataSenseQA](https://github.com/raywanb/DataSenseQA).** The portfolio display name has changed; the upstream implementation and authorship have not. Original authors: Felix Krumme, Ray Wan, Dimple Amitha Garuadapuri and Manan Dhanuka.

## At a glance

| Item | Status |
|---|---|
| Purpose | Architecture study and preparation for an attributed extension |
| Current work in this copy | Portfolio naming and recruiter-oriented documentation, prepared with AI assistance; no upstream application-code changes |
| Application code changes | None |
| Runtime verification | Not performed for this clone |
| Hosted demo | No deployment of this clone; previous similarly named demos are separate implementations |
| Upstream snapshot | `d59eebb918f49336909366a9d9c3a47f698b29a8` |

## Problem and approach

An LLM answer about a table can look plausible while failing retrieval, data curation or multi-step statistical reasoning.

```text
CSV datasets + question sets → configured LangChain agent → evaluator → saved per-model results → analysis and charts
```

**Technology:** Python, LangChain, CSV/JSON data, Jupyter notebooks and external LLM APIs.

## Explore the repository

| Path | What to inspect |
|---|---|
| [langchain_agent.py](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/langchain_agent.py) | Agent and evaluator implementation |
| [datasets](https://github.com/raywanb/DataSenseQA/tree/d59eebb918f49336909366a9d9c3a47f698b29a8/datasets) | Tabular datasets |
| [questions](https://github.com/raywanb/DataSenseQA/tree/d59eebb918f49336909366a9d9c3a47f698b29a8/questions) | Question sets |
| [results_folder](https://github.com/raywanb/DataSenseQA/tree/d59eebb918f49336909366a9d9c3a47f698b29a8/results_folder) | Upstream saved results |
| [result_analysis.py](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/result_analysis.py) | Aggregate result analysis |
| [langchain_run_script.ipynb](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/langchain_run_script.ipynb) | Benchmark execution notebook |
| [visualize.ipynb](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/visualize.ipynb) | Result visualizations |

## Setup and demonstration status

Review the preserved upstream README for provider configuration and model selection. Supply only the keys for the providers you intend to use through a local .env file; never commit credentials. The upstream instructions refer to a root requirements.txt, but that file is absent in this snapshot. A pinned environment must be prepared before claiming reproducible execution. No installation or provider calls were performed here.

## What I can discuss with a recruiter

**Relevant areas:** Python, data processing, LLM evaluation, statistical analysis, failure analysis and reproducibility.

Explain how answers are graded, how evaluator bias can affect scores, and how retrieval differs from multi-table reasoning. Separate upstream saved results from any future reproduction.

An accurate introduction is: “I am studying DataSense / DataSenseQA under the working portfolio name SQL Analytics Lab. I have organized its documentation; the implementation is upstream. I will identify and demonstrate my own engineering changes separately as they are completed.”

## Scope and evidence

Despite the portfolio title, this clone is a tabular-agent benchmark, not the separately built SQL web application. It does not inherit that application’s read-only SQL safeguards or deployed interface. Saved results belong to the upstream study; no new benchmark run has been performed here.

Renaming and README editing do not establish implementation experience, benchmark results or a working deployment. Upstream awards belong to the original team. This upstream copy should be described as a study copy until substantive changes are implemented and verified. The separate application in this repository has its own implementation and verification record in the root README.

## Attribution and reuse

Original source: [DataSense / DataSenseQA](https://github.com/raywanb/DataSenseQA). Original authors: Felix Krumme, Ray Wan, Dimple Amitha Garuadapuri and Manan Dhanuka. Upstream authorship and applicable notices are recorded here; the upstream source is not included in this repository.

No clear reuse licence was found in the inspected files. This is a local reference copy; public redistribution needs appropriate permission.

[Original upstream README](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/readme.md).

## Relationship to this repository

This document describes the original upstream reference, not the application deployed from this repository. Only study documentation is published here; the upstream source is not included in this repository. Use the [repository README](../README.md) for the current application, live demo, tests and contribution details.
