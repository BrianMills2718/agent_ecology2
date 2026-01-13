#!/usr/bin/env python3
"""
Summarize specs using Gemini API in parallel chunks
"""

import sys
import asyncio
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "llm_provider_standalone"))
from llm_provider import LLMProvider

SPECS_FILE = REPO_ROOT / "agent_ecology_v2_specs.txt"
OUTPUT_FILE = REPO_ROOT / "specs_summary.md"

# Define chunks by line ranges and expected content
CHUNKS = [
    (1, 400, "Sections 1-2: Purpose, Scope, Design Philosophy"),
    (400, 750, "Section 3: Core Ontology and Primitives"),
    (750, 1300, "Sections 4-5: Resource Physics and Cost Model"),
    (1300, 1900, "Sections 6-7: Artifacts and Actions"),
    (1900, 2500, "Sections 8-10: Standing, Contracts, Time"),
    (2500, 3200, "Sections 11-12: LLM Integration, Cognition vs Execution"),
    (3200, 4000, "Sections 13-15: Coordination, Firms, Scheduling"),
    (4000, 4800, "Sections 16-18: Communication, Topology, Money"),
    (4800, 5600, "Sections 19-21: External Feedback, Observability"),
    (5600, 6500, "Sections 22-24: Bootstrapping, Genesis, Initial Agents"),
    (6500, 7500, "Sections 25-27: Demo Harness, Visual Artifacts"),
    (7500, 8500, "Sections 28-29: Implementation Slices"),
    (8500, 9500, "Section 30: Open Questions"),
    (9500, 10500, "Section 30 continued + Section 31: Risks"),
    (10500, 11500, "Section 32: Core Commitments"),
    (11500, 12530, "Sections 33-35: Non-Goals, Implications, Handoff"),
]

PROMPT_TEMPLATE = """You are summarizing a technical specification document.

Create a detailed, faithful summary (400-600 words) of this section.
- Preserve the actual reasoning and nuance
- Keep section/subsection structure where present
- Do NOT editorialize or add your own interpretation
- Do NOT reference "the document" - just state the content directly
- Use bullet points for lists of concepts

SECTION: {section_name}

CONTENT:
{content}

---
Provide the summary now:"""


async def summarize_chunk(provider: LLMProvider, chunk_id: int, start: int, end: int, section_name: str, lines: list) -> tuple:
    """Summarize a single chunk"""
    content = "\n".join(lines[start:end])
    prompt = PROMPT_TEMPLATE.format(section_name=section_name, content=content)

    try:
        result = await provider.generate_async(prompt)
        return (chunk_id, section_name, result)
    except Exception as e:
        return (chunk_id, section_name, f"ERROR: {e}")


async def main():
    # Read specs
    print(f"Reading {SPECS_FILE}...")
    with open(SPECS_FILE) as f:
        lines = f.readlines()
    print(f"Loaded {len(lines)} lines")

    # Initialize provider
    provider = LLMProvider(
        model="gemini/gemini-2.5-flash",
        log_dir="llm_logs",
        timeout=120
    )

    # Process chunks in parallel (but limit concurrency for rate limits)
    print(f"Processing {len(CHUNKS)} chunks...")

    tasks = []
    for i, (start, end, section_name) in enumerate(CHUNKS):
        task = summarize_chunk(provider, i, start, end, section_name, lines)
        tasks.append(task)

    # Run with some concurrency limit
    results = []
    batch_size = 4  # Process 4 at a time to avoid rate limits

    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        print(f"  Processing batch {i//batch_size + 1}/{(len(tasks) + batch_size - 1)//batch_size}...")
        batch_results = await asyncio.gather(*batch)
        results.extend(batch_results)

        # Small delay between batches for rate limiting
        if i + batch_size < len(tasks):
            await asyncio.sleep(2)

    # Sort by chunk_id and compile
    results.sort(key=lambda x: x[0])

    output = ["# Agent Ecology V2 - Specification Summary\n"]
    output.append("*Auto-generated faithful summary of the full specification*\n")
    output.append("---\n")

    for chunk_id, section_name, summary in results:
        output.append(f"\n## {section_name}\n")
        output.append(summary)
        output.append("\n")

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(output))

    print(f"\nWritten to {OUTPUT_FILE}")
    print(f"Total sections: {len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
