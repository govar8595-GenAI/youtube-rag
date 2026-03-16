import argparse
import json
import requests

API = "http://localhost:8000"

EXAMPLE_QUERIES = [
    # video_specific_question
    "What is the main topic of this video?",
    # timestamp_lookup
    "When does the speaker first mention machine learning?",
    # summarization
    "Give me a 3-sentence summary of the key points covered.",
    # conceptual_question
    "Can you explain the concept of attention mechanism mentioned in the video?",
    # general_information
    "What are the latest benchmarks for GPT-4o on reasoning tasks?",
]


def ingest(url: str, title: str = "") -> str:
    print(f"\n📥  Ingesting: {url}")
    r = requests.post(f"{API}/ingest", json={"url": url, "title": title})
    r.raise_for_status()
    data = r.json()
    print(f"    ✅  video_id={data['video_id']}, chunks={data['num_chunks']}")
    return data["video_id"]


def ask(video_id: str, question: str) -> None:
    print(f"\n{'─'*70}")
    print(f"❓  {question}")
    r = requests.post(f"{API}/chat", json={"video_id": video_id, "question": question})
    r.raise_for_status()
    data = r.json()

    print(f"\n💬  Answer:\n{data['answer']}")
    print(f"\n📊  Intent: {data['intent']} | Confidence: {data['confidence']}")

    print("\n📚  Sources:")
    for src in data["sources"]:
        if src["type"] == "youtube":
            print(f"    🎬  [{src.get('timestamp', '')}]  {src.get('youtube_url', '')}")
        else:
            print(f"    🌐  {src.get('title', '')} → {src.get('url', '')}")

    ev = data.get("evaluation", {})
    print(f"\n🔍  Evaluation: groundedness={ev.get('groundedness_score'):.0%}  "
          f"completeness={ev.get('completeness_score'):.0%}  "
          f"hallucination={ev.get('hallucination_risk')}")

    print("\n📋  Retrieval log:")
    for step in data["retrieval_log"]:
        print(f"    • {step}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--title", default="", help="Optional video title")
    args = parser.parse_args()

    video_id = ingest(args.url, args.title)

    for query in EXAMPLE_QUERIES:
        try:
            ask(video_id, query)
        except Exception as exc:
            print(f"    ⚠️  Query failed: {exc}")


if __name__ == "__main__":
    main()
