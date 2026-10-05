# An agent is only as good as the evaluation loop around it: trace every step, grade each component, judge the path, then keep measuring in production

Source: DeepLearning.AI - Evaluating AI Agents (short course with Arize AI) - https://www.deeplearning.ai/courses/evaluating-ai-agents. Captured 2026-10-05.

Instructors: John Gilhuly (Head of Developer Relations, Arize AI) and Aman Khan (Director of Product, Arize AI). Level: Beginner. Duration: 2h36m, 15 video lessons plus 6 code examples, a graded quiz and an appendix. Prerequisite: basic Python; prompting experience helpful but not required.

## What the source teaches

The three outcomes the course page promises, verbatim:

- "Learn how to add observability to your agent to gain insights into its steps and know how to debug it."
- "Learn how to set up evaluations for the agent components by preparing testing examples, choosing the appropriate evaluator (code-based or LLM-as-a-Judge), and identifying the right metrics."
- "Learn how to structure your evaluation into experiments to iterate on and improve the output quality and the path taken by your agent."

Course description: students build an agent, add observability to visualise its steps, and evaluate performance component by component using code-based and LLM evaluators.

Lesson map, titles verbatim from the course page. The one-line takeaways are not on the page and come from model knowledge of the course, so each carries (AI-supplemented).

| # | Lesson (type, length) | Takeaway |
|---|-----------------------|----------|
| 1 | Introduction (video, 3m) | Agents fail quietly; evaluation is the feedback loop that makes iteration possible (AI-supplemented) |
| 2 | Evaluation in the time of LLMs (video, 7m) | LLM outputs are non-deterministic, so pass/fail unit tests give way to graded, sampled judgement (AI-supplemented) |
| 3 | Decomposing agents (video, 6m) | An agent is a router plus skills plus memory or state; evaluate each part separately before the whole (AI-supplemented) |
| 4 | Lab 1: Building your agent (video + code, 16m) | Build a data-analysis agent: a function-calling router that dispatches to tools such as database lookup, analysis and chart generation (AI-supplemented) |
| 5 | Tracing agents (video, 4m) | Instrument every LLM call and tool call as spans in a trace so you can see what the agent did (AI-supplemented) |
| 6 | Lab 2: Tracing your agent (video + code, 16m) | Send traces to Arize Phoenix and inspect the span tree, inputs, outputs and latency (AI-supplemented) |
| 7 | Adding router and skill evaluations (video, 12m) | Router eval asks "did it pick the right tool with the right arguments"; skill eval asks "is the tool output correct and relevant" (AI-supplemented) |
| 8 | Lab 3: Adding router and skill evaluations (video + code, 17m) | Implement function-call correctness and skill-level evaluators in code (AI-supplemented) |
| 9 | Adding trajectory evaluations (video, 5m) | Judge the path, not only the answer: convergence compares steps taken with the minimum needed (AI-supplemented) |
| 10 | Lab 4: Adding trajectory evaluations (video + code, 9m) | Compute convergence over a set of runs (AI-supplemented) |
| 11 | Adding structure to your evaluations (video, 7m) | Curate a test dataset, define evaluators, run experiments and compare versions (AI-supplemented) |
| 12 | Lab 5: Adding structure to your evaluations (video + code, 15m) | Run structured experiments in Phoenix and compare prompt or model changes (AI-supplemented) |
| 13 | Improving your LLM-as-a-judge (video, 4m) | Iterate the judge prompt: a clear rubric, few-shot examples, label-only outputs, and a check against human labels (AI-supplemented) |
| 14 | Monitoring agents (video, 6m) | In production, sample live traffic and run the same evaluators online (AI-supplemented) |
| 15 | Conclusion (video, 1m) | Trace, evaluate, experiment, monitor, repeat (AI-supplemented) |
| 16 | Quiz (graded, 10m) | |
| 17 | Appendix - Resources, Tips and Help (code, 10m) | |

## Key points

### kp1 - LLM evaluation is not classic software testing: grade sampled outputs with an evaluator and a rubric instead of asserting exact results

- Why it matters: a test suite that expects one exact string will fail on a correct paraphrase and pass on a confident wrong answer; the evaluator has to grade meaning.
- Source says: lesson 2 is titled "Evaluation in the time of LLMs"; the page says you prepare testing examples and choose "the appropriate evaluator (code-based or LLM-as-a-Judge)" and identify the right metrics.
- Open question: how many sampled runs per test case are needed before a grade is stable, and who decides the rubric.

### kp2 - Decompose the agent into router and skills (and memory) and evaluate each component where it fails, before judging the whole

- Why it matters: an end-to-end score tells you the agent is wrong, not whether the router chose the wrong tool or the tool did its job badly.
- Source says: lesson 3 is "Decomposing agents"; the description says performance is evaluated "component-by-component"; lessons 7 and 8 add "router and skill evaluations".
- Open question: where memory and state fit in the evaluation when the course's lab agent is mostly stateless (AI-supplemented).

### kp3 - Trace every step: instrument LLM calls, tool calls and retrievals as spans so you can see and debug what the agent did

- Why it matters: without a trace, a wrong answer has no history; with one, each span carries its inputs, outputs and latency.
- Source says: outcome 1 promises observability "to gain insights into its steps and know how to debug it"; lessons 5 and 6 are "Tracing agents" and "Lab 2: Tracing your agent".
- Open question: whether the labs use OpenTelemetry-compatible instrumentation (OpenInference via Arize Phoenix) or a Phoenix-only format (AI-supplemented).

### kp4 - Use code-based checks, LLM-as-a-judge and human labels as the three evaluator families, pick per component, and iterate the judge until it agrees with humans

- Why it matters: a judge prompt is itself a model output; if nobody checks it against human labels, you are grading with an ungraded grader.
- Source says: the page names "code-based or LLM-as-a-Judge" evaluators; lesson 13 is "Improving your LLM-as-a-judge".
- Open question: what agreement level with human labels the course treats as good enough, and on how many examples (AI-supplemented).

### kp5 - Evaluate trajectories, not only final answers: convergence compares steps taken with the minimum needed and exposes loops and wasted tool calls

- Why it matters: two agents can reach the same answer, one in three steps and one in thirty; cost, latency and risk live in the path.
- Source says: outcome 3 promises to improve "the path taken by your agent"; lessons 9 and 10 are "Adding trajectory evaluations".
- Open question: whether convergence is computed against a reference trajectory or against the best observed run (AI-supplemented).

### kp6 - Make evaluation structured and continuous: a curated dataset, experiments that compare versions, and online monitoring once the agent ships

- Why it matters: a one-off eval proves a version; a loop proves the process still holds after the next prompt change, model swap or traffic shift.
- Source says: outcome 3 says "structure your evaluation into experiments to iterate"; lessons 11 and 12 are "Adding structure to your evaluations"; lesson 14 is "Monitoring agents".
- Open question: how the course bridges offline experiments to online monitoring (sampling rate, which evaluators run live) (AI-supplemented).

## Glossary

| Term | Meaning in this source |
|------|------------------------|
| Agent | An LLM application that decides which tools or skills to call and in what order (AI-supplemented) |
| Router | The component that reads the user request and picks the skill or tool to run (AI-supplemented) |
| Skill | A tool or sub-task the router can dispatch to, such as a database lookup or chart generation (AI-supplemented) |
| Observability | Instrumentation that records each step of the agent so it can be inspected and debugged |
| Trace and span | A trace is one agent run; a span is one step inside it with inputs, outputs and timing (AI-supplemented) |
| Code-based evaluator | A deterministic check written in code, such as exact match or a schema test |
| LLM-as-a-Judge | An LLM prompted with a rubric to grade another model's output |
| Router evaluation | Did the agent call the right skill with the right arguments (AI-supplemented) |
| Skill evaluation | Was the skill's output correct and relevant (AI-supplemented) |
| Trajectory evaluation | A grade on the sequence of steps the agent took, not only the final answer |
| Convergence | Steps the agent took compared with the fewest steps needed (AI-supplemented) |
| Experiment | A run of a dataset through a version of the agent with evaluators attached, for comparison across versions |
| Monitoring | Running evaluators on sampled live traffic after deployment (AI-supplemented) |

## Open questions

- How large a test dataset the labs use and how it was curated; answered by taking Lab 5.
- Whether the course quantifies judge agreement with humans; answered by lesson 13 and the appendix.
- Whether the Phoenix traces follow the OpenTelemetry GenAI conventions; answered by reading the OpenInference spec and the lab notebook imports.
- Whether convergence penalises a correct but long path or only loops; answered by Lab 4.
