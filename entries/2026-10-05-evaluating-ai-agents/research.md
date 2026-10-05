# Research for Evaluating AI agents: decompose, trace, judge, monitor

Counts are OpenAlex `cited_by_count` as of 2026-10-05; they under-count arXiv papers. Treat them as a relative ranking, never a true total. Rows with count 0 and "no count" in why are essays or specs OpenAlex does not index. Tier is from source-checker: PRIMARY read the source, SECONDARY a reputable citing source, UNVERIFIED not reached, CONTRADICTED the source says otherwise, SUPERSEDED replaced by a newer document.

## How the references were found

- 64 OpenAlex queries through `cite_rank.py` on 2026-10-05: broad noun phrases first (for example "holistic evaluation of language models", "hidden technical debt machine learning systems" with `--since 2005`), then one exact-title variant per paper.
- Picks are the highest-cited records whose abstract is on topic, with at least one from the last three years per key point. Where OpenAlex holds both the arXiv record and the venue record of the same paper, the venue record (higher count) is used.
- Dropped for title mismatch (the OpenAlex arXiv record carried another paper's title or abstract): the Chatbot Arena record under DOI 10.4230/lipics.cp.2024.25, the WebArena id 2307.13854 labelled "Autonomous Tester Agent Benchmark", and the SWE-bench id 2310.06770 labelled "GardenBench". ReAct, Gorilla, tau-bench and Reliance on Metrics (Thomas and Uminsky) did not surface in OpenAlex under their titles and are left out rather than cited with a remembered count.
- Three rows are not papers: the Anthropic agents essay, the OpenTelemetry GenAI conventions and Hamel Husain's evals essay. They carry `cited_by` 0 and "no count" in why.
- Tier breakdown across 41 rows: PRIMARY 40, SECONDARY 1.
- The six "where they disagree" lines name two positions and the evidence that would settle each; none is resolved here.

## Course bundle method

One course per platform, the source course excluded. Each pick was confirmed on its own page on 2026-10-05; Udemy returns 403 to fetch tools so its page was read in the browser pane (title, 7h 29m, 9 sections). Nothing was taken from search snippets alone.
