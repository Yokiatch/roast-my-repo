from github_fetcher import fetch_repo
from analyzer import analyze_repo

data = fetch_repo("https://github.com/Yokiatch/interview-assistant")
print("Fetched repo, running analysis...")
result = analyze_repo(data)

print("\n🔥 ROAST:")
print(result["roast"])
print("\n📊 SCORECARD:")
for dim, val in result["scorecard"].items():
    print(f"  {dim}: {val['score']}/10 — {val['reason']}")
print(f"\n💼 HIRE SCORE: {result['hire_score']}/10")
print(f"VERDICT: {result['hire_verdict']}")
print("\n🚨 RED FLAGS:")
for flag in result["red_flags"]:
    print(f"  • {flag}")