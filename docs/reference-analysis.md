# DataSense reference analysis

Inspected on 22 October 2026. This is source inspection, not an observation of
the original project's runtime. REA's source-repository route was used; no
binary decompilation or REA engine was needed.

**Target:** [raywanb/DataSenseQA](https://github.com/raywanb/DataSenseQA), commit
`d59eebb918f49336909366a9d9c3a47f698b29a8`.

## Observations and evidence

| Source | Observation | Consequence for this project |
| --- | --- | --- |
| [readme.md](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/readme.md) | The repository separates datasets, question sets, model results, and analysis scripts. | Keep fixtures, runner, and reports separate and reproducible. |
| [questions/information_retrieval_2_crm.json](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/questions/information_retrieval_2_crm.json) | Each question carries `ground_truth`, `derivation`, `difficulty`, `subtype`, `type`, and table paths. CRM questions include multi-table joins and aggregation. | Stratify original SQL questions by difficulty and category; store explicit expected rows. |
| [langchain_agent.py](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/langchain_agent.py), `DataFrameAgentProcessor.process_questions` | Loads CSVs into pandas and creates a LangChain dataframe agent with `allow_dangerous_code=True`. | Do not reproduce arbitrary Python execution on a public demo. Use a fixed read-only SQL database and bounded queries. |
| Same file, `strict_evaluator` | Uses GPT-4o to judge generated answers against ground truth and parses a binary score. | Use deterministic row comparison for this narrower SQL task; preserve columns, duplicates, types, and numeric tolerance. No judge-model cost or judge variability. |
| [result_analysis.py](https://github.com/raywanb/DataSenseQA/blob/d59eebb918f49336909366a9d9c3a47f698b29a8/result_analysis.py) | Groups results by model/dataset/difficulty to compute score means and counts. | Report sample counts and per-difficulty results rather than one unqualified percentage. |

## Design choices, rather than recovered behavior

This repository's FastAPI UI, seeded SQLite database, read-only URI mode,
execution progress deadline, SQL fixtures, and deterministic evaluator are
original additions to Deepak Gangwar's existing SQL_Assistant. They are not
features asserted to exist in DataSense.

No DataSense source code, datasets, questions, graphics, or benchmark results
were copied. Its benchmark organization is credited as inspiration. The
original authors are Felix Krumme, Ray Wan, Dimple Amitha Garuadapuri, and Manan
Dhanuka. Their hackathon award is theirs, not this project's.

## Boundaries and unknowns

- Inspected the listed source files and inventory; did not audit every upstream
  notebook, data source, or generated result.
- Did not run upstream code or independently reproduce its published scores.
- This app's 18 synthetic questions are separate from its six guided UI
  examples. Gold answers are public and this is not an independently sealed
  benchmark. Do not claim broad unseen-schema generalization.
- Reference-SQL correctness does not measure natural-language generation. Live
  model evaluation is a separate command and requires a configured provider.
